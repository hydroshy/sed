# 💡 Light Controller Integration Steps

## 🎯 Step 1: Import Light Controller

Add to top of `gui/tcp_controller_manager.py`:

```python
from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QLineEdit, QListWidget, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from controller.tcp_controller import TCPController
from controller.tcp_light_controller import TCPLightController  # ✨ ADD THIS
from gui.tcp_optimized_trigger import OptimizedTCPControllerManager
import logging
import time
```

---

## 🎯 Step 2: Initialize Light Controller in `__init__`

```python
class TCPControllerManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.tcp_controller = TCPController()
        
        # ✨ NEW: Light controller
        self.light_controller = TCPLightController()
        
        # ✅ OPTIMIZATION: Initialize optimized trigger handler
        self.optimized_manager = None
        
        # UI components - Camera Controller
        self.ip_edit: QLineEdit = None
        self.port_edit: QLineEdit = None
        self.connect_button: QPushButton = None
        self.status_label: QLabel = None
        self.message_list: QListWidget = None
        self.message_edit: QLineEdit = None
        self.send_button: QPushButton = None
        
        # ✨ NEW: UI components - Light Controller
        self.light_ip_edit: QLineEdit = None
        self.light_port_edit: QLineEdit = None
        self.light_connect_button: QPushButton = None
        self.light_status_label: QLabel = None
        self.light_message_list: QListWidget = None
        self.light_message_edit: QLineEdit = None
        self.light_send_button: QPushButton = None
```

---

## 🎯 Step 3: Create Setup Method for Light Controller

Add new method to `TCPControllerManager` class:

```python
def setup_light_controller(self, 
                          ip_edit: QLineEdit, 
                          port_edit: QLineEdit,
                          connect_button: QPushButton, 
                          status_label: QLabel,
                          message_list: QListWidget, 
                          message_edit: QLineEdit,
                          send_button: QPushButton):
    """Setup light controller UI components"""
    try:
        # Store UI components
        self.light_ip_edit = ip_edit
        self.light_port_edit = port_edit
        self.light_connect_button = connect_button
        self.light_status_label = status_label
        self.light_message_list = message_list
        self.light_message_edit = message_edit
        self.light_send_button = send_button
        
        # Set initial states
        self.light_status_label.setText("Disconnected")
        self.light_status_label.setStyleSheet("color: red")
        self._update_light_button_states(False)
        
        # Connect signals
        self.light_controller.connection_status_changed.connect(
            self._on_light_connection_status_changed
        )
        self.light_controller.message_received.connect(
            self._on_light_message_received
        )
        self.light_controller.light_status_changed.connect(
            self._on_light_status_changed
        )
        
        # Connect buttons
        self.light_connect_button.clicked.connect(
            self._on_light_connect_button_clicked
        )
        self.light_send_button.clicked.connect(
            self._on_light_send_button_clicked
        )
        
        # Allow pressing Enter in message edit to send
        self.light_message_edit.returnPressed.connect(
            self._on_light_send_button_clicked
        )
        
        logging.info("💡 Light controller UI setup completed")
        
    except Exception as e:
        logging.error(f"💡 Error setting up light controller UI: {e}")
```

---

## 🎯 Step 4: Add Signal Handlers for Light Controller

Add these methods to `TCPControllerManager` class:

```python
def _on_light_connection_status_changed(self, connected: bool, status: str):
    """Handle light controller connection status change"""
    try:
        if connected:
            self.light_status_label.setText(f"✓ {status}")
            self.light_status_label.setStyleSheet("color: green")
            self._update_light_button_states(True)
            logging.info(f"💡 Light controller connected: {status}")
        else:
            self.light_status_label.setText(f"✗ {status}")
            self.light_status_label.setStyleSheet("color: red")
            self._update_light_button_states(False)
            logging.info(f"💡 Light controller disconnected: {status}")
    except Exception as e:
        logging.error(f"💡 Error updating connection status: {e}")

def _on_light_message_received(self, message: str):
    """Handle message received from light controller"""
    try:
        if message:
            # Add to message list with incoming indicator
            self.light_message_list.addItem(f"← {message}")
            # Auto-scroll to bottom
            self.light_message_list.scrollToBottom()
            logging.debug(f"💡 Message from light controller: {message}")
    except Exception as e:
        logging.error(f"💡 Error handling received message: {e}")

def _on_light_status_changed(self, status: str):
    """Handle light status change"""
    try:
        logging.info(f"💡 Light status changed: {status}")
        # You can add custom handling here, e.g., update an indicator
    except Exception as e:
        logging.error(f"💡 Error handling status change: {e}")

def _on_light_connect_button_clicked(self):
    """Handle light controller connect button"""
    try:
        ip = self.light_ip_edit.text().strip()
        port = self.light_port_edit.text().strip()
        
        if not ip or not port:
            QMessageBox.warning(
                self.main_window,
                "Error",
                "Please enter both IP and port for light controller"
            )
            return
        
        if self.light_controller.is_connected:
            # Already connected, disconnect first
            self.light_controller._disconnect()
            self.light_connect_button.setText("Connect")
            logging.info("💡 Light controller disconnected")
        else:
            # Try to connect
            if self.light_controller.connect(ip, port):
                self.light_connect_button.setText("Disconnect")
                logging.info(f"💡 Connecting to light controller at {ip}:{port}")
            else:
                logging.error(f"💡 Failed to connect to light controller")
                
    except Exception as e:
        logging.error(f"💡 Error in connect button handler: {e}")
        QMessageBox.critical(self.main_window, "Error", f"Connection error: {e}")

def _on_light_send_button_clicked(self):
    """Handle light controller send button"""
    try:
        message = self.light_message_edit.text().strip()
        
        if not message:
            logging.warning("💡 Cannot send empty message")
            return
        
        if not self.light_controller.is_connected:
            QMessageBox.warning(
                self.main_window,
                "Error",
                "Not connected to light controller"
            )
            return
        
        if self.light_controller.send_message(message):
            # Add to message list with outgoing indicator
            self.light_message_list.addItem(f"→ {message}")
            self.light_message_list.scrollToBottom()
            
            # Clear input field
            self.light_message_edit.clear()
            
            logging.info(f"💡 Sent message to light controller: {message}")
        else:
            QMessageBox.warning(
                self.main_window,
                "Error",
                "Failed to send message to light controller"
            )
            
    except Exception as e:
        logging.error(f"💡 Error in send button handler: {e}")
        QMessageBox.critical(self.main_window, "Error", f"Send error: {e}")

def _update_light_button_states(self, connected: bool):
    """Update enabled/disabled state of light controller buttons"""
    try:
        # When connected: enable send, disable connect inputs
        # When disconnected: disable send, enable connect inputs
        self.light_ip_edit.setEnabled(not connected)
        self.light_port_edit.setEnabled(not connected)
        self.light_send_button.setEnabled(connected)
        self.light_message_edit.setEnabled(connected)
        
        if connected:
            self.light_connect_button.setText("Disconnect")
        else:
            self.light_connect_button.setText("Connect")
            
    except Exception as e:
        logging.error(f"💡 Error updating button states: {e}")
```

---

## 🎯 Step 5: Call Light Controller Setup in `main.py`

In `main.py` where you initialize TCP controller manager:

```python
# After TCP controller setup for camera
tcp_manager = TCPControllerManager(self)

# Setup camera controller
tcp_manager.setup(
    self.ipLineEdit,
    self.portLineEdit,
    self.connectButton,
    self.statusLabel,
    self.msgListWidget,
    self.msgLineEdit,
    self.sendButton
)

# ✨ NEW: Setup light controller
tcp_manager.setup_light_controller(
    self.ipLineEditLightController,
    self.portLineEditLightController,
    self.connectButtonLightController,
    self.statusLabelLightController,
    self.msgListWidgetLightController,
    self.msgLineEditLightController,
    self.sendButtonLightController
)

self.tcp_manager = tcp_manager
```

---

## 💡 Usage Example: Control Light in Trigger Workflow

You can now add light control to the delay trigger:

```python
def _check_and_trigger_camera_if_needed(self, message: str):
    """Check if message is trigger command and trigger camera with light control"""
    if not message.startswith('start_rising'):
        return
    
    camera_manager = self.main_window.camera_manager
    if not camera_manager:
        return
    
    try:
        # Check if delay trigger is enabled
        delay_enabled = self.main_window.delayTriggerCheckBox.isChecked()
        
        # ✨ NEW: Control light
        light_controller = self.main_window.tcp_manager.light_controller
        
        if delay_enabled:
            delay_ms = self.main_window.delayTriggerTime.value()
            logging.info(f"★ Trigger with {delay_ms}ms delay")
            
            # Turn on light FIRST
            if light_controller.is_connected:
                light_controller.turn_on()
                logging.info("💡 Light turned ON before delay")
            
            # Apply delay
            time.sleep(delay_ms / 1000.0)
            
            # Trigger camera
            camera_manager.activate_capture_request()
            
            # Turn off light AFTER capture
            if light_controller.is_connected:
                light_controller.turn_off()
                logging.info("💡 Light turned OFF after capture")
        else:
            # No delay - still control light
            if light_controller.is_connected:
                light_controller.turn_on()
            
            camera_manager.activate_capture_request()
            
            if light_controller.is_connected:
                light_controller.turn_off()
        
        logging.info(f"✓ Trigger completed")
        
    except Exception as e:
        logging.error(f"Error in trigger: {e}")
```

---

## 📝 Summary of Changes

| Step | File | Change |
|------|------|--------|
| 1 | tcp_controller_manager.py | Import `TCPLightController` |
| 2 | tcp_controller_manager.py | Add light controller instance in `__init__` |
| 3 | tcp_controller_manager.py | Add `setup_light_controller()` method |
| 4 | tcp_controller_manager.py | Add signal handlers for light controller |
| 5 | main.py | Call `setup_light_controller()` with UI elements |
| 6 | tcp_controller_manager.py | (Optional) Add light control to trigger workflow |

---

## ✅ Testing Checklist

- [ ] Import works without errors
- [ ] Light controller initializes without errors
- [ ] Light tab UI components are recognized
- [ ] Can enter IP and port for light device
- [ ] Connect button works
- [ ] Status label updates on connection
- [ ] Send button is disabled when not connected
- [ ] Send button is enabled when connected
- [ ] Can send commands to light device
- [ ] Receive messages are displayed correctly
- [ ] Lights respond to commands

---

## 🚀 Next: Light Control in Trigger

Once light controller is fully integrated, you can add automatic light control to the camera trigger workflow. See section "Usage Example: Control Light in Trigger Workflow" above.
