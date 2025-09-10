"""
Camera Tool cho hệ thống SED
"""
import logging
import numpy as np
import cv2
import os
import subprocess
from typing import Dict, Any, Tuple, Optional, List, Union
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread, QMutex, QMutexLocker

from tools.base_tool import BaseTool, ToolConfig

logger = logging.getLogger(__name__)

try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False
    logger.warning("PiCamera2 không khả dụng. Sẽ sử dụng camera mô phỏng.")

class CameraTool(BaseTool):
    SUPPORTED_FORMATS = ["RGB888", "BGR888", "XRGB8888", "YUV420", "NV12"]
    """
    Công cụ quản lý camera, cung cấp hình ảnh đầu vào cho pipeline
    """
    
    def __init__(self, name: str = "Camera Source", config: Optional[Union[Dict[str, Any], ToolConfig]] = None, tool_id: Optional[int] = None):
        """
        Khởi tạo Camera Tool
        
        Args:
            name: Tên hiển thị của công cụ
            config: Cấu hình của công cụ
            tool_id: ID của công cụ trong job
        """
        super().__init__(name, config, tool_id)
        
        # Ensure name is always "Camera Source" for proper detection
        self.name = "Camera Source"
        self.display_name = "Camera Source"
        
        # Log thông tin công cụ cho debug
        logger.info(f"CameraTool initialized: name={self.name}, display_name={self.display_name}, tool_id={self.tool_id}")
        
        # Config is now always a dictionary due to BaseTool handling
        if self.config is None:
            self.config = {}
            
        # Đảm bảo các giá trị cần thiết tồn tại trong config
        if "rotation_angle" not in self.config:
            self.config["rotation_angle"] = 0
        if "exposure" not in self.config:
            self.config["exposure"] = 10000  # 10ms mặc định
        if "gain" not in self.config:
            self.config["gain"] = 1.0
        if "ev" not in self.config:
            self.config["ev"] = 0.0
        if "auto_exposure" not in self.config:
            self.config["auto_exposure"] = True
        if "camera_mode" not in self.config:
            self.config["camera_mode"] = "live"  # "live" hoặc "trigger"
        if "enable_external_trigger" not in self.config:
            self.config["enable_external_trigger"] = False
            
        # Log thông tin cấu hình
        logger.info(
            f"Camera Tool created with config: rotation_angle={self.config['rotation_angle']}, "
            f"exposure={self.config['exposure']}, gain={self.config['gain']}, "
            f"auto_exposure={self.config.get('auto_exposure', True)}, "
            f"auto_white_balance={self.config.get('auto_white_balance', True)}, "
            f"camera_mode={self.config['camera_mode']}, "
            f"enable_external_trigger={self.config['enable_external_trigger']}"
        )
        
        # Don't initialize separate camera instance - this conflicts with main camera stream
        # CameraTool just stores configuration that will be applied to main camera_manager
        self.is_camera_available = False
        self.picam2 = None
        self.is_live = False  # Add is_live attribute for job manager compatibility
        
        # Camera configuration (stored for reference)
        self.current_exposure = self.config.get("exposure", 10000)
        self.current_format = self.config.get("format", "RGB888")
        self.frame_size = self.config.get("frame_size", (1440, 1080))
        self.target_fps = self.config.get("target_fps", 10.0)
        
        # Reference to the main camera manager - will be set by main window
        self.camera_manager = None
        
        # Trigger mode properties
        self.trigger_ready = False  # Flag to indicate if camera is ready for triggering
        self.last_trigger_frame = None  # Store the last triggered frame
        self.is_gs_camera = self._check_if_gs_camera()  # Check if we have a global shutter camera
        
        # Don't start any timers or camera operations
        logger.info("CameraTool created as configuration holder - no separate camera instance")

    # ==== AE/AWB convenience APIs for UI buttons ====
    def set_auto_ae(self, enabled: bool) -> bool:
        """Enable/disable Auto-Exposure and apply immediately."""
        self.config["auto_exposure"] = bool(enabled)
        if hasattr(self, 'camera_manager') and self.camera_manager:
            if enabled and hasattr(self.camera_manager, 'set_auto_exposure_mode'):
                self.camera_manager.set_auto_exposure_mode()
            elif not enabled and hasattr(self.camera_manager, 'set_manual_exposure_mode'):
                self.camera_manager.set_manual_exposure_mode()
        return True

    def set_auto_awb(self, enabled: bool) -> bool:
        """Enable/disable Auto-White-Balance and apply immediately (async)."""
        self.config["auto_white_balance"] = bool(enabled)
        return self._apply_awb_to_camera_manager()

    def set_colour_gains(self, r_gain: float, b_gain: float) -> bool:
        """Set manual AWB gains (R, B) and apply immediately when AWB is manual."""
        try:
            self.config["colour_gain_r"] = float(r_gain)
            self.config["colour_gain_b"] = float(b_gain)
            self.config["colour_gains"] = (float(r_gain), float(b_gain))
        except Exception:
            pass
        if not self.config.get("auto_white_balance", True):
            return self._apply_awb_to_camera_manager()
        return True

    def _check_if_gs_camera(self) -> bool:
        """
        Kiểm tra xem có phải camera global shutter (IMX296) không
        
        Returns:
            True nếu là camera IMX296, False nếu không
        """
        try:
            # Kiểm tra xem module imx296 có tồn tại không
            return os.path.exists('/sys/module/imx296')
        except Exception as e:
            logger.warning(f"Không thể kiểm tra loại camera: {e}")
            return False
    
    def setup_config(self) -> None:
        """Thiết lập cấu hình mặc định cho Camera Tool"""
        # Camera settings
        self.config.set_default("frame_size", (1440, 1080))
        self.config.set_default("format", "RGB888")
        try:
            self.config.set_validator("format", lambda v: str(v) in CameraTool.SUPPORTED_FORMATS)
        except Exception:
            pass
        self.config.set_default("exposure_time", 10000)  # in microseconds
        self.config.set_default("frame_rate", 60)
        # Defaults: UI yêu cầu mặc định Auto cho AE và AWB
        self.config.set_default("auto_exposure", True)
        self.config.set_default("auto_white_balance", True)
        self.config.set_default("color_temperature", 5500)
        self.config.set_default("analogue_gain", 1.0)
        self.config.set_default("rotation", 0)  # 0, 90, 180, 270
        self.config.set_default("flip_horizontal", False)
        self.config.set_default("flip_vertical", False)
        
        # Additional camera settings for Camera Source tool
        self.config.set_default("exposure", 10000)  # Default exposure in microseconds
        self.config.set_default("gain", 1.0)        # Default gain
        self.config.set_default("ev", 0.0)          # Default EV
        self.config.set_default("rotation_angle", 0)  # Camera rotation angle
        # Auto exposure mode (new key)
        self.config.set_default("auto_exposure", True)
        # AWB manual gains mặc định (khi user chuyển sang manual)
        self.config.set_default("colour_gain_r", 1.8)
        self.config.set_default("colour_gain_b", 1.8)
        
        # Trigger mode settings
        self.config.set_default("camera_mode", "live")  # "live" hoặc "trigger"
        self.config.set_default("enable_external_trigger", False)  # Sử dụng trigger ngoài cho IMX296
        self.config.set_default("trigger_delay_ms", 0)  # Độ trễ sau khi nhận trigger (ms)
        
        # UI settings
        self.config.set_default("show_fps", True)
        self.config.set_default("show_histogram", False)
        self.config.set_default("show_exposure_warning", True)
        
    def set_camera_mode(self, mode: str) -> bool:
        """
        Thiết lập chế độ camera (live hoặc trigger)
        
        Args:
            mode: Chế độ camera ("live" hoặc "trigger")
            
        Returns:
            True nếu thành công, False nếu không
        """
        if mode not in ["live", "trigger", "single"]:
            logger.error(f"Chế độ camera không hợp lệ: {mode}")
            return False
            
        # Cập nhật cấu hình trong CameraTool
        old_mode = self.config.get("camera_mode", "live")
        self.config["camera_mode"] = mode
        logger.info(f"CameraTool: Camera mode changed from {old_mode} to {mode}")
        
        # Auto-enable external trigger for IMX296 when switching to trigger mode
        if mode == "trigger" and self.is_gs_camera:
            self.config["enable_external_trigger"] = True
            print(f"DEBUG: [CameraTool] Auto-enabled external trigger for IMX296 in trigger mode")
        elif mode == "live":
            self.config["enable_external_trigger"] = False
            print(f"DEBUG: [CameraTool] Disabled external trigger for live mode")
        
        # Delegate to CameraManager for hardware control ONLY
        if hasattr(self, 'camera_manager') and self.camera_manager:
            print(f"DEBUG: [CameraTool] Delegating hardware control to CameraManager")
            
            # Update CameraManager's current_mode to stay in sync
            self.camera_manager.current_mode = mode
            
            # Set hardware trigger mode based on camera mode
            if mode == "trigger":
                success = self.camera_manager.set_trigger_mode(True)
            else:  # live or single
                success = self.camera_manager.set_trigger_mode(False)
            
            # Update CameraManager UI to reflect the mode change
            if hasattr(self.camera_manager, 'update_camera_mode_ui'):
                self.camera_manager.update_camera_mode_ui()
            
            # Apply other camera settings
            self._apply_config_to_camera_manager()
            
            return success
        else:
            print(f"DEBUG: [CameraTool] No camera_manager reference, config stored only")
            return True
    
    def get_camera_mode(self) -> str:
        """
        Lấy chế độ camera hiện tại
        
        Returns:
            Chế độ camera hiện tại ("live" hoặc "trigger")
        """
        return self.config.get("camera_mode", "live")
    
    def is_trigger_mode(self) -> bool:
        """
        Kiểm tra xem có đang ở chế độ trigger không
        
        Returns:
            True nếu đang ở chế độ trigger, False nếu không
        """
        return self.get_camera_mode() == "trigger"
    
    def is_live_mode(self) -> bool:
        """
        Kiểm tra xem có đang ở chế độ live không
        
        Returns:
            True nếu đang ở chế độ live, False nếu không
        """
        return self.get_camera_mode() == "live"
    
    def _apply_config_to_camera_manager(self):
        """Apply current config to camera manager"""
        if not hasattr(self, 'camera_manager') or not self.camera_manager:
            return
            
        print(f"DEBUG: [CameraTool] Applying config to camera_manager")
        
        # Apply frame size and format first to avoid reconfigure flicker
        if "frame_size" in self.config and hasattr(self.camera_manager, 'camera_stream') \
           and self.camera_manager.camera_stream and hasattr(self.camera_manager.camera_stream, 'set_frame_size'):
            try:
                w, h = self.config["frame_size"]
                self.camera_manager.camera_stream.set_frame_size(w, h)
            except Exception as e:
                logger.warning(f"Could not apply frame size: {e}")
        if "format" in self.config and hasattr(self.camera_manager, 'camera_stream') \
           and self.camera_manager.camera_stream and hasattr(self.camera_manager.camera_stream, 'set_format'):
            try:
                fmt = str(self.config["format"]) if "format" in self.config else "RGB888"
                if fmt not in CameraTool.SUPPORTED_FORMATS:
                    logger.warning(f"Unsupported pixel format '{fmt}', falling back to 'RGB888'")
                    fmt = "RGB888"
                    try:
                        self.config.set("format", fmt)
                    except Exception:
                        pass
                self.current_format = fmt
                self.camera_manager.camera_stream.set_format(fmt)
            except Exception as e:
                logger.warning(f"Could not apply pixel format: {e}")
        if "target_fps" in self.config and hasattr(self.camera_manager, 'camera_stream') \
           and self.camera_manager.camera_stream and hasattr(self.camera_manager.camera_stream, 'set_target_fps'):
            try:
                self.camera_manager.camera_stream.set_target_fps(self.config["target_fps"])
            except Exception as e:
                logger.warning(f"Could not apply target FPS: {e}")

        # Apply exposure settings
        if "exposure" in self.config and hasattr(self.camera_manager, 'set_exposure_value'):
            self.camera_manager.set_exposure_value(self.config["exposure"])
            
        # Apply gain settings  
        if "gain" in self.config and hasattr(self.camera_manager, 'set_gain_value'):
            self.camera_manager.set_gain_value(self.config["gain"])
            
        # Apply EV settings
        if "ev" in self.config and hasattr(self.camera_manager, 'set_ev_value'):
            self.camera_manager.set_ev_value(self.config["ev"])
            
        # Apply auto exposure mode (new key only)
        if "auto_exposure" in self.config:
            if bool(self.config["auto_exposure"]):
                if hasattr(self.camera_manager, 'set_auto_exposure_mode'):
                    self.camera_manager.set_auto_exposure_mode()
            else:
                if hasattr(self.camera_manager, 'set_manual_exposure_mode'):
                    self.camera_manager.set_manual_exposure_mode()

        # Apply AWB settings (auto/manual + gains)
        try:
            awb_auto = None
            if "auto_white_balance" in self.config:
                awb_auto = bool(self.config.get("auto_white_balance", True))
            # When switching to manual AWB, also apply current gains
            if awb_auto is not None or any(k in self.config for k in ("colour_gain_r", "colour_gain_b", "colour_gains", "color_gains")):
                self._apply_awb_to_camera_manager()
        except Exception as e:
            logger.warning(f"Could not apply AWB settings: {e}")

    def _apply_awb_to_camera_manager(self):
        """Apply AWB (auto/manual + gains) to the active camera via CameraManager.

        Uses CameraStream.picam2.set_controls as a fallback if no higher-level API exists.
        """
        if not hasattr(self, 'camera_manager') or not self.camera_manager:
            return False
        cs = getattr(self.camera_manager, 'camera_stream', None)
        if cs is None:
            return False

        awb_auto = bool(self.config.get("auto_white_balance", True))

        # First try high-level API if present
        applied = False
        if hasattr(cs, 'set_awb_enable') and callable(getattr(cs, 'set_awb_enable')):
            try:
                cs.set_awb_enable(awb_auto)
                applied = True
            except Exception:
                applied = False

        # Build controls dict for direct Picamera2 access
        controls = {"AwbEnable": awb_auto}
        if not awb_auto:
            # Determine manual gains (R, B)
            r = self.config.get("colour_gain_r")
            b = self.config.get("colour_gain_b")
            cg = self.config.get("colour_gains") or self.config.get("color_gains")
            try:
                if (r is None or b is None) and cg and len(cg) >= 2:
                    r = r if r is not None else float(cg[0])
                    b = b if b is not None else float(cg[1])
            except Exception:
                pass
            if r is not None and b is not None:
                # Prefer high-level API if available
                if hasattr(cs, 'set_colour_gains') and callable(getattr(cs, 'set_colour_gains')):
                    try:
                        cs.set_colour_gains(float(r), float(b))
                        applied = True
                    except Exception:
                        pass
                # Also prepare fallback controls
                try:
                    controls["ColourGains"] = (float(r), float(b))
                except Exception:
                    pass

        # Fallback to direct controls if Picamera2 is available
        try:
            picam2 = getattr(cs, 'picam2', None)
            if picam2 is not None and hasattr(picam2, 'set_controls'):
                picam2.set_controls(controls)
                applied = True
        except Exception as e:
            logger.warning(f"AWB control apply failed: {e}")

        return applied
        
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """
        Cập nhật cấu hình của camera
        
        Args:
            new_config: Cấu hình mới
            
        Returns:
            True nếu cập nhật thành công, False nếu không
        """
        # Kiểm tra và xử lý các thay đổi chế độ camera
        camera_mode_changed = False
        if "camera_mode" in new_config and new_config["camera_mode"] != self.config.get("camera_mode", "live"):
            camera_mode_changed = True
            print(f"DEBUG: [CameraTool] Camera mode changing from {self.config.get('camera_mode', 'live')} to {new_config['camera_mode']}")
        
        # Cập nhật config
        result = super().update_config(new_config)
        
        # Nếu cập nhật thành công, áp dụng cấu hình mới
        if result:
            # Xử lý thay đổi chế độ camera - delegate to CameraManager
            if camera_mode_changed:
                print(f"DEBUG: [CameraTool] Setting camera mode to {self.config['camera_mode']}")
                
                # Nếu chuyển sang chế độ trigger, đảm bảo external_trigger được bật
                if self.config["camera_mode"] == "trigger" and self.is_gs_camera:
                    self.config["enable_external_trigger"] = True
                    print(f"DEBUG: [CameraTool] Setting enable_external_trigger=True for trigger mode")
                
                # Delegate to CameraManager
                self.set_camera_mode(self.config["camera_mode"])
                
                # Ensure camera is visible (regardless of whether Camera Source is added to the pipeline)
                if hasattr(self, 'camera_manager') and self.camera_manager:
                    print(f"DEBUG: [CameraTool] Ensuring camera preview is active")
                    if hasattr(self.camera_manager, 'toggle_live_camera'):
                        self.camera_manager.toggle_live_camera(True)
            
            # Apply any exposure/gain changes directly to camera manager if available
            if hasattr(self, 'camera_manager') and self.camera_manager:
                # Frame size / format / fps updates
                if "frame_size" in new_config and hasattr(self.camera_manager, 'camera_stream') and \
                   self.camera_manager.camera_stream and hasattr(self.camera_manager.camera_stream, 'set_frame_size'):
                    try:
                        w, h = new_config['frame_size']
                        print(f"DEBUG: [CameraTool] Updating frame size to {w}x{h}")
                        self.camera_manager.camera_stream.set_frame_size(w, h)
                    except Exception as e:
                        logger.warning(f"Failed to update frame size: {e}")
                if "format" in new_config and hasattr(self.camera_manager, 'camera_stream') and \
                   self.camera_manager.camera_stream and hasattr(self.camera_manager.camera_stream, 'set_format'):
                    try:
                        pf = str(new_config['format'])
                        if pf not in CameraTool.SUPPORTED_FORMATS:
                            logger.warning(f"Requested unsupported pixel format '{pf}', ignoring")
                        else:
                            print(f"DEBUG: [CameraTool] Updating pixel format to {pf}")
                            self.current_format = pf
                            self.camera_manager.camera_stream.set_format(pf)
                    except Exception as e:
                        logger.warning(f"Failed to update pixel format: {e}")
                if "target_fps" in new_config and hasattr(self.camera_manager, 'camera_stream') and \
                   self.camera_manager.camera_stream and hasattr(self.camera_manager.camera_stream, 'set_target_fps'):
                    try:
                        fps = new_config['target_fps']
                        print(f"DEBUG: [CameraTool] Updating target FPS to {fps}")
                        self.camera_manager.camera_stream.set_target_fps(fps)
                    except Exception as e:
                        logger.warning(f"Failed to update target FPS: {e}")
                # Check for parameter changes (new keys only)
                if "exposure_us" in new_config:
                    print(f"DEBUG: [CameraTool] Updating exposure_us to {new_config['exposure_us']}")
                    if hasattr(self.camera_manager, 'set_exposure_value'):
                        self.camera_manager.set_exposure_value(new_config['exposure_us'])
                
                if "analogue_gain" in new_config:
                    print(f"DEBUG: [CameraTool] Updating analogue_gain to {new_config['analogue_gain']}")
                    if hasattr(self.camera_manager, 'set_gain_value'):
                        self.camera_manager.set_gain_value(new_config['analogue_gain'])
                
                if "ev" in new_config:
                    print(f"DEBUG: [CameraTool] Updating EV to {new_config['ev']}")
                    if hasattr(self.camera_manager, 'set_ev_value'):
                        self.camera_manager.set_ev_value(new_config['ev'])
                
                if "auto_exposure" in new_config:
                    auto_exp = new_config["auto_exposure"]
                    print(f"DEBUG: [CameraTool] Updating auto exposure to {auto_exp}")
                    if auto_exp:
                        if hasattr(self.camera_manager, 'set_auto_exposure_mode'):
                            self.camera_manager.set_auto_exposure_mode()
                    else:
                        if hasattr(self.camera_manager, 'set_manual_exposure_mode'):
                            self.camera_manager.set_manual_exposure_mode()
                # AWB: auto/manual toggle + manual gains apply ngay
                if any(k in new_config for k in ("auto_white_balance", "colour_gain_r", "colour_gain_b", "colour_gains", "color_gains")):
                    print("DEBUG: [CameraTool] Applying AWB change(s) immediately")
                    self._apply_awb_to_camera_manager()
        
    def trigger_capture(self) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Kích hoạt chụp ảnh trong chế độ trigger - delegate to CameraManager
        
        Returns:
            Tuple chứa (ảnh chụp, kết quả)
        """
        # Delegate to CameraManager
        if hasattr(self, 'camera_manager') and self.camera_manager:
            return self.camera_manager.trigger_capture()
        else:
            # Fallback response if no camera manager
            frame = np.zeros((1080, 1440, 3), dtype=np.uint8)
            return frame, {"error": "Camera manager not available"}
            
    def _query_frame(self) -> np.ndarray:
        """Lấy khung hình từ camera - delegate to CameraManager"""
        if hasattr(self, 'camera_manager') and self.camera_manager:
            # Get current frame from camera manager's camera stream
            if self.camera_manager.camera_stream and self.camera_manager.camera_stream.is_running():
                try:
                    # Get the latest frame from camera stream
                    if hasattr(self.camera_manager.camera_stream, 'get_latest_frame'):
                        return self.camera_manager.camera_stream.get_latest_frame()
                    else:
                        # Fallback to a basic frame
                        return np.zeros((1080, 1440, 3), dtype=np.uint8)
                except Exception as e:
                    logger.error(f"Error getting frame from camera stream: {e}")
                    return np.zeros((1080, 1440, 3), dtype=np.uint8)
            
        # Return a blank frame if no camera available
        return np.zeros((1080, 1440, 3), dtype=np.uint8)
        """
        Chụp ảnh độ phân giải cao
        
        Returns:
            Tuple chứa (ảnh chụp, kết quả)
        """
        if not self.is_camera_available:
            logger.warning("Camera không khả dụng, không thể chụp ảnh")
            # Trả về khung hình giả
            frame = np.zeros((1080, 1440, 3), dtype=np.uint8)
            return frame, {"error": "Camera không khả dụng"}
            
        try:
            # Tạm dừng live view
            was_live = self.is_live
            if was_live:
                self.stop_live_view()
                
            # Chuyển sang cấu hình still
            self.picam2.configure(self.still_config)
            self.picam2.start()
            
            # Chụp ảnh
            frame = self.picam2.capture_array()
            
            # Chuyển trở lại cấu hình preview
            self.picam2.stop()
            self.picam2.configure(self.preview_config)
            
            # Khởi động lại live view nếu trước đó đang sử dụng
            if was_live:
                self.start_live_view()
                
            # Tạo kết quả
            result = {
                'tool_name': self.display_name,
                'frame_size': frame.shape[1::-1],  # (width, height)
                'frame_format': self.current_format,
                'exposure_time': self.current_exposure,
                'is_still': True
            }
            
            return frame, result
            
        except Exception as e:
            logger.error(f"Lỗi chụp ảnh: {e}")
            # Trả về khung hình giả nếu có lỗi
            frame = np.zeros((1080, 1440, 3), dtype=np.uint8)
            return frame, {"error": f"Lỗi chụp ảnh: {e}"}
            
    def cleanup(self) -> None:
        """Giải phóng tài nguyên camera"""
        # CameraTool doesn't manage camera directly - no cleanup needed
        logger.info("CameraTool cleanup called - no camera resources to clean")

    def start_camera(self) -> bool:
        """
        Bắt đầu camera theo chế độ đã cấu hình
        
        Returns:
            True nếu thành công, False nếu không
        """
        mode = self.config.get("camera_mode", "live")
        if mode == "live":
            return self.start_live_mode()
        else:
            return self.start_trigger_mode()
    
    def stop_camera(self) -> bool:
        """
        Dừng camera
        
        Returns:
            True nếu thành công, False nếu không
        """
        # Camera Source tool doesn't directly control camera - managed by CameraManager
        logger.info("CameraTool.stop_camera called - delegating to main CameraManager")
        return True
    
    def start_live_mode(self) -> bool:
        """
        Bật chế độ live camera
        
        Returns:
            True nếu thành công, False nếu không
        """
        # Use set_camera_mode instead of manual assignment to avoid duplication
        result = self.set_camera_mode("live")
        
        # This is a placeholder - actual camera control is done by camera_manager
        logger.info("Camera mode set to LIVE")
        return result
        
    def start_trigger_mode(self) -> bool:
        """
        Bật chế độ trigger camera
        
        Returns:
            True nếu thành công, False nếu không
        """
        # Use set_camera_mode instead of manual assignment to avoid duplication
        result = self.set_camera_mode("trigger")
        
        # This is a placeholder - actual camera control is done by camera_manager
        logger.info("Camera mode set to TRIGGER")
        return result
    
    def is_running(self) -> bool:
        """
        Kiểm tra xem camera có đang chạy hay không
        
        Returns:
            True nếu camera đang chạy, False nếu không
        """
        # Camera Source tool doesn't directly control camera - managed by CameraManager
        return False  # Always return False since this tool doesn't control the camera directly

# Factory function for creating CameraTool
def create_camera_tool(config: Optional[Dict[str, Any]] = None) -> CameraTool:
    """
    Tạo một CameraTool mới
    
    Args:
        config: Cấu hình cho camera
        
    Returns:
        CameraTool instance
    """
    if config is None:
        config = {}
    
    # Ensure default camera mode and trigger settings
    if "camera_mode" not in config:
        config["camera_mode"] = "live"  # Default to live mode
    if "enable_external_trigger" not in config:
        config["enable_external_trigger"] = False
    
    return CameraTool("Camera Source", config)



