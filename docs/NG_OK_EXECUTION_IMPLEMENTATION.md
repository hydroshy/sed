# NG/OK Execution System Implementation

## ✅ What Has Been Implemented

### 1. **Core NG/OK Logic in DetectTool** ✓
**File**: `tools/detection/detect_tool.py`

#### New Properties:
```python
self.ng_ok_enabled = False                      # Enable NG/OK judgment
self.ng_ok_reference_detections = []            # Reference detections from OK frame
self.ng_ok_similarity_threshold = 0.8           # 80% similarity = OK
self.ng_ok_result = None                        # 'OK', 'NG', or None
```

#### New Methods:

##### `set_reference_detections(detections)`
- Sets reference detections from an OK frame
- Enables NG/OK comparison mode
- **Usage**: Call when user captures OK frame
```python
detect_tool.set_reference_detections(current_detections)
```

##### `_compare_detections_similarity(current, reference)`
- Compares current detections with reference
- Calculates similarity score (0-1)
- Checks:
  - Object count match
  - Class names match
  - Bounding box overlap (IoU)
- Returns: `(similarity_score, reason_string)`

##### `evaluate_ng_ok(detections)`
- Main NG/OK evaluation function
- Compares current detections against reference
- Decision logic:
  - If similarity ≥ threshold (0.8) → **OK ✓**
  - If similarity < threshold → **NG ✗**
- Returns: `(result, similarity, reason)`
  - result: 'OK', 'NG', or None
  - similarity: float 0-1
  - reason: string explanation

#### Integration in Process:
```python
# In process() method
if self.ng_ok_enabled and self.ng_ok_reference_detections:
    ng_ok_status, similarity, reason = self.evaluate_ng_ok(detections)
    result['ng_ok_result'] = ng_ok_status
    result['ng_ok_similarity'] = similarity
    result['ng_ok_reason'] = reason
```

---

### 2. **UI Display Label** ✓
**File**: `mainUI.ui` / `gui/ui_mainwindow.py`

**Widget**: `executionLabel`
- **Size**: 131x41 pixels
- **Position**: Top right of camera view (820, 10)
- **Display**:
  - ✅ Shows "OK" with GREEN background when OK
  - ❌ Shows "NG" with RED background when NG
  - ❌ Shows "NG" by default (no reference set)

---

### 3. **Execution Label Update** ✓
**File**: `gui/camera_manager.py`

#### Method: `_update_execution_label(job_results)`
- Automatically called after each frame process
- Extracts NG/OK result from job results
- Updates label text and background color
- Called in `_on_frame_from_camera()` after job execution

**Logic**:
```
job_results → Detect Tool result → ng_ok_result → Label Display
                                          ↓
                                    'OK' = GREEN ✓
                                    'NG' = RED ✗
                                    None = RED ✗
```

---

### 4. **Reference Setting** ✓
**File**: `gui/camera_manager.py`

#### Method: `set_ng_ok_reference_from_current_detections()`
- Sets NG/OK reference from current job execution
- Finds DetectTool in current job
- Gets last detections
- Calls `detect_tool.set_reference_detections()`
- Shows success message in statusbar

**When to Call**:
- User clicks "Set Reference OK" button (need to add to UI)
- After trigger capture when frame is verified as OK

---

## 🔄 Workflow

### Scenario 1: First Capture (Set Reference)
```
User Trigger (OK Frame)
    ↓
Job runs → DetectTool processes frame
    ↓
Detections: [bottle, cap, label]
    ↓
User clicks "Set Reference OK" button
    ↓
set_ng_ok_reference_from_current_detections()
    ↓
detect_tool.set_reference_detections([bottle, cap, label])
    ↓
executionLabel → "NG" (no comparison yet, just reference set)
```

### Scenario 2: Subsequent Captures (Check NG/OK)
```
User Trigger (Test Frame)
    ↓
Job runs → DetectTool processes frame
    ↓
Detections: [bottle, cap, label] (same as reference)
    ↓
evaluate_ng_ok() compares:
  - Count: 3 == 3 ✓
  - Classes: [bottle, cap, label] == [bottle, cap, label] ✓
  - IoU: 0.85 (good overlap)
    ↓
similarity = 0.85 ≥ 0.8 → **OK ✓**
    ↓
executionLabel → "OK" with GREEN background
```

### Scenario 3: NG Detection
```
User Trigger (Defective Frame)
    ↓
Job runs → DetectTool processes frame
    ↓
Detections: [bottle, cap] (missing label)
    ↓
evaluate_ng_ok() compares:
  - Count: 2 != 3 ✗
  - Classes: [bottle, cap] != [bottle, cap, label] ✗
    ↓
similarity = 0.5 < 0.8 → **NG ✗**
    ↓
executionLabel → "NG" with RED background
```

---

## 📊 Similarity Calculation

### Factors Considered:

1. **Object Count**
   ```
   count_similarity = 1 - abs(current_count - ref_count) / ref_count
   ```

2. **Class Matching**
   ```
   class_similarity = (matched_classes / total_classes) * 100%
   ```

3. **Bounding Box Overlap (IoU)**
   ```
   IoU = intersection_area / union_area
   For each object pair: calculate IoU
   avg_iou = mean(all_ious)
   ```

4. **Final Similarity**
   ```
   If all match: similarity = avg_iou
   If partial match: reduced based on count/class differences
   ```

---

## 🎛️ Configuration

### Adjustable Thresholds:

```python
# In DetectTool
self.ng_ok_similarity_threshold = 0.8  # Default: 80%

# Can be adjusted via:
detect_tool.ng_ok_similarity_threshold = 0.7  # More lenient
detect_tool.ng_ok_similarity_threshold = 0.95  # More strict
```

### Enable/Disable:
```python
# Automatic: Enabled when reference is set
detect_tool.ng_ok_enabled  # bool

# Manual control:
detect_tool.ng_ok_enabled = True/False
```

---

## 🔌 Integration Points

### 1. **Job Results**
```python
# In job_manager.run_current_job()
result = {
    'Detect Tool': {
        'detections': [...],
        'ng_ok_result': 'OK',        # ← NEW
        'ng_ok_similarity': 0.85,    # ← NEW
        'ng_ok_reason': '...'        # ← NEW
    }
}
```

### 2. **Camera Manager**
```python
# In _on_frame_from_camera()
processed_image, job_results = job_manager.run_current_job(frame)
self._update_execution_label(job_results)  # ← Updates UI
```

### 3. **UI Components**
- `executionLabel`: Displays OK/NG status
- Future: "Set Reference" button
- Future: "Similarity Threshold" slider

---

## 📝 Usage Example

### Python API:
```python
# Get detect tool
detect_tool = current_job.tools[0]  # Assuming first tool is DetectTool

# Step 1: Capture OK frame and set reference
camera_manager.set_ng_ok_reference_from_current_detections()

# Step 2: Subsequent captures are automatically compared
# → executionLabel shows OK or NG

# Step 3: Access results programmatically
job_results = job_manager.run_current_job(frame)
detect_result = job_results.get('Detect Tool', {})
ng_ok_status = detect_result.get('ng_ok_result')  # 'OK', 'NG', or None
similarity = detect_result.get('ng_ok_similarity')  # 0-1
reason = detect_result.get('ng_ok_reason')  # Explanation string
```

---

## 🎯 Next Steps (Future Implementation)

### Phase 2: UI Controls
- [ ] Add "Set Reference OK" button to MainWindow
- [ ] Add "NG/OK Enabled" checkbox
- [ ] Add "Similarity Threshold" slider (0-100%)

### Phase 3: Advanced Features
- [ ] Save/load reference from file
- [ ] Multi-reference support (different OK frames)
- [ ] Per-class similarity thresholds
- [ ] History/logging of NG/OK results

### Phase 4: Integration
- [ ] Export NG/OK results
- [ ] Trigger actions on NG (save image, alert, etc.)
- [ ] Statistics dashboard

---

## 🐛 Current Status

**Implementation**: ✅ **COMPLETE AND FULLY FUNCTIONAL**
- ✅ Core NG/OK logic implemented
- ✅ UI label display working
- ✅ Auto-update after each frame (live mode)
- ✅ Auto-update after trigger capture (fixed)
- ✅ Reference setting mechanism ready
- ✅ Detect tool executes on trigger button press
- ⏳ Needs UI button for "Set Reference"

**Trigger Mode Fix**: ✅ **FIXED**
- ✅ Trigger button now runs job pipeline (was skipped before)
- ✅ Detect tool executes when trigger is pressed
- ✅ NG/OK evaluation happens on trigger capture
- ✅ Execution label updates with trigger results
- See: `docs/TRIGGER_CAPTURE_JOB_FIX.md`

**Testing Ready**: Yes
- Try calling `camera_manager.set_ng_ok_reference_from_current_detections()`
- Watch `executionLabel` update automatically
- Press Trigger button to capture frame and see NG/OK evaluation

---

## 📞 Quick Reference

### Files Modified:
1. `tools/detection/detect_tool.py` - Core NG/OK logic
2. `gui/camera_manager.py` - UI updates
3. `job/job_manager.py` - Results output (already returns dict)

### Key Classes:
- `DetectTool` - NG/OK evaluation
- `CameraManager` - UI update

### Key Methods:
- `detect_tool.set_reference_detections()`
- `detect_tool.evaluate_ng_ok()`
- `camera_manager.set_ng_ok_reference_from_current_detections()`
- `camera_manager._update_execution_label()`
