# 💡 Light Controller UI Integration - For main.py

## 📝 Steps to Integrate Light Controller UI in main.py

### Step 1: In your `main.py` (where you setup TCP manager)

Find where you have the camera controller setup:

```python
# Existing camera controller setup
tcp_manager = TCPControllerManager(self)
tcp_manager.setup(
    self.ipLineEdit,
    self.portLineEdit,
    self.connectButton,
    self.statusLabel,
    self.msgListWidget,
    self.msgLineEdit,
    self.sendButton
)
```

### Step 2: Add Light Controller Setup Right After

Add this right after the camera controller setup:

```python
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

# Store reference
self.tcp_manager = tcp_manager
```

### Step 3: Add Cleanup in Closeup/Exit Handler

If you have a closeup event handler, add:

```python
def closeEvent(self, event):
    # ... existing cleanup code ...
    
    # ✨ Cleanup TCP manager (including light controller)
    if hasattr(self, 'tcp_manager') and self.tcp_manager:
        self.tcp_manager.cleanup()
    
    event.accept()
```

---

## 🎯 Complete Example

```python
# In your MainWindow class initialization or setup method

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # ... load UI ...
        
        # Initialize TCP manager
        self.tcp_manager = TCPControllerManager(self)
        
        # Setup camera controller (existing)
        self.tcp_manager.setup(
            self.ipLineEdit,
            self.portLineEdit,
            self.connectButton,
            self.statusLabel,
            self.msgListWidget,
            self.msgLineEdit,
            self.sendButton
        )
        
        # ✨ Setup light controller (NEW)
        self.tcp_manager.setup_light_controller(
            self.ipLineEditLightController,
            self.portLineEditLightController,
            self.connectButtonLightController,
            self.statusLabelLightController,
            self.msgListWidgetLightController,
            self.msgLineEditLightController,
            self.sendButtonLightController
        )
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Cleanup TCP manager
        if hasattr(self, 'tcp_manager') and self.tcp_manager:
            self.tcp_manager.cleanup()
        
        event.accept()
```

---

## ✅ What Gets Connected

### UI Components Connected:
- ✅ ipLineEditLightController → IP input
- ✅ portLineEditLightController → Port input
- ✅ connectButtonLightController → Connect/Disconnect button
- ✅ statusLabelLightController → Status display
- ✅ msgListWidgetLightController → Message history
- ✅ msgLineEditLightController → Message input
- ✅ sendButtonLightController → Send button

### Functionality:
- ✅ Connect button: Connects/disconnects from light device
- ✅ Send button: Sends message to light device
- ✅ Enter key: Also sends message (from msgLineEditLightController)
- ✅ Status label: Shows connection status (green=connected, red=disconnected)
- ✅ Message list: Shows all sent/received messages

---

## 🧪 Testing

After integration, test:

1. **UI appears**: Light controller tab and all components visible
2. **Connect button works**: Can enter IP/port and click Connect
3. **Status updates**: Status label changes to green when connected
4. **Send works**: Can type message and send it
5. **Message history**: Messages appear in list (→ for sent, ← for received)
6. **Disconnect works**: Can click button to disconnect

---

## 🎯 Now You Can:

1. **Manual Control**
   - Fill IP/port of light device
   - Click Connect
   - Type commands like "on", "off", "brightness:50"
   - Send and see responses

2. **Programmatic Control** (later, when integrating with camera)
   - Use: `self.tcp_manager.light_controller.turn_on()`
   - Use: `self.tcp_manager.light_controller.turn_off()`
   - Use: `self.tcp_manager.light_controller.set_brightness(100)`

3. **Monitor Status**
   - Use: `self.tcp_manager.light_controller.is_connected`
   - Use: `self.tcp_manager.light_controller.light_status`

---

## 📋 Summary of Changes

**File:** `gui/tcp_controller_manager.py`
- ✅ Import TCPLightController
- ✅ Add light_controller initialization in __init__
- ✅ Add setup_light_controller() method
- ✅ Add light controller signal handlers
- ✅ Add light controller button handlers
- ✅ Update cleanup() method

**File:** `main.py` (your application)
- ⏳ Add setup_light_controller() call
- ⏳ Add cleanup in closeEvent (optional but recommended)

---

## 🚀 You're Ready!

The light controller is now fully integrated and ready to use from the UI. No need for manual coding - just connect, send commands, and see responses!
