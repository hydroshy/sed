# camera_stream_fixed.py
# Phiên bản sửa lỗi của camera_stream.py với tất cả các phương thức cần thiết
# Lưu tệp này và thay thế camera_stream.py hiện tại bằng tệp này

from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread, QMutex, QMutexLocker, QWaitCondition
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QImage, QPixmap
import sys
import os
import numpy as np
import threading
import logging
import time

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Try to import Picamera2, or use mock if not available
try:
    from picamera2 import Picamera2
    logger.info("Successfully imported Picamera2")
except ImportError as e:
    logger.error(f"Failed to import Picamera2: {e}")
    # Create a placeholder for Picamera2 that will raise an exception if used
    class Picamera2:
        def __init__(self):
            logger.error("Using mock Picamera2 class due to import error")
            raise RuntimeError("Picamera2 import failed - camera functionality unavailable")

class TriggerWaiterThread(QThread):
    """Thread riêng biệt để đợi trigger mà không làm treo UI"""
    trigger_completed = pyqtSignal(object)  # Phát tín hiệu khi có frame mới
    trigger_timeout = pyqtSignal()          # Phát tín hiệu khi timeout
    trigger_error = pyqtSignal(str)         # Phát tín hiệu khi có lỗi
    
    def __init__(self, camera_stream, timeout_ms=5000):
        super().__init__()
        self.camera_stream = camera_stream
        self.timeout_ms = timeout_ms
        self.mutex = QMutex()
        self.condition = QWaitCondition()
        self.stopped = False
        self.frame_ready = False
        self.last_frame = None
        
    def run(self):
        """Hàm chạy chính của thread"""
        try:
            print("DEBUG: [TriggerWaiterThread] Started waiting for trigger")
            # Đợi frame từ external trigger
            timeout_ms = self.timeout_ms
            
            with QMutexLocker(self.mutex):
                # Đợi cho đến khi có frame hoặc timeout
                while not self.frame_ready and not self.stopped:
                    # Đợi signal từ camera callback hoặc timeout
                    timeout = self.condition.wait(self.mutex, timeout_ms)
                    if not timeout:  # Nếu timeout
                        print("DEBUG: [TriggerWaiterThread] Timeout waiting for trigger")
                        self.trigger_timeout.emit()
                        return
                
                if self.frame_ready and self.last_frame is not None:
                    print("DEBUG: [TriggerWaiterThread] Frame received, emitting signal")
                    self.trigger_completed.emit(self.last_frame)
        except Exception as e:
            print(f"DEBUG: [TriggerWaiterThread] Error: {e}")
            self.trigger_error.emit(str(e))
    
    def stop(self):
        """Dừng thread an toàn"""
        with QMutexLocker(self.mutex):
            self.stopped = True
            self.condition.wakeAll()
    
    def notify_frame_ready(self, frame):
        """Được gọi từ callback khi có frame mới"""
        with QMutexLocker(self.mutex):
            self.last_frame = frame
            self.frame_ready = True
            self.condition.wakeAll()

class CameraStream(QObject):
    frame_ready = pyqtSignal(np.ndarray)

    def _safe_init_picamera(self):
        """Safely initialize Picamera2 with error handling"""
        if hasattr(self, '_picamera_import_failed') and self._picamera_import_failed:
            logger.warning("Skipping Picamera2 initialization due to previous import failure")
            return False
        
        try:
            # Add stubs directory to path if it exists (for pykms stub)
            stubs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'stubs')
            if os.path.exists(stubs_dir) and stubs_dir not in sys.path:
                sys.path.insert(0, stubs_dir)
                logger.info(f"Added stubs directory to path: {stubs_dir}")
            
            # Try to import and initialize Picamera2
            from picamera2 import Picamera2
            self.picam2 = Picamera2()
            self.is_camera_available = True
            logger.info("Picamera2 initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Picamera2: {e}")
            self._picamera_import_failed = True
            self.is_camera_available = False
            return False

    def __init__(self):
        super().__init__()
        self.is_camera_available = False
        self.picam2 = None
        self._mutex = QMutex()  # For thread safety
        self.job_enabled = False  # Mặc định DISABLE job execution để tránh camera bị đóng băng
        self._picamera_import_failed = False
        
        # Thêm các biến cho trigger không đồng bộ
        self.trigger_mutex = QMutex()
        self.trigger_condition = QWaitCondition()
        self.trigger_thread = None
        self.trigger_timeout_ms = 5000  # 5 giây mặc định
        
        # Try to initialize the camera
        if self._safe_init_picamera():
            print("DEBUG: [CameraStream] Camera initialized successfully")
            print("DEBUG: [CameraStream] Job execution is DISABLED by default (camera will still work, but without job processing)")
            print("DEBUG: [CameraStream] Use job toggle button to enable full processing if needed")
            
            # Workaround for allocator attribute error in some Picamera2 versions
            self._setup_allocator_workaround()
        else:
            print("DEBUG: [CameraStream] Camera initialization failed, running in fallback mode")
            self.is_camera_available = False
            
        self.timer = QTimer()
        self.is_live = False
        
        # Initialize exposure tracking
        self.current_exposure = 10000  # Default 10ms in μs
        self.current_format = "BGR888" # Default format
        
        # Only configure if camera is available
        if self.is_camera_available and self.picam2:
            try:
                # Đặt độ phân giải đồng bộ cho cả preview và still
                self.frame_size = (1440, 1080)  # Crop nhỏ để tăng fps, bạn có thể chỉnh lại
                # Đặt FrameRate cao cho Global Shutter (nếu camera hỗ trợ)
                self.preview_config = self.picam2.create_preview_configuration(
                    main={"size": self.frame_size, "format": self.current_format},
                    controls={
                        "FrameRate": 60,
                        "ExposureTime": self.current_exposure,
                        "AeEnable": False  # Start in manual mode
                    }
                )
                self.still_config = self.picam2.create_still_configuration(main={"size": self.frame_size, "format": self.current_format})
                
                # Configure the camera with preview config
                self.picam2.configure(self.preview_config)
                print("DEBUG: [CameraStream] Camera configured successfully")
            except Exception as e:
                print(f"DEBUG: [CameraStream] Camera configuration failed: {e}")
                self.is_camera_available = False
        else:
            print("DEBUG: [CameraStream] Camera not available, skipping configuration")
            
        # Kết nối timer tại đây sau khi các phương thức đã được định nghĩa
        self._setup_timer()

    def _setup_timer(self):
        """Thiết lập và kết nối timer với phương thức query_frame"""
        try:
            if hasattr(self, 'timer'):
                self.timer.timeout.connect(self._query_frame)
                print("DEBUG: [CameraStream] Timer connected to _query_frame")
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error setting up timer: {e}")
            
    def get_available_formats(self):
        """Get available camera formats."""
        if not self.is_camera_available or not self.picam2:
            return []
        try:
            # Return a list of safe format strings
            # MJPEG format caused a crash, so exclude it
            return ["BGR888", "RGB888", "YUV420"]
        except Exception as e:
            print(f"DEBUG: [CameraStream] Could not get formats: {e}")
            return ["BGR888", "RGB888"]
            
    def set_format(self, format_str):
        """Set the camera format and reconfigure."""
        if not self.is_camera_available or not self.picam2:
            print("DEBUG: [CameraStream] Camera not available to set format.")
            return

        print(f"DEBUG: [CameraStream] Setting format to {format_str}")
        
        # Kiểm tra format an toàn
        safe_formats = ["BGR888", "RGB888", "YUV420"]
        if format_str not in safe_formats:
            print(f"DEBUG: [CameraStream] Format {format_str} may not be supported. Using BGR888 instead.")
            format_str = "BGR888"
            
        self.current_format = format_str
        
        # Stop the camera if it's running
        was_live = self.is_live
        if was_live:
            self.stop_live()

        # Re-create configurations with the new format
        try:
            self.preview_config = self.picam2.create_preview_configuration(
                main={"size": self.frame_size, "format": self.current_format},
                controls={
                    "FrameRate": 60,
                    "ExposureTime": self.current_exposure,
                    "AeEnable": False
                }
            )
            self.still_config = self.picam2.create_still_configuration(
                main={"size": self.frame_size, "format": self.current_format}
            )
            
            # Re-configure the camera
            self.picam2.configure(self.preview_config)
            print(f"DEBUG: [CameraStream] Reconfigured camera for format {self.current_format}")

            # Restart the live view if it was running before
            if was_live:
                self.start_live()
        except Exception as e:
            print(f"DEBUG: [CameraStream] Failed to set format: {e}")

    def _setup_allocator_workaround(self):
        """Workaround for allocator attribute error in some Picamera2 versions"""
        try:
            if hasattr(self.picam2, 'allocator'):
                # Allocator exists, no workaround needed
                return
            
            # If allocator doesn't exist, try to create a dummy one
            # This is a workaround for version compatibility issues
            class DummyAllocator:
                def sync(self, allocator, buffer, flag):
                    # Dummy implementation
                    return True
                
            # Attach the dummy allocator to picam2
            self.picam2.allocator = DummyAllocator()
            print("DEBUG: [CameraStream] Applied allocator workaround")
        except Exception as e:
            print(f"DEBUG: [CameraStream] Failed to apply allocator workaround: {e}")

    def is_running(self):
        """Check if camera is running (in live mode)"""
        return self.is_live
    
    def set_trigger_mode(self, enabled):
        """
        Set the camera hardware trigger mode via system command
        
        Args:
            enabled (bool): True to enable hardware trigger mode, False for normal mode
        
        Returns:
            bool: Success status
        """
        try:
            value = "1" if enabled else "0"
            cmd = f"echo {value} | sudo tee /sys/module/imx296/parameters/trigger_mode"
            print(f"DEBUG: [CameraStream] Setting hardware trigger mode to {value} with: {cmd}")
            
            import subprocess
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"DEBUG: [CameraStream] Successfully set trigger mode to {value}")
                print(f"DEBUG: [CameraStream] Command output: {result.stdout.strip()}")
                return True
            else:
                print(f"DEBUG: [CameraStream] Failed to set trigger mode: {result.stderr}")
                return False
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error setting trigger mode: {e}")
            return False

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
                
            # Also update still config if it exists to keep them in sync
            if hasattr(self, 'still_config') and self.still_config:
                if "controls" not in self.still_config:
                    self.still_config["controls"] = {}
                self.still_config["controls"]["ExposureTime"] = exposure_to_use
                self.still_config["controls"]["AeEnable"] = False
                print(f"DEBUG: Updated still config ExposureTime to {exposure_to_use}μs")
        except Exception as e:
            print(f"DEBUG: _update_preview_config error: {e}")

    def set_job_enabled(self, enabled):
        """Set job execution enabled/disabled"""
        self.job_enabled = enabled
        print(f"DEBUG: [CameraStream] Job execution {'ENABLED' if enabled else 'DISABLED'}")

    def is_job_enabled(self):
        """Check if job execution is enabled"""
        return self.job_enabled
    
    def start_live(self):
        """Start live camera preview"""
        try:
            print("DEBUG: [CameraStream] start_live called")
            
            if not self.is_camera_available:
                print("DEBUG: [CameraStream] Camera not available for live mode")
                return
            
            # Ensure camera is initialized
            if not hasattr(self, 'picam2') or self.picam2 is None:
                print("DEBUG: [CameraStream] Camera not initialized, reinitializing...")
                if not self._safe_init_picamera():
                    print("DEBUG: [CameraStream] Camera reinitialization failed")
                    return
                print("DEBUG: [CameraStream] Camera reinitialized for live mode")
            
            # Update preview config with current settings (exposure, etc.)
            self._update_preview_config()
            
            if not self.is_live:
                # Only start if not already running
                self._mutex.lock()
                try:
                    print("DEBUG: [CameraStream] Starting live preview")
                    if self.picam2 is None:
                        print("DEBUG: [CameraStream] picam2 is None, aborting start_live")
                        return
                        
                    # Configure camera with current settings
                    if not hasattr(self, 'preview_config') or not self.preview_config:
                        self.preview_config = self.picam2.create_preview_configuration()
                    
                    # Make sure preview config has proper controls
                    if "controls" not in self.preview_config:
                        self.preview_config["controls"] = {}
                    
                    # Set common controls for preview
                    self.preview_config["controls"]["ExposureTime"] = self.current_exposure
                    self.preview_config["controls"]["AeEnable"] = False  # Manual exposure
                    
                    # Configure and start the camera
                    self.picam2.configure(self.preview_config)
                    
                    # Start camera with job-dependent settings
                    if self.job_enabled:
                        self.picam2.start()
                    else:
                        # Use show_preview=False for headless operation without job
                        self.picam2.start(show_preview=False)
                    
                    # Start the timer for frame capture
                    self.timer.start(33)  # ~30 FPS update rate
                    
                    self.is_live = True
                    print("DEBUG: [CameraStream] Live preview started successfully")
                except Exception as e:
                    print(f"DEBUG: [CameraStream] Error starting live preview: {e}")
                    self.is_live = False
                finally:
                    self._mutex.unlock()
            else:
                print("DEBUG: [CameraStream] Camera already in live mode")
        except Exception as e:
            print(f"DEBUG: [CameraStream] Unhandled error in start_live: {e}")
    
    def stop_live(self):
        """Stop live camera preview"""
        self._mutex.lock()
        try:
            if self.is_live and self.picam2:
                print("DEBUG: [CameraStream] Stopping live preview")
                
                # Stop the timer first
                if self.timer and self.timer.isActive():
                    self.timer.stop()
                    
                # Then stop the camera
                if self.picam2 and self.picam2.started:
                    self.picam2.stop()
                    
                self.is_live = False
                print("DEBUG: [CameraStream] Live preview stopped")
                return True
            else:
                print("DEBUG: [CameraStream] Camera not in live mode, nothing to stop")
                return False
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error stopping live preview: {e}")
            return False
        finally:
            self._mutex.unlock()
            
    def _query_frame(self):
        """Query frame from camera - called by timer (with timeout protection)"""
        # Use tryLock with timeout to prevent blocking
        if not self._mutex.tryLock(5):  # 5ms timeout
            print("DEBUG: [CameraStream] Frame capture skipped - camera busy")
            return
            
        try:
            if not self.is_live:
                return
                
            # Check if camera is available and initialized
            if not self.picam2:
                # Camera was closed, skip frame
                return
                
            if not self.picam2.started:
                print("DEBUG: [CameraStream] Camera not started, skipping frame")
                return
            
            # Check job status before capture
            if not self.job_enabled:
                # Simple frame capture without job processing
                try:
                    frame = self.picam2.capture_array()
                    if frame is not None:
                        self.frame_ready.emit(frame)
                except Exception as e:
                    print(f"DEBUG: [CameraStream] Simple capture error: {e}")
                return
                
            # Full frame capture with job processing (if enabled)
            try:
                frame = self.picam2.capture_array()
                if frame is not None:
                    # Emit frame directly for better UI responsiveness
                    self.frame_ready.emit(frame)
            except Exception as e:
                print(f"DEBUG: [CameraStream] Full capture error: {e}")
                # Don't stop live mode on single frame error
        finally:
            self._mutex.unlock()

    def _process_frame(self, frame):
        """Process frame - currently just emits the frame"""
        # Placeholder for future frame processing logic
        # Keep simple for now to avoid UI lag
        self.frame_ready.emit(frame)

    def trigger_capture(self):
        """
        Trigger single photo capture
        
        NOTE: Trigger capture ALWAYS works regardless of job_enabled setting.
        - Job enabled: Full processing with potential longer capture time
        - Job disabled: Simple capture, faster but no advanced processing
        """
        try:
            print("DEBUG: [CameraStream] trigger_capture called")
            
            if not self.is_camera_available:
                print("DEBUG: [CameraStream] Camera not available")
                # Emit a test frame for testing without camera
                import numpy as np
                test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                self.frame_ready.emit(test_frame)
                return
                
            # Ensure camera is initialized
            if not hasattr(self, 'picam2') or self.picam2 is None:
                print("DEBUG: [CameraStream] Camera not initialized, reinitializing...")
                if not self._safe_init_picamera():
                    print("DEBUG: [CameraStream] Camera reinitialization failed")
                    return
                print("DEBUG: [CameraStream] Camera reinitialized for trigger capture")
                
            # Remember current state
            was_live = self.is_live
            print(f"DEBUG: [CameraStream] was_live: {was_live}")
            
            # Stop current capture if running
            if was_live or (self.picam2 and self.picam2.started):
                print("DEBUG: [CameraStream] Stopping current capture")
                if self.picam2:
                    self.picam2.stop()
            
            # Configure for still capture
            print("DEBUG: [CameraStream] Configuring for still capture")
            if not hasattr(self, 'still_config') or not self.still_config:
                # Create still config if not exists
                self.still_config = self.picam2.create_still_configuration()
                print("DEBUG: [CameraStream] Created still config")
            
            # Update still config with current exposure settings
            if "controls" not in self.still_config:
                self.still_config["controls"] = {}
                
            # Apply current exposure settings to still capture
            self.still_config["controls"]["ExposureTime"] = self.current_exposure
            self.still_config["controls"]["AeEnable"] = False  # Manual exposure
            
            # Set frame duration limits to accommodate exposure time
            min_frame_duration = max(100, self.current_exposure + 1000)  # At least exposure + 1ms
            self.still_config["controls"]["FrameDurationLimits"] = (min_frame_duration, 1000000000)
            
            # Handle noise reduction properly to avoid TDN error
            if not self.job_enabled:
                # Use minimal noise reduction instead of completely off
                self.still_config["controls"]["NoiseReductionMode"] = 3  # Minimal
            else:
                # Use high quality for full processing
                self.still_config["controls"]["NoiseReductionMode"] = 2  # HighQuality
            
            print(f"DEBUG: [CameraStream] Still config exposure: {self.current_exposure}μs")
            
            # Configure camera with error handling
            try:
                self.picam2.configure(self.still_config)
                print("DEBUG: [CameraStream] Still configuration successful")
            except Exception as config_error:
                print(f"DEBUG: [CameraStream] Still config failed: {config_error}")
                # Fallback to simpler configuration
                simple_config = self.picam2.create_still_configuration()
                simple_config["controls"] = {
                    "ExposureTime": self.current_exposure,
                    "AeEnable": False,
                    "NoiseReductionMode": 3  # Minimal to avoid TDN error
                }
                self.picam2.configure(simple_config)
                print("DEBUG: [CameraStream] Fallback configuration applied")
            
            # Start and capture
            print(f"DEBUG: [CameraStream] Starting still capture (Job: {'ON' if self.job_enabled else 'OFF'})")
            # Always start camera for trigger capture, but control preview based on job setting
            try:
                self.picam2.start(show_preview=False)  # Always use safe mode for trigger
                print("DEBUG: [CameraStream] Camera started successfully for still capture")
            except Exception as start_error:
                print(f"DEBUG: [CameraStream] Camera start failed: {start_error}")
                # Try to recover
                if "TDN" in str(start_error):
                    print("DEBUG: [CameraStream] TDN error detected, trying simpler config")
                    self.picam2.stop()
                    # Ultra-simple config to avoid TDN issues
                    ultra_simple = self.picam2.create_still_configuration()
                    ultra_simple["controls"] = {"ExposureTime": self.current_exposure, "AeEnable": False}
                    self.picam2.configure(ultra_simple)
                    self.picam2.start(show_preview=False)
                else:
                    raise start_error
            
            print("DEBUG: [CameraStream] Capturing frame")
            # Trigger capture ALWAYS works, but with different handling based on job setting
            try:
                frame = self.picam2.capture_array()
                if frame is None:
                    print("DEBUG: [CameraStream] No frame captured, retrying...")
                    # Retry once
                    frame = self.picam2.capture_array()
            except Exception as capture_error:
                print(f"DEBUG: [CameraStream] Capture error: {capture_error}")
                frame = None
            
            if frame is not None:
                print(f"DEBUG: [CameraStream] Frame captured: {frame.shape}")
                self.frame_ready.emit(frame)
            else:
                print("DEBUG: [CameraStream] No frame captured")
            
            # Stop still capture
            print("DEBUG: [CameraStream] Stopping still capture")
            if not self.job_enabled:
                # Force close to avoid job execution on stop
                self.picam2.close()
                # Reinitialize for next operation
                if not self._safe_init_picamera():
                    print("DEBUG: [CameraStream] Camera reinitialization failed after still capture")
                else:
                    print("DEBUG: [CameraStream] Camera reinitialized after still capture")
            else:
                self.picam2.stop()
            
            # Restore preview if was live
            if was_live:
                print("DEBUG: [CameraStream] Restoring live preview")
                if self.picam2:
                    self.picam2.configure(self.preview_config)
                    if self.job_enabled:
                        self.picam2.start()
                    else:
                        self.picam2.start(show_preview=False)
            else:
                print("DEBUG: [CameraStream] Not restoring live (was not live)")
                
            print("DEBUG: [CameraStream] trigger_capture completed successfully")
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error in trigger_capture: {e}")
            # Try to recover by reconfiguring preview
            try:
                if self.is_camera_available and hasattr(self, 'picam2') and self.picam2:
                    self.picam2.stop()
                    self.picam2.configure(self.preview_config)
                    if was_live:
                        self.picam2.start()
            except Exception as recovery_error:
                print(f"DEBUG: [CameraStream] Recovery failed: {recovery_error}")
                
    def trigger_capture_async(self, timeout_ms=5000):
        """
        Kích hoạt chụp ảnh không đồng bộ, trả về ngay lập tức và thông báo khi có kết quả
        
        Args:
            timeout_ms: Thời gian tối đa đợi cho việc trigger (ms)
            
        Returns:
            bool: True nếu trigger được bắt đầu, False nếu có lỗi
        """
        try:
            print("DEBUG: [CameraStream] trigger_capture_async called")
            
            if not self.is_camera_available:
                print("DEBUG: [CameraStream] Camera not available")
                # Emit a test frame for testing without camera sau 500ms
                import numpy as np
                test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                
                # Giả lập việc đợi frame bằng timer
                def emit_test_frame():
                    self.frame_ready.emit(test_frame)
                
                QTimer.singleShot(500, emit_test_frame)
                return True
            
            # Tạo thread mới để đợi trigger
            if hasattr(self, 'trigger_thread') and self.trigger_thread is not None:
                # Dừng thread cũ nếu đang chạy
                if self.trigger_thread.isRunning():
                    print("DEBUG: [CameraStream] Stopping existing trigger thread")
                    self.trigger_thread.stop()
                    self.trigger_thread.wait(1000)  # Đợi tối đa 1 giây
            
            self.trigger_thread = TriggerWaiterThread(self, timeout_ms)
            
            # Kết nối tín hiệu với các callback
            self.trigger_thread.trigger_completed.connect(self._on_trigger_completed)
            self.trigger_thread.trigger_timeout.connect(self._on_trigger_timeout)
            self.trigger_thread.trigger_error.connect(self._on_trigger_error)
            
            # Bắt đầu thread đợi
            self.trigger_thread.start()
            
            # Khởi tạo việc chụp hình trong thread riêng biệt
            capture_thread = threading.Thread(target=self._perform_async_capture)
            capture_thread.daemon = True  # Thread sẽ tự kết thúc khi chương trình đóng
            capture_thread.start()
            
            print("DEBUG: [CameraStream] Async trigger initiated")
            return True
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error starting async trigger: {e}")
            return False
            
    def _perform_async_capture(self):
        """Thực hiện việc chụp hình trong thread riêng biệt"""
        try:
            print("DEBUG: [CameraStream] Starting async capture in separate thread")
            
            # Lưu trạng thái live hiện tại
            was_live = self.is_live
            
            # Dừng camera trước nếu đang live
            if was_live or (self.picam2 and self.picam2.started):
                print("DEBUG: [CameraStream] Stopping current capture")
                if self.picam2:
                    self.picam2.stop()
            
            # Cấu hình cho still capture
            if not hasattr(self, 'still_config') or not self.still_config:
                self.still_config = self.picam2.create_still_configuration()
            
            # Cập nhật các cài đặt phơi sáng
            if "controls" not in self.still_config:
                self.still_config["controls"] = {}
                
            self.still_config["controls"]["ExposureTime"] = self.current_exposure
            self.still_config["controls"]["AeEnable"] = False  # Manual exposure
            
            # Cấu hình camera
            try:
                self.picam2.configure(self.still_config)
                self.picam2.start(show_preview=False)
            except Exception as config_error:
                print(f"DEBUG: [CameraStream] Config error: {config_error}")
                # Fallback to simpler config if needed
            
            # Thực hiện chụp
            try:
                frame = self.picam2.capture_array()
                if frame is None:
                    print("DEBUG: [CameraStream] No frame captured, retrying...")
                    frame = self.picam2.capture_array()
            except Exception as capture_error:
                print(f"DEBUG: [CameraStream] Capture error: {capture_error}")
                frame = None
            
            # Dừng camera sau khi chụp
            if self.picam2 and self.picam2.started:
                self.picam2.stop()
            
            # Khôi phục chế độ live nếu cần
            if was_live:
                try:
                    self.picam2.configure(self.preview_config)
                    self.picam2.start()
                except Exception as restore_error:
                    print(f"DEBUG: [CameraStream] Error restoring live mode: {restore_error}")
            
            # Thông báo frame cho thread đợi
            if frame is not None and hasattr(self, 'trigger_thread') and self.trigger_thread is not None:
                print(f"DEBUG: [CameraStream] Frame captured: {frame.shape}")
                self.trigger_thread.notify_frame_ready(frame)
            else:
                print("DEBUG: [CameraStream] No frame captured in async trigger")
                
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error in async capture thread: {e}")
    
    def _on_trigger_completed(self, frame):
        """Callback khi trigger hoàn thành"""
        print("DEBUG: [CameraStream] Async trigger completed")
        # Phát tín hiệu frame_ready để camera_view có thể hiển thị
        self.frame_ready.emit(frame)
    
    def _on_trigger_timeout(self):
        """Callback khi trigger timeout"""
        print("DEBUG: [CameraStream] Async trigger timeout")
        # Tạo một frame trống để hiển thị thông báo lỗi
        import numpy as np
        error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Bạn có thể thêm text "Timeout" vào frame này nếu cần
        self.frame_ready.emit(error_frame)
    
    def _on_trigger_error(self, error_msg):
        """Callback khi có lỗi trigger"""
        print(f"DEBUG: [CameraStream] Async trigger error: {error_msg}")
        # Tạo một frame trống để hiển thị thông báo lỗi
        import numpy as np
        error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Bạn có thể thêm text về lỗi vào frame này nếu cần
        self.frame_ready.emit(error_frame)

    def set_zoom(self, value):
        """Placeholder for zoom control.

        Currently unused by the codebase. Keep as a no-op placeholder for
        backwards compatibility. If Picamera2 supports a zoom control on the
        target device, this method can be implemented. Any calls are logged
        for observability.
        """
        logger.debug(f"CameraStream.set_zoom called with value={value} (placeholder no-op)")
        try:
            if self.picam2 and hasattr(self.picam2, 'set_controls'):
                # Best-effort attempt — many Picamera2 builds do not expose a 'Zoom'
                # control; wrap in try/except to avoid raising.
                self.picam2.set_controls({'Zoom': float(value)})
                logger.debug("CameraStream.set_zoom: attempted to apply Zoom control via picam2.set_controls")
        except Exception as e:
            logger.debug(f"CameraStream.set_zoom: not implemented on this camera backend: {e}")

    def set_focus(self, value):
        """Placeholder for focus control.

        Currently unused by the codebase. Kept as a no-op for compatibility.
        Logs calls so usage can be discovered during runtime.
        """
        logger.debug(f"CameraStream.set_focus called with value={value} (placeholder no-op)")
        try:
            if self.picam2 and hasattr(self.picam2, 'set_controls'):
                # Attempt to set a focus control if available on the backend
                self.picam2.set_controls({'Focus': float(value)})
                logger.debug("CameraStream.set_focus: attempted to apply Focus control via picam2.set_controls")
        except Exception as e:
            logger.debug(f"CameraStream.set_focus: not implemented on this camera backend: {e}")

    # --- Chuyển đổi giá trị giữa UI và camera ---
    def ui_to_exposure(self, value):
        """Convert UI exposure (ms) to camera exposure (μs).

        Args:
            value: Exposure value in milliseconds from UI.

        Returns:
            int: Exposure time in microseconds for camera.
        """
        # Ensure value is a float
        value = float(value)
        
        # Convert from ms to μs for camera (multiplied by 1000)
        return int(value * 1000)

    def exposure_to_ui(self, value):
        """Convert camera exposure (μs) to UI exposure (ms).

        Args:
            value: Exposure value in microseconds from camera.

        Returns:
            float: Exposure time in milliseconds for UI.
        """
        # Ensure value is a float
        value = float(value)
        
        # Convert from μs to ms for UI (divided by 1000)
        return value / 1000.0

    def set_exposure(self, value):
        # value từ UI là μs, camera cũng cần μs
        try:
            if not self.picam2:
                print("DEBUG: [CameraStream] Cannot set exposure - camera not available")
                # Still store the value for when camera becomes available
                self.current_exposure = int(value)
                return
                
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
            
    def get_exposure(self):
        """Get current exposure value in microseconds.

        Returns:
            int: Current exposure time in microseconds.
        """
        # Trả về μs cho UI
        try:
            if not self.picam2:
                return 10000  # Default when camera not available
            
            # Only try to get metadata if camera is started and in live mode
            if not self.picam2.started:
                return self.current_exposure  # Return stored value
                
            val = self.picam2.capture_metadata().get("ExposureTime", 0)
            return int(val)  # Đã là μs
        except Exception as e:
            print(f"DEBUG: [CameraStream] get_exposure error: {e}")
            return self.current_exposure  # Fallback to stored value

    def set_gain(self, value):
        try:
            if not self.picam2:
                print("DEBUG: [CameraStream] Cannot set gain - camera not available")
                return
            cam_value = self.ui_to_gain(value)
            self.picam2.set_controls({"AnalogueGain": cam_value})
        except Exception as e:
            print(f"[CameraStream] set_gain error: {e}")

    def set_ev(self, value):
        try:
            if not self.picam2:
                print("DEBUG: [CameraStream] Cannot set EV - camera not available")
                return
            cam_value = self.ui_to_ev(value)
            self.picam2.set_controls({"ExposureValue": cam_value})
        except Exception as e:
            print(f"[CameraStream] set_ev error: {e}")

    def set_auto_exposure(self, enable: bool):
        try:
            if not self.picam2:
                print("DEBUG: [CameraStream] Cannot set auto exposure - camera not available")
                return
            self.picam2.set_controls({"AeEnable": enable})
            print(f"DEBUG: [CameraStream] Set AeEnable to {enable}")
        except Exception as e:
            print(f"[CameraStream] set_auto_exposure error: {e}")

    def get_gain(self):
        try:
            if not self.picam2:
                return 1.0  # Default when camera not available
                
            # Only try to get metadata if camera is started and in live mode
            if not self.picam2.started:
                return 1.0  # Default value
                
            val = self.picam2.capture_metadata().get("AnalogueGain", 1.0)
            return self.gain_to_ui(val)
        except Exception as e:
            print(f"DEBUG: [CameraStream] get_gain error: {e}")
            return 1.0  # Default on error

    def get_ev(self):
        try:
            if not self.picam2:
                return 0.0  # Default when camera not available
                
            # Only try to get metadata if camera is started and in live mode
            if not self.picam2.started:
                return 0.0  # Default value
                
            val = self.picam2.capture_metadata().get("ExposureValue", 0.0)
            return self.ev_to_ui(val)
        except Exception as e:
            print(f"DEBUG: [CameraStream] get_ev error: {e}")
            return 0.0  # Default on error

    def is_auto_exposure(self):
        try:
            if not self.picam2:
                return False  # Default when camera not available
                
            # Only try to get metadata if camera is started and in live mode
            if not self.picam2.started:
                return False  # Default value
                
            return self.picam2.capture_metadata().get("AeEnable", False)
        except Exception as e:
            print(f"DEBUG: [CameraStream] is_auto_exposure error: {e}")
            return False  # Default on error

    # --- Conversion utilities ---
    def ui_to_gain(self, value):
        # Direct 1:1 mapping
        return float(value)
        
    def gain_to_ui(self, value):
        # Direct 1:1 mapping
        return float(value)
        
    def ui_to_ev(self, value):
        # Direct 1:1 mapping
        return float(value)
        
    def ev_to_ui(self, value):
        # Direct 1:1 mapping
        return float(value)

    def set_roi(self, x, y, width, height):
        """Set region of interest for camera.

        Args:
            x: X coordinate (normalized 0-1)
            y: Y coordinate (normalized 0-1)
            width: Width (normalized 0-1)
            height: Height (normalized 0-1)
        
        Returns:
            bool: Success status
        """
        if not self.is_camera_available or not self.picam2:
            return False
            
        try:
            # Convert normalized coordinates to actual camera sensor coordinates
            # This depends on the specific camera sensor size
            # For now, just log the request
            print(f"DEBUG: [CameraStream] ROI requested: {x}, {y}, {width}, {height}")
            
            # This would be implemented properly with camera-specific calculations
            return True
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error setting ROI: {e}")
            return False

    def reset_roi(self):
        """Reset region of interest to full frame."""
        if not self.is_camera_available or not self.picam2:
            return False
            
        try:
            # This would reset any ROI settings
            print("DEBUG: [CameraStream] ROI reset requested")
            return True
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error resetting ROI: {e}")
            return False

    def save_image(self, path, frame=None):
        """Save current image to file.

        Args:
            path: Path to save the image to.
            frame: Optional frame to save. If None, captures a new frame.
        
        Returns:
            bool: Success status
        """
        try:
            import cv2
            
            if frame is None:
                # Capture a new frame if none provided
                if not self.is_camera_available or not self.picam2:
                    print("DEBUG: [CameraStream] Camera not available for saving image")
                    return False
                
                # Use trigger_capture to get a high-quality still image
                was_live = self.is_live
                if was_live:
                    self.stop_live()
                    
                try:
                    # Configure for still capture
                    if not hasattr(self, 'still_config') or not self.still_config:
                        self.still_config = self.picam2.create_still_configuration()
                    
                    # Apply current settings
                    if "controls" not in self.still_config:
                        self.still_config["controls"] = {}
                    self.still_config["controls"]["ExposureTime"] = self.current_exposure
                    self.still_config["controls"]["AeEnable"] = False
                    
                    # Configure and capture
                    self.picam2.configure(self.still_config)
                    self.picam2.start(show_preview=False)
                    frame = self.picam2.capture_array()
                    self.picam2.stop()
                    
                    # Restore live if needed
                    if was_live:
                        self.start_live()
                finally:
                    # Always try to restore live mode
                    if was_live and not self.is_live:
                        self.start_live()
            
            if frame is not None:
                # Save the frame
                cv2.imwrite(path, frame)
                print(f"DEBUG: [CameraStream] Image saved to {path}")
                return True
            else:
                print("DEBUG: [CameraStream] No frame to save")
                return False
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error saving image: {e}")
            return False

    def get_camera_properties(self):
        """Get camera properties as dict."""
        props = {
            "is_camera_available": self.is_camera_available,
            "is_live": self.is_live,
            "current_exposure": self.current_exposure,
            "current_format": self.current_format,
            "job_enabled": self.job_enabled
        }
        
        # Add camera model info if available
        if self.is_camera_available and self.picam2:
            try:
                camera_properties = self.picam2.camera_properties
                if camera_properties:
                    model = camera_properties.get("Model", "Unknown")
                    props["camera_model"] = model
            except Exception as e:
                print(f"DEBUG: [CameraStream] Error getting camera model: {e}")
                props["camera_model"] = "Error reading model"
        
        return props
