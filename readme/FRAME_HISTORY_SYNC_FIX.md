# ReviewView Frame Ordering Fix - Threading Synchronization

## Problem
- ReviewView hiển thị **đứt quãng**, frame không đúng thứ tự
- Bounding box không match với frame hiển thị
- Detections từ frame A nhưng hiển thị trên frame B

## Root Cause - Multithreading Desynchronization

**Old Flow (WRONG):**
```
Thread: Display (UI)
  ↓
Frame A hiển thị (_display_qimage)
  ↓
update_frame_history(frameA, None)  ← Detections still being calculated!
  ↓
frame_history: [frameA, ...]
detections_history: [None, ...]     ← Mismatch!

Thread: Job Processing
  ↓
[200ms delay - job calculating detections]
  ↓
_handle_detection_results()
  ↓
detections_history.append(detectionsA)
  ↓
detections_history: [None, detectionsA, ...]  ← Now 1 item out of sync!
```

**Problem:** Frame được add vào history **TRƯỚC** detections tính ra, dẫn đến mismatch.

**Result:** 
- ReviewView[1] shows Frame A nhưng Detections B (từ frame trước)
- ReviewView[2] shows Frame B nhưng Detections C
- **Frame history bị xáo trộn**

## Solution - Synchronized Add to History

**New Flow (CORRECT):**
```
Thread: Display (UI)
  ↓
Frame A hiển thị (_display_qimage)
  ↓
NO update_frame_history here! ← KEY CHANGE
  ↓

Thread: Job Processing (parallel)
  ↓
[200ms: calculating detections for Frame A]
  ↓
_handle_detection_results() ← Called when job COMPLETE
  ↓
Detections A ready
Current_frame = Frame A (still in memory)
  ↓
update_frame_history(frameA, detectionsA) ← ADD BOTH SYNCHRONIZED!
  ↓
Queue: (frameA, detectionsA)  ← MATCHED!

Thread: FrameHistoryWorker
  ↓
Extract from queue: frame, detections
  ↓
frame_history.append(frameA)
detections_history.append(detectionsA)  ← SAME INDEX!
```

**Result:**
- ✅ Frame history[0] = Frame A, Detections history[0] = Detections A
- ✅ Always matching indices
- ✅ No out-of-sync corruption

## Implementation Changes

### 1. Disable Frame History Add in Display Method
**File:** `gui/camera_view.py` (~line 1828)

**Change:**
```python
# BEFORE: Added frame immediately to history
if self.current_frame is not None:
    rgb_frame = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
    self.update_frame_history(rgb_frame, detections=self.detection_results)

# AFTER: Disabled - frame added later when detections ready
if False:  # Disabled - see _handle_detection_results for correct approach
    # Frame history update moved to _handle_detection_results
```

**Reason:** At this point, detections haven't been calculated yet for this frame.

### 2. Add Frame+Detections in Detection Handler
**File:** `gui/camera_view.py` (~line 625)

**Change:**
```python
if detection_results and 'detections' in detection_results:
    detections = detection_results['detections']
    
    # Store for display
    self.detection_results = detections
    
    # ✅ NOW: Add frame+detections SYNCHRONIZED
    if self.current_frame is not None:
        rgb_frame = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
        # Add BOTH together with guaranteed match
        self.update_frame_history(rgb_frame, detections=detections)
```

**Reason:** `current_frame` is exactly the frame that was just processed. Job callback guarantees frame and detections are matched.

### 3. Queue Structure Stays Same
```python
# update_frame_history creates tuple
item = (history_frame.copy(), detections)
frame_history_queue.append(item)

# FrameHistoryWorker extracts both
frame, detections = item
frame_history.append(frame)
detections_history.append(detections)
```

## Synchronization Guarantee

**Before:** ❌
- Frame added: t=0ms (immediately on display)
- Detections added: t=200ms (after job complete)
- **200ms gap = mismatch**

**After:** ✅
- Frame + Detections added together: t=200ms (when job complete)
- **0ms gap = always matched**

## Flow Diagram

```
UI Thread                   Job Thread              Worker Thread
    |                           |                        |
Frame display                   |                        |
    |                           |                        |
Display QImage              Process frame                |
    | (no history add)           |                        |
    |                       [200ms working]              |
    |                           |                        |
    |                    Job complete                    |
    |                           |                        |
    |<-----detection_results callback                    |
    |                           |                        |
Add to history              (current_frame              |
update_frame_history        still in memory)            |
(frame + detections)            |                        |
    |                           |                        |
Emit to queue-----------> (frame, detections)          |
    |                       tuple created               |
    |                           |                        |
    |                           |            Process queue
    |                           |                  |
    |                           |            Extract: frame, detections
    |                           |                  |
    |                           |            Add BOTH to history
    |                           |                  |
    |                           |            ✅ SYNCHRONIZED!
```

## Verification

**Check logs for:**
```
[FrameHistory] Adding frame+detections to history SYNCHRONIZED - frame shape=(...), detections count=5
Frame history: 1, Detections history: 1, Histories in sync: True
```

**Should show:**
- `Histories in sync: True` ← Key indicator
- Frame count = Detections count
- Same indices → same data

## Files Modified
- `gui/camera_view.py` (2 sections)

## Impact
- ✅ Frame history always synchronized
- ✅ ReviewView displays correct boxes with correct frames
- ✅ No frame skipping or out-of-order display
- ✅ Detections always match their frames
- ⚠️ Slight delay in history update (wait for job complete instead of immediate display)
  - But this is CORRECT behavior - frame shouldn't appear in review until detections ready

## Edge Cases

1. **No job running:** Frame not added to history (correct - no detections)
2. **Job fails:** Fallback detection_results = empty list → added with empty detections
3. **Multiple frames queued:** Worker only keeps latest (`.clear()` then append)
4. **Fast frame rate:** Frames dropped if job slower than capture - no sync issues since only matched pairs added

## Testing

- [ ] Check log shows "Histories in sync: True"
- [ ] ReviewView frames appear in correct order
- [ ] Bounding boxes match detected objects
- [ ] No frames skipped or repeated
- [ ] No performance degradation
- [ ] Works in both trigger and continuous mode

## Performance Note

Slight increase in latency for review history (~job processing time):
- **Before:** Frame in history immediately (even before detection)
- **After:** Frame in history only after detection complete

This is **correct trade-off**: Better to have accurate delayed history than inaccurate real-time history.
