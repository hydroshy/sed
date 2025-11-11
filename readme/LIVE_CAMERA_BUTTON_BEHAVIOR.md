# Live Camera Button (onlineCamera) Behavior

## Tổng quan

Nút "Live Camera" (onlineCamera) hoạt động khác nhau tùy vào chế độ camera được chọn:

## Chế độ hoạt động

### 🟢 LIVE MODE (liveCameraMode)

**Khi click nút "Live Camera" trong chế độ Live:**

```
Live Camera Button (OFF) → Click → Live Camera Button (ON)
                                         ↓
                              _start_camera_stream_continuous()
                                         ↓
                           1. Disable external trigger (nếu có)
                           2. Call camera_stream.start_live()
                           3. Enable job processing
                           4. Stream liên tục ✅
```

**Kết quả**: Camera chạy **liên tục (continuous)** - nhận frame liên tục từ camera

**Chi tiết code**:
```python
def on_live_camera_clicked(self):
    if current_mode == 'live':
        # LIVE MODE: Start continuous streaming
        success = self._start_camera_stream_continuous()
    
def _start_camera_stream_continuous(self):
    # Disable trigger mode
    if self.camera_stream.external_trigger_enabled:
        self.camera_stream.set_trigger_mode(False)
    
    # Start continuous live stream
    success = self.camera_stream.start_live()
    
    # Enable job processing
    self.job_enabled = True
```

### 🔴 TRIGGER MODE (triggerCameraMode)

**Khi click nút "Live Camera" trong chế độ Trigger:**

```
Live Camera Button (OFF) → Click → Live Camera Button (ON)
                                         ↓
                              _start_camera_stream()
                                         ↓
                        Giữ nguyên chế độ trigger hiện tại
                        (Không ép forced continuous) ✅
```

**Kết quả**: Camera hoạt động ở **chế độ hiện tại** (trigger mode) - không bắt buộc chuyển sang continuous

**Chi tiết code**:
```python
def on_live_camera_clicked(self):
    if current_mode == 'trigger':
        # TRIGGER MODE: Keeping current trigger mode
        success = self._start_camera_stream()
    
def _start_camera_stream(self):
    # Start stream nhưng giữ trigger configuration
    # Không disable external trigger - camera vẫn ở trigger mode
    success = self.camera_stream.start_live()
    self.job_enabled = True
```

## Sự khác biệt chính

| Chế độ | Nút "Live Camera" | Kết quả |
|-------|-----------------|--------|
| **Live** 🟢 | ON | Continuous streaming (liên tục) |
| **Trigger** 🔴 | ON | Giữ trigger mode (chế độ trigger) |

## Frame source

### Live Mode
- Stream continuous từ camera `start_live()`
- Frame được phát hành liên tục
- Thích hợp cho preview/monitoring

### Trigger Mode
- Camera ở trigger mode (chờ trigger signal)
- Frame chỉ được capture khi nhận trigger
- Thích hợp cho capture controlled/timed

## UX Flow

### Kịch bản 1: Live Mode Preview
```
1. Chọn "Live Camera Mode" button
   → camera_manager.current_mode = 'live'
   
2. Click "Live Camera" button (ON)
   → on_live_camera_clicked()
   → current_mode == 'live' → _start_camera_stream_continuous()
   → camera_stream.start_live()
   → Stream liên tục ✅
   
3. Click "Live Camera" button (OFF)
   → _stop_camera_stream()
   → camera_stream.stop_live()
```

### Kịch bản 2: Trigger Mode Monitoring
```
1. Chọn "Trigger Camera Mode" button
   → camera_manager.current_mode = 'trigger'
   
2. Cấu hình trigger (external IMX296, delay, v.v.)
   
3. Click "Live Camera" button (ON)
   → on_live_camera_clicked()
   → current_mode == 'trigger' → _start_camera_stream()
   → Giữ trigger mode (external_trigger_enabled = true)
   → Camera chờ trigger signals ✅
   
4. Khi có trigger signal:
   → Camera capture frame
   → trigger_capture() được gọi
   
5. Click "Live Camera" button (OFF)
   → _stop_camera_stream()
```

## Implementation Details

### Method: `on_live_camera_clicked()`
- **Location**: `gui/camera_manager.py` line ~1655
- **Logic**: 
  - Nếu live mode → gọi `_start_camera_stream_continuous()`
  - Nếu trigger mode → gọi `_start_camera_stream()`
  - Tắt → gọi `_stop_camera_stream()` (chung cho cả 2 mode)

### Method: `_start_camera_stream_continuous()`
- **Location**: `gui/camera_manager.py` (new method)
- **Mục đích**: Bảo đảm continuous streaming trong live mode
- **Steps**:
  1. Check xem camera đã stream hay chưa
  2. Disable external trigger nếu đang bật
  3. Call `camera_stream.start_live()` để stream liên tục
  4. Enable job processing

### Method: `_start_camera_stream()`
- **Location**: `gui/camera_manager.py` line ~1777
- **Mục đích**: Start stream nhưng giữ current mode (dùng trong trigger mode)
- **Khác biệt**: Không disable external trigger → camera vẫn ở trigger mode

## Notes

- ✅ Behavior **phụ thuộc vào current camera mode** (live vs trigger)
- ✅ Button text vẫn là "Live Camera" nhưng hoạt động khác nhau
- ✅ Trigger mode vẫn có thể show preview (nếu capture được)
- ✅ Job processing được enable trong cả 2 mode (nếu cần)

