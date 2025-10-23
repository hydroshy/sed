# 🚀 Light Controller Quick Reference

## 📦 What Was Created

**File:** `controller/tcp_light_controller.py`

**Class:** `TCPLightController` (similar to `TCPController`)

---

## 🎯 Quick Commands

```python
from controller.tcp_light_controller import TCPLightController

# Initialize
light = TCPLightController()

# Connect
light.connect("192.168.1.100", "5000")

# Control
light.turn_on()              # Bật đèn
light.turn_off()             # Tắt đèn
light.toggle()               # Chuyển đổi
light.set_brightness(75)     # Độ sáng 0-100%

# Check status
light.is_connected           # True/False
light.light_status           # 'on', 'off', 'error', 'unknown'

# Send custom command
light.send_message('brightness:50')
```

---

## 🔌 UI Integration (3 Steps)

### 1️⃣ **Import in tcp_controller_manager.py**
```python
from controller.tcp_light_controller import TCPLightController
```

### 2️⃣ **Initialize in __init__**
```python
self.light_controller = TCPLightController()
```

### 3️⃣ **Setup UI in main.py**
```python
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

## 💡 Use in Trigger (With Delay)

```python
# Bật đèn → Chờ delay → Chụp camera → Tắt đèn

if delay_enabled:
    # Turn on light FIRST
    light_controller.turn_on()
    
    # Wait for light to stabilize
    time.sleep(delay_ms / 1000.0)
    
    # Capture frame
    camera_manager.activate_capture_request()
    
    # Turn off light AFTER capture
    light_controller.turn_off()
```

---

## 📊 Protocol

**Commands sent to light:**
```
on\n
off\n
toggle\n
brightness:50\n
```

**Responses from light:**
```
status:on\n
status:off\n
brightness:75\n
```

---

## 🔗 Files

| File | Purpose |
|------|---------|
| `controller/tcp_light_controller.py` | Light controller logic ✅ Created |
| `gui/tcp_controller_manager.py` | Integrate light controller (TODO) |
| `main.py` | Setup light UI (TODO) |

---

## 📋 Required UI Components (Already in lightControllerTab)

```
ipLineEditLightController          ← Input IP
portLineEditLightController        ← Input Port
connectButtonLightController       ← Connect button
statusLabelLightController         ← Status display
msgListWidgetLightController       ← Message history
msgLineEditLightController         ← Message input
sendButtonLightController          ← Send button
```

---

## ⚠️ Important Notes

1. **Light must turn ON before delay** (not after)
2. **Delay time lets light stabilize** before camera captures
3. **Turn off light after capture** to prevent overheating
4. **Protocol:** All messages end with `\n`
5. **Thread-safe:** Uses background monitor thread

---

## 📚 Full Documentation

- **Integration Steps:** See `LIGHT_CONTROLLER_INTEGRATION_STEPS.md`
- **API Reference:** See `TCP_LIGHT_CONTROLLER_INTEGRATION.md`

---

## ✅ Verification

```bash
# Check file exists
Test-Path "e:\PROJECT\sed\controller\tcp_light_controller.py"

# Check syntax
python -m py_compile controller\tcp_light_controller.py
```

**Status:** ✅ File created and syntax verified
