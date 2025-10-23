# ResultTool - Expected Console Output Timeline

## Timeline of What You'll See

### 🟢 Application Startup
```
2025-10-23 16:35:00,000 - root - INFO - Starting application...
2025-10-23 16:35:00,500 - root - INFO - Loading GUI...
2025-10-23 16:35:01,000 - root - INFO - Initializing components...
DetectToolManager initialized
CameraManager initialized
2025-10-23 16:35:02,000 - root - INFO - Application ready
```

---

### 🟡 User Clicks "Apply" in Detect Tab

**Before clicking Apply** (normal state):
```
Camera Source tool only running (or none if no job yet)
```

**CLICK "Apply" button**

---

### 🟢 Console Output: ResultTool Creation (THIS IS KEY!)

```
================================================================================
DEBUG: apply_detect_tool_to_job called - STARTING DETECT TOOL APPLICATION
================================================================================
SUCCESS: DetectTool created: Detect Tool
DEBUG: Current job found: Job 1
DEBUG: Current job tools count: 1
✓ Added DetectTool to job. Tools count: 2
✓ Added ResultTool to job. Final tools count: 3
================================================================================
JOB PIPELINE SETUP:
  [0] Camera Source (ID: 1)
  [1] Detect Tool (ID: 2)
  [2] Result Tool (ID: 3)
================================================================================
```

**What this tells you**:
✅ apply_detect_tool_to_job was called successfully
✅ DetectTool was created
✅ ResultTool was created and added
✅ Job now has 3 tools: CameraSource, DetectTool, ResultTool

---

### 🟡 User Switches to "Camera" Tab

**First time after Apply** (camera starts):
```
2025-10-23 16:35:05,000 - root - INFO - Simple camera toggle: True
2025-10-23 16:35:05,100 - root - INFO - Starting camera stream...
2025-10-23 16:35:05,200 - root - INFO - Camera stream started
DEBUG: [CameraStream] Creating camera...
DEBUG: [CameraStream] Camera created
```

---

### 🟢 Live View Running with 3-Tool Pipeline

**For EACH frame** (repeats ~20-30 times per second):

```
DEBUG: [CameraManager] _on_frame_from_camera called - _trigger_capturing=False (call #45), processing live frame
DEBUG: Job has 3 tools: [Camera Source, Detect Tool, Result Tool]
DEBUG: [CameraManager] RUNNING JOB PIPELINE (trigger_capturing=False)
2025-10-23 16:35:08,651 - job.job_manager - DEBUG - Running tool: Camera Source (ID: 1)
2025-10-23 16:35:08,652 - job.job_manager - DEBUG - Running tool: Detect Tool (ID: 2)
2025-10-23 16:35:08,653 - job.job_manager - DEBUG - Running tool: Result Tool (ID: 3)
DEBUG: [CameraManager] JOB PIPELINE COMPLETED
DEBUG: [CameraManager] Execution status: NG
Processing frame with format: RGB888 [CameraDisplayWorker]
```

**What's happening**:
- Frame #45 received from camera
- Job pipeline running with 3 tools
- Tool 1 (CameraSource): Captures frame
- Tool 2 (DetectTool): Detects objects
- Tool 3 (ResultTool): Evaluates NG/OK (no reference yet = NG)
- executionLabel shows RED "NG"

---

### 🟡 User Clicks "Set Reference"

**When you point camera at OK object and click "Set Reference":**

```
DEBUG: [CameraManager] set_ng_ok_reference_from_current_detections called
DEBUG: DetectTool found in job
DEBUG: ResultTool found in job
DEBUG: [CameraManager] Getting last detections: 5 objects found
DEBUG: [CameraManager] Setting reference on ResultTool...
DEBUG: [CameraManager] NG/OK Reference set on ResultTool with 5 objects
✓ Reference set: 5 objects
```

**What happened**:
✅ set_reference_detections() called on ResultTool (not DetectTool anymore)
✅ 5 objects stored as reference
✅ ResultTool.ng_ok_enabled = True
✅ Ready for evaluation

---

### 🟢 Live View with Reference (Evaluation Active)

**Next frames with reference set**:

```
DEBUG: [CameraManager] _on_frame_from_camera called - _trigger_capturing=False (call #187), processing live frame
DEBUG: Job has 3 tools: [Camera Source, Detect Tool, Result Tool]
DEBUG: [CameraManager] RUNNING JOB PIPELINE (trigger_capturing=False)
2025-10-23 16:35:15,754 - job.job_manager - DEBUG - Running tool: Camera Source (ID: 1)
2025-10-23 16:35:15,755 - job.job_manager - DEBUG - Running tool: Detect Tool (ID: 2)
2025-10-23 16:35:15,756 - job.job_manager - DEBUG - Running tool: Result Tool (ID: 3)
DEBUG: [CameraManager] JOB PIPELINE COMPLETED
DEBUG: [CameraManager] Execution status: OK
```

**If camera shows SAME object** (matches reference):
```
Execution status: OK  ← GREEN label appears
```

**If camera shows DIFFERENT object** (doesn't match):
```
Execution status: NG  ← RED label appears
```

---

## Full Execution Flow Example

### Scenario: User applies DetectTool, sets reference, then moves camera

```
═════════════════════════════════════════════════════════════════════════════
TIME: 16:35:10 - USER CLICKS "APPLY" BUTTON
═════════════════════════════════════════════════════════════════════════════

================================================================================
DEBUG: apply_detect_tool_to_job called - STARTING DETECT TOOL APPLICATION
================================================================================
SUCCESS: DetectTool created: Detect Tool
✓ Added DetectTool to job. Tools count: 2
✓ Added ResultTool to job. Final tools count: 3
================================================================================
JOB PIPELINE SETUP:
  [0] Camera Source (ID: 1)
  [1] Detect Tool (ID: 2)
  [2] Result Tool (ID: 3)
================================================================================

═════════════════════════════════════════════════════════════════════════════
TIME: 16:35:12 - USER SWITCHES TO CAMERA TAB
═════════════════════════════════════════════════════════════════════════════

2025-10-23 16:35:12,500 - root - INFO - Starting camera stream...

DEBUG: [CameraManager] _on_frame_from_camera called - _trigger_capturing=False (call #1), processing live frame
DEBUG: Job has 3 tools: [Camera Source, Detect Tool, Result Tool]
DEBUG: [CameraManager] RUNNING JOB PIPELINE (trigger_capturing=False)
DEBUG: [CameraManager] JOB PIPELINE COMPLETED
DEBUG: [CameraManager] Execution status: NG

DEBUG: [CameraManager] _on_frame_from_camera called - _trigger_capturing=False (call #2), processing live frame
DEBUG: Job has 3 tools: [Camera Source, Detect Tool, Result Tool]
DEBUG: [CameraManager] RUNNING JOB PIPELINE (trigger_capturing=False)
DEBUG: [CameraManager] JOB PIPELINE COMPLETED
DEBUG: [CameraManager] Execution status: NG

[... frames 3-49 continue with similar pattern ...]

═════════════════════════════════════════════════════════════════════════════
TIME: 16:35:15 - USER POINTS AT OK OBJECT AND CLICKS "SET REFERENCE"
═════════════════════════════════════════════════════════════════════════════

DEBUG: [CameraManager] set_ng_ok_reference_from_current_detections called
DEBUG: DetectTool found in job
DEBUG: ResultTool found in job
DEBUG: [CameraManager] NG/OK Reference set on ResultTool with 3 objects
✓ Reference set: 3 objects

═════════════════════════════════════════════════════════════════════════════
TIME: 16:35:16 - NEXT FRAMES (SAME OBJECT, MATCHES REFERENCE)
═════════════════════════════════════════════════════════════════════════════

DEBUG: [CameraManager] _on_frame_from_camera called - _trigger_capturing=False (call #78), processing live frame
DEBUG: Job has 3 tools: [Camera Source, Detect Tool, Result Tool]
DEBUG: [CameraManager] RUNNING JOB PIPELINE (trigger_capturing=False)
DEBUG: [CameraManager] JOB PIPELINE COMPLETED
DEBUG: [CameraManager] Execution status: OK  ← GREEN LABEL

[... more frames showing OK ...]

═════════════════════════════════════════════════════════════════════════════
TIME: 16:35:18 - USER MOVES CAMERA AWAY (DIFFERENT OBJECT)
═════════════════════════════════════════════════════════════════════════════

DEBUG: [CameraManager] _on_frame_from_camera called - _trigger_capturing=False (call #120), processing live frame
DEBUG: Job has 3 tools: [Camera Source, Detect Tool, Result Tool]
DEBUG: [CameraManager] RUNNING JOB PIPELINE (trigger_capturing=False)
DEBUG: [CameraManager] JOB PIPELINE COMPLETED
DEBUG: [CameraManager] Execution status: NG  ← RED LABEL

[... more frames showing NG ...]

═════════════════════════════════════════════════════════════════════════════
```

---

## Key Console Markers

| Marker | Meaning |
|--------|---------|
| `================================================================================` | Important section separator |
| `✓ Added DetectTool to job` | DetectTool successfully added |
| `✓ Added ResultTool to job` | ResultTool successfully added |
| `JOB PIPELINE SETUP:` | Shows all tools in pipeline |
| `[0] Camera Source` | First tool in pipeline |
| `[1] Detect Tool` | Second tool - detects objects |
| `[2] Result Tool` | Third tool - evaluates OK/NG |
| `DEBUG: Job has 3 tools:` | Pipeline has correct tools |
| `Execution status: OK` | Reference matched - GREEN label |
| `Execution status: NG` | Reference didn't match - RED label |
| `✓ Reference set:` | Reference successfully stored |

---

## What Each Tool Does in Console

### Camera Source Tool
```
Running tool: Camera Source (ID: 1)
├─ Gets latest frame from camera
└─ Outputs: Raw frame
```

### Detect Tool
```
Running tool: Detect Tool (ID: 2)
├─ Receives: Frame from CameraSource
├─ Detects: Objects using YOLO
└─ Outputs: {detections: [...], confidence: [...], ...}
```

### Result Tool (NEW!)
```
Running tool: Result Tool (ID: 3)
├─ Receives: Detections via context['detections']
├─ Compares: With reference (if set)
├─ Evaluates: Similarity score
└─ Outputs: {ng_ok_result: "OK"/"NG", similarity: 0.85, reason: "..."}
```

---

## Troubleshooting by Console Output

### Problem: Apply doesn't create tools

**Look for**:
```
ERROR: Failed to create DetectTool job
```
**Meaning**: Model or classes not selected

**Look for**:
```
ERROR: Job manager not available
```
**Meaning**: Job manager initialization issue

---

### Problem: Only 2 tools instead of 3

**Look for**:
```
ERROR: Failed to add ResultTool: [error message]
```
**Check**:
- ResultTool file exists
- No import errors
- No syntax errors

---

### Problem: NG/OK always NG

**Look for**:
```
Reference set: 0 objects
```
**Meaning**: No detections in last frame when setting reference

**Or**:
```
ng_ok_enabled = False
```
**Meaning**: set_reference_detections() wasn't called

---

### Problem: Set Reference not working

**Look for**:
```
ResultTool found in job: False
```
**Meaning**: ResultTool not in job pipeline

**Or**:
```
ERROR: set_ng_ok_reference_from_current_detections failed
```
**Check**: ResultTool has set_reference_detections method

---

## Video of What Happens

If you could "see" the console in real-time:

1. **Apply click** → console shows "JOB PIPELINE SETUP" ✅
2. **Camera view** → sees "Job has 3 tools" every frame ✅
3. **Set reference** → shows "Reference set: X objects" ✅
4. **Frame processing** → "Execution status: OK" or "NG" 30x/second ✅

---

## Success Indicators ✅

Look for these in console:

```
✓ apply_detect_tool_to_job called
✓ SUCCESS: DetectTool created
✓ Added DetectTool to job
✓ Added ResultTool to job
✓ JOB PIPELINE SETUP: shows 3 tools
✓ Job has 3 tools: [Camera Source, Detect Tool, Result Tool]
✓ Execution status: OK or NG (not "None")
✓ Reference set: X objects
```

If you see all these → **ResultTool is working perfectly!** 🎉

---

**Print this document and keep it handy while testing on Raspberry Pi!**

---

**Last Updated**: 2025-10-23
