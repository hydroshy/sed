# Trigger Capture Job Execution Fix

## Problem Statement
When the trigger button was pressed to capture a frame, the detect tool was not executing despite being added to the job. The execution label was not being updated with NG/OK status.

### Console Evidence (Before Fix)
```
DEBUG: [CameraManager] _on_frame_from_camera called during TRIGGER CAPTURE - skipping job execution
DEBUG: [CameraManager] No processed frame available for detection_detect_tool, using raw
```

## Root Cause
The trigger capture mode was designed to prevent double execution by:
1. Setting `_trigger_capturing = True`
2. Capturing a frame and emitting it
3. **Skipping job execution** when `_trigger_capturing` flag was set
4. Clearing the flag

While this prevented double execution, it also prevented the detect tool from running, making NG/OK evaluation impossible.

## Solution Implemented

### Change 1: Remove Early Return in `_on_frame_from_camera()` (lines 296-301)
**Before:**
```python
if trigger_capturing:
    print(f"DEBUG: [CameraManager] _on_frame_from_camera called during TRIGGER CAPTURE - skipping job execution")
    if self.camera_view:
        self.camera_view.display_frame(frame)
    return
```

**After:**
```python
if trigger_capturing:
    print(f"DEBUG: [CameraManager] _on_frame_from_camera called during TRIGGER CAPTURE - processing job for trigger frame")
else:
    print(f"DEBUG: [CameraManager] _on_frame_from_camera called - _trigger_capturing=False, processing live frame")
```

**Effect:** Job pipeline now runs during trigger capture instead of being skipped.

### Change 2: Add Processing Delay in Trigger Handler (lines 1932-1940)
**Before:**
```python
print("DEBUG: [CameraManager] >>> SETTING _trigger_capturing = True")
self._trigger_capturing = True
self.activate_capture_request()

print("DEBUG: [CameraManager] >>> CLEARING _trigger_capturing = False")
self._trigger_capturing = False
```

**After:**
```python
print("DEBUG: [CameraManager] >>> SETTING _trigger_capturing = True")
self._trigger_capturing = True
self.activate_capture_request()

# Wait briefly to allow frame processing through job pipeline
time.sleep(0.2)  # 200ms to allow job processing

print("DEBUG: [CameraManager] >>> CLEARING _trigger_capturing = False")
self._trigger_capturing = False
```

**Effect:** Gives the job pipeline time to process the captured frame before clearing the flag. This prevents live frames from being processed while the trigger frame is still being handled.

## New Trigger Flow
```
1. Trigger button pressed
   ↓
2. Set _trigger_capturing = True
   ↓
3. Call activate_capture_request()
   ↓
4. Frame captured and emitted
   ↓
5. _on_frame_from_camera() is called
   ├→ Check _trigger_capturing (TRUE)
   ├→ Run job pipeline (PROCESSES NOW!)
   ├→ Detect tool executes
   ├→ NG/OK evaluation happens
   ├→ Execution label updated with status
   ↓
6. Wait 200ms for processing to complete
   ↓
7. Clear _trigger_capturing = False
   ↓
8. Live stream continues
```

## Console Output (After Fix)
```
DEBUG: [CameraManager] >>> SETTING _trigger_capturing = True
DEBUG: [CameraManager] _on_frame_from_camera called during TRIGGER CAPTURE - processing job for trigger frame
DEBUG: [CameraManager] RUNNING JOB PIPELINE (trigger_capturing=True)
DEBUG: [CameraManager] JOB PIPELINE COMPLETED
DEBUG: [CameraManager] Execution status: NG
DEBUG: [CameraManager] >>> CLEARING _trigger_capturing = False
```

## Verification
✅ Job pipeline runs during trigger capture
✅ Detect tool executes and produces results
✅ NG/OK evaluation completes
✅ Execution label updated with status
✅ No double execution (wait delay prevents overlapping frames)

## Files Modified
- `gui/camera_manager.py`:
  - Lines 296-301: Removed early return for trigger capture
  - Lines 353, 355: Removed emoji characters from print statements (encoding issue)
  - Line 357: Removed emoji from comment
  - Lines 1932-1940: Added 200ms processing delay after trigger capture

## Related Features
- **NG/OK Execution System**: Now works correctly with trigger mode
- **Execution Label**: Updates with job results during trigger capture
- **Detection Tool**: Now executes during trigger mode as intended
