# Frame History Synchronization - Quick Fix

## Issue
ReviewView frames bị **đứt quãng** - không đúng thứ tự, bounding boxes không match

## Why?
**Multithreading race condition:**
- Frame add vào history NGAY (UI thread) → detections = None
- 200ms sau: Detections tính xong (Job thread) → add detections 
- **Result:** Frame history[0]=Frame A, Detections history[0]=None, Detections history[1]=A
- **ReviewView displays mismatch!**

## How Fixed
Moved frame history add from **display time** to **detection time**:

**BEFORE (Wrong):**
```
_display_qimage() → update_frame_history(frame, None)
                ↓ 200ms later
_handle_detection_results() → add detections
Result: ❌ OUT OF SYNC
```

**AFTER (Correct):**
```
_display_qimage() → [do nothing]
                ↓ 200ms later (job completes)
_handle_detection_results() → update_frame_history(frame, detections)
Result: ✅ SYNCHRONIZED
```

## Technical Change
Two code sections modified in `gui/camera_view.py`:

**1. Line ~1828: Disable frame add in display**
```python
if False:  # Disabled - see _handle_detection_results
    # self.update_frame_history() moved to detection handler
```

**2. Line ~625: Add frame+detections in detection handler**
```python
if detection_results and 'detections' in detection_results:
    # ...
    # ✅ Add frame+detections TOGETHER when both ready
    self.update_frame_history(rgb_frame, detections=detections)
```

## Result
✅ ReviewView frames now display in correct order  
✅ Bounding boxes match their frames  
✅ No more "đứt quãng" or frame skipping  
✅ Perfect index synchronization  

## Testing
Check logs:
```
Frame history: 1, Detections history: 1, Histories in sync: True
                                       ↑
                                    Must be True
```

## Files Changed
- `gui/camera_view.py`

## No Breaking Changes
- ReviewView delay slightly longer (waits for job) - this is CORRECT
- Still shows last 5 frames in history
- Still updates every 300ms
- Backward compatible with all existing code
