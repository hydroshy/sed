# Complete Frame Display Pipeline - Line Reference

## Frame Flow with Exact Line Numbers

```
┌─ FRAME ARRIVES (from camera)
│  File: camera/camera_stream.py
│  └─ _LiveWorker.run() (line ~60)
│     └─ picam2.capture_array() → frame captured
│        └─ self.frame_ready.emit(frame) (line ~72)
│
└─ SIGNAL PROPAGATION
   File: gui/camera_manager.py
   └─ Signal connection (line 164):
      self.camera_stream.frame_ready.connect(self.camera_view.display_frame)
      
└─ FRAME RECEPTION ✅ DEBUG HERE
   File: gui/camera_view.py
   └─ display_frame(frame) (line 415+)
      DEBUG: [display_frame] Frame received: shape={shape}, worker={True/False}
      │
      ├─ Check if camera_display_worker exists
      │  DEBUG: [display_frame] Adding frame to worker queue
      │  │
      │  └─ camera_display_worker.add_frame(frame) (line ~430)
      │     └─ CameraDisplayWorker.add_frame() (line 86+)
      │        DEBUG: [CameraDisplayWorker.add_frame] Frame added to queue, size={size}
      │        └─ frame_queue.append(frame.copy())
      │
      └─ [FALLBACK] If worker is None:
         DEBUG: [display_frame] Worker is None! Thread: ..., Running: ...
         └─ _display_frame_sync(frame) (line 458)
```

---

## Worker Thread Processing (Background)

```
File: gui/camera_view.py

INITIALIZATION (GUI thread):
└─ CameraView.__init__()
   └─ _start_camera_display_worker() (line 1609+)
      DEBUG: [_start_camera_display_worker] Starting worker...
      │
      ├─ Create CameraDisplayWorker (line 1617)
      │  DEBUG: [_start_camera_display_worker] Creating CameraDisplayWorker
      │
      ├─ Create QThread (line 1618)
      ├─ moveToThread() (line 1621)
      │  DEBUG: [_start_camera_display_worker] Moving worker to thread
      │
      ├─ Connect signals (line 1624-1625)
      │  DEBUG: [_start_camera_display_worker] Connecting signals
      │  └─ thread.started → worker.process_frames()
      │  └─ worker.frameProcessed → view._handle_processed_frame()
      │
      └─ thread.start() (line 1628)
         DEBUG: [_start_camera_display_worker] Starting thread
         DEBUG: [_start_camera_display_worker] Worker started successfully

PROCESSING (Worker thread):
└─ [thread.started signal triggers]
   └─ CameraDisplayWorker.process_frames() (line 93+)
      DEBUG: [CameraDisplayWorker.process_frames] Worker thread started, running=True
      │
      ├─ Loop: while self.running (line 96)
      │
      ├─ Dequeue frame (line 99-102)
      │
      ├─ If frame available:
      │  DEBUG: [CameraDisplayWorker.process_frames] Processing frame, shape={shape}
      │  │
      │  └─ _process_frame_to_qimage(frame) (line 105)
      │     └─ CameraDisplayWorker._process_frame_to_qimage() (line 122+)
      │        DEBUG: [_process_frame_to_qimage] Processing with format: {format}
      │        DEBUG: [_process_frame_to_qimage] Creating QImage: {w}x{h}
      │        DEBUG: [_process_frame_to_qimage] QImage created successfully, isNull={False}
      │        │
      │        └─ Frame color conversion (BGR→RGB)
      │           └─ cv2.cvtColor() conversions
      │        
      │        └─ Return: qimage.copy(), frame_for_history.copy()
      │
      └─ If qimage not None:
         DEBUG: [CameraDisplayWorker.process_frames] Emitting frameProcessed signal
         └─ self.frameProcessed.emit(qimage, frame_for_history) (line 108)
            └─ Signal emitted to main thread
```

---

## Main Thread Signal Handling (GUI Thread)

```
File: gui/camera_view.py

SIGNAL RECEPTION:
└─ [frameProcessed signal received on main thread]
   └─ _handle_processed_frame(qimage, frame_for_history) (line 1653+)
      DEBUG: [_handle_processed_frame] Received processed frame, qimage is None: {False}
      │
      ├─ Store frame for internal use (line 1659)
      │  self.current_frame = frame_for_history
      │
      ├─ Store last valid QImage (line 1662)
      │  self.last_valid_qimage = qimage
      │
      └─ Call display method:
         DEBUG: [_handle_processed_frame] Calling _display_qimage
         └─ _display_qimage(qimage) (line 1687)

DISPLAY RENDERING:
└─ _display_qimage(qimage) (line 1699+)
   DEBUG: [_display_qimage] Displaying QImage
   │
   ├─ Create pixmap (line 1704)
   │  pixmap = QPixmap.fromImage(qimage)
   │  DEBUG: [_display_qimage] Pixmap created, isNull={False}, size={QSize}
   │
   ├─ Get graphics scene (line 1709)
   │  scene = self.graphics_view.scene()
   │
   ├─ Clear scene (line 1713)
   │  scene.clear()
   │
   ├─ Add pixmap to scene (line 1716)
   │  scene.addPixmap(pixmap)
   │  DEBUG: [_display_qimage] Adding pixmap to scene
   │
   └─ Apply transforms (zoom, rotation)
      ✅ IMAGE SHOULD NOW APPEAR IN CAMERA VIEW
```

---

## Debug Checkpoint Markers

### During Startup
```
Frame 1: 0.0s  - _start_camera_display_worker: Starting...
Frame 2: 0.1s  - _start_camera_display_worker: Creating CameraDisplayWorker
Frame 3: 0.2s  - _start_camera_display_worker: Starting thread
Frame 4: 0.3s  - _start_camera_display_worker: Worker started successfully
Frame 5: 0.4s  - process_frames: Worker thread started, running=True
```

### During Frame Reception (Repeating)
```
Frame N:    X.Xs  - display_frame: Frame received: shape=(480, 640, 3)
Frame N+1:  X.Xs  - CameraDisplayWorker.add_frame: Frame added to queue, size=1
Frame N+2:  X.Xs  - process_frames: Processing frame
Frame N+3:  X.Xs  - _process_frame_to_qimage: Creating QImage
Frame N+4:  X.Xs  - _process_frame_to_qimage: QImage created successfully
Frame N+5:  X.Xs  - process_frames: Emitting frameProcessed signal
Frame N+6:  X.Xs  - _handle_processed_frame: Received processed frame
Frame N+7:  X.Xs  - _display_qimage: Displaying QImage
Frame N+8:  X.Xs  - _display_qimage: Adding pixmap to scene
```

---

## Error States to Look For

### Error 1: Worker Not Created
```
DEBUG: [_start_camera_display_worker] ERROR: ...
DEBUG: [display_frame] Worker is None! 
→ Worker initialization failed
```

### Error 2: QImage Creation Failed
```
DEBUG: [_process_frame_to_qimage] ERROR: ...
DEBUG: [_process_frame_to_qimage] Unsupported format: ...
→ Frame conversion failed
```

### Error 3: Signal Not Received
```
[display_frame messages but no _handle_processed_frame messages]
→ frameProcessed signal not connected or not working
```

### Error 4: Scene Not Updated
```
DEBUG: [_display_qimage] Adding pixmap to scene
[But no image appears in GUI]
→ Graphics view not rendering scene
```

---

## Complete Signal Chain

```
CameraStream.frame_ready
    ↓ [Signal Connection at camera_manager.py:164]
CameraView.display_frame()
    ↓ [Call] 
CameraDisplayWorker.add_frame()
    ↓ [Queue]
CameraDisplayWorker.process_frames() [Background Thread]
    ↓ [Process]
CameraDisplayWorker._process_frame_to_qimage()
    ↓ [Convert]
CameraDisplayWorker.frameProcessed.emit()
    ↓ [Signal to Main Thread]
CameraView._handle_processed_frame()
    ↓ [Call]
CameraView._display_qimage()
    ↓ [Render]
QGraphicsScene.addPixmap()
    ↓ [Display]
QGraphicsView (Graphics Widget in GUI)
    ↓ [Show]
USER SEES IMAGE
```

---

## How to Trace a Specific Problem

### Problem: No image appears
**Step 1**: Check for "Worker started successfully"
- NO → Worker initialization failed (see Error 1)
- YES → Continue to Step 2

**Step 2**: Check for "Frame received" messages
- NO → Signal not connected or camera not streaming (verify with camera logs)
- YES → Continue to Step 3

**Step 3**: Check for "QImage created successfully, isNull=False"
- NO → Frame conversion failing (see Error 2)
- YES → Continue to Step 4

**Step 4**: Check for "Adding pixmap to scene"
- NO → Signal not reaching main thread (see Error 3)
- YES → Graphics view not rendering (see Error 4)

---

## Performance Notes

Each debug print adds small overhead, but negligible:
- String formatting: ~0.1ms per print
- Total per frame: ~10-20 debug prints = 1-2ms overhead
- Display rate: ~10 FPS base → ~9.8 FPS with debugging
- Acceptable for diagnostic purposes

---

## Files and Functions Summary

| File | Function | Line | Debug Points |
|------|----------|------|-------------| 
| camera_view.py | display_frame | 415 | Frame received |
| camera_view.py | CameraDisplayWorker.add_frame | 86 | Queue added |
| camera_view.py | process_frames | 93 | Thread start |
| camera_view.py | _process_frame_to_qimage | 122 | Conversion |
| camera_view.py | _start_camera_display_worker | 1609 | Initialization |
| camera_view.py | _handle_processed_frame | 1653 | Signal handling |
| camera_view.py | _display_qimage | 1699 | Display rendering |
