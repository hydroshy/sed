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
        if "is_auto_exposure" not in self.config:
            self.config["is_auto_exposure"] = True
        if "camera_mode" not in self.config:
            self.config["camera_mode"] = "live"  # "live" hoặc "trigger"
        if "enable_external_trigger" not in self.config:
            self.config["enable_external_trigger"] = False
            
        # Log thông tin cấu hình
        logger.info(f"Camera Tool created with config: rotation_angle={self.config['rotation_angle']}, "
                   f"exposure={self.config['exposure']}, gain={self.config['gain']}, "
                   f"auto_exposure={self.config['is_auto_exposure']}, "
                   f"camera_mode={self.config['camera_mode']}, "
                   f"enable_external_trigger={self.config['enable_external_trigger']}")
        
        # Don't initialize separate camera instance - this conflicts with main camera stream
        # CameraTool just stores configuration that will be applied to main camera_manager
        self.is_camera_available = False
        self.picam2 = None
        self.is_live = False  # Add is_live attribute for job manager compatibility
        
        # Camera configuration (stored for reference)
        self.current_exposure = self.config.get("exposure", 10000)
        self.current_format = self.config.get("format", "BGR888")
        self.frame_size = self.config.get("frame_size", (1440, 1080))
        
        # Reference to the main camera manager - will be set by main window
        self.camera_manager = None
        
        # Trigger mode properties
        self.trigger_ready = False  # Flag to indicate if camera is ready for triggering
        self.last_trigger_frame = None  # Store the last triggered frame
        self.is_gs_camera = self._check_if_gs_camera()  # Check if we have a global shutter camera
        
        # Don't start any timers or camera operations
        logger.info("CameraTool created as configuration holder - no separate camera instance")
        
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
        self.config.set_default("format", "BGR888")
        self.config.set_default("exposure_time", 10000)  # in microseconds
        self.config.set_default("frame_rate", 60)
        self.config.set_default("auto_exposure", False)
        self.config.set_default("auto_white_balance", False)
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
        self.config.set_default("is_auto_exposure", False)  # Auto exposure mode
        
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
            
        # Cập nhật cấu hình
        self.config["camera_mode"] = mode
        logger.info(f"Đã đặt chế độ camera thành: {mode}")
        
        # Khi thay đổi chế độ, đảm bảo camera vẫn hoạt động
        # Bỏ qua kiểm tra liên quan đến nguồn camera
        try:
            # Update configuration in main camera manager if available
            if hasattr(self, 'camera_manager') and self.camera_manager:
                print(f"DEBUG: [CameraTool] Applying {mode} mode to camera_manager")
                
                if mode == "live":
                    # Make sure preview is active
                    if hasattr(self.camera_manager, 'toggle_live_camera'):
                        self.camera_manager.toggle_live_camera(True)
                elif mode == "trigger":
                    # Switch to trigger mode while keeping preview active
                    if hasattr(self.camera_manager, 'set_trigger_mode'):
                        self.camera_manager.set_trigger_mode(True)
                        # Make sure preview is active
                        if hasattr(self.camera_manager, 'toggle_live_camera'):
                            self.camera_manager.toggle_live_camera(True)
                elif mode == "single":
                    # Similar to trigger but uses software trigger
                    if hasattr(self.camera_manager, 'set_trigger_mode'):
                        self.camera_manager.set_trigger_mode(False)
                        # Make sure preview is active
                        if hasattr(self.camera_manager, 'toggle_live_camera'):
                            self.camera_manager.toggle_live_camera(True)
            
            # Nếu là camera global shutter và chế độ trigger, cấu hình external trigger
            if mode == "trigger" and self.is_gs_camera and self.config.get("enable_external_trigger", False):
                return self._setup_external_trigger(True)
            elif mode == "live" and self.is_gs_camera and self.config.get("enable_external_trigger", False):
                return self._setup_external_trigger(False)
                
            return True
        except Exception as e:
            logger.error(f"Error setting camera mode: {e}")
            return False
        
    def _setup_external_trigger(self, enable: bool) -> bool:
        """
        Bật/tắt chế độ external trigger cho camera IMX296
        
        Args:
            enable: True để bật, False để tắt
            
        Returns:
            True nếu thành công, False nếu không
        """
        if not self.is_gs_camera:
            logger.warning("Không phải camera IMX296, không thể cấu hình external trigger")
            return False
            
        try:
            # Đặt giá trị cho trigger_mode
            value = 1 if enable else 0
            cmd = f"echo {value} | sudo tee /sys/module/imx296/parameters/trigger_mode"
            
            # Thực thi lệnh
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Đã {'bật' if enable else 'tắt'} external trigger cho IMX296")
                return True
            else:
                logger.error(f"Lỗi thiết lập external trigger: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi thiết lập external trigger: {e}")
            return False
            
    def trigger_capture(self) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Kích hoạt chụp ảnh trong chế độ trigger
        
        Returns:
            Tuple chứa (ảnh chụp, kết quả)
        """
        # Kiểm tra xem có đang ở chế độ trigger không
        if self.config.get("camera_mode") != "trigger":
            logger.warning("Không thể kích hoạt chụp vì không ở chế độ trigger")
            # Trả về khung hình cuối cùng hoặc khung hình giả
            frame = self.last_trigger_frame if self.last_trigger_frame is not None else np.zeros((1080, 1440, 3), dtype=np.uint8)
            return frame, {"error": "Không ở chế độ trigger"}
            
        # Nếu chúng ta sử dụng external trigger, không làm gì cả vì trigger được xử lý bởi phần cứng
        if self.is_gs_camera and self.config.get("enable_external_trigger", False):
            logger.info("Đang sử dụng external trigger, chờ camera phản hồi...")
            # Trả về khung hình cuối cùng hoặc khung hình giả
            frame = self.last_trigger_frame if self.last_trigger_frame is not None else np.zeros((1080, 1440, 3), dtype=np.uint8)
            return frame, {"status": "waiting_for_external_trigger"}
            
        # Nếu không, thực hiện chụp ảnh qua phần mềm
        try:
            # Capture through the main camera_stream
            if hasattr(self, 'camera_manager') and self.camera_manager:
                # Use the camera_manager if available
                frame, metadata = self.camera_manager.trigger_capture()
                self.last_trigger_frame = frame.copy()
                return frame, metadata
            else:
                # Fallback to direct capture if camera_manager is not available
                # This assumes picam2 is properly initialized elsewhere
                if not self.is_camera_available or not self.picam2:
                    frame = np.zeros((1080, 1440, 3), dtype=np.uint8)
                    return frame, {"error": "Camera không khả dụng"}
                
                # Capture directly using picam2
                frame = self.picam2.capture_array()
                self.last_trigger_frame = frame.copy()
                
                # Tạo kết quả
                result = {
                    'tool_name': self.display_name,
                    'frame_size': frame.shape[1::-1],  # (width, height)
                    'frame_format': self.current_format,
                    'exposure_time': self.current_exposure,
                    'trigger_mode': True
                }
                return frame, result
                
        except Exception as e:
            logger.error(f"Lỗi kích hoạt chụp ảnh: {e}")
            # Trả về khung hình giả nếu có lỗi
            frame = self.last_trigger_frame if self.last_trigger_frame is not None else np.zeros((1080, 1440, 3), dtype=np.uint8)
            return frame, {"error": f"Lỗi kích hoạt chụp ảnh: {e}"}
            
    def _query_frame(self) -> np.ndarray:
        """Lấy khung hình từ camera"""
        if not self.is_camera_available or not self.is_live:
            # Tạo khung hình giả nếu camera không khả dụng
            return np.zeros((480, 640, 3), dtype=np.uint8)
            
        try:
            with QMutexLocker(self._mutex):
                frame = self.picam2.capture_array()
                
                # Xử lý khung hình theo config
                rotation = self.config.get("rotation", 0)
                flip_h = self.config.get("flip_horizontal", False)
                flip_v = self.config.get("flip_vertical", False)
                
                # Xoay ảnh nếu cần
                if rotation == 90:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                elif rotation == 180:
                    frame = cv2.rotate(frame, cv2.ROTATE_180)
                elif rotation == 270:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                    
                # Lật ảnh nếu cần
                if flip_h or flip_v:
                    flip_code = -1 if (flip_h and flip_v) else (0 if flip_v else 1)
                    frame = cv2.flip(frame, flip_code)
                    
                return frame
        except Exception as e:
            logger.error(f"Lỗi lấy khung hình: {e}")
            # Trả về khung hình giả nếu có lỗi
            return np.zeros((480, 640, 3), dtype=np.uint8)
            
    def process(self, image: np.ndarray = None, context: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Cung cấp khung hình cho pipeline
        
        Args:
            image: Không được sử dụng vì đây là công cụ đầu vào
            context: Ngữ cảnh từ các công cụ trước
            
        Returns:
            Tuple chứa (khung hình từ camera, kết quả)
        """
        # Xác định chế độ camera
        camera_mode = self.config.get("camera_mode", "live")
        
        # Nếu là chế độ trigger, trả về khung hình đã chụp cuối cùng
        if camera_mode == "trigger":
            if self.last_trigger_frame is not None:
                frame = self.last_trigger_frame.copy()
            else:
                # Nếu chưa có khung hình nào, cố gắng lấy một khung hình
                if hasattr(self, 'camera_manager') and self.camera_manager:
                    frame, _ = self.camera_manager.trigger_capture()
                    self.last_trigger_frame = frame.copy()
                else:
                    # Trả về khung hình giả nếu không có camera_manager
                    frame = np.zeros((1080, 1440, 3), dtype=np.uint8)
                    logger.warning("Chế độ trigger: không có khung hình sẵn có")
        # Chế độ live: lấy khung hình từ camera hoặc sử dụng ảnh đầu vào
        else:
            if image is not None:
                frame = image.copy()
            else:
                frame = self._query_frame()
        
        # Áp dụng rotation từ cấu hình của Camera Source
        rotation = self.config.get("rotation", 0)
        rotation_angle = self.config.get("rotation_angle", 0)
        
        # Áp dụng rotation từ góc xoay trước
        if rotation_angle != 0:
            # Tính toán ma trận xoay
            h, w = frame.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, rotation_angle, 1.0)
            frame = cv2.warpAffine(frame, M, (w, h), flags=cv2.INTER_LINEAR)
        
        # Áp dụng rotation tiêu chuẩn nếu được cấu hình
        if rotation > 0:
            if rotation == 90:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            elif rotation == 180:
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            elif rotation == 270:
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        
        # Tạo kết quả
        result = {
            'tool_name': self.display_name,
            'frame_size': frame.shape[1::-1],  # (width, height)
            'frame_format': self.current_format,
            'exposure_time': self.current_exposure,
            'exposure': self.config.get("exposure", 10000),
            'gain': self.config.get("gain", 1.0),
            'ev': self.config.get("ev", 0.0),
            'rotation': rotation,
            'rotation_angle': rotation_angle,
            'is_camera_available': self.is_camera_available,
            'is_live': self.is_live,
            'auto_exposure': self.config.get("auto_exposure", False),
            'is_auto_exposure': self.config.get("is_auto_exposure", False),
            'camera_mode': camera_mode,
            'enable_external_trigger': self.config.get("enable_external_trigger", False),
            'is_gs_camera': self.is_gs_camera
        }
        
        return frame, result
        
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
        
        external_trigger_changed = False
        if "enable_external_trigger" in new_config and new_config["enable_external_trigger"] != self.config.get("enable_external_trigger", False):
            external_trigger_changed = True
        
        # Cập nhật config
        result = super().update_config(new_config)
        
        # Nếu cập nhật thành công, áp dụng cấu hình mới
        if result:
            # Xử lý thay đổi chế độ camera - luôn giữ camera hiển thị khi thay đổi chế độ
            if camera_mode_changed:
                print(f"DEBUG: [CameraTool] Setting camera mode to {self.config['camera_mode']}")
                self.set_camera_mode(self.config["camera_mode"])
                
                # Ensure camera is visible (regardless of whether Camera Source is added to the pipeline)
                if hasattr(self, 'camera_manager') and self.camera_manager:
                    print(f"DEBUG: [CameraTool] Ensuring camera preview is active")
                    if hasattr(self.camera_manager, 'toggle_live_camera'):
                        self.camera_manager.toggle_live_camera(True)
                
            # Xử lý thay đổi chế độ external trigger
            if external_trigger_changed and self.is_gs_camera:
                self._setup_external_trigger(self.config["enable_external_trigger"])
            
            # Apply any exposure/gain changes directly to camera manager if available
            if hasattr(self, 'camera_manager') and self.camera_manager:
                # Check for parameter changes
                if "exposure" in new_config:
                    print(f"DEBUG: [CameraTool] Updating exposure to {new_config['exposure']}")
                    if hasattr(self.camera_manager, 'set_exposure_value'):
                        self.camera_manager.set_exposure_value(new_config['exposure'])
                
                if "gain" in new_config:
                    print(f"DEBUG: [CameraTool] Updating gain to {new_config['gain']}")
                    if hasattr(self.camera_manager, 'set_gain_value'):
                        self.camera_manager.set_gain_value(new_config['gain'])
                
                if "ev" in new_config:
                    print(f"DEBUG: [CameraTool] Updating EV to {new_config['ev']}")
                    if hasattr(self.camera_manager, 'set_ev_value'):
                        self.camera_manager.set_ev_value(new_config['ev'])
                
                if "is_auto_exposure" in new_config:
                    auto_exp = new_config["is_auto_exposure"]
                    print(f"DEBUG: [CameraTool] Updating auto exposure to {auto_exp}")
                    if auto_exp:
                        if hasattr(self.camera_manager, 'set_auto_exposure_mode'):
                            self.camera_manager.set_auto_exposure_mode()
                    else:
                        if hasattr(self.camera_manager, 'set_manual_exposure_mode'):
                            self.camera_manager.set_manual_exposure_mode()
        
        return result
        
    def capture_still(self) -> Tuple[np.ndarray, Dict[str, Any]]:
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
        # Set camera mode to live
        self.config["camera_mode"] = "live"
        self.set_camera_mode("live")
        
        # This is a placeholder - actual camera control is done by camera_manager
        logger.info("Camera mode set to LIVE")
        return True
        
    def start_trigger_mode(self) -> bool:
        """
        Bật chế độ trigger camera
        
        Returns:
            True nếu thành công, False nếu không
        """
        # Set camera mode to trigger
        self.config["camera_mode"] = "trigger"
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
