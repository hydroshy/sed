# ResultTool Integration Testing Guide

## How to Test the ResultTool Integration

### Step 1: Start the Application
```bash
python run.py
```

### Step 2: Apply DetectTool (This triggers ResultTool Addition)
1. Click on **"Detect"** tab in the left sidebar
2. Select a **model** (e.g., if available)
3. Select **classes** you want to detect
4. Click **"Apply"** button at the bottom

**Expected Output in Console:**
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

### Step 3: Verify in Live View
1. Click **"Camera"** tab
2. Live view should now run the **full pipeline**: Camera Source → Detect Tool → Result Tool

**Expected Console Output (for each frame):**
```
DEBUG: Job has 3 tools: [Camera Source, Detect Tool, Result Tool]
DEBUG: [CameraManager] RUNNING JOB PIPELINE
DEBUG: [CameraManager] JOB PIPELINE COMPLETED
DEBUG: [CameraManager] Execution status: NG
```

### Step 4: Set Reference (Test NG/OK Logic)
1. Point camera at an **OK** object
2. Click **"Set Reference"** button (in Detect panel, if available)

**Expected Output:**
```
DEBUG: [CameraManager] NG/OK Reference set on ResultTool with X objects
✓ Reference set: X objects
```

### Step 5: Test NG/OK Evaluation
1. Keep camera on the **same OK object** → should show **GREEN "OK"**
2. Move camera away or change object → should show **RED "NG"**

**Expected Console for OK:**
```
DEBUG: [CameraManager] Execution status: OK
```

**Expected Console for NG:**
```
DEBUG: [CameraManager] Execution status: NG
```

---

## Troubleshooting

### If you see only CameraSource tool:
- Make sure you clicked **"Apply"** button in Detect tab
- Check if the Apply button is actually connected (check console for "apply_detect_tool_to_job called")
- Check if model and classes are selected

### If ResultTool is not added:
- Check console for error: `ERROR: Failed to add ResultTool`
- Verify `tools/result_tool.py` exists
- Verify import: `from tools.result_tool import ResultTool` works

### If NG/OK status shows "NG" always:
- Make sure to **"Set Reference"** first
- Console should show `ng_ok_enabled = True` and reference detection count
- Check if ResultTool received the reference: `NG/OK Reference set on ResultTool`

---

## What's Happening Under the Hood

1. **apply_detect_tool_to_job()** called when you click Apply
2. Creates **DetectTool** instance with your selected model
3. Creates **ResultTool** instance
4. Both are added to job pipeline
5. Next frame triggers job pipeline with all 3 tools
6. DetectTool detects objects → passes detections via context
7. ResultTool receives detections → compares with reference → outputs OK/NG
8. CameraManager reads OK/NG from ResultTool → updates UI label

---

## Console Output Markers

| Marker | Meaning |
|--------|---------|
| `✓` | Success - tool added |
| `ERROR:` | Something failed |
| `SUCCESS:` | Operation completed |
| `================` | Important section separator |
| `JOB PIPELINE SETUP:` | Shows all tools in pipeline |
| `Execution status: OK` | Reference matched, status OK |
| `Execution status: NG` | Reference didn't match, status NG |

