# Simplified DetectTool Refactoring - Complete Documentation

## Objective
Refactor DetectTool to remove drawArea functionality and simplify to basic model + class selection UI.

**Status:** ✅ COMPLETE

## Changes Made

### 1. Created `tools/detection/detect_tool_simplified.py`
**New Simplified DetectTool Implementation**

#### What's Removed:
- ❌ All detection_region/detection_area configuration
- ❌ drawAreaButton UI elements
- ❌ x1Position, x2Position, y1Position, y2Position coordinates
- ❌ Detection area drawing/visualization
- ❌ `_prepare_detection_region()` with area cropping logic

#### What's Kept:
- ✅ Core ONNX inference pipeline
- ✅ Letterbox preprocessing (_letterbox_fast)
- ✅ NMS algorithm (_nms_numpy_fast)
- ✅ Universal YOLO decoder (_yolo_universal_decode)
- ✅ Model loading and initialization
- ✅ Class filtering by selected_classes
- ✅ Per-class thresholds (class_thresholds)
- ✅ Detection visualization on full image
- ✅ Performance optimizations (caching, vectorized operations)

#### Configuration Setup (setup_config):
```python
'model_name'            # Model identifier
'model_path'            # Path to ONNX model file
'class_names'           # List of all classes from model
'selected_classes'      # List of selected classes for detection
'class_thresholds'      # Dict of per-class confidence thresholds
'confidence_threshold'  # Global confidence threshold (default: 0.5)
'nms_threshold'         # NMS IoU threshold (default: 0.45)
'imgsz'                 # Image size for letterbox (default: 640)
```

#### Key Methods:
| Method | Purpose |
|--------|---------|
| `setup_config()` | Initialize default configuration |
| `initialize_detection()` | Load ONNX model and cache parameters |
| `process(image, context)` | Run detection on full image |
| `_letterbox_fast()` | Fast letterbox resize with caching |
| `_nms_numpy_fast()` | Optimized NMS using vectorized numpy |
| `_yolo_universal_decode()` | Universal YOLO output decoder |
| `_draw_detections()` | Visualize detections on output image |
| `get_tool_config()` | Get current configuration |
| `update_config()` | Update tool configuration |

#### Usage:
```python
from tools.detection.detect_tool_simplified import create_detect_tool_from_manager_config

# Create from manager config
config = {
    'model_name': 'yolov5s.onnx',
    'model_path': '/path/to/yolov5s.onnx',
    'class_names': ['person', 'car', 'dog'],
    'selected_classes': ['person', 'car'],
    'class_thresholds': {'person': 0.6, 'car': 0.5}
}

detect_tool = create_detect_tool_from_manager_config(config)
```

---

### 2. Created `gui/detect_tool_manager_simplified.py`
**New Simplified DetectToolManager Implementation**

#### What's Removed:
- ❌ Detection area UI elements (drawAreaButton, position inputs)
- ❌ `_get_detection_area()` method
- ❌ Detection region config handling
- ❌ Area drawing logic

#### What's Kept:
- ✅ Model selection (algorithmComboBox)
- ✅ Class selection (classificationComboBox)
- ✅ Add class button (addClassificationButton)
- ✅ Remove class button (removeClassificationButton)
- ✅ Classification table view (classificationTableView)
- ✅ Class threshold management
- ✅ Per-class confidence thresholds

#### UI Components Managed:
| Component | Purpose |
|-----------|---------|
| `algorithm_combo` | Model selection dropdown |
| `classification_combo` | Class selection dropdown |
| `add_classification_btn` | Add selected class to table |
| `remove_classification_btn` | Remove selected class from table |
| `classification_table` | Display selected classes with thresholds |
| `classification_model` | QStandardItemModel for table |

#### Configuration Methods:
| Method | Purpose |
|--------|---------|
| `get_tool_config()` | Get current tool config (NO detection_area) |
| `load_tool_config(config)` | Load tool config (NO detection_area) |
| `load_available_models()` | Populate model dropdown |
| `_load_model_classes()` | Populate class dropdown |
| `get_class_thresholds()` | Get threshold dict from table |
| `set_selected_classes()` | Set classes in table |
| `load_selected_classes_with_thresholds()` | Load classes with thresholds |

#### Table Structure:
```
┌──────────────────┬──────────┐
│  Class Name      │ Threshold│
├──────────────────┼──────────┤
│ person           │  0.6     │
│ car              │  0.5     │
│ dog              │  0.55    │
└──────────────────┴──────────┘
```

#### Usage:
```python
from gui.detect_tool_manager_simplified import DetectToolManager

# Initialize manager
manager = DetectToolManager(main_window)

# Setup UI components
manager.setup_ui_components(
    algorithm_combo=ui.algorithmComboBox,
    classification_combo=ui.classificationComboBox,
    add_btn=ui.addClassificationButton,
    remove_btn=ui.removeClassificationButton,
    scroll_area=ui.classificationScrollArea,
    table_view=ui.classificationTableView
)

# Get configuration
config = manager.get_tool_config()

# Create and apply detection tool
detect_tool = manager.create_detect_tool_job()
manager.apply_detect_tool_to_job()
```

---

## How to Migrate from Old to New

### Step 1: Replace Imports
**Old:**
```python
from tools.detection.detect_tool import DetectTool
from gui.detect_tool_manager import DetectToolManager
```

**New:**
```python
from tools.detection.detect_tool_simplified import DetectTool
from gui.detect_tool_manager_simplified import DetectToolManager
```

### Step 2: Remove Detection Area UI Elements
Remove these from your UI file:
- drawAreaButton
- x1PositionSpinBox (or input field)
- x2PositionSpinBox (or input field)
- y1PositionSpinBox (or input field)
- y2PositionSpinBox (or input field)
- Any labels associated with these

### Step 3: Keep These UI Elements
These remain unchanged:
- algorithmComboBox (model selection)
- classificationComboBox (class selection)
- addClassificationButton
- removeClassificationButton
- classificationTableView (class + threshold display)

### Step 4: Update Configuration Handling
Remove any code that handles:
- detection_region
- detection_area
- Area coordinate validation

The new simplified config only needs:
```python
config = {
    'model_name': str,
    'model_path': str,
    'class_names': List[str],
    'selected_classes': List[str],
    'class_thresholds': Dict[str, float]
}
```

---

## Processing Pipeline

### Input Image Processing Flow:
```
Input Image (BGR)
    ↓
Letterbox Resize (640x640 with padding)
    ↓
RGB Convert + Normalization (0-1)
    ↓
Transpose to [1, 3, H, W] format
    ↓
ONNX Inference
    ↓
Universal YOLO Decoder
    ↓
NMS (IoU threshold: 0.45)
    ↓
Class Filtering (selected_classes only)
    ↓
Per-Class Threshold Filtering
    ↓
Coordinate Denormalization
    ↓
Bounding Box Drawing
    ↓
Output Image + Detection Results
```

### Detection Result Format:
```python
{
    'detections': [
        {
            'class_id': int,
            'class_name': str,
            'confidence': float,  # 0-1
            'x1': float,          # Pixel coordinates
            'y1': float,
            'x2': float,
            'y2': float,
            'width': float,
            'height': float
        },
        # ... more detections
    ],
    'detection_count': int,
    'inference_time': float,  # seconds
    'total_time': float,      # seconds
    'model': str,
    'classes_total': int,
    'classes_selected': int
}
```

---

## Performance Optimizations

### 1. Letterbox Caching
- Caches last preprocessed image
- Returns cached result if image shape unchanged
- Avoids redundant preprocessing

### 2. Vectorized NMS
- Numpy vectorized operations for IoU calculation
- 2-3x faster than loop-based NMS

### 3. Contiguous Array Handling
- Checks for C-contiguous arrays
- Fast path for contiguous data

### 4. ONNX Providers
- GPU acceleration (CUDAExecutionProvider) if available
- Automatic fallback to CPU

### 5. Inference Timing
- Tracks preprocessing, inference, and total times
- Useful for performance monitoring

---

## Class Threshold System

### Per-Class Confidence Thresholds
Unlike simple confidence threshold, per-class thresholds allow different detection sensitivities for different objects:

```python
class_thresholds = {
    'person': 0.6,   # Higher threshold for person detection
    'car': 0.5,      # Standard threshold for cars
    'bike': 0.55     # Medium threshold for bikes
}
```

### Threshold Application in Detection:
```python
for detection in detections_raw:
    # Get class-specific threshold
    threshold = class_thresholds.get(class_name, global_threshold)
    
    # Apply threshold
    if confidence >= threshold:
        # Accept detection
```

### UI Table Management:
```
User adds "person" class
    ↓
Table shows: person | 0.5 (default)
    ↓
User edits threshold to 0.6
    ↓
get_class_thresholds() returns {'person': 0.6}
    ↓
DetectTool applies 0.6 threshold to person detections
```

---

## Migration Checklist

- [ ] Backup original files
- [ ] Replace DetectTool import with detect_tool_simplified
- [ ] Replace DetectToolManager import with detect_tool_manager_simplified
- [ ] Remove drawArea UI elements from UI file
- [ ] Update main_window.py to use new manager
- [ ] Remove any detection_region/detection_area handling code
- [ ] Test model selection
- [ ] Test class selection and addition
- [ ] Test class removal
- [ ] Test threshold editing in table
- [ ] Test detection on live camera feed
- [ ] Verify frame history labels still work (reviewLabel_1-5)
- [ ] Verify ResultManager integration still works

---

## Troubleshooting

### Issue: Model not loading
**Solution:** Verify model path exists and model_name matches model file

### Issue: Classes not appearing in dropdown
**Solution:** Ensure model_manager correctly loads model info

### Issue: Detection not filtering by selected classes
**Solution:** Check that selected_classes list is properly populated in config

### Issue: Threshold not applied
**Solution:** Verify threshold is in class_thresholds dict with correct class name

### Issue: Performance slow
**Solution:** 
- Check if GPU is available (CUDAExecutionProvider)
- Reduce model size (use yolov5n instead of yolov5l)
- Check image resolution (larger images = slower inference)

---

## Files Status

| File | Status | Changes |
|------|--------|---------|
| `tools/detection/detect_tool_simplified.py` | ✅ NEW | Full rewrite, removed drawArea |
| `gui/detect_tool_manager_simplified.py` | ✅ NEW | Full rewrite, removed drawArea |
| `tools/detection/detect_tool.py` | ⏳ KEEP | Original, can be kept for reference |
| `gui/detect_tool_manager.py` | ⏳ KEEP | Original, can be kept for reference |

---

## Summary

✅ **Simplified DetectTool removes all detection_area functionality**
✅ **Keeps core YOLO inference pipeline intact**
✅ **UI simplified to: model selection + class/threshold management**
✅ **Full image detection (no region cropping)**
✅ **Per-class threshold support maintained**
✅ **Performance optimizations preserved**

The new implementation is cleaner, easier to maintain, and focuses on the essential detection workflow without the complexity of drawing and managing detection regions.
