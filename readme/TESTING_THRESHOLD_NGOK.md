# 🧪 Testing Guide - Threshold-Based NG/OK

**Date:** 2025-10-30

---

## 📋 Test Steps

### Step 1: Start Application
```bash
cd e:\PROJECT\sed
python run.py
```

### Step 2: Setup Detection Tool
```
1. Go to "Detect" tab
2. Select model (e.g., pilsner_detection.onnx)
3. Select classes (e.g., pilsner333)
4. Set confidence threshold (e.g., 0.5)
5. Click "Apply"
```

**Expected Console Output:**
```
================================================================================
🚀 apply_detect_tool_to_job() START
📦 Creating DetectTool...
✅ DetectTool created: Detect Tool (ID: 2)
🔗 Adding DetectTool to job...
✅ Added DetectTool to job. Current tools: 2
   Workflow: ['Camera Source', 'Detect Tool']
================================================================================
```

### Step 3: Go to Camera Tab
```
1. Click "Camera" tab
2. Setup should show detection area overlay (if configured)
3. Camera stream should be live
```

### Step 4: Capture with Object Present (Should be OK)
```
1. Place beer bottle in front of camera
2. Click "Trigger" button
3. Wait for processing (should take ~200ms)
```

**Expected Console Output:**
```
🔍 DetectTool.process() called - Image shape: (480, 640, 3)
✅ DetectTool initialized, starting detection...
✅ DetectTool found 1 detections:
   Detection 0: pilsner333 (0.93)
⏱️  DetectTool - 1 detections in 0.184s (inference: 0.171s)

🔍 ResultTool.process() - 1 detections, 1 thresholds, 1 selected classes
📊 Using threshold-based evaluation
🔍 Evaluating 1 detections against thresholds: {'pilsner333': 0.5}
   📊 pilsner333: confidence=0.93, threshold=0.5
      ✅ PASS: 0.93 >= 0.5
✅ RESULT: OK - OK: pilsner333 confidence 0.93 meets threshold
```

**Expected UI Result:**
```
Status: OK ✅ (GREEN COLOR)
```

---

### Step 5: Capture with Object Removed (Should be NG)
```
1. Remove beer bottle from camera
2. Click "Trigger" button
3. Wait for processing
```

**Expected Console Output:**
```
🔍 DetectTool.process() called - Image shape: (480, 640, 3)
✅ DetectTool initialized, starting detection...
❌ DetectTool found NO detections
⏱️  DetectTool - 0 detections in 0.145s (inference: 0.128s)

🔍 ResultTool.process() - 0 detections, 1 thresholds, 1 selected classes
📊 Using threshold-based evaluation
🔍 Evaluating 0 detections against thresholds: {'pilsner333': 0.5}
✅ RESULT: NG - NG: No detection met confidence threshold
```

**Expected UI Result:**
```
Status: NG ❌ (RED COLOR)
```

---

### Step 6: Test with Low Confidence (Should be NG)
```
1. Place beer bottle partially in frame (low confidence)
2. Set threshold higher than object confidence
   - If bottle detected at 0.45 confidence
   - Set threshold to 0.5 or higher
3. Click "Trigger"
```

**Expected Console Output:**
```
🔍 Evaluating 1 detections against thresholds: {'pilsner333': 0.5}
   📊 pilsner333: confidence=0.45, threshold=0.5
      ❌ FAIL: 0.45 < 0.5
✅ RESULT: NG - NG: No detection met confidence threshold
```

**Expected UI Result:**
```
Status: NG ❌ (RED COLOR) - Even though object detected
```

---

### Step 7: Test Multiple Classes
```
1. Go to Detect tab
2. Select multiple classes: [pilsner333, corona]
3. Set different thresholds:
   - pilsner333: 0.6
   - corona: 0.7
4. Apply
5. Trigger with pilsner bottle
```

**Expected Console Output:**
```
🔍 Evaluating 1 detections against thresholds: {'pilsner333': 0.6, 'corona': 0.7}
   📊 pilsner333: confidence=0.93, threshold=0.6
      ✅ PASS: 0.93 >= 0.6
   📊 corona: confidence=0.65, threshold=0.7
      ❌ FAIL: 0.65 < 0.7
✅ RESULT: OK - OK: pilsner333 confidence 0.93 meets threshold
```

**Expected UI Result:**
```
Status: OK ✅ (GREEN COLOR) - pilsner333 passed
```

---

## ✅ Verification Checklist

- [ ] DetectTool logs show "found X detections"
- [ ] DetectTool output includes `class_thresholds` and `selected_classes`
- [ ] ResultTool logs show "Using threshold-based evaluation"
- [ ] ResultTool compares each detection vs threshold
- [ ] UI shows OK (green) when confidence >= threshold
- [ ] UI shows NG (red) when confidence < threshold
- [ ] UI shows NG (red) when no detections
- [ ] Multiple classes work correctly
- [ ] Each class uses its own threshold

---

## 🐛 Troubleshooting

### Issue: ResultTool shows "Disabled"
**Problem:** Thresholds not being passed
**Solution:** Check DetectTool output includes `class_thresholds` key

### Issue: Always NG even with object
**Problem:** Threshold too high
**Solution:** Lower the threshold value in Detect tab

### Issue: Console shows no detection but UI shows OK
**Problem:** Stale context data
**Solution:** Restart application

### Issue: Multiple classes not working
**Problem:** Class names don't match
**Solution:** Check console - class names must match exactly

---

## 📊 Performance Metrics

Expected timing:
```
DetectTool processing: ~180-200ms total
  - ONNX inference: ~150-170ms
  - Pre/post-processing: ~30ms

ResultTool processing: ~1-2ms
  - Threshold comparison: O(n) where n = number of detections

Total pipeline: ~185-205ms
```

---

## 📝 Expected Files to Check

1. **`tools/detection/detect_tool.py`**
   - Output includes `class_thresholds` and `selected_classes`

2. **`tools/result_tool.py`**
   - `evaluate_ng_ok_by_threshold()` method exists
   - `process()` uses threshold evaluation

3. **`job/job_manager.py`**
   - `context.update(result_data)` merges DetectTool output

---

## 🎯 Success Criteria

✅ **All tests pass if:**
1. Object present + confidence >= threshold → OK (GREEN)
2. Object present + confidence < threshold → NG (RED)
3. No object detected → NG (RED)
4. Multiple classes evaluated correctly
5. Console shows detailed comparison logs
6. UI responds correctly to NG/OK decision

