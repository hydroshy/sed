# Tối ưu hóa Logging - Chỉ hiển thị DEBUG khi --debug

## Tóm tắt thay đổi

Đã tối ưu hóa logging system để:
- **Khi chạy bình thường**: Tất cả logs được ghi vào file `sed_app.log`, terminal sạch (không console output)
- **Khi chạy với `--debug`**: Chỉ hiển thị DEBUG messages lên terminal, định dạng ngắn gọn `DEBUG: [message]`

## Cách sử dụng

### Chạy bình thường (không debug)
```bash
python main.py
```
- Terminal sạch sẽ (không có output ngoài errors)
- Tất cả logs được ghi vào `sed_app.log`

### Chạy với debug mode
```bash
python main.py --debug
```
- Chỉ DEBUG messages hiển thị lên terminal
- Format: `DEBUG: [module] [message]`
- Tất cả logs vẫn được ghi vào `sed_app.log` (đầy đủ với timestamps)

## Cấu trúc logging

### Terminal (Console Output)
- **Debug mode OFF**: Không có output
- **Debug mode ON**: Chỉ DEBUG level messages
  - Format: `DEBUG: %(message)s`
  - Giúp theo dõi chi tiết khi phát triển/debug

### File Logging (`sed_app.log`)
- **Luôn ON**: Tất cả levels (DEBUG, INFO, WARNING, ERROR)
- **Format**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- **Giữ toàn bộ lịch sử** cho debugging/troubleshooting sau này

## Các file bị thay đổi

1. **main.py**
   - Thêm custom handler `DebugOnlyStreamHandler`
   - Cấu hình logging để chỉ DEBUG messages lên console khi `--debug`
   - File logging luôn bật

2. **camera_view.py**
   - Xóa basicConfig (để main.py quản lý)
   - Sử dụng module logger cho logging

3. **main_window.py**
   - Xóa basicConfig (để main.py quản lý)
   - Sử dụng module logger cho logging

4. **camera_stream.py**
   - Giữ nguyên (đã sử dụng module logger)

## Lợi ích

✅ **Terminal sạch**: Không bị lộn xộn khi chạy bình thường
✅ **Debug dễ**: Khi cần debug (`--debug`), xem được chi tiết
✅ **Log đầy đủ**: File log luôn có tất cả thông tin
✅ **Dễ bảo trì**: Tất cả logging cấu hình tập trung ở main.py

## Ví dụ output

### Chạy bình thường
```
$ python main.py
(Không có output - terminal sạch)
```

### Chạy với --debug
```
$ python main.py --debug
DEBUG: Debug logging enabled - only DEBUG messages will show in terminal
DEBUG: [CameraManager] _on_frame_from_camera called during TRIGGER CAPTURE...
DEBUG: [CameraView] No processed frame available for detection_detect_tool...
DEBUG: [_process_frame_to_qimage] Processing with format: RGB888...
DEBUG: [TCPController] Sensor IN received: 17363496
...
```

File `sed_app.log` sẽ có:
```
2025-12-19 15:31:44,855 - root - INFO - [CameraManager] No waiting frame - buffering result for later
2025-12-19 15:31:44,855 - gui.result_tab_manager - INFO - [ResultTabManager] Saved pending job result...
DEBUG: [CameraManager] Buffering result (TCP signal not received yet)
...
```
