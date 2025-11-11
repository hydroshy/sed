# FRAME DISPLAY DEBUGGING GUIDE

## Problem Statement
Frames are successfully captured by the camera and are streaming (confirmed by debug logs showing `Execute job` commands), but **no images are displayed in the cameraView widget**.

## Root Cause Analysis (In Progress)

The frame display pipeline has many steps, and the issue could be at any step:
1. ✅ Camera captures frames successfully
2. ✅ Signal is emitted from camera stream
3. ❓ Signal received by camera_view's `display_frame()`
4. ❓ Frame added to worker queue
5. ❓ Worker thread processing frames
6. ❓ Worker converting frame to QImage
7. ❓ frameProcessed signal emitted
8. ❓ Main thread receiving frameProcessed signal
9. ❓ QImage displayed in graphics scene

## What I've Added for Debugging

I've added comprehensive console output logging to trace each step of the frame display pipeline.

### Debug Print Locations

#### 1. **Frame Reception** (`display_frame()` - GUI thread)
When camera stream emits a frame, this is called:

```python
DEBUG: [display_frame] Frame received: shape={shape}, worker={True/False}
```

- **shape**: Should show (height, width, channels) e.g. `(480, 640, 3)`
- **worker**: Should be `True` (if False, worker initialization failed)

If you see "worker=False", it means `camera_display_worker` is None/not initialized.

---

#### 2. **Worker Queue Management** (`CameraDisplayWorker.add_frame()` - GUI thread)
When frame is added to worker's processing queue:

```python
DEBUG: [CameraDisplayWorker.add_frame] Frame added to queue, size={size}
```

- **size**: Should be 1 (due to `frame_queue.clear()` before append)

---

#### 3. **Worker Initialization** (`_start_camera_display_worker()` - GUI thread)
During CameraView initialization:

```python
DEBUG: [_start_camera_display_worker] Starting worker, thread={None or obj}
DEBUG: [_start_camera_display_worker] Creating CameraDisplayWorker
DEBUG: [_start_camera_display_worker] Moving worker to thread
DEBUG: [_start_camera_display_worker] Connecting signals
DEBUG: [_start_camera_display_worker] Starting thread
DEBUG: [_start_camera_display_worker] Worker started successfully
```

or if error:
```python
DEBUG: [_start_camera_display_worker] ERROR: {exception message}
```

---

#### 4. **Worker Frame Processing** (`CameraDisplayWorker.process_frames()` - Worker thread)
Worker thread processing loop:

```python
DEBUG: [CameraDisplayWorker.process_frames] Worker thread started, running=True
DEBUG: [CameraDisplayWorker.process_frames] Processing frame, shape={shape}
DEBUG: [_process_frame_to_qimage] Processing with format: BGR888, shape=(480, 640, 3)
DEBUG: [_process_frame_to_qimage] Creating QImage: 640x480, channels=3
DEBUG: [_process_frame_to_qimage] QImage created successfully, isNull=False
DEBUG: [CameraDisplayWorker.process_frames] Emitting frameProcessed signal
```

or if error:
```python
DEBUG: [CameraDisplayWorker.process_frames] processed_qimage is None!
DEBUG: [_process_frame_to_qimage] ERROR: {exception}
```

---

#### 5. **Signal Handling** (`_handle_processed_frame()` - GUI thread)
Main thread receiving processed frame signal:

```python
DEBUG: [_handle_processed_frame] Received processed frame, qimage is None: False
DEBUG: [_handle_processed_frame] Calling _display_qimage
```

---

#### 6. **Display Rendering** (`_display_qimage()` - GUI thread)
Graphics scene update:

```python
DEBUG: [_display_qimage] Displaying QImage
DEBUG: [_display_qimage] Pixmap created, isNull=False, size=PyQt5.QtCore.QSize(640, 480)
DEBUG: [_display_qimage] Adding pixmap to scene
```

---

## How to Run and Capture Output

### Option 1: Run from PowerShell with output capture
```powershell
cd e:\PROJECT\sed
python main.py 2>&1 | Tee-Object -FilePath debug_output.txt
```

Then check `debug_output.txt` for the debug messages.

### Option 2: Run directly and watch console
```powershell
cd e:\PROJECT\sed
python main.py
```

Watch the console window for debug output as frames arrive.

### Option 3: Redirect to file
```powershell
cd e:\PROJECT\sed
python main.py > debug_output.log 2>&1
```

---

## Expected Output Sequence

### Startup (first few seconds):
```
DEBUG: [_start_camera_display_worker] Starting worker, thread=None
DEBUG: [_start_camera_display_worker] Creating CameraDisplayWorker
DEBUG: [_start_camera_display_worker] Moving worker to thread
DEBUG: [_start_camera_display_worker] Connecting signals
DEBUG: [_start_camera_display_worker] Starting thread
DEBUG: [_start_camera_display_worker] Worker started successfully
DEBUG: [CameraDisplayWorker.process_frames] Worker thread started, running=True
```

### When frames start arriving (continuous):
```
DEBUG: [display_frame] Frame received: shape=(480, 640, 3), worker=True
DEBUG: [display_frame] Adding frame to worker queue
DEBUG: [CameraDisplayWorker.add_frame] Frame added to queue, size=1
DEBUG: [CameraDisplayWorker.process_frames] Processing frame, shape=(480, 640, 3)
DEBUG: [_process_frame_to_qimage] Processing with format: BGR888, shape=(480, 640, 3)
DEBUG: [_process_frame_to_qimage] Creating QImage: 640x480, channels=3
DEBUG: [_process_frame_to_qimage] QImage created successfully, isNull=False
DEBUG: [CameraDisplayWorker.process_frames] Emitting frameProcessed signal
DEBUG: [_handle_processed_frame] Received processed frame, qimage is None: False
DEBUG: [_handle_processed_frame] Calling _display_qimage
DEBUG: [_display_qimage] Displaying QImage
DEBUG: [_display_qimage] Pixmap created, isNull=False, size=PyQt5.QtCore.QSize(640, 480)
DEBUG: [_display_qimage] Adding pixmap to scene
```

This pattern should repeat for each frame.

---

## Troubleshooting Guide

### Problem: No debug output appears at all
- Check if CameraView is actually being initialized
- Look for any error messages before debug output starts
- Verify that `_start_camera_display_worker()` is called during initialization

### Problem: "Frame received" appears but "Adding frame to worker queue" doesn't
- Worker is None (initialization failed)
- Look for error messages in `_start_camera_display_worker` section
- Worker might have crashed

### Problem: "Adding frame to worker queue" appears but "Processing frame" doesn't
- Worker thread is not running
- Check for thread-related errors
- Thread might have terminated

### Problem: "Processing frame" appears but "QImage created successfully" shows isNull=True or doesn't appear
- Frame conversion failed
- Look for "ERROR" messages in `_process_frame_to_qimage` section
- Check frame format/shape

### Problem: "Adding pixmap to scene" appears but still no image display
- Graphics view not rendering
- QGraphicsScene might be wrong
- Display widget might not be updated/refreshed

### Problem: "Worker is None! Thread: ... Running: False"
- Worker initialization failed OR worker was garbage collected
- Check error messages during startup
- Worker thread might be exiting immediately

---

## Next Action Items

1. **Run the application** with these debug logs active
2. **Capture the console output** (use one of the methods above)
3. **Send me the output** showing:
   - Whether "Worker started successfully" appears
   - Whether "Frame received" messages appear
   - Whether "Adding pixmap to scene" messages appear
   - Any ERROR messages

4. **Based on the output**, I can pinpoint exactly where frames are getting stuck

---

## Modified Files

- `gui/camera_view.py` - Added debug print statements throughout the frame display pipeline
- `FRAME_DISPLAY_DEBUGGING.md` - Documentation of debug locations
- `test_debug_markers.py` - Script to verify debug markers are in place

---

## Key Code Sections for Reference

### Frame Reception (Line 415+)
```python
def display_frame(self, frame):
    print(f"DEBUG: [display_frame] Frame received: shape={frame.shape}, worker={self.camera_display_worker is not None}")
    if self.camera_display_worker:
        print(f"DEBUG: [display_frame] Adding frame to worker queue")
        self.camera_display_worker.add_frame(frame)
    else:
        print(f"DEBUG: [display_frame] Worker is None!")
```

### Worker Initialization (Line 1609+)
```python
def _start_camera_display_worker(self):
    print(f"DEBUG: [_start_camera_display_worker] Starting worker...")
    # ... initialization code with debug prints ...
```

### Frame Processing (Line 93+)
```python
def process_frames(self):
    print(f"DEBUG: [CameraDisplayWorker.process_frames] Worker thread started...")
    # ... processing code with debug prints ...
```

### Display Update (Line 1697+)
```python
def _display_qimage(self, qimage):
    print(f"DEBUG: [_display_qimage] Displaying QImage")
    pixmap = QPixmap.fromImage(qimage)
    print(f"DEBUG: [_display_qimage] Pixmap created, isNull={pixmap.isNull()}")
    scene.addPixmap(pixmap)
    print(f"DEBUG: [_display_qimage] Adding pixmap to scene")
```
