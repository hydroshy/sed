# FIX: 4-Channel Frame Conversion in CameraTool + Camera Start Live

## Vấn Đề Mới: 4-Channel Frame Detection Error

```
ValueError: could not broadcast input array from shape (480,640,4) into shape (480,640,3)
```

**Root Cause**: 
- Camera stream output: XRGB8888 (4-channel)
- DetectTool nhận: 4-channel frame
- DetectTool chỉ support: 3-channel
- CameraTool không convert 4ch → 3ch

### Giải Pháp:

Thêm 4-channel conversion trong CameraTool.process():

```python
# NEW: Convert 4-channel to 3-channel
if current_frame.shape[2] == 4:
    if pixel_format in ('RGB888', 'XRGB8888'):
        current_frame = cv2.cvtColor(current_frame, cv2.COLOR_BGRA2RGB)
    elif pixel_format in ('BGR888', 'XBGR8888'):
        current_frame = cv2.cvtColor(current_frame, cv2.COLOR_RGBA2BGR)
```

Result: Frame becomes (480, 640, 3) for DetectTool ✅

---

# Fix Camera Start Live Streaming (Original)

## Problem Found

The camera manager was trying to pass an invalid parameter to `CameraStream.start_live()`:

```
DEBUG: [CameraManager] Exception starting live camera: CameraStream.start_live() got an unexpected keyword argument 'preserve_trigger_mode'
```

## Root Cause

In `gui/camera_manager.py`, the code was attempting to call:
```python
success = self.camera_stream.start_live(preserve_trigger_mode=True)
```

However, the actual method signature in `camera/camera_stream.py` is:
```python
def start_live(self):
    """Start live view from camera or stub generator when hardware unavailable"""
```

The method does **not** accept any parameters.

## Changes Made

### File: `gui/camera_manager.py`

**Location 1 (Line 1602-1608):**
- Removed: Conditional check for `preserve_trigger_mode` parameter
- Removed: Attempt to pass `preserve_trigger_mode=True` argument
- Changed to: Simple `self.camera_stream.start_live()` call

**Location 2 (Line 1739-1747):**
- Removed: Unused `preserve_trigger_mode = editing_camera_tool` variable
- Removed: Complex parameter checking with `inspect.signature()`
- Changed to: Simple `self.camera_stream.start_live()` call

## Result

✅ Camera manager now correctly calls `start_live()` without invalid parameters

✅ No more "unexpected keyword argument" errors

✅ Camera will start successfully when switching to Camera Source tool

## Testing

The camera should now start properly when:
1. Adding Camera Source tool
2. Editing Camera Source settings
3. Any other mode that requires camera preview

No behavior changes - just fixed the parameter passing error.
