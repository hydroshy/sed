"""
Camera stream module
Provides CameraStream class for interacting with camera hardware
"""

import os
import time
import threading
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
        
        # Performance monitoring
        self._frame_count = 0
        self._last_fps_time = 0
        self._fps_interval = 5.0  # Report FPS every 5 seconds

    @pyqtSlot()
    def run(self):
        self._running = True
        try:
            period = 1.0 / max(1.0, self._target_fps)
        except Exception:
            period = 0.1
        
        next_t = time.monotonic()
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self._running:
            start_time = time.monotonic()
            
            try:
                picam2 = getattr(self._stream, 'picam2', None)
                if not picam2 or not getattr(picam2, 'started', False):
                    time.sleep(0.05)  # Increased sleep for camera not ready
                    continue
                
                # Use capture_array with timeout to prevent blocking
                # If capture takes too long, skip frame to maintain FPS
                try:
                    frame = picam2.capture_array()
                    if frame is not None:
                        self.frame_ready.emit(frame)
                        consecutive_errors = 0  # Reset error counter on success
                        
                        # FPS monitoring for performance debugging
                        self._frame_count += 1
                        now_fps = time.monotonic()
                        if self._last_fps_time == 0:
                            self._last_fps_time = now_fps
                        elif now_fps - self._last_fps_time >= self._fps_interval:
                            actual_fps = self._frame_count / (now_fps - self._last_fps_time)
                            from utils.debug_utils import debug_log
                            debug_log(f"LiveWorker FPS: {actual_fps:.1f} (target: {self._target_fps})", level="INFO")
                            self._frame_count = 0
                            self._last_fps_time = now_fps
                except Exception as capture_e:
                    # Handle capture-specific errors without stopping worker
                    consecutive_errors += 1
                    if consecutive_errors <= max_consecutive_errors:
                        # Don't emit error for first few failures (could be timing issues)
                        time.sleep(0.01)
                        continue
                    else:
                        # Only emit error after multiple consecutive failures
                        if not self._running:
                            break
                        self.error.emit(f"capture_array timeout/error: {capture_e}")
                        time.sleep(0.1)  # Longer sleep after persistent errors
                        continue
                        
            except Exception as e:
                if not self._running:
                    break
                consecutive_errors += 1
                if consecutive_errors > max_consecutive_errors:
                    self.error.emit(f"live worker error: {e}")
                time.sleep(0.05)
                continue

            # Precise timing control to maintain target FPS
            now = time.monotonic()
            elapsed = now - start_time
            
            # Calculate sleep time more accurately
            sleep_time = max(0.001, next_t - now)  # Minimum 1ms sleep
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            # Update next target time
            next_t = max(now, next_t) + period

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
        
        # Cleanup guard flag - prevents multiple cleanup calls
        self._cleanup_in_progress = False
        
        self.is_camera_available = has_picamera2
        # Track current pixel format selection for preview/display
        # Default to BGR888 since PiCamera2 naturally outputs BGR
        self._pixel_format = 'BGR888'
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
        
        # Single shot trigger control
        self._single_shot_lock = threading.Lock()
        self._cooldown_s = 0.25  # ⚠️ TESTING: Cooldown disabled (was 0.25 = 250ms)
        self._last_trigger_time = 0.0
        self._trigger_sent_time = 0.0  # 💡 Track when trigger signal was sent for synchronization
        
        # Trigger mode state - when True, prevent live streaming
        self._in_trigger_mode = False
        
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
        h, w = 480, 640
        
        # Try to load a real test image instead of synthetic patterns
        test_image_path = "/home/pi/Desktop/project/image/pilsner333/pilsner333_3.jpg"
        try:
            import cv2
            if hasattr(cv2, 'imread'):
                test_img = cv2.imread(test_image_path)
                if test_img is not None:
                    # Resize to camera frame size
                    test_frame = cv2.resize(test_img, (w, h))
                    print(f"DEBUG: [CameraStream] Using real test image: {test_image_path}")
                    return test_frame
        except Exception as e:
            # print(f"DEBUG: [CameraStream] Could not load real test image: {e}")
            pass
        
        # Fallback to synthetic patterns if real image fails
        # Create varied patterns that change over time for proper classification testing
        # This ensures different frames will produce different classification results
        pattern_cycle = int(time.time() * 0.5) % 6  # Change pattern every 2 seconds
        
        r = np.zeros((h, w), dtype=np.uint8)
        g = np.zeros((h, w), dtype=np.uint8)
        b = np.zeros((h, w), dtype=np.uint8)
        
        if pattern_cycle == 0:
            # Pattern 0: Red gradient with blue noise
            r[:, :] = np.tile(np.linspace(0, 255, w, dtype=np.uint8), (h, 1))
            b[:, :] = np.random.randint(0, 100, (h, w), dtype=np.uint8)
        elif pattern_cycle == 1:
            # Pattern 1: Green checkerboard
            for i in range(0, h, 32):
                for j in range(0, w, 32):
                    if (i//32 + j//32) % 2 == 0:
                        g[i:i+32, j:j+32] = 200
        elif pattern_cycle == 2:
            # Pattern 2: Blue radial gradient
            center_y, center_x = h//2, w//2
            for y in range(h):
                for x in range(w):
                    dist = np.sqrt((y - center_y)**2 + (x - center_x)**2)
                    b[y, x] = min(255, int(dist * 0.8))
        elif pattern_cycle == 3:
            # Pattern 3: Multi-color stripes
            stripe_width = w // 8
            for i in range(8):
                start_x = i * stripe_width
                end_x = min(w, (i + 1) * stripe_width)
                if i % 3 == 0:
                    r[:, start_x:end_x] = 255
                elif i % 3 == 1:
                    g[:, start_x:end_x] = 255
                else:
                    b[:, start_x:end_x] = 255
        elif pattern_cycle == 4:
            # Pattern 4: Random noise with color bias
            r[:, :] = np.random.randint(100, 255, (h, w), dtype=np.uint8)
            g[:, :] = np.random.randint(0, 150, (h, w), dtype=np.uint8)
            b[:, :] = np.random.randint(0, 100, (h, w), dtype=np.uint8)
        else:  # pattern_cycle == 5
            # Pattern 5: Geometric shapes
            # Triangle in top-left
            for y in range(h//2):
                for x in range(w//2):
                    if x < y:
                        r[y, x] = 255
            # Circle in bottom-right
            center_y, center_x = 3*h//4, 3*w//4
            radius = min(h, w) // 8
            for y in range(h//2, h):
                for x in range(w//2, w):
                    if (y - center_y)**2 + (x - center_x)**2 < radius**2:
                        g[y, x] = 255
        
        # Add format identifier text area (white rectangle in corner) - keep this
        r[10:50, 10:200] = 255
        g[10:50, 10:200] = 255
        b[10:50, 10:200] = 255

        pf = getattr(self, '_pixel_format', 'RGB888')
        print(f"DEBUG: [CameraStream] Generating test frame with format: {pf}, pattern: {pattern_cycle}")
        
        if pf == 'BGR888':
            # BGR order: Blue, Green, Red
            frame = np.dstack((b, g, r))
        elif pf == 'RGB888':
            # RGB order: Red, Green, Blue
            frame = np.dstack((r, g, b))
        elif pf == 'XRGB8888':
            # RGBA order with opaque alpha
            a = np.full((h, w), 255, dtype=np.uint8)
            frame = np.dstack((r, g, b, a))
        else:
            # For unsupported formats, default to BGR for compatibility
            print(f"DEBUG: [CameraStream] Unsupported format {pf}, using BGR")
            frame = np.dstack((b, g, r))
        
        # Store and emit the test frame
        self.latest_frame = frame
        self.frame_ready.emit(frame)
    
    def set_trigger_mode(self, enabled):
        """Set trigger mode - now uses capture_request() instead of hardware GPIO trigger.

        When enabled:
        - Camera continues running in preview mode
        - Frames are only captured when capture_single_frame_request() is called
        - No more GPIO/sysfs interaction needed
        
        When disabled:
        - Camera returns to continuous live streaming mode
        """
        print(f"DEBUG: [CameraStream] set_trigger_mode({enabled}) called - using capture_request mode")
        
        try:
            # Simply update internal state - no more hardware GPIO/sysfs interaction
            self.external_trigger_enabled = bool(enabled)
            self._in_trigger_mode = bool(enabled)  # Set trigger mode flag
            self._last_sensor_ts = 0
            
            print(f"DEBUG: [CameraStream] Trigger mode set to: {enabled}")
            print("DEBUG: [CameraStream] Note: Using capture_request() mode - no GPIO trigger needed")
            
            # If camera is not available, just update state
            if not self.is_camera_available:
                print("DEBUG: [CameraStream] Camera not available - state updated only")
                return True
            
            # Ensure camera is initialized
            if not hasattr(self, 'picam2') or self.picam2 is None:
                print("DEBUG: [CameraStream] Camera not initialized")
                return True  # State is updated, camera will be configured when needed
            
            # Check if camera is currently running
            was_live = bool(getattr(self, 'is_live', False))
            print(f"DEBUG: [CameraStream] Camera was running: {was_live}")
            
            if enabled:
                # Entering trigger mode
                print("DEBUG: [CameraStream] Entering trigger mode - stopping live streaming")
                
                # FIRST: Stop live streaming immediately to prevent continuous frames
                if was_live:
                    self._stop_live_streaming()
                    print("DEBUG: [CameraStream] Stopped live streaming for trigger mode")
                
                # SECOND: Ensure camera is configured and started for capture_request calls
                # but NOT streaming continuously
                if not self.picam2.started:
                    print("DEBUG: [CameraStream] Starting camera for trigger mode (no streaming)")
                    if not hasattr(self, 'preview_config') or not self.preview_config:
                        self.preview_config = self.picam2.create_preview_configuration(
                            main={"size": (1920, 1080), "format": "RGB888"},
                            queue=False,           # không lấy khung cũ
                            buffer_count=2
                        )
                    
                    # Apply current camera settings
                    if "controls" not in self.preview_config:
                        self.preview_config["controls"] = {}
                    
                    # Apply exposure settings
                    if not self._is_auto_exposure:
                        self.preview_config["controls"]["ExposureTime"] = self.current_exposure
                        self.preview_config["controls"]["AeEnable"] = False
                    else:
                        self.preview_config["controls"]["AeEnable"] = True
                    
                    # Apply gain settings
                    self.preview_config["controls"]["AnalogueGain"] = self.current_gain
                    
                    # Configure and start camera but DON'T start streaming
                    self.picam2.configure(self.preview_config)
                    self.picam2.start(show_preview=False)  # Start camera but no preview
                    print("DEBUG: [CameraStream] Camera started in trigger mode (ready for capture_request)")
                else:
                    print("DEBUG: [CameraStream] Camera already started - stopping any streaming")
                    # If camera is already started, make sure streaming is stopped
                    self._stop_live_streaming()
                
                print("DEBUG: [CameraStream] Trigger mode ready - camera will only capture on demand")
                    
            else:
                # Exiting trigger mode - return to live streaming if it was active before
                print("DEBUG: [CameraStream] Exiting trigger mode")
                
                # Reset trigger mode flag to allow live streaming
                self._in_trigger_mode = False
                
                if was_live:
                    print("DEBUG: [CameraStream] Restoring live streaming mode")
                    # Restart live streaming
                    self._start_live_streaming()
                else:
                    print("DEBUG: [CameraStream] Camera remains in stopped state")
            
            print(f"DEBUG: [CameraStream] set_trigger_mode completed successfully: {enabled}")
            return True
                
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error in set_trigger_mode: {e}")
            # Update state anyway
            self.external_trigger_enabled = bool(enabled)
            return False
    
    def _stop_live_streaming(self):
        """Helper method to stop live streaming completely"""
        try:
            # Stop timer-based streaming
            if hasattr(self, 'timer') and self.timer:
                self.timer.stop()
                print("DEBUG: [CameraStream] Timer stopped")
            
            # Stop threaded worker
            if hasattr(self, '_live_worker') and self._live_worker:
                self._live_worker.stop()
                print("DEBUG: [CameraStream] Live worker stopped")
            
            # Stop thread if running
            if hasattr(self, '_live_thread') and self._live_thread and self._live_thread.isRunning():
                self._live_thread.quit()
                self._live_thread.wait(1000)  # Wait up to 1 second
                print("DEBUG: [CameraStream] Live thread stopped")
            
            # Clear live state
            self.is_live = False
            print("DEBUG: [CameraStream] Live streaming stopped completely")
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error stopping live streaming: {e}")
    
    def _start_live_streaming(self):
        """Helper method to start live streaming"""
        try:
            if self._use_threaded_live:
                self._start_live_worker()
            else:
                if hasattr(self, 'timer') and self.timer:
                    self.timer.start(100)  # 10 FPS
            
            self.is_live = True
            print("DEBUG: [CameraStream] Live streaming started")
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error starting live streaming: {e}")


        
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
    
    def start_live(self, preserve_trigger_mode=False):
        """Start live view from camera or stub generator when hardware unavailable
        
        Args:
            preserve_trigger_mode: If True, don't change trigger mode when starting live
        """
        print(f"DEBUG: [CameraStream] start_live called with preserve_trigger_mode={preserve_trigger_mode}")
        
        # Handle stub mode (no picamera2): start test-frame timer instead of failing
        if not self.is_camera_available:
            print("DEBUG: [CameraStream] Camera not available -> starting stub live timer")
            try:
                # Ensure a timer exists and is wired to generate frames
                if not hasattr(self, 'timer'):
                    self.timer = QTimer()
                    self.timer.timeout.connect(self._generate_test_frame)
                # Start timer at target FPS
                interval = int(1000.0 / max(1.0, float(getattr(self, '_target_fps', 10.0))))
                if not self.timer.isActive():
                    self.timer.start(max(1, interval))
                self.is_live = True
                return True
            except Exception as e:
                print(f"DEBUG: [CameraStream] Error starting stub live: {e}")
                return False
            
        try:
            # For regular live view, we need to disable trigger mode if it's enabled
            # UNLESS we're being asked to preserve the current mode (for editing)
            current_trigger_mode = getattr(self, 'external_trigger_enabled', False)
            if not preserve_trigger_mode and hasattr(self, 'external_trigger_enabled') and self.external_trigger_enabled:
                print("DEBUG: [CameraStream] Disabling trigger mode for live view")
                self.set_trigger_mode(False)
            else:
                print(f"DEBUG: [CameraStream] Preserving trigger mode: {current_trigger_mode}")
            
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
            
            # Start threaded live capturing or fallback timer ONLY if not in trigger mode
            if getattr(self, '_in_trigger_mode', False):
                print("DEBUG: [CameraStream] In trigger mode - NOT starting live streaming")
            elif getattr(self, '_use_threaded_live', False):
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
    
    def start_preview(self):
        """Start simple camera preview stream like testjob.py - no mode changes"""
        print("DEBUG: [CameraStream] start_preview called - simple streaming mode")
        
        # Handle stub mode (no picamera2): start test-frame timer instead of failing
        if not self.is_camera_available:
            print("DEBUG: [CameraStream] Camera not available -> starting stub preview timer")
            try:
                # Ensure a timer exists and is wired to generate frames
                if not hasattr(self, 'timer'):
                    self.timer = QTimer()
                    self.timer.timeout.connect(self._generate_test_frame)
                # Start timer at target FPS
                interval = int(1000.0 / max(1.0, float(getattr(self, '_target_fps', 10.0))))
                if not self.timer.isActive():
                    self.timer.start(max(1, interval))
                self.is_live = True
                return True
            except Exception as e:
                print(f"DEBUG: [CameraStream] Error starting stub preview: {e}")
                return False
                
        try:
            # Ensure camera is initialized (but don't change trigger mode)
            if not hasattr(self, 'picam2') or self.picam2 is None:
                print("DEBUG: [CameraStream] Initializing camera for preview")
                if not self._safe_init_picamera():
                    print("DEBUG: [CameraStream] Failed to initialize camera")
                    return False
            
            # If camera is already started, stop it first
            if hasattr(self, 'picam2') and self.picam2 and self.picam2.started:
                print("DEBUG: [CameraStream] Camera already started, stopping first")
                self.picam2.stop()
            
            # Configure for preview (use preview config regardless of mode)
            self.picam2.configure(self.preview_config)
            print("DEBUG: [CameraStream] Camera configured for preview")
            
            # Start the camera
            print("DEBUG: [CameraStream] Starting camera for preview streaming")
            self.picam2.start(show_preview=False)
            
            # Start threaded live capturing or fallback timer ONLY if not in trigger mode
            if getattr(self, '_in_trigger_mode', False):
                print("DEBUG: [CameraStream] In trigger mode - NOT starting preview streaming")
            elif getattr(self, '_use_threaded_live', False):
                print(f"DEBUG: [CameraStream] Starting threaded preview worker at {self._target_fps} FPS")
                if hasattr(self, 'timer') and self.timer.isActive():
                    self.timer.stop()
                self._start_live_worker()
            else:
                if hasattr(self, 'timer') and not self.timer.isActive():
                    interval = int(1000.0 / max(1.0, float(self._target_fps)))
                    self.timer.start(interval)
            
            self.is_live = True
            print("DEBUG: [CameraStream] Preview streaming started successfully")
            return True
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error starting preview: {e}")
            self.camera_error.emit(f"Failed to start camera preview: {str(e)}")
            self.is_live = False
            return False
    
    def stop_preview(self):
        """Stop preview stream like testjob.py - simple stop"""
        print("DEBUG: [CameraStream] stop_preview called")
        return self.stop_live()  # Reuse existing stop_live logic
    
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
        """Set preview pixel format (e.g., 'RGB888', 'BGR888') with immediate apply using cancel_all_and_flush pattern."""
        try:
            old_format = getattr(self, '_pixel_format', 'Unknown')
            print(f"DEBUG: [CameraStream] Setting format from {old_format} to {pixel_format}")
            
            # Persist selection regardless of backend availability
            self._pixel_format = str(pixel_format)
            print(f"DEBUG: [CameraStream] _pixel_format updated to: {self._pixel_format}")
            
            if not self.is_camera_available or not hasattr(self, 'picam2') or self.picam2 is None:
                # Stub path: just ack success; test frames will reflect selection
                print(f"DEBUG: [CameraStream] (stub) set_format -> {self._pixel_format}")
                return True
                
            # Update preview config
            if not hasattr(self, 'preview_config') or self.preview_config is None:
                try:
                    self.preview_config = self.picam2.create_preview_configuration(main={"format": str(pixel_format)})
                except Exception:
                    self.preview_config = self.picam2.create_preview_configuration()
            else:
                if "main" not in self.preview_config:
                    self.preview_config["main"] = {}
                self.preview_config["main"]["format"] = str(pixel_format)
            
            # Apply immediately using cancel_all_and_flush pattern (like set_exposure)
            if hasattr(self.picam2, 'started') and self.picam2.started:
                print(f"DEBUG: [CameraStream] Using cancel_all_and_flush for immediate format change")
                # Cancel pending requests and flush buffers to prevent blocking
                if hasattr(self.picam2, 'cancel_all_and_flush'):
                    self.picam2.cancel_all_and_flush()
                
                # Stop, reconfigure with new format, and restart
                self.picam2.stop()
                self.picam2.configure(self.preview_config)
                self.picam2.start()
                print(f"DEBUG: [CameraStream] Format change applied immediately with camera restart")
            else:
                # Camera not running, safe to reconfigure
                self.picam2.configure(self.preview_config)
                print(f"DEBUG: [CameraStream] Configured camera with new format (camera not running)")
            
            print(f"DEBUG: [CameraStream] Pixel format set to {pixel_format}")
            return True
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error setting format: {e}")
            return False

    # --- Query helpers ---
    def get_pixel_format(self) -> str:
        """Return current preview pixel format string (e.g., 'RGB888')."""
        try:
            format_str = str(self._pixel_format)
            # Debug logging disabled for performance
            # print(f"DEBUG: [CameraStream] get_pixel_format() returning: {format_str}")
            return format_str
        except Exception:
            # print(f"DEBUG: [CameraStream] get_pixel_format() exception, returning BGR888")
            return 'BGR888'

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
    
    def capture_single_frame_request(self):
        """
        Capture a single frame using capture_request() method with cooldown protection.
        
        Uses threading lock and cooldown to ensure only one frame is captured per trigger,
        preventing multiple frames when button is pressed.
        
        Returns:
            numpy.ndarray: Captured frame, or None if capture failed or cooldown active
        """
        print("DEBUG: [CameraStream] capture_single_frame_request called")
        
        # Check cooldown and acquire lock (non-blocking)
        now = time.monotonic()
        if now - self._last_trigger_time < self._cooldown_s:
            print(f"DEBUG: [CameraStream] Trigger ignored - cooldown active ({self._cooldown_s}s)")
            return None
            
        if not self._single_shot_lock.acquire(False):
            print("DEBUG: [CameraStream] Trigger ignored - already processing")
            return None
        
        # Update last trigger time immediately after acquiring lock
        self._last_trigger_time = now
        
        try:
            if not self.is_camera_available:
                print("DEBUG: [CameraStream] Camera not available, generating test frame")
                # Generate a test frame for testing without camera
                import numpy as np
                test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                # Add some pattern to distinguish from regular test frames
                test_frame[100:200, 100:200] = [255, 0, 0]  # Red square
                self.latest_frame = test_frame
                self.frame_ready.emit(test_frame)
                return test_frame
                
            # Ensure camera is initialized
            if not hasattr(self, 'picam2') or self.picam2 is None:
                print("DEBUG: [CameraStream] Camera not initialized, reinitializing...")
                if not self._safe_init_picamera():
                    print("DEBUG: [CameraStream] Camera reinitialization failed")
                    return None
                print("DEBUG: [CameraStream] Camera reinitialized for capture_request")
            
            # Ensure camera is started (configured and running)
            if not self.picam2.started:
                print("DEBUG: [CameraStream] Camera not started, starting preview...")
                # Use preview config for continuous capture_request mode
                if not hasattr(self, 'preview_config') or not self.preview_config:
                    self.preview_config = self.picam2.create_preview_configuration(
                        main={"size": (1920, 1080), "format": "RGB888"},
                        queue=False,           # không lấy khung cũ
                        buffer_count=2
                    )
                    print("DEBUG: [CameraStream] Created preview config for capture_request")
                
                # Apply current settings to preview config
                if "controls" not in self.preview_config:
                    self.preview_config["controls"] = {}
                
                # Apply exposure settings
                if not self._is_auto_exposure:
                    self.preview_config["controls"]["ExposureTime"] = self.current_exposure
                    self.preview_config["controls"]["AeEnable"] = False
                else:
                    self.preview_config["controls"]["AeEnable"] = True
                
                # Apply gain settings
                self.preview_config["controls"]["AnalogueGain"] = self.current_gain
                
                # Apply AWB settings
                if self._awb_enable:
                    self.preview_config["controls"]["AwbEnable"] = True
                else:
                    self.preview_config["controls"]["AwbEnable"] = False
                    self.preview_config["controls"]["ColourGains"] = self._colour_gains
                
                print(f"DEBUG: [CameraStream] Preview config - Exposure: {self.current_exposure}μs, Gain: {self.current_gain}, AE: {self._is_auto_exposure}")
                
                # Configure and start camera
                self.picam2.configure(self.preview_config)
                self.picam2.start(show_preview=False)  # Start without preview display
                print("DEBUG: [CameraStream] Camera started for capture_request mode")
            
            print("DEBUG: [CameraStream] Calling capture_request() - waiting for next frame...")
            
            # Use capture_request() to get a completed request
            # This blocks until a request is completed with frame and metadata
            request = self.picam2.capture_request()
            
            if request is None:
                print("DEBUG: [CameraStream] capture_request returned None")
                return None
            
            try:
                # Get the main stream frame from the request
                # Usually 'main' stream contains the primary image
                frame = request.make_array("main")
                
                if frame is None:
                    print("DEBUG: [CameraStream] No frame in main stream")
                    return None
                
                print(f"DEBUG: [CameraStream] SYNCHRONIZED FRAME captured: {frame.shape} (immediate capture)")
                
                # Get metadata to validate frame timing
                metadata = request.get_metadata()
                if metadata:
                    # Use system time for comparison, not sensor timestamp (they use different epoch)
                    capture_time = time.time()
                    time_since_trigger = (capture_time - self._trigger_sent_time) * 1000  # Convert to ms
                    print(f"DEBUG: [CameraStream] Frame metadata: ExposureTime={metadata.get('ExposureTime', 'N/A')}, AnalogueGain={metadata.get('AnalogueGain', 'N/A')}, delta_trigger={time_since_trigger:.1f}ms")
                
                # Store frame and emit signal
                self.latest_frame = frame.copy()  # Make a copy since we'll release the request
                
                # Emit frame to UI
                self.frame_ready.emit(self.latest_frame)
                
                return self.latest_frame
                
            finally:
                # IMPORTANT: Always release the request to return buffers to pipeline
                request.release()
                print("DEBUG: [CameraStream] Request released")
                
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error in capture_single_frame_request: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            # Always release the lock
            self._single_shot_lock.release()
            print("DEBUG: [CameraStream] Single shot lock released")
    
    def set_trigger_cooldown(self, cooldown_seconds=0.25):
        """
        Set the cooldown time between trigger captures.
        
        Args:
            cooldown_seconds: Minimum time between captures in seconds (default 0.25s)
        """
        self._cooldown_s = float(cooldown_seconds)
        print(f"DEBUG: [CameraStream] Trigger cooldown set to {self._cooldown_s}s")
    
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

    def cleanup(self):
        """
        Clean up camera resources and stop all operations.
        Safe to call multiple times - uses flag to prevent re-entry.
        Avoids threading hang by using timeouts and force-quit fallback.
        """
        # Guard against multiple cleanup calls (prevents double-deletion issues)
        if hasattr(self, '_cleanup_in_progress') and self._cleanup_in_progress:
            return
        
        try:
            self._cleanup_in_progress = True
            
            # Stop live capture if active (with timeout)
            if hasattr(self, 'is_live') and self.is_live:
                try:
                    self.stop_live()
                except Exception as e:
                    print(f"DEBUG: [CameraStream] Error stopping live: {e}")
            
            # Stop any live worker thread (force stop)
            if hasattr(self, '_live_worker') and self._live_worker:
                try:
                    if hasattr(self._live_worker, '_running'):
                        self._live_worker._running = False
                except Exception as e:
                    print(f"DEBUG: [CameraStream] Error stopping live worker: {e}")
            
            # Quit live thread with very short timeout to prevent hang
            if hasattr(self, '_live_thread') and self._live_thread:
                try:
                    if self._live_thread and self._live_thread.isRunning():
                        self._live_thread.quit()
                        # Short timeout - don't wait long for thread to finish
                        if not self._live_thread.wait(500):  # 500ms max wait
                            try:
                                # Note: terminate() is harsh but prevents hang
                                self._live_thread.terminate()
                                self._live_thread.wait(100)  # Very short final wait
                            except Exception:
                                pass
                except Exception as e:
                    print(f"DEBUG: [CameraStream] Error stopping live thread: {e}")
            
            # Stop timer if active (check if not already deleted)
            if hasattr(self, 'timer') and self.timer is not None:
                try:
                    # Check if Qt object is still valid before calling methods
                    self.timer.stop()
                except RuntimeError as e:
                    # Qt object already deleted - this is OK
                    if "wrapped C/C++ object" in str(e):
                        pass  # Already deleted by Qt
                    else:
                        print(f"DEBUG: [CameraStream] RuntimeError stopping timer: {e}")
                except Exception as e:
                    print(f"DEBUG: [CameraStream] Error stopping timer: {e}")
            
            # Close picamera2 if available (no blocking)
            if hasattr(self, 'picam2') and self.picam2 is not None:
                try:
                    if hasattr(self.picam2, 'stop') and getattr(self.picam2, 'started', False):
                        self.picam2.stop()
                except Exception as e:
                    print(f"DEBUG: [CameraStream] Error stopping picam2: {e}")
                
                try:
                    if hasattr(self.picam2, 'close'):
                        self.picam2.close()
                except Exception as e:
                    print(f"DEBUG: [CameraStream] Error closing picam2: {e}")
            
            print("DEBUG: [CameraStream] Cleanup completed successfully")
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Unexpected error during cleanup: {e}")
        finally:
            self._cleanup_in_progress = False


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

    def set_trigger_sent_time(self):
        """
        🎯 Mark when trigger signal was sent.
        Used to validate frame timestamps for synchronization.
        """
        self._trigger_sent_time = time.time()
        print(f"DEBUG: [CameraStream] Trigger sent time marked: {self._trigger_sent_time:.6f}")
    
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
