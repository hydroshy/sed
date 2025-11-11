# OnlineCamera Button - Quick Reference

## Button Behavior at a Glance

```
                          onlineCamera Button Click
                                    |
                    _________________|_________________
                   |                                   |
              checked == True                    checked == False
            (Start Camera)                       (Stop Camera)
                   |                                   |
        ___________|___________                       |
       |                       |                       |
   LIVE Mode            TRIGGER Mode            Stop Streaming
   (continuous)         (simple preview)              |
       |                       |                       |
       |                       |              stop_preview() / stop_live()
       |                       |                       |
       v                       v                       v
  start_live()  -->  set_trigger_mode(True)  -->  [Camera OFF]
  (continuous      start_preview()                    |
   streaming)      Lock 3A (AE+AWB)           Button: Red (#f44336)
       |                       |                       
       |                       |                  
       v                       v
  [Camera ON]         [Camera ON] (preview)
  Continuous video    Ready for trigger


Legend:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📹 LIVE Mode    = Continuous streaming (frames flow non-stop)
📸 TRIGGER Mode = Simple preview (frames flow until trigger capture)
🟢 Green (#4CAF50) = Camera running
🔴 Red (#f44336)   = Camera stopped
⚪ Gray (#cccccc)   = Button disabled (no Camera Source in job)
```

---

## Key Differences

| Aspect | LIVE Mode | TRIGGER Mode |
|--------|-----------|--------------|
| **Behavior** | Continuous streaming | Simple preview + trigger ready |
| **Frame Flow** | Non-stop | Until trigger capture |
| **3A Lock** | ❌ Unlocked (auto AE/AWB) | ✅ Locked (manual) |
| **Use Case** | Real-time monitoring | Single-shot capture |
| **Next Action** | Watch video | Click trigger to capture |

---

## Code Location

**File**: `e:\PROJECT\sed\gui\main_window.py`
**Method**: `_toggle_camera(checked)` (Lines ~975-1108)
**Signal**: `onlineCamera.clicked → _toggle_camera(True/False)`

---

## Debug Markers to Look For

### LIVE Mode Started:
```
📹 LIVE mode: starting continuous live camera stream
```

### TRIGGER Mode Started:
```
📸 TRIGGER mode: ensuring trigger mode then starting simple camera stream
✅ 3A locked (AE + AWB disabled)
```

### Camera Stopped:
```
Stopping camera stream...
Camera stream stopped
```

---

## Button State Conditions

```
Enabled + Red     = Camera source exists, camera OFF
Enabled + Green   = Camera source exists, camera ON (trigger mode)
Disabled + Gray   = No camera source in job OR editing Camera Tool
```

---

## Decision Logic

```python
def _toggle_camera(checked):
    if checked:  # START camera
        if current_mode == 'live':
            → start_live_camera()     # 📹 Continuous
        else:  # TRIGGER mode
            → set_trigger_mode(True)  # Ensure trigger enabled
            → start_preview()         # Simple preview
            → lock_3a()               # Disable AE/AWB
    else:  # STOP camera
        → stop_preview() / stop_live()
```
