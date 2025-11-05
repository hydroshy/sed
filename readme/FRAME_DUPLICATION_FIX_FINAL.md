# Frame Duplication Fix - Final Implementation

## Problem Statement

Frames were being added to the frame history **twice** per trigger capture instead of once. This caused:
- Two identical frames in the review history per trigger
- Incorrect frame-to-status mapping (showing two frames for one trigger)
- Frame history display duplicating entries

### Root Cause Analysis

Through detailed logging, discovered:
- **Single signal emission** but **double handler invocation**
- `frameProcessed` signal emitted ONCE (emit #4)
- But `_handle_processed_frame()` called TWICE (at timestamps within 1ms)
- Evidence:
  ```
  2025-10-31 20:24:11,015 - [CameraView] _handle_processed_frame called  
  2025-10-31 20:24:11,016 - [FrameHistory] New frame received  
  2025-10-31 20:24:11,016 - [CameraView] _handle_processed_frame called  ← SECOND CALL
  2025-10-31 20:24:11,017 - [FrameHistory] New frame received  ← DUPLICATE
  ```

### Why It Happened

PyQt5 signals can have **multiple handlers connected to the same slot**:
1. User edits DetectTool threshold (0.5 → 0.95) and clicks Apply
2. Camera stopped → `_stop_camera_display_worker()` called
3. OLD worker reference saved for cleanup
4. Camera restarted → `_start_camera_display_worker()` called
5. NEW worker created and handler connected
6. BUT: OLD worker's signal still had active connections from before
7. Result: When signal emitted from NEW worker, both NEW and OLD handlers fired

**Problem with initial fix:**
- Only tried to disconnect OLD worker's signal
- But old signal connections might be managed by PyQt internally
- `disconnect()` with specific handler might not work properly

## Solution Implemented

### 1. Aggressive Disconnect in `_start_camera_display_worker()` (camera_view.py)

**Changed from:**
```python
# Old approach - try to disconnect specific handler
try:
    self.camera_display_worker.frameProcessed.disconnect(self._handle_processed_frame)
except TypeError:
    pass  # Expected if no connection
```

**Changed to:**
```python
# New approach - disconnect ALL handlers from signal first
try:
    self.camera_display_worker.frameProcessed.disconnect()  # No parameter = disconnect ALL
    logging.warning(f"[CameraView] ✅ Disconnected ALL handlers from NEW worker (clean slate)")
except TypeError:
    logging.warning(f"[CameraView] No existing handlers on NEW worker (expected - first time)")
```

**Key Points:**
- `signal.disconnect()` without parameters disconnects **ALL handlers** from that signal
- Called BEFORE connecting new handler to ensure clean slate
- Also disconnect ALL from old worker's signal before cleanup

**Code Changes:**
```python
# Disconnect ALL existing connections from NEW worker FIRST
try:
    self.camera_display_worker.frameProcessed.disconnect()
    logging.warning(f"[CameraView] ✅ Disconnected ALL handlers from NEW worker (clean slate)")
except TypeError:
    logging.warning(f"[CameraView] No existing handlers on NEW worker (expected - first time)")

# Connect handler to NEW worker's signal
self.camera_display_worker.frameProcessed.connect(self._handle_processed_frame)
```

### 2. Proper Old Worker Cleanup

**Disconnect ALL handlers from old worker's signal:**
```python
if hasattr(self, '_old_display_worker') and self._old_display_worker is not None:
    logging.warning(f"[CameraView] Found OLD worker (id: {id(self._old_display_worker)}), disconnecting ALL handlers...")
    try:
        # Disconnect ALL handlers from old worker's signal (not just specific ones)
        self._old_display_worker.frameProcessed.disconnect()
        logging.warning("[CameraView] ✅ OLD worker's frameProcessed signal: ALL handlers disconnected")
    except Exception as e:
        logging.warning(f"[CameraView] ⚠️  Could not disconnect all handlers from old worker: {e}")
    self._old_display_worker = None
```

### 3. Clear Frame History When Editing Tools

Added new functionality to clear review labels and frame history when users enter tool editing mode.

**Files Modified:**
1. `gui/camera_view.py` - Added `clear_frame_history_and_reviews()`
2. `gui/result_manager.py` - Added `clear_history()`  
3. `gui/settings_manager.py` - Call clear when tool editing starts

**Implementation:**

**camera_view.py - `clear_frame_history_and_reviews()`:**
```python
def clear_frame_history_and_reviews(self):
    """Clear frame history and all review labels (called when editing tools)"""
    try:
        logging.info("[CameraView] === CLEARING FRAME HISTORY AND REVIEWS ===")
        
        # Clear frame history
        with self.frame_history_lock:
            self.frame_history.clear()
            self.frame_history_queue.clear()
        logging.info("[CameraView] ✅ Frame history cleared")
        
        # Clear all review labels (if available)
        if hasattr(self, 'review_labels') and self.review_labels:
            for i in range(1, 6):  # Labels 1-5
                label_name = f'reviewLabel_{i}'
                if label_name in self.review_labels:
                    label = self.review_labels[label_name]
                    label.clear()
                    label.setText("")
                    label.setStyleSheet("")
                    logging.info(f"[CameraView] ✅ Cleared {label_name}")
        
        # Clear result manager history
        try:
            if hasattr(self, 'main_window') and self.main_window:
                result_manager = getattr(self.main_window, 'result_manager', None)
                if result_manager:
                    result_manager.clear_history()
                    logging.info("[CameraView] ✅ Cleared result manager history")
        except Exception as e:
            logging.warning(f"[CameraView] Could not clear result manager: {e}")
        
        logging.info("[CameraView] === FRAME HISTORY AND REVIEWS CLEARED ===")
```

**result_manager.py - `clear_history()`:**
```python
def clear_history(self):
    """Clear frame status history (called when editing tools)"""
    try:
        self.frame_status_history.clear()
        logging.info("[ResultManager] Frame status history cleared")
    except Exception as e:
        logger.error(f"ResultManager: Error clearing frame status history: {e}")
```

**settings_manager.py - Integration:**
```python
def switch_to_tool_setting_page(self, tool_name):
    """..."""
    # ✅ CLEAR FRAME HISTORY when entering tool editing mode
    try:
        if hasattr(self.main_window, 'camera_manager') and self.main_window.camera_manager:
            camera_view = self.main_window.camera_manager.camera_view
            if camera_view:
                camera_view.clear_frame_history_and_reviews()
                logging.info("SettingsManager: Cleared frame history when entering tool editing")
    except Exception as e:
        logging.warning(f"SettingsManager: Could not clear frame history: {e}")
    
    # ... rest of method
```

## Testing Strategy

### Expected Behavior After Fix

1. **Frame Duplication Fix:**
   - Single trigger → Single frame in history (not two)
   - `_handle_processed_frame` called ONCE per signal emit (not twice)
   - Frame shown in exactly one review label position

2. **Review Label Clearing:**
   - When clicking on a tool to edit, all 5 review labels clear
   - Frame history empties
   - Result status history empties
   - Fresh start for new captures

### How to Test

**Test 1: Frame Duplication**
```
1. Launch application
2. Trigger one capture (click Trigger button)
3. Check review display - should show 1 frame
4. Look for logs:
   - "frameProcessed signal emitted (emit #N)" - count emits
   - "[CameraView] _handle_processed_frame called" - should match emit count
5. If fix works: emit count = handler call count
```

**Test 2: Multiple Triggers**
```
1. Trigger multiple captures in sequence
2. Review display should show up to 5 frames (most recent first)
3. Each frame appears exactly once
4. Look for logs showing frame history queue updating correctly
```

**Test 3: Tool Editing Clear**
```
1. Trigger 3-5 captures, fill review display
2. Click on "Detect Tool" to edit it
3. Verify all 5 review labels clear immediately
4. Look for logs: "[CameraView] === CLEARING FRAME HISTORY AND REVIEWS ==="
5. Apply new settings and trigger new captures
6. New frames should be fresh, not mixed with old ones
```

**Test 4: Settings Apply Flow**
```
1. Edit threshold (0.5 → 0.95)
2. Click Apply
3. Trigger new capture
4. Frame should appear once (not twice)
5. Check logs for worker lifecycle markers
```

## Implementation Files

| File | Changes | Line Range |
|------|---------|-----------|
| `gui/camera_view.py` | _start_camera_display_worker() - aggressive disconnect | 1604-1655 |
| `gui/camera_view.py` | _stop_camera_display_worker() - enhanced cleanup | 1657-1680 |
| `gui/camera_view.py` | clear_frame_history_and_reviews() - new method | ~1570-1605 |
| `gui/result_manager.py` | clear_history() - new method | ~425-432 |
| `gui/settings_manager.py` | switch_to_tool_setting_page() - call clear | 124-140 |

## Why This Fix Works

1. **Comprehensive Disconnect:** `signal.disconnect()` with no parameters ensures ALL handlers disconnected, not just specific ones
2. **Clean Slate:** Disconnect before connect ensures new handler is the only connection
3. **Proper Lifecycle:** Save old worker → disconnect all its handlers → create new worker → ensure clean connection
4. **User Expectation:** Clear history when tool editing to match UI refresh pattern
5. **Thread Safety:** Uses existing locks for thread-safe clearing

## Verification Checklist

- [ ] Single capture produces single frame in history
- [ ] _handle_processed_frame called once per signal emit
- [ ] Multiple triggers show frames in correct order (newest first)
- [ ] Tool editing clears frame history and labels
- [ ] Settings changes don't create duplicate frame connections
- [ ] Frame-to-status mapping is correct (no duplicates in review display)
- [ ] No memory leaks from old worker connections
- [ ] Logs show proper worker lifecycle

## Future Improvements

1. **Signal Wrapper Class:** Create a custom signal wrapper to ensure single connection
2. **Connection Manager:** Centralized connection management to prevent accidental duplicates
3. **Weak References:** Use weak references for worker lifecycle management
4. **Qt.UniqueConnection:** Use Qt.UniqueConnection flag if PyQt5 supports it

## References

- PyQt5 Signals: https://doc.qt.io/qt-5/signalsandslots.html
- disconnect() behavior: Calling without parameters disconnects ALL handlers
- Previous fix attempts: Phase 11c attempted disconnect with specific handler (didn't work)
- Logs that identified issue: Phase 11e diagnostic logging with object IDs

## Conclusion

The frame duplication issue was caused by leftover signal connections from old workers persisting after new workers were created. The fix uses aggressive disconnection (disconnect ALL handlers) before setting up new connections, combined with proper old worker cleanup. Additionally, frame history is now cleared when users enter tool editing mode to provide a cleaner, more intuitive user experience.
