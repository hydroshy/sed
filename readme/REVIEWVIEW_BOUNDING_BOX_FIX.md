# ReviewView Bounding Box Fix

## Problem
- ReviewView hiển thị frame đúng nhưng không vẽ bounding boxes
- Bounding box chỉ hiển thị trên main cameraView, không hiển thị trên 5 review thumbnails

## Root Cause
**Frame và Detections không được track cùng nhau:**
- `frame_history`: lưu trữ 5 frame gần nhất
- `detection_results`: chỉ lưu detection của frame HIỆN TẠI
- `detections_history`: **không tồn tại** → không có cách lấy detections của frame trong history

**Flow bị lỗi:**
1. Frame display → add vào `frame_history`
2. Job process frame → `_handle_detection_results` called
3. Detections tính ra nhưng **không được lưu với frame** trong history
4. Review view vẽ frame nhưng **không có detections để vẽ bounding box**

## Solution

### 1. Added `detections_history` List
```python
# Line 266
self.detections_history = []  # ✅ Store detections for each frame (parallel to frame_history)
```

### 2. Queue Structure Change
**Before:**
- `frame_history_queue`: chứa frames

**After:**
- `frame_history_queue`: chứa tuples `(frame, detections)`

### 3. Update Frame History Flow

**In `_display_qimage` (line 1820):**
```python
# Pass detections along with frame to history
self.update_frame_history(rgb_frame, detections=self.detection_results if self.detection_results else None)
```

**In `update_frame_history` (line 1539):**
```python
# Create tuple and add to queue
item = (history_frame.copy(), detections if detections else [])
self.frame_history_queue.append(item)
```

**In `FrameHistoryWorker.process_frame_history` (line 31):**
```python
# Extract frame and detections from tuple
frame, detections = item
# Keep histories in sync
self.camera_view.frame_history.append(frame.copy())
self.camera_view.detections_history.append(detections if detections else [])
```

### 4. Draw Bounding Boxes on Review Frames

**In `_update_review_views_with_frames` (line 1892):**
```python
# Get detections for this frame (parallel index)
detections = []
if frame_index >= 0 and frame_index < len(self.detections_history):
    detections = self.detections_history[frame_index]

# Pass detections to display method
self._display_frame_in_review_view(review_view, frame, i + 1, detections)
```

**In `_display_frame_in_review_view` (line 1947):**
```python
def _display_frame_in_review_view(self, review_view, frame, view_number, detections=None):
    # ... color conversion code ...
    
    # ✅ Draw bounding boxes BEFORE converting to QPixmap
    if detections and len(detections) > 0:
        display_frame_bgr = cv2.cvtColor(display_frame, cv2.COLOR_RGB2BGR)
        
        for detection in detections:
            bbox = detection.get('bbox', [])
            if len(bbox) >= 4:
                x1, y1, x2, y2 = bbox
                # Apply resize scale if frame was resized
                if resize_scale != 1.0:
                    x1 = int(x1 * resize_scale)
                    y1 = int(y1 * resize_scale)
                    x2 = int(x2 * resize_scale)
                    y2 = int(y2 * resize_scale)
                
                # Draw bounding box (green)
                cv2.rectangle(display_frame_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw label with confidence
                class_name = detection.get('class_name', 'Object')
                confidence = detection.get('confidence', 0.0)
                label = f"{class_name}: {confidence:.2f}"
                
                # Draw label background (red) and text (white)
                # ...
        
        display_frame = cv2.cvtColor(display_frame_bgr, cv2.COLOR_BGR2RGB)
```

### 5. Keep Histories in Sync

**In `clear_frame_history_and_reviews` (line 1575):**
```python
with self.frame_history_lock:
    self.frame_history.clear()
    self.detections_history.clear()  # ✅ Also clear detections history
    self.frame_history_queue.clear()
```

## Files Modified
- `e:\PROJECT\sed\gui\camera_view.py`

## Changes Summary

| Line | Change | Impact |
|------|--------|--------|
| 266 | Add `self.detections_history = []` | Store detections parallel to frames |
| 31-46 | Update `FrameHistoryWorker.process_frame_history()` | Extract and store detections from queue |
| 1575 | Clear `detections_history` | Keep histories in sync |
| 1539 | Modify `update_frame_history()` | Accept detections parameter, create tuple queue items |
| 1820 | Pass `self.detection_results` to `update_frame_history` | Send current detections with frame |
| 1892 | Get detections from `detections_history` | Match detections with frame index |
| 1947 | Update `_display_frame_in_review_view` signature | Accept detections parameter |
| 1955-2000 | Draw bounding boxes on review frames | Render detection boxes with labels |

## Test Checklist

- [ ] ReviewView displays frames with bounding boxes
- [ ] Bounding boxes align correctly with objects
- [ ] Labels show class name and confidence
- [ ] Colors are consistent (green boxes, red label backgrounds, white text)
- [ ] Bounding boxes scale correctly with resized frames (320x240)
- [ ] All 5 review labels show boxes correctly
- [ ] Clear frame history clears both frames and detections
- [ ] No errors in logs when detections are empty

## Performance Considerations

- Bounding box drawing uses cv2 operations (fast)
- Resizing happens before drawing (smaller target = faster drawing)
- Detections stored as-is (minimal memory overhead)
- Only 5 frames + detections in history (fixed memory)

## Edge Cases Handled

1. **Frame resized**: Bounding box coordinates scaled by `resize_scale`
2. **No detections**: Empty list stored, no drawing errors
3. **Legacy queue items**: Handles both tuple and frame-only items
4. **Color format**: Converts RGB↔BGR for cv2 operations, back to RGB for QPixmap
5. **Memory sync**: Histories kept same length (pop from both when full)
