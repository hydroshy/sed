"""
Job Manager mới cho hệ thống SED với giao diện chuẩn cho các công cụ
"""
import logging
import time
import numpy as np
from typing import Dict, Any, List, Tuple, Optional, Union, Type, Callable

from tools.base_tool import BaseTool, ToolConfig
from tools.camera_tool import CameraTool, create_camera_tool

logger = logging.getLogger(__name__)

class JobManager:
    """
    Quản lý toàn bộ luồng xử lý với các công cụ được chuẩn hóa giao diện
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Khởi tạo JobManager
        
        Args:
            config: Cấu hình cho JobManager
        """
        self.config = config or {}
        
        # Danh sách các công cụ trong pipeline
        self.tools: List[BaseTool] = []
        
        # ID tự động tăng cho các công cụ
        self.next_tool_id = 0
        
        # Các công cụ có sẵn để thêm vào pipeline
        self.available_tool_factories = {}
        
        # Kết quả mới nhất của mỗi công cụ
        self.latest_results: Dict[int, Dict[str, Any]] = {}
        
        # Ảnh đầu vào và đầu ra mới nhất
        self.latest_input_image = None
        self.latest_output_image = None
        
        # Khởi tạo mặc định với camera tool
        self._initialize_default_tools()
        self._register_available_tools()
        
    def _initialize_default_tools(self):
        """Khởi tạo các công cụ mặc định (camera)"""
        # Thêm camera tool
        camera_tool = create_camera_tool()
        self.add_tool(camera_tool)
        
    def _register_available_tools(self):
        """Đăng ký các công cụ có sẵn để thêm vào pipeline"""
        # Đăng ký CameraTool
        self.register_tool_factory("Camera", create_camera_tool)
        
        # TODO: Đăng ký các công cụ khác ở đây
        # Ví dụ: self.register_tool_factory("DetectTool", create_detect_tool)
        
    def register_tool_factory(self, tool_name: str, factory_func: Callable) -> None:
        """
        Đăng ký factory function cho một loại công cụ
        
        Args:
            tool_name: Tên hiển thị của loại công cụ
            factory_func: Hàm factory để tạo công cụ
        """
        self.available_tool_factories[tool_name] = factory_func
        logger.info(f"Đã đăng ký công cụ {tool_name}")
        
    def get_available_tools(self) -> List[str]:
        """
        Lấy danh sách các công cụ có sẵn để thêm vào pipeline
        
        Returns:
            Danh sách tên các công cụ có sẵn
        """
        return list(self.available_tool_factories.keys())
        
    def create_tool(self, tool_name: str, config: Optional[Dict[str, Any]] = None) -> Optional[BaseTool]:
        """
        Tạo một công cụ mới từ tên
        
        Args:
            tool_name: Tên của loại công cụ
            config: Cấu hình cho công cụ
            
        Returns:
            Công cụ mới hoặc None nếu không tìm thấy
        """
        if tool_name in self.available_tool_factories:
            factory_func = self.available_tool_factories[tool_name]
            try:
                return factory_func(config)
            except Exception as e:
                logger.error(f"Lỗi tạo công cụ {tool_name}: {e}")
                return None
        else:
            logger.warning(f"Không tìm thấy loại công cụ {tool_name}")
            return None
            
    def add_tool(self, tool: BaseTool) -> int:
        """
        Thêm công cụ vào pipeline
        
        Args:
            tool: Công cụ cần thêm
            
        Returns:
            ID của công cụ trong pipeline
        """
        tool_id = self.next_tool_id
        self.next_tool_id += 1
        
        tool.set_tool_id(tool_id)
        self.tools.append(tool)
        
        logger.info(f"Đã thêm công cụ {tool.display_name} với ID {tool_id}")
        return tool_id
        
    def remove_tool(self, tool_id: int) -> bool:
        """
        Xóa công cụ khỏi pipeline
        
        Args:
            tool_id: ID của công cụ cần xóa
            
        Returns:
            True nếu xóa thành công, False nếu không
        """
        for i, tool in enumerate(self.tools):
            if tool.tool_id == tool_id:
                # Gọi cleanup để giải phóng tài nguyên
                try:
                    tool.cleanup()
                except Exception as e:
                    logger.error(f"Lỗi giải phóng tài nguyên công cụ {tool.display_name}: {e}")
                
                # Xóa công cụ khỏi danh sách
                self.tools.pop(i)
                
                # Xóa kết quả mới nhất
                if tool_id in self.latest_results:
                    del self.latest_results[tool_id]
                    
                logger.info(f"Đã xóa công cụ ID {tool_id}")
                return True
                
        logger.warning(f"Không tìm thấy công cụ ID {tool_id}")
        return False
        
    def get_tool(self, tool_id: int) -> Optional[BaseTool]:
        """
        Lấy công cụ theo ID
        
        Args:
            tool_id: ID của công cụ
            
        Returns:
            Công cụ hoặc None nếu không tìm thấy
        """
        for tool in self.tools:
            if tool.tool_id == tool_id:
                return tool
        return None
        
    def get_tools(self) -> List[BaseTool]:
        """
        Lấy danh sách tất cả các công cụ trong pipeline
        
        Returns:
            Danh sách các công cụ
        """
        return self.tools.copy()
        
    def move_tool(self, tool_id: int, new_position: int) -> bool:
        """
        Di chuyển công cụ đến vị trí mới trong pipeline
        
        Args:
            tool_id: ID của công cụ cần di chuyển
            new_position: Vị trí mới (index)
            
        Returns:
            True nếu di chuyển thành công, False nếu không
        """
        # Tìm công cụ cần di chuyển
        tool_index = None
        for i, tool in enumerate(self.tools):
            if tool.tool_id == tool_id:
                tool_index = i
                break
                
        if tool_index is None:
            logger.warning(f"Không tìm thấy công cụ ID {tool_id}")
            return False
            
        # Giới hạn vị trí mới
        new_position = max(0, min(new_position, len(self.tools) - 1))
        
        # Di chuyển công cụ
        if tool_index != new_position:
            tool = self.tools.pop(tool_index)
            self.tools.insert(new_position, tool)
            logger.info(f"Đã di chuyển công cụ {tool.display_name} từ vị trí {tool_index} đến {new_position}")
            
        return True
        
    def run_pipeline(self, input_image: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Chạy toàn bộ pipeline với ảnh đầu vào hoặc lấy từ camera
        
        Args:
            input_image: Ảnh đầu vào (nếu None, sẽ lấy từ công cụ đầu tiên)
            
        Returns:
            Tuple chứa (ảnh đầu ra, kết quả tổng hợp)
        """
        if not self.tools:
            logger.warning("Không có công cụ nào trong pipeline")
            return input_image, {"error": "Không có công cụ nào trong pipeline"}
            
        start_time = time.time()
        
        # Khởi tạo ngữ cảnh
        context = {}
        
        # Biến để theo dõi ảnh qua các bước
        current_image = input_image
        
        # Chạy từng công cụ trong pipeline
        for tool in self.tools:
            if not tool.enabled:
                logger.debug(f"Bỏ qua công cụ {tool.display_name} (disabled)")
                continue
                
            tool_start_time = time.time()
            
            try:
                # Xử lý với công cụ hiện tại
                current_image, result = tool.process(current_image, context)
                
                # Lưu kết quả
                self.latest_results[tool.tool_id] = result
                
                # Cập nhật ngữ cảnh
                context[f"tool_{tool.tool_id}"] = result
                
                # Tính thời gian xử lý
                processing_time = time.time() - tool_start_time
                logger.debug(f"Công cụ {tool.display_name} xử lý trong {processing_time:.4f}s")
                
            except Exception as e:
                logger.error(f"Lỗi xử lý công cụ {tool.display_name}: {e}")
                # Nếu có lỗi, không dừng pipeline mà tiếp tục với công cụ tiếp theo
                context[f"tool_{tool.tool_id}_error"] = str(e)
                
        # Lưu ảnh đầu vào và đầu ra
        self.latest_input_image = input_image
        self.latest_output_image = current_image
        
        # Tạo kết quả tổng hợp
        total_time = time.time() - start_time
        result_summary = {
            "total_processing_time": total_time,
            "tool_count": len(self.tools),
            "active_tool_count": sum(1 for tool in self.tools if tool.enabled),
            "timestamp": time.time()
        }
        
        logger.debug(f"Pipeline hoàn thành trong {total_time:.4f}s")
        return current_image, result_summary
        
    def get_latest_result(self, tool_id: int) -> Optional[Dict[str, Any]]:
        """
        Lấy kết quả mới nhất của một công cụ
        
        Args:
            tool_id: ID của công cụ
            
        Returns:
            Kết quả mới nhất hoặc None nếu không có
        """
        return self.latest_results.get(tool_id)
        
    def get_latest_results(self) -> Dict[int, Dict[str, Any]]:
        """
        Lấy tất cả kết quả mới nhất
        
        Returns:
            Dictionary chứa ID công cụ và kết quả tương ứng
        """
        return self.latest_results.copy()
        
    def get_latest_input_image(self) -> Optional[np.ndarray]:
        """
        Lấy ảnh đầu vào mới nhất
        
        Returns:
            Ảnh đầu vào mới nhất hoặc None
        """
        return self.latest_input_image
        
    def get_latest_output_image(self) -> Optional[np.ndarray]:
        """
        Lấy ảnh đầu ra mới nhất
        
        Returns:
            Ảnh đầu ra mới nhất hoặc None
        """
        return self.latest_output_image
        
    def update_tool_config(self, tool_id: int, new_config: Dict[str, Any]) -> bool:
        """
        Cập nhật cấu hình của một công cụ
        
        Args:
            tool_id: ID của công cụ
            new_config: Cấu hình mới
            
        Returns:
            True nếu cập nhật thành công, False nếu không
        """
        tool = self.get_tool(tool_id)
        if tool:
            return tool.update_config(new_config)
        return False
        
    def enable_tool(self, tool_id: int, enabled: bool = True) -> bool:
        """
        Bật/tắt công cụ
        
        Args:
            tool_id: ID của công cụ
            enabled: True để bật, False để tắt
            
        Returns:
            True nếu thành công, False nếu không
        """
        tool = self.get_tool(tool_id)
        if tool:
            tool.enabled = enabled
            return True
        return False
        
    def show_tool(self, tool_id: int, visible: bool = True) -> bool:
        """
        Hiển thị/ẩn công cụ trong UI
        
        Args:
            tool_id: ID của công cụ
            visible: True để hiển thị, False để ẩn
            
        Returns:
            True nếu thành công, False nếu không
        """
        tool = self.get_tool(tool_id)
        if tool:
            tool.visible = visible
            return True
        return False
        
    def cleanup(self) -> None:
        """Giải phóng tài nguyên của tất cả các công cụ"""
        for tool in self.tools:
            try:
                tool.cleanup()
            except Exception as e:
                logger.error(f"Lỗi giải phóng tài nguyên công cụ {tool.display_name}: {e}")
        
        # Xóa danh sách công cụ
        self.tools.clear()
        self.latest_results.clear()
        self.latest_input_image = None
        self.latest_output_image = None
        
        logger.info("Đã giải phóng tài nguyên tất cả các công cụ")
