# Quick Fix: Empty Detections Display Bug

## Problem (User Report)
"Việc hiển thị bây giờ đang bị sai lệch" (Display showing wrong data)
- All review frames showing 1 detection
- Even frames with NO detections show old detection boxes

## Root Cause (In Code)
```python
# ❌ WRONG - Only updates when detections > 0
if detections is not None and len(detections) > 0:
    detections_history[-1] = detections.copy()
else:
    # NOTHING! Old data remains!
```

Result: Frames with 0 detections keep the previous frame's detections!

## Solution Applied
```python
# ✅ CORRECT - Always updates, even when empty
if detections is not None:
    if len(detections) > 0:
        # Log individual detections
        for det in detections:
            logging.debug(...)
    
    # ALWAYS update, regardless of count
    detections_history[-1] = detections.copy()  # [] if empty, [det] if has detections
```

## Result
| Frame | Detections | Before | After |
|-------|-----------|--------|-------|
| Frame 1 | 1 found | ✅ Shows 1 box | ✅ Shows 1 box |
| Frame 2 | 0 found | ❌ Shows 1 box (WRONG!) | ✅ Shows 0 boxes |
| Frame 3 | 0 found | ❌ Shows 1 box (WRONG!) | ✅ Shows 0 boxes |
| Frame 4 | 1 found | ✅ Shows 1 box | ✅ Shows 1 box |
| Frame 5 | 0 found | ❌ Shows 1 box (WRONG!) | ✅ Shows 0 boxes |

## Files Changed
- `gui/camera_view.py` line 625-695 in `_handle_detection_results()`

## Key Insight
**Parallel data structures MUST stay in sync!**

When you have:
- `frame_history = [Frame1, Frame2, Frame3]`
- `detections_history = [?, ?, ?]`

EVERY operation on one must update the other, including empty updates.

```
Good practice:
frame_history[i]     ↔ detections_history[i]    (ALWAYS paired!)

Bad practice:
frame_history[i]     ↔ detections_history[i]    (only if detections exist!)
```

## Testing
Look for these logs after fix:

**With detections:**
```
[Detection Extract] ✅ Found 1 detections
Updated most recent detections in history: 1 dets
[ReviewView 1] Drawing 1 detections
```

**Without detections:**
```
[Detection Extract] ✅ Found 0 detections
Updated most recent detections in history: 0 dets  ← NEW! (was missing before)
[ReviewView 1] Drawing 0 detections
```
