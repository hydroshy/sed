# Fix Exposure Handlers - Instant Apply

## Vấn đề hiện tại
- Exposure/Gain/EV adjustments chỉ lưu vào pending settings
- Không apply ngay lập tức → Không có tác dụng khi chỉnh
- User expect instant feedback khi điều chỉnh exposure

## Giải pháp đã implement

### 1. Helper Method
```python
def _apply_setting_if_manual(self, setting_type, value):
    """Apply setting ngay lập tức nếu đang ở manual mode"""
    if not self._is_auto_exposure and self.camera_stream:
        if setting_type == 'exposure':
            self.camera_stream.set_exposure(value)
        elif setting_type == 'gain':
            self.camera_stream.set_gain(value)
        elif setting_type == 'ev':
            self.camera_stream.set_ev(value)
```

### 2. Updated Handlers Pattern
```python
# Pattern cũ (chỉ lưu pending)
self._pending_exposure_settings['exposure'] = value

# Pattern mới (instant apply + pending)
self._pending_exposure_settings['exposure'] = value
self._apply_setting_if_manual('exposure', value)
```

## Logic hoạt động

### Instant Apply Mode (Khi Manual Exposure):
1. User thay đổi exposure/gain/ev slider/spinbox
2. **Apply ngay lập tức** để user thấy effect
3. **Lưu vào pending** để Apply button có thể sync

### Pending Mode (Khi Auto Exposure):
1. User thay đổi giá trị (nhưng đang ở auto mode)
2. **Không apply** vì auto mode đang hoạt động
3. **Lưu vào pending** để apply khi switch sang manual

### Apply Button:
- Apply tất cả pending settings
- Useful để sync lại hoặc apply batch changes

### Cancel Button:
- Reset về default values
- Clear tất cả pending settings

## Status Update Needed

Các handler sau cần được update:
- ✅ `on_exposure_slider_changed` - Đã update
- ⏳ `on_exposure_edit_changed` - Cần update  
- ⏳ `on_gain_slider_changed` - Cần update
- ⏳ `on_gain_edit_changed` - Cần update
- ⏳ `on_ev_slider_changed` - Cần update
- ⏳ `on_ev_edit_changed` - Cần update

## Cần làm tiếp
1. Update remaining handlers to use `_apply_setting_if_manual()`
2. Test instant apply functionality
3. Ensure Apply/Cancel buttons still work correctly

## Expected Behavior
- **Manual Mode**: Instant feedback khi adjust exposure
- **Auto Mode**: Changes saved for later apply
- **Smooth UX**: Real-time response without lag
