# Phase 8c - Verification Commands

## 🔍 Quick Verification

### 1. Verify No Auto ResultTool Addition
```bash
cd e:\PROJECT\sed
grep -n "ResultTool" gui/detect_tool_manager.py | grep -i "add_tool"
# Should return: NOTHING (no auto-add)
# If shows lines, auto-add still present
```

### 2. Verify Result Tool in UI
```bash
grep -n "Result Tool" gui/ui_mainwindow.py
# Should return:
#   389: self.toolComboBox.addItem("")  (4th item)
#   768: self.toolComboBox.setItemText(3, _translate("MainWindow", "Result Tool"))
```

### 3. Verify Result Tool Handling in tool_manager
```bash
grep -n "elif self._pending_tool == \"Result Tool\"" gui/tool_manager.py
# Should return:
#   287: elif self._pending_tool == "Result Tool":
```

### 4. Verify Result Tool Routing in main_window
```bash
grep -n "elif tool_name == \"Result Tool\"" gui/main_window.py
# Should return:
#   1531: elif tool_name == "Result Tool":
```

### 5. Verify Result Tool Mapping in settings_manager
```bash
grep -n "\"Result Tool\"" gui/settings_manager.py
# Should return:
#   47: "Result Tool": "detect"  # Mapping
```

---

## ✅ Syntax Verification

```bash
cd e:\PROJECT\sed

# Verify all files compile
python -m py_compile gui/detect_tool_manager.py
python -m py_compile gui/ui_mainwindow.py
python -m py_compile gui/tool_manager.py
python -m py_compile gui/main_window.py
python -m py_compile gui/settings_manager.py

# Should all complete without errors
# If any errors, files need fixing
```

---

## 📋 File Contents Verification

### File 1: detect_tool_manager.py
**Check:** Lines 113-135 should NOT have ResultTool auto-add
```bash
sed -n '113,135p' gui/detect_tool_manager.py | grep -i "result"
# Should return: NOTHING
# If returns lines, auto-add code still there
```

**Should see instead:**
```bash
sed -n '113,125p' gui/detect_tool_manager.py
# Should show:
# print("=" * 80)
# print("JOB PIPELINE SETUP:")
# for i, tool in enumerate...
```

### File 2: ui_mainwindow.py  
**Check:** Has 4 toolComboBox items
```bash
sed -n '386,393p' gui/ui_mainwindow.py | grep addItem
# Should return 4 lines with addItem("")
```

**Check:** Result Tool setText
```bash
sed -n '764,769p' gui/ui_mainwindow.py
# Should include:
# setItemText(3, _translate("MainWindow", "Result Tool"))
```

### File 3: tool_manager.py
**Check:** Result Tool handling exists
```bash
sed -n '287,302p' gui/tool_manager.py | grep -E "elif|ResultTool|from tools"
# Should show Result Tool handling code
```

### File 4: main_window.py
**Check:** Result Tool routing exists
```bash
sed -n '1531,1536p' gui/main_window.py | grep -E "elif|Result Tool"
# Should show Result Tool condition
```

### File 5: settings_manager.py
**Check:** Result Tool mapping exists
```bash
sed -n '40,50p' gui/settings_manager.py | grep "Result Tool"
# Should show: "Result Tool": "detect"
```

---

## 🧪 Pre-Testing Checks

### Before Running Application

✅ **Syntax Check**
```bash
python -m py_compile gui/*.py
# All should pass
```

✅ **Import Check**
```bash
python -c "from gui.detect_tool_manager import DetectToolManager; print('OK')"
# Should print: OK
```

✅ **File Existence**
```bash
ls -la tools/result_tool.py
# Should exist
```

---

## 🔧 Quick Test Script

Create file: `test_phase8c.py`

```python
#!/usr/bin/env python3
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Test 1: Check detect_tool_manager.py
print("Test 1: Check for auto-ResultTool removal...")
with open('gui/detect_tool_manager.py', 'r') as f:
    content = f.read()
    if 'ResultTool("Result Tool"' in content and 'current_job.add_tool(result_tool)' in content and 'add_tool(detect_tool)' in content:
        print("  ❌ FAIL: Auto-ResultTool still present")
        sys.exit(1)
    else:
        print("  ✅ PASS: Auto-ResultTool removed")

# Test 2: Check ui_mainwindow.py for 4 items
print("Test 2: Check toolComboBox has 4 items...")
with open('gui/ui_mainwindow.py', 'r') as f:
    lines = f.readlines()
    # Count addItem calls around line 389
    count = sum(1 for i in range(385, 395) if 'addItem("")' in lines[i])
    if count >= 4:
        print(f"  ✅ PASS: Found {count} addItem calls")
    else:
        print(f"  ❌ FAIL: Only found {count} addItem calls (need 4)")
        sys.exit(1)

# Test 3: Check Result Tool setText
print("Test 3: Check Result Tool setText...")
with open('gui/ui_mainwindow.py', 'r') as f:
    content = f.read()
    if 'setItemText(3, _translate("MainWindow", "Result Tool"))' in content:
        print("  ✅ PASS: Result Tool setText found")
    else:
        print("  ❌ FAIL: Result Tool setText not found")
        sys.exit(1)

# Test 4: Check Result Tool in tool_manager
print("Test 4: Check Result Tool in tool_manager.py...")
with open('gui/tool_manager.py', 'r') as f:
    content = f.read()
    if 'elif self._pending_tool == "Result Tool":' in content:
        print("  ✅ PASS: Result Tool handling found")
    else:
        print("  ❌ FAIL: Result Tool handling not found")
        sys.exit(1)

# Test 5: Check Result Tool mapping
print("Test 5: Check Result Tool mapping in settings_manager.py...")
with open('gui/settings_manager.py', 'r') as f:
    content = f.read()
    if '"Result Tool": "detect"' in content:
        print("  ✅ PASS: Result Tool mapping found")
    else:
        print("  ❌ FAIL: Result Tool mapping not found")
        sys.exit(1)

# Test 6: Syntax check
print("Test 6: Syntax verification...")
import py_compile
try:
    py_compile.compile('gui/detect_tool_manager.py', doraise=True)
    py_compile.compile('gui/ui_mainwindow.py', doraise=True)
    py_compile.compile('gui/tool_manager.py', doraise=True)
    py_compile.compile('gui/main_window.py', doraise=True)
    py_compile.compile('gui/settings_manager.py', doraise=True)
    print("  ✅ PASS: All files have valid syntax")
except py_compile.PyCompileError as e:
    print(f"  ❌ FAIL: Syntax error - {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✅ ALL PRE-TESTS PASSED - Ready for runtime testing!")
print("="*60)
```

**Run:**
```bash
cd e:\PROJECT\sed
python test_phase8c.py
# Should show: ✅ ALL PRE-TESTS PASSED
```

---

## 📊 Expected Results

### ✅ Correct Setup
- All file checks pass
- All syntax checks pass
- No import errors
- Result Tool file exists

### ❌ Issues to Fix
- Auto-ResultTool code still present → Need to verify deletion
- Missing Result Tool setText → Need to check ui_mainwindow.py
- Missing Result Tool handling → Need to check tool_manager.py
- Syntax errors → Need to fix Python syntax

---

## 🚀 Ready to Test?

When all verification commands pass:

```
✅ Syntax verified
✅ Files configured correctly
✅ No auto-ResultTool
✅ Result Tool in UI
✅ Result Tool handling implemented

→ Ready to restart application and test!
```

See: `readme/PHASE_8c_TESTING_CHECKLIST.md` for runtime tests
