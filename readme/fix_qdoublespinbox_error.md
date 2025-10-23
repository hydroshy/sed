# Fix cho AttributeError: 'QDoubleSpinBox' object has no attribute 'setValidator'

## Vấn đề
- Code cũ sử dụng QLineEdit với setValidator()
- Code mới đã thay đổi thành QDoubleSpinBox
- QDoubleSpinBox không có setValidator() - thay vào đó sử dụng setMinimum(), setMaximum(), setDecimals()

## Những gì đã sửa

### 1. **gui/main_window.py**

#### Thay thế validators bằng SpinBox configuration:
```python
# TRƯỚC (QLineEdit + Validator)
self.exposureEdit.setValidator(QDoubleValidator(0.03, 10000, 2, self))

# SAU (QDoubleSpinBox + Configuration)  
self.exposureEdit.setMinimum(0.001)
self.exposureEdit.setMaximum(1000.0)
self.exposureEdit.setValue(10.0)
self.exposureEdit.setDecimals(3)
self.exposureEdit.setSuffix(" ms")
```

#### Cấu hình cho tất cả SpinBox:
- **exposureEdit**: 0.001-1000.0 ms, 3 decimals, suffix " ms"
- **gainEdit**: 1.0-16.0, 2 decimals  
- **evEdit**: -2.0 to 2.0, 1 decimal

#### Xóa import không cần thiết:
- Removed: `QIntValidator`, `QDoubleValidator`
- Kept: `QCloseEvent` (still needed)

#### Fix widget duplicates:
- Xóa duplicate findChild cho `applySetting` và `cancelSetting`

#### Graceful handling cho missing widgets:
```python
# Sử dụng getattr với None fallback
live_camera_btn=getattr(self, 'liveCamera', None),
```

### 2. **gui/camera_manager.py**

#### Thêm logging cho missing widgets:
```python
missing_widgets = []
if not self.live_camera_btn:
    missing_widgets.append('liveCamera')
# ... check other widgets
if missing_widgets:
    logging.warning(f"Missing UI widgets: {', '.join(missing_widgets)}")
```

#### Updated exposure handlers cho QDoubleSpinBox:
```python
# Auto-detect widget type và sử dụng phù hợp
if hasattr(self.exposure_edit, 'setValue'):  # QDoubleSpinBox
    self.exposure_edit.setValue(display_value)
else:  # QLineEdit fallback
    self.exposure_edit.setText(str(display_value))
```

## Kết quả
- ✅ **AttributeError được fix**: Không còn gọi setValidator() trên QDoubleSpinBox
- ✅ **Graceful degradation**: App sẽ chạy được ngay cả khi thiếu một số UI widgets
- ✅ **Better UX**: QDoubleSpinBox có validation built-in và UX tốt hơn QLineEdit
- ✅ **Logging**: Warning về missing widgets để debug

## UI Requirements
Để tận dụng đầy đủ tính năng, cần thêm vào `mainUI.ui`:

```xml
<!-- Thay đổi widget types -->
exposureEdit: QLineEdit → QDoubleSpinBox
gainEdit: QLineEdit → QDoubleSpinBox  
evEdit: QLineEdit → QDoubleSpinBox

<!-- Thêm Apply/Cancel buttons -->
applySetting: QPushButton
cancelSetting: QPushButton
```

## Test Results Expected
- App khởi động thành công
- Warning log về missing widgets (nếu chưa update UI)
- Camera functionality hoạt động với widgets hiện có
- Pending settings system ready cho khi UI được update
