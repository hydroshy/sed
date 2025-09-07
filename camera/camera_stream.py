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

def _ensure_xdg_runtime_dir():
    """Ensure XDG_RUNTIME_DIR is set with correct permissions (for Pi/Qt)."""
    try:
        xdg = os.environ.get("XDG_RUNTIME_DIR")
        if not xdg:
            # Fallback safe path
            uid = os.getuid() if hasattr(os, "getuid") else 1000
            xdg = f"/tmp/xdg-runtime-{uid}"
            os.makedirs(xdg, exist_ok=True)
            try:
                os.chmod(xdg, 0o700)
            except Exception:
                pass
            os.environ["XDG_RUNTIME_DIR"] = xdg
    except Exception:
        # Best-effort only
        pass


class _LiveWorker(QObject):
    """Background worker to pull frames at target FPS using existing picam2."""
    frame_ready = pyqtSignal(object)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, camera_stream, target_fps=10.0):
        super().__init__()
        self._running = False
        self._stream = camera_stream
        try:
            self._target_fps = float(target_fps)
        except Exception:
            self._target_fps = 10.0

    @pyqtSlot()
    def run(self):
        self._running = True
        try:
            period = 1.0 / max(1.0, self._target_fps)
        except Exception:
            period = 0.1
        next_t = time.monotonic()
        while self._running:
            try:
                picam2 = getattr(self._stream, 'picam2', None)
                if not picam2 or not getattr(picam2, 'started', False):
                    time.sleep(0.01)
                    continue
                frame = picam2.capture_array()
                if frame is not None:
                    self.frame_ready.emit(frame)
            except Exception as e:
                if not self._running:
                    break
                self.error.emit(f"capture_array error: {e}")
                time.sleep(0.01)
                continue

            now = time.monotonic()
            if now < next_t:
                time.sleep(max(0, next_t - now))
            next_t = now + period

        self.finished.emit()

    @pyqtSlot()
    def stop(self):
        self._running = False

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
        self.current_gain = 1.0       # Default analogue gain
        self.current_ev = 0.0         # Default EV (UI only)
        self.job_enabled = False
        self.external_trigger_enabled = False
        self._last_sensor_ts = 0
        self._trigger_waiting = False
        self._available_formats = []  # Will be populated in _safe_init_picamera
        self.latest_frame = None       # Store latest frame for consumers
        self._use_threaded_live = True # Use threaded live capture aligned with testjob.py
        self._target_fps = 10.0        # Default live FPS
        self._live_thread = None
        self._live_worker = None
        self._is_auto_exposure = True  # AE enabled by default (align with new UI)
        # AWB state
        self._awb_enable = True
        self._colour_gains = (1.8, 1.8)
        
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

    # -------------- AWB controls (high-level API) --------------
    def set_awb_enable(self, enabled: bool):
        """Enable/disable Auto White Balance and apply/persist controls."""
        try:
            self._awb_enable = bool(enabled)
            # Persist into preview_config so it survives reconfigure
            if hasattr(self, 'preview_config') and self.preview_config is not None:
                if "controls" not in self.preview_config:
                    self.preview_config["controls"] = {}
                self.preview_config["controls"]["AwbEnable"] = self._awb_enable
            # Apply to running camera if available
            if self.is_camera_available and hasattr(self, 'picam2') and self.picam2 is not None:
                controls = {"AwbEnable": self._awb_enable}
                if not self._awb_enable:
                    # When switching to manual, also push current gains if known
                    try:
                        r, b = self._colour_gains
                        controls["ColourGains"] = (float(r), float(b))
                    except Exception:
                        pass
                if self.picam2.started:
                    self.picam2.set_controls(controls)
            return True
        except Exception:
            return False

    def set_colour_gains(self, r_gain: float, b_gain: float):
        """Set manual colour gains (R, B) and apply if AWB is disabled."""
        try:
            r = float(r_gain)
            b = float(b_gain)
            self._colour_gains = (r, b)
            # Persist into preview_config
            if hasattr(self, 'preview_config') and self.preview_config is not None:
                if "controls" not in self.preview_config:
                    self.preview_config["controls"] = {}
                self.preview_config["controls"]["ColourGains"] = (r, b)
            # Apply to running camera if available and AWB is manual
            if (not self._awb_enable) and self.is_camera_available and hasattr(self, 'picam2') and self.picam2 is not None and self.picam2.started:
                try:
                    self.picam2.set_controls({"ColourGains": (r, b)})
                except Exception:
                    pass
            return True
        except Exception:
            return False

    # ---------- Prime & Lock (like testjob) ----------
    def prime_and_lock(self, prime_ms: int = 400):
        """Briefly enable AE/AWB to settle, read metadata, then lock manual values.

        This mimics testjob's _prime_and_lock behaviour.
        """
        if not self.is_camera_available:
            return False
        try:
            # Ensure initialized
            if not hasattr(self, 'picam2') or self.picam2 is None:
                if not self._safe_init_picamera():
                    return False
            # Configure and start with AE/AWB enabled
            if not getattr(self, 'preview_config', None):
                try:
                    self.preview_config = self.picam2.create_preview_configuration(main={"format": "RGB888"})
                except Exception:
                    self.preview_config = self.picam2.create_preview_configuration()
            if "controls" not in self.preview_config:
                self.preview_config["controls"] = {}
            self.preview_config["controls"].update({"AeEnable": True, "AwbEnable": True})
            self.picam2.configure(self.preview_config)
            self.picam2.start()
            time.sleep(max(0.0, float(prime_ms) / 1000.0))
            md = {}
            try:
                md = self.picam2.capture_metadata()
            except Exception:
                md = {}
            # Extract values
            exp = int(md.get("ExposureTime", self.current_exposure))
            gain = float(md.get("AnalogueGain", self.current_gain))
            cg = md.get("ColourGains", self._colour_gains)
            try:
                cg = (float(cg[0]), float(cg[1]))
            except Exception:
                cg = self._colour_gains
            # Stop and lock manual values
            self.picam2.stop()
            self.current_exposure = exp
            self.current_gain = gain
            self._colour_gains = cg
            self._awb_enable = False
            self._is_auto_exposure = False
            # Persist locked values
            if not getattr(self, 'preview_config', None):
                try:
                    self.preview_config = self.picam2.create_preview_configuration(main={"format": "RGB888"})
                except Exception:
                    self.preview_config = self.picam2.create_preview_configuration()
            if "controls" not in self.preview_config:
                self.preview_config["controls"] = {}
            self.preview_config["controls"].update({
                "ExposureTime": self.current_exposure,
                "AnalogueGain": self.current_gain,
                "AeEnable": False,
                "AwbEnable": False,
                "ColourGains": (self._colour_gains[0], self._colour_gains[1]),
            })
            # Reconfigure with locked settings
            self.picam2.configure(self.preview_config)
            return True
        except Exception as e:
            print(f"DEBUG: [CameraStream] prime_and_lock error: {e}")
            return False
    
    def _safe_init_picamera(self):
        """Safe initialization of picamera2 with error handling"""
        if not has_picamera2:
            return False
            
        try:
            _ensure_xdg_runtime_dir()
            self.picam2 = Picamera2()
            print("DEBUG: [CameraStream] picamera2 initialized successfully")
            
            # Get available camera formats
            self._available_formats = []
            try:
                camera_properties = self.picam2.camera_properties
                if "pixel_formats" in camera_properties:
                    self._available_formats = camera_properties["pixel_formats"]
                    print(f"DEBUG: [CameraStream] Available formats: {self._available_formats}")
                else:
                    # Fallback default formats if not found in properties
                    self._available_formats = ["BGGR10", "BGGR12", "BGGR8", "YUV420"]
                    print(f"DEBUG: [CameraStream] Using default formats: {self._available_formats}")
            except Exception as format_error:
                print(f"DEBUG: [CameraStream] Error getting formats: {format_error}")
                # Fallback default formats on error
                self._available_formats = ["BGGR10", "BGGR12", "BGGR8", "YUV420"]
            
            # Create default configurations (prefer RGB888 for UI-friendly pipeline)
            try:
                self.preview_config = self.picam2.create_preview_configuration(main={"format": "RGB888"})
            except Exception:
                self.preview_config = self.picam2.create_preview_configuration()
            self.still_config = self.picam2.create_still_configuration()
            
            # Add exposure controls
            if "controls" not in self.preview_config:
                self.preview_config["controls"] = {}
            self.preview_config["controls"]["ExposureTime"] = self.current_exposure
            self.preview_config["controls"]["AnalogueGain"] = self.current_gain
            self.preview_config["controls"]["AeEnable"] = bool(self._is_auto_exposure)
            # AWB defaults
            self.preview_config["controls"]["AwbEnable"] = True
            
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
        
        # Store and emit the test frame
        self.latest_frame = frame
        self.frame_ready.emit(frame)
    
    def set_trigger_mode(self, enabled):
        """Enable/disable external hardware trigger and reconfigure Picamera2.

        - Sets IMX296 sysfs trigger parameter (requires privileges).
        - Configures Picamera2 to external trigger (video pipeline) and uses non-blocking polling.
        - Arms once; does not reconfigure per trigger.
        """
        success_hw = True
        print(f"DEBUG: [CameraStream] set_trigger_mode({enabled}) called")
        
        try:
            value = "1" if enabled else "0"
            cmd = f"echo {value} | sudo -S tee /sys/module/imx296/parameters/trigger_mode"
            print(f"DEBUG: [CameraStream] Setting IMX296 trigger_mode={value} with command: {cmd}")
            import subprocess
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            # Check if command succeeded
            if result.returncode == 0:
                print(f"DEBUG: [CameraStream] Successfully set IMX296 trigger_mode={value}")
                success_hw = True
            else:
                print(f"DEBUG: [CameraStream] Failed to set IMX296 trigger_mode: {result.stderr}")
                success_hw = False
                
                # Try alternative command without -S flag (assume sudo is already configured)
                try:
                    alt_cmd = f"echo {value} | sudo tee /sys/module/imx296/parameters/trigger_mode"
                    print(f"DEBUG: [CameraStream] Trying alternative command (without -S): {alt_cmd}")
                    alt_result = subprocess.run(alt_cmd, shell=True, capture_output=True, text=True)
                    if alt_result.returncode == 0:
                        print(f"DEBUG: [CameraStream] Alternative command succeeded")
                        success_hw = True
                    else:
                        print(f"DEBUG: [CameraStream] Alternative command also failed: {alt_result.stderr}")
                        # Try pkexec as last resort
                        pkexec_cmd = f"pkexec bash -c 'echo {value} > /sys/module/imx296/parameters/trigger_mode'"
                        print(f"DEBUG: [CameraStream] Trying pkexec command: {pkexec_cmd}")
                        pkexec_result = subprocess.run(pkexec_cmd, shell=True, capture_output=True, text=True)
                        if pkexec_result.returncode == 0:
                            print(f"DEBUG: [CameraStream] pkexec command succeeded")
                            success_hw = True
                        else:
                            print(f"DEBUG: [CameraStream] pkexec command failed: {pkexec_result.stderr}")
                except Exception as alt_e:
                    print(f"DEBUG: [CameraStream] Error with alternative commands: {alt_e}")
            
            # Verify the setting by reading back the value
            try:
                verify_cmd = "cat /sys/module/imx296/parameters/trigger_mode"
                verify_result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
                if verify_result.returncode == 0:
                    actual_value = verify_result.stdout.strip()
                    expected_value = value
                    print(f"DEBUG: [CameraStream] Verification: expected={expected_value}, actual={actual_value}")
                    if actual_value == expected_value:
                        print(f"DEBUG: [CameraStream] Trigger mode setting verified successfully")
                        success_hw = True
                    else:
                        print(f"DEBUG: [CameraStream] WARNING: Trigger mode verification failed!")
                        success_hw = False
                else:
                    print(f"DEBUG: [CameraStream] Could not verify trigger mode: {verify_result.stderr}")
            except Exception as verify_e:
                print(f"DEBUG: [CameraStream] Error verifying trigger mode: {verify_e}")
                
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error writing IMX296 trigger sysfs: {e}")
            success_hw = False

        # Always update internal state
        self.external_trigger_enabled = bool(enabled)
        self._last_sensor_ts = 0
        print(f"DEBUG: [CameraStream] Internal state updated: external_trigger_enabled = {self.external_trigger_enabled}")
        
        if not self.picam2:
            print(f"DEBUG: [CameraStream] No picam2 instance available, returning")
            return success_hw

        # Check if camera is currently running
        was_live = bool(getattr(self, 'is_live', False))
        print(f"DEBUG: [CameraStream] Camera was running: {was_live}")
        
        if was_live:
            # Stop the camera before changing modes
            try:
                print(f"DEBUG: [CameraStream] Stopping camera before mode change")
                if hasattr(self, 'stop_live'):
                    self.stop_live()
                elif hasattr(self.picam2, 'stop'):
                    self.picam2.stop()
            except Exception as e:
                print(f"DEBUG: [CameraStream] Error stopping camera: {e}")
            
            # Restart camera in appropriate mode
            try:
                if enabled:
                    print("DEBUG: [CameraStream] Restarting camera in trigger mode")
                    # Configure for still capture if available
                    if hasattr(self, 'still_config') and self.still_config:
                        print("DEBUG: [CameraStream] Configuring with still_config for trigger mode")
                        self.picam2.configure(self.still_config)
                    self.start_live()  # Keep trigger enabled
                else:
                    print("DEBUG: [CameraStream] Restarting camera in live mode (no trigger)")
                    # Configure for preview if available
                    if hasattr(self, 'preview_config') and self.preview_config:
                        print("DEBUG: [CameraStream] Configuring with preview_config for live mode")
                        self.picam2.configure(self.preview_config)
                    self.start_live()  # Trigger already disabled above
            except Exception as e:
                print(f"DEBUG: [CameraStream] Error restarting camera: {e}")
                success_hw = False

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
                
            # Store and emit the frame
            self.latest_frame = frame
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
            # DON'T automatically disable hardware trigger here
            # Let the caller decide if they want trigger mode or not
            print(f"DEBUG: [CameraStream] Current trigger mode: {self.external_trigger_enabled}")
            
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
            
            # Start threaded live capturing or fallback timer
            if getattr(self, '_use_threaded_live', False):
                print(f"DEBUG: [CameraStream] Starting threaded live worker at {self._target_fps} FPS")
                if hasattr(self, 'timer') and self.timer.isActive():
                    self.timer.stop()
                self._start_live_worker()
            else:
                if hasattr(self, 'timer') and not self.timer.isActive():
                    interval = int(1000.0 / max(1.0, float(self._target_fps)))
                    self.timer.start(interval)
            
            self.is_live = True
            print("DEBUG: [CameraStream] Live view started successfully")
            
            return True
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error starting live view: {e}")
            self.camera_error.emit(f"Failed to start camera: {str(e)}")
            self.is_live = False
            return False

    def start_live_no_trigger(self):
        """Start live view from camera with hardware trigger explicitly disabled"""
        print("DEBUG: [CameraStream] start_live_no_trigger called")
        
        # First disable hardware trigger if it's enabled
        if hasattr(self, 'external_trigger_enabled') and self.external_trigger_enabled:
            print("DEBUG: [CameraStream] Disabling hardware trigger for live mode")
            self.set_trigger_mode(False)
        
        # Then start live view normally
        return self.start_live()
    
    def stop_live(self):
        """Stop live view"""
        print("DEBUG: [CameraStream] stop_live called")

        try:
            # Ensure any pending requests are cancelled to unblock capture
            try:
                if hasattr(self, 'picam2') and self.picam2 is not None and hasattr(self.picam2, 'cancel_all_and_flush'):
                    self.picam2.cancel_all_and_flush()
            except Exception:
                pass

            # Stop the timer
            if hasattr(self, 'timer') and self.timer.isActive():
                self.timer.stop()
            
            # Stop threaded worker if running
            if getattr(self, '_live_worker', None) is not None:
                try:
                    self._live_worker.stop()
                except Exception:
                    pass
            if getattr(self, '_live_thread', None) is not None:
                try:
                    self._live_thread.quit()
                    self._live_thread.wait(1500)
                except Exception:
                    pass
                self._live_thread = None
                self._live_worker = None
            
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

    def cancel_all_and_flush(self):
        """Cancel pending camera requests and flush pipeline (Picamera2 helper)."""
        try:
            if hasattr(self, 'picam2') and self.picam2 is not None and hasattr(self.picam2, 'cancel_all_and_flush'):
                self.picam2.cancel_all_and_flush()
                print("DEBUG: [CameraStream] cancel_all_and_flush executed")
                return True
            return False
        except Exception as e:
            print(f"DEBUG: [CameraStream] cancel_all_and_flush error: {e}")
            return False

    def cancel_and_stop_live(self):
        """Preferred safe stop: cancel pending requests then stop live view and worker."""
        self.cancel_all_and_flush()
        return self.stop_live()

    def _start_live_worker(self):
        """Create and start a background worker for live frames."""
        # Stop any existing worker
        if getattr(self, '_live_worker', None) is not None:
            try:
                self._live_worker.stop()
            except Exception:
                pass
        if getattr(self, '_live_thread', None) is not None:
            try:
                self._live_thread.quit()
                self._live_thread.wait(500)
            except Exception:
                pass
            self._live_thread = None
            self._live_worker = None

        self._live_thread = QThread()
        self._live_worker = _LiveWorker(self, target_fps=self._target_fps)
        self._live_worker.moveToThread(self._live_thread)

        # Wire signals
        self._live_thread.started.connect(self._live_worker.run)
        self._live_worker.frame_ready.connect(self._handle_worker_frame)
        self._live_worker.error.connect(self.camera_error.emit)
        self._live_worker.finished.connect(self._live_thread.quit)

        self._live_thread.start()

    @pyqtSlot(object)
    def _handle_worker_frame(self, frame):
        """Store and forward frames from worker."""
        try:
            self.latest_frame = frame
        except Exception:
            pass
        self.frame_ready.emit(frame)
    
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

    # ---------- AE controls ----------
    def set_auto_exposure(self, enabled: bool):
        """Enable/disable auto exposure (AeEnable) and persist to configs."""
        try:
            self._is_auto_exposure = bool(enabled)
            # Persist to preview config
            if hasattr(self, 'preview_config') and self.preview_config is not None:
                if "controls" not in self.preview_config:
                    self.preview_config["controls"] = {}
                self.preview_config["controls"]["AeEnable"] = self._is_auto_exposure
            # Persist to still config as well
            if hasattr(self, 'still_config') and self.still_config is not None:
                if "controls" not in self.still_config:
                    self.still_config["controls"] = {}
                self.still_config["controls"]["AeEnable"] = self._is_auto_exposure
            # Apply to running camera
            if self.is_camera_available and hasattr(self, 'picam2') and self.picam2 is not None and self.picam2.started:
                self.picam2.set_controls({"AeEnable": self._is_auto_exposure})
            return True
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error in set_auto_exposure: {e}")
            return False

    def get_exposure(self):
        """Return current exposure time in microseconds (cached value)."""
        try:
            return int(self.current_exposure)
        except Exception:
            return self.current_exposure

    # ---------- Gain controls ----------
    def set_gain(self, gain: float):
        """Set analogue gain and persist/apply."""
        try:
            g = float(gain)
            self.current_gain = g
            # Persist
            if hasattr(self, 'preview_config') and self.preview_config is not None:
                if "controls" not in self.preview_config:
                    self.preview_config["controls"] = {}
                self.preview_config["controls"]["AnalogueGain"] = g
            if hasattr(self, 'still_config') and self.still_config is not None:
                if "controls" not in self.still_config:
                    self.still_config["controls"] = {}
                self.still_config["controls"]["AnalogueGain"] = g
            # Apply to running
            if self.is_camera_available and hasattr(self, 'picam2') and self.picam2 is not None and self.picam2.started:
                try:
                    self.picam2.set_controls({"AnalogueGain": g})
                except Exception:
                    pass
            print(f"DEBUG: [CameraStream] Analogue gain set to {g}")
            return True
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error setting gain: {e}")
            return False

    def get_gain(self):
        """Return current analogue gain (cached value)."""
        try:
            return float(self.current_gain)
        except Exception:
            return self.current_gain

    # ---------- EV controls (UI only fallback) ----------
    def set_ev(self, ev: float):
        """Store EV compensation value (UI/display)."""
        try:
            self.current_ev = float(ev)
            # Picamera2 EV mapping varies; skip direct hardware apply for safety
            return True
        except Exception:
            return False

    def get_ev(self):
        try:
            return float(self.current_ev)
        except Exception:
            return self.current_ev

    # ---------- Job toggle (for pipeline processing) ----------
    def set_job_enabled(self, enabled: bool):
        try:
            self.job_enabled = bool(enabled)
            return True
        except Exception:
            return False

    def set_frame_size(self, width, height):
        """Set preview frame size and reconfigure if needed."""
        try:
            if not self.is_camera_available or not hasattr(self, 'picam2') or self.picam2 is None:
                print("DEBUG: [CameraStream] Camera not available for set_frame_size")
                return False
            if not hasattr(self, 'preview_config') or self.preview_config is None:
                try:
                    self.preview_config = self.picam2.create_preview_configuration(main={"size": (int(width), int(height))})
                except Exception:
                    self.preview_config = self.picam2.create_preview_configuration()
            else:
                if "main" not in self.preview_config:
                    self.preview_config["main"] = {}
                self.preview_config["main"]["size"] = (int(width), int(height))
            was_running = bool(self.picam2.started)
            if was_running:
                self.picam2.stop()
            self.picam2.configure(self.preview_config)
            if was_running:
                self.picam2.start(show_preview=False)
            print(f"DEBUG: [CameraStream] Frame size set to {width}x{height}")
            return True
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error setting frame size: {e}")
            return False

    def set_format(self, pixel_format):
        """Set preview pixel format (e.g., 'RGB888', 'BGR888')."""
        try:
            if not self.is_camera_available or not hasattr(self, 'picam2') or self.picam2 is None:
                print("DEBUG: [CameraStream] Camera not available for set_format")
                return False
            if not hasattr(self, 'preview_config') or self.preview_config is None:
                try:
                    self.preview_config = self.picam2.create_preview_configuration(main={"format": str(pixel_format)})
                except Exception:
                    self.preview_config = self.picam2.create_preview_configuration()
            else:
                if "main" not in self.preview_config:
                    self.preview_config["main"] = {}
                self.preview_config["main"]["format"] = str(pixel_format)
            was_running = bool(self.picam2.started)
            if was_running:
                self.picam2.stop()
            self.picam2.configure(self.preview_config)
            if was_running:
                self.picam2.start(show_preview=False)
            print(f"DEBUG: [CameraStream] Pixel format set to {pixel_format}")
            return True
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error setting format: {e}")
            return False

    def set_target_fps(self, fps):
        """Set target FPS for live streaming (threaded or timer)."""
        try:
            self._target_fps = float(fps)
            if hasattr(self, 'timer') and self.timer.isActive() and not getattr(self, '_use_threaded_live', False):
                self.timer.stop()
                interval = int(1000.0 / max(1.0, self._target_fps))
                self.timer.start(interval)
            print(f"DEBUG: [CameraStream] Target FPS set to {self._target_fps}")
            return True
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error setting target FPS: {e}")
            return False

    def get_latest_frame(self):
        """Return the most recent frame if available."""
        try:
            return self.latest_frame.copy() if self.latest_frame is not None else None
        except Exception:
            return self.latest_frame
    
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
                self.latest_frame = frame
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

    def get_available_formats(self):
        """
        Trả về danh sách các định dạng camera khả dụng
        
        Returns:
            list: Danh sách các định dạng pixel camera hỗ trợ
        """
        if not self.is_camera_available:
            # Nếu không có camera thực, trả về danh sách các định dạng mặc định
            return ["BGGR10", "BGGR12", "BGGR8", "YUV420"]
            
        # Trả về danh sách định dạng đã thu thập trong _safe_init_picamera
        return self._available_formats.copy() if hasattr(self, '_available_formats') and self._available_formats else ["BGGR10", "BGGR12", "BGGR8", "YUV420"]

    def is_running(self):
        """
        Kiểm tra xem camera có đang chạy không
        
        Returns:
            bool: True nếu camera đang chạy, False nếu không
        """
        # Kiểm tra trạng thái is_live
        if hasattr(self, 'is_live'):
            return bool(self.is_live)
            
        # Kiểm tra trạng thái picam2 nếu không có is_live
        if hasattr(self, 'picam2') and self.picam2:
            return bool(getattr(self.picam2, 'started', False))
            
        # Mặc định là không chạy
        return False

# End of CameraStream class

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
