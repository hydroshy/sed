# External Trigger - Quick Reference Card

## 🚀 One-Minute Summary

You asked for two things for GS Camera on Raspberry Pi:

### ✅ #1 Hardware External Trigger Control
**When:** User clicks "Trigger Camera Mode" button  
**What:** Executes `echo 1 | sudo tee /sys/module/imx296/parameters/trigger_mode`  
**Where:** `camera_stream.py:_set_external_trigger_sysfs()`  
**Result:** ✅ Camera waits for hardware trigger signals instead of continuous streaming

### ✅ #2 Automatic 3A Lock on Camera Start
**When:** User clicks "onlineCamera" button while in trigger mode  
**What:** Automatically locks exposure (AE) and white balance (AWB)  
**Where:** `main_window.py:_toggle_camera()`  
**Result:** ✅ Consistent image quality for inspection/detection algorithms

---

## 📊 Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│ User clicks "Trigger Camera Mode"                       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
            set_trigger_mode(True)
                       │
                       ▼
        _set_external_trigger_sysfs(True)
                       │
         echo 1 | sudo tee /sys/.../trigger_mode
                       │
        ✅ GS Camera EXTERNAL TRIGGER ENABLED
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ User clicks "onlineCamera" button                       │
└──────────────────────┬──────────────────────────────────┘
                       │
        Detect: current_mode == 'trigger'?
                       │
                    YES ▼
        set_manual_exposure_mode()  ← Lock AE
        set_auto_white_balance(False) ← Lock AWB
                       │
        ✅ 3A LOCKED (Exposure + White Balance)
                       │
                       ▼
        camera_stream.start_preview()
                       │
            ✅ Camera waiting for trigger signal
                       │
                       ▼
            Hardware sends trigger pulse
                       │
                       ▼
            Camera captures frame
                       │
                       ▼
            Job processes detection
                       │
                       ▼
            Result displays in Result Tab
```

---

## 🔧 Code Changes Summary

### File 1: `camera/camera_stream.py`

#### What was changed?
- **Line 8:** Added `import subprocess`
- **Line 559:** Modified `set_trigger_mode()` to call `_set_external_trigger_sysfs()`
- **Lines 693-731:** Added new method `_set_external_trigger_sysfs(enabled)`

#### What does it do?
```python
def _set_external_trigger_sysfs(self, enabled):
    # Runs: echo 1 | sudo tee /sys/module/imx296/parameters/trigger_mode
    # Returns: True on success, False on error
    # Timeout: 5 seconds (prevents hanging)
```

### File 2: `gui/main_window.py`

#### What was changed?
- **Lines 1008-1028:** Added 3A locking logic in `_toggle_camera()` method

#### What does it do?
```python
if current_mode == 'trigger':
    logging.info("🔒 Locking 3A (AE + AWB) for trigger mode...")
    self.camera_manager.set_manual_exposure_mode()
    camera_stream.set_auto_white_balance(False)
    logging.info("✅ 3A locked (AE + AWB disabled)")
```

---

## 🧪 Test It

### Test 1: Enable Trigger Mode
```
1. Click "Trigger Camera Mode" button
2. Check console output:
   ✅ "External trigger ENABLED"
   ✅ Output shows "1"
```

### Test 2: 3A Lock on Camera Start
```
1. Click "onlineCamera" button
2. Check console output:
   ✅ "Locking 3A (AE + AWB) for trigger mode..."
   ✅ "AWB locked"
   ✅ "3A locked (AE + AWB disabled)"
3. Camera preview shows live feed
```

### Test 3: Send Trigger Signal
```
1. Send hardware trigger signal (GPIO pulse)
2. Frame captured
3. Result appears in Result Tab
```

---

## 📋 Commands to Know

### Enable External Trigger
```bash
echo 1 | sudo tee /sys/module/imx296/parameters/trigger_mode
```

### Disable External Trigger
```bash
echo 0 | sudo tee /sys/module/imx296/parameters/trigger_mode
```

### Check Status
```bash
cat /sys/module/imx296/parameters/trigger_mode
# Returns 1 (enabled) or 0 (disabled)
```

---

## 🎯 Why This Implementation?

### Hardware sysfs Control (Not Software Mode)
```
✅ Matches Raspberry Pi GS Camera spec
✅ Faster response to trigger signals
✅ More reliable signal synchronization
✅ Lower CPU overhead
✅ Professional camera behavior
```

### Automatic 3A Lock (Not Manual)
```
✅ Prevents exposure variations
✅ Consistent image quality
✅ Better detection accuracy
✅ Simpler user workflow
✅ Aligns with trigger use case
```

---

## 📝 Log Examples

### When Enabling Trigger Mode
```
DEBUG: [CameraStream] Running external trigger command: echo 1 | sudo tee /sys/module/imx296/parameters/trigger_mode
✅ [CameraStream] External trigger ENABLED
   Output: 1
```

### When Starting Camera in Trigger Mode
```
INFO: Starting camera stream...
🔒 Locking 3A (AE + AWB) for trigger mode...
✅ AWB locked
✅ 3A locked (AE + AWB disabled)
INFO: Camera stream started successfully
```

---

## 🔐 Requirements

### sudo Setup (One-time)
```bash
# Add this line to sudoers (sudo visudo):
pi ALL=(ALL) NOPASSWD: /usr/bin/tee
```

### Hardware
- Raspberry Pi with GS Camera
- External trigger source (GPIO, sensor, etc.)

### Software
- Python 3.7+
- picamera2 library
- subprocess module (built-in)

---

## ❓ FAQ

**Q: Do I need to manually lock 3A?**  
A: No! When you click "onlineCamera" in trigger mode, 3A locks automatically.

**Q: Can I switch between trigger and live mode?**  
A: Yes! Click "Trigger Camera Mode" or "Live Camera Mode" anytime.

**Q: What if sudo command fails?**  
A: Check logs for error message. Usually needs sudo setup (see Requirements).

**Q: Will this affect live mode?**  
A: No! Live mode is completely unaffected. Only trigger mode uses external trigger.

**Q: Can I test without hardware trigger?**  
A: Camera will start but won't capture without actual trigger signal.

---

## 📚 Full Documentation

For complete details, see:
- **Full Implementation:** `docs/EXTERNAL_TRIGGER_GS_CAMERA.md`
- **Summary:** `EXTERNAL_TRIGGER_SUMMARY.md`
- **This File:** `GS_CAMERA_EXTERNAL_TRIGGER_COMPLETE.md`

---

**Status:** ✅ COMPLETE  
**Date:** 2025-11-07  
**Ready:** Yes - Live testing with GS Camera

