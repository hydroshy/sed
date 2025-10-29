# Detailed Fix: Why Config Was Lost When Editing

## 📋 The Problem Flow

### What User Did
```
1. Create DetectTool
   - Select model: "sed"
   - Select class: "pilsner333"
   - Set threshold: 0.5
   - Click "Apply Setting"
   
2. Edit the tool (right-click → Edit)
   
3. UI Shows:
   ✗ Model: "Select Model..." (should be "sed")
   ✗ Classes: empty table (should have pilsner333)
   ✗ Everything reset to defaults
   
❌ User sees: "All information lost!"
```

---

## 🔍 Technical Investigation

### Step 1: Track Config Save
```python
# When tool created:
config = detect_tool_manager.get_tool_config()
# Returns: {
#   'model_name': 'sed',
#   'selected_classes': ['pilsner333'],
#   'class_thresholds': {'pilsner333': 0.5},
#   ...
# }

detect_tool = create_detect_tool_from_manager_config(config)
# Tool object created with this config ✓
```

### Step 2: Track Config Load (Edit Mode)
```python
# User clicks Edit
tool_config = tool.config.to_dict()
# Should return: {
#   'model_name': 'sed',
#   'selected_classes': ['pilsner333'],
#   'class_thresholds': {'pilsner333': 0.5},
#   ...
# }  ✓ Config exists!

main_window._load_tool_config_to_ui(tool)
```

### Step 3: Inside _load_tool_config_to_ui()
```python
# Step 3a: Clear UI
self._clear_tool_config_ui()
# Resets everything:
# - algo_combo → index 0 ("Select Model...")
# - classification_table → empty
# - selected_classes → []

# Step 3b: Load config
detect_tool_manager.load_tool_config(config)
# Should restore everything
```

### Step 4: Inside OLD load_tool_config()
```python
# OLD CODE:
self.loading_config = True  # ← FLAG SET!

if 'model_name' in config:
    model_name = config['model_name']  # "sed"
    self.set_current_model(model_name)
    
    # Inside set_current_model():
    #   self.algorithm_combo.setCurrentIndex(index)  # Sets to "sed"
    #   self._on_model_changed(model_name)           # Calls...
    #
    #   Inside _on_model_changed():
    #     if self.loading_config:  # ← TRUE!
    #         logger.debug("Skipping signal...")
    #         return  # ← EARLY RETURN! ❌
    #
    #     Never executes the rest:
    #     model_info = self.model_manager.get_model_info(model_name)
    #     self._load_model_classes(model_info['classes'])  # ← NEVER CALLED!

finally:
    self.loading_config = False

# RESULT:
# ✓ Combo box set to "sed"
# ✗ But classes NOT loaded into classification combo!
# ✗ UI doesn't show pilsner333, saxizero, warriorgrape
```

### Step 5: Visual Result
```
UI shows:
✗ Model combo: "sed" (correct)
✗ Classification combo: empty (should have [pilsner333, saxizero, warriorgrape])
✗ Selected classes table: empty (should have [pilsner333, 0.5])

User sees: "Everything reset!"
```

---

## ✅ The Fix

### Problem Identified
Flag `loading_config=True` prevented `_on_model_changed()` from loading model classes.

### Solution
**Option 1:** Remove the flag check
- Simply remove the early return
- Trust that explicit calls are safe

**Option 2:** Avoid setting flag during config load
- Don't use signals
- Directly manipulate UI + call methods

We chose **Option 2** (more controlled):

```python
def load_tool_config(self, config):
    # No flag setting!
    
    if 'model_name' in config:
        model_name = config['model_name']
        
        # Direct UI manipulation (no signals)
        if self.algorithm_combo:
            index = self.algorithm_combo.findText(model_name)
            if index >= 0:
                # Disable signals temporarily
                self.algorithm_combo.blockSignals(True)
                self.algorithm_combo.setCurrentIndex(index)
                self.algorithm_combo.blockSignals(False)
                
                # ✓ Combo box updated
        
        # ✓ Explicitly call to load classes
        self._on_model_changed(model_name)
        # Now _on_model_changed() runs fully:
        # - Gets model info ✓
        # - Loads classes into classification combo ✓
        # - All data populated ✓
```

### Also Updated _on_model_changed()
```python
def _on_model_changed(self, model_name):
    # OLD:
    # if self.loading_config:
    #     return  # ← BLOCKED DURING CONFIG LOAD
    
    # NEW:
    # No early return! Processes fully
    
    # Load model info
    model_info = self.model_manager.get_model_info(model_name)  # ✓
    
    # Load classes into UI
    self._load_model_classes(model_info['classes'])  # ✓
```

---

## 🎯 Execution Flow After Fix

```python
# User clicks Edit on DetectTool with model="sed", class="pilsner333"

main_window._load_tool_config_to_ui(tool)
  ↓
main_window._clear_tool_config_ui()
  # Clears UI (expected)
  ↓
detect_tool_manager.load_tool_config(config)
  # config = {'model_name': 'sed', 'selected_classes': ['pilsner333'], ...}
  ↓
  # Step 1: Set combo box
  index = algorithm_combo.findText('sed')  # → 1
  algorithm_combo.setCurrentIndex(1)
  # UI: algo_combo now shows "sed" ✓
  ↓
  # Step 2: Explicitly call handler
  _on_model_changed('sed')
    ↓
    # No early return! Processes fully
    model_info = model_manager.get_model_info('sed')
    # model_info = {'name': 'sed', 'classes': [...]}
    ↓
    _load_model_classes(model_info['classes'])
      ↓
      classification_combo.clear()
      classification_combo.addItem("Select Class...")
      for class_name in ['pilsner333', 'saxizero', 'warriorgrape']:
          classification_combo.addItem(class_name)
      # UI: classification_combo now shows all classes ✓
  ↓
  # Step 3: Load selected classes into table
  load_selected_classes_with_thresholds(['pilsner333'], {'pilsner333': 0.5})
    ↓
    classification_table.addRow(['pilsner333', '0.5'])
    # UI: table now shows selected classes ✓

RESULT:
✓ Model: "sed" shown correctly
✓ Classes: pilsner333, saxizero, warriorgrape available
✓ Selected: pilsner333, 0.5 shown in table
✓ All configuration preserved!
```

---

## 🧪 Test Scenarios

### Scenario 1: Simple Edit
```
Create: model=sed, class=pilsner333
Edit:   ✓ Should see sed + pilsner333
Apply:  ✓ Should keep config
```

### Scenario 2: Change Selection
```
Create: model=sed, class=pilsner333
Edit:   Add saxizero, remove pilsner333
        ✓ Model stays as sed
        ✓ Can modify classes
Apply:  ✓ Changes saved
```

### Scenario 3: Different Model
```
Create: model=sed
Change: Select different model
        ✓ New model's classes load
Apply:  ✓ New model saved
```

---

## 📊 Summary

| Component | Before | After |
|-----------|--------|-------|
| `load_tool_config()` | Sets flag, blocks model loading | No flag, direct method calls |
| `_on_model_changed()` | Checks flag, returns early | Processes fully |
| Model Loading | ✗ Partial (combo set, classes not loaded) | ✓ Complete |
| Classes Display | ✗ Empty | ✓ Populated |
| User Experience | ❌ "Lost all config" | ✅ "Config preserved" |

---

## ✅ Verification

Files modified and verified:
- ✅ `gui/detect_tool_manager_simplified.py` - Syntax OK
- ✅ Logic flow correct
- ✅ No circular dependencies
- ✅ Signal blocking prevents recursion

Ready for user testing!
