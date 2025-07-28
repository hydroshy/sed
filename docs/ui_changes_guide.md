# Hướng dẫn thay đổi UI cho Logic mới

## Mô tả thay đổi

### 1. Camera Mode Selection (Mutual Exclusive)
- **Live Camera** và **Trigger Camera** chỉ cho phép chọn 1 trong 2
- Khi chọn Live → Trigger bị disable
- Khi chọn Trigger → Live bị disable
- UI hiển thị trạng thái với màu sắc khác nhau

### 2. Initial State
- Tất cả UI camera bị disable khi khởi động
- Chỉ enable sau khi setup hoàn tất

### 3. Exposure Settings với Apply/Cancel
- **Auto/Manual Exposure**: Mutual exclusive
- Khi chọn Auto → các control manual bị disable
- Khi chọn Manual → có thể điều chỉnh exposure/gain/ev
- **Apply Setting**: Áp dụng tất cả thay đổi
- **Cancel Setting**: Khôi phục về giá trị mặc định

### 4. UI Controls thay đổi
- `exposureEdit`: Từ QLineEdit → **QDoubleSpinBox**
- `gainEdit`: Từ QLineEdit → **QDoubleSpinBox**  
- `evEdit`: Từ QLineEdit → **QDoubleSpinBox**

## UI Widgets cần thêm/sửa trong mainUI.ui

### 1. Thay đổi widget types:
```
exposureEdit: QLineEdit → QDoubleSpinBox
- objectName: exposureEdit
- minimum: 0.001
- maximum: 1000.0
- value: 10.0
- suffix: " ms"
- decimals: 3

gainEdit: QLineEdit → QDoubleSpinBox
- objectName: gainEdit
- minimum: 1.0
- maximum: 16.0
- value: 1.0
- decimals: 2

evEdit: QLineEdit → QDoubleSpinBox
- objectName: evEdit
- minimum: -2.0
- maximum: 2.0
- value: 0.0
- decimals: 1
```

### 2. Thêm Apply/Cancel buttons:
```
applySetting: QPushButton
- objectName: applySetting
- text: "Apply"

cancelSetting: QPushButton
- objectName: cancelSetting
- text: "Cancel"
```

### 3. Kiểm tra tên button hiện có:
```
liveCamera: QPushButton (đã có)
triggerCamera: QPushButton (đã có)
autoExposure: QPushButton (đã có)
manualExposure: QPushButton (đã có)
```

## Tính năng đã implement

### CameraManager (gui/camera_manager.py)
- ✅ **Camera Mode Logic**: Mutual exclusive Live/Trigger
- ✅ **UI State Management**: Enable/disable toàn bộ UI
- ✅ **Exposure Mode Logic**: Auto/Manual exclusive
- ✅ **Pending Settings**: Lưu trữ settings chưa apply
- ✅ **Apply/Cancel Logic**: Áp dụng hoặc hủy thay đổi
- ✅ **Visual Feedback**: Màu sắc button theo trạng thái

### MainWindow (gui/main_window_new.py)
- ✅ **Widget Finding**: Tìm tất cả widget cần thiết
- ✅ **Setup Integration**: Kết nối với CameraManager
- ✅ **Auto Enable**: Tự động enable UI sau setup

## Trạng thái UI

### Camera Mode States:
- **No Mode**: Cả 2 button bình thường, cả 2 enabled
- **Live Mode**: Live button đỏ + "Stop Live", Trigger disabled
- **Trigger Mode**: Trigger button xanh + "Trigger", Live disabled

### Exposure Mode States:
- **Auto Mode**: Auto button xanh, manual controls disabled
- **Manual Mode**: Manual button vàng, manual controls enabled

### Button Colors:
```css
Live Active: background-color: #ff6b6b (Red)
Trigger Active: background-color: #4ecdc4 (Teal)
Auto Exposure: background-color: #51cf66 (Green)
Manual Exposure: background-color: #ffd43b (Yellow)
```

## Workflow sử dụng

### 1. Khởi động:
- Tất cả UI disabled
- Sau setup → UI enabled
- Mặc định: Auto exposure mode

### 2. Camera Operation:
- Chọn Live Camera → Start preview, Trigger disabled
- Chọn Trigger Camera → Take photo, Live disabled
- Click button đang active → Tắt mode, enable button còn lại

### 3. Settings Operation:
- Thay đổi exposure mode → UI update ngay
- Điều chỉnh values → Lưu vào pending (chưa apply)
- Click Apply → Áp dụng tất cả pending settings
- Click Cancel → Reset về default values

## Lưu ý implementation
- Tất cả camera operations đều async
- UI state được update real-time
- Pending settings đảm bảo không bị mất khi switch mode
- Error handling cho tất cả operations
- Logging đầy đủ cho debugging
