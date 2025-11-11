# External Trigger Implementation - Visual Architecture

## System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           SYSTEM OVERVIEW                                     │
└──────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │   User (You)    │
                              └────────┬────────┘
                                       │
                ┌──────────────────────┼──────────────────────┐
                │                      │                      │
                ▼                      ▼                      ▼
        ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
        │  Trigger Mode│      │ Online Camera│      │ Live Camera  │
        │    Button    │      │    Button    │      │    Button    │
        └──────┬───────┘      └──────┬───────┘      └──────┬───────┘
               │                     │                     │
               │ (trigger mode)      │ (in trigger mode)   │ (returns to live)
               │                     │                     │
               ▼                     ▼                     ▼
        ┌────────────────────────────────────────────────────────┐
        │         camera_manager.py                              │
        │  ┌─────────────────────────────────────────────────┐  │
        │  │ on_trigger_camera_mode_clicked()                │  │
        │  │ set_trigger_mode(True)                          │  │
        │  └──────────────────┬────────────────────────────┘  │
        │                     │                                │
        │  ┌─────────────────────────────────────────────────┐  │
        │  │ main_window._toggle_camera(checked)             │  │
        │  │ Detect: current_mode == 'trigger'?              │  │
        │  │ If yes:                                         │  │
        │  │   - set_manual_exposure_mode()  ← Lock AE       │  │
        │  │   - set_auto_white_balance(False) ← Lock AWB    │  │
        │  └──────────────────┬────────────────────────────┘  │
        │                     │                                │
        └─────────────────────┼────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────────────────────┐
        │         camera_stream.py                               │
        │  ┌─────────────────────────────────────────────────┐  │
        │  │ set_trigger_mode(enabled)                       │  │
        │  │   self.external_trigger_enabled = True          │  │
        │  │   self._in_trigger_mode = True                  │  │
        │  │   _set_external_trigger_sysfs(enabled) ← NEW    │  │
        │  └──────────────────┬────────────────────────────┘  │
        │                     │                                │
        │  ┌──────────────────────────────────────────────┐   │
        │  │ NEW: _set_external_trigger_sysfs(enabled)    │   │
        │  │                                               │   │
        │  │  subprocess.run(                             │   │
        │  │    "echo 1 | sudo tee /sys/.../trigger_mode" │   │
        │  │  )                                            │   │
        │  │                                               │   │
        │  │  Returns: True on success, False on error    │   │
        │  └──────────────────┬────────────────────────┘   │
        │                     │                               │
        └─────────────────────┼───────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────────────────────┐
        │     /sys/module/imx296/parameters/trigger_mode         │
        │                                                        │
        │  ┌─ echo 1 | sudo tee ... ──────────────────────────┐ │
        │  │                                                   │ │
        │  │  ✅ External Trigger ENABLED                     │ │
        │  │     (Value = 1)                                  │ │
        │  │     Camera waits for hardware trigger signal     │ │
        │  │                                                   │ │
        │  └──────────────────────────────────────────────────┘ │
        │                                                        │
        │  ┌─ echo 0 | sudo tee ... ──────────────────────────┐ │
        │  │                                                   │ │
        │  │  ✅ External Trigger DISABLED                    │ │
        │  │     (Value = 0)                                  │ │
        │  │     Camera returns to continuous streaming       │ │
        │  │                                                   │ │
        │  └──────────────────────────────────────────────────┘ │
        └────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────────────────────┐
        │              GS Camera (Hardware)                       │
        │                                                        │
        │  State 1: External Trigger ENABLED (1)               │
        │  ┌───────────────────────────────────────────────┐    │
        │  │ 🎥 Waits for external trigger signal          │    │
        │  │                                               │    │
        │  │ 3A Status:                                    │    │
        │  │  ✅ AE Locked (exposure fixed)               │    │
        │  │  ✅ AWB Locked (white balance fixed)         │    │
        │  │                                               │    │
        │  │ Ready for: Hardware GPIO pulse / Sensor signal │   │
        │  └───────────────────────────────────────────────┘    │
        │                                                        │
        │  State 2: External Trigger DISABLED (0)              │
        │  ┌───────────────────────────────────────────────┐    │
        │  │ 📹 Continuous live streaming                  │    │
        │  │                                               │    │
        │  │ 3A Status:                                    │    │
        │  │  ❌ AE Auto (exposure adjusts automatically)  │    │
        │  │  ❌ AWB Auto (white balance adjusts auto)    │    │
        │  │                                               │    │
        │  │ Ready for: Live preview display              │    │
        │  └───────────────────────────────────────────────┘    │
        └────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────────────────────┐
        │          Frame Processing Pipeline                     │
        │                                                        │
        │  Trigger State                                        │
        │  ├─ Hardware trigger signal arrives                   │
        │  │   └─ Camera captures frame                         │
        │  │       └─ Frame → cameraView (display)              │
        │  │           └─ Frame → Job pipeline                  │
        │  │               └─ Detection/Classification          │
        │  │                   └─ Result → Result Tab           │
        │  │                       └─ Frame history updated      │
        │  │                                                    │
        │  Live State                                           │
        │  ├─ Continuous frames (30 FPS)                       │
        │  │   └─ Frame → cameraView (display)                  │
        │  │       └─ Frame → Job pipeline (if enabled)        │
        │  │           └─ Detection/Classification              │
        │  │               └─ Result → Result Tab               │
        │  │                   └─ Frame history updated          │
        │  │                                                    │
        └────────────────────────────────────────────────────────┘
```

## State Transition Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                      CAMERA STATE MACHINE                         │
└──────────────────────────────────────────────────────────────────┘

                          ┌─────────────┐
                          │   STOPPED   │
                          │  (No camera)│
                          └──────┬──────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
            ┌──────────────┐         ┌──────────────┐
            │LIVE STREAMING│         │TRIGGER READY │
            │              │         │              │
            │ 📹 Continuous│         │ 🎥 Waiting   │
            │    Frames    │         │   for signal │
            │              │         │              │
            │ 3A: AUTO     │         │ 3A: LOCKED   │
            │ AE: AUTO     │         │ AE: MANUAL   │
            │ AWB: AUTO    │         │ AWB: MANUAL  │
            └──────┬───────┘         └───────┬──────┘
                   │                        │
    ┌──────────────────────────────┐  ┌─────────────────────────────┐
    │ trigger_mode = False          │  │ trigger_mode = True         │
    │ echo 0 | sudo tee /sys/...    │  │ echo 1 | sudo tee /sys/...  │
    └──────────────────────────────┘  └─────────────────────────────┘
                   ▲                        ▲
                   │                        │
                   │ Click "Live Mode"      │ Click "Trigger Mode"
                   │                        │
                   └────────────────────────┘
```

## Code Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                      CODE EXECUTION FLOW                          │
└──────────────────────────────────────────────────────────────────┘

SCENARIO 1: User clicks "Trigger Camera Mode" button
════════════════════════════════════════════════════════════════════

    main_window.py (line ~1200)
         │
         ├─ triggerCameraMode.clicked → on_trigger_camera_mode_clicked()
         │
         ├─ camera_manager.py (line ~2282)
         │  │
         │  └─ on_trigger_camera_mode_clicked()
         │     │
         │     ├─ Find Camera Source tool
         │     ├─ camera_tool.set_camera_mode("trigger")
         │     │
         │     └─ Fallback: _handle_trigger_mode_directly()
         │        │
         │        └─ self.set_trigger_mode(True)  ← Entry point
         │
         ├─ camera_stream.py (line 559)
         │  │
         │  └─ set_trigger_mode(True)
         │     │
         │     ├─ self.external_trigger_enabled = True
         │     ├─ self._in_trigger_mode = True
         │     │
         │     └─ self._set_external_trigger_sysfs(True)  ← NEW
         │        │
         │        └─ camera_stream.py (line 693)
         │           │
         │           └─ _set_external_trigger_sysfs(True)
         │              │
         │              ├─ trigger_value = "1"
         │              ├─ sysfs_path = "/sys/module/imx296/parameters/trigger_mode"
         │              ├─ command = f"echo {trigger_value} | sudo tee {sysfs_path}"
         │              │
         │              └─ subprocess.run(command, shell=True, timeout=5)
         │                 │
         │                 ├─ Execute: echo 1 | sudo tee /sys/.../trigger_mode
         │                 │
         │                 ├─ Success? Print ✅
         │                 │  └─ "✅ [CameraStream] External trigger ENABLED"
         │                 │
         │                 └─ Failure? Print ❌
         │                    └─ "❌ [CameraStream] Failed to set external trigger"
         │
         └─ RESULT: ✅ GS Camera external trigger ENABLED


SCENARIO 2: User clicks "onlineCamera" button (in trigger mode)
════════════════════════════════════════════════════════════════════

    main_window.py (line ~990)
         │
         ├─ onlineCamera.clicked(True) → _toggle_camera(True)
         │
         ├─ main_window.py (line 994)
         │  │
         │  └─ _toggle_camera(True)
         │     │
         │     ├─ if checked:
         │     │  │
         │     │  ├─ logging.info("Starting camera stream...")
         │     │  │
         │     │  ├─ camera_stream.start_preview()
         │     │  │  └─ Camera starts (ready for trigger)
         │     │  │
         │     │  ├─ Detect current mode: ← NEW LOGIC
         │     │  │  │
         │     │  │  └─ current_mode = getattr(camera_manager, 'current_mode', 'live')
         │     │  │     │
         │     │  │     ├─ Is trigger mode?
         │     │  │     │  │
         │     │  │     │  └─ YES:
         │     │  │     │     │
         │     │  │     │     ├─ logging.info("🔒 Locking 3A...")
         │     │  │     │     │
         │     │  │     │     ├─ camera_manager.set_manual_exposure_mode()
         │     │  │     │     │  │
         │     │  │     │     │  └─ camera_stream.py (line ~1093)
         │     │  │     │     │     │
         │     │  │     │     │     └─ set_auto_exposure(False)
         │     │  │     │     │        │
         │     │  │     │     │        └─ AeEnable = False (Lock exposure)
         │     │  │     │     │
         │     │  │     │     ├─ camera_stream.set_auto_white_balance(False)
         │     │  │     │     │  │
         │     │  │     │     │  └─ camera_stream.py (somewhere)
         │     │  │     │     │     │
         │     │  │     │     │     └─ AwbEnable = False (Lock white balance)
         │     │  │     │     │
         │     │  │     │     ├─ logging.info("✅ 3A locked (AE + AWB disabled)")
         │     │  │     │     │
         │     │  │     │     └─ Ready for trigger signal!
         │     │  │     │
         │     │  │     └─ NO (live mode): Skip 3A locking
         │     │  │
         │     │  └─ Set button style green (active)
         │     │
         │     └─ RESULT: ✅ Camera running with 3A locked
         │
         └─ Hardware trigger signal arrives
            │
            ├─ Camera captures frame
            │
            ├─ Frame displayed on cameraView
            │
            ├─ Job pipeline processes
            │
            └─ Result displays in Result Tab
```

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│              TRIGGER MODE DATA FLOW                               │
└──────────────────────────────────────────────────────────────────┘

INPUT: User clicks "Trigger Camera Mode"
   │
   ├─ Signal: triggerCameraMode.clicked()
   │
   ├─ Handler: on_trigger_camera_mode_clicked()
   │
   ├─ State Change: current_mode = 'trigger'
   │
   └─ Action: set_trigger_mode(True)
       │
       ├─ Parameter: enabled = True
       │
       ├─ Subprocess Creation:
       │  ├─ command = "echo 1 | sudo tee /sys/module/imx296/parameters/trigger_mode"
       │  ├─ shell = True
       │  ├─ capture_output = True
       │  ├─ timeout = 5 seconds
       │  └─ text = True
       │
       ├─ Subprocess Execution:
       │  ├─ Shell parses: "echo 1" → "1"
       │  ├─ Pipe operator: | → send output to next command
       │  ├─ sudo: runs with elevated privileges
       │  ├─ tee: writes to sysfs file AND stdout
       │  └─ File write: 1 → /sys/module/imx296/parameters/trigger_mode
       │
       ├─ Return Code Check:
       │  ├─ returncode == 0 → SUCCESS
       │  │  └─ stdout = "1\n"
       │  │     └─ Print: ✅ External trigger ENABLED
       │  │
       │  └─ returncode != 0 → FAILURE
       │     └─ stderr = error message
       │        └─ Print: ❌ Failed to set external trigger
       │
       └─ Result: GS Camera firmware detects sysfs write
          └─ Camera switches to external trigger mode

INPUT: User clicks "onlineCamera" (in trigger mode)
   │
   ├─ Signal: onlineCamera.clicked(True)
   │
   ├─ Handler: _toggle_camera(True)
   │
   ├─ Check: current_mode == 'trigger'? YES
   │  │
   │  ├─ Call: set_manual_exposure_mode()
   │  │  ├─ _is_auto_exposure = False
   │  │  ├─ camera_stream.set_auto_exposure(False)
   │  │  │  └─ preview_config["controls"]["AeEnable"] = False
   │  │  │     └─ Exposure mode becomes MANUAL
   │  │  │
   │  │  └─ Persist to picam2 configuration
   │  │
   │  ├─ Call: set_auto_white_balance(False)
   │  │  ├─ AwbEnable = False
   │  │  └─ White balance mode becomes MANUAL
   │  │
   │  └─ Result: 3A is now LOCKED
   │
   ├─ Call: camera_stream.start_preview()
   │  └─ picam2.start(show_preview=False)
   │     └─ Camera initialized and ready
   │
   └─ READY STATE:
      ├─ Camera: Running, waiting for trigger
      ├─ AE: Manual (exposure fixed)
      ├─ AWB: Manual (white balance fixed)
      ├─ Trigger: Enabled, waiting for signal
      └─ Status: ✅ Ready for hardware trigger
```

---

## Summary

### Architecture Highlights
- ✅ Clean separation of concerns (camera_stream vs main_window)
- ✅ Subprocess isolation for sysfs commands
- ✅ Error handling at each layer
- ✅ Backward compatible (live mode unchanged)
- ✅ Clear state transitions

### Key Integration Points
1. **camera_stream.set_trigger_mode()** ← Main entry point
2. **_set_external_trigger_sysfs()** ← Hardware control (NEW)
3. **main_window._toggle_camera()** ← 3A lock logic (MODIFIED)
4. **camera_manager.set_manual_exposure_mode()** ← Exposure lock
5. **camera_stream.set_auto_white_balance()** ← White balance lock

### Control Flow
```
User Action → Signal → Handler → State Change → Hardware Command → Result
```

---

**Diagram Generated:** 2025-11-07
