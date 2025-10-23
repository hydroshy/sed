# ResultTool Debug Checklist

Use this guide to verify ResultTool integration step by step.

## Pre-Flight Checks

### ✓ Files Created and Modified

```bash
# Check files exist
ls tools/result_tool.py                      # Should exist
ls readme/RESULTTOOL_*.md                    # Should have 3 docs
git diff gui/detect_tool_manager.py          # Should show changes
git diff gui/camera_manager.py               # Should show changes
git diff tools/detection/detect_tool.py      # Should show removals
```

### ✓ Import Check

```python
# Open Python console and test imports:
from tools.result_tool import ResultTool
from tools import ResultTool  # Alternative import
from tools import BaseTool

# All should work without ImportError
```

---

## Runtime Testing

### Stage 1: Application Startup

**Expected Log Output**:
```
Loading GUI...
DetectToolManager initialized
Camera started
```

**If you see error**:
- Check Python path includes project root
- Verify no import errors in tools/result_tool.py
- Look for: `ImportError: cannot import name 'ResultTool'`

---

### Stage 2: Apply DetectTool

**Actions**:
1. Open GUI
2. Go to "Detect" tab
3. Select a model (if available)
4. Select classes
5. Click "Apply" button

**Expected Console Output**:
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

**If you see different output**:

❌ "apply_detect_tool_to_job called" NOT shown:
- Apply button not connected to method
- Check: `detect_tool_manager.apply_detect_tool_to_job` called from main_window.py line 1851

❌ "Failed to create DetectTool job":
- Model or classes not selected
- Select model first, then classes, then Apply
- Check config in console

❌ "No current job available":
- Job manager not initialized
- Check: `self.main_window.job_manager` exists
- Try: Refresh GUI or restart

❌ "ERROR: Failed to add ResultTool":
- ImportError in result_tool.py
- Check: `from tools.result_tool import ResultTool` works in Python
- Check: `tools/result_tool.py` file exists and is not corrupted
- Look for specific error message in console

❌ Only 1 or 2 tools shown instead of 3:
- ResultTool not being added
- Check exception handler in detect_tool_manager.py (lines 115-125)
- Add more debug: `print(f"ResultTool type: {type(result_tool)}")`

---

### Stage 3: Live View with Pipeline

**Actions**:
1. Switch to "Camera" tab
2. Camera should start live preview

**Expected Console Output (for each frame)**:
```
DEBUG: Job has 3 tools: [Camera Source, Detect Tool, Result Tool]
DEBUG: [CameraManager] RUNNING JOB PIPELINE (trigger_capturing=False)
2025-10-23 16:35:48,754 - job.job_manager - DEBUG - Running tool: Detect Tool (ID: 2)
DEBUG: [CameraManager] JOB PIPELINE COMPLETED
DEBUG: [CameraManager] Execution status: NG
```

**If you see different output**:

❌ "Job has 1 tools: [Camera Source]":
- ResultTool not in job
- Go back to Stage 2 - Apply wasn't successful
- Verify console shows "JOB PIPELINE SETUP" with 3 tools

❌ "WARNING: No job available":
- Job is None or empty
- Check: Line 326-327 in camera_manager.py
- Verify job was created in Stage 2

❌ Only sees Camera Source:
- DetectTool and ResultTool were created but not in pipeline
- Check: Line 333-334 in detect_tool_manager.py - tools were added?
- Verify: `current_job.add_tool(detect_tool)` and `current_job.add_tool(result_tool)` both executed

❌ "Detect Tool (ID: 2)" not running:
- Check job tools order
- Verify detection model loaded
- Check for YOLO/ONNX errors

---

### Stage 4: Object Detection

**Actions**:
1. Point camera at an object
2. Should see bounding boxes on live view

**Expected Result**:
- Objects detected and drawn
- executionLabel shows "NG" (no reference set yet)
- Console shows detection count

**If detection not working**:
- Check: Model loaded correctly
- Check: Classes selected
- Check: Detection threshold (confidence_threshold in config)
- Look for YOLO-specific errors

---

### Stage 5: Set Reference

**Actions**:
1. Point camera at an **OK** object
2. Find and click "Set Reference" button
   - Usually in Detect panel or toolbar
   - May be labeled "Set Reference" or "Capture Reference"

**Expected Console Output**:
```
DEBUG: set_ng_ok_reference_from_current_detections called
DEBUG: ResultTool found in job
DEBUG: [CameraManager] NG/OK Reference set on ResultTool with 5 objects
✓ Reference set: 5 objects
```

**If reference not setting**:

❌ "ResultTool found in job" NOT shown:
- ResultTool not in job - check Stage 2-3
- Verify tool name is exactly "Result Tool"

❌ "with 0 objects":
- No detections in last frame
- Point camera at an object and try again
- Check DetectTool is detecting

❌ No "Reference set" message:
- set_ng_ok_reference_from_current_detections() not called
- Check if "Set Reference" button exists
- Check button connection

❌ Exception "attribute 'set_reference_detections' not found":
- ResultTool not created with proper methods
- Verify result_tool.py has this method
- Check indentation in result_tool.py

---

### Stage 6: NG/OK Evaluation

**Actions**:
1. Keep camera on same object → should show **GREEN "OK"**
2. Move away or change object → should show **RED "NG"**

**Expected Result**:
```
Same object:
  DEBUG: [CameraManager] Execution status: OK
  executionLabel: Background GREEN, text "OK"

Different object:
  DEBUG: [CameraManager] Execution status: NG
  executionLabel: Background RED, text "NG"
```

**If always showing NG**:

❌ "ng_ok_result is None":
- NG/OK evaluation disabled
- Check: Reference was set successfully
- Check: `ng_ok_enabled = True` in ResultTool

❌ "ng_ok_result is always NG":
- Similarity threshold too high
- Default is 0.8 (80%) - might be too strict
- Check: `_compare_detections_similarity()` calculation
- Try: Lower confidence threshold for more stable detections

❌ Weird similarity values:
- Check IoU calculation in `_calculate_iou()`
- Verify bounding box format is [x1, y1, x2, y2]
- Check: DetectTool returns correct format

---

## Performance Checks

### Frame Rate

**Normal**: 20-30 FPS in live view  
**With Detection**: 5-15 FPS (depends on model size)  
**With NG/OK**: Same as with detection (ResultTool overhead < 1ms)

**If slow**:
- Check detection model size
- Verify no console errors (would slow down logs)
- Check CPU usage: should be 40-70% on RPi5

### Memory Usage

**Typical**:
- Base app: ~150MB
- With camera: ~200MB
- With detection: ~400-600MB (depends on model)
- With ResultTool: +5-10MB

**If high**:
- Check for memory leaks (growing over time)
- Verify model isn't loaded multiple times
- Check: `nvidia-smi` or `free -h` on Linux

---

## Tool Inspection Commands

### Check Job Pipeline at Runtime

```python
# In Python console while app running:
from job.job_manager import JobManager
jm = JobManager()
job = jm.get_current_job()

print(f"Job name: {job.name}")
print(f"Tools count: {len(job.tools)}")
for i, tool in enumerate(job.tools):
    print(f"  [{i}] {tool.name} (ID: {tool.tool_id})")
    if hasattr(tool, 'ng_ok_enabled'):
        print(f"      - NG/OK enabled: {tool.ng_ok_enabled}")
```

### Check ResultTool State

```python
# Find ResultTool in pipeline:
result_tool = None
for tool in job.tools:
    if 'result' in tool.name.lower():
        result_tool = tool
        break

if result_tool:
    print(f"ng_ok_enabled: {result_tool.ng_ok_enabled}")
    print(f"ng_ok_result: {result_tool.ng_ok_result}")
    print(f"reference count: {len(result_tool.ng_ok_reference_detections)}")
```

---

## Common Error Messages and Solutions

| Error | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'result_tool'` | Verify `tools/result_tool.py` exists |
| `ImportError: cannot import name 'ResultTool'` | Check syntax in result_tool.py, verify class name |
| `AttributeError: 'ResultTool' object has no attribute 'ng_ok_enabled'` | Verify __init__ sets all attributes |
| `TypeError: process() missing required argument` | Check process method signature matches BaseTool |
| `KeyError: 'detections'` | DetectTool didn't run or didn't output detections |
| `RecursionError or infinite loop` | Check tool source_tool not set to self |
| `Float division by zero` | Check IoU calculation handles zero area |

---

## Verification Checklist

- [ ] `tools/result_tool.py` file exists
- [ ] `from tools.result_tool import ResultTool` works
- [ ] apply_detect_tool_to_job() shows "JOB PIPELINE SETUP" with 3 tools
- [ ] Live view shows job with 3 tools message
- [ ] Objects are detected on camera
- [ ] "Set Reference" button adds reference
- [ ] Same object shows GREEN "OK"
- [ ] Different object shows RED "NG"
- [ ] No console exceptions
- [ ] Frame rate is acceptable (5+ FPS)
- [ ] No memory leaks (stable memory over time)
- [ ] Can set new reference multiple times

---

## If Still Having Issues

1. **Collect full console output** (from startup to problem)
2. **Check all 3 docs**: RESULTTOOL_MIGRATION.md, RESULTTOOL_TESTING.md, RESULTTOOL_COMPLETE_STATUS.md
3. **Verify files modified correctly**: `git diff` shows expected changes
4. **Test in isolation**: 
   ```python
   # Test ResultTool alone
   from tools.result_tool import ResultTool
   rt = ResultTool()
   rt.setup_config()
   rt.set_reference_detections([{"x1": 0, "y1": 0, "x2": 100, "y2": 100, "class_name": "test", "confidence": 0.9}])
   status, sim, reason = rt.evaluate_ng_ok([...])
   ```
5. **Ask for help** with:
   - Full console output (copy-paste)
   - Step where it fails (stages 1-6 above)
   - Screenshot of GUI state
   - Hardware info (RPi5, Camera type)

---

**Last Updated**: 2025-10-23  
**Compatibility**: Raspberry Pi 5 with PiCamera2
