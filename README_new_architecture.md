# Hướng dẫn sử dụng kiến trúc mới

## Tổng quan

Kiến trúc mới của ứng dụng tách biệt rõ ràng các thành phần để cải thiện khả năng bảo trì và mở rộng. Các thành phần chính bao gồm:

1. **ToolManager** - quản lý các công cụ và tương tác giữa công cụ và giao diện người dùng
2. **SettingsManager** - quản lý việc hiển thị và điều khiển các trang cài đặt
3. **CameraManager** - quản lý camera và các tương tác liên quan đến camera

## Cách sử dụng

Bạn có thể chọn sử dụng kiến trúc cũ hoặc mới:

### Sử dụng kiến trúc cũ:
```python
python main.py
```

### Sử dụng kiến trúc mới:
1. Mở file `main_new.py`
2. Uncomment dòng `from gui.main_window_new import MainWindow`
3. Comment dòng `from gui.main_window import MainWindow`
4. Chạy:
```python
python main_new.py
```

## Cấu trúc thư mục

```
sed/
├── main.py               # Entry point sử dụng kiến trúc cũ
├── main_new.py           # Entry point sử dụng kiến trúc mới
├── mainUI.ui             # File giao diện Qt
├── gui/
│   ├── __init__.py           # Package initialization
│   ├── main_window.py        # Main window (kiến trúc cũ)
│   ├── main_window_new.py    # Main window (kiến trúc mới)
│   ├── camera_view.py        # Camera view
│   ├── tool_manager.py       # Quản lý công cụ
│   ├── settings_manager.py   # Quản lý cài đặt
│   └── camera_manager.py     # Quản lý camera
├── camera/
│   ├── __init__.py
│   └── camera_stream.py      # Xử lý luồng camera
├── detection/
│   ├── __init__.py
│   ├── edge_detection.py     # Phát hiện cạnh
│   └── ocr_tool.py           # Công cụ OCR
└── job/
    ├── __init__.py
    └── job_manager.py        # Quản lý job
```

## Lợi ích của kiến trúc mới

1. **Mô-đun hóa**: Mỗi thành phần được tách biệt rõ ràng thành các module riêng biệt
2. **Dễ bảo trì**: Việc sửa chữa và cập nhật từng phần được thực hiện độc lập
3. **Mở rộng dễ dàng**: Thêm tính năng mới không yêu cầu sửa đổi toàn bộ ứng dụng
4. **Dễ kiểm thử**: Mỗi thành phần có thể được kiểm thử riêng biệt
5. **Tính linh hoạt**: Các thành phần có thể được sử dụng lại trong các dự án khác
