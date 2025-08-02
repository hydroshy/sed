"""
Camera Tool cho hệ thống SED
"""
import logging
import numpy as np
import cv2
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
            
        # Log thông tin cấu hình
        logger.info(f"Camera Tool created with config: rotation_angle={self.config['rotation_angle']}, "
                   f"exposure={self.config['exposure']}, gain={self.config['gain']}, "
                   f"auto_exposure={self.config['is_auto_exposure']}")
        
        # Don't initialize separate camera instance - this conflicts with main camera stream
        # CameraTool just stores configuration that will be applied to main camera_manager
        self.is_camera_available = False
        self.picam2 = None
        
        # Camera configuration (stored for reference)
        self.current_exposure = self.config.get("exposure", 10000)
        self.current_format = self.config.get("format", "BGR888")
        self.frame_size = self.config.get("frame_size", (1440, 1080))
        
        # Don't start any timers or camera operations
        logger.info("CameraTool created as configuration holder - no separate camera instance")
        
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
        # UI settings
        self.config.set_default("show_fps", True)
        self.config.set_default("show_histogram", False)
        self.config.set_default("show_exposure_warning", True)
        
    def start_live_view(self) -> bool:
        """Bắt đầu chế độ xem trực tiếp"""
        if not self.is_camera_available:
            logger.warning("Camera không khả dụng")
            return False
            
        try:
            if not self.is_live:
                self.picam2.start()
                self.timer.start(33)  # ~30 FPS
                self.is_live = True
                logger.info("Đã bắt đầu chế độ xem trực tiếp")
            return True
        except Exception as e:
            logger.error(f"Lỗi bắt đầu chế độ xem trực tiếp: {e}")
            return False
            
    def stop_live_view(self) -> bool:
        """Dừng chế độ xem trực tiếp"""
        if not self.is_camera_available:
            return False
            
        try:
            if self.is_live:
                self.timer.stop()
                self.picam2.stop()
                self.is_live = False
                logger.info("Đã dừng chế độ xem trực tiếp")
            return True
        except Exception as e:
            logger.error(f"Lỗi dừng chế độ xem trực tiếp: {e}")
            return False
            
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
        # Lấy khung hình từ camera hoặc sử dụng ảnh đầu vào nếu có
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
            'is_auto_exposure': self.config.get("is_auto_exposure", False)
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
        # Cập nhật config
        result = super().update_config(new_config)
        
        # Nếu cập nhật thành công và camera khả dụng, áp dụng cấu hình mới
        if result and self.is_camera_available and self.picam2:
            # Nếu kích thước khung hình hoặc định dạng thay đổi, cần cấu hình lại camera
            if ("frame_size" in new_config or "format" in new_config):
                self.stop_live_view()
                self._configure_camera()
                self.start_live_view()
            else:
                # Cập nhật các thông số khác
                controls = {}
                
                if "exposure_time" in new_config:
                    self.current_exposure = new_config["exposure_time"]
                    controls["ExposureTime"] = self.current_exposure
                    
                if "auto_exposure" in new_config:
                    controls["AeEnable"] = new_config["auto_exposure"]
                    
                if "auto_white_balance" in new_config:
                    controls["AwbEnable"] = new_config["auto_white_balance"]
                    
                if "color_temperature" in new_config and not new_config.get("auto_white_balance", False):
                    controls["ColourTemperature"] = new_config["color_temperature"]
                    
                if "analogue_gain" in new_config:
                    controls["AnalogueGain"] = new_config["analogue_gain"]
                    
                # Áp dụng các thông số đã thay đổi
                if controls and self.is_live:
                    self.picam2.set_controls(controls)
                    
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
        """Camera Source tool doesn't directly control camera - managed by CameraManager"""
        logger.info("CameraTool.start_camera called - delegating to main CameraManager")
        return True
        
    def stop_camera(self) -> bool:
        """Camera Source tool doesn't directly control camera - managed by CameraManager"""
        logger.info("CameraTool.stop_camera called - delegating to main CameraManager")
        return True
        
    def is_running(self) -> bool:
        """Camera Source tool doesn't directly control camera - managed by CameraManager"""
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
    return CameraTool("Camera Source", config)
