"""
Công cụ phát hiện đối tượng với giao diện chuẩn
"""
import logging
import numpy as np
from typing import Dict, Any, List, Tuple, Optional, Union

from .base_tool import BaseTool, ToolConfig
try:
    from tools.detection.detect_tool import DetectTool as AdvancedDetectTool
    from tools.detection.model_manager import ModelManager
    DETECT_TOOLS_AVAILABLE = True
except ImportError:
    DETECT_TOOLS_AVAILABLE = False
    logging.warning("Detect Tools không khả dụng. Kiểm tra thư mục detection.")

class DetectTool(BaseTool):
    """
    Công cụ phát hiện đối tượng với YOLO
    """
    
    def __init__(self, name: str = "Detect Tool", config: Optional[Union[Dict[str, Any], ToolConfig]] = None, tool_id: Optional[int] = None):
        """
        Khởi tạo công cụ phát hiện
        
        Args:
            name: Tên hiển thị của công cụ
            config: Cấu hình cho công cụ
            tool_id: ID của công cụ
        """
        super().__init__(name, config, tool_id)
        
        # Trạng thái của công cụ
        self.is_model_loaded = False
        self.advanced_tool = None
        
        # Khởi tạo advanced detect tool nếu có sẵn
        if DETECT_TOOLS_AVAILABLE:
            try:
                self.advanced_tool = AdvancedDetectTool(name, config)
                self.is_model_loaded = self.advanced_tool.is_model_loaded
                logging.info(f"Đã khởi tạo Advanced Detect Tool: {self.is_model_loaded}")
            except Exception as e:
                logging.error(f"Lỗi khởi tạo Advanced Detect Tool: {e}")
                self.is_model_loaded = False
        
    def setup_config(self) -> None:
        """Thiết lập cấu hình mặc định cho Detect Tool"""
        # Cấu hình model
        self.config.set_default("model_path", "")
        self.config.set_default("confidence_threshold", 0.5)
        self.config.set_default("iou_threshold", 0.45)
        self.config.set_default("input_size", (640, 640))
        
        # Cấu hình hiển thị
        self.config.set_default("show_boxes", True)
        self.config.set_default("show_labels", True)
        self.config.set_default("show_confidence", True)
        self.config.set_default("label_position", "top")  # top, bottom
        
        # Cấu hình xử lý
        self.config.set_default("enable_class_filtering", False)
        self.config.set_default("allowed_classes", [])
        
    def process(self, image: np.ndarray, context: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Phát hiện đối tượng trong hình ảnh
        
        Args:
            image: Hình ảnh đầu vào
            context: Ngữ cảnh từ các công cụ trước
            
        Returns:
            Tuple chứa (hình ảnh với các đối tượng được đánh dấu, kết quả phát hiện)
        """
        if not DETECT_TOOLS_AVAILABLE or not self.advanced_tool or not self.is_model_loaded:
            logging.warning("Advanced Detect Tool không khả dụng hoặc model chưa được tải")
            return image, {
                "tool_name": self.display_name,
                "error": "Model không khả dụng",
                "detections": []
            }
            
        try:
            # Cập nhật cấu hình từ context nếu cần
            if context and "detection_config" in context:
                self.update_config(context["detection_config"])
                
            # Sử dụng advanced detect tool
            result_image, results = self.advanced_tool.process(image)
            
            # Tạo kết quả phát hiện
            detections = results.get('detections', [])
            
            # Tạo kết quả
            result = {
                "tool_name": self.display_name,
                "detections": detections,
                "detection_count": len(detections),
                "model_name": self.advanced_tool.model_name if hasattr(self.advanced_tool, 'model_name') else "unknown",
                "processing_time": results.get('processing_time', 0)
            }
            
            return result_image, result
            
        except Exception as e:
            logging.error(f"Lỗi xử lý Detect Tool: {e}")
            return image, {
                "tool_name": self.display_name,
                "error": f"Lỗi xử lý: {str(e)}",
                "detections": []
            }
            
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """
        Cập nhật cấu hình của công cụ
        
        Args:
            new_config: Cấu hình mới
            
        Returns:
            True nếu cập nhật thành công, False nếu không
        """
        result = super().update_config(new_config)
        
        # Cập nhật cấu hình cho advanced detect tool
        if result and self.advanced_tool:
            try:
                # Truyền cấu hình cho advanced tool
                self.advanced_tool.update_config(new_config)
            except Exception as e:
                logging.error(f"Lỗi cập nhật cấu hình cho Advanced Detect Tool: {e}")
                return False
                
        return result
        
    def get_info(self) -> Dict[str, Any]:
        """
        Lấy thông tin về công cụ
        
        Returns:
            Dictionary chứa thông tin về công cụ
        """
        info = super().get_info()
        
        # Thêm thông tin về model
        if self.advanced_tool:
            info.update({
                "is_model_loaded": self.is_model_loaded,
                "model_name": self.advanced_tool.model_name if hasattr(self.advanced_tool, 'model_name') else "unknown",
                "model_path": self.config.get("model_path", ""),
            })
            
        return info
        
    def cleanup(self) -> None:
        """Giải phóng tài nguyên"""
        if self.advanced_tool:
            try:
                # Gọi cleanup cho advanced tool nếu có
                if hasattr(self.advanced_tool, 'cleanup'):
                    self.advanced_tool.cleanup()
            except Exception as e:
                logging.error(f"Lỗi giải phóng tài nguyên Advanced Detect Tool: {e}")
                
        logging.info("Đã giải phóng tài nguyên Detect Tool")

# Factory function để tạo DetectTool
def create_detect_tool(config: Optional[Dict[str, Any]] = None) -> DetectTool:
    """
    Tạo một DetectTool mới
    
    Args:
        config: Cấu hình cho công cụ phát hiện
        
    Returns:
        DetectTool instance
    """
    return DetectTool("Detect Tool", config)
