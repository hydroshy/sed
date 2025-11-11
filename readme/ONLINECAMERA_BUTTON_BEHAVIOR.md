# OnlineCamera Button Behavior

## Overview

The **onlineCamera** button (`Online Camera` in UI) toggles camera streaming with **mode-dependent behavior**:

- **LIVE mode**: Starts **continuous streaming** (like testjob.py)
- **TRIGGER mode**: Preserves **trigger configuration** and starts **simple camera preview**

This behavior is implemented in `gui/main_window.py::_toggle_camera()`.

---

## Button States

| State | Color | Meaning |
|-------|-------|---------|
| ✅ Checked + Green | `#4CAF50` (Green) | Camera running in trigger mode |
| ❌ Unchecked + Red | `#f44336` (Red) | Camera stopped |
| 🔒 Disabled + Gray | `#cccccc` (Gray) | No Camera Source in job or editing Camera Tool |

---

## Click Behavior

### When `checked == True` (Start camera):

#### LIVE Mode Detected:
```
onlineCamera.clicked(True)
  ↓
desired_mode == 'live'
  ↓
camera_manager.start_live_camera(force_mode_change=True)
  ↓
start_live() [continuous streaming]
  ↓
✅ Camera running continuously
```

**Result**: Camera streams continuously without requiring trigger clicks.

---

#### TRIGGER Mode Detected:
```
onlineCamera.clicked(True)
  ↓
desired_mode == 'trigger'
  ↓
Ensure trigger mode enabled → camera_manager.set_trigger_mode(True)
  ↓
camera_stream.start_preview() [simple preview, no job]
  ↓
Lock 3A (AE + AWB disabled)
  ↓
✅ Camera preview running in trigger mode
```

**Result**: Camera preview starts, trigger mode active, ready for trigger captures.

---

### When `checked == False` (Stop camera):

```
onlineCamera.clicked(False)
  ↓
camera_stream.stop_preview() or stop_live()
  ↓
Disable job execution
  ↓
✅ Camera stopped, button set to red
```

---

## Code Flow

### File: `gui/main_window.py`

```python
def _toggle_camera(self, checked):
    if checked:
        # Get current mode
        desired_mode = getattr(self.camera_manager, 'current_mode', 'live')
        
        if desired_mode == 'live':
            # 📹 LIVE mode: continuous streaming
            success = self.camera_manager.start_live_camera(force_mode_change=True)
            
        else:  # TRIGGER mode
            # 📸 TRIGGER mode: ensure trigger enabled, then preview
            self.camera_manager.set_trigger_mode(True)
            self.camera_manager.camera_stream.start_preview()
            
            # Lock 3A (AE + AWB)
            self.camera_manager.set_manual_exposure_mode()
            self.camera_manager.camera_stream.set_auto_white_balance(False)
            
            # Set button green
            self.onlineCamera.setStyleSheet("background-color: #4CAF50")
    else:
        # Stop camera
        self.camera_manager.camera_stream.stop_preview()
        # Set button red
        self._set_camera_button_off_style()
```

---

## Integration Points

### Camera Manager Methods Called:

1. **`camera_manager.start_live_camera(force_mode_change=True)`**
   - Used in LIVE mode
   - Starts continuous streaming
   - Updates UI state
   
2. **`camera_manager.set_trigger_mode(True)`**
   - Used in TRIGGER mode
   - Enables external trigger on camera
   - Waits for sysfs command completion

3. **`camera_stream.start_preview()`**
   - Used in TRIGGER mode
   - Simple frame streaming without job processing
   
4. **`camera_stream.stop_preview()` / `stop_live()`**
   - Stops any active streaming
   - Disables job execution

### Settings Manager Integration:

When Camera Source tool is applied or job changes, `_update_camera_button_state()` is called to:
- Enable/disable the button
- Update button style
- Reflect current job state

---

## Signal Connections

### In `setup_signals()`:

```python
if self.onlineCamera:
    self.onlineCamera.setCheckable(True)
    self.onlineCamera.clicked.connect(self._toggle_camera)
    self._update_camera_button_state()
```

---

## Mode Switching via Live Camera Mode / Trigger Camera Mode buttons:

When user switches mode using `liveCameraMode` or `triggerCameraMode` buttons:

1. Button click updates `camera_manager.current_mode`
2. Next `onlineCamera` click will use new mode
3. If camera already running, may need to restart to apply mode changes

---

## Debug Output

When onlineCamera button is clicked, you'll see debug logs like:

```
OnlineCamera button toggled: True
Starting camera stream (mode=live)
📹 LIVE mode: starting continuous live camera stream
>>> CALLING: camera_manager.start_live_camera(force_mode_change=True)
Camera stream started successfully
```

Or for trigger mode:

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

---

## Related Files

- `gui/main_window.py` - `_toggle_camera()` method (Lines 975-1108)
- `gui/camera_manager.py` - `start_live_camera()`, `set_trigger_mode()`, `_start_camera_stream()`
- `gui/main_window.py` - `setup_signals()` - button signal connections
- `gui/settings_manager.py` - Updates button state when Camera Source changes

---

## Example Usage Flow

### Scenario 1: User starts camera in LIVE mode

1. User in LIVE mode (default)
2. Clicks `onlineCamera` button
3. Button becomes checkable and toggles on
4. `_toggle_camera(True)` called
5. Detects `desired_mode == 'live'`
6. Calls `camera_manager.start_live_camera(force_mode_change=True)`
7. Camera runs **continuously** - frames stream non-stop
8. User sees live video feed

### Scenario 2: User switches to TRIGGER mode and starts camera

1. User clicks `triggerCameraMode` button
2. `camera_manager.current_mode = 'trigger'`
3. User clicks `onlineCamera` button
4. `_toggle_camera(True)` called
5. Detects `desired_mode == 'trigger'`
6. Calls `camera_manager.set_trigger_mode(True)`
7. Disables AE/AWB (3A lock)
8. Calls `camera_stream.start_preview()`
9. Camera preview runs - ready for trigger clicks
10. User clicks `triggerCamera` button to capture frame

### Scenario 3: User stops camera

1. User clicks `onlineCamera` button again
2. `_toggle_camera(False)` called
3. Stops camera stream
4. Button set to red (off state)
5. Camera preview stops

---

## Notes

- Button is automatically **disabled** (gray) when no Camera Source tool exists in job
- Button is automatically **disabled** when editing Camera Source tool
- 3A (AE + AWB) is **locked** only in TRIGGER mode for consistent lighting
- In LIVE mode, 3A remains unlocked for natural exposure adjustments
- Mode switching while camera is running may require camera restart
