# ✅ Frame Size Fix - Verification Guide

## Quick Check

### Method 1: Check Logs During Startup

1. Start application
2. Look for these messages in console:

```
DEBUG: [CameraStream] Preview config created with size 1280x720
DEBUG: [CameraStream] Still config created with size 640x480
DEBUG: [CameraStream] Camera configured for preview
DEBUG: [CameraStream] Live view started successfully
```

✅ If you see these → LIVE mode is correctly initialized with 1280x720

### Method 2: Switch to TRIGGER Mode

1. Click TRIGGER mode button
2. Look for:

```
DEBUG: [CameraStream] Restarting camera in trigger mode
DEBUG: [CameraStream] Still config created with frame size 640x480
DEBUG: [CameraStream] Camera configured with trigger mode frame size
```

✅ If you see these → TRIGGER mode is correctly set to 640x480

### Method 3: Capture Frame

1. In TRIGGER mode, click "Capture"
2. Check log for frame shape:

```
DEBUG: [CameraDisplayWorker.process_frames] Processing frame, shape=(640, 480, 3)
```

✅ If you see `(640, 480, 3)` → Frame size is CORRECT!
❌ If you see `(1080, 1440, ...)` → Frame size is WRONG

## Full Test Scenario

### Test Case 1: LIVE Mode Startup

| Step | Action | Expected Log | Status |
|------|--------|--------------|--------|
| 1 | Start app | `Preview config created with size 1280x720` | ✅/❌ |
| 2 | Wait for frame | `shape=(1280, 720, ...)` or similar height | ✅/❌ |
| 3 | Live stream | Continuous frames at 1280x720 | ✅/❌ |

### Test Case 2: Switch to TRIGGER Mode

| Step | Action | Expected Log | Status |
|------|--------|--------------|--------|
| 1 | Click TRIGGER | `Still config created with frame size 640x480` | ✅/❌ |
| 2 | Wait for config | `Camera configured with trigger mode frame size` | ✅/❌ |
| 3 | Check frame | `shape=(640, 480, ...)` | ✅/❌ |

### Test Case 3: Capture in TRIGGER Mode

| Step | Action | Expected Log | Status |
|------|--------|--------------|--------|
| 1 | Click Capture | Frame capture starts | ✅/❌ |
| 2 | Wait completion | `Still config frame size set to 640x480` | ✅/❌ |
| 3 | Process frame | `Processing frame, shape=(640, 480, 3)` | ✅/❌ |

### Test Case 4: Return to LIVE Mode

| Step | Action | Expected Log | Status |
|------|--------|--------------|--------|
| 1 | Click LIVE | Camera reconfigures | ✅/❌ |
| 2 | Wait for frame | Frame should go back to 1280x720 | ✅/❌ |
| 3 | Continuous stream | Larger frames again | ✅/❌ |

## Expected Frame Shapes by Mode

### LIVE Mode
- **Height**: ~1440 or ~720 (depending on camera support)
- **Width**: ~1920 or ~1280
- **Channels**: 3 (RGB) or 4 (RGBA)
- **Example**: `shape=(1280, 720, 3)` or `shape=(1440, 1920, 3)`

### TRIGGER Mode
- **Height**: 480
- **Width**: 640
- **Channels**: 3 (RGB) or 4 (RGBA)
- **Example**: `shape=(640, 480, 3)` or `shape=(480, 640, 3)`

## Debug Commands

### Check Frame Size Programmatically

If you want to verify frame size from code:

```python
# In LIVE mode
frame = camera_stream.get_latest_frame()
if frame is not None:
    print(f"LIVE frame shape: {frame.shape}")
    # Expected: (1280, 720, 3) or similar

# In TRIGGER mode  
camera_stream.trigger_capture()
frame = camera_stream.get_latest_frame()
if frame is not None:
    print(f"TRIGGER frame shape: {frame.shape}")
    # Expected: (640, 480, 3)
```

## Troubleshooting

### Issue: Still seeing (1080, 1440, ...) in TRIGGER mode

**Cause**: Camera didn't reconfigure properly

**Solution**:
1. Check logs for errors in `set_trigger_mode`
2. Try restarting the application
3. Verify camera hardware is responsive

### Issue: Configuration fails with "Cannot use 640x480"

**Cause**: Camera doesn't support 640x480 resolution

**Solution**:
1. Check camera capabilities
2. Use fallback resolution
3. Log shows warning: `Failed to set trigger frame size`

### Issue: LIVE mode also shows 640x480

**Cause**: `_initialize_configs_with_sizes()` wasn't called

**Solution**:
1. Restart application
2. Check logs for initialization messages
3. Verify `preview_config` is being created

## Performance Verification

### Expected Performance Gains

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Frame Memory | 6.2 MB | 1.2 MB | **80% reduction** |
| Processing Time | ~100ms | ~25ms | **4x faster** |
| Data Transfer | ~6MB/frame | ~1.2MB/frame | **80% reduction** |

### How to Measure

Use Python timing:

```python
import time

# Measure TRIGGER frame processing
start = time.time()
camera_stream.trigger_capture()
# Process frame...
elapsed = time.time() - start
print(f"Processing time: {elapsed*1000:.1f}ms")
```

Expected: < 50ms for 640x480

## Log Analysis

### Good Logs (Expected)

```
INFO: Camera initialized successfully
DEBUG: Preview config created with size 1280x720
DEBUG: Still config created with size 640x480
DEBUG: Camera configured for preview
INFO: Live view started successfully
DEBUG: Restarting camera in trigger mode
DEBUG: Still config created with frame size 640x480
DEBUG: Camera configured with trigger mode frame size
DEBUG: Still config frame size set to 640x480
INFO: Processing frame, shape=(640, 480, 3)
```

### Bad Logs (Indicates Problem)

```
ERROR: Failed to set trigger frame size
WARNING: Cannot use 640x480, using default
ERROR: Error initializing configs with sizes
```

If you see errors, check:
1. Camera is connected and responsive
2. Required permissions for camera access
3. Picamera2 library is up to date

## Success Criteria

✅ **PASSED** if all the following are true:

- [ ] Preview config shows 1280x720 on startup
- [ ] Still config shows 640x480 on startup
- [ ] LIVE mode frames are ~1280×720
- [ ] TRIGGER mode frames are 640×480
- [ ] Mode switching takes 1-2 seconds
- [ ] Capture completes within 5 seconds
- [ ] No error messages in logs
- [ ] Application remains responsive

## Reporting Results

If something doesn't work as expected, please report:

1. **Frame sizes observed**
2. **Log messages from startup**
3. **Mode switch logs**
4. **Expected vs actual frame shape**
5. **Any error messages**

Example report:
```
LIVE mode:
  - Expected: 1280x720
  - Actual: 1920x1080
  - Issue: Frame size larger than expected

TRIGGER mode:
  - Expected: 640x480
  - Actual: 640x480
  - Status: ✅ CORRECT
```

---

**Verification Date**: After Frame Size Fix Implementation
**Status**: Ready for Testing

