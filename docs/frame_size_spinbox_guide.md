# Hướng dẫn thêm SpinBox điều chỉnh kích thước Frame Camera

## Mô tả
Tính năng này cho phép người dùng điều chỉnh kích thước frame camera theo thời gian thực thông qua hai spinbox:
- `widthCameraFrameSpinBox`: Điều chỉnh chiều rộng (64-1456 pixels)
- `heightCameraFrameSpinBox`: Điều chỉnh chiều cao (64-1088 pixels)

## Cách thêm SpinBox vào UI

### 1. Mở Qt Designer và file mainUI.ui

### 2. Thêm hai QSpinBox widgets với tên sau:
- **widthCameraFrameSpinBox**: QSpinBox cho chiều rộng
- **heightCameraFrameSpinBox**: QSpinBox cho chiều cao

### 3. Cấu hình properties cho mỗi SpinBox:

#### widthCameraFrameSpinBox:
```
objectName: widthCameraFrameSpinBox
minimum: 64
maximum: 1456
value: 1456
suffix: " px"
```

#### heightCameraFrameSpinBox:
```
objectName: heightCameraFrameSpinBox
minimum: 64
maximum: 1088
value: 1088
suffix: " px"
```

### 4. Vị trí đề xuất
Đặt hai spinbox gần khu vực điều khiển camera, có thể trong một GroupBox có label "Frame Size" hoặc "Kích thước Frame".

## Tính năng đã được implement

### CameraStream (camera/camera_stream.py)
- ✅ `set_frame_size(width, height)`: Thay đổi kích thước frame cho cả live preview và still capture
- ✅ `get_frame_size()`: Lấy kích thước hiện tại
- ✅ Auto restart pipeline khi thay đổi kích thước
- ✅ Auto FPS adjustment: Tự động điều chỉnh FPS theo kích thước (60fps cho <0.5MP, 45fps cho 0.5-1MP, 30fps cho >1MP)
- ✅ Unified frame size: Live preview và still capture đều sử dụng cùng kích thước

### CameraManager (gui/camera_manager.py)
- ✅ `setup_frame_size_spinboxes()`: Thiết lập spinboxes
- ✅ `on_frame_size_changed()`: Xử lý khi giá trị thay đổi
- ✅ `set_frame_size()` và `get_frame_size()`: Interface điều khiển

### MainWindow (gui/main_window_new.py)
- ✅ Tìm spinbox widgets tự động
- ✅ Setup connection với CameraManager
- ✅ Import QSpinBox đã được thêm

## Cách sử dụng sau khi thêm UI

1. **Tự động**: Khi người dùng thay đổi giá trị trong spinbox, kích thước frame sẽ thay đổi ngay lập tức
2. **Programmatic**: 
   ```python
   # Đặt kích thước
   camera_manager.set_frame_size(1280, 720)
   
   # Lấy kích thước hiện tại
   width, height = camera_manager.get_frame_size()
   ```

## Giới hạn kỹ thuật
- **Chiều rộng**: 64-1456 pixels (giới hạn bởi sensor IMX296)
- **Chiều cao**: 64-1088 pixels (giới hạn bởi sensor IMX296)
- **Auto FPS**: Tự động điều chỉnh theo kích thước:
  - <0.5MP (320x240): 60 FPS
  - 0.5-1MP (720x576): 45 FPS  
  - >1MP (1456x1088): 30 FPS
- **Unified size**: Live preview và still capture sử dụng cùng kích thước
- **Auto restart**: Pipeline camera sẽ restart tự động khi thay đổi kích thước

## Lưu ý
- Kích thước mặc định là 1456x1088 (full resolution)
- **Live preview và still capture**: Đều sử dụng cùng kích thước frame
- **Auto FPS optimization**: Hệ thống tự động điều chỉnh FPS để duy trì hiệu suất mượt mà
- **Smart restart**: Việc thay đổi kích thước sẽ làm tạm dừng camera một chút để restart pipeline
- **Performance**: Với kích thước lớn (1456x1088), FPS sẽ giảm xuống 30fps để đảm bảo ổn định
