# 🔍 Threshold Loading Diagnosis Guide

## Problem
User says: "Vẫn chưa thấy detect tool lấy được threshold từ classificationTableView khi thêm class vào"

Translation: "Still can't see detect tool getting the threshold from classificationTableView when adding class"

---

## Current Flow

```
User adds class to table
    ↓
Table shows: pilsner333 | 0.5
    ↓
User edits threshold: pilsner333 | 0.8
    ↓
User clicks Apply
    ↓
apply_detect_tool_to_job() called
    ↓
create_detect_tool_job() called
    ↓
get_tool_config() called
    ↓
get_class_thresholds() reads from table
    ↓
create_detect_tool_from_manager_config() receives config
    ↓
DetectTool stored in self.class_thresholds
    ↓
Later: initialize_detection() loads from config
    ↓
process() uses self.class_thresholds
```

---

## New Logging Added

### 1. detect_tool_manager.py - Line 324
```python
logger.info(f"Reading thresholds from table - Rows: {self.classification_model.rowCount()}")
```
**Purpose:** Check if table has any rows

### 2. detect_tool_manager.py - Line 338
```python
logger.info(f"  Row {row}: {class_name} = {threshold}")
```
**Purpose:** Show each class/threshold read from table

### 3. detect_tool_manager.py - Line 344
```python
logger.info(f"Final thresholds dict: {thresholds}")
```
**Purpose:** Show complete threshold dictionary after reading

### 4. detect_tool_manager.py - Line 461
```python
logger.info(f"get_tool_config() - Thresholds from table: {thresholds}")
```
**Purpose:** Confirm thresholds are in config being created

### 5. detect_tool.py - Line 532
```python
logger.info(f"  Class thresholds: {tool_config.get('class_thresholds', {})}")
```
**Purpose:** Verify thresholds passed to factory function

### 6. detect_tool.py - Line 278
```python
logger.info(f"  Thresholds: {self.class_thresholds}")
```
**Purpose:** Confirm thresholds loaded into self.class_thresholds

---

## Test Procedure

### Step 1: Start Application
```
python run.py
```

### Step 2: Go to Detect Tab
Look for "Detect Tool" section

### Step 3: Select Model
- Select model dropdown (e.g., "sed.onnx")
- Wait for model to load

### Step 4: Add Class with Custom Threshold
1. Open "Classification combo" dropdown
2. Select "pilsner333"
3. Click "Add" button
   - Check console for: `Added class: pilsner333`
4. In table, double-click threshold cell (should show "0.5")
5. Change to "0.8"
6. Press Enter to confirm

### Step 5: Click Apply Button
**Look for these logs in console:**

```
[detect_tool_manager.py]
✓ Got config: model=sed.onnx, classes=1
📦 Creating DetectTool...
get_tool_config() - Thresholds from table: {'pilsner333': 0.8}
Reading thresholds from table - Rows: 1
  Row 0: pilsner333 = 0.8
Final thresholds dict: {'pilsner333': 0.8}

[detect_tool.py factory function]
Created DetectTool from manager config
  Model: /path/to/sed.onnx
  Selected classes: ['pilsner333']
  Class thresholds: {'pilsner333': 0.8}

[detect_tool.py initialize()]
✅ DetectTool initialized, starting detection...
  Model: sed.onnx
  Classes: 3 total, 1 selected
  Thresholds: {'pilsner333': 0.8}
```

### Step 6: Trigger Capture
1. Add object to camera view
2. Click "Trigger" button
3. Look for logs:

```
✅ DetectTool found 1 detections:
   Detection 0: pilsner333 (0.93)

🔍 ResultTool.process() - 1 detections, 1 thresholds, 1 selected classes
📊 Using threshold-based evaluation
   Detection: pilsner333 (0.93)
   Threshold: 0.8
   ✅ 0.93 >= 0.8? YES
✅ RESULT: OK
```

---

## Expected Outputs at Each Stage

| Stage | Expected Log | If Missing, Check |
|-------|--------------|-------------------|
| Add class | `Added class: pilsner333` | Button click connected? |
| Click Apply | `Reading thresholds from table - Rows: 1` | Table populated? |
| Apply (thresholds) | `Row 0: pilsner333 = 0.8` | Threshold editable? |
| Create DetectTool | `Class thresholds: {'pilsner333': 0.8}` | Config passed correctly? |
| Initialize | `Thresholds: {'pilsner333': 0.8}` | self.config loaded? |
| Trigger | `Using threshold-based evaluation` | ResultTool working? |

---

## Troubleshooting

### If thresholds are EMPTY at any stage:

**Check 1:** Is the table actually populated?
- Log shows: `Rows: 0` → User hasn't added classes yet
- Add a class first!

**Check 2:** Is threshold being edited?
- Log shows: `Row 0: pilsner333 = 0.5` (still default)
- User needs to double-click and edit the threshold

**Check 3:** Is the table model connected?
- Log shows: `Classification model not available`
- Table widget may not be initialized properly

### If thresholds ARE in config but not in DetectTool:

**Check:** Factory function receive
- Log shows factory getting empty dict
- Config.get() failing

---

## Console Command to Filter Logs

To see only threshold-related logs:

```bash
python run.py 2>&1 | grep -i "threshold"
```

Or to see full logging flow:

```bash
python run.py 2>&1 | grep -E "(threshold|Reading|Row |Final|Created DetectTool|Thresholds:)"
```

---

## Files Modified

1. **detect_tool_manager.py**
   - Line 324: Added `Rows:` log
   - Line 338: Added row-by-row log
   - Line 344: Added `Final thresholds dict` log
   - Line 461: Added config creation log

2. **detect_tool.py**
   - Line 532: Added factory function log
   - Line 278: Added initialize log

---

## Next Steps After Diagnosis

Once you run the test and see the logs:

1. Share the logs here
2. I'll identify exactly where thresholds are lost
3. Apply fix based on diagnosis results

---

## Expected Successful Output Example

```
2025-10-30 17:45:08 [detect_tool_manager.py] INFO: Reading thresholds from table - Rows: 1
2025-10-30 17:45:08 [detect_tool_manager.py] INFO:   Row 0: pilsner333 = 0.8
2025-10-30 17:45:08 [detect_tool_manager.py] INFO: Final thresholds dict: {'pilsner333': 0.8}
2025-10-30 17:45:08 [detect_tool_manager.py] INFO: get_tool_config() - Thresholds from table: {'pilsner333': 0.8}
2025-10-30 17:45:08 [detect_tool.py] INFO: Created DetectTool from manager config
2025-10-30 17:45:08 [detect_tool.py] INFO:   Class thresholds: {'pilsner333': 0.8}
2025-10-30 17:45:08 [detect_tool.py] INFO:   Thresholds: {'pilsner333': 0.8}
2025-10-30 17:45:09 [result_tool.py] INFO: 🔍 ResultTool.process() - 1 detections, 1 thresholds, 1 selected classes
2025-10-30 17:45:09 [result_tool.py] INFO: ✅ RESULT: OK - pilsner333 confidence 0.93 meets threshold 0.8
```

When you see this output pattern, thresholds are working! ✅

