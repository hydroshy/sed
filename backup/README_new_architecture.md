# Hướng dẫn sử dụng SED Application

## Tổng quan

Ứng dụng SED hiện đã được chuyển đổi hoàn toàn sang kiến trúc mới với các thành phần được tách biệt rõ ràng để cải thiện khả năng bảo trì và mở rộng. Các thành phần chính bao gồm:

1. **ToolManager** - quản lý các công cụ và tương tác giữa công cụ và giao diện người dùng
2. **SettingsManager** - quản lý việc hiển thị và điều khiển các trang cài đặt
3. **CameraManager** - quản lý camera và các tương tác liên quan đến camera

## Cách sử dụng

### Khởi chạy ứng dụng:
```python
python main.py
# hoặc
python run.py
```

## Cấu trúc thư mục

```
sed/
├── main.py               # Entry point chính
├── run.py                # Convenience script 
├── mainUI.ui             # File giao diện Qt
├── gui/
│   ├── __init__.py           # Package initialization
│   ├── main_window.py        # Main window (kiến trúc mới)
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

## Lợi ích của kiến trúc hiện tại

1. **Mô-đun hóa**: Mỗi thành phần được tách biệt rõ ràng thành các module riêng biệt
2. **Dễ bảo trì**: Việc sửa chữa và cập nhật từng phần được thực hiện độc lập
3. **Mở rộng dễ dàng**: Thêm tính năng mới không yêu cầu sửa đổi toàn bộ ứng dụng
4. **Dễ kiểm thử**: Mỗi thành phần có thể được kiểm thử riêng biệt
5. **Tính linh hoạt**: Các thành phần có thể được sử dụng lại trong các dự án khác
