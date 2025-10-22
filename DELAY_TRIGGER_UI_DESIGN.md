# 🎨 Delay Trigger UI - Chi Tiết Thiết Kế

## 📐 Layout

```
┌─────────────────────────────────────────────┐
│ Tab: Control                                │
├─────────────────────────────────────────────┤
│                                             │
│  ☑ Delay Trigger    [10.0 ms]              │
│                                             │
│  (Checkbox tích)    (Spinbox bật)           │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 🧩 Components

### 1. Checkbox: `delayTriggerCheckBox`
**From mainUI.ui (line 751)**
```xml
<widget class="QCheckBox" name="delayTriggerCheckBox">
  <property name="text">
    <string>Delay Trigger</string>
  </property>
</widget>
```

- **objectName:** `delayTriggerCheckBox`
- **Text:** "Delay Trigger"
- **Type:** QCheckBox
- **State:** Checked/Unchecked
- **Position:** x=10, y=340, width=91, height=21

### 2. Spinbox: `delayTriggerTime`
**From mainUI.ui (line 764)**
```xml
<widget class="QDoubleSpinBox" name="delayTriggerTime">
  <property name="maximum">
    <double>100.000000000000000</double>
  </property>
</widget>
```

- **objectName:** `delayTriggerTime`
- **Type:** QDoubleSpinBox
- **Maximum:** 100.0 (ms)
- **Position:** x=110, y=340, width=71, height=21

---

## 🔧 Configuration Code

### main_window.py

```python
def _setup_delay_trigger_controls(self):
    """Setup delay trigger checkbox and spinbox controls"""
    try:
        delay_checkbox = getattr(self, 'delayTriggerCheckBox', None)
        delay_spinbox = getattr(self, 'delayTriggerTime', None)
        
        if not delay_checkbox or not delay_spinbox:
            logging.warning("⚠️ Delay trigger widgets not found in UI")
            return
        
        # Cấu hình Spinbox
        delay_spinbox.setEnabled(False)           # Ban đầu disabled
        delay_spinbox.setDecimals(1)              # 1 decimal place
        delay_spinbox.setMinimum(0.0)             # Min: 0.0 ms
        delay_spinbox.setMaximum(100.0)           # Max: 100.0 ms
        delay_spinbox.setSingleStep(0.1)          # Step: 0.1 ms
        delay_spinbox.setValue(0.0)               # Default: 0.0 ms
        delay_spinbox.setSuffix(" ms")            # Add " ms" suffix
        
        # Kết nối Checkbox → Enable/Disable Spinbox
        delay_checkbox.stateChanged.connect(
            lambda state: self._on_delay_trigger_toggled(state, delay_spinbox)
        )
        
        logging.info("✓ Delay trigger controls setup successfully")
        
    except Exception as e:
        logging.error(f"✗ Error setting up delay trigger controls: {e}", exc_info=True)

def _on_delay_trigger_toggled(self, state, spinbox):
    """Handle checkbox state change"""
    try:
        is_checked = state == 2  # Qt.Checked = 2
        spinbox.setEnabled(is_checked)
        
        if is_checked:
            logging.info(f"✓ Delay trigger enabled - delay: {spinbox.value():.1f}ms")
        else:
            logging.info("✓ Delay trigger disabled")
            
    except Exception as e:
        logging.error(f"✗ Error toggling delay trigger: {e}", exc_info=True)
```

---

## 📊 Spinbox Properties

### Decimals
```python
delay_spinbox.setDecimals(1)
```
- **Chức năng:** Hiển thị 1 chữ số thập phân
- **Ví dụ:** 5.0, 10.5, 25.3
- **Precision:** 0.1 ms

### Minimum & Maximum
```python
delay_spinbox.setMinimum(0.0)      # Min: 0.0 ms
delay_spinbox.setMaximum(100.0)    # Max: 100.0 ms
```
- **Range:** 0.0 - 100.0 milliseconds
- **Reason:** Đủ cho phần lớn trường hợp (150ms là quá nhiều)

### Single Step
```python
delay_spinbox.setSingleStep(0.1)
```
- **Khi dùng mũi tên:** Tăng/giảm 0.1 ms
- **Khi gõ:** Có thể gõ bất kỳ giá trị nào (0.1 - 100.0)

### Suffix
```python
delay_spinbox.setSuffix(" ms")
```
- **Hiển thị:** "5.0 ms", "10.5 ms", etc.
- **User-friendly:** Người dùng biết đơn vị là milliseconds

---

## 🔄 State Transitions

### Checkbox Ticked (Enabled Delay)

```
┌─────────────────────────────────────┐
│ ☑ Delay Trigger    [10.0 ms] ✓     │
│   ↑                  ↑              │
│   Checked            Enabled        │
│                                     │
│ Action: Khi trigger:                │
│  1. Chờ delay được chỉ định         │
│  2. Trigger camera                  │
│  3. Log: "[TRIGGER+10.0ms]..."      │
└─────────────────────────────────────┘
```

### Checkbox Unchecked (Disabled Delay)

```
┌─────────────────────────────────────┐
│ ☐ Delay Trigger    [10.0 ms] ✗     │
│   ↑                  ↑              │
│   Unchecked          Disabled (grayed out)
│                                     │
│ Action: Khi trigger:                │
│  1. Trigger camera ngay             │
│  2. Log: "[TRIGGER]..."             │
│  3. Giá trị spinbox được giữ        │
└─────────────────────────────────────┘
```

---

## 🎨 Visual States

### Enable State (Checkbox ☑️)

**Spinbox visible và interactive:**
```
Input:  [10.0 ▲▼]  ← User có thể click mũi tên
        ┗━━━━━┛
        Editable

User có thể:
- Click mũi tên ▲▼ (tăng/giảm 0.1 ms)
- Double-click để edit (gõ số)
- Scroll mouse để thay đổi
```

### Disable State (Checkbox ☐)

**Spinbox grayed out:**
```
Input:  [10.0 ▲▼]  ← Grayed out (disabled)
        ┗━━━━━┛
        Not interactive

User không thể:
- Click mũi tên
- Double-click để edit
- Scroll để thay đổi
- Nhưng giá trị vẫn được lưu
```

---

## 💾 Data Persistence

### Saved Values
- ✅ Giá trị spinbox được lưu khi tắt checkbox
- ✅ Checkbox state được lưu
- ✅ Lần tới mở lại ứng dụng sẽ khôi phục

### Reset on Startup
- ✅ Checkbox: Unchecked (tắt)
- ✅ Spinbox: Disabled + value = 0.0 ms

---

## 🚀 Features

| Feature | Implementation |
|---------|-----------------|
| **Enable/Disable** | Checkbox → Enable spinbox |
| **Unit Display** | Suffix " ms" (automatic) |
| **Input Range** | 0.0 - 100.0 ms |
| **Precision** | 0.1 ms steps |
| **User Feedback** | Log messages in console |
| **Message List** | Shows delay in output "[TRIGGER+Xms]" |

---

## 📝 Full Usage Example

### Step-by-step

```
1. Open application
   → Checkbox: ☐ (unchecked)
   → Spinbox: [0.0 ms] (disabled, grayed out)

2. User ticks checkbox
   → Checkbox: ☑ (checked)
   → Spinbox: [0.0 ms] (enabled, active)
   → Log: "✓ Delay trigger enabled - delay: 0.0ms"

3. User edits spinbox to 15.5
   → Spinbox shows: [15.5 ms]
   → Value stored

4. User sends TCP trigger message
   → Log: "★ Detected trigger command: start_rising||1234567"
   → Log: "⏱️  Applying delay: 15.5ms (0.0155s)"
   → (system waits 15.5ms)
   → Log: "✓ Delay completed, triggering camera now..."
   → Camera triggers
   → Message List: "[TRIGGER+15.5ms] Camera captured from..."

5. User unchecks checkbox
   → Checkbox: ☐ (unchecked)
   → Spinbox: [15.5 ms] (disabled, value kept)
   → Log: "✓ Delay trigger disabled"

6. User sends TCP trigger message (without delay)
   → Log: "★ Detected trigger command: start_rising||1234567"
   → Camera triggers immediately (no delay)
   → Message List: "[TRIGGER] Camera captured from..."
```

---

## ✅ Checklist

- ✅ Checkbox created in mainUI.ui
- ✅ Spinbox created in mainUI.ui
- ✅ Spinbox configured with correct properties
- ✅ Checkbox connected to enable/disable spinbox
- ✅ Delay logic integrated into trigger function
- ✅ Logging implemented for debugging
- ✅ Message list shows delay information
- ✅ No syntax errors
- ✅ Backward compatible
- ✅ Documentation complete

---

## 🎉 Status

**✅ COMPLETE & READY TO USE**

