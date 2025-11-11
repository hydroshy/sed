# Fix: Frame Size Sync Between LIVE and TRIGGER Modes

## Problem Description
When switching from **LIVE mode** to **TRIGGER mode**, the frame size was not being synchronized. The application was receiving frames with size **1080x1440** (LIVE resolution) instead of **640x480** (TRIGGER resolution).

**Error Message Observed**:
```
DEBUG: [CameraDisplayWorker.process_frames] Processing frame, shape=(1080, 1440, 4)
```

Expected: `(480, 640, 3)` or `(640, 480, 3)` depending on format

## Root Cause
The issue occurred because:

1. **LIVE mode** used `preview_config` without explicitly defining frame size → defaulted to camera's full resolution
2. **TRIGGER mode** used `still_config` without frame size definition → inherited from previous config
3. When switching modes, frame size was NOT being reconfigured

The configurations were created without explicit `main.size` parameters:
```python
# OLD - No frame size specified
self.preview_config = self.picam2.create_preview_configuration(main={"format": "RGB888"})
self.still_config = self.picam2.create_still_configuration()
```

## Solution Implemented

### 1. New Helper Method: `_initialize_configs_with_sizes()`
Created a new method that explicitly sets frame sizes for each mode:

```python
def _initialize_configs_with_sizes(self):
    """Initialize preview_config and still_config with appropriate frame sizes
    
    LIVE mode: Uses larger frame (1280x720) for better quality
    TRIGGER mode: Uses smaller frame (640x480) for faster processing
    """
    # LIVE mode - 1280x720
    self.preview_config = self.picam2.create_preview_configuration(
        main={"size": (1280, 720), "format": "RGB888"}
    )
    
    # TRIGGER mode - 640x480
    self.still_config = self.picam2.create_still_configuration(
        main={"size": (640, 480), "format": "RGB888"}
    )
```

### 2. Updated `_safe_init_picamera()`
Now calls the new helper method during camera initialization:

```python
# Create default configurations with appropriate frame sizes
self._initialize_configs_with_sizes()
```

### 3. Updated `set_trigger_mode()`
Ensures when enabling trigger mode, frame size is explicitly set to 640x480:

```python
if enabled:
    logger.debug("Restarting camera in trigger mode")
    # Create still_config with trigger-specific frame size (640x480)
    try:
        self.still_config = self.picam2.create_still_configuration()
        if "main" not in self.still_config:
            self.still_config["main"] = {}
        self.still_config["main"]["size"] = (640, 480)  # Explicit size
        self.picam2.configure(self.still_config)
    except Exception as config_e:
        logger.warning(f"Failed to set trigger frame size: {config_e}")
        # Fallback to default still_config if size setting fails
```

### 4. Updated `trigger_capture()`
Ensures frame size is always 640x480 when capturing:

```python
# Ensure still config has correct frame size (640x480 for trigger)
if "main" not in self.still_config:
    self.still_config["main"] = {}
self.still_config["main"]["size"] = (640, 480)
logger.debug("Still config frame size set to 640x480")
```

## Frame Size Configuration

### LIVE Mode (preview_config)
- **Resolution**: 1280x720
- **Format**: RGB888
- **Use Case**: Continuous preview on GUI
- **Quality**: Higher (better for display)

### TRIGGER Mode (still_config)
- **Resolution**: 640x480
- **Format**: RGB888
- **Use Case**: Single frame capture for processing
- **Speed**: Faster processing time

## Testing Checklist

- [ ] Start app in LIVE mode → verify frame is 1280x720
- [ ] Switch to TRIGGER mode → verify frame is 640x480
- [ ] Capture image in TRIGGER mode → verify frame is 640x480
- [ ] Switch back to LIVE mode → verify frame is 1280x720
- [ ] Trigger capture while in LIVE mode → should use 640x480
- [ ] Check logs for proper frame size messages

## Expected Log Output

```
DEBUG: Still config created with size 640x480
DEBUG: Still config frame size set to 640x480
DEBUG: Camera configured with trigger mode frame size
```

## Performance Impact

- **Memory**: Smaller frames (640x480) use less memory
- **Processing**: TRIGGER frames process faster with smaller resolution
- **Quality**: LIVE mode benefits from larger frame size
- **Latency**: TRIGGER mode has reduced latency with smaller frames

## Files Modified

- `camera/camera_stream.py`:
  - Added `_initialize_configs_with_sizes()` method (lines ~187-235)
  - Updated `_safe_init_picamera()` to call helper method
  - Updated `set_trigger_mode()` to explicitly set 640x480
  - Updated `trigger_capture()` to enforce 640x480

## Backwards Compatibility

- ✅ No API changes
- ✅ No new dependencies
- ✅ Fallback to defaults if size setting fails
- ✅ Works with existing camera configurations

## Future Improvements

1. Make frame sizes configurable via settings
2. Add resolution presets (640x480, 1280x720, 1920x1080, etc.)
3. Adaptive frame size based on CPU usage
4. Per-mode frame rate optimization

---

**Status**: ✅ IMPLEMENTED  
**Date**: Phase 1 Optimization Continuation  
**Tested**: To be validated in testing phase
