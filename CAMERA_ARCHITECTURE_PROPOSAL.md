# Đề xuất cải thiện kiến trúc Camera System

## Vấn đề hiện tại:
1. **Xung đột quyền điều khiển**: CameraManager và CameraTool đều có thể ảnh hưởng đến camera
2. **Flow phức tạp**: Nhiều đường dẫn khác nhau có thể bật/tắt camera
3. **State không đồng bộ**: UI state và camera state có thể không khớp

## Kiến trúc được đề xuất:

### Nguyên tắc "Single Source of Truth":
- **CameraManager**: Là controller duy nhất của camera hardware
- **CameraTool**: Chỉ là data holder, không điều khiển camera trực tiếp
- **CameraStream**: Hardware abstraction layer

### Flow được đơn giản hóa:

```
1. User adds Camera Source tool
   └── CameraTool created (config only)
   └── CameraTool.camera_manager = MainWindow.camera_manager
   └── UI enabled, but camera NOT auto-started

2. User clicks "Start Camera"
   └── CameraManager.start_live_camera()
   └── CameraStream.start_live()
   └── Camera starts in current mode

3. User changes camera mode
   └── CameraManager.on_live_camera_mode_clicked()
   └── Camera stopped → mode changed → camera restarted if was running
```

### Thay đổi cần thiết:

#### 1. CameraTool (tools/camera_tool.py):
- Loại bỏ tất cả direct camera control
- Chỉ lưu trữ configuration
- Tham chiếu đến CameraManager để apply config

#### 2. CameraManager (gui/camera_manager.py):
- Trở thành single controller của camera
- Handle tất cả camera operations
- Sync config từ CameraTool khi cần

#### 3. ToolManager (gui/tool_manager.py):
- Không gọi camera operations trực tiếp
- Chỉ enable UI controls khi add Camera Source

#### 4. MainWindow (gui/main_window.py):
- Đảm bảo CameraTool.camera_manager reference được set đúng

## Lợi ích:
1. **Đơn giản hóa**: Chỉ có một nơi điều khiển camera
2. **Tránh xung đột**: Không có multiple controllers
3. **Dễ debug**: Clear flow và responsibility
4. **UI consistency**: UI state luôn reflect camera state
