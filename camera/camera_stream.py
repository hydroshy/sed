"""
Camera stream module
Provides CameraStream class for interacting with camera hardware
"""

import os
import time
import traceback
import logging
from PyQt5.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QMessageBox
import numpy as np

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Try to import picamera2
try:
    from picamera2 import Picamera2
    has_picamera2 = True
    logger.debug("Successfully imported picamera2")
except ImportError:
    has_picamera2 = False
    logger.warning("Failed to import picamera2, will use stub implementation")

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
        # Track current pixel format selection for preview/display
        self._pixel_format = 'RGB888'
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
            logger.warning("picamera2 not available, using stub implementation")
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

    # -------------- Helper Methods (Quick Optimizations) ------
    def _is_picam2_ready(self) -> bool:
        """Check if picamera2 is available and initialized"""
        return (self.is_camera_available and 
                hasattr(self, 'picam2') and 
                self.picam2 is not None)

    def _is_camera_running(self) -> bool:
        """Check if camera is currently streaming/started"""
        return (self._is_picam2_ready() and 
                self.picam2.started)

    def _cleanup_live_worker(self) -> bool:
        """Stop live worker thread safely - consolidates duplicate cleanup code"""
        try:
            if getattr(self, '_live_worker', None) is not None:
                try:
                    self._live_worker.stop()
                except Exception as e:
                    logger.warning(f"Error stopping live worker: {e}")
                    
            if getattr(self, '_live_thread', None) is not None:
                try:
                    self._live_thread.quit()
                    self._live_thread.wait(1500)
                except Exception as e:
                    logger.warning(f"Error quitting live thread: {e}")
                    
            self._live_worker = None
            self._live_thread = None
            return True
        except Exception as e:
            logger.error(f"Error in cleanup_live_worker: {e}")
            return False

    def _get_camera_supported_sizes(self):
        """Query camera for actually supported frame sizes
        
        Returns dict with available sizes, or None if query fails
        """
        try:
            if not self._is_picam2_ready():
                return None
            
            # Try to get camera properties to find supported sizes
            props = self.picam2.camera_properties
            if props and "PixelArrayActiveAreas" in props:
                # Get the active area dimensions
                active_areas = props["PixelArrayActiveAreas"]
                if active_areas:
                    # Format is typically [[0, 0, width, height], ...]
                    width = active_areas[0][2]
                    height = active_areas[0][3]
                    logger.info(f"Camera active area: {width}×{height}")
                    return {"width": width, "height": height}
            
            logger.debug("Could not determine camera supported sizes from properties")
            return None
        except Exception as e:
            logger.debug(f"Error querying camera supported sizes: {e}")
            return None

    def _initialize_configs_with_sizes(self):
        """Initialize preview_config and still_config with appropriate frame sizes
        
        Strategy:
        1. Try preferred size (1280x720)
        2. If camera doesn't support, use its native supported sizes
        3. Falls back gracefully if camera doesn't support configured sizes
        
        Note: Picamera2 silently selects closest supported size if requested size
        isn't available. This method logs what was actually selected.
        """
        if not self._is_picam2_ready():
            return False
        
        try:
            # Try to query supported sizes from camera hardware
            supported_sizes = self.query_supported_sizes()
            
            # Determine preferred size: use largest supported, or fallback to 1440x1080
            if supported_sizes and len(supported_sizes) > 0:
                preferred_size = supported_sizes[0]  # Largest size (list is sorted descending)
                logger.info(f"📷 Using max supported size: {preferred_size} from {supported_sizes}")
            else:
                preferred_size = (1440, 1080)
                logger.warning(f"📷 Could not query supported sizes, using requested: {preferred_size}")
            
            # Initialize preview_config (LIVE mode)
            if not getattr(self, 'preview_config', None):
                try:
                    # Try with preferred size - picamera2 will handle if not supported
                    self.preview_config = self.picam2.create_preview_configuration(
                        main={"size": preferred_size, "format": "RGB888"}
                    )
                    actual_size = self.preview_config.get("main", {}).get("size")
                    
                    # Check if camera actually accepted our request
                    if actual_size and actual_size != preferred_size:
                        logger.warning(
                            f"Preview config: Requested {preferred_size}, "
                            f"camera using {actual_size} (camera may not support requested size)"
                        )
                    else:
                        logger.debug(f"Preview config: Successfully set to {actual_size}")
                        
                except Exception as e:
                    logger.warning(f"Cannot create preview with size {preferred_size}: {e}")
                    try:
                        # Fallback to format only, let camera choose size
                        self.preview_config = self.picam2.create_preview_configuration(
                            main={"format": "RGB888"}
                        )
                        actual_size = self.preview_config.get("main", {}).get("size")
                        logger.info(f"Preview config: Using camera default size: {actual_size}")
                    except Exception as e2:
                        logger.warning(f"Fallback preview config creation failed: {e2}")
                        # Final fallback to completely default
                        self.preview_config = self.picam2.create_preview_configuration()
                        actual_size = self.preview_config.get("main", {}).get("size")
                        logger.info(f"Preview config: Using bare default size: {actual_size}")
            
            # Initialize still_config (TRIGGER mode - attempt same size as LIVE)
            if not getattr(self, 'still_config', None):
                try:
                    # Try with preferred size - picamera2 will handle if not supported
                    self.still_config = self.picam2.create_still_configuration(
                        main={"size": preferred_size, "format": "RGB888"}
                    )
                    actual_size = self.still_config.get("main", {}).get("size")
                    
                    # Check if camera actually accepted our request
                    if actual_size and actual_size != preferred_size:
                        logger.warning(
                            f"Still config: Requested {preferred_size}, "
                            f"camera using {actual_size} (camera may not support requested size)"
                        )
                    else:
                        logger.debug(f"Still config: Successfully set to {actual_size}")
                        
                except Exception as e:
                    logger.warning(f"Cannot create still config with size {preferred_size}: {e}")
                    try:
                        # Fallback to default
                        self.still_config = self.picam2.create_still_configuration()
                        actual_size = self.still_config.get("main", {}).get("size")
                        logger.info(f"Still config: Using camera default size: {actual_size}")
                    except Exception as e2:
                        logger.error(f"Still config fallback creation failed: {e2}")
                        raise
            
            # Log frame size info at startup
            preview_size = self.preview_config.get("main", {}).get("size")
            still_size = self.still_config.get("main", {}).get("size")
            logger.info(f"Frame sizes - LIVE: {preview_size}, TRIGGER: {still_size}")
            
            # Query and log what sizes camera hardware actually supports
            supported_sizes = self.query_supported_sizes()
            
            # Warn if sizes don't match (original goal was to unify them)
            if preview_size and still_size and preview_size != still_size:
                logger.warning(
                    f"Frame size mismatch: LIVE uses {preview_size}, TRIGGER uses {still_size}. "
                    f"This camera may not support unified frame sizes."
                )
            
            return True
        except Exception as e:
            logger.error(f"Error initializing configs with sizes: {e}")
            return False

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
            logger.error(f"prime_and_lock error: {e}")
            return False
    
    def _safe_init_picamera(self):
        """Safe initialization of picamera2 with error handling"""
        if not has_picamera2:
            return False
            
        try:
            _ensure_xdg_runtime_dir()
            self.picam2 = Picamera2()
            logger.info("picamera2 initialized successfully")
            
            # Get available camera formats
            self._available_formats = []
            try:
                camera_properties = self.picam2.camera_properties
                if "pixel_formats" in camera_properties:
                    self._available_formats = camera_properties["pixel_formats"]
                    logger.debug(f"Available formats: {self._available_formats}")
                else:
                    # Fallback default formats if not found in properties
                    self._available_formats = ["BGGR10", "BGGR12", "BGGR8", "YUV420"]
                    logger.debug(f"Using default formats: {self._available_formats}")
            except Exception as format_error:
                logger.error(f"Error getting formats: {format_error}")
                # Fallback default formats on error
                self._available_formats = ["BGGR10", "BGGR12", "BGGR8", "YUV420"]
            
            # Create default configurations (prefer RGB888 for UI-friendly pipeline)
            # Use helper method to create configs with appropriate frame sizes
            self._initialize_configs_with_sizes()
            
            # After creating configs, immediately sync the actual formats that will be used
            # Picamera2 may have selected different formats in the config objects
            if hasattr(self, 'preview_config') and self.preview_config and "main" in self.preview_config:
                actual_preview_format = self.preview_config["main"].get("format", "RGB888")
                self._pixel_format = str(actual_preview_format)
                logger.debug(f"Preview config has format: {actual_preview_format}")
            
            # Verify configs exist, if not create fallback
            if not getattr(self, 'preview_config', None):
                try:
                    self.preview_config = self.picam2.create_preview_configuration(main={"format": "RGB888"})
                except Exception:
                    self.preview_config = self.picam2.create_preview_configuration()
            
            if not getattr(self, 'still_config', None):
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
            
            # Sync actual format that camera is using (may differ from what we requested)
            self._sync_actual_format_after_config()
            
            # Initialize is successful
            self.is_camera_available = True
            return True
            
        except Exception as e:
            logger.error(f"Error initializing camera: {e}")
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
                logger.info(f"Detected IMX camera: {camera_info['model']}")
                
                # Set specific size for IMX cameras if needed
                if "size" not in self.preview_config["main"]:
                    self.preview_config["main"]["size"] = (1456, 1080)
                    logger.debug("Fixed preview size to 1456x1080 for IMX camera")
            
        except Exception as e:
            logger.warning(f"Warning in fix_preview_size: {e}")
    
    def _add_missing_methods(self):
        """Add missing methods to support older versions of library"""
        # Ensure all required methods exist
        if not hasattr(CameraStream, 'start_live'):
            logger.debug("Adding start_live method to class")
            CameraStream.start_live = self._fallback_start_live
            
        if not hasattr(CameraStream, 'start_live_camera'):
            logger.debug("Adding start_live_camera method to class")
            CameraStream.start_live_camera = self._fallback_start_live_camera

    def _fallback_start_live(self):
        """Fallback implementation of start_live for CameraManager compatibility"""
        logger.debug("Fallback start_live called")
        try:
            if not self.is_camera_available:
                logger.warning("Camera not available in fallback start_live")
                return False
                
            # Ensure camera is initialized
            if self.picam2 is None:
                logger.debug("Reinitializing camera in fallback start_live")
                if not self._safe_init_picamera():
                    return False
                    
            # Start the camera
            if self.picam2 and not self.picam2.started:
                logger.debug("Starting camera in fallback start_live")
                self.picam2.start()
                
            # Start the timer
            if hasattr(self, 'timer') and not self.timer.isActive():
                logger.debug("Starting timer in fallback start_live")
                self.timer.start(100)  # 10 FPS
                
            self.is_live = True
            return True
            
        except Exception as e:
            logger.error(f"Error in fallback start_live: {e}")
            self.camera_error.emit(f"Failed to start camera: {str(e)}")
            return False
    
    def _fallback_start_live_camera(self):
        """Fallback implementation of start_live_camera for older versions"""
        logger.debug("Fallback start_live_camera called")
        return self._fallback_start_live()
        
    def _generate_test_frame(self):
        """Generate a test frame for testing without a real camera"""
        h, w = 1080, 1456
        # Create base gradients for channels
        r = np.tile(np.linspace(0, 255, w, dtype=np.uint8), (h, 1))
        g = np.tile(np.linspace(0, 255, h, dtype=np.uint8).reshape(h, 1), (1, w))
        b = np.full((h, w), int(time.time() * 10) % 255, dtype=np.uint8)

        pf = getattr(self, '_pixel_format', 'RGB888')
        if pf == 'BGR888':
            frame = np.dstack((b, g, r))
        elif pf == 'RGB888':
            frame = np.dstack((r, g, b))
        elif pf == 'XRGB8888' or pf == 'RGB888':
            # Assemble RGBA with opaque alpha; viewer will convert to RGB
            a = np.full((h, w), 255, dtype=np.uint8)
            frame = np.dstack((r, g, b, a))
        else:
            # For YUV-like formats in stub, just provide BGR-like visualization
            frame = np.dstack((b, g, r))
        
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
        logger.debug(f"set_trigger_mode({enabled}) called")
        
        try:
            value = "1" if enabled else "0"
            cmd = f"echo {value} | sudo -S tee /sys/module/imx296/parameters/trigger_mode"
            logger.debug(f"Setting IMX296 trigger_mode={value} with command: {cmd}")
            import subprocess
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            # Check if command succeeded
            if result.returncode == 0:
                logger.info(f"Successfully set IMX296 trigger_mode={value}")
                success_hw = True
            else:
                logger.error(f"Failed to set IMX296 trigger_mode: {result.stderr}")
                success_hw = False
                
                # Try alternative command without -S flag (assume sudo is already configured)
                try:
                    alt_cmd = f"echo {value} | sudo tee /sys/module/imx296/parameters/trigger_mode"
                    logger.debug(f"Trying alternative command (without -S): {alt_cmd}")
                    alt_result = subprocess.run(alt_cmd, shell=True, capture_output=True, text=True)
                    if alt_result.returncode == 0:
                        logger.info("Alternative command succeeded")
                        success_hw = True
                    else:
                        logger.error(f"Alternative command also failed: {alt_result.stderr}")
                        # Try pkexec as last resort
                        pkexec_cmd = f"pkexec bash -c 'echo {value} > /sys/module/imx296/parameters/trigger_mode'"
                        logger.debug(f"Trying pkexec command: {pkexec_cmd}")
                        pkexec_result = subprocess.run(pkexec_cmd, shell=True, capture_output=True, text=True)
                        if pkexec_result.returncode == 0:
                            logger.info("pkexec command succeeded")
                            success_hw = True
                        else:
                            logger.error(f"pkexec command failed: {pkexec_result.stderr}")
                except Exception as alt_e:
                    logger.error(f"Error with alternative commands: {alt_e}")
            
            # Verify the setting by reading back the value
            try:
                verify_cmd = "cat /sys/module/imx296/parameters/trigger_mode"
                verify_result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
                if verify_result.returncode == 0:
                    actual_value = verify_result.stdout.strip()
                    expected_value = value
                    logger.debug(f"Verification: expected={expected_value}, actual={actual_value}")
                    if actual_value == expected_value:
                        logger.info("Trigger mode setting verified successfully")
                        success_hw = True
                    else:
                        logger.warning("WARNING: Trigger mode verification failed!")
                        success_hw = False
                else:
                    logger.warning(f"Could not verify trigger mode: {verify_result.stderr}")
            except Exception as verify_e:
                logger.error(f"Error verifying trigger mode: {verify_e}")
                
        except Exception as e:
            logger.error(f"Error writing IMX296 trigger sysfs: {e}")
            success_hw = False

        # Always update internal state
        self.external_trigger_enabled = bool(enabled)
        self._last_sensor_ts = 0
        logger.debug(f"Internal state updated: external_trigger_enabled = {self.external_trigger_enabled}")
        
        if not self.picam2:
            logger.warning("No picam2 instance available, returning")
            return success_hw

        # Check if camera is currently running
        was_live = bool(getattr(self, 'is_live', False))
        logger.debug(f"Camera was running: {was_live}")
        
        if was_live:
            # Stop the camera before changing modes
            try:
                logger.debug("Stopping camera before mode change")
                if hasattr(self, 'stop_live'):
                    self.stop_live()
                elif hasattr(self.picam2, 'stop'):
                    self.picam2.stop()
            except Exception as e:
                logger.error(f"Error stopping camera: {e}")
            
            # Restart camera in appropriate mode
            try:
                if enabled:
                    logger.debug("Restarting camera in trigger mode")
                    # Use preview_config for trigger mode to get 1456x1080
                    # (still_config may not support 1456x1080 on this camera hardware)
                    try:
                        if hasattr(self, 'preview_config') and self.preview_config:
                            logger.debug("Using preview_config for trigger mode (should give 1456x1080)")
                            self.picam2.configure(self.preview_config)
                            logger.debug("Camera configured with trigger mode using preview_config")
                            
                            # Query actual size camera accepted
                            actual_size = self.get_actual_frame_size()
                            if actual_size:
                                logger.warning(f"⚠️  Trigger mode: camera accepted size: {actual_size}")
                        else:
                            logger.warning("No preview_config available, trying still_config fallback")
                            self.still_config = self.picam2.create_still_configuration(
                                main={"size": (1456, 1080), "format": "RGB888"}
                            )
                            logger.debug("Still config created for trigger mode (size 1456x1080)")
                            self.picam2.configure(self.still_config)
                            logger.debug("Camera configured with trigger mode")
                            
                            # Query actual size camera accepted
                            actual_size = self.get_actual_frame_size()
                            if actual_size:
                                logger.warning(f"⚠️  Requested 1456x1080 but camera accepted: {actual_size}")
                        
                    except Exception as config_e:
                        logger.warning(f"Failed to set trigger config, using default: {config_e}")
                        # Fallback to default still_config if size setting fails
                        if hasattr(self, 'still_config') and self.still_config:
                            logger.debug("Configuring with default still_config for trigger mode")
                            self.picam2.configure(self.still_config)
                    self.start_live()  # Keep trigger enabled
                else:
                    logger.debug("Restarting camera in live mode (no trigger)")
                    # Configure for preview if available
                    if hasattr(self, 'preview_config') and self.preview_config:
                        logger.debug("Configuring with preview_config for live mode")
                        # Ensure format is correct before configuring
                        self._ensure_preview_config_format()
                        self.picam2.configure(self.preview_config)
                    self.start_live()  # Trigger already disabled above
            except Exception as e:
                logger.error(f"Error restarting camera: {e}")
                success_hw = False

        return success_hw
        
    def process_frame(self):
        """Process a new frame from the camera"""
        if not self._is_picam2_ready():
            return
            
        try:
            # Get the latest frame
            frame = self.picam2.capture_array()
            
            # Check if the frame is valid
            if frame is None or frame.size == 0:
                logger.debug("Empty frame received")
                return
                
            # Store and emit the frame
            self.latest_frame = frame
            self.frame_ready.emit(frame)
        
        except Exception as e:
            logger.debug(f"Frame processing error: {e}")
            # Only emit error if it seems serious
            if "timeout" not in str(e).lower() and "closed" not in str(e).lower():
                self.camera_error.emit(f"Frame processing error: {str(e)}")
    
    def _ensure_preview_config_format(self):
        """Ensure preview_config and still_config have RGB888 format set correctly
        
        This is called before using any config to ensure the format
        doesn't get overridden by picamera2's defaults.
        """
        # Ensure preview_config format
        if not hasattr(self, 'preview_config') or self.preview_config is None:
            logger.debug("preview_config not initialized yet, will use default format")
            self._pixel_format = "RGB888"
        else:
            try:
                # Ensure main format is RGB888
                if "main" not in self.preview_config:
                    self.preview_config["main"] = {}
                
                current_format = self.preview_config["main"].get("format", "UNKNOWN")
                if current_format != "RGB888":
                    logger.debug(f"Updating preview_config format from {current_format} to RGB888")
                    self.preview_config["main"]["format"] = "RGB888"
                
                # Also update the internal tracking
                self._pixel_format = "RGB888"
                logger.debug(f"preview_config format ensured: RGB888")
                
            except Exception as e:
                logger.error(f"Error ensuring preview_config format: {e}")
        
        # Ensure still_config format too
        if hasattr(self, 'still_config') and self.still_config is not None:
            try:
                if "main" not in self.still_config:
                    self.still_config["main"] = {}
                
                current_format = self.still_config["main"].get("format", "UNKNOWN")
                if current_format != "RGB888":
                    logger.debug(f"Updating still_config format from {current_format} to RGB888")
                    self.still_config["main"]["format"] = "RGB888"
                
                logger.debug(f"still_config format ensured: RGB888")
                
            except Exception as e:
                logger.error(f"Error ensuring still_config format: {e}")
    
    def _sync_actual_format_after_config(self):
        """After configuring camera, read and sync the actual format used.
        
        Picamera2 may select a different format than requested if the requested
        format is not available. This method queries what was actually set.
        """
        try:
            if not self._is_picam2_ready():
                logger.debug("Camera not ready, skipping format sync")
                return
            
            logger.debug("Attempting to sync actual format from camera...")
            
            # Try to get the camera's actual configuration that was applied
            # Note: camera_config is a property/attribute that returns a dict, not a callable method
            try:
                if hasattr(self.picam2, 'camera_config'):
                    # camera_config is NOT a method, it's a property/dict
                    current_config = self.picam2.camera_config
                    logger.debug(f"Got camera_config: type={type(current_config)}, keys={current_config.keys() if isinstance(current_config, dict) else 'N/A'}")
                    
                    if isinstance(current_config, dict) and "main" in current_config:
                        actual_format = current_config["main"].get("format", "UNKNOWN")
                        logger.debug(f"Actual format from camera.camera_config: {actual_format}")
                        
                        # Update our internal tracking to match reality
                        if hasattr(self, 'preview_config') and self.preview_config:
                            if "main" not in self.preview_config:
                                self.preview_config["main"] = {}
                            self.preview_config["main"]["format"] = actual_format
                        self._pixel_format = str(actual_format)
                        
                        logger.info(f"Synced actual camera format: {actual_format}")
                        return
            except Exception as e:
                logger.debug(f"Could not get format from camera_config: {e}")
            
            # Fallback: use what we have in preview_config
            if hasattr(self, 'preview_config') and self.preview_config and "main" in self.preview_config:
                actual_format = self.preview_config["main"].get("format", "RGB888")
                self._pixel_format = str(actual_format)
                logger.warning(f"Using fallback format from preview_config: {actual_format}")
                    
        except Exception as e:
            logger.error(f"Error syncing actual format: {e}")

    def start_online_camera(self):

        """Start online camera (live view) from camera or stub generator when hardware unavailable
        
        This is the main method called by the onlineCamera button.
        Starts continuous camera streaming in current mode (LIVE or TRIGGER).
        """
        logger.debug("start_online_camera called")
        
        # Handle stub mode (no picamera2): start test-frame timer instead of failing
        if not self.is_camera_available:
            logger.debug("Camera not available -> starting stub live timer")
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
                logger.error(f"Error starting stub live: {e}")
                return False
            
        try:
            # Check current trigger mode to decide which config to use
            logger.debug(f"Current trigger mode: {self.external_trigger_enabled}")
            
            # Ensure camera is initialized
            if not self._is_picam2_ready():
                logger.debug("Reinitializing camera")
                if not self._safe_init_picamera():
                    logger.error("Failed to initialize camera")
                    return False
            
            # If camera is already started, stop it first
            if self._is_camera_running():
                logger.debug("Camera already started, stopping first")
                self.picam2.stop()
            
            # Choose config based on trigger mode
            if self.external_trigger_enabled:
                logger.debug("Trigger mode ENABLED - using still_config for 1456x1080")
                logger.debug(f"still_config exists: {self.still_config is not None}")
                if self.still_config:
                    still_size = self.still_config.get("main", {}).get("size")
                    logger.debug(f"still_config size: {still_size}")
                config_to_use = self.still_config
                mode_name = "Trigger"
            else:
                logger.debug("Trigger mode DISABLED - using preview_config")
                config_to_use = self.preview_config
                mode_name = "Live"
            
            # Ensure the selected config has correct format
            self._ensure_preview_config_format()
            
            # Configure with selected config
            logger.debug(f"Configuring camera with {mode_name} mode config")
            self.picam2.configure(config_to_use)
            logger.debug(f"Camera configured for {mode_name} mode")
            
            # Query actual size camera accepted
            actual_size = self.get_actual_frame_size()
            if actual_size:
                logger.info(f"📷 {mode_name} mode - Requested 1456x1080, camera accepted: {actual_size}")
            
            # Sync the actual format that picamera2 applied (may differ from requested)
            self._sync_actual_format_after_config()
            
            # Log what format we're actually using
            actual_fmt = self.get_actual_camera_format()
            logger.info(f"Actual format after configuration: {actual_fmt}")
            
            # Start the camera
            logger.debug(f"Starting camera in {mode_name} mode (Job: {'ON' if self.job_enabled else 'OFF'})")
            if self.job_enabled:
                self.picam2.start()
            else:
                self.picam2.start(show_preview=False)
            
            # Start threaded live capturing or fallback timer
            if getattr(self, '_use_threaded_live', False):
                logger.debug(f"Starting threaded live worker at {self._target_fps} FPS")
                if hasattr(self, 'timer') and self.timer.isActive():
                    self.timer.stop()
                self._start_live_worker()
            else:
                if hasattr(self, 'timer') and not self.timer.isActive():
                    interval = int(1000.0 / max(1.0, float(self._target_fps)))
                    self.timer.start(interval)
            
            self.is_live = True
            logger.info(f"Live view started successfully in {mode_name} mode")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting live view: {e}")
            self.camera_error.emit(f"Failed to start camera: {str(e)}")
            self.is_live = False
            return False
    
    def start_live(self):
        """Backward compatibility alias for start_online_camera()
        
        This method is kept for backward compatibility with existing code
        that calls start_live(). New code should use start_online_camera().
        """
        logger.debug("start_live() called (backward compatibility alias)")
        return self.start_online_camera()

    def start_live_no_trigger(self):
        """Start live view from camera with hardware trigger explicitly disabled"""
        logger.debug("start_live_no_trigger called")
        
        # First disable hardware trigger if it's enabled
        if hasattr(self, 'external_trigger_enabled') and self.external_trigger_enabled:
            logger.debug("Disabling hardware trigger for live mode")
            self.set_trigger_mode(False)
        
        # Then start live view normally
        return self.start_live()
    
    def stop_live(self):
        """Stop live view"""
        logger.debug("stop_live called")

        try:
            # Ensure any pending requests are cancelled to unblock capture
            try:
                if self._is_picam2_ready() and hasattr(self.picam2, 'cancel_all_and_flush'):
                    self.picam2.cancel_all_and_flush()
            except Exception:
                pass

            # Stop the timer
            if hasattr(self, 'timer') and self.timer.isActive():
                self.timer.stop()
            
            # Stop threaded worker if running
            self._cleanup_live_worker()
            
            # Stop the camera if it's running
            if self._is_camera_running():
                logger.debug("Stopping camera")
                self.picam2.stop()
            
            # Clean up frame to prevent memory leak
            self.latest_frame = None
            
            self.is_live = False
            logger.info("Live view stopped")
            
            return True
            
        except Exception as e:
            logger.error(f"Error stopping live view: {e}")
            self.is_live = False
            return False

    def cancel_all_and_flush(self):
        """Cancel pending camera requests and flush pipeline (Picamera2 helper)."""
        try:
            if self._is_picam2_ready() and hasattr(self.picam2, 'cancel_all_and_flush'):
                self.picam2.cancel_all_and_flush()
                logger.debug("cancel_all_and_flush executed")
                return True
            return False
        except Exception as e:
            logger.error(f"cancel_all_and_flush error: {e}")
            return False

    def cancel_and_stop_live(self):
        """Preferred safe stop: cancel pending requests then stop live view and worker."""
        self.cancel_all_and_flush()
        return self.stop_live()

    def _start_live_worker(self):
        """Create and start a background worker for live frames."""
        # Stop any existing worker first
        self._cleanup_live_worker()

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
        logger.debug(f"Setting exposure to {exposure_us}μs")
        
        # Store the exposure value
        self.current_exposure = int(exposure_us)
        
        if not self.is_camera_available or not hasattr(self, 'picam2') or self.picam2 is None:
            logger.warning("Camera not available for exposure setting")
            return False
            
        try:
            # Apply to current configuration
            controls = {}
            controls["ExposureTime"] = self.current_exposure
            controls["AeEnable"] = False  # Manual exposure
            
            # Apply directly if camera is running
            if self.picam2.started:
                logger.debug(f"Applying exposure {self.current_exposure}μs to running camera")
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
            
            logger.debug(f"Exposure set to {self.current_exposure}μs")
            return True
            
        except Exception as e:
            logger.error(f"Error setting exposure: {e}")
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
            logger.error(f"Error in set_auto_exposure: {e}")
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
            logger.info(f"Analogue gain set to {g}")
            return True
        except Exception as e:
            logger.error(f"Error setting gain: {e}")
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
                logger.warning("Camera not available for set_frame_size")
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
            logger.info(f"Frame size set to {width}x{height}")
            return True
        except Exception as e:
            logger.error(f"Error setting frame size: {e}")
            return False

    def set_format(self, pixel_format):
        """Set preview pixel format (e.g., 'RGB888', 'BGR888').
        
        This updates the camera configuration to use the specified format
        and preserves the current frame size settings.
        """
        try:
            # Map our format strings to picamera2 actual formats
            # Note: picamera2 uses "RGB888", "BGR888", "XBGR8888", "XRGB8888" as format names
            # However, the actual format that gets applied depends on camera capabilities
            format_map = {
                'RGB888': 'RGB888',        # RGB888 -> RGB888 (standard RGB format for picamera2)
                'BGR888': 'BGR888',        # BGR888 -> BGR888 (standard BGR format for picamera2)
                'XRGB8888': 'RGB888',      # XRGB8888 -> RGB888 (map to RGB888 for compatibility)
                'XBGR8888': 'BGR888',      # XBGR8888 -> BGR888 (map to BGR888 for compatibility)
                'YUV420': 'YUV420',        # YUV420 -> YUV420
                'NV12': 'NV12',            # NV12 -> NV12
            }
            
            # Persist our format string (not actual hardware format)
            self._pixel_format = str(pixel_format)
            
            # Get actual hardware format for picamera2
            actual_format = format_map.get(str(pixel_format), 'XRGB8888')
            
            if not self.is_camera_available or not hasattr(self, 'picam2') or self.picam2 is None:
                # Stub path: just ack success
                logger.debug(f"(stub) set_format -> {self._pixel_format} (actual: {actual_format})")
                return True
            
            # Stop camera if running to reconfigure safely
            was_running = bool(self.picam2.started)
            if was_running:
                logger.debug(f"Camera running, stopping to apply format change...")
                self.picam2.stop()
            
            # Update preview config with new format (keep existing size)
            if hasattr(self, 'preview_config') and self.preview_config and "main" in self.preview_config:
                # Keep existing main config but update format
                self.preview_config["main"]["format"] = actual_format
                logger.debug(f"Updated preview_config format to {actual_format}, size: {self.preview_config['main'].get('size')}")
            else:
                # Create new preview config with format
                try:
                    self.preview_config = self.picam2.create_preview_configuration(main={"format": actual_format})
                    logger.debug(f"Created new preview_config with format {actual_format}")
                except Exception as e:
                    logger.error(f"Could not set preview format to {actual_format}: {e}")
                    self.preview_config = self.picam2.create_preview_configuration()
            
            # Update still config with new format (keep existing size) 
            if hasattr(self, 'still_config') and self.still_config and "main" in self.still_config:
                # Keep existing main config but update format
                self.still_config["main"]["format"] = actual_format
                logger.debug(f"Updated still_config format to {actual_format}, size: {self.still_config['main'].get('size')}")
            else:
                # Create new still config with format
                try:
                    self.still_config = self.picam2.create_still_configuration(main={"format": actual_format})
                    logger.debug(f"Created new still_config with format {actual_format}")
                except Exception as e:
                    logger.error(f"Could not set still format to {actual_format}: {e}")
                    self.still_config = self.picam2.create_still_configuration()
            
            # Reconfigure camera with new settings
            # Use preview_config since camera is typically in live/preview mode
            try:
                self.picam2.configure(self.preview_config)
                logger.debug(f"Camera reconfigured with format {actual_format}")
            except Exception as e:
                logger.error(f"Error reconfiguring camera: {e}")
                return False
            
            # Restart camera if it was running
            if was_running:
                try:
                    self.picam2.start(show_preview=False)
                    logger.debug(f"Camera restarted after format change")
                except Exception as e:
                    logger.error(f"Error restarting camera: {e}")
                    return False
                
            logger.info(f"Pixel format set to {pixel_format} (actual hardware format: {actual_format})")
            return True
        except Exception as e:
            logger.error(f"Error setting format: {e}")
            return False

    def get_pixel_format(self) -> str:
        """Return current preview pixel format string (e.g., 'RGB888').
        
        Note: Returns the requested format, not necessarily what the camera
        is actually capturing (the camera may select a different format
        if the requested one is not supported).
        """
        try:
            return str(self._pixel_format)
        except Exception:
            return 'RGB888'
    
    def get_actual_camera_format(self) -> str:
        """Get the actual format the camera is using from picamera2 config.
        
        This may differ from get_pixel_format() if the requested format
        is not supported by the camera hardware.
        
        Always reads from the ACTUAL camera configuration, not just our local variable.
        """
        try:
            if not self._is_picam2_ready():
                return self.get_pixel_format()
            
            # Try to read from the actual camera configuration first
            try:
                if hasattr(self.picam2, 'camera_config'):
                    # camera_config is a property that returns the actual applied config
                    camera_cfg = self.picam2.camera_config
                    if isinstance(camera_cfg, dict) and "main" in camera_cfg:
                        actual_format = camera_cfg["main"].get("format", "UNKNOWN")
                        logger.debug(f"Actual camera format from picam2.camera_config: {actual_format}")
                        return str(actual_format)
            except Exception as e:
                logger.debug(f"Could not read from camera_config: {e}")
            
            # Fallback to our preview_config
            if hasattr(self, 'preview_config') and self.preview_config:
                if "main" in self.preview_config:
                    actual_format = self.preview_config["main"].get("format", "XRGB8888")
                    logger.debug(f"Actual camera format from preview_config: {actual_format}")
                    return str(actual_format)
            
            return self.get_pixel_format()
        except Exception as e:
            logger.debug(f"Error getting actual camera format: {e}")
            return self.get_pixel_format()

    def get_actual_frame_size(self):
        """Query actual frame size from camera_config after configuration"""
        try:
            if hasattr(self.picam2, 'camera_config'):
                camera_cfg = self.picam2.camera_config
                if isinstance(camera_cfg, dict) and "main" in camera_cfg:
                    actual_size = camera_cfg["main"].get("size", None)
                    actual_format = camera_cfg["main"].get("format", "UNKNOWN")
                    logger.info(f"📷 Actual camera config - size: {actual_size}, format: {actual_format}")
                    return actual_size
        except Exception as e:
            logger.debug(f"Could not read actual frame size from camera_config: {e}")
        return None

    def query_supported_sizes(self):
        """Query what frame sizes this camera hardware actually supports"""
        try:
            if not hasattr(self.picam2, 'sensor_modes'):
                logger.warning("Camera doesn't have sensor_modes attribute")
                return None
            
            sensor_modes = self.picam2.sensor_modes
            logger.info(f"📷 Camera sensor modes: {sensor_modes}")
            
            if sensor_modes:
                # Extract unique sizes from sensor modes
                sizes = set()
                for mode in sensor_modes:
                    if hasattr(mode, 'size'):
                        sizes.add(mode.size)
                
                logger.info(f"📷 Supported camera sizes: {sorted(sizes, reverse=True)}")
                return sorted(sizes, reverse=True)  # Largest first
        except Exception as e:
            logger.debug(f"Could not query sensor modes: {e}")
        return None

    def set_target_fps(self, fps):
        """Set target FPS for live streaming (threaded or timer)."""
        try:
            self._target_fps = float(fps)
            if hasattr(self, 'timer') and self.timer.isActive() and not getattr(self, '_use_threaded_live', False):
                self.timer.stop()
                interval = int(1000.0 / max(1.0, self._target_fps))
                self.timer.start(interval)
            logger.info(f"Target FPS set to {self._target_fps}")
            return True
        except Exception as e:
            logger.error(f"Error setting target FPS: {e}")
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
            logger.debug("trigger_capture called")
            
            if not self.is_camera_available:
                logger.warning("Camera not available")
                # Emit a test frame for testing without camera
                import numpy as np
                test_frame = np.zeros((1080, 1440, 3), dtype=np.uint8)
                self.frame_ready.emit(test_frame)
                return
                
            # Ensure camera is initialized
            if not hasattr(self, 'picam2') or self.picam2 is None:
                logger.debug("Camera not initialized, reinitializing...")
                if not self._safe_init_picamera():
                    logger.error("Camera reinitialization failed")
                    return
                logger.info("Camera reinitialized for trigger capture")
                
            # Remember current state
            was_live = self.is_live
            logger.debug(f"was_live: {was_live}")
            
            # Stop current capture if running
            if was_live or (self.picam2 and self.picam2.started):
                logger.debug("Stopping current capture")
                if self.picam2:
                    self.picam2.stop()
            
            # Configure for still capture
            logger.debug("Configuring for still capture")
            if not hasattr(self, 'still_config') or not self.still_config:
                # Create still config if not exists
                self.still_config = self.picam2.create_still_configuration()
                logger.debug("Created still config")
            
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
            
            logger.debug(f"Still config exposure: {self.current_exposure}μs")
            
            # Configure camera with error handling
            try:
                self.picam2.configure(self.still_config)
                logger.info("Still configuration successful")
            except Exception as config_error:
                logger.error(f"Still config failed: {config_error}")
                # Fallback to simpler configuration
                simple_config = self.picam2.create_still_configuration()
                simple_config["controls"] = {
                    "ExposureTime": self.current_exposure,
                    "AeEnable": False,
                    "NoiseReductionMode": 3  # Minimal to avoid TDN error
                }
                self.picam2.configure(simple_config)
                logger.debug("Fallback configuration applied")
            
            # Start and capture
            logger.debug(f"Starting still capture (Job: {'ON' if self.job_enabled else 'OFF'})")
            # Always start camera for trigger capture, but control preview based on job setting
            try:
                self.picam2.start(show_preview=False)  # Always use safe mode for trigger
                logger.info("Camera started successfully for still capture")
            except Exception as start_error:
                logger.error(f"Camera start failed: {start_error}")
                # Try to recover
                if "TDN" in str(start_error):
                    logger.debug("TDN error detected, trying simpler config")
                    self.picam2.stop()
                    # Ultra-simple config to avoid TDN issues
                    ultra_simple = self.picam2.create_still_configuration()
                    ultra_simple["controls"] = {"ExposureTime": self.current_exposure, "AeEnable": False}
                    self.picam2.configure(ultra_simple)
                    self.picam2.start(show_preview=False)
                else:
                    raise start_error
            
            logger.debug("Capturing frame")
            # Trigger capture ALWAYS works, but with different handling based on job setting
            try:
                frame = self.picam2.capture_array()
                if frame is None:
                    logger.warning("No frame captured, retrying...")
                    # Retry once
                    frame = self.picam2.capture_array()
            except Exception as capture_error:
                logger.error(f"Capture error: {capture_error}")
                frame = None
            
            if frame is not None:
                logger.debug(f"Frame captured: {frame.shape}")
                self.latest_frame = frame
                self.frame_ready.emit(frame)
            else:
                logger.warning("No frame captured")
            
            # Stop still capture
            logger.debug("Stopping still capture")
            if not self.job_enabled:
                # Force close to avoid job execution on stop
                self.picam2.close()
                # Reinitialize for next operation
                if not self._safe_init_picamera():
                    logger.error("Camera reinitialization failed after still capture")
                else:
                    logger.info("Camera reinitialized after still capture")
            else:
                self.picam2.stop()
            
            # Restore preview if was live
            if was_live:
                logger.debug("Restoring live preview")
                if self.picam2:
                    self.picam2.configure(self.preview_config)
                    if self.job_enabled:
                        self.picam2.start()
                    else:
                        self.picam2.start(show_preview=False)
            else:
                logger.debug("Not restoring live (was not live)")
                
            logger.info("trigger_capture completed successfully")
            
        except Exception as e:
            logger.error(f"Error in trigger_capture: {e}")
            # Try to recover by reconfiguring preview
            try:
                if self.is_camera_available and hasattr(self, 'picam2') and self.picam2:
                    self.picam2.stop()
                    self.picam2.configure(self.preview_config)
                    if was_live:
                        self.picam2.start()
            except Exception as recovery_error:
                logger.error(f"Recovery failed: {recovery_error}")
    
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
            logger.debug("trigger_capture_async called")
            
            if not self.is_camera_available:
                logger.warning("Camera not available for async capture")
                # Emit a test frame
                import numpy as np
                test_frame = np.zeros((1080, 1440, 3), dtype=np.uint8)
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
            logger.error(f"Error in trigger_capture_async: {e}")
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
        logger.debug(f"Setting job processing: {enabled}")
        
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
            logger.error(f"CaptureWorker error: {e}")
        finally:
            # Signal that we're done
            self.finished.emit()
