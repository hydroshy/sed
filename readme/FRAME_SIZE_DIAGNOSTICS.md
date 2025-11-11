# Frame Size Diagnostics & Fallback Strategy

## Problem Discovered

When testing with real Picamera2 hardware, the configured frame size (1280×720) was not being applied to the camera. Instead, the camera was capturing:
- **TRIGGER mode**: 480×640 (not 1280×720)
- **LIVE mode**: 1080×1440 (not 1280×720)

## Root Cause

**Picamera2 silently falls back to camera's native/default sizes when requested size is not supported.**

This means:
- The camera hardware has built-in supported resolutions
- 1280×720 may not be one of them
- When requesting unsupported size, Picamera2 selects the closest available size
- No exception is raised—configuration "succeeds" but with different size

## Solution Implemented

### 1. Enhanced Diagnostic Logging

Updated `_initialize_configs_with_sizes()` in `camera/camera_stream.py` to:

```python
# Try with preferred size - picamera2 will handle if not supported
self.preview_config = self.picam2.create_preview_configuration(
    main={"size": preferred_size, "format": "RGB888"}
)
actual_size = self.preview_config.get("main", {}).get("size")

# Check if camera actually accepted our request
if actual_size and actual_size != preferred_size:
    logger.warning(
        f"Preview config: Requested {preferred_size}, "
        f"camera using {actual_size} (camera may not support requested size)"
    )
```

**What this reveals**:
- Logs show both requested AND actual frame sizes
- Makes size mismatch immediately visible in logs
- Shows when camera doesn't support configured resolution

### 2. Graceful Fallback Strategy

Three-level fallback system in config creation:

```
LEVEL 1: Try preferred size (1280×720)
    ↓ (if fails or returns different size)
LEVEL 2: Use camera's default size (no size parameter)
    ↓ (if fails)
LEVEL 3: Use bare default config (completely minimal)
```

Each level logs what size was actually selected.

### 3. Frame Size Mismatch Detection

After both configs initialized, code checks:

```python
preview_size = self.preview_config.get("main", {}).get("size")
still_size = self.still_config.get("main", {}).get("size")

if preview_size != still_size:
    logger.warning(
        f"Frame size mismatch: LIVE uses {preview_size}, TRIGGER uses {still_size}. "
        f"This camera may not support unified frame sizes."
    )
```

This explicitly reports if LIVE and TRIGGER modes have different frame sizes.

### 4. Camera Capabilities Query

New helper method `_get_camera_supported_sizes()` attempts to query camera properties:

```python
def _get_camera_supported_sizes(self):
    """Query camera for actually supported frame sizes"""
    try:
        props = self.picam2.camera_properties
        if props and "PixelArrayActiveAreas" in props:
            # Extract dimensions from PixelArrayActiveAreas
            active_areas = props["PixelArrayActiveAreas"]
            width = active_areas[0][2]
            height = active_areas[0][3]
            logger.info(f"Camera active area: {width}×{height}")
            return {"width": width, "height": height}
    except Exception as e:
        logger.debug(f"Error querying camera supported sizes: {e}")
```

(Can be extended to handle other camera property queries)

## Testing & Debugging

### To verify the fix works:

1. **Run application with LIVE mode**
   - Check logs for: `Frame sizes - LIVE: XXX, TRIGGER: XXX`
   - Should show actual sizes being used

2. **Monitor startup logs**
   - Look for "Preview config" and "Still config" messages
   - These show what size was requested vs actual
   - Example:
     ```
     Preview config: Requested (1280, 720), camera using (480, 640)
     ```

3. **Check for mismatch warnings**
   - If you see: `Frame size mismatch: LIVE uses X, TRIGGER uses Y`
   - This means camera doesn't support unified frame sizes
   - Application will still work, but sizes differ per mode

### Expected Log Output Examples

**Scenario A: Camera supports 1280×720**
```
Preview config: Successfully set to (1280, 720)
Still config: Successfully set to (1280, 720)
Frame sizes - LIVE: (1280, 720), TRIGGER: (1280, 720)
```

**Scenario B: Camera doesn't support 1280×720 (falls back)**
```
Preview config: Requested (1280, 720), camera using (480, 640) (camera may not support requested size)
Still config: Requested (1280, 720), camera using (480, 640) (camera may not support requested size)
Frame sizes - LIVE: (480, 640), TRIGGER: (480, 640)
```

**Scenario C: Camera forces different sizes (hardware limitation)**
```
Preview config: Requested (1280, 720), camera using (1080, 1440)
Still config: Requested (1280, 720), camera using (480, 640)
Frame sizes - LIVE: (1080, 1440), TRIGGER: (480, 640)
Frame size mismatch: LIVE uses (1080, 1440), TRIGGER uses (480, 640). This camera may not support unified frame sizes.
```

## Next Steps for User

1. **Run application and check logs** - Determine what frame sizes your camera actually supports
2. **If all logs show same size** - Success! ✅ Frame sizes are now properly detected and logged
3. **If logs show different sizes** - Document the supported sizes and decide:
   - Option A: Accept camera defaults (simplest)
   - Option B: Configure to use specific supported size
   - Option C: Use different sizes per mode

## Code Location

**File**: `e:\PROJECT\sed\camera\camera_stream.py`

**Method**: `_initialize_configs_with_sizes()` (lines ~217-314)

**Helper Method**: `_get_camera_supported_sizes()` (lines ~189-215)

## Related Files

- `camera/camera_stream.py` - Main camera stream management
- Logs show frame sizes in: `camera_stream.start()` method
- Frame size validation happening in: `_initialize_configs_with_sizes()`

## Summary

The frame size configuration now has:
- ✅ **Explicit logging** showing requested vs actual sizes
- ✅ **Fallback strategy** for graceful degradation
- ✅ **Mismatch detection** warning if LIVE ≠ TRIGGER sizes
- ✅ **Size query capability** to identify camera limits
- ✅ **No exceptions** - continues working even if size not supported

This allows diagnosis of camera-specific limitations while maintaining application stability.
