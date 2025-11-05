# Double Frame Jump Fix - Preventing ReviewView Double Updates

## 问题 (Problem)
When triggering, 2 frames jump/flash at once instead of smooth single frame update.

## 原因 (Root Cause)
**Double Update Trigger:**
1. `_handle_detection_results()` calls `_update_review_views_threaded()` (Fix #4)
2. FrameHistoryWorker ALSO calls `_update_review_views_threaded()` 
3. Both updates happen within milliseconds
4. Result: ReviewView refreshes twice → frames jump/flash

## 解决方案 (Solution)

Instead of preventing the second call entirely, we **update the throttle timestamp** after our immediate update:

```python
# After detecting and updating detections_history:
self._last_review_update = time.time()  # ← Update timestamp!
QTimer.singleShot(0, self._update_review_views_threaded)
```

**How it works:**
1. We trigger immediate update after detection processing
2. We set `_last_review_update = current_time`
3. FrameHistoryWorker checks: `(current_time - _last_review_update) >= 0.3`
4. Since we just updated, the interval isn't met
5. FrameHistoryWorker skips its update (prevents double-trigger)
6. Single smooth frame update ✓

## 代码变更 (Code Change)

**File:** `gui/camera_view.py`  
**Method:** `_handle_detection_results()`  
**Lines:** 691-696

```python
# Force refresh display to show detection boxes
self._show_frame_with_zoom()
logging.info("Refreshed frame display to show detections")

# ✅ CRITICAL FIX: Trigger review view update after detections are updated
# Update the timestamp to prevent double-update from FrameHistoryWorker
logging.info(f"[DETECTION SYNC] Triggering review view update after detection results processed")
self._last_review_update = time.time()  # Update timestamp to throttle FrameHistoryWorker
QTimer.singleShot(0, self._update_review_views_threaded)
```

## 验证 (Verification)

Expected behavior:
- ✅ Click trigger → single smooth frame update
- ✅ No double jump/flash
- ✅ ReviewView shows correct detections immediately
- ✅ No 2nd trigger needed

Look for logs showing single update:
```
INFO - [DETECTION SYNC] Triggering review view update after detection results processed
INFO - [ReviewViewUpdate] Main thread update triggered - frame_history_count=5
```

NOT seeing duplicate updates like:
```
❌ [ReviewViewUpdate] triggered
❌ [ReviewViewUpdate] triggered  (2x within 10ms)
```

## 技术细节 (Technical Details)

### FrameHistoryWorker Throttle Logic
```python
# In FrameHistoryWorker.process_frame_history():
current_time = time.time()
if (current_time - self.camera_view._last_review_update) >= self.camera_view._review_update_interval:
    # Only update if 300ms has passed since last update
    QTimer.singleShot(0, self.camera_view._update_review_views_threaded)
    self.camera_view._last_review_update = current_time
```

### What We Do
- When detection processed, update `_last_review_update`
- This prevents FrameHistoryWorker from triggering within 300ms
- We get 1 immediate update, FrameHistoryWorker gets next slot

### Benefit
- ✅ No double updates on single trigger
- ✅ FrameHistoryWorker still provides periodic fallback updates
- ✅ Both mechanisms complement each other
- ✅ Smooth, responsive display

## 相关 (Related)
- Previous Fix #4: Immediate ReviewView update after detection
- This Fix: Prevents double-update from the previous fix + FrameHistoryWorker

Together: Perfect balance of immediate response + no double-jumping
