# Testing Guide - Config Lost Bug Fix

## 🐛 Bug Description
When editing DetectTool already in job, configuration lost:
- Model resets to "Select Model..."
- Selected classes cleared
- Thresholds reset

## ✅ Bug Fixed
- Removed `loading_config` flag checks that blocked config restoration
- Both `detect_tool_manager.py` and `detect_tool_manager_simplified.py` updated
- Direct method calls ensure model and classes load during edit

---

## 🧪 Test Procedure

### Step 1: Create DetectTool
1. **Start application**
2. **Select "Detect Tool"** from toolComboBox
3. **Configure:**
   - Model: "sed"
   - Add Class: "pilsner333" (threshold 0.5)
4. **Click "Apply Setting"**
   - Job should show: [Camera Source, Detect Tool]

### Step 2: Edit DetectTool (THE TEST)
1. **In job view, select Detect Tool**
2. **Right-click → Edit** (or double-click)
3. **VERIFY - Settings page shows:**
   - ✅ Model: "sed" (NOT "Select Model...")
   - ✅ Classification combo: pilsner333, saxizero, warriorgrape (NOT empty)
   - ✅ Selected classes table: pilsner333, 0.5 (NOT empty)

### Step 3: Modify Configuration
1. **Add another class:** "saxizero" with threshold 0.55
2. **Remove previous:** "pilsner333"
3. **Verify table shows:** Only "saxizero, 0.55"
4. **Click "Apply Setting"**

### Step 4: Edit Again
1. **Select Detect Tool again**
2. **Right-click → Edit**
3. **VERIFY - Should show:**
   - ✅ Model: "sed"
   - ✅ Selected: saxizero, 0.55

---

## 📊 Expected Log Output

### CORRECT (After Fix)
```
DEBUG: Loading tool config: {...}
2025-10-29 15:26:46 - Set current model: sed
2025-10-29 15:26:46 - Model changed to: sed
2025-10-29 15:26:46 - Loaded model: sed with 3 classes
2025-10-29 15:26:46 - Loaded 3 classes into classification combo box
2025-10-29 15:26:46 - Tool configuration loaded successfully
```

### WRONG (Before Fix)
```
DEBUG: Loading tool config: {...}
2025-10-29 15:26:46 - Set current model: sed
2025-10-29 15:26:46 - Model changed to: sed
2025-10-29 15:26:46 - Skipping signal - currently loading config  ❌
2025-10-29 15:26:46 - Tool configuration loaded successfully
```

---

## ✅ Success Criteria

All of these must be TRUE:

- [ ] Edit DetectTool → Model preserved (sed shown)
- [ ] Edit DetectTool → Classes preserved (pilsner333, saxizero, etc shown)
- [ ] Edit DetectTool → Thresholds preserved (0.5, 0.55, etc shown)
- [ ] Modify configuration → Changes saved
- [ ] Edit again → Modified config shown
- [ ] Console does NOT show "Skipping signal"
- [ ] All configuration data intact after edit

---

## 🆘 Troubleshooting

### Issue: Still shows "Select Model..."
**Solution:**
- [ ] Restart application (Python cache may need clearing)
- [ ] Check console for error messages
- [ ] Verify files compiled: `python -m py_compile gui/detect_tool_manager.py`

### Issue: Classes table still empty
**Solution:**
- [ ] Check if model is loaded first
- [ ] Look for log: "Loaded X classes into classification combo"
- [ ] If missing, check method call chain

### Issue: Still see "Skipping signal"
**Solution:**
- [ ] File may not have been saved properly
- [ ] Check file content: `grep "Skipping signal" gui/detect_tool_manager.py`
- [ ] Should return 0 results (not found)

---

## 📝 Test Results Template

| Test | Expected | Actual | Pass |
|------|----------|--------|------|
| Create DetectTool | 2 tools added | ? | [ ] |
| Edit tool - model shown | "sed" | ? | [ ] |
| Edit tool - classes shown | 3+ classes | ? | [ ] |
| Edit tool - threshold shown | 0.5 | ? | [ ] |
| Modify & save | Config saved | ? | [ ] |
| Edit modified tool | New config shown | ? | [ ] |
| No "Skipping signal" | True | ? | [ ] |

---

## 🎯 Test Scenarios

### Scenario A: Single Class
```
Create: sed + pilsner333 (0.5)
Edit:   Should show sed + pilsner333 ✓
Apply:  Should save ✓
Edit:   Should still show sed + pilsner333 ✓
```

### Scenario B: Multiple Classes
```
Create: sed + [pilsner333, saxizero] (0.5, 0.6)
Edit:   Should show both classes ✓
Apply:  Should save both ✓
Edit:   Should still show both ✓
```

### Scenario C: Change Model
```
Create: sed + pilsner333
Edit:   Add saxizero
Apply:  Should save new config ✓
Edit:   Should show updated config ✓
```

---

## ✨ Sign of Success

After fix, you should see:
```
✅ Can edit DetectTool
✅ Model preserved in UI
✅ Classes preserved in UI
✅ Thresholds preserved in UI
✅ Changes persist across edits
✅ No "Skipping signal" messages
✅ All information intact
```

---

## 🚀 Ready to Test!

Files are compiled and ready. Simply:
1. **Restart the application**
2. **Follow test procedure above**
3. **Report any issues**

Good luck! 🎉
