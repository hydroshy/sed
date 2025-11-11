# FIX: Camera Frame Color Format Issue (BGR vs RGB)

## Vấn Đề
Khi sử dụng SaveImage Tool, ảnh được lưu ra có màu sắc sai (BGR thay vì RGB).
- CameraView hiển thị đúng màu RGB
- ReviewView hiển thị đúng màu RGB
- Nhưng SaveImage Tool lưu ảnh BGR

## Nguyên Nhân Gốc

### Luồng Frame Gốc (Sai):
```
Camera (BGR)
    ↓
_on_frame_from_camera(frame) - frame là BGR
    ↓
SaveImageTool.process(frame)
    ↓ [Không chuyển đổi vì nghĩ frame là BGR]
cv2.imwrite() - lưu BGR
    ↓
FILE: BGR ❌
```

### Vấn Đề:
1. Frame từ camera là **BGR** (định dạng mặc định của camera/OpenCV)
2. CameraView convert BGR→RGB để **hiển thị đúng**
3. Nhưng **SaveImageTool nhận frame BGR gốc** từ camera_manager
4. SaveImageTool lưu BGR như-là
5. **Kết quả**: Ảnh lưu dưới dạng BGR, khi mở sẽ hiển thị sai màu

## Sửa Chữa Áp Dụng

### File: `tools/saveimage_tool.py` - Method `save_image_array()`

**Thay đổi logic chuyển đổi màu:**

**Trước:**
```python
if input_format and input_format.startswith('RGB'):
    # Convert RGB->BGR
    save_image = cv2.cvtColor(save_image, cv2.COLOR_RGB2BGR)
else:
    # Assume BGR, no conversion
    pass
```

**Sau:**
```python
if input_format and input_format.startswith('RGB'):
    # Already RGB, save as-is
    pass
else:
    # BGR from camera - convert BGR->RGB for saving
    logger.info("SaveImageTool: Input format BGR from camera, converting to RGB for saving")
    save_image = cv2.cvtColor(save_image, cv2.COLOR_BGR2RGB)
```

### Điểm Chính Yếu:
1. Frame từ camera là **BGR** → set `pixel_format = 'BGR888'` trong context
2. SaveImageTool nhận BGR
3. **Convert BGR→RGB trước lưu** (thay vì để BGR)
4. `cv2.imwrite()` lưu array RGB như-là
5. **Kết quả**: File lưu RGB ✅

## Luồng Frame Sau Sửa:

```
Camera (BGR)
    ↓
_on_frame_from_camera(frame, pixel_format='BGR888')
    ↓
SaveImageTool.process(frame, context={pixel_format: 'BGR888'})
    ↓ [Detect format là BGR]
Sửa lỗi: Convert BGR→RGB
    ↓
cv2.imwrite() - lưu RGB
    ↓
FILE: RGB ✅
```

## Kết Quả
- ✅ CameraView hiển thị RGB (như trước)
- ✅ ReviewView hiển thị RGB (như trước)
- ✅ **SaveImage Tool lưu RGB (mới)**
- ✅ Ảnh được lưu với màu sắc đúng

## Files Modified
- `gui/camera_manager.py` - Đảm bảo truyền `pixel_format='BGR888'` vào context
- `tools/saveimage_tool.py` - Thêm logic convert BGR→RGB trước lưu khi frame là BGR

## Cách Kiểm Tra
1. Chạy ứng dụng
2. Chụp ảnh (Save Image Tool)
3. Mở ảnh được lưu trong Paint/Photoshop/Preview
4. **Màu sắc phải khớp với cameraView** ✅
