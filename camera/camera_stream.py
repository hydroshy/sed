import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread, QMutex, QMutexLocker
from picamera2 import Picamera2
import threading
import time
import logging

# Import performance monitoring
try:
    from utils.performance_monitor import profile_operation, record_frame, record_frame_drop
    PERFORMANCE_MONITORING = True
except ImportError:
    PERFORMANCE_MONITORING = False
    logging.warning("Performance monitoring not available")

class CameraStream(QObject):
    frame_ready = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.is_camera_available = False
        self.picam2 = None
        self._mutex = QMutex()  # For thread safety
        self.job_enabled = False  # Mặc định DISABLE job execution để tránh camera bị đóng băng
        
        try:
            self.picam2 = Picamera2()
            self.is_camera_available = True
            print("DEBUG: [CameraStream] Camera initialized successfully")
            print("DEBUG: [CameraStream] Job execution is DISABLED by default (camera will still work, but without job processing)")
            print("DEBUG: [CameraStream] Use job toggle button to enable full processing if needed")
        except Exception as e:
            print(f"DEBUG: [CameraStream] Camera initialization failed: {e}")
            self.is_camera_available = False
            
        self.timer = QTimer()
        self.timer.timeout.connect(self._query_frame)
        self.is_live = False
        
        # Initialize exposure tracking
        self.current_exposure = 10000  # Default 10ms in μs
        
        # Only configure if camera is available
        if self.is_camera_available and self.picam2:
            try:
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
                
                # Configure the camera with preview config
                self.picam2.configure(self.preview_config)
                print("DEBUG: [CameraStream] Camera configured successfully")
            except Exception as e:
                print(f"DEBUG: [CameraStream] Camera configuration failed: {e}")
                self.is_camera_available = False
        else:
            print("DEBUG: [CameraStream] Camera not available, skipping configuration")

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
                return False
                
            if self.is_live:
                print("DEBUG: [CameraStream] Already in live mode")
                return True
            
            # Ensure camera is initialized
            if self.picam2 is None:
                print("DEBUG: [CameraStream] Reinitializing camera...")
                try:
                    from picamera2 import Picamera2
                    self.picam2 = Picamera2()
                    print("DEBUG: [CameraStream] Camera reinitialized successfully")
                except Exception as e:
                    print(f"DEBUG: [CameraStream] Camera reinit failed: {e}")
                    self.is_camera_available = False
                    return False
                
            print("DEBUG: [CameraStream] Starting live preview...")
            
            # Update config with current settings
            self._update_preview_config()
            
            # Stop camera if running
            if self.picam2 and self.picam2.started:
                print("DEBUG: [CameraStream] Stopping camera before reconfigure")
                self.picam2.stop()
            
            # Configure and start
            print("DEBUG: [CameraStream] Configuring camera for preview")
            self.picam2.configure(self.preview_config)
            
            print("DEBUG: [CameraStream] Starting camera")
            # Chỉ start camera nếu job được enable, hoặc force start
            if self.job_enabled:
                print("DEBUG: [CameraStream] Job enabled - starting camera normally")
                self.picam2.start()
            else:
                print("DEBUG: [CameraStream] Job disabled - starting camera in safe mode")
                self.picam2.start(show_preview=False)  # Start without preview to avoid job execution
            
            print("DEBUG: [CameraStream] Starting timer for frame capture")
            self.timer.start(100)  # 10 FPS thay vì 30 FPS để giảm load
            
            self.is_live = True
            print(f"DEBUG: [CameraStream] Live mode started successfully (Job: {'ON' if self.job_enabled else 'OFF'})")
            return True
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error starting live mode: {e}")
            self.is_live = False
            # Try to stop timer and camera to avoid hanging state
            try:
                if self.timer.isActive():
                    self.timer.stop()
                if self.picam2 and self.picam2.started:
                    self.picam2.stop()
            except:
                pass
            return False

    def stop_live(self):
        """Stop live camera preview with proper cleanup"""
        print("DEBUG: [CameraStream] stop_live called")
        
        # Use mutex to ensure thread-safe stop
        self._mutex.lock()
        try:
            # Set flag first to stop timer callbacks
            self.is_live = False
            
            # Stop timer
            if self.timer.isActive():
                print("DEBUG: [CameraStream] Stopping timer")
                self.timer.stop()
            
            # Stop camera with different method based on job status
            if self.picam2 and self.picam2.started:
                print("DEBUG: [CameraStream] Stopping camera")
                if not self.job_enabled:
                    # If job disabled, force close to avoid job execution
                    print("DEBUG: [CameraStream] Job disabled - force closing camera")
                    try:
                        # Try to close without waiting for jobs
                        self.picam2.close()
                        # Don't reinitialize immediately - let it be lazy loaded next time
                        self.picam2 = None
                        print("DEBUG: [CameraStream] Camera closed and reset")
                    except Exception as e:
                        print(f"DEBUG: [CameraStream] Error during force close: {e}")
                        # Try normal stop as fallback
                        try:
                            if self.picam2:
                                self.picam2.stop()
                        except:
                            pass
                        self.picam2 = None
                else:
                    # Normal stop if job enabled
                    self.picam2.stop()
            
            print("DEBUG: [CameraStream] Live mode stopped successfully")
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error stopping live mode: {e}")
            # Force cleanup
            self.is_live = False
            try:
                if self.timer.isActive():
                    self.timer.stop()
            except:
                pass
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
                    frame_start_time = time.perf_counter() if PERFORMANCE_MONITORING else None
                    
                    if PERFORMANCE_MONITORING:
                        with profile_operation("camera_simple_capture"):
                            frame = self.picam2.capture_array()
                        
                        # Record frame timing
                        processing_time = (time.perf_counter() - frame_start_time) * 1000  # ms
                        record_frame(processing_time)
                    else:
                        frame = self.picam2.capture_array()
                    
                    if frame is not None:
                        self.frame_ready.emit(frame)
                except Exception as e:
                    print(f"DEBUG: [CameraStream] Simple capture error: {e}")
                    if PERFORMANCE_MONITORING:
                        record_frame_drop()
                return
                
            # Full frame capture with job processing (if enabled)
            try:
                frame_start_time = time.perf_counter() if PERFORMANCE_MONITORING else None
                
                if PERFORMANCE_MONITORING:
                    with profile_operation("camera_frame_capture_with_jobs"):
                        frame = self.picam2.capture_array()
                    
                    # Record frame timing
                    processing_time = (time.perf_counter() - frame_start_time) * 1000  # ms
                    record_frame(processing_time)
                else:
                    frame = self.picam2.capture_array()
                
                if frame is not None:
                    # Emit frame directly for better UI responsiveness
                    self.frame_ready.emit(frame)
            except Exception as e:
                print(f"DEBUG: [CameraStream] Full capture error: {e}")
                if PERFORMANCE_MONITORING:
                    record_frame_drop()
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
                try:
                    from picamera2 import Picamera2
                    self.picam2 = Picamera2()
                    print("DEBUG: [CameraStream] Camera reinitialized for trigger capture")
                except Exception as e:
                    print(f"DEBUG: [CameraStream] Camera reinit failed: {e}")
                    return
                
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
                try:
                    from picamera2 import Picamera2
                    self.picam2 = Picamera2()
                    print("DEBUG: [CameraStream] Camera reinitialized after still capture")
                except Exception as e:
                    print(f"DEBUG: [CameraStream] Reinit after still failed: {e}")
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
            self.picam2.set_controls({"AeEnable": bool(enable)})
        except Exception as e:
            print(f"[CameraStream] set_auto_exposure error: {e}")

    def get_exposure(self):
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
            return self.current_exposure  # Return stored value on error

    def get_gain(self):
        try:
            if not self.picam2:
                return 1.0  # Default when camera not available
                
            # Only try to get metadata if camera is started and in live mode
            if not self.picam2.started:
                return 1.0  # Return default value
                
            val = self.picam2.capture_metadata().get("AnalogueGain", 1.0)
            return self.gain_to_ui(val)
        except Exception as e:
            print(f"DEBUG: [CameraStream] get_gain error: {e}")
            return 1.0

    def get_ev(self):
        try:
            if not self.picam2:
                return 0  # Default when camera not available
                
            # Only try to get metadata if camera is started and in live mode
            if not self.picam2.started:
                return 0  # Return default value
                
            val = self.picam2.capture_metadata().get("ExposureValue", 0.0)
            return self.ev_to_ui(val)
        except Exception as e:
            print(f"DEBUG: [CameraStream] get_ev error: {e}")
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

    def cleanup(self):
        """Cleanup camera resources"""
        print("DEBUG: [CameraStream] Cleanup called")
        try:
            # Stop live mode first
            if self.is_live:
                self.stop_live()
                
            # Force close camera if still running
            if self.picam2:
                try:
                    if hasattr(self.picam2, 'started') and self.picam2.started:
                        print("DEBUG: [CameraStream] Force closing camera")
                        self.picam2.close()
                except Exception as e:
                    print(f"DEBUG: [CameraStream] Error closing camera: {e}")
                finally:
                    self.picam2 = None
                    
            print("DEBUG: [CameraStream] Cleanup completed")
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Cleanup error: {e}")
