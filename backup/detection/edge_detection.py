import cv2
import numpy as np
from typing import Dict, Any, Tuple, Optional
from tools.base_tool import BaseTool, ToolConfig

from tools.base_tool import GenericTool
class EdgeDetectionTool(GenericTool):
    """Công cụ phát hiện biên sử dụng Canny edge detection"""
    
    def __init__(self, name: str = "EdgeDetection", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)
        
    def setup_config(self) -> None:
        """Thiết lập cấu hình mặc định cho edge detection"""
        self.config.set_default("low_threshold", 50)
        self.config.set_default("high_threshold", 150)
        self.config.set_default("aperture_size", 3)
        self.config.set_default("l2_gradient", False)
        self.config.set_default("blur_kernel_size", 5)
        self.config.set_default("enable_blur", True)
        
        # Validators
        self.config.set_validator("low_threshold", lambda x: 0 <= x <= 255)
        self.config.set_validator("high_threshold", lambda x: 0 <= x <= 255)
        self.config.set_validator("aperture_size", lambda x: x in [3, 5, 7])
        self.config.set_validator("blur_kernel_size", lambda x: x > 0 and x % 2 == 1)
        
    def process(self, image: np.ndarray, context: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Xử lý phát hiện biên trên ảnh
        
        Args:
            image: Ảnh đầu vào
            context: Ngữ cảnh từ các tool trước
            
        Returns:
            Tuple chứa ảnh đã xử lý và kết quả
        """
        try:
            # Chuyển sang grayscale nếu là ảnh màu
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
                
            # Áp dụng Gaussian blur nếu được bật
            if self.config.get("enable_blur"):
                kernel_size = self.config.get("blur_kernel_size")
                gray = cv2.GaussianBlur(gray, (kernel_size, kernel_size), 0)
            
            # Phát hiện biên bằng Canny
            low_threshold = self.config.get("low_threshold")
            high_threshold = self.config.get("high_threshold")
            aperture_size = self.config.get("aperture_size")
            l2_gradient = self.config.get("l2_gradient")
            
            edges = cv2.Canny(gray, low_threshold, high_threshold, 
                            apertureSize=aperture_size, L2gradient=l2_gradient)
            
            # Chuyển edges về 3 channels để hiển thị
            if len(image.shape) == 3:
                edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            else:
                edges_colored = edges
                
            # Tính toán thống kê
            total_pixels = edges.shape[0] * edges.shape[1]
            edge_pixels = np.count_nonzero(edges)
            edge_density = edge_pixels / total_pixels
            
            # Tìm contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            result = {
                "edge_count": len(contours),
                "edge_density": edge_density,
                "edge_pixels": edge_pixels,
                "total_pixels": total_pixels,
                "contours": contours,
                "config_used": self.config.to_dict()
            }
            
            return edges_colored, result
            
        except Exception as e:
            error_msg = f"Lỗi trong EdgeDetectionTool: {str(e)}"
            return image, {"error": error_msg}
