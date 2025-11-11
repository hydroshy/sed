# Frame Display Debugging - Complete Trace

## Problem
Frames are being captured by the camera successfully, but they are NOT being displayed in the cameraView widget.

## Debug Path Added

I've added comprehensive logging to trace the frame display pipeline:

### 1. **Frame Reception** (`display_frame` method - line 415+)
```
DEBUG: [display_frame] Frame received: shape={frame.shape}, worker={True/False}
DEBUG: [display_frame] Adding frame to worker queue
DEBUG: [display_frame] Worker is None! Thread: ..., Running: ...
```

**What it checks:**
- Is display_frame receiving frames from the signal?
- Is camera_display_worker initialized?
- If worker is None, why? (thread status)

---

### 2. **Worker Queue Management** (`add_frame` method - line 86+)
```
DEBUG: [CameraDisplayWorker.add_frame] Frame added to queue, size={queue_size}
```

**What it checks:**
- Are frames being added to the worker's queue?
- Queue size (should be 0 or 1 due to clear logic)

---

### 3. **Worker Thread Processing** (`process_frames` method - line 93+)
```
DEBUG: [CameraDisplayWorker.process_frames] Worker thread started, running=True
DEBUG: [CameraDisplayWorker.process_frames] Processing frame, shape={frame.shape}
DEBUG: [CameraDisplayWorker.process_frames] Emitting frameProcessed signal
DEBUG: [CameraDisplayWorker.process_frames] processed_qimage is None!
```

**What it checks:**
- Is worker thread actually running?
- Are frames being dequeued from the queue?
- Is _process_frame_to_qimage successfully converting frames to QImage?

---

### 4. **Worker Initialization** (`_start_camera_display_worker` method - line 1609+)
```
DEBUG: [_start_camera_display_worker] Starting worker, thread={thread_obj/None}
DEBUG: [_start_camera_display_worker] Worker already started, returning
DEBUG: [_start_camera_display_worker] Creating CameraDisplayWorker
DEBUG: [_start_camera_display_worker] Moving worker to thread
DEBUG: [_start_camera_display_worker] Connecting signals
DEBUG: [_start_camera_display_worker] Starting thread
DEBUG: [_start_camera_display_worker] Worker started successfully
DEBUG: [_start_camera_display_worker] ERROR: {exception}
```

**What it checks:**
- Is worker initialized on startup?
- Are signals properly connected?
- Is thread.start() being called?
- Are there any exceptions during startup?

---

### 5. **Signal Processing** (`_handle_processed_frame` method - line 1653+)
```
DEBUG: [_handle_processed_frame] Received processed frame, qimage is None: {True/False}
DEBUG: [_handle_processed_frame] Calling _display_qimage
DEBUG: [_handle_processed_frame] ERROR: {exception}
```

**What it checks:**
- Is the frameProcessed signal being received on the main thread?
- Is _handle_processed_frame being called?
- Are there exceptions in the handler?

---

### 6. **Display Rendering** (`_display_qimage` method - line 1697+)
```
DEBUG: [_display_qimage] Displaying QImage
DEBUG: [_display_qimage] Pixmap created, isNull={True/False}, size={QSize}
DEBUG: [_display_qimage] Pixmap is null, returning
DEBUG: [_display_qimage] Creating new graphics scene
DEBUG: [_display_qimage] Adding pixmap to scene
```

**What it checks:**
- Is QPixmap.fromImage successfully creating pixmaps?
- Is the graphics scene being created/updated?
- Is pixmap being added to scene?

---

### 7. **Fallback Path** (synchronous display if worker unavailable)
```
DEBUG: [display_frame] Worker is None! Thread: {thread_obj}, Running: {True/False}
```

**What it checks:**
- Is the fallback being used instead of the async worker?
- Why might the worker be None? (initialization failed?)

---

## How to Use This Debugging Info

When you run the application with these debug prints, look for:

1. **Missing "Frame received" messages?** → Signal connection might be broken
2. **"Frame added to queue" messages but no "Processing frame"?** → Worker thread not running
3. **"Processing frame" but "processed_qimage is None!"?** → Frame to QImage conversion failed  
4. **"Adding pixmap to scene" but still no display?** → Graphics view not updated
5. **"Worker is None!" messages?** → Initialization failed or worker was destroyed

---

## Expected Debug Sequence (Normal Operation)

```
DEBUG: [_start_camera_display_worker] Starting worker, thread=None
DEBUG: [_start_camera_display_worker] Creating CameraDisplayWorker
DEBUG: [_start_camera_display_worker] Moving worker to thread
DEBUG: [_start_camera_display_worker] Connecting signals
DEBUG: [_start_camera_display_worker] Starting thread
DEBUG: [_start_camera_display_worker] Worker started successfully
DEBUG: [CameraDisplayWorker.process_frames] Worker thread started, running=True

[When frame arrives...]
DEBUG: [display_frame] Frame received: shape=(480, 640, 3), worker=True
DEBUG: [display_frame] Adding frame to worker queue
DEBUG: [CameraDisplayWorker.add_frame] Frame added to queue, size=1
DEBUG: [CameraDisplayWorker.process_frames] Processing frame, shape=(480, 640, 3)
DEBUG: [CameraDisplayWorker.process_frames] Emitting frameProcessed signal
DEBUG: [_handle_processed_frame] Received processed frame, qimage is None: False
DEBUG: [_handle_processed_frame] Calling _display_qimage
DEBUG: [_display_qimage] Displaying QImage
DEBUG: [_display_qimage] Pixmap created, isNull=False, size=PyQt5.QtCore.QSize(640, 480)
DEBUG: [_display_qimage] Adding pixmap to scene
```

---

## Next Steps

1. Run the application and **capture the console output**
2. **Send the console output** showing what debug messages appear
3. Based on which debug messages appear (or don't appear), we can identify exactly where the frames are getting stuck

---

## Code Changes Made

- `display_frame()` - Added frame reception debugging
- `CameraDisplayWorker.add_frame()` - Added queue management debugging
- `CameraDisplayWorker.process_frames()` - Added thread/processing debugging
- `_start_camera_display_worker()` - Added initialization debugging
- `_handle_processed_frame()` - Added signal handling debugging
- `_display_qimage()` - Added display rendering debugging
