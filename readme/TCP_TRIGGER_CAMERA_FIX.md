# TCP Trigger Camera Fix - Gửi Lệnh Qua TCP Thay Vì Capture Trực Tiếp

## Yêu Cầu (User Request)
"Sửa lại cách hoạt động của nút triggerCamera, khi nhấn sẽ gửi lệnh triggerCamera qua TCP thay vì triggerCamera bằng cách capture"

Translation: "Fix the triggerCamera button to send 'triggerCamera' command via TCP instead of direct capture"

## Vấn Đề Cũ (Old Behavior)
Khi người dùng nhấn nút "Trigger Camera", ứng dụng thực hiện:
1. Gửi TR1 signal tới light controller
2. **Thực hiện capture trực tiếp** từ camera (activate_capture_request)
3. Xử lý frame qua job pipeline

```python
# ❌ OLD CODE
self._send_trigger_to_light_controller()  # Send TR1 signal
self.activate_capture_request()            # ❌ Direct capture - not TCP!
```

## Giải Pháp Mới (New Behavior)
Khi người dùng nhấn nút "Trigger Camera", ứng dụng sẽ:
1. **Gửi lệnh "triggerCamera" qua TCP** đến thiết bị remote
2. Thiết bị remote xử lý trigger và trả lại kết quả

```python
# ✅ NEW CODE
tcp_controller = self.main_window.tcp_controller
trigger_command = "triggerCamera"
success = tcp_controller.send_message(trigger_command)  # ✅ Send via TCP!
```

## File Được Sửa
- **`gui/camera_manager.py`** - Phương thức `on_trigger_camera_clicked()` (lines 1950-2050)

## Chi Tiết Thay Đổi

### Trước (Before):
```python
def on_trigger_camera_clicked(self):
    # ... validation code ...
    
    if current_mode == 'trigger' and button_is_enabled:
        self.trigger_camera_btn.setEnabled(False)
        
        # Gửi TR1 tới light controller
        self._send_trigger_to_light_controller()
        
        # ❌ Capture trực tiếp bằng activate_capture_request
        self._trigger_capturing = True
        self.activate_capture_request()  # PROBLEM: Direct capture!
        self._trigger_capturing = False
        
        self.trigger_camera_btn.setEnabled(True)
```

### Sau (After):
```python
def on_trigger_camera_clicked(self):
    # ... validation code ...
    
    if current_mode == 'trigger' and button_is_enabled:
        self.trigger_camera_btn.setEnabled(False)
        
        # ✅ Gửi lệnh "triggerCamera" qua TCP
        try:
            tcp_controller = self.main_window.tcp_controller
            
            # Kiểm tra kết nối TCP
            if not tcp_controller._connected:
                print("TCP connection not active")
                return
            
            # Gửi lệnh via TCP
            trigger_command = "triggerCamera"
            success = tcp_controller.send_message(trigger_command)
            
            if success:
                print(f"Successfully sent TCP command: {trigger_command}")
        except Exception as e:
            print(f"Error sending triggerCamera via TCP: {e}")
        finally:
            self.trigger_camera_btn.setEnabled(True)
```

## Lưu Ý Quan Trọng

### 1. **TCP Connection Cần Phải Active**
```python
if not tcp_controller._connected:
    print("TCP connection not active")
    # Button sẽ được enable lại và trigger không gửi được
    return
```

### 2. **Error Handling**
- Nếu tcp_controller không tồn tại → hiển thị debug message
- Nếu TCP không kết nối → hiển thị debug message
- Nếu gửi thất bại → hiển thị debug message
- Trong mọi trường hợp, button vẫn được enable lại bằng `finally` block

### 3. **Double-Click Protection Vẫn Hoạt Động**
```python
# 500ms cooldown vẫn có hiệu lực
if time_since_last < 500:
    print(f"Trigger clicked too fast")
    return
```

## Flow Diagram

### Old Flow (Direct Capture):
```
Button Click
    ↓
Validate mode & button state
    ↓
Send TR1 to Light Controller
    ↓
activate_capture_request()  ← Direct local capture
    ↓
Process frame through job pipeline
```

### New Flow (TCP Command):
```
Button Click
    ↓
Validate mode & button state
    ↓
Get TCP Controller
    ↓
Check TCP Connection
    ↓
Send "triggerCamera" via TCP  ← Remote trigger!
    ↓
Remote device processes and sends back frame
```

## Testing
1. Đảm bảo TCP connection đang active
2. Chuyển sang Trigger Mode
3. Nhấn nút "Trigger Camera"
4. Kiểm tra console debug messages:
   - `Successfully sent TCP command: triggerCamera` ✅ OK
   - `TCP connection not active` ❌ Error
   - `TCP controller not found` ❌ Error

## Lợi Ích
- ✅ Gửi trigger qua TCP cho phép remote control
- ✅ Không phải capture trực tiếp từ local camera
- ✅ Thiết bị remote có thể kiểm soát quá trình trigger
- ✅ Giảm coupling giữa UI và camera hardware
