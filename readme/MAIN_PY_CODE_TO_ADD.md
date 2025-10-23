# 📝 Exact Code to Add to main.py

## 🎯 Find This Code

Search for where you have the camera controller setup. It should look like:

```python
# ============ TCP CONTROLLER SETUP ============
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

# Store for later access
self.tcp_manager = tcp_manager
```

Or something similar in your `__init__` method or setup method.

---

## ✂️ Copy-Paste This Code

Add this code **right after** the camera controller setup:

```python
        # ============ LIGHT CONTROLLER SETUP ============
        # ✨ NEW: Setup light controller (same as camera, but for lights)
        tcp_manager.setup_light_controller(
            self.ipLineEditLightController,
            self.portLineEditLightController,
            self.connectButtonLightController,
            self.statusLabelLightController,
            self.msgListWidgetLightController,
            self.msgLineEditLightController,
            self.sendButtonLightController
        )
```

---

## 📍 Where to Add It

### Location Example 1: In __init__

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # ... other initialization ...
        
        # Initialize managers
        self.tcp_manager = TCPControllerManager(self)
        
        # Setup camera controller
        self.tcp_manager.setup(
            self.ipLineEdit,
            self.portLineEdit,
            self.connectButton,
            self.statusLabel,
            self.msgListWidget,
            self.msgLineEdit,
            self.sendButton
        )
        
        # ✨ ADD HERE: Setup light controller
        self.tcp_manager.setup_light_controller(
            self.ipLineEditLightController,
            self.portLineEditLightController,
            self.connectButtonLightController,
            self.statusLabelLightController,
            self.msgListWidgetLightController,
            self.msgLineEditLightController,
            self.sendButtonLightController
        )
        
        # ... rest of initialization ...
```

### Location Example 2: In a setup method

```python
def setup_controllers(self):
    """Setup TCP controllers"""
    
    # Setup camera controller
    self.tcp_manager = TCPControllerManager(self)
    self.tcp_manager.setup(
        self.ipLineEdit,
        self.portLineEdit,
        self.connectButton,
        self.statusLabel,
        self.msgListWidget,
        self.msgLineEdit,
        self.sendButton
    )
    
    # ✨ ADD HERE: Setup light controller
    self.tcp_manager.setup_light_controller(
        self.ipLineEditLightController,
        self.portLineEditLightController,
        self.connectButtonLightController,
        self.statusLabelLightController,
        self.msgListWidgetLightController,
        self.msgLineEditLightController,
        self.sendButtonLightController
    )
```

---

## 🔧 Complete Before/After Example

### BEFORE:
```python
# Setup TCP manager
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
self.tcp_manager = tcp_manager
```

### AFTER:
```python
# Setup TCP manager
tcp_manager = TCPControllerManager(self)

# Camera controller setup
tcp_manager.setup(
    self.ipLineEdit,
    self.portLineEdit,
    self.connectButton,
    self.statusLabel,
    self.msgListWidget,
    self.msgLineEdit,
    self.sendButton
)

# ✨ NEW: Light controller setup (exactly like camera, but for lights)
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

## ✅ Verification

After adding the code:

1. ✅ Check no syntax errors
2. ✅ Run application
3. ✅ Look for light controller tab
4. ✅ All components should be visible
5. ✅ Light tab should work like camera tab

---

## 🚨 If You Get Errors

### Error: "AttributeName not defined"
- Make sure UI component names in setup_light_controller() match your `.ui` file
- Check: ipLineEditLightController, portLineEditLightController, etc.

### Error: "tcp_manager not defined"
- Make sure you're adding the code where tcp_manager is already defined
- It should be right after tcp_manager.setup(...) call

### Error: "Module not found"
- The import is already in tcp_controller_manager.py
- No need to import again in main.py

---

## 💾 One-Liner Version

If you prefer a more compact format:

```python
tcp_manager.setup_light_controller(self.ipLineEditLightController, self.portLineEditLightController, self.connectButtonLightController, self.statusLabelLightController, self.msgListWidgetLightController, self.msgLineEditLightController, self.sendButtonLightController)
```

But the multi-line version is more readable!

---

## 🎯 That's All!

Just add the setup_light_controller() call and everything will work automatically!

No other code changes needed in main.py.

---

## 📞 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Light tab doesn't appear | Check UI file has light components |
| Buttons don't work | Check setup call was added |
| Syntax error | Check component names match UI file |
| Connection fails | Check IP/port are correct |
| No messages appear | Check light device is on and responding |

---

## ✨ Summary

**What to add:** 10 lines of code (or 1 line if formatted compactly)
**Where to add:** After tcp_manager.setup() call
**What it does:** Connects all light UI components automatically
**Result:** Light controller tab works exactly like camera tab

Done! 🎉
