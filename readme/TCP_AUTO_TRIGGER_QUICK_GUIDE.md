# ⚡ TCP AUTO-TRIGGER CAMERA - QUICK SETUP

## 3-Step Setup

### Step 1: Set Camera to Trigger Mode
```
App → Camera Tool Tab
Camera Mode: Select "Trigger" ✅
```

### Step 2: Connect to Sensor Device
```
App → Controller Tab
IP: 192.168.1.190
Port: 4000
Click "Connect" ✅
```

### Step 3: Start Capture
```
Sensor sends: "start_rising||1634723"
↓
System automatically captures frame ✅
```

---

## How It Works

```
Sensor GPIO trigger
  ↓
TCP message: "start_rising||timestamp"
  ↓
TCPControllerManager receives
  ↓
Check: Is "start_rising" in message? YES
  ↓
Check: Is camera in trigger mode? YES
  ↓
Call: camera_manager.activate_capture_request()
  ↓
📸 FRAME CAPTURED!
```

---

## Console Verification

Look for these logs:

```
★ Detected trigger command: start_rising||1634723
★ Camera is in trigger mode, triggering capture
✓ Camera triggered successfully
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Camera not triggering | Check: Is camera in TRIGGER mode? |
| Message shows but no trigger | Check: Is TCP connected? |
| Error: camera_manager not found | Check: Camera widget initialized? |
| Too many captures | Increase cooldown: `set_trigger_cooldown(0.5)` |

---

## Key Files

- **Code:** `gui/tcp_controller_manager.py` (method: `_check_and_trigger_camera_if_needed`)
- **Docs:** `TCP_TRIGGER_CAMERA.md` (detailed guide)
- **Config:** Camera Tool → Mode selection

---

## Expected Output

**Message List:**
```
RX: start_rising||1634723
[TRIGGER] Camera captured from: start_rising||1634723
```

**Console:**
```
★★★ _on_message_received CALLED!
★ Detected trigger command
✓ Camera triggered successfully
```

---

✅ **Ready!** Your system will now auto-capture when sensor sends command.

See: `TCP_TRIGGER_CAMERA.md` for detailed documentation.
