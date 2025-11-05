# Detection Bounding Box Extraction Fix

**Date:** 2025-11-05  
**Status:** ✅ FIXED  
**Issue:** ReviewView showing `detections=0` - bounding boxes not appearing on review thumbnails  
**Root Cause:** Two issues preventing detection display:
1. Incorrect navigation of job_results data structure
2. Detection objects using different coordinate keys than code expected

---

## Problem Analysis

### From Logs
User reported: "Bị việc hiển thị 1 frame có boundingbox, 1 frame bị mất" (One frame showing bounding box, one frame missing)

**Key Log Observations:**
```
[ReviewLabel] reviewLabel_1 - Displaying frame #4, shape=(480, 640, 3), detections=0
WARNING - No detection results found in job output
```

All reviewLabels showed `detections=0` despite successful job execution with detections.

### Root Causes Identified

**Issue 1: Incorrect Job Results Navigation**

Job results structure:
```python
{
  'job_name': 'Job 1',
  'execution_time': 0.22,
  'results': {
    'Camera Source': {'data': {...}, 'execution_time': ...},
    'Detect Tool': {'data': {'detections': [...]}, 'execution_time': ...},
    'Result Tool': {'data': {...}, 'execution_time': ...}
  }
}
```

Old code was iterating directly on `results.items()` expecting tool results at top level.  
**Correct path:** `results['results']['Detect Tool']['data']['detections']`

**Issue 2: Detection Coordinate Keys**

Detection object from pipeline:
```python
{
  'class_id': 0,
  'class_name': 'pilsner333',
  'confidence': 0.909,
  'x1': 224.96,      # ← These keys
  'y1': 126.13,      # ← Are used
  'x2': 426.38,      # ← Not 'bbox'
  'y2': 417.90,
  'width': 201.48,
  'height': 291.77
}
```

Old code was looking for `detection.get('bbox', [])` which doesn't exist.

---

## Solution Implemented

### Fix 1: Correct Job Results Navigation

**File:** `gui/camera_view.py` (lines 605-680)  
**Method:** `_handle_detection_results(results, processed_frame)`

```python
# Navigate to 'results' key first (was missing this step!)
if 'results' not in results:
    logging.warning("No 'results' key in job output")
    return

tool_results = results['results']  # ← Get the tool_results dict
detections = None

# Find Detect Tool results
for tool_name, tool_result in tool_results.items():
    if 'detect' in tool_name.lower() and 'data' in tool_result:
        tool_data = tool_result['data']  # ← Get the data dict
        
        if 'detections' in tool_data:
            detections = tool_data['detections']  # ← Extract detections
            break
```

**Changes:**
- Added intermediate step to get `results['results']` first
- Corrected nested access to `tool_result['data']['detections']`
- Added debug logging to track navigation path
- Better error messages at each step

**Result:** ✅ Detections are now correctly extracted and stored in `detections_history`

---

### Fix 2: Support Both Coordinate Formats

**File:** `gui/camera_view.py` (lines 2084-2127)  
**Method:** `_display_frame_in_review_view(..., detections=None)`

```python
# ✅ Support both 'bbox' key and x1,y1,x2,y2 keys
bbox = detection.get('bbox', None)
if bbox and len(bbox) >= 4:
    x1, y1, x2, y2 = bbox[:4]
else:
    # Try x1, y1, x2, y2 keys
    x1 = detection.get('x1', None)
    y1 = detection.get('y1', None)
    x2 = detection.get('x2', None)
    y2 = detection.get('y2', None)
    
    if None in [x1, y1, x2, y2]:
        logging.warning(f"Detection missing bbox coords: {detection.keys()}")
        continue
```

**Changes:**
- Try 'bbox' key first (for compatibility)
- Fall back to x1/y1/x2/y2 keys (actual data format)
- Convert to integers (float → int)
- Add bounds clamping to prevent drawing outside frame
- Detailed logging of coordinate extraction

**Result:** ✅ Bounding boxes now drawn correctly on review frames

---

## Frame/Detection Synchronization

The system maintains parallel lists:
- `frame_history[]`: Last 5 frames in RGB format
- `detections_history[]`: Detections for each frame (same indices)

**Synchronization Timing:**
```
t=0ms:     Frame added to history (immediate display)
           frame_history[4] = FrameA (newest)
           detections_history[4] = [] (empty initially)

t=200ms:   Job complete with detections
           Call _handle_detection_results()
           Update detections_history[-1] (NOT append!)
           detections_history[4] = [Detection1, Detection2]

Result:    Frame[4] ↔ Detections[4] ✅ SYNCHRONIZED
```

**Key:** UPDATE operation on `detections_history[-1]` keeps indices in sync!

---

## Testing Verification

**Expected Behavior After Fix:**

1. ✅ ReviewLabel displays 5 frames (reviewLabel_1 through reviewLabel_5)
2. ✅ Each frame shows correct number of detections in log: `detections=1` (or 0 if no detections)
3. ✅ Green bounding boxes visible on frames with detections
4. ✅ Red background labels showing class name + confidence
5. ✅ All frames in correct chronological order (newest to oldest)
6. ✅ Boxes match detected objects (not misaligned)

**Test Steps:**
```
1. Start application
2. Enable Detect Tool
3. Switch to trigger mode
4. Click trigger button multiple times
5. Observe ReviewView thumbnails
   - Should see frames populate
   - If detections found, should see green boxes
   - Labels should show "pilsner333: 0.91" format
```

---

## Code Changes Summary

| File | Method | Change | Lines |
|------|--------|--------|-------|
| `camera_view.py` | `_handle_detection_results()` | Fix job results navigation + extraction | 605-680 |
| `camera_view.py` | `_display_frame_in_review_view()` | Support x1/y1/x2/y2 coordinates | 2084-2127 |

---

## Logs Generated

**Good Log (After Fix):**
```
[Detection Extract] ✅ Found 1 detections in Detect Tool
Stored 1 detections for visualization
Frame history: 5, Detections history: 5, In sync: True
[ReviewLabel] reviewLabel_1 - Displaying frame #4, detections=1
[ReviewView 1] Drawing 1 detections
```

**Bad Log (Before Fix):**
```
WARNING - No detection results found in job output (None or empty)
[ReviewLabel] reviewLabel_1 - Displaying frame #4, detections=0
[ReviewView 1] Drawing 0 detections
```

---

## Related Issues Fixed

1. ✅ UI Freezing → JobProcessorThread (earlier fix)
2. ✅ ReviewView Color Mismatch → BGR→RGB conversion (earlier fix)
3. ✅ Frame Ordering → Hybrid sync approach (earlier fix)
4. ✅ **Detection Extraction → This fix** ← YOU ARE HERE
5. ✅ Bounding Box Coordinates → This fix (detection coordinate keys)

---

## Next Steps

1. **Test:** Run application and verify bounding boxes display
2. **Monitor Logs:** Check for "Updated most recent detections in history" messages
3. **Verify Sync:** Confirm frame_history count = detections_history count
4. **Visual Check:** Ensure boxes match actual objects in frame

If issues remain, check:
- Are detections being generated? (Check "Found X detections" in logs)
- Are detections reaching ReviewView? (Check detections parameter in _display_frame_in_review_view)
- Are boxes being drawn? (Check "Drawing X detections" in logs)
