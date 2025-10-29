# Bug Fix: DetectTool Config Lost When Editing

## 🐛 Problem

When user edits a DetectTool that was already added to job:
- Model selection is lost (shows "Select Model..." instead of previously selected model)
- Selected classes disappear from classification table
- All configuration is reset to defaults

**User Report:**
```
"khi edit lại detect tool đã thêm vào job thì mất tất cả thông tin 
về model và class đã chọn"

Translation: "When editing DetectTool already added to job, 
all model and class information is lost"
```

---

## 🔍 Root Cause Analysis

### Flow When Editing Tool:
1. User clicks Edit on DetectTool
2. `_load_tool_config_to_ui()` called in main_window.py
3. It first calls `_clear_tool_config_ui()` → **CLEARS ALL UI**
4. Then calls `detect_tool_manager.load_tool_config(config)` → **SHOULD RESTORE**

### The Bug:
In `load_tool_config()`, code was:
```python
# Set flag to prevent signal recursion
self.loading_config = True  # ← FLAG SET TO TRUE

# Then call set_current_model()
self.set_current_model(model_name)
  └─→ calls _on_model_changed()
      └─→ checks: if self.loading_config: return  # ← EARLY RETURN!
          └─→ Never loads model classes into UI!

finally:
    self.loading_config = False  # ← Flag reset
```

**Result:** Model combo box set correctly, but classification combo box NOT updated!
- `self.current_model` is set
- But `_load_model_classes()` never called
- So UI doesn't show the available classes

---

## ✅ Solution

### Fix 1: Remove `loading_config` Flag Logic
Changed `_on_model_changed()` to NOT check `loading_config` flag:
- Removed: `if self.loading_config: return`
- Now allows processing during config loading
- This is safe because we explicitly call it from `load_tool_config()`

### Fix 2: Properly Load Model in Config Loading
Changed `load_tool_config()` to:
1. Directly set algorithm combo box index (don't use `set_current_model()`)
2. Directly call `_on_model_changed()` with `blockSignals()`
3. This ensures all model data loads without early returns

**New Flow:**
```python
# Find model in combo
index = self.algorithm_combo.findText(model_name)

# Set it without signal triggers
self.algorithm_combo.blockSignals(True)
self.algorithm_combo.setCurrentIndex(index)
self.algorithm_combo.blockSignals(False)

# Manually call to load classes
self._on_model_changed(model_name)  # ← Fully runs now!
  └─→ Loads model classes into classification combo ✅
  └─→ UI shows all classes ✅
```

---

## 📋 Files Modified

**File:** `gui/detect_tool_manager_simplified.py`

### Change 1: `_on_model_changed()` (Lines 160-190)
- **Removed:** `if self.loading_config: return` check
- **Reason:** We now explicitly call this during config loading
- **Result:** Classes load properly when editing

### Change 2: `load_tool_config()` (Lines 453-505)
- **Removed:** `self.loading_config = True` flag
- **Changed:** Use direct combo box manipulation instead of `set_current_model()`
- **Added:** Explicit `_on_model_changed()` call after setting combo
- **Result:** Config loads completely

---

## 🧪 Expected Behavior After Fix

### Scenario: Edit DetectTool

**Before:**
```
1. User clicks Edit on DetectTool (had model="sed", class="pilsner333")
2. UI clears (expected)
3. Config loads BUT:
   - Model combo = "Select Model..." ✗
   - Classes table = empty ✗
   - Result: "Lost all information"
```

**After:**
```
1. User clicks Edit on DetectTool (had model="sed", class="pilsner333")
2. UI clears (expected)
3. Config loads AND:
   - Model combo = "sed" ✓
   - Classification combo = [pilsner333, saxizero, warriorgrape] ✓
   - Classes table = [(pilsner333, 0.5)] ✓
   - Result: All information preserved!
```

---

## 🔧 Technical Details

### Why `loading_config` Flag Was Problematic

The flag was meant to prevent **signal recursion** when signals triggered:
```
Combo Box Change Signal 
  → _on_model_changed() called
  → May trigger more signals
  → Infinite loop? No, because flag prevents it
```

But this logic broke during config loading because:
- We WANT full processing during load
- But flag was blocking it
- Solution: Directly call methods, don't rely on signals

### Why Direct Call Works

```python
# Old way (signal-based):
self.algorithm_combo.setCurrentIndex(index)  # ← Triggers signal
  → _on_model_changed() called automatically
  → But flag may block it

# New way (direct call):
self.algorithm_combo.blockSignals(True)      # ← Disable auto signal
self.algorithm_combo.setCurrentIndex(index)
self.algorithm_combo.blockSignals(False)
self._on_model_changed(model_name)            # ← Manually call
  → Full processing guaranteed
  → No signal recursion
  → Classes load properly
```

---

## ✅ Verification

```bash
python -m py_compile gui/detect_tool_manager_simplified.py
# Result: ✅ NO ERRORS
```

**Code Changes:**
- ✅ `_on_model_changed()` - Removed early return
- ✅ `load_tool_config()` - Direct model loading
- ✅ Both methods syntax verified

---

## 📚 Related Methods

### `_on_model_changed(model_name)`
- Loads model info
- Updates classification combo
- Populates available classes

### `load_tool_config(config)`
- Loads saved configuration from tool
- Restores model selection
- Restores class selections

### `load_selected_classes_with_thresholds(classes, thresholds)`
- Populates classification table
- Shows selected classes with thresholds

---

## 🎯 Testing

**To test the fix:**

1. **Create DetectTool:**
   - Select model "sed"
   - Select class "pilsner333"
   - Set threshold 0.6
   - Click "Apply Setting"

2. **Edit the tool:**
   - Right-click DetectTool in job view
   - Select "Edit"
   - **VERIFY:**
     - ✅ Model combo shows "sed"
     - ✅ Classes table shows "pilsner333, 0.6"
     - ✅ All configuration preserved

3. **Make changes:**
   - Add another class (e.g., "saxizero", 0.55)
   - Change model to another
   - Click "Apply Setting"

4. **Edit again:**
   - Verify new configuration is saved

---

## 📊 Before vs After

| Aspect | Before | After |
|--------|--------|-------|
| Edit DetectTool | ❌ Loses model | ✅ Model shown |
| Edit DetectTool | ❌ Loses classes | ✅ Classes shown |
| Edit DetectTool | ❌ Reset to defaults | ✅ Config restored |
| Load Config | ❌ Incomplete | ✅ Full restore |
| Model Classes | ❌ Not shown | ✅ Shown correctly |

---

## 🚀 Status

✅ **FIX COMPLETE**
- Issue identified
- Root cause found
- Solution implemented
- Syntax verified
- Ready for testing

**Next:** User should restart application and test editing DetectTool
