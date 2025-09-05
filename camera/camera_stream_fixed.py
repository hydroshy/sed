"""
Camera stream module
Provides CameraStream class for interacting with camera hardware
"""

import os
import time
import traceback
from PyQt5.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QMessageBox
import numpy as np

# Try to import picamera2
try:
    from picamera2 import Picamera2
    has_picamera2 = True
    print("DEBUG: [CameraStream] Successfully imported picamera2")
except ImportError:
    has_picamera2 = False
    print("DEBUG: [CameraStream] Failed to import picamera2, will use stub implementation")

class CameraStream(QObject):
    """Camera stream handler using picamera2"""
    
    # Signal definitions
    frame_ready = pyqtSignal(object)  # Emits numpy array when new frame is ready
    camera_error = pyqtSignal(str)    # Emits error message when camera error occurs
    
    def __init__(self, parent=None):
        """Initialize camera stream"""
        super().__init__(parent)
        
        self.is_camera_available = has_picamera2
        self.current_exposure = 5000  # Default 5ms exposure
        self.job_enabled = False
        self.external_trigger_enabled = False
        self._last_sensor_ts = 0
        self._trigger_waiting = False
        
        if not has_picamera2:
            print("DEBUG: [CameraStream] picamera2 not available, using stub implementation")
            self.picam2 = None
            # Set up a timer to generate test frames
            self.timer = QTimer()
            self.timer.timeout.connect(self._generate_test_frame)
            self.is_live = False
            return
            
        # Initialize the camera
        self._safe_init_picamera()
        
        # Set up a timer for processing frames
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_frame)
        self.is_live = False
        
        # Default configurations
        self.preview_config = None
        self.still_config = None
        
        # Fix preview size if needed
        self._fix_preview_size()
        
        # Add missing methods if needed
        self._add_missing_methods()
    
    def _safe_init_picamera(self):
        """Safe initialization of picamera2 with error handling"""
        if not has_picamera2:
            return False
            
        try:
            self.picam2 = Picamera2()
            print("DEBUG: [CameraStream] picamera2 initialized successfully")
            
            # Create default configurations
            self.preview_config = self.picam2.create_preview_configuration()
            self.still_config = self.picam2.create_still_configuration()
            
            # Add exposure controls
            if "controls" not in self.preview_config:
                self.preview_config["controls"] = {}
            self.preview_config["controls"]["ExposureTime"] = self.current_exposure
            self.preview_config["controls"]["AeEnable"] = False  # Manual exposure
            
            # Configure with preview config by default
            self.picam2.configure(self.preview_config)
            
            # Initialize is successful
            self.is_camera_available = True
            return True
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error initializing camera: {e}")
            self.is_camera_available = False
            self.picam2 = None
            self.camera_error.emit(f"Camera initialization failed: {str(e)}")
            return False
    
    def _fix_preview_size(self):
        """Fix preview size for some camera modules"""
        if not hasattr(self, 'picam2') or not self.picam2:
            return
            
        try:
            # Get camera info
            camera_info = self.picam2.camera_properties
            
            # Check if we need to fix the size
            if "model" in camera_info and "imx" in camera_info["model"].lower():
                print(f"DEBUG: [CameraStream] Detected IMX camera: {camera_info['model']}")
                
                # Set specific size for IMX cameras if needed
                if "size" not in self.preview_config["main"]:
                    self.preview_config["main"]["size"] = (1280, 720)
                    print("DEBUG: [CameraStream] Fixed preview size to 1280x720 for IMX camera")
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Warning in fix_preview_size: {e}")
    
    def _add_missing_methods(self):
        """Add missing methods to support older versions of library"""
        # Ensure all required methods exist
        if not hasattr(CameraStream, 'start_live'):
            print("DEBUG: [CameraStream] Adding start_live method to class")
            CameraStream.start_live = self._fallback_start_live
            
        if not hasattr(CameraStream, 'start_live_camera'):
            print("DEBUG: [CameraStream] Adding start_live_camera method to class")
            CameraStream.start_live_camera = self._fallback_start_live_camera

    def _fallback_start_live(self):
        """Fallback implementation of start_live for CameraManager compatibility"""
        print("DEBUG: [CameraStream] Fallback start_live called")
        try:
            if not self.is_camera_available:
                print("DEBUG: [CameraStream] Camera not available in fallback start_live")
                return False
                
            # Ensure camera is initialized
            if self.picam2 is None:
                print("DEBUG: [CameraStream] Reinitializing camera in fallback start_live")
                if not self._safe_init_picamera():
                    return False
                    
            # Start the camera
            if self.picam2 and not self.picam2.started:
                print("DEBUG: [CameraStream] Starting camera in fallback start_live")
                self.picam2.start()
                
            # Start the timer
            if hasattr(self, 'timer') and not self.timer.isActive():
                print("DEBUG: [CameraStream] Starting timer in fallback start_live")
                self.timer.start(100)  # 10 FPS
                
            self.is_live = True
            return True
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error in fallback start_live: {e}")
            self.camera_error.emit(f"Failed to start camera: {str(e)}")
            return False
    
    def _fallback_start_live_camera(self):
        """Fallback implementation of start_live_camera for older versions"""
        print("DEBUG: [CameraStream] Fallback start_live_camera called")
        return self._fallback_start_live()
        
    def _generate_test_frame(self):
        """Generate a test frame for testing without a real camera"""
        # Create a gradient test pattern
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :, 0] = np.linspace(0, 255, 640, dtype=np.uint8)
        frame[:, :, 1] = np.linspace(0, 255, 480, dtype=np.uint8)[:, np.newaxis]
        frame[:, :, 2] = np.full((480, 640), int(time.time() % 255), dtype=np.uint8)
        
        # Emit the test frame
        self.frame_ready.emit(frame)
    
    def set_trigger_mode(self, enabled):
        """Enable/disable external hardware trigger and reconfigure Picamera2.

        - Sets IMX296 sysfs trigger parameter (requires privileges).
        - Configures Picamera2 to external trigger (video pipeline) and uses non-blocking polling.
        - Arms once; does not reconfigure per trigger.
        """
        success_hw = True
        try:
            value = "1" if enabled else "0"
            cmd = f"echo {value} | sudo tee /sys/module/imx296/parameters/trigger_mode"
            print(f"DEBUG: [CameraStream] Setting IMX296 trigger_mode={value}")
            import subprocess
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"DEBUG: [CameraStream] Failed to set IMX296 trigger_mode: {result.stderr}")
                success_hw = False
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error writing IMX296 trigger sysfs: {e}")
            success_hw = False

        self.external_trigger_enabled = bool(enabled)
        self._last_sensor_ts = 0
        if not self.picam2:
            return success_hw

        was_live = bool(getattr(self, 'is_live', False))
        if was_live and hasattr(self, 'stop_live'):
            try:
                self.stop_live()
            except Exception:
                pass

        return success_hw
        
    def process_frame(self):
        """Process a new frame from the camera"""
        if not self.is_camera_available or not hasattr(self, 'picam2') or self.picam2 is None:
            return
            
        try:
            # Get the latest frame
            frame = self.picam2.capture_array()
            
            # Check if the frame is valid
            if frame is None or frame.size == 0:
                print("DEBUG: [CameraStream] Empty frame received")
                return
                
            # Emit the frame
            self.frame_ready.emit(frame)
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error in process_frame: {e}")
            # Only emit error if it seems serious
            if "timeout" not in str(e).lower() and "closed" not in str(e).lower():
                self.camera_error.emit(f"Frame processing error: {str(e)}")
    
    def start_live(self):
        """Start live view from camera"""
        print("DEBUG: [CameraStream] start_live called")
        
        if not self.is_camera_available:
            print("DEBUG: [CameraStream] Camera not available")
            return False
            
        try:
            # Make sure hardware trigger is off
            if hasattr(self, 'external_trigger_enabled') and self.external_trigger_enabled:
                print("DEBUG: [CameraStream] Disabling hardware trigger")
                self.set_trigger_mode(False)
            
            # Ensure camera is initialized
            if not hasattr(self, 'picam2') or self.picam2 is None:
                print("DEBUG: [CameraStream] Reinitializing camera")
                if not self._safe_init_picamera():
                    print("DEBUG: [CameraStream] Failed to initialize camera")
                    return False
            
            # If camera is already started, stop it first
            if hasattr(self, 'picam2') and self.picam2 and self.picam2.started:
                print("DEBUG: [CameraStream] Camera already started, stopping first")
                self.picam2.stop()
            
            # Configure for preview
            self.picam2.configure(self.preview_config)
            print("DEBUG: [CameraStream] Camera configured for preview")
            
            # Start the camera
            print(f"DEBUG: [CameraStream] Starting camera in live mode (Job: {'ON' if self.job_enabled else 'OFF'})")
            if self.job_enabled:
                self.picam2.start()
            else:
                self.picam2.start(show_preview=False)
            
            # Start the timer for frame processing
            if hasattr(self, 'timer') and not self.timer.isActive():
                self.timer.start(100)  # 10 FPS
            
            self.is_live = True
            print("DEBUG: [CameraStream] Live view started successfully")
            
            return True
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error starting live view: {e}")
            self.camera_error.emit(f"Failed to start camera: {str(e)}")
            self.is_live = False
            return False
    
    def stop_live(self):
        """Stop live view"""
        print("DEBUG: [CameraStream] stop_live called")
        
        try:
            # Stop the timer
            if hasattr(self, 'timer') and self.timer.isActive():
                self.timer.stop()
            
            # Stop the camera if it's running
            if self.is_camera_available and hasattr(self, 'picam2') and self.picam2 and self.picam2.started:
                print("DEBUG: [CameraStream] Stopping camera")
                self.picam2.stop()
            
            self.is_live = False
            print("DEBUG: [CameraStream] Live view stopped")
            
            return True
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error stopping live view: {e}")
            self.is_live = False
            return False
    
    def set_exposure(self, exposure_us):
        """Set camera exposure in microseconds
        
        Args:
            exposure_us: Exposure time in microseconds
        """
        print(f"DEBUG: [CameraStream] Setting exposure to {exposure_us}μs")
        
        # Store the exposure value
        self.current_exposure = int(exposure_us)
        
        if not self.is_camera_available or not hasattr(self, 'picam2') or self.picam2 is None:
            print("DEBUG: [CameraStream] Camera not available for exposure setting")
            return False
            
        try:
            # Apply to current configuration
            controls = {}
            controls["ExposureTime"] = self.current_exposure
            controls["AeEnable"] = False  # Manual exposure
            
            # Apply directly if camera is running
            if self.picam2.started:
                print(f"DEBUG: [CameraStream] Applying exposure {self.current_exposure}μs to running camera")
                self.picam2.set_controls(controls)
            
            # Update saved configurations for future use
            if hasattr(self, 'preview_config') and self.preview_config:
                if "controls" not in self.preview_config:
                    self.preview_config["controls"] = {}
                self.preview_config["controls"]["ExposureTime"] = self.current_exposure
                self.preview_config["controls"]["AeEnable"] = False
            
            if hasattr(self, 'still_config') and self.still_config:
                if "controls" not in self.still_config:
                    self.still_config["controls"] = {}
                self.still_config["controls"]["ExposureTime"] = self.current_exposure
                self.still_config["controls"]["AeEnable"] = False
            
            print(f"DEBUG: [CameraStream] Exposure set to {self.current_exposure}μs")
            return True
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error setting exposure: {e}")
            self.camera_error.emit(f"Failed to set exposure: {str(e)}")
            return False
    
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
        Trigger capture asynchronously and wait for the result
        
        This method starts a capture in a separate thread to avoid blocking the UI
        
        Args:
            timeout_ms: Maximum time to wait for capture (ms)
            
        Returns:
            True if capture was triggered, False otherwise
        """
        try:
            print("DEBUG: [CameraStream] trigger_capture_async called")
            
            if not self.is_camera_available:
                print("DEBUG: [CameraStream] Camera not available for async capture")
                # Emit a test frame
                import numpy as np
                test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                self.frame_ready.emit(test_frame)
                return False
                
            # Use a worker thread for capture
            self.capture_thread = QThread()
            self.capture_worker = CaptureWorker(self, timeout_ms)
            self.capture_worker.moveToThread(self.capture_thread)
            
            # Connect signals
            self.capture_thread.started.connect(self.capture_worker.run)
            self.capture_worker.finished.connect(self.capture_thread.quit)
            self.capture_worker.finished.connect(self.capture_worker.deleteLater)
            self.capture_thread.finished.connect(self.capture_thread.deleteLater)
            
            # Start capture thread
            self.capture_thread.start()
            return True
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error in trigger_capture_async: {e}")
            return False
    
    def toggle_job_processing(self, enabled):
        """Toggle full job processing mode
        
        In job mode, the camera is configured for optimal image quality
        for detection and processing, but may have slightly lower frame rate.
        When job processing is disabled, the camera is optimized for
        frame rate and responsiveness.
        
        Args:
            enabled: Boolean, True to enable job processing
        """
        print(f"DEBUG: [CameraStream] Setting job processing: {enabled}")
        
        # Store the setting
        self.job_enabled = bool(enabled)
        
        # If live view is active, restart it with new settings
        was_live = self.is_live
        if was_live:
            self.stop_live()
            self.start_live()
        
        return True


# Add set_trigger_mode method if it doesn't exist
if not hasattr(CameraStream, 'set_trigger_mode'):
    print("DEBUG: [CameraStream] Adding set_trigger_mode method to class")
    def _set_trigger_mode(self, enabled):
        """
        Set external hardware trigger mode
        
        In trigger mode, the camera waits for an external trigger signal
        before capturing an image. This is used for synchronized captures.
        
        Args:
            enabled: Boolean, True to enable trigger mode
        """
        try:
            print(f"DEBUG: [CameraStream] set_trigger_mode({enabled}) called")
            
            # Write to sysfs trigger_mode parameter if it exists
            sysfs_path = "/sys/module/imx296/parameters/trigger_mode"
            if os.path.exists(sysfs_path):
                try:
                    with open(sysfs_path, 'w') as f:
                        f.write("1" if enabled else "0")
                    print(f"DEBUG: [CameraStream] Set IMX296 trigger_mode={1 if enabled else 0}")
                except Exception as e:
                    # Don't fail if sysfs write fails, it might need sudo
                    print(f"DEBUG: [CameraStream] Failed to write to {sysfs_path}: {e}")
                    print("DEBUG: [CameraStream] Try using: sudo chmod 666 /sys/module/imx296/parameters/trigger_mode")
            else:
                # Try using subprocess with sudo for setting trigger mode
                try:
                    import subprocess
                    value = "1" if enabled else "0"
                    cmd = f"echo {value} | sudo tee {sysfs_path}"
                    print(f"DEBUG: [CameraStream] Running: {cmd}")
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if result.returncode == 0:
                        print(f"DEBUG: [CameraStream] Successfully set trigger_mode via sudo")
                    else:
                        print(f"DEBUG: [CameraStream] Failed to set trigger_mode via sudo: {result.stderr}")
                except Exception as e:
                    print(f"DEBUG: [CameraStream] Error using sudo for trigger_mode: {e}")
            
            # Update our internal state
            self.external_trigger_enabled = bool(enabled)
            
            # If the camera is running, may need to reconfigure
            if hasattr(self, 'picam2') and self.picam2 and self.picam2.started:
                print("DEBUG: [CameraStream] Camera is running, updating configuration for trigger mode")
                
                # Different behavior depending on trigger mode
                if enabled:
                    # No need to do anything special here, external trigger will be handled by wait_for_frame_with_timeout
                    pass
                else:
                    # When disabling trigger mode, restart camera in normal mode
                    was_live = self.is_live
                    if was_live:
                        print("DEBUG: [CameraStream] Restarting camera in normal mode")
                        self.stop_live()
                        self.start_live()
            
            return True
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error in set_trigger_mode: {e}")
            return False
    
    CameraStream.set_trigger_mode = _set_trigger_mode

# Add trigger_capture method if it doesn't exist
if not hasattr(CameraStream, 'trigger_capture'):
    print("DEBUG: [CameraStream] Adding trigger_capture method to class")
    def _trigger_capture(self):
        """
        Trigger single photo capture
        
        NOTE: Trigger capture ALWAYS works regardless of job_enabled setting.
        - Job enabled: Full processing with potential longer capture time
        - Job disabled: Simple capture, faster but no advanced processing
        """
        try:
            print("DEBUG: [CameraStream] trigger_capture called")
            
            # Check for hardware trigger and use appropriate method
            if hasattr(self, 'external_trigger_enabled') and self.external_trigger_enabled:
                print("DEBUG: [CameraStream] Using hardware trigger method")
                frame = self.wait_for_frame_with_timeout(timeout_ms=5000)
                if frame is not None:
                    self.frame_ready.emit(frame)
                    print("DEBUG: [CameraStream] Frame captured via hardware trigger")
                    return
                else:
                    print("DEBUG: [CameraStream] Hardware trigger timed out, falling back to software trigger")
            
            # Continue with normal trigger capture
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
            except Exception:
                pass
    
    CameraStream.trigger_capture = _trigger_capture

# Add wait_for_frame_with_timeout method if it doesn't exist
if not hasattr(CameraStream, 'wait_for_frame_with_timeout'):
    print("DEBUG: [CameraStream] Adding wait_for_frame_with_timeout method to class")
    def _wait_for_frame_with_timeout(self, timeout_ms=5000):
        """
        Đợi frame mới từ camera với timeout
        
        Args:
            timeout_ms: Thời gian tối đa đợi frame mới (ms)
            
        Returns:
            np.ndarray: Frame mới hoặc None nếu timeout
        """
        try:
            print(f"DEBUG: [CameraStream] Waiting for new frame with timeout {timeout_ms}ms")
            
            if not self.is_camera_available or not self.picam2:
                print("DEBUG: [CameraStream] Camera not available for waiting frame")
                return None
                
            # Lưu timestamp trước khi đợi
            last_ts = getattr(self, '_last_sensor_ts', 0)
            start_time = time.time()
            
            # Cố gắng đợi frame mới
            while (time.time() - start_time) * 1000 < timeout_ms:
                try:
                    # Thử capture_request với wait=False để kiểm tra frame mới
                    req = self.picam2.capture_request(wait=False)
                    if not req:
                        # Không có frame mới, đợi một chút
                        time.sleep(0.1)
                        continue
                        
                    # Kiểm tra timestamp để xác định frame mới
                    try:
                        md = req.get_metadata()
                        ts = md.get('SensorTimestamp', 0) if isinstance(md, dict) else 0
                        
                        if ts and ts != last_ts:
                            # Đã nhận được frame mới
                            frame = req.make_array('main') if hasattr(req, 'make_array') else None
                            req.release()
                            
                            if frame is not None:
                                print(f"DEBUG: [CameraStream] Got new frame: {frame.shape}, ts: {ts}")
                                # Cập nhật timestamp mới nhất
                                self._last_sensor_ts = ts
                                return frame
                    except Exception as e:
                        print(f"DEBUG: [CameraStream] Error processing request: {e}")
                    finally:
                        try:
                            req.release()
                        except Exception:
                            pass
                        
                except Exception as e:
                    print(f"DEBUG: [CameraStream] Error in capture_request: {e}")
                    time.sleep(0.1)
            
            # Timeout - không có frame mới
            print(f"DEBUG: [CameraStream] Timeout waiting for new frame after {timeout_ms}ms")
            return None
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error in wait_for_frame_with_timeout: {e}")
            return None
    
    # Add the method to the class
    CameraStream.wait_for_frame_with_timeout = _wait_for_frame_with_timeout

# Helper classes
class CaptureWorker(QObject):
    """Worker for asynchronous capture"""
    
    finished = pyqtSignal()
    
    def __init__(self, camera_stream, timeout_ms):
        super().__init__()
        self.camera_stream = camera_stream
        self.timeout_ms = timeout_ms
    
    def run(self):
        """Run the capture worker"""
        try:
            # Trigger capture
            self.camera_stream.trigger_capture()
        except Exception as e:
            print(f"DEBUG: [CaptureWorker] Error: {e}")
        finally:
            # Signal that we're done
            self.finished.emit()
