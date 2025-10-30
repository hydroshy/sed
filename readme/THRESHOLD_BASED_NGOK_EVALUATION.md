# ✅ Detect Tool + Result Tool - Threshold-Based NG/OK Evaluation

**Date:** 2025-10-30  
**Feature:** Confidence-based detection evaluation

---

## 📋 Overview

Bây giờ system hoạt động như sau:

1. **User chọn classes + thresholds** trong DetectTool UI
2. **DetectTool detect vật** và lấy confidence score
3. **DetectTool truyền** detections + class_thresholds + selected_classes vào context
4. **ResultTool so sánh** confidence vs threshold
5. **ResultTool output** OK/NG decision

---

## 🔄 Data Flow

```
User Interface (Detect Tab)
    ↓
DetectToolManager.get_tool_config()
    └─ classes: ['pilsner333']
    └─ class_thresholds: {'pilsner333': 0.5}
    ↓
Apply → DetectTool created with config
    ↓
Frame triggered
    ↓
DetectTool.process(frame)
    ├─ Run ONNX inference
    ├─ Get detections: [{'class_name': 'pilsner333', 'confidence': 0.93, ...}]
    └─ Output result:
       {
           'detections': [...],
           'class_thresholds': {'pilsner333': 0.5},
           'selected_classes': ['pilsner333'],
           ...
       }
    ↓
job_manager.run_current_job()
    └─ context.update(detect_tool_result) ← Merge detections + thresholds
    ↓
ResultTool.process(frame, context)
    ├─ Get: detections, class_thresholds, selected_classes from context
    ├─ For each detection:
    │   └─ Get class_name: 'pilsner333'
    │   └─ Get confidence: 0.93
    │   └─ Get threshold: 0.5
    │   └─ Compare: 0.93 >= 0.5 ✅ → OK
    └─ Output:
       {
           'ng_ok_result': 'OK',
           'ng_ok_similarity': 0.93,
           'ng_ok_reason': 'OK: pilsner333 confidence 0.93 meets threshold'
       }
    ↓
CameraManager._update_execution_label()
    └─ Display: "OK" (green)
```

---

## 💡 Example Scenarios

### Scenario 1: Detection meets threshold ✅
```
Setup:
  - Selected class: pilsner333
  - Threshold: 0.5

Detection:
  - pilsner333: confidence 0.93
  
Logic:
  0.93 >= 0.5? YES ✅
  
Result: OK (GREEN)
```

### Scenario 2: Detection below threshold ❌
```
Setup:
  - Selected class: pilsner333
  - Threshold: 0.95

Detection:
  - pilsner333: confidence 0.93
  
Logic:
  0.93 >= 0.95? NO ❌
  
Result: NG (RED)
```

### Scenario 3: Multiple detections (best one) ✅
```
Setup:
  - Selected classes: [pilsner333, corona]
  - Thresholds: {pilsner333: 0.6, corona: 0.7}

Detections:
  - pilsner333: confidence 0.92 (≥ 0.6) ✅
  - corona: confidence 0.65 (< 0.7) ❌
  
Logic:
  At least one detection meets threshold? YES ✅
  Best confidence: 0.92 (pilsner333)
  
Result: OK (GREEN) - pilsner333 passed
```

### Scenario 4: No detections ❌
```
Setup:
  - Selected classes: [pilsner333]
  - Threshold: 0.5

Detections:
  - (empty)

Logic:
  Any detection? NO ❌
  
Result: NG (RED) - reason: "No detections found"
```

---

## 🔧 Code Changes

### 1. DetectTool - Add thresholds to output

**File:** `tools/detection/detect_tool.py`

```python
result = {
    'detections': detections,
    'detection_count': len(detections),
    'class_thresholds': self.class_thresholds,  # ✅ ADD
    'selected_classes': self.selected_classes,  # ✅ ADD
    ...
}
```

### 2. ResultTool - New threshold evaluation

**File:** `tools/result_tool.py`

```python
def evaluate_ng_ok_by_threshold(self, detections, class_thresholds, selected_classes):
    """
    Compare each detection's confidence with its class-specific threshold
    
    Returns: (result, confidence, reason)
      - 'OK' if any detection >= threshold
      - 'NG' if no detection meets threshold
    """
    if not detections:
        return 'NG', 0.0, "No detections found"
    
    best_detection = None
    best_confidence = 0.0
    
    for detection in detections:
        class_name = detection['class_name']
        confidence = detection['confidence']
        
        # Skip if class not selected
        if class_name not in selected_classes:
            continue
        
        threshold = class_thresholds.get(class_name, 0.5)
        
        # Check if meets threshold
        if confidence >= threshold:
            if confidence > best_confidence:
                best_detection = detection
                best_confidence = confidence
    
    if best_detection:
        return 'OK', best_confidence, f"OK: {best_detection['class_name']} met threshold"
    else:
        return 'NG', 0.0, f"NG: No detection met confidence threshold"
```

### 3. ResultTool.process() - Use threshold evaluation

```python
def process(self, image, context):
    detections = context.get('detections', [])
    class_thresholds = context.get('class_thresholds', {})
    selected_classes = context.get('selected_classes', [])
    
    # Try threshold-based evaluation first
    if class_thresholds and selected_classes:
        ng_ok_status, similarity, reason = self.evaluate_ng_ok_by_threshold(
            detections,
            class_thresholds,
            selected_classes
        )
    # Fall back to reference-based
    elif self.ng_ok_enabled and self.ng_ok_reference_detections:
        ng_ok_status, similarity, reason = self.evaluate_ng_ok(detections)
    else:
        ng_ok_status, similarity, reason = None, None, "Disabled"
    
    return image, {
        'ng_ok_result': ng_ok_status,
        'ng_ok_similarity': similarity,
        'ng_ok_reason': reason
    }
```

---

## 📊 Console Log Output

```
2025-10-30 17:38:05,109 - tools.detection.detect_tool - INFO - ✅ DetectTool found 1 detections:
2025-10-30 17:38:05,109 - tools.detection.detect_tool - INFO -    Detection 0: pilsner333 (0.93)
2025-10-30 17:38:05,109 - tools.detection.detect_tool - INFO - ⏱️  DetectTool - 1 detections in 0.184s

🔍 ResultTool.process() - 1 detections, 1 thresholds, 1 selected classes
📊 Using threshold-based evaluation
🔍 Evaluating 1 detections against thresholds: {'pilsner333': 0.5}
   📊 pilsner333: confidence=0.93, threshold=0.5
      ✅ PASS: 0.93 >= 0.5
✅ RESULT: OK - OK: pilsner333 confidence 0.93 meets threshold
```

---

## ✅ UI Behavior

### When OK
```
Camera View:
  ┌─────────────────────────┐
  │ [Detection Box]         │
  │ pilsner333 (0.93)       │
  │                         │
  │ Status: OK ✅           │ ← GREEN
  └─────────────────────────┘
```

### When NG
```
Camera View:
  ┌─────────────────────────┐
  │ (Empty - no detections) │
  │                         │
  │ Status: NG ❌           │ ← RED
  └─────────────────────────┘
```

---

## 🎯 Key Features

✅ **Simple Logic**
- Just compare: detection_confidence >= class_threshold

✅ **Per-Class Thresholds**
- Each class can have different threshold
- E.g., pilsner333: 0.5, corona: 0.7

✅ **Multiple Classes Support**
- If ANY selected class meets threshold → OK
- Best detection wins (highest confidence)

✅ **Detailed Logging**
- Shows each detection vs threshold comparison
- Clear OK/NG reason

✅ **Backward Compatible**
- Falls back to reference-based evaluation if thresholds not set
- Reference mode still works for complex scenarios

---

## 🔍 Debug

To enable detailed debug output:

```python
# In ResultTool config
config['enable_debug'] = True
```

Output:
```
ResultTool: OK - OK: pilsner333 confidence 0.93 meets threshold
```

---

## 🚀 Next Steps

1. **Test:** Run application → Select class + threshold → Trigger
2. **Verify:** Check console for "OK: pilsner333 meets threshold"
3. **Observe:** UI should show green "OK" status
4. **Remove object:** Trigger again → Should show red "NG"

---

## 📝 Summary

| Component | Change |
|-----------|--------|
| DetectTool | Now outputs `class_thresholds` and `selected_classes` |
| ResultTool | New `evaluate_ng_ok_by_threshold()` method |
| Job Pipeline | Automatically merges DetectTool output → ResultTool input |
| UI | Shows OK/NG based on confidence vs threshold comparison |

**Result:** Simple, effective, and user-friendly NG/OK decision! ✅

