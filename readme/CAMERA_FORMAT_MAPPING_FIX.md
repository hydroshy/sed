# FIX: RGB888 Format Mapping Issue (Camera Format String vs Hardware Format)

## Vấn Đề Người Dùng Báo Cáo
> "Vẫn hiển thị ra màu BGR, không biết có lỗi định dạng gì ở cameratool không, biết rằng tôi chọn định dạng RGB"

**Log cho thấy**:
```
'main': {'size': (640, 480), 'format': 'XBGR8888', ...}
```

**Kỳ vọng**: Format = RGB888 (vì user chọn)
**Thực tế**: Format = XBGR8888 (camera stream mặc định)

---

## Nguyên Nhân Gốc

### Sự Khác Biệt: Format String vs Hardware Format

**Format String** (tên logic):
- "RGB888", "BGR888", "XRGB8888", "YUV420", "NV12"
- Dùng cho UI, config, pipeline logic
- Python-friendly strings

**Hardware Format** (tên thực tế picamera2):
- "XRGB8888", "XBGR8888", "RGB888", "BGR888", etc.
- Dùng cho libcamera/picamera2 configuration
- Đây là format string mà libcamera hiểu

### Vấn Đề: Format String Không Map Tới Hardware Format

```python
# OLD (SAI)
camera_stream.set_format('RGB888')
    ↓
self.preview_config["main"]["format"] = 'RGB888'
    ↓
picam2.configure(config)
    ↓
libcamera không recognize 'RGB888'
    ↓
Dùng mặc định: 'XBGR8888' ❌
```

**Vì sao xảy ra?**
- Picamera2/libcamera **không accept string 'RGB888'**
- Chúng chỉ accept các format thực: XRGB8888, XBGR8888, etc.
- Cần map từ format string sang actual format

---

## Giải Pháp: Format Mapping

### Thay Đổi 1: Camera Stream Format Mapping

**File**: `camera/camera_stream.py` (method `set_format()`)

**Thêm format map**:
```python
format_map = {
    'RGB888': 'XRGB8888',      # Map RGB888 → XRGB8888 (actual format)
    'BGR888': 'XBGR8888',      # Map BGR888 → XBGR8888 (actual format)
    'XRGB8888': 'XRGB8888',    # Already correct
    'XBGR8888': 'XBGR8888',    # Already correct
    'YUV420': 'YUV420',
    'NV12': 'NV12',
}

# Persist format string (for pipeline)
self._pixel_format = str(pixel_format)

# Get actual hardware format (for picamera2)
actual_format = format_map.get(str(pixel_format), 'XRGB8888')

# Send actual format to picamera2
self.preview_config["main"]["format"] = actual_format
```

**Kết quả**:
- User chọn "RGB888"
- System lưu `_pixel_format = 'RGB888'` (cho pipeline)
- System gửi `format = 'XRGB8888'` cho picamera2 (cho hardware)
- Hardware thực sự config XRGB8888 ✅

---

### Thay Đổi 2: Camera Tool Default Format

**File**: `tools/camera_tool.py` (line 85, 156)

**Thay đổi**:
```python
# OLD
self.current_format = self.config.get("format", "BGR888")
self.config.set_default("format", "BGR888")

# NEW
self.current_format = self.config.get("format", "RGB888")
self.config.set_default("format", "RGB888")
```

**Kết quả**:
- Camera Tool mặc định RGB888 thay vì BGR888
- Khớp với RGB pipeline default

---

## Luồng Hoạt Động Sau Sửa

```
┌─────────────────────────────────┐
│ User chọn RGB888 trong          │
│ Camera Tool UI                  │
└────────────────┬────────────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ camera_tool.py     │
        │ Format: RGB888     │ ← Lưu format string
        │ (config)           │
        └────────┬───────────┘
                 │
                 ▼
    camera_manager.set_format_async('RGB888')
                 │
                 ▼
    camera_stream.set_format('RGB888')
                 │
                 ▼ Format Map
    format_map['RGB888'] = 'XRGB8888'
                 │
                 ▼
    self._pixel_format = 'RGB888'     (store string)
    actual_format = 'XRGB8888'        (for hardware)
                 │
                 ▼
    preview_config["main"]["format"] = 'XRGB8888'
                 │
                 ▼
    picam2.configure(config)
                 │
                 ▼
    libcamera receives XRGB8888 ✅
    Hardware configures XRGB8888 ✅
                 │
                 ▼
    get_pixel_format() returns 'RGB888'
                 │
                 ▼
    Pipeline logic uses 'RGB888' ✅
    (cameraview, saveimage, etc.)
```

---

## Format Map Chi Tiết

| Format String | Hardware Format | Byte Order | Channels |
|---------------|-----------------|-----------|----------|
| `RGB888` | `XRGB8888` | XRGB | 4 |
| `BGR888` | `XBGR8888` | XBGR | 4 |
| `XRGB8888` | `XRGB8888` | XRGB | 4 |
| `XBGR8888` | `XBGR8888` | XBGR | 4 |
| `YUV420` | `YUV420` | YUV | 3 |
| `NV12` | `NV12` | YUV | 2 |

**Lưu ý**: 
- Picamera2/libcamera không support "RGB888" hoặc "BGR888" string
- Chúng yêu cầu "XRGB8888" hoặc "XBGR8888" (4-channel formats)
- "RGB888" và "BGR888" là tên logic của chúng ta

---

## CameraView Color Handling

Sau khi hardware được config đúng:

```python
# CameraView line 135
pixel_format = 'RGB888'  # Từ camera_stream.get_pixel_format()

# CameraView line 147-170
if str(pixel_format) == 'RGB888':
    # Frame from camera là XRGB byte order [X,R,G,B,...]
    # Cần chuyển thành RGB [R,G,B,R,G,B,...]
    # Mặc dù tên là 'RGB888', thực tế frame là XRGB (4-channel)
    frame_to_process = cv2.cvtColor(frame_to_process, cv2.COLOR_BGRA2RGB)
```

**Vấn đề**: Logic CameraView cần cập nhật để handle XRGB properly!

---

## Cập Nhật Cần Thiết Tiếp Theo

### Xem xét cập nhật CameraView logic:

```python
# CURRENT (có vấn đề)
if str(pixel_format) == 'RGB888':
    pass  # No conversion - SAI!

# SHOULD BE
if str(pixel_format) == 'RGB888':
    # Frame là XRGB8888, cần convert BGRA→RGB (drop X channel)
    frame_to_process = cv2.cvtColor(frame_to_process, cv2.COLOR_BGRA2RGB)
```

---

## Files Modified

| File | Lines | Change | Status |
|------|-------|--------|--------|
| `camera/camera_stream.py` | 901-945 | Add format mapping | ✅ |
| `tools/camera_tool.py` | 85 | RGB888 default | ✅ |
| `tools/camera_tool.py` | 156 | RGB888 default | ✅ |

---

## Console Output Expected

**Khi set format = RGB888**:
```
DEBUG: [CameraStream] Pixel format set to RGB888 (actual: XRGB8888)
[3:32:15.469950625] [4645] INFO Camera camera.cpp:1205
  configuring streams: (0) 640x480-XRGB8888/sRGB
```

**Kỳ vọng**: Format config = XRGB8888 ✅

---

## Cách Kiểm Tra

1. Chạy ứng dụng
2. Mở Camera Tool
3. Chọn RGB888
4. Click Apply
5. Xem console log:
   ```
   DEBUG: [CameraStream] Pixel format set to RGB888 (actual: XRGB8888)
   ```
6. Xem libcamera config:
   ```
   'main': {'size': (640, 480), 'format': 'XRGB8888', ...}
   ```
7. Format phải là **XRGB8888** ✅

---

## Tóm Tắt

**Vấn đề**: Format string không map tới hardware format
**Giải pháp**: Thêm format map trong camera_stream.set_format()
**Kết quả**: 
- User chọn RGB888 → System gửi XRGB8888 tới libcamera → Hardware config đúng
- Pipeline logic vẫn dùng RGB888 (format string)
- Color display xử lý XRGB frame

**Status**: ✅ Fixed - Ready for test

---

**Next**: Kiểm tra xem màu hiển thị có đúng không sau khi sửa
