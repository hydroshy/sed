"""
This module serves as a central location for applying all necessary
monkey patches to the CameraStream class.

Import this module after camera.camera_stream is imported to ensure
all required methods are available.
"""

def apply_all_patches():
    """Apply all patches to CameraStream class"""
    from camera.camera_stream import CameraStream
    
    # Add necessary import
    from PyQt5.QtCore import QTimer
    import numpy as np
    import os
    import logging
    import subprocess
    
    # Apply all patches
    print("DEBUG: Applying all CameraStream patches")
    
    # 1. Patch for start_live method
    if not hasattr(CameraStream, 'start_live'):
        print("DEBUG: Patching start_live method")
        def _start_live(self):
            """Start live camera preview - dynamically added method"""
            print("DEBUG: [CameraStream] Dynamically added start_live called")
            try:
                if not self.is_camera_available:
                    print("DEBUG: [CameraStream] Camera not available for live mode")
                    return False
                    
                if hasattr(self, 'is_live') and self.is_live:
                    print("DEBUG: [CameraStream] Already in live mode")
                    return True
                
                # Ensure camera is initialized
                if self.picam2 is None:
                    print("DEBUG: [CameraStream] Reinitializing camera...")
                    if not self._safe_init_picamera():
                        print("DEBUG: [CameraStream] Camera reinitialization failed")
                        return False
                    print("DEBUG: [CameraStream] Camera reinitialized successfully")
                    
                print("DEBUG: [CameraStream] Starting live preview...")
                
                # Update config with current settings
                if hasattr(self, '_update_preview_config'):
                    self._update_preview_config()
                
                # Stop camera if running
                if self.picam2 and hasattr(self.picam2, 'started') and self.picam2.started:
                    print("DEBUG: [CameraStream] Stopping camera before reconfigure")
                    self.picam2.stop()
                
                # Configure and start
                if hasattr(self, 'preview_config'):
                    print("DEBUG: [CameraStream] Configuring camera for preview")
                    self.picam2.configure(self.preview_config)
                
                print("DEBUG: [CameraStream] Starting camera")
                # Start camera based on job enabled state
                if hasattr(self, 'job_enabled') and self.job_enabled:
                    print("DEBUG: [CameraStream] Job enabled - starting camera normally")
                    self.picam2.start()
                else:
                    print("DEBUG: [CameraStream] Job disabled - starting camera in safe mode")
                    try:
                        self.picam2.start(show_preview=False)  # Start without preview to avoid job execution
                    except TypeError:
                        # If show_preview is not supported, just start normally
                        self.picam2.start()
                
                print("DEBUG: [CameraStream] Starting timer for frame capture")
                if hasattr(self, 'timer'):
                    self.timer.start(100)  # 10 FPS
                
                self.is_live = True
                print("DEBUG: [CameraStream] Live mode started successfully")
                return True
                
            except Exception as e:
                print(f"DEBUG: [CameraStream] Error starting live mode: {e}")
                self.is_live = False
                # Try to stop timer and camera to avoid hanging state
                try:
                    if hasattr(self, 'timer') and self.timer.isActive():
                        self.timer.stop()
                    if self.picam2 and hasattr(self.picam2, 'started') and self.picam2.started:
                        self.picam2.stop()
                except:
                    pass
                return False
        
        # Add the method to the class
        CameraStream.start_live = _start_live
        
        # Also add start_live_camera as an alias
        if not hasattr(CameraStream, 'start_live_camera'):
            CameraStream.start_live_camera = _start_live
    
    # 2. Patch for trigger_capture method
    if not hasattr(CameraStream, 'trigger_capture'):
        print("DEBUG: Patching trigger_capture method")
        def _trigger_capture(self):
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
        
        # Add the method to the class
        CameraStream.trigger_capture = _trigger_capture
    
    # Add other patches as needed
    
    print("DEBUG: All CameraStream patches applied successfully")
