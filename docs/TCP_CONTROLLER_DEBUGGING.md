# Hướng Dẫn Kiểm Tra TCP Controller Setup

## 📋 Danh Sách Kiểm Tra

### ✅ 1. Widgets Được Khai Báo Đúng

Tất cả 7 widget TCP đã được khai báo trong `mainUI.ui`:

| Widget | Type | ObjectName | UI Line | Status |
|--------|------|-----------|---------|--------|
| IP Input | QLineEdit | ipLineEdit | 695 | ✓ |
| Port Input | QLineEdit | portLineEdit | 705 | ✓ |
| Status Label | QLabel | statusLabel | 656 | ✓ |
| Connect Button | QPushButton | connectButton | 630 | ✓ |
| Message List | QListWidget | messageListWidget | 685 | ✓ |
| Message Input | QLineEdit | messageLineEdit | 728 | ✓ |
| Send Button | QPushButton | sendButton | 738 | ✓ |

### ✅ 2. Thứ Tự Khởi Tạo Đúng

```
MainWindow.__init__()
  ↓
  • Khởi tạo TCPControllerManager
  ↓
  • Load UI (mainUI.ui)
  ↓
  • _find_widgets() - TÌM WIDGETS
  ↓
  • _setup_managers()
      └─ _setup_tcp_controller() - SETUP SIGNALS ← **QUAN TRỌNG**
  ↓
  • GUI sẵn sàng
```

### ✅ 3. Code đã Được Sửa

#### A. Tạo phương thức `_setup_tcp_controller()` ✓

**Location**: `gui/main_window.py` - Dòng ~454

```python
def _setup_tcp_controller(self):
    """Thiết lập TCP Controller Manager với các widgets đã tìm thấy"""
    # Kiểm tra tất cả widget
    # Gọi tcp_controller.setup()
    # Log chi tiết
```

#### B. Gọi trong `_setup_managers()` ✓

**Location**: `gui/main_window.py` - Cuối của `_setup_managers()`

```python
def _setup_managers(self):
    # ... setup khác ...
    
    # Setup TCP Controller Manager
    self._setup_tcp_controller()  # ← THÊM DÒNG NÀY
```

#### C. Dọn dẹp `_find_widgets()` ✓

- Loại bỏ code fallback rời rạc
- Loại bỏ lần gọi setup() đầu tiên (sẽ được gọi lại)
- Giữ logic tìm widgets từ controllerTab

## 🔍 Cách Debug Nếu Vẫn Có Lỗi

### Bước 1: Kiểm tra Console Output

Chạy chương trình và xem console. Bạn sẽ thấy:

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

**Nếu thấy**:
- `✗ Not Found` → Widget không được tìm thấy
- `Setting up TCP Controller with all required widgets...` không xuất hiện → Setup chưa được gọi

### Bước 2: Kiểm Tra Widget Existence

Thêm code debug này vào `_setup_tcp_controller()`:

```python
logging.info(f"ipEdit: {self.ipEdit}")
logging.info(f"portEdit: {self.portEdit}")
logging.info(f"connectButton: {self.connectButton}")
logging.info(f"statusLabel: {self.statusLabel}")
logging.info(f"messageList: {self.messageList}")
logging.info(f"messageEdit: {self.messageEdit}")
logging.info(f"sendButton: {self.sendButton}")
```

### Bước 3: Kiểm Tra Signal Connections

Nếu nút vẫn không hoạt động, kiểm tra xem signal có được kết nối không:

```python
# Thêm vào _setup_tcp_controller()
if self.connectButton:
    connections = self.connectButton.receivers(self.connectButton.clicked)
    logging.info(f"connectButton receivers: {connections}")
```

Nếu `connections = 0`, signal chưa được kết nối.

### Bước 4: Kiểm Tra TCPControllerManager.setup()

Thêm debug code vào `tcp_controller_manager.py`:

```python
def setup(self, ...):
    logging.info("=== TCPControllerManager.setup() called ===")
    logging.info(f"ip_edit: {ip_edit}")
    logging.info(f"port_edit: {port_edit}")
    # ... etc
    
    # Kết nối signals
    logging.info("Connecting signals...")
    self.connect_button.clicked.connect(self._on_connect_click)
    logging.info(f"Signal connected, receivers: {self.connect_button.receivers(self.connect_button.clicked)}")
```

## 🧪 Test Script

Chạy test script để kiểm tra:

```bash
cd e:\PROJECT\sed
python tests/test_tcp_setup.py
```

## 📌 Các Điểm Chính

1. **TCP widgets PHẢI được tìm thấy từ controllerTab**
   - Không tìm kiếm cấp cao nhất (findChild trong MainWindow)
   - controllerTab là parent của tất cả TCP widgets

2. **setup() PHẢI được gọi trong _setup_managers()**
   - Được gọi SAU khi _find_widgets() tìm xong
   - Gọi TRƯỚC khi _connect_signals()

3. **Signals PHẢI được kết nối**
   - connectButton.clicked → _on_connect_click
   - sendButton.clicked → _on_send_click
   - tcp_controller.connection_status_changed → _on_connection_status

## 🎯 Sự Kiện Khi Nhấn Nút

### Khi nhấn "Connect":
1. `connectButton.clicked` → signal phát
2. `_on_connect_click()` được gọi
3. Kiểm tra IP/Port nhập vào
4. Gọi `tcp_controller.connect(ip, port)`
5. `connection_status_changed` signal phát
6. `_on_connection_status()` cập nhật UI

### Khi nhấn "Send":
1. `sendButton.clicked` → signal phát
2. `_on_send_click()` được gọi
3. Lấy tin nhắn từ `messageEdit`
4. Gọi `tcp_controller.send_message(message)`
5. Thêm tin nhắn vào `messageList`

## ❓ Câu Hỏi Thường Gặp

**Q: Nút connectButton vẫn không hoạt động?**
A: Kiểm tra:
- Console có log `✓ TCP Controller setup completed successfully` không?
- Có bao nhiêu receivers trong connectButton?
- Widgets có được tìm thấy không?

**Q: Không nhận được tin nhắn từ thiết bị?**
A: Kiểm tra:
- TCP connection có thành công không? (Status label xanh?)
- Thiết bị có hoạt động và lắng nghe TCP không?
- Port có đúng không?

**Q: Status label hiển thị "Error" hoặc không thay đổi?**
A: Kiểm tra:
- Kết nối TCP signal `connection_status_changed` có hoạt động không?
- `_on_connection_status()` có được gọi không?
- Có log error nào trong console không?

## 📞 Liên Hệ Hỗ Trợ

Nếu vẫn có vấn đề, kiểm tra:
1. Chạy `python tests/test_tcp_setup.py` để xác nhận widgets
2. Xem console output để tìm line lỗi
3. Kiểm tra `TCP_CONTROLLER_FIX_SUMMARY.md` để hiểu thêm
