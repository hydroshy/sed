# DetectTool Simplified - Migration Guide

## Overview
This guide shows how to migrate from the old DetectTool with drawArea to the new simplified version that removes all draw area functionality.

---

## Phase 1: File Structure

### New Files Created
```
e:\PROJECT\sed\
├── tools/detection/
│   └── detect_tool_simplified.py          [NEW] Simplified DetectTool
│
├── gui/
│   └── detect_tool_manager_simplified.py  [NEW] Simplified manager
│
└── SIMPLIFIED_DETECT_TOOL_DOCUMENTATION.md [NEW] Full documentation
```

### Old Files (Can be kept as reference)
- `tools/detection/detect_tool.py` (Original with drawArea)
- `gui/detect_tool_manager.py` (Original with drawArea)

---

## Phase 2: Update Imports

### In main_window.py or wherever DetectToolManager is initialized:

**OLD:**
```python
from gui.detect_tool_manager import DetectToolManager

manager = DetectToolManager(self)
```

**NEW:**
```python
from gui.detect_tool_manager_simplified import DetectToolManager

manager = DetectToolManager(self)
```

---

## Phase 3: Verify UI Components

### Components That STAY THE SAME:
✅ `algorithmComboBox` - Model selection
✅ `classificationComboBox` - Class selection
✅ `addClassificationButton` - Add class
✅ `removeClassificationButton` - Remove class
✅ `classificationTableView` - Display classes + thresholds

### Components That MUST BE REMOVED:
❌ `drawAreaButton` (if exists)
❌ `x1PositionSpinBox` (or input)
❌ `x2PositionSpinBox` (or input)
❌ `y1PositionSpinBox` (or input)
❌ `y2PositionSpinBox` (or input)
❌ Any labels for drawing instructions
❌ Any detection area visualization code

---

## Phase 4: Update Configuration Handling

### Old Config Structure (with drawArea):
```python
{
    'model_name': 'yolov5s.onnx',
    'model_path': '/path/to/model.onnx',
    'class_names': ['person', 'car'],
    'selected_classes': ['person'],
    'class_thresholds': {'person': 0.6},
    'detection_region': (0, 0, 640, 480),  # ❌ REMOVE THIS
    'detection_area': {...},                # ❌ REMOVE THIS
    'x1': 0,                                # ❌ REMOVE THIS
    'y1': 0,                                # ❌ REMOVE THIS
    'x2': 640,                              # ❌ REMOVE THIS
    'y2': 480                               # ❌ REMOVE THIS
}
```

### New Config Structure (simplified):
```python
{
    'model_name': 'yolov5s.onnx',
    'model_path': '/path/to/model.onnx',
    'class_names': ['person', 'car'],
    'selected_classes': ['person'],
    'class_thresholds': {'person': 0.6},
    'confidence_threshold': 0.5,
    'nms_threshold': 0.45,
    'imgsz': 640,
    'visualize_results': True,
    'show_confidence': True,
    'show_class_names': True
}
```

### Code Changes Required:

**Remove any code that handles:**
```python
# ❌ DELETE THESE:
config['detection_region'] = (x1, y1, x2, y2)
config['detection_area'] = area_dict
detection_area = self._get_detection_area()
region_coords = config.get('detection_region')
area_info = config.get('detection_area')
```

**Keep configuration like:**
```python
# ✅ KEEP THESE:
config['selected_classes'] = manager.get_selected_classes()
config['class_thresholds'] = manager.get_class_thresholds()
config['model_name'] = model_name
config['model_path'] = model_path
```

---

## Phase 5: Update Job Creation

### Job Creation Method
The create_detect_tool_job() is still the same:

```python
from gui.detect_tool_manager_simplified import DetectToolManager

manager = DetectToolManager(main_window)
manager.setup_ui_components(
    algorithm_combo=ui.algorithmComboBox,
    classification_combo=ui.classificationComboBox,
    add_btn=ui.addClassificationButton,
    remove_btn=ui.removeClassificationButton,
    scroll_area=None,  # Can be None now
    table_view=ui.classificationTableView
)

# Create and apply detect tool
detect_tool = manager.create_detect_tool_job()
manager.apply_detect_tool_to_job()
```

---

## Phase 6: Verify Detection Processing

### Detection Now Works On:
✅ **Full Image** - No more area cropping
✅ **Selected Classes** - Filters by selected_classes list
✅ **Per-Class Thresholds** - Different threshold per class
✅ **Full Resolution** - No limitation to drawing area

### Processing Pipeline:
```
Camera Feed (Full Image)
    ↓
Letterbox Resize
    ↓
ONNX Inference
    ↓
NMS + Class Filtering
    ↓
Per-Class Threshold Filtering
    ↓
Output: Full Image with Detections
```

---

## Phase 7: Testing Checklist

### ✅ Basic Tests
- [ ] Application starts without errors
- [ ] Model dropdown loads correctly
- [ ] Can select a model
- [ ] Classes appear in class dropdown after model selection

### ✅ Class Management
- [ ] Can add class to table
- [ ] Can see default threshold (0.5) in table
- [ ] Can edit threshold in table
- [ ] Can remove class from table
- [ ] Class names display correctly in table

### ✅ Detection Tests
- [ ] Camera feed shows
- [ ] Detection works on full image
- [ ] Bounding boxes draw correctly
- [ ] Class names display with confidence
- [ ] Only selected classes are detected

### ✅ Threshold Tests
- [ ] Different per-class thresholds work
- [ ] High threshold filters more detections
- [ ] Low threshold shows more detections

### ✅ Integration Tests
- [ ] DetectTool creates successfully
- [ ] ResultTool adds after DetectTool
- [ ] Frame history labels display (reviewLabel_1-5)
- [ ] NG/OK status shows correctly
- [ ] Job execution completes without error

---

## Phase 8: Common Issues & Solutions

### Issue: Import Error
```
ModuleNotFoundError: No module named 'tools.detection.detect_tool_simplified'
```
**Solution:** Make sure you're using the correct new import path

### Issue: Model not loading
```
Error initializing DetectTool: Model not found
```
**Solution:** Verify model path in get_tool_config() is correct

### Issue: Classes not appearing
```
Warning: No class selected for detection
```
**Solution:** Make sure to select classes in table before running detection

### Issue: Detection area still being used
```
Error: detection_region not found in config
```
**Solution:** Remove all detection_region references from code, use full image instead

### Issue: Old manager still being used
```
AttributeError: '_get_detection_area' object has no attribute
```
**Solution:** Update import to use `detect_tool_manager_simplified`

---

## Phase 9: Rollback Plan

If you need to go back to old version:

```python
# Switch back to old manager
from gui.detect_tool_manager import DetectToolManager

# Use old DetectTool
from tools.detection.detect_tool import DetectTool
```

But recommended to delete drawArea UI elements first if using old version.

---

## Summary of Changes

### What Changed:
| Aspect | Old | New |
|--------|-----|-----|
| Detection Area | UI to draw region | Full image only |
| Coordinates | x1, y1, x2, y2 stored | Processed coords only |
| Config Size | Large (with region) | Compact (no region) |
| Complexity | Higher (area handling) | Lower (full image) |
| Performance | Depends on region size | Consistent |

### What Stayed Same:
| Aspect | Status |
|--------|--------|
| Model selection | ✅ Same |
| Class management | ✅ Same |
| Threshold system | ✅ Same |
| Inference pipeline | ✅ Same |
| Job integration | ✅ Same |
| ResultManager | ✅ Same |
| Frame history | ✅ Same |

---

## Quick Start

### For New Users:
1. Use `detect_tool_manager_simplified.py`
2. Initialize with UI components
3. Select model → Select classes → Set thresholds
4. Create detect tool job
5. Add to job manager

### For Migrating Users:
1. Update import to `detect_tool_manager_simplified`
2. Remove drawArea UI elements from UI file
3. Remove detection_region/detection_area from config
4. Test model + class selection
5. Run detection on full image
6. Verify all tests pass

---

## Support

For detailed technical information, see:
- `SIMPLIFIED_DETECT_TOOL_DOCUMENTATION.md` - Full technical docs
- `tools/detection/detect_tool_simplified.py` - Source code
- `gui/detect_tool_manager_simplified.py` - Manager code
