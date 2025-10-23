# 💡 TCP Light Controller Integration Guide

## 📋 File Created
- **File:** `controller/tcp_light_controller.py`
- **Class:** `TCPLightController` (QObject)
- **Purpose:** Handle TCP communication with light hardware (LED, lamp, etc.)

---

## 🎯 Features

### 1. **Connection Management**
```python
controller = TCPLightController()
controller.connect("192.168.1.100", "5000")  # Connect to light device
```

### 2. **Light Control Commands**
```python
controller.turn_on()           # Bật đèn
controller.turn_off()          # Tắt đèn
controller.toggle()            # Chuyển đổi trạng thái
controller.set_brightness(75)  # Điều chỉnh độ sáng 0-100%
```

### 3. **Custom Messages**
```python
controller.send_message('on')               # Gửi lệnh 'on'
controller.send_message('brightness:50')   # Gửi lệnh độ sáng
```

### 4. **Status Tracking**
```python
controller.is_connected        # Kiểm tra kết nối
controller.light_status        # Trạng thái: 'on', 'off', 'error', 'unknown'
controller.current_ip          # IP hiện tại
controller.current_port        # Port hiện tại
```

### 5. **Signals (Qt Signals)**
```python
controller.connection_status_changed.connect(on_connection_changed)
controller.message_received.connect(on_message_received)
controller.light_status_changed.connect(on_light_status_changed)
```

---

## 🔧 Integration with GUI (mainUI)

### Step 1: Initialize in `tcp_controller_manager.py`

```python
from controller.tcp_light_controller import TCPLightController

class TCPControllerManager(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        
        # Existing TCP controller for camera
        self.tcp_controller = TCPController()
        
        # ✨ NEW: Light controller
        self.light_controller = TCPLightController()
        
        # Setup light controller signals
        self._setup_light_controller_signals()
        
    def _setup_light_controller_signals(self):
        """Setup signals for light controller tab"""
        # Connection status
        self.light_controller.connection_status_changed.connect(
            self._on_light_connection_changed
        )
        
        # Message received
        self.light_controller.message_received.connect(
            self._on_light_message_received
        )
        
        # Light status changed
        self.light_controller.light_status_changed.connect(
            self._on_light_status_changed
        )
        
    @pyqtSlot(bool, str)
    def _on_light_connection_changed(self, connected: bool, status: str):
        """Update light controller connection status in UI"""
        self.main_window.statusLabelLightController.setText(
            f"✓ {status}" if connected else f"✗ {status}"
        )
        self.main_window.statusLabelLightController.setStyleSheet(
            "color: green;" if connected else "color: red;"
        )
        
    @pyqtSlot(str)
    def _on_light_message_received(self, message: str):
        """Add received message to light controller message list"""
        self.main_window.msgListWidgetLightController.addItem(
            f"← {message}"  # Arrow indicates incoming
        )
        # Auto-scroll to bottom
        self.main_window.msgListWidgetLightController.scrollToBottom()
        
    @pyqtSlot(str)
    def _on_light_status_changed(self, status: str):
        """Update light status indicator"""
        logging.info(f"💡 Light status changed: {status}")
        # You can update an indicator or perform actions based on status
```

### Step 2: Connect UI Buttons and Input Fields

```python
class TCPControllerManager(QObject):
    def connect_light_ui_controls(self):
        """Connect light controller UI elements to slots"""
        
        # Connect button
        self.main_window.connectButtonLightController.clicked.connect(
            self._on_connect_light_controller
        )
        
        # Send button
        self.main_window.sendButtonLightController.clicked.connect(
            self._on_send_light_message
        )
        
    @pyqtSlot()
    def _on_connect_light_controller(self):
        """Handle light controller connect button"""
        ip = self.main_window.ipLineEditLightController.text().strip()
        port = self.main_window.portLineEditLightController.text().strip()
        
        if not ip or not port:
            QMessageBox.warning(self.main_window, "Error", "Please enter IP and port")
            return
        
        if self.light_controller.connect(ip, port):
            logging.info(f"💡 Connecting to light controller at {ip}:{port}")
        else:
            logging.error(f"💡 Failed to connect to {ip}:{port}")
            
    @pyqtSlot()
    def _on_send_light_message(self):
        """Handle light controller send button"""
        message = self.main_window.msgLineEditLightController.text().strip()
        
        if not message:
            logging.warning("💡 Cannot send empty message")
            return
        
        if self.light_controller.send_message(message):
            # Add to message list
            self.main_window.msgListWidgetLightController.addItem(
                f"→ {message}"  # Arrow indicates outgoing
            )
            self.main_window.msgListWidgetLightController.scrollToBottom()
            
            # Clear input
            self.main_window.msgLineEditLightController.clear()
        else:
            QMessageBox.warning(self.main_window, "Error", "Failed to send message")
```

### Step 3: Add Quick Light Control Buttons (Optional)

```python
@pyqtSlot()
def _on_light_on_clicked(self):
    """Quick button to turn light on"""
    if self.light_controller.turn_on():
        logging.info("💡 Light ON command sent")
        
@pyqtSlot()
def _on_light_off_clicked(self):
    """Quick button to turn light off"""
    if self.light_controller.turn_off():
        logging.info("💡 Light OFF command sent")
```

---

## 📱 Expected Protocol

The light controller expects messages in this format:

### Commands from Pi to Light Device
```
on\n              # Turn on
off\n             # Turn off
toggle\n          # Toggle state
brightness:50\n   # Set brightness to 50%
brightness:100\n  # Set brightness to 100%
```

### Responses from Light Device to Pi
```
status:on\n       # Light is on
status:off\n      # Light is off
brightness:75\n   # Current brightness is 75%
```

---

## 🔌 UI Components Required (mainUI.ui)

These components should already exist in your `lightControllerTab`:

| Component | Purpose |
|-----------|---------|
| `ipLineEditLightController` | Input for light device IP |
| `portLineEditLightController` | Input for light device port |
| `connectButtonLightController` | Button to connect |
| `statusLabelLightController` | Label showing connection status |
| `msgListWidgetLightController` | List for message history |
| `msgLineEditLightController` | Input for custom messages |
| `sendButtonLightController` | Button to send message |

---

## 🎨 Integration Example in TCP Controller Manager

```python
from controller.tcp_light_controller import TCPLightController

class TCPControllerManager(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.tcp_controller = TCPController()
        self.light_controller = TCPLightController()  # ✨ NEW
        
        self._setup_signals()
        self._connect_ui_controls()
        
    def _setup_signals(self):
        """Setup both camera and light controller signals"""
        # ... existing TCP controller setup ...
        
        # ✨ NEW: Light controller setup
        self.light_controller.connection_status_changed.connect(
            self._on_light_connection_changed
        )
        self.light_controller.message_received.connect(
            self._on_light_message_received
        )
        self.light_controller.light_status_changed.connect(
            self._on_light_status_changed
        )
        
    def _connect_ui_controls(self):
        """Connect UI elements to slots"""
        # ... existing controls ...
        
        # ✨ NEW: Light controller UI
        self.main_window.connectButtonLightController.clicked.connect(
            self._on_connect_light_controller
        )
        self.main_window.sendButtonLightController.clicked.connect(
            self._on_send_light_message
        )
```

---

## 💡 Usage Scenarios

### Scenario 1: Manual Control
User fills IP/port → Clicks connect → Sends commands via text input

### Scenario 2: Auto Control (Trigger Integration)
- Light trigger is received → Light automatically turns on
- Camera captures frame → Light automatically turns off

### Scenario 3: Brightness Control
```python
# In trigger flow
self.light_controller.set_brightness(100)  # Full brightness
time.sleep(delay_ms / 1000.0)
camera.capture()
self.light_controller.set_brightness(0)    # Turn off (brightness 0)
```

---

## ⚙️ Methods Reference

### Connection Methods
- `connect(ip: str, port: str) -> bool` - Connect to device
- `is_connected -> bool` - Check if connected
- Property access: `current_ip`, `current_port`, `light_status`

### Light Control Methods
- `turn_on() -> bool` - Turn on light
- `turn_off() -> bool` - Turn off light
- `toggle() -> bool` - Toggle state
- `set_brightness(level: int) -> bool` - Set brightness 0-100

### Message Methods
- `send_message(message: str) -> bool` - Send custom command

### Signals
- `connection_status_changed(connected: bool, status: str)`
- `message_received(message: str)`
- `light_status_changed(status: str)`

---

## 🚀 Next Steps

1. ✅ **File Created:** `controller/tcp_light_controller.py`
2. **TODO:** Integrate into `tcp_controller_manager.py`
3. **TODO:** Connect UI elements from `lightControllerTab`
4. **TODO:** Test communication with light device
5. **TODO:** (Optional) Add light control to camera trigger workflow

---

## 📝 Notes

- Based on same architecture as `TCPController`
- Optimized for responsive light control
- All messages end with `\n` (newline) character
- Thread-safe communication with monitor thread
- Comprehensive logging with 💡 emoji indicators
