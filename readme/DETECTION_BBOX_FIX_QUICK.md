# Quick Reference: Bounding Box Detection Fix

## Problem
- ReviewView showing `detections=0`
- No green bounding boxes appearing on review thumbnails
- Detection results not being extracted correctly

## Solution

### Issue #1: Job Results Navigation
**Wrong path:**
```python
# ❌ OLD - Iterating on wrong level
for tool_name, tool_result in results.items():  # Missing 'results' key!
```

**Correct path:**
```python
# ✅ NEW - Navigate through job structure
if 'results' not in results:
    return
tool_results = results['results']  # Get the tool dict
for tool_name, tool_result in tool_results.items():
    if 'data' in tool_result:
        detections = tool_result['data']['detections']
```

### Issue #2: Coordinate Keys
**Wrong extraction:**
```python
# ❌ OLD - Looking for 'bbox' key (doesn't exist)
bbox = detection.get('bbox', [])
if len(bbox) >= 4:
    x1, y1, x2, y2 = bbox
```

**Correct extraction:**
```python
# ✅ NEW - Support both formats
bbox = detection.get('bbox', None)
if bbox and len(bbox) >= 4:
    x1, y1, x2, y2 = bbox[:4]
else:
    # Use x1/y1/x2/y2 keys (actual format)
    x1 = int(detection.get('x1', 0))
    y1 = int(detection.get('y1', 0))
    x2 = int(detection.get('x2', 0))
    y2 = int(detection.get('y2', 0))
```

## Data Structure
```
Job Results:
{
  'results': {
    'Detect Tool': {
      'data': {
        'detections': [
          {'class_name': 'pilsner333', 'confidence': 0.91, 'x1': 224, 'y1': 126, 'x2': 426, 'y2': 418}
        ]
      }
    }
  }
}
```

## Files Modified
- `gui/camera_view.py` line 605: `_handle_detection_results()` method
- `gui/camera_view.py` line 2084: `_display_frame_in_review_view()` method

## Expected Result After Fix
✅ Green bounding boxes on review frames  
✅ Red background labels with class name + confidence  
✅ Detections synchronized with frames  
✅ All 5 review thumbnails showing frames correctly

## Debug Logs to Check
```
[Detection Extract] ✅ Found X detections in Detect Tool
Updated most recent detections in history
Frame history: 5, Detections history: 5, In sync: True
[ReviewLabel] reviewLabel_N - detections=1
[ReviewView N] Drawing 1 detections
```
