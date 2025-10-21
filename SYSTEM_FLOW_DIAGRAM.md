# 🔄 TCP AUTO-TRIGGER CAMERA - SYSTEM FLOW

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SENSOR DEVICE (IMX296)                        │
│                    192.168.1.190:4000                            │
│                                                                   │
│  - GPIO trigger input                                            │
│  - Sends: "start_rising||2075314"                               │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ TCP Stream
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────┐
│              TCP CONTROLLER (socket/recv)                        │
│              controller/tcp_controller.py                        │
│                                                                   │
│  1. Receive raw bytes: b'start_rising||2075314\n'               │
│  2. Decode UTF-8: 'start_rising||2075314'                       │
│  3. Split by newlines (fixed in Phase 1)                        │
│  4. Emit signal: message_received.emit('start_rising||2075314') │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ PyQt5 Signal
                 │
                 ↓
┌─────────────────────────────────────────────────────────────────┐
│         TCP CONTROLLER MANAGER                                   │
│         gui/tcp_controller_manager.py                            │
│                                                                   │
│  Signal Connected: message_received                             │
│  Slot Called: _on_message_received(message)                    │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ├─→ Display in message list
                 │   "RX: start_rising||2075314"
                 │
                 └─→ Call: _check_and_trigger_camera_if_needed()
                          │
                          ├─ CHECK 1: "start_rising" in message?
                          │            YES ✅ → Continue
                          │            NO  ❌ → Return
                          │
                          ├─ CHECK 2: camera_manager exists?
                          │            YES ✅ → Continue
                          │            NO  ❌ → Return
                          │
                          ├─ CHECK 3: camera_manager.current_mode == 'trigger'?
                          │            YES ✅ → Continue
                          │            NO  ❌ → Return (user in live mode)
                          │
                          └─→ TRIGGER: camera_manager.activate_capture_request()
                                       │
                                       ↓
                         ┌─────────────────────────────┐
                         │    CAMERA MANAGER           │
                         │  gui/camera_manager.py      │
                         │                             │
                         │  current_mode = 'trigger'  │
                         │  activate_capture_request() │
                         │         ↓                   │
                         │  camera_stream             │
                         │  .request_frame()          │
                         └────────────┬────────────────┘
                                      │
                                      ↓
                         ┌─────────────────────────────┐
                         │    CAMERA STREAM            │
                         │  camera/camera_stream.py    │
                         │                             │
                         │  Capture single frame       │
                         │  (In trigger mode)          │
                         └────────────┬────────────────┘
                                      │
                                      ↓
                         ┌─────────────────────────────┐
                         │   📸 FRAME CAPTURED         │
                         │   1456x1088 raw image       │
                         │   (PISP compressed)         │
                         └────────────┬────────────────┘
                                      │
                                      ↓ (if job enabled)
                         ┌─────────────────────────────┐
                         │   JOB PIPELINE              │
                         │  job/job_manager.py         │
                         │                             │
                         │  1. Detection (YOLO/etc)   │
                         │  2. Classification         │
                         │  3. Storage/Display         │
                         └────────────┬────────────────┘
                                      │
                                      ↓
                         ┌─────────────────────────────┐
                         │   📊 RESULTS DISPLAY        │
                         │   - Bboxes                  │
                         │   - Labels                  │
                         │   - Confidence scores       │
                         └─────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                    UI FEEDBACK (Synchronous)                     │
│                                                                   │
│  Message List Updates:                                          │
│  ├─ "RX: start_rising||2075314"                                 │
│  └─ "[TRIGGER] Camera captured from: start_rising||2075314"     │
│                                                                   │
│  Status Label: "Camera triggered"                               │
│                                                                   │
│  Console Logs:                                                  │
│  ├─ "★ Detected trigger command: start_rising||2075314"        │
│  ├─ "★ Camera is in trigger mode"                              │
│  └─ "✓ Camera triggered successfully"                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Decision Tree

```
Message Received: "start_rising||2075314"
│
├─ PARSE: Contains "start_rising"?
│  │
│  ├─ NO → [DEBUG] Not a trigger command → SKIP
│  │
│  └─ YES ↓
│
├─ CHECK: camera_manager exists?
│  │
│  ├─ NO → [WARNING] camera_manager not found → SKIP
│  │
│  └─ YES ↓
│
├─ CHECK: current_mode attribute exists?
│  │
│  ├─ NO → [WARNING] current_mode not found → SKIP
│  │
│  └─ YES ↓
│
├─ CHECK: current_mode == 'trigger'?
│  │
│  ├─ NO (mode='live') → [DEBUG] Not in trigger mode → SKIP
│  │
│  └─ YES (mode='trigger') ↓
│
├─ ACTION: Call activate_capture_request()
│  │
│  ├─ SUCCESS → [INFO] ✓ Camera triggered successfully
│  │            Update UI: "[TRIGGER] Camera captured"
│  │
│  └─ FAIL → [ERROR] ✗ Failed to trigger camera
│            Log exception details
│
└─ DONE
```

---

## State Transitions

```
┌──────────────────────────────────────────────┐
│         CAMERA MODE SELECTION                │
│                                              │
│  Button: "Live Mode" | "Trigger Mode"        │
└──────────────────────────────────────────────┘
         │                      │
         │                      │
         ↓                      ↓
    current_mode=          current_mode=
    'live'                  'trigger'
    │                       │
    ├─ Continuous preview   ├─ Single frame capture
    ├─ All TCP messages     ├─ Only on demand
    │   displayed           ├─ AUTO-TRIGGERED by
    ├─ NO auto-trigger      │   "start_rising" command
    └─ Manual capture only  └─ OR manual button click
```

---

## Data Flow - Frame Capture

```
TCP Message:
"start_rising||2075314"
     ↓
Parse timestamp: 2075314 microseconds
     ↓
Camera is in trigger mode ✅
     ↓
activate_capture_request()
     ↓
CameraStream.request_frame()
     ↓
PiCamera2 capture_single()
     ↓
Raw frame buffer (1456x1088, PISP_COMP1)
     ↓
Main stream (640x480, RGB888)
Raw stream (1456x1088, BGGR_PISP_COMP1)
     ↓
Display in camera_view widget
     ↓
If job enabled:
├─ Send to detection model (YOLO)
├─ Annotate with bboxes
├─ Display results
└─ Store if configured
```

---

## Timing Sequence

```
Time    Event
────────────────────────────────────────────────────────
T0      Sensor detects GPIO trigger
        └─ Captures timestamp: 2075314 μs
T1      Sensor sends TCP packet
        └─ "start_rising||2075314\n"
T2      TCPController.recv() reads socket
        └─ Stores in buffer
T3      Newline detected in buffer
        └─ Line extracted and decoded
T4      message_received signal emitted
        └─ _on_message_received() called
T5      Message added to UI list
        └─ "RX: start_rising||2075314" displayed
T6      _check_and_trigger_camera_if_needed() called
        └─ Parse message (instant)
        └─ Check conditions (instant)
T7      activate_capture_request() called
        └─ Request queued to camera thread
T8      Camera captures frame
        └─ Takes ~33ms at 30fps
T9      Frame available in buffer
        └─ [TRIGGER] event added to UI
T10     Job pipeline processes (if enabled)
        └─ Detection: ~100-200ms (YOLO)
T11     Results displayed
        └─ User sees detection results

Total Latency: ~150-300ms from sensor trigger to capture
```

---

## Message Format & Parsing

```
From Sensor:
┌────────────────────────────────────────────┐
│  "start_rising||2075314\n"                 │
│  │                 │           │           │
│  │                 │           └─ TCP ending
│  │                 └─ Timestamp (microseconds)
│  └─ Command identifier
└────────────────────────────────────────────┘
         ↓
Parse by _check_and_trigger_camera_if_needed():
├─ Check contains: "start_rising" (case-insensitive)
├─ Extract timestamp (optional, not used yet)
└─ Trigger if: "start_rising" found AND camera in trigger mode
         ↓
Result:
✅ Camera captures frame at timestamp T2 (sensor time: 2075314 μs)
```

---

## Error Handling Paths

```
_check_and_trigger_camera_if_needed()
│
├─ Exception Handler 1: Outer try/except
│  └─ Catches ANY exception
│     └─ Logs: "Error in _check_and_trigger_camera_if_needed"
│
├─ Exception Handler 2: Inner try/except
│  └─ Catches exceptions in activate_capture_request()
│     └─ Logs: "Error triggering camera"
│
└─ Graceful Returns:
   ├─ Message not trigger → silent return
   ├─ camera_manager missing → warning log
   ├─ current_mode missing → warning log
   ├─ Not in trigger mode → debug log
   └─ Trigger fails → error log

Result: NEVER CRASHES - always logs and returns gracefully
```

---

## Integration Points (All Verified ✅)

```
tcp_controller_manager.py
│
├─ self.main_window ✅
│  └─ Passed at initialization
│
├─ self.main_window.camera_manager ✅
│  └─ Initialized in MainWindow.__init__()
│
├─ camera_manager.current_mode ✅
│  └─ Attribute in CameraManager class
│
├─ camera_manager.activate_capture_request() ✅
│  └─ Method in CameraManager class
│
├─ self.message_list ✅
│  └─ QListWidget provided by caller
│
└─ logging module ✅
   └─ Standard Python logging

All integration points verified and working! ✅
```

---

## Summary

**System:** Automatic camera capture triggered by TCP sensor command  
**Trigger:** "start_rising||<timestamp>" message from sensor device  
**Condition:** Camera must be in 'trigger' mode (not 'live')  
**Action:** Single frame captured and processed through job pipeline  
**Feedback:** UI displays "[TRIGGER]" event and console logs  
**Status:** ✅ COMPLETE AND TESTED  
