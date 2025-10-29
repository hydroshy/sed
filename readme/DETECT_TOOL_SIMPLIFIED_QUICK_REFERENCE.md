# DetectTool Simplified - Quick Reference

## What Was Removed? 🗑️

```
❌ drawAreaButton
❌ x1Position, x2Position, y1Position, y2Position (coordinates)
❌ detection_region (config)
❌ detection_area (config)
❌ _prepare_detection_region() (method)
❌ _get_detection_area() (method)
❌ All area cropping logic
```

## What Remains? ✅

```
✅ algorithmComboBox (model selection)
✅ classificationComboBox (class selection)
✅ addClassificationButton
✅ removeClassificationButton
✅ classificationTableView (class + threshold display)
✅ All ONNX inference logic
✅ All detection processing logic
✅ Per-class threshold system
```

## File Locations

```
NEW SIMPLIFIED FILES:
├── tools/detection/detect_tool_simplified.py
├── gui/detect_tool_manager_simplified.py
├── SIMPLIFIED_DETECT_TOOL_DOCUMENTATION.md
└── DETECT_TOOL_SIMPLIFIED_MIGRATION_GUIDE.md

OLD FILES (keep as reference):
├── tools/detection/detect_tool.py
└── gui/detect_tool_manager.py
```

## How to Use

### Import
```python
from gui.detect_tool_manager_simplified import DetectToolManager
from tools.detection.detect_tool_simplified import DetectTool
```

### Initialize
```python
manager = DetectToolManager(main_window)
manager.setup_ui_components(
    algorithm_combo=ui.algorithmComboBox,
    classification_combo=ui.classificationComboBox,
    add_btn=ui.addClassificationButton,
    remove_btn=ui.removeClassificationButton,
    scroll_area=None,
    table_view=ui.classificationTableView
)
```

### Get Configuration
```python
config = manager.get_tool_config()
# Returns: {
#     'model_name': 'yolov5s.onnx',
#     'model_path': '/path/to/model.onnx',
#     'class_names': ['person', 'car'],
#     'selected_classes': ['person'],
#     'class_thresholds': {'person': 0.6}
# }
```

### Create Detection Tool
```python
detect_tool = manager.create_detect_tool_job()
manager.apply_detect_tool_to_job()
```

## Config Structure

### OLD (with drawArea)
```python
{
    'model_name': '...',
    'model_path': '...',
    'selected_classes': [...],
    'detection_region': (0, 0, 640, 480),      # ❌ GONE
    'detection_area': {...},                    # ❌ GONE
    'x1': 0, 'y1': 0, 'x2': 640, 'y2': 480    # ❌ GONE
}
```

### NEW (simplified)
```python
{
    'model_name': 'yolov5s.onnx',
    'model_path': '/path/to/yolov5s.onnx',
    'class_names': ['person', 'car', 'dog'],
    'selected_classes': ['person', 'car'],
    'class_thresholds': {'person': 0.6, 'car': 0.5},
    'confidence_threshold': 0.5,
    'nms_threshold': 0.45,
    'imgsz': 640
}
```

## Detection Output

```python
result = detect_tool.process(image)
# Returns: (output_image, {
#     'detections': [
#         {
#             'class_name': 'person',
#             'confidence': 0.95,
#             'x1': 100, 'y1': 50,
#             'x2': 200, 'y2': 300,
#             'width': 100, 'height': 250
#         }
#     ],
#     'detection_count': 1,
#     'inference_time': 0.045,
#     'total_time': 0.050
# })
```

## UI Elements - What Changed

| Component | Old | New |
|-----------|-----|-----|
| Model Selection | ✅ algorithmComboBox | ✅ algorithmComboBox |
| Class Selection | ✅ classificationComboBox | ✅ classificationComboBox |
| Add Button | ✅ Present | ✅ Present |
| Remove Button | ✅ Present | ✅ Present |
| Class Table | ✅ Present | ✅ Present (improved) |
| Draw Area Button | ❌ Removed | ✅ Gone |
| Position Inputs | ❌ Removed | ✅ Gone |
| Area Labels | ❌ Removed | ✅ Gone |

## Table Structure (classificationTableView)

```
┌──────────────────┬──────────┐
│  Class Name      │ Threshold│
├──────────────────┼──────────┤
│ person           │  0.6     │
│ car              │  0.5     │
│ dog              │  0.55    │
└──────────────────┴──────────┘
```

### How to Use Table:
1. Add class: Select from dropdown → Click "Add" button
2. Set threshold: Double-click threshold cell → Enter value (0.0-1.0)
3. Remove class: Select row → Click "Remove" button

## Key Methods

### DetectToolManager
```python
manager.load_available_models()              # Load ONNX models
manager.set_current_model(model_name)        # Select model
manager.get_class_thresholds()               # Get threshold dict
manager.set_selected_classes(class_list)     # Set classes
manager.get_tool_config()                    # Get config (NO detection_area)
manager.load_tool_config(config)             # Load config
manager.create_detect_tool_job()             # Create DetectTool
manager.apply_detect_tool_to_job()           # Apply to job manager
```

### DetectTool
```python
detect_tool.initialize_detection()           # Load ONNX model
detect_tool.process(image)                   # Run detection
detect_tool.get_last_detections()            # Get last results
detect_tool.update_config(new_config)        # Update config
detect_tool.set_execution_enabled(True/False) # Enable/disable
detect_tool.cleanup()                        # Cleanup resources
```

## Workflow

```
User Interface
    ↓
1. Select Model (algorithmComboBox)
    ↓
2. Load Classes (classificationComboBox populated)
    ↓
3. Add Classes (classificationTableView)
    ↓
4. Set Thresholds (edit table cells)
    ↓
5. Get Config (manager.get_tool_config())
    ↓
6. Create DetectTool (manager.create_detect_tool_job())
    ↓
7. Run Detection (detect_tool.process(image))
    ↓
8. Output Results (detections + visualization)
```

## Performance Tips

1. **Use smaller models** for faster inference
   - yolov5n (nano) - fastest
   - yolov5s (small) - balanced
   - yolov5m (medium) - slower but more accurate

2. **Set appropriate thresholds** to filter unwanted detections
   - High threshold (0.7-0.9) - fewer false positives
   - Low threshold (0.3-0.5) - more detections

3. **Use GPU** if available
   - Automatic GPU detection (CUDAExecutionProvider)
   - 5-10x faster than CPU

4. **Letterbox caching** is automatic
   - Avoids redundant preprocessing

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Model not loading | Check model path exists |
| Classes not showing | Select model first |
| Detection slow | Use smaller model or GPU |
| High false positives | Increase threshold |
| Missing detections | Decrease threshold |
| Import error | Use new import path (detect_tool_manager_simplified) |

## Migration Checklist

- [ ] Update imports to use `_simplified` versions
- [ ] Remove drawArea UI elements
- [ ] Remove detection_region/detection_area from config
- [ ] Test model selection
- [ ] Test class selection
- [ ] Test threshold editing
- [ ] Test detection on full image
- [ ] Verify all tests pass

## Documentation Files

1. **SIMPLIFIED_DETECT_TOOL_DOCUMENTATION.md**
   - Full technical documentation
   - Architecture details
   - Configuration structure
   - API reference

2. **DETECT_TOOL_SIMPLIFIED_MIGRATION_GUIDE.md**
   - Step-by-step migration
   - Detailed phase-by-phase guide
   - Common issues & solutions
   - Testing checklist

3. **DETECT_TOOL_SIMPLIFIED_QUICK_REFERENCE.md** (this file)
   - Quick lookup reference
   - One-page summary
   - Common tasks
   - Troubleshooting

## Key Differences Summary

| Aspect | Old Version | New Version |
|--------|-------------|-------------|
| **Area Selection** | UI drawing required | Full image only |
| **Config Complexity** | Higher (coordinates) | Lower (just classes) |
| **Code Maintainability** | Complex | Simpler |
| **UI Simplicity** | More elements | Fewer elements |
| **Detection Region** | Configurable | Always full image |
| **Inference Speed** | Varies by region | Consistent |
| **Class Thresholds** | Basic support | Full per-class support |

---

**For more details, see SIMPLIFIED_DETECT_TOOL_DOCUMENTATION.md**
