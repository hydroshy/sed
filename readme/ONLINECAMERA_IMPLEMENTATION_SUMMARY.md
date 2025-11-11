# OnlineCamera Button - Implementation Summary

**Date**: November 10, 2025  
**Status**: ✅ Complete  
**File Modified**: `gui/main_window.py`

---

## What Changed

The **onlineCamera button** (previously: live camera button) now has **mode-dependent behavior**:

### Before:
- Forced TRIGGER mode when clicked
- Always set external trigger enabled
- Then started simple camera preview

### After:
- **LIVE Mode**: Starts **continuous streaming** (non-stop frame flow)
- **TRIGGER Mode**: Preserves **trigger configuration** and starts **simple preview** (ready for triggers)

---

## Implementation Details

### File: `gui/main_window.py`
### Method: `_toggle_camera(checked)` 
### Lines: ~975-1113

#### Logic Flow:

```python
def _toggle_camera(self, checked):
    if checked:  # Start camera
        desired_mode = current_camera_mode  # 'live' or 'trigger'
        
        if desired_mode == 'live':
            # Start continuous streaming
            camera_manager.start_live_camera(force_mode_change=True)
            # Result: Continuous video, button green
        else:
            # Start trigger mode streaming
            camera_manager.set_trigger_mode(True)
            camera_stream.start_preview()
            camera_manager.set_manual_exposure_mode()  # Lock AE
            camera_stream.set_auto_white_balance(False)  # Lock AWB
            # Result: Preview ready for triggers, button green
            
    else:  # Stop camera
        camera_stream.stop_preview()
        # Result: Camera off, button red
```

---

## Button Behavior Reference

### State: Checked (Camera Running)
- **Color**: 🟢 Green (`#4CAF50`)
- **LIVE Mode**: Continuous streaming active
- **TRIGGER Mode**: Preview running, trigger ready

### State: Unchecked (Camera Stopped)
- **Color**: 🔴 Red (`#f44336`)
- **Action Needed**: Click button again to start

### State: Disabled (No Camera Source)
- **Color**: ⚪ Gray (`#cccccc`)
- **Reason**: No Camera Source tool in job or editing Camera Tool
- **Action Needed**: Add Camera Source tool or finish editing

---

## Mode Detection

Current camera mode is determined by:
```python
desired_mode = getattr(self.camera_manager, 'current_mode', 'live')
```

This reflects:
- User's selection via `liveCameraMode` / `triggerCameraMode` buttons
- Default: `'live'`
- Updated by: `camera_manager.set_trigger_mode(enabled)`

---

## Integration Points

### CameraManager Methods Called:

| Method | Mode | Purpose |
|--------|------|---------|
| `start_live_camera(force_mode_change=True)` | LIVE | Start continuous streaming with UI updates |
| `set_trigger_mode(True)` | TRIGGER | Enable external trigger on hardware |
| `camera_stream.start_preview()` | TRIGGER | Start simple frame preview |
| `camera_stream.stop_preview()` | Both | Stop any active streaming |

### Signals & UI Updates:

```
onlineCamera.clicked(True/False)
    ↓
_toggle_camera(checked)
    ↓
Update camera_manager state & camera_stream
    ↓
Button style updated (green/red)
    ↓
Debug logs printed
```

---

## Debug Output Examples

### LIVE Mode Started:
```
OnlineCamera button toggled: True
Starting camera stream (mode=live)
📹 LIVE mode: starting continuous live camera stream
Camera stream started successfully
```

### TRIGGER Mode Started:
```
OnlineCamera button toggled: True
Starting camera stream (mode=trigger)
📸 TRIGGER mode: ensuring trigger mode then starting simple camera stream
>>> CALLING: camera_manager.set_trigger_mode(True)
✅ Trigger mode command completed (sysfs executed)
Camera stream started successfully (trigger mode)
🔒 Locking 3A (AE + AWB) for trigger mode...
✅ 3A locked (AE + AWB disabled)
```

### Camera Stopped:
```
OnlineCamera button toggled: False
Stopping camera stream...
Camera stream stopped
```

---

## Testing Checklist

- [ ] LIVE Mode: Click onlineCamera → camera starts continuous streaming
- [ ] LIVE Mode: Video plays without interruption
- [ ] TRIGGER Mode: Click `triggerCameraMode`, then click onlineCamera → camera preview starts
- [ ] TRIGGER Mode: `triggerCamera` button is enabled and ready for clicks
- [ ] TRIGGER Mode: 3A lock applied (AE + AWB disabled)
- [ ] Stop: Click onlineCamera again → camera stops, button turns red
- [ ] Mode Switch: Switch from LIVE to TRIGGER while camera running → should restart
- [ ] No Camera Source: Without Camera Source in job → button should be disabled (gray)
- [ ] Editing: While editing Camera Source → button should be disabled (gray)

---

## Related Documentation

- `ONLINECAMERA_BUTTON_BEHAVIOR.md` - Detailed behavior documentation
- `ONLINECAMERA_QUICK_REFERENCE.md` - Quick reference guide
- `LIVE_CAMERA_BUTTON_BEHAVIOR.md` - Previous implementation notes

---

## Files Modified

| File | Changes | Impact |
|------|---------|--------|
| `gui/main_window.py` | `_toggle_camera()` method (lines 975-1113) | ✅ Mode-dependent button behavior |

---

## Notes

1. **Backward Compatibility**: If `current_mode` is not set, defaults to `'live'` for safety
2. **Fail-Safe**: If camera fails to start, button automatically unchecked and set to red
3. **State Preservation**: When switching modes while camera stopped, mode preference is remembered
4. **UI Feedback**: Green color indicates camera is running, red indicates stopped
5. **3A Locking**: Only applied in TRIGGER mode to ensure consistent lighting for captures

---

## Future Enhancements

- Add confirmation dialog before mode switches while camera running
- Remember user's last camera state per session
- Add button tooltip showing current mode
- Add FPS indicator for LIVE mode
- Add countdown timer for TRIGGER mode captures
