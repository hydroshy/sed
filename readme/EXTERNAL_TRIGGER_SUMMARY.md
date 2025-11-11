# External Trigger Implementation - Quick Summary

## ✅ Implemented Features

### 1. Hardware External Trigger Control (GS Camera)
**File:** `camera/camera_stream.py`

**New Method:** `_set_external_trigger_sysfs(enabled)`
- Executes: `echo 1 | sudo tee /sys/module/imx296/parameters/trigger_mode`
- Enables/disables hardware trigger at sysfs level
- 5-second timeout to prevent hanging
- Returns True/False for success/failure

**Modified Method:** `set_trigger_mode(enabled)` (Line 559)
- Now calls `_set_external_trigger_sysfs(enabled)` 
- Uses hardware sysfs control instead of software-only mode

### 2. Automatic 3A Locking in Trigger Mode
**File:** `gui/main_window.py`

**Modified Method:** `_toggle_camera(checked)` (Line 994)
- Detects if `current_mode == 'trigger'`
- Automatically locks AE (Exposure): `set_manual_exposure_mode()`
- Automatically locks AWB (White Balance): `set_auto_white_balance(False)`
- Provides clear logging feedback

---

## Workflow

```
1. User clicks "Trigger Camera Mode"
   └─ set_trigger_mode(True)
      └─ echo 1 | sudo tee /sys/module/imx296/parameters/trigger_mode
         └─ ✅ GS Camera external trigger ENABLED

2. User clicks "onlineCamera" button (in trigger mode)
   └─ Detect current_mode == 'trigger'
      └─ Lock 3A (AE + AWB)
         └─ camera.set_manual_exposure_mode()
         └─ camera.set_auto_white_balance(False)
            └─ ✅ 3A LOCKED

3. Camera waits for hardware trigger signal
   └─ Frame received
      └─ Job processes
         └─ Result displays in Result Tab
```

---

## Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `camera/camera_stream.py` | Added `_set_external_trigger_sysfs()` method, modified `set_trigger_mode()`, added `subprocess` import | 559, 693-731 |
| `gui/main_window.py` | Added 3A locking in `_toggle_camera()` when trigger mode detected | 1008-1028 |

---

## Key Commands

### Enable External Trigger (When switching to trigger mode)
```bash
echo 1 | sudo tee /sys/module/imx296/parameters/trigger_mode
```

### Disable External Trigger (When switching to live mode)
```bash
echo 0 | sudo tee /sys/module/imx296/parameters/trigger_mode
```

### Check Current Status
```bash
cat /sys/module/imx296/parameters/trigger_mode
```

---

## Expected Log Output

### Enabling Trigger Mode
```
DEBUG: [CameraStream] Running external trigger command: echo 1 | sudo tee /sys/module/imx296/parameters/trigger_mode
✅ [CameraStream] External trigger ENABLED
   Output: 1
```

### Starting Camera in Trigger Mode with 3A Lock
```
INFO: Starting camera stream...
🔒 Locking 3A (AE + AWB) for trigger mode...
✅ AWB locked
✅ 3A locked (AE + AWB disabled)
INFO: Camera stream started successfully
```

---

## Testing Steps

### Test 1: Enable Trigger Mode
1. Load a job with Camera Source tool
2. Click "Trigger Camera Mode" button
3. Check logs for: `✅ [CameraStream] External trigger ENABLED`
4. Verify: `cat /sys/module/imx296/parameters/trigger_mode` returns `1`

### Test 2: 3A Lock on Camera Start
1. In trigger mode, click "onlineCamera" button
2. Check logs for: `✅ 3A locked (AE + AWB disabled)`
3. Send hardware trigger signal
4. Verify frame appears in Result Tab

### Test 3: Disable Trigger Mode
1. Click "Live Camera Mode" button
2. Check logs for: `✅ [CameraStream] External trigger DISABLED`
3. Verify: `cat /sys/module/imx296/parameters/trigger_mode` returns `0`

---

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Command timed out | sysfs access slow | Check `/sys/module/imx296` exists |
| External trigger failed | Permission denied | Add sudo rule without password |
| 3A not locked | Function not called | Check logs for AWB lock message |

---

## Technical Details

### sysfs Path
```
/sys/module/imx296/parameters/trigger_mode
```

### Values
- `1` = External trigger ENABLED (camera waits for trigger)
- `0` = External trigger DISABLED (continuous capture)

### subprocess Configuration
- `shell=True` for pipe (`|`) support
- `capture_output=True` for error handling
- `text=True` for string output
- `timeout=5` prevents hanging

### 3A Components
- **AE (Auto Exposure):** `AeEnable = False` via `set_manual_exposure_mode()`
- **AWB (Auto White Balance):** `AwbEnable = False` via `set_auto_white_balance(False)`

---

## References

- [Raspberry Pi GS Camera External Trigger](https://www.raspberrypi.com/documentation/accessories/camera.html#external-trigger-on-the-gs-camera)
- Implementation: `docs/EXTERNAL_TRIGGER_GS_CAMERA.md`

---

**Status:** ✅ Complete and Ready for Testing  
**Implementation Date:** 2025-11-07
