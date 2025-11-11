# FIX: ReviewView Color Issue (Màu sắc sai trong reviewView)

## Vấn đề
ReviewView hiển thị màu sắc sai so với cameraView (ví dụ: đỏ thành xanh, xanh thành đỏ).

## Nguyên nhân Gốc
Trong `_display_qimage()` method, frame được convert lại từ BGR→RGB:

```python
# ❌ WRONG:
rgb_frame = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
```

**Nhưng** `self.current_frame` đã là RGB rồi! Nó được set từ `frame_for_history` trong `_handle_processed_frame()`, và frame này đã được convert sang RGB trong `CameraDisplayWorker._process_frame_to_qimage()`.

Kết quả:
- Frame RGB được convert BGR→RGB lại
- Màu B (xanh lam) ↔ R (đỏ) bị đảo
- ReviewView hiển thị màu sai

## Luồng Frame
```
CameraStream (BGR)
    ↓
CameraDisplayWorker._process_frame_to_qimage()
    ↓ [Convert BGR→RGB]
frame_to_process (RGB) ✅
    ↓ [Return as frame_for_history]
_handle_processed_frame()
    ↓ [Set self.current_frame = frame_for_history]
self.current_frame (RGB) ✅
    ↓
_display_qimage()
    ↓ [❌ WRONG: Convert BGR→RGB lại]
rgb_frame (BGR) ❌ [Màu sai!]
    ↓
update_frame_history()
    ↓
reviewView display [Màu sai!]
```

## Sửa Chữa Áp Dụng

**File: `gui/camera_view.py` - Method `_display_qimage()`**

Thay vì:
```python
rgb_frame = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
self.update_frame_history(rgb_frame)
```

Thành:
```python
# current_frame is already RGB (converted in CameraDisplayWorker._process_frame_to_qimage)
# Use it directly without conversion
self.update_frame_history(self.current_frame)
```

## Kết Quả
✅ Frame được lưu vào history với màu RGB đúng
✅ ReviewView hiển thị màu sắc đúng như cameraView
✅ Không có conversion lặp lại (BGR→RGB→BGR→RGB)

## Kiểm Tra Lại
Luồng frame sau khi sửa:
```
CameraStream (BGR)
    ↓
CameraDisplayWorker._process_frame_to_qimage()
    ↓ [Convert BGR→RGB]
frame_to_process (RGB) ✅
    ↓ [Return as frame_for_history]
_handle_processed_frame()
    ↓ [Set self.current_frame = frame_for_history]
self.current_frame (RGB) ✅
    ↓
_display_qimage()
    ↓ [✅ Use directly - NO conversion]
self.current_frame (RGB) ✅
    ↓
update_frame_history()
    ↓
reviewView display [Màu đúng! ✅]
```

## Files Modified
- `gui/camera_view.py` - Line ~1740-1750: Removed incorrect color conversion in `_display_qimage()`
