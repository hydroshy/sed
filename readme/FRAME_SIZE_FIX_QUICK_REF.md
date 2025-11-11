# Frame Size Issue - Quick Reference

## What Was Wrong

✅ Code was configured to use **1280×720** for both LIVE and TRIGGER modes  
❌ But actual camera was capturing **480×640** (TRIGGER) and **1080×1440** (LIVE)

## Why It Happened

**Picamera2 doesn't reject unsupported frame sizes**—it silently picks the closest available size instead.

## What's Fixed Now

### Enhanced Logging
The camera stream now logs:
1. **What size was requested**
2. **What size camera is actually using**
3. **Mismatch warnings** if sizes differ between modes

### Example Log Output
```
Frame sizes - LIVE: (480, 640), TRIGGER: (480, 640)
Preview config: Requested (1280, 720), camera using (480, 640)
```

This immediately shows when camera can't support configured sizes.

## How to Test

1. **Run the application in LIVE or TRIGGER mode**
2. **Check the application logs** (should appear in console/log file)
3. **Look for lines like**:
   ```
   Frame sizes - LIVE: XXX, TRIGGER: YYY
   Preview config: Requested ...
   Still config: Requested ...
   ```
4. **Document the actual sizes** your camera uses

## Possible Outcomes

| Outcome | Logs Show | Next Action |
|---------|-----------|-------------|
| Success | LIVE and TRIGGER both use (1280, 720) | ✅ Done! Frame sizes matched |
| Fallback | Both modes using (480, 640) or (1080, 1440) | Document camera's actual sizes |
| Mixed | LIVE=(1080, 1440), TRIGGER=(480, 640) | Camera doesn't support unified sizes |

## If Sizes Don't Match

**This is NOT an error**—it's a camera hardware limitation:
- Your camera model may not support 1280×720
- Application will still work, just with camera's native sizes
- Frame quality will be based on what camera actually supports

## Code Changes

**File**: `camera/camera_stream.py`

**Method**: `_initialize_configs_with_sizes()`

Changes:
- ✅ Added diagnostic logging for frame sizes
- ✅ Enhanced fallback handling
- ✅ Added mismatch detection
- ✅ Added frame size summary at startup

## What To Do Next

### Immediate (Next Run)
1. Start application
2. Check logs for "Frame sizes" line
3. Note the actual sizes being used

### If Sizes Wrong
1. Check camera specs for supported resolutions
2. Consider using camera's native resolution
3. Or configure to use specific supported size

### If All Working
✅ Frame size diagnostics successfully implemented
✅ Camera using appropriate resolution
✅ Both modes synchronized (if applicable)

## Documentation Reference

**Full Details**: See `readme/FRAME_SIZE_DIAGNOSTICS.md`

**Technical Details**: See `camera/camera_stream.py` method `_initialize_configs_with_sizes()` (lines ~217-314)
