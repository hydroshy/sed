"""
Các phương thức hỗ trợ external trigger cho CameraStream
File này chứa các hàm giúp camera chờ và phản hồi với external trigger từ hardware
"""

from .camera_stream import CameraStream
import time
import os

# Add external trigger methods if they don't exist
if not hasattr(CameraStream, 'start_external_trigger'):
    print("DEBUG: [CameraStream] Adding start_external_trigger method to class")
    def _start_external_trigger(self):
        """
        Bắt đầu chế độ external trigger - chờ tín hiệu trigger từ ngoài vào
        
        - Thiết lập hardware để đợi tín hiệu trigger ngoài
        - Cấu hình camera đúng cách cho chế độ trigger
        - Bắt đầu chờ frame mới từ trigger
        """
        try:
            print("DEBUG: [CameraStream] Starting external trigger mode")
            
            # Đảm bảo camera khởi tạo
            if not hasattr(self, 'picam2') or self.picam2 is None:
                print("DEBUG: [CameraStream] Initializing camera for external trigger")
                if not self._safe_init_picamera():
                    print("DEBUG: [CameraStream] Failed to initialize camera for trigger mode")
                    return False
            
            # Dừng camera hiện tại nếu đang chạy
            if hasattr(self, 'picam2') and self.picam2 and self.picam2.started:
                print("DEBUG: [CameraStream] Stopping current camera before trigger mode")
                self.picam2.stop()
            
            # Thiết lập hardware trigger
            self.set_trigger_mode(True)
            
            # Cấu hình cho chế độ trigger
            self.external_trigger_enabled = True
            self._trigger_waiting = True
            self._last_sensor_ts = 0
            
            # Cấu hình camera cho chế độ trigger
            try:
                # Tạo cấu hình video thay vì still để chờ trigger liên tục
                video_config = self.picam2.create_video_configuration()
                
                # Thiết lập các tham số cần thiết
                if "controls" not in video_config:
                    video_config["controls"] = {}
                
                # Thiết lập manual exposure
                video_config["controls"]["ExposureTime"] = self.current_exposure
                video_config["controls"]["AeEnable"] = False
                
                # Noise reduction tối thiểu để tránh lỗi TDN
                video_config["controls"]["NoiseReductionMode"] = 3  # Minimal
                
                # Cấu hình camera
                self.picam2.configure(video_config)
                print("DEBUG: [CameraStream] Camera configured for external trigger")
                
                # Bắt đầu camera không có preview
                self.picam2.start(show_preview=False)
                print("DEBUG: [CameraStream] Camera started for external trigger")
                
                # Bắt đầu timer để kiểm tra frame mới từ trigger
                if hasattr(self, 'timer') and not self.timer.isActive():
                    print("DEBUG: [CameraStream] Starting timer for trigger checking")
                    self.timer.start(100)  # 10 FPS check
                
                return True
            except Exception as e:
                print(f"DEBUG: [CameraStream] Error configuring camera for trigger: {e}")
                # Cố gắng khôi phục về chế độ bình thường
                self.set_trigger_mode(False)
                return False
                
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error in start_external_trigger: {e}")
            return False
    
    CameraStream.start_external_trigger = _start_external_trigger

if not hasattr(CameraStream, 'stop_external_trigger'):
    print("DEBUG: [CameraStream] Adding stop_external_trigger method to class")
    def _stop_external_trigger(self):
        """
        Dừng chế độ external trigger
        
        - Tắt chế độ trigger của hardware
        - Dừng camera và timer
        - Đặt lại các flag liên quan
        """
        try:
            print("DEBUG: [CameraStream] Stopping external trigger mode")
            
            # Dừng chờ trigger
            self._trigger_waiting = False
            self.external_trigger_enabled = False
            
            # Dừng timer nếu đang chạy
            if hasattr(self, 'timer') and self.timer.isActive():
                print("DEBUG: [CameraStream] Stopping timer for trigger")
                self.timer.stop()
            
            # Dừng camera
            if hasattr(self, 'picam2') and self.picam2 and self.picam2.started:
                print("DEBUG: [CameraStream] Stopping camera from trigger mode")
                self.picam2.stop()
            
            # Thiết lập lại hardware
            self.set_trigger_mode(False)
            
            return True
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error in stop_external_trigger: {e}")
            return False
    
    CameraStream.stop_external_trigger = _stop_external_trigger

if not hasattr(CameraStream, 'check_trigger_frame'):
    print("DEBUG: [CameraStream] Adding check_trigger_frame method to class")
    def _check_trigger_frame(self):
        """
        Kiểm tra xem có frame mới từ external trigger hay không
        
        Phương thức này được gọi định kỳ bởi timer để kiểm tra frame mới
        khi camera đang ở chế độ external trigger.
        """
        if not hasattr(self, '_trigger_waiting') or not self._trigger_waiting or not hasattr(self, 'external_trigger_enabled') or not self.external_trigger_enabled:
            return
            
        try:
            # Thử lấy frame mới với timeout ngắn
            frame = self.wait_for_frame_with_timeout(timeout_ms=100)  # Timeout ngắn để check nhanh
            
            if frame is not None:
                print("DEBUG: [CameraStream] Got new frame from external trigger")
                # Phát tín hiệu frame_ready với frame mới
                self.frame_ready.emit(frame)
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error in check_trigger_frame: {e}")
    
    CameraStream.check_trigger_frame = _check_trigger_frame

# Bổ sung xử lý check_trigger_frame vào timerEvent
if hasattr(CameraStream, 'timerEvent'):
    original_timerEvent = CameraStream.timerEvent
    
    def _enhanced_timerEvent(self, event):
        # Gọi timerEvent gốc
        original_timerEvent(self, event)
        
        # Thêm xử lý trigger frame
        if hasattr(self, '_trigger_waiting') and self._trigger_waiting and hasattr(self, 'check_trigger_frame'):
            self.check_trigger_frame()
    
    CameraStream.timerEvent = _enhanced_timerEvent
