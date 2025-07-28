import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from picamera2 import Picamera2
import threading

class CameraStream(QObject):
    frame_ready = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.picam2 = Picamera2()
        self.timer = QTimer()
        self.timer.timeout.connect(self._query_frame)
        self.is_live = False
        
        # Initialize exposure tracking
        self.current_exposure = 10000  # Default 10ms in μs
        
        # Đặt độ phân giải đồng bộ cho cả preview và still
        self.frame_size = (1440, 1080)  # Crop nhỏ để tăng fps, bạn có thể chỉnh lại
        # Đặt FrameRate cao cho Global Shutter (nếu camera hỗ trợ)
        self.preview_config = self.picam2.create_preview_configuration(
            main={"size": self.frame_size},
            controls={
                "FrameRate": 60,
                "ExposureTime": self.current_exposure,
                "AeEnable": False  # Start in manual mode
            }
        )
        self.still_config = self.picam2.create_still_configuration(main={"size": self.frame_size})
        self.picam2.configure(self.preview_config)

    def _update_preview_config(self):
        """Update preview config với current settings"""
        # Method để update preview config trước khi restart camera
        try:
            # Use the stored current_exposure value instead of trying to get from metadata
            # when camera is stopped
            exposure_to_use = self.current_exposure
            print(f"DEBUG: Using stored current_exposure: {exposure_to_use}μs")
            
            # Update preview config with current controls
            if hasattr(self, 'preview_config') and self.preview_config:
                if "controls" not in self.preview_config:
                    self.preview_config["controls"] = {}
                
                # Update exposure time in preview config
                self.preview_config["controls"]["ExposureTime"] = exposure_to_use
                self.preview_config["controls"]["AeEnable"] = False  # Keep manual mode
                print(f"DEBUG: Updated preview config ExposureTime to {exposure_to_use}μs")
        except Exception as e:
            print(f"DEBUG: _update_preview_config error: {e}")
    
    def start_live(self):
        if not self.is_live:
            self._update_preview_config()  # Update config trước khi restart
            self.picam2.stop()
            self.picam2.configure(self.preview_config)
            self.picam2.start()
            self.timer.start(33)  # Adjusted to ~30 FPS for better performance
            self.is_live = True

    def stop_live(self):
        if self.timer.isActive():
            self.timer.stop()
        if self.is_live:
            self.picam2.stop()
            self.is_live = False

    def _query_frame(self):
        frame = self.picam2.capture_array()
        if frame is not None:
            # Process frame in a separate thread to avoid blocking
            threading.Thread(target=self._process_frame, args=(frame,), daemon=True).start()

    def _process_frame(self, frame):
        # Placeholder for frame processing logic
        # Add any heavy processing here
        self.frame_ready.emit(frame)

    def trigger_capture(self):
        # Chuyển sang chế độ still, chụp ảnh, sau đó về preview
        was_live = self.is_live
        self.picam2.stop()
        self.picam2.configure(self.still_config)
        self.picam2.start()
        frame = self.picam2.capture_array()
        if frame is not None:
            self.frame_ready.emit(frame)
        self.picam2.stop()
        self.picam2.configure(self.preview_config)
        if was_live:
            self.picam2.start()

    def set_zoom(self, value):
        pass  # Có thể cấu hình zoom qua Picamera2 nếu cần

    def set_focus(self, value):
        pass  # Có thể cấu hình focus qua Picamera2 nếu cần

    # --- Chuyển đổi giá trị giữa UI và camera ---
    def ui_to_exposure(self, value):
        # UI nhập ms, camera cần us
        # Nếu bạn muốn UI nhập trực tiếp us thì bỏ *1000
        return int(float(value) * 1000)

    def exposure_to_ui(self, value):
        # Camera trả về us, UI hiển thị ms
        return round(float(value) / 1000, 2)

    def ui_to_gain(self, value):
        # UI nhập int, camera cần float
        return float(value)

    def gain_to_ui(self, value):
        # Camera trả về float, UI hiển thị int
        return int(round(value))

    def ui_to_ev(self, value):
        # UI chỉ cho phép -1, 0, 1
        try:
            v = int(value)
            if v < -1:
                v = -1
            elif v > 1:
                v = 1
            return float(v)
        except Exception:
            return 0.0

    def ev_to_ui(self, value):
        # Camera trả về float, UI hiển thị int, chỉ -1,0,1
        v = int(round(value))
        if v < -1:
            v = -1
        elif v > 1:
            v = 1
        return v

    def set_exposure(self, value):
        # value từ UI là μs, camera cũng cần μs
        try:
            exposure_value = int(value)
            print(f"DEBUG: Setting exposure to {exposure_value}μs")
            
            # Set the control on the camera
            self.picam2.set_controls({"ExposureTime": exposure_value, "AeEnable": False})
            print(f"DEBUG: Set camera ExposureTime to {exposure_value} and AeEnable to False")
            
            # Store current exposure for _update_preview_config
            self.current_exposure = exposure_value
            
            # Also update preview config if we have it
            if hasattr(self, 'preview_config') and self.preview_config:
                if "controls" not in self.preview_config:
                    self.preview_config["controls"] = {}
                self.preview_config["controls"]["ExposureTime"] = exposure_value
                self.preview_config["controls"]["AeEnable"] = False
                print(f"DEBUG: Updated preview_config ExposureTime to {exposure_value}μs")
                
        except Exception as e:
            print(f"[CameraStream] set_exposure error: {e}")

    def set_gain(self, value):
        try:
            cam_value = self.ui_to_gain(value)
            self.picam2.set_controls({"AnalogueGain": cam_value})
        except Exception as e:
            print(f"[CameraStream] set_gain error: {e}")

    def set_ev(self, value):
        try:
            cam_value = self.ui_to_ev(value)
            self.picam2.set_controls({"ExposureValue": cam_value})
        except Exception as e:
            print(f"[CameraStream] set_ev error: {e}")

    def set_auto_exposure(self, enable: bool):
        try:
            self.picam2.set_controls({"AeEnable": bool(enable)})
        except Exception as e:
            print(f"[CameraStream] set_auto_exposure error: {e}")

    def get_exposure(self):
        # Trả về μs cho UI
        try:
            val = self.picam2.capture_metadata().get("ExposureTime", 0)
            return int(val)  # Đã là μs
        except Exception:
            return 10000  # Default 10ms

    def get_gain(self):
        try:
            val = self.picam2.capture_metadata().get("AnalogueGain", 1.0)
            return self.gain_to_ui(val)
        except Exception:
            return 1

    def get_ev(self):
        try:
            val = self.picam2.capture_metadata().get("ExposureValue", 0.0)
            return self.ev_to_ui(val)
        except Exception:
            return 0

    def set_frame_size(self, width, height):
        """Set frame size và cập nhật camera configuration"""
        try:
            print(f"DEBUG: Setting frame size to {width}x{height}")
            
            # Update frame_size
            self.frame_size = (width, height)
            
            # Update preview config
            if hasattr(self, 'preview_config'):
                self.preview_config = self.picam2.create_preview_configuration(
                    main={"size": self.frame_size},
                    controls={
                        "FrameRate": 60,
                        "ExposureTime": self.current_exposure,
                        "AeEnable": False
                    }
                )
                print(f"DEBUG: Updated preview_config with new frame size: {self.frame_size}")
            
            # Update still config
            if hasattr(self, 'still_config'):
                self.still_config = self.picam2.create_still_configuration(
                    main={"size": self.frame_size}
                )
                print(f"DEBUG: Updated still_config with new frame size: {self.frame_size}")
            
            # If camera is running, restart with new config
            if self.is_live:
                print("DEBUG: Camera is live, restarting with new frame size")
                self.stop_live()
                self.start_live()
            else:
                # Just reconfigure
                self.picam2.configure(self.preview_config)
                print("DEBUG: Reconfigured camera with new frame size")
                
        except Exception as e:
            print(f"[CameraStream] set_frame_size error: {e}")
