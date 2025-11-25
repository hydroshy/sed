# 🐛 Issue: Camera UI Freezing on Trigger Mode Change

## Vấn Đề
Khi người dùng nhấn "Trigger Camera Mode", hệ thống gọi `cancel_all_and_flush()` ngay lập tức, khiến:
- Giao diện bị "đơ" (freeze)
- Camera buffer bị xóa toàn bộ
- Frame hiện tại bị hủy

---

## 🔍 Root Cause

**File**: `gui/camera_manager.py`

**Flow khi nhấn Trigger Camera Mode button**:
```
on_trigger_camera_mode_clicked()
    ↓
camera_tool.set_camera_mode("trigger")
    ↓ (hoặc) _handle_trigger_mode_directly()
    ↓
set_trigger_mode(True)
    ├─ Async thread: camera_stream.set_trigger_mode(enabled)
    └─ Immediately: update_camera_mode_ui()
    
+ set_manual_exposure_mode()
    ├─ camera_stream.set_auto_exposure(False)
    └─ _apply_setting_if_manual()
        └─ camera_stream.set_exposure()  ← Có thể gây freeze
```

**Vấn đề**:
- Khi mode thay đổi, các thiết lập được áp dụng ngay
- Nếu có frame đang xử lý, nó bị flush ngay (không chờ frame hoàn thành)
- UI không responsive trong quá trình này

---

## 💡 Solution

**Không gọi cancel_all_and_flush() ngay**. Thay vào đó:

1. **Đặt flag**: `_mode_changing = True`
2. **Skip apply settings tạm thời**: Không push exposure/gain ngay
3. **Sau frame tiếp theo**: Mới apply settings
4. **Reset flag**: `_mode_changing = False`

---

## 🔧 Implementation

### Option A: Defer Settings Application (Recommended)

```python
def on_trigger_camera_mode_clicked(self):
    """Xử lý khi click Trigger Camera Mode button"""
    
    # Flag: Đang trong quá trình chuyển mode
    self._mode_changing = True
    
    # 1. Chuyển sang trigger mode (async)
    camera_tool = self.find_camera_tool()
    if camera_tool:
        camera_tool.set_camera_mode("trigger")
    else:
        self._handle_trigger_mode_directly()
    
    # 2. Set manual exposure nhưng KHÔNG apply ngay
    self._is_auto_exposure = False
    self.set_manual_exposure_mode()
    
    # 3. Cập nhật UI
    self.update_camera_mode_ui()
    
    # 4. Schedule deferred settings apply (sau 100ms)
    QTimer.singleShot(100, self._apply_trigger_mode_settings)
    
    # 5. Reset flag
    self._mode_changing = False


def _apply_trigger_mode_settings(self):
    """Áp dụng settings sau khi mode đã chuyển xong"""
    if not self.camera_stream:
        return
    
    try:
        # Áp dụng exposure hiện tại
        if self.exposure_edit:
            exp_val = self.exposure_edit.value()
            self.camera_stream.set_exposure(exp_val)
        
        # Áp dụng gain hiện tại
        if self.gain_edit:
            gain_val = self.gain_edit.value()
            self.camera_stream.set_gain(gain_val)
    except Exception as e:
        print(f"DEBUG: Error applying settings: {e}")
```

---

### Option B: Skip cancel_all_and_flush During Mode Change

**File**: `gui/camera_manager.py`

**Modify**: `set_trigger_mode()` hoặc `_apply_setting_if_manual()`

```python
def _apply_setting_if_manual(self, setting_type, value):
    """Helper: Apply setting nếu đang ở manual mode"""
    
    # SKIP if mode is changing để avoid freeze
    if getattr(self, '_mode_changing', False):
        print("DEBUG: Skipping settings application during mode change")
        return
    
    if self._instant_apply and not self._is_auto_exposure and self.camera_stream:
        try:
            if setting_type == 'exposure':
                self.camera_stream.set_exposure(value)
            elif setting_type == 'gain':
                self.camera_stream.set_gain(value)
        except AttributeError:
            pass
```

---

## 📊 Comparison

| Approach | Pros | Cons |
|----------|------|------|
| **A: Defer** | UI không freeze, settings được apply | Hơi phức tạp, cần QTimer |
| **B: Skip** | Đơn giản, ít code | Settings bị delay, might be lost |

---

## ✅ Recommended Fix

**Approach A**: Defer settings application

**Implementation**:
1. Thêm `_mode_changing` flag
2. Khi mode đang thay đổi, không apply settings ngay
3. Dùng `QTimer.singleShot()` để apply sau 100ms
4. Reset flag khi xong

**Benefit**:
- ✅ UI không freeze
- ✅ Settings được áp dụng đúng cách
- ✅ Frame buffer không bị flush ngay
- ✅ Frame tiếp theo được xử lý bình thường

---

## 🧪 Testing

```
1. Click "Trigger Camera Mode" button
2. Observe UI responsiveness (không bị freeze)
3. Verify exposure/gain được apply
4. Verify frame stream tiếp tục bình thường
```

---

**Status**: ⏳ Cần sửa  
**Priority**: Medium (ảnh hưởng UX)  
**Effort**: Low (10-15 lines code)
