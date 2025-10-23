# TCP Controller Setup - Kiểm Tra và Sửa Chữa

## Vấn Đề Tìm Thấy

### 1. **Widget TCP không được khai báo trong mainUI.ui** ✓ KIỂM TRA
- ✓ `ipLineEdit` - Có (dòng 695)
- ✓ `portLineEdit` - Có (dòng 705)
- ✓ `statusLabel` - Có (dòng 656)
- ✓ `connectButton` - Có (dòng 630)
- ✓ `messageListWidget` - Có (dòng 685)
- ✓ `messageLineEdit` - Có (dòng 728)
- ✓ `sendButton` - Có (dòng 738)

**Kết luận**: Tất cả các widget TCP đã được khai báo trong mainUI.ui

### 2. **Vấn Đề Chính: TCP Controller không được setup()** ❌ → ✓ ĐÃ SỬA

**Vị trí vấn đề**: `gui/main_window.py` 

#### Trước đó:
- `_find_widgets()` tìm kiếm TCP widgets nhưng có logic phức tạp và lặp lại
- **`_setup_managers()` KHÔNG gọi `tcp_controller.setup()`** ← **ĐÂY LÀ VẤN ĐỀ CHÍNH**
- Setup chỉ được gọi trong `_find_widgets()` ở một số branch code

#### Sau khi sửa:
1. **Tạo phương thức mới**: `_setup_tcp_controller()` 
   - Kiểm tra tất cả widget TCP có được tìm thấy không
   - Gọi `tcp_controller.setup()` với đầy đủ 7 parameters
   - Log chi tiết về các widget tìm thấy

2. **Trong `_setup_managers()`**: Gọi `self._setup_tcp_controller()` ở cuối
   - Đảm bảo TCP controller được setup SAU khi `_find_widgets()` đã tìm xong tất cả widgets

3. **Dọn dẹp `_find_widgets()`**:
   - Loại bỏ code redundant/fallback
   - Loại bỏ code gọi setup() lặp lại
   - Giữ nguyên logic tìm widgets từ controllerTab

## Chi tiết Sửa Chữa

### File: `gui/main_window.py`

#### 1. Thêm phương thức `_setup_tcp_controller()`
```python
def _setup_tcp_controller(self):
    """Thiết lập TCP Controller Manager với các widgets đã tìm thấy"""
    try:
        # Kiểm tra xem tất cả các widget TCP có được tìm thấy không
        required_widgets = {
            'ipLineEdit': self.ipEdit,
            'portLineEdit': self.portEdit,
            'connectButton': self.connectButton,
            'statusLabel': self.statusLabel,
            'messageListWidget': self.messageList,
            'messageLineEdit': self.messageEdit,
            'sendButton': self.sendButton
        }
        
        # Log trạng thái của tất cả các widget
        for name, widget in required_widgets.items():
            found = widget is not None
            logging.info(f"TCP Widget '{name}': {'✓ Found' if found else '✗ Not Found'}")
            if widget:
                logging.info(f"  - Type: {type(widget).__name__}")
                logging.info(f"  - ObjectName: {widget.objectName()}")
                logging.info(f"  - Enabled: {widget.isEnabled()}")
                logging.info(f"  - Visible: {widget.isVisible()}")
        
        # Kiểm tra xem tất cả các widget bắt buộc có được tìm thấy không
        missing_widgets = [name for name, widget in required_widgets.items() if widget is None]
        
        if missing_widgets:
            logging.error(f"Missing TCP widgets: {', '.join(missing_widgets)}")
            logging.error("TCP Controller setup will be skipped!")
            return False
        
        # Thiết lập TCP Controller
        logging.info("Setting up TCP Controller with all required widgets...")
        self.tcp_controller.setup(
            self.ipEdit,
            self.portEdit,
            self.connectButton,
            self.statusLabel,
            self.messageList,
            self.messageEdit,
            self.sendButton
        )
        logging.info("✓ TCP Controller setup completed successfully")
        return True
        
    except Exception as e:
        logging.error(f"Error setting up TCP Controller: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return False
```

#### 2. Trong `_setup_managers()`, thêm:
```python
# Setup TCP Controller Manager
self._setup_tcp_controller()
```

#### 3. Dọn dẹp `_find_widgets()`:
- Loại bỏ code fallback rời rạc
- Loại bỏ lần gọi setup() đầu tiên (sẽ được gọi lại trong `_setup_tcp_controller()`)
- Giữ nguyên code tìm TCP widgets từ controllerTab

## Quy Trình Khởi Tạo (Sau Khi Sửa)

```
MainWindow.__init__()
    ↓
Khởi tạo TCPControllerManager
    ↓
Load UI từ mainUI.ui (uic.loadUi)
    ↓
_find_widgets()
    └─ Tìm TCP widgets từ controllerTab trong paletteTab
       ├─ self.ipEdit
       ├─ self.portEdit
       ├─ self.connectButton
       ├─ self.statusLabel
       ├─ self.messageList
       ├─ self.messageEdit
       └─ self.sendButton
    ↓
_setup_managers()
    ├─ Setup CameraManager, ToolManager, SettingsManager, ...
    └─ _setup_tcp_controller()  ← ĐÂY!
       └─ tcp_controller.setup(ip_edit, port_edit, connect_button, ...)
          ├─ Lưu trữ widgets
          └─ Kết nối signals (connectButton.clicked → _on_connect_click)
    ↓
_connect_signals()
    ↓
GUI sẵn sàng
```

## Các Thành Phần Liên Quan

### 1. **TCPControllerManager** (`gui/tcp_controller_manager.py`)
- `setup()` - Khởi tạo và kết nối signals
- `_on_connect_click()` - Xử lý nút Connect/Disconnect
- `_on_send_click()` - Xử lý nút Send

### 2. **TCPController** (`controller/tcp_controller.py`)
- `connect(ip, port)` - Kết nối TCP
- `send_message(message)` - Gửi tin nhắn
- `_monitor_socket()` - Thread theo dõi socket
- Signals:
  - `connection_status_changed` - Phát ra khi trạng thái kết nối thay đổi
  - `message_received` - Phát ra khi nhận tin nhắn

## Kiểm Tra Sau Khi Sửa

1. **Chạy chương trình**:
   ```bash
   python run.py
   ```

2. **Trong console, kiểm tra xem có log như sau**:
   ```
   TCP Widget 'ipLineEdit': ✓ Found
   TCP Widget 'portLineEdit': ✓ Found
   TCP Widget 'connectButton': ✓ Found
   TCP Widget 'statusLabel': ✓ Found
   TCP Widget 'messageListWidget': ✓ Found
   TCP Widget 'messageLineEdit': ✓ Found
   TCP Widget 'sendButton': ✓ Found
   Setting up TCP Controller with all required widgets...
   TCP controller signals connected
   ✓ TCP Controller setup completed successfully
   ```

3. **Trong GUI**:
   - Nhập IP (ví dụ: 192.168.1.100)
   - Nhập Port (ví dụ: 5000)
   - Nhấn nút "Connect"
   - Status label sẽ đổi màu đỏ hoặc xanh tuỳ theo kết nối thành công hay không

## Kết Luận

Vấn đề chính là **TCP Controller không được setup() gọi trong `_setup_managers()`**. Sau khi sửa, quy trình khởi tạo sẽ:
1. Tìm tất cả TCP widgets ✓
2. **Gọi setup() để kết nối signals** ✓
3. Khi nút được nhấn, sự kiện sẽ được xử lý chính xác ✓
