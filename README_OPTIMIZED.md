# Smart Eye Detection (SED) - Optimized Architecture

## Tổng quan về các tối ưu hóa

Dự án đã được tối ưu hóa với các cải tiến chính sau:

### 1. **Kiến trúc code được cải thiện**
- ✅ Tách biệt rõ ràng các thành phần (Manager pattern)
- ✅ Code dễ bảo trì và mở rộng
- ✅ Xử lý lỗi tốt hơn
- ✅ Logging chi tiết cho debugging

### 2. **Detection Tools được hiện thực đầy đủ**

#### EdgeDetectionTool
- Sử dụng Canny edge detection với cấu hình linh hoạt
- Hỗ trợ preprocessing (Gaussian blur)
- Cung cấp thống kê chi tiết (edge density, contour count)
- Validator cho các tham số đầu vào

#### OcrTool  
- Hỗ trợ cả EasyOCR và Tesseract
- Preprocessing tự động để cải thiện độ chính xác
- Threshold confidence configurable
- Output format linh hoạt (text only, boxes, both)

### 3. **Camera Stream được tối ưu với Picamera2 Pipeline**
- **Pipeline Architecture**: Sử dụng pipeline native của Picamera2
- **Multi-Stream Support**: Preview, Still, và RAW capture streams
- **Real-time Controls**: Dynamic exposure, gain, white balance control
- **Performance Optimized**: 
  - Preview stream tối ưu cho real-time display (640x480)
  - Still capture chất lượng cao (1456x1088 native)
  - RAW stream cho advanced processing
- **Advanced Features**:
  - Auto/Manual exposure modes
  - White balance presets
  - Focus control (nếu camera hỗ trợ)
  - Metadata extraction (exposure time, gain, lux, etc.)
  - Callback-based processing
- **Robust Error Handling**: Graceful degradation và detailed logging

### 4. **Job Management hoàn chỉnh**
- Save/Load jobs từ JSON files
- Tool configuration management
- Job execution với error handling
- Performance metrics tracking

### 5. **UI/UX Improvements**
- Settings manager cho tool configuration
- Proper signal/slot connections
- Better error dialogs
- Configurable startup options

## Cách sử dụng

### Test Camera Pipeline trước khi chạy app
```bash
# Test tất cả tính năng camera
python test_camera_pipeline.py
```

### Khởi chạy đơn giản
```bash
python run.py
```

### Khởi chạy với tùy chọn
```bash
# Sử dụng kiến trúc mới (mặc định)
python run.py --arch new

# Sử dụng kiến trúc cũ
python run.py --arch old

# Debug mode
python run.py --debug

# Test mode (không cần camera)
python run.py --no-camera

# Cài đặt dependencies
python run.py --install-deps
```

### Khởi chạy trực tiếp
```bash
# Kiến trúc mới
python main.py --architecture new

# Kiến trúc cũ  
python main.py --architecture old

# Debug mode
python main.py --debug
```

## Cấu trúc file được tối ưu

```
sed/
├── main.py                 # Entry point tối ưu với argument parsing
├── run.py                  # Convenience script 
├── requirements.txt        # Dependencies chi tiết
├── camera/
│   └── camera_stream.py    # Tối ưu với fallback support
├── detection/
│   ├── edge_detection.py   # EdgeDetectionTool hoàn chỉnh
│   └── ocr_tool.py        # OcrTool với multi-engine support
├── gui/
│   ├── main_window_new.py  # Kiến trúc mới (recommended)
│   ├── main_window.py      # Kiến trúc cũ (backward compatibility)
│   ├── tool_manager.py     # Tool management logic
│   ├── settings_manager.py # Settings UI management
│   └── camera_manager.py   # Camera control logic
└── job/
    └── job_manager.py      # Job execution và serialization
```

## Tính năng nâng cao của Picamera2 Pipeline

### 1. **Multi-Stream Architecture**
```python
# Preview stream (real-time)
preview_config = {
    "main": {"size": (640, 480), "format": "RGB888"},
    "lores": {"size": (320, 240), "format": "YUV420"}  # For processing
}

# Still capture (high quality)  
still_config = {
    "main": {"size": (1456, 1088), "format": "RGB888"}
}

# RAW capture (for advanced processing)
raw_config = {
    "main": {"size": (1456, 1088), "format": "RGB888"},
    "raw": {"size": sensor_resolution, "format": sensor_format}
}
```

### 2. **Real-time Camera Controls**
```python
# Exposure control (in milliseconds)
camera.set_exposure(20)  # 20ms exposure

# Gain control
camera.set_gain(2.0)  # 2x analog gain

# Auto exposure
camera.set_auto_exposure(True)

# White balance presets
camera.set_white_balance("daylight")  # auto, daylight, cloudy, tungsten, etc.

# Focus control (if supported)
camera.set_focus(0.5)  # Manual focus at 50%
camera.set_focus()     # Auto focus
```

### 3. **Advanced Capture Modes**
```python
# Still capture với chất lượng cao
camera.trigger_capture("still")

# RAW capture cho advanced processing
camera.trigger_capture("raw")

# Callback-based processing
def process_frame(frame, metadata):
    # Your processing here
    return processed_frame

camera.capture_with_callback(process_frame)
```

### 4. **Metadata Extraction**
```python
# Lấy thông tin chi tiết từ camera
metadata = camera.get_camera_metadata()
print(f"Exposure: {metadata['ExposureTime']}us")
print(f"Gain: {metadata['AnalogueGain']}")
print(f"Color Temp: {metadata['ColourTemperature']}K")
print(f"Lux: {metadata['Lux']}")
```

## Dependencies

### Core (Required)
- PyQt5 >= 5.15.0
- numpy >= 1.21.0  
- opencv-python >= 4.5.0

### Camera (Raspberry Pi)
- picamera2 >= 0.3.0

### OCR (Optional)
- easyocr >= 1.6.0 (recommended)
- pytesseract >= 3.8.0 (alternative)

### Object Detection
- ultralytics >= 8.0.0

## Troubleshooting

### Camera không hoạt động
- Kiểm tra kết nối camera
- Chạy với `--no-camera` để test UI
- Kiểm tra log files

### OCR không hoạt động  
- Cài đặt easyocr: `pip install easyocr`
- Hoặc cài đặt tesseract: `pip install pytesseract`

### Performance issues
- Giảm resolution trong camera settings
- Tắt preprocessing trong OCR settings
- Monitor với `--debug` flag

## Development

### Thêm Tool mới
1. Inherit từ `Tool` class trong `job_manager.py`
2. Implement `process()` method
3. Đăng ký trong `JobManager.register_default_tools()`
4. Thêm UI settings nếu cần

### Kiểm tra code quality
```bash
# Chạy tests (nếu có)
python -m pytest

# Check formatting
python -m black . --check

# Linting
python -m flake8 .
```

## License

Tham khảo file LICENSE.txt cho thông tin license.
