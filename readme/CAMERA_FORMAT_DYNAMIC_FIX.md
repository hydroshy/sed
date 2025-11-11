# FIX: Camera Format Dynamic Detection (RGB vs BGR)

## Vấn Đề Người Dùng Hỏi
> "khi tôi dùng camera_tool chỉnh sang định dạng RGB thì hình ảnh màu có chuyển theo không?"

**Trả Lời**: Vâng, nó sẽ chuyển theo! Nhưng cần xác nhận rằng system đã được update.

## Vấn Đề Đã Phát Hiện

### Trước (Sai):
```python
# gui/camera_manager.py line 340 - HARDCODED
pixel_format = 'BGR888'  # Luôn BGR, bất kể user chọn gì

initial_context = {"force_save": True, "pixel_format": str(pixel_format)}
# Luôn truyền BGR888 dù camera đang ở RGB888
```

**Hệ quả**:
- User chọn RGB888 trong camera_tool
- Camera stream thay đổi sang RGB
- Nhưng SaveImageTool vẫn nhận `pixel_format='BGR888'`
- SaveImageTool convert BGR→RGB (sai!)
- Ảnh được save lại bị swap màu

### Sau (Đúng):
```python
# gui/camera_manager.py lines 339-351 - DYNAMIC
pixel_format = 'BGR888'  # Default
if hasattr(self.camera_stream, 'get_pixel_format'):
    try:
        current_format = self.camera_stream.get_pixel_format()
        if current_format and current_format in ['BGR888', 'RGB888', 'XRGB8888', 'YUV420', 'NV12']:
            pixel_format = current_format
            print(f"DEBUG: Using current camera format: {pixel_format}")
    except Exception as e:
        print(f"DEBUG: Could not get camera format: {e}, using default BGR888")

initial_context = {"force_save": True, "pixel_format": str(pixel_format)}
# Truyền format hiện tại của camera
```

**Lợi Ích**:
- Lấy format hiện tại từ camera stream
- Truyền format chính xác cho SaveImageTool
- SaveImageTool xử lý conversion đúng dựa trên format

## Luồng Hoạt Động Sau Sửa

```
User thay đổi format thành RGB888 trong camera_tool
            ↓
camera_tool gọi camera_manager.set_format_async('RGB888')
            ↓
camera_stream.set_format('RGB888')
            ↓
Frame từ camera: RGB (không phải BGR)
            ↓
_on_frame_from_camera() được gọi
            ↓
Lấy hiện tại format từ camera: 'RGB888'
            ↓
Truyền context: {"force_save": True, "pixel_format": "RGB888"}
            ↓
SaveImageTool nhận format: RGB888
            ↓
Frame đã là RGB → không cần convert
            ↓
cv2.imwrite() lưu RGB
            ↓
FILE: RGB ✅
```

## SaveImageTool Logic (Đã có)

```python
# tools/saveimage_tool.py lines 240-260
if input_format and input_format.startswith('RGB'):
    # Frame đã là RGB
    logger.info("SaveImageTool: Input format RGB, keeping as RGB for saving")
    pass  # Không convert, lưu như-là
else:
    # Frame là BGR
    logger.info("SaveImageTool: Input format BGR, converting to RGB for saving")
    save_image = cv2.cvtColor(save_image, cv2.COLOR_BGR2RGB)
```

## Cách Kiểm Tra

1. **Mở camera_tool (Camera Source)**
2. **Chọn format RGB888** (từ dropdown)
3. **Áp dụng**
4. **Chạy capture image**
5. **Kiểm tra ảnh được save**:
   - Màu sắc phải **đúng như hiển thị trên cameraView**
   - Nếu đúng → fix thành công ✅
   - Nếu sai (đỏ/xanh bị swap) → vấn đề khác

## Debug Logging

Khi capture, xem console log:
```
DEBUG: [CameraManager] Using current camera format: RGB888
DEBUG: [CameraManager] Frame format: RGB888 for job processing
SaveImageTool: Input format RGB, keeping as RGB for saving
```

Nếu thấy log này → format được truyền đúng ✅

## Files Modified

1. **gui/camera_manager.py** - Lines 339-351
   - Thêm dynamic format detection
   - Lấy format từ camera_stream
   - Truyền format chính xác vào context

2. **tools/saveimage_tool.py** - Không cần sửa
   - Logic đã đúng (check input_format)
   - Convert BGR→RGB khi cần
   - Giữ RGB khi đã RGB

## Tóm Tắt

✅ **Câu hỏi**: Khi chuyển định dạng sang RGB, hình ảnh có chuyển theo không?
✅ **Trả lời**: Vâng, nó sẽ chuyển!
✅ **Cách thức**: System giờ **tự động lấy format hiện tại** thay vì hardcode
✅ **Kết quả**: SaveImageTool nhận format chính xác → xử lý conversion đúng → ảnh save đúng
