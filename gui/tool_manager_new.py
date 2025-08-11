"""
Tool Manager mới cho hệ thống SED với giao diện chuẩn cho các công cụ
"""
import logging
from typing import Dict, Any, List, Optional, Union, Callable
from PyQt5.QtCore import QObject, pyqtSignal

from tools.base_tool import BaseTool, ToolConfig
from job.job_manager_new import JobManager

logger = logging.getLogger(__name__)

class ToolManager(QObject):
    """
    Quản lý các công cụ trong giao diện người dùng
    """
    
    # Tín hiệu
    tool_added = pyqtSignal(int)  # tool_id
    tool_removed = pyqtSignal(int)  # tool_id
    tool_moved = pyqtSignal(int, int)  # tool_id, new_position
    tool_config_changed = pyqtSignal(int)  # tool_id
    tool_enabled_changed = pyqtSignal(int, bool)  # tool_id, enabled
    tool_visibility_changed = pyqtSignal(int, bool)  # tool_id, visible
    
    def __init__(self, parent=None):
        """
        Khởi tạo ToolManager
        
        Args:
            parent: Đối tượng cha
        """
        super().__init__(parent)
        
        # JobManager để quản lý các công cụ
        self.job_manager = JobManager()
        
        # Ánh xạ tool_id -> widget (được thiết lập bởi UI)
        self.tool_widgets: Dict[int, Any] = {}
        
        # Công cụ hiện tại được chọn
        self.current_tool_id: Optional[int] = None
        
    def get_available_tools(self) -> List[str]:
        """
        Lấy danh sách các công cụ có sẵn để thêm vào pipeline
        
        Returns:
            Danh sách tên các công cụ có sẵn
        """
        return self.job_manager.get_available_tools()
        
    def add_tool(self, tool_name: str, config: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """
        Thêm một công cụ mới vào pipeline
        
        Args:
            tool_name: Tên loại công cụ
            config: Cấu hình cho công cụ
            
        Returns:
            ID của công cụ nếu thành công, None nếu thất bại
        """
        tool = self.job_manager.create_tool(tool_name, config)
        if tool:
            tool_id = self.job_manager.add_tool(tool)
            self.tool_added.emit(tool_id)
            
            # Nếu chưa có công cụ nào được chọn, chọn công cụ này
            if self.current_tool_id is None:
                self.set_current_tool(tool_id)
                
            return tool_id
        return None
        
    def remove_tool(self, tool_id: int) -> bool:
        """
        Xóa công cụ khỏi pipeline
        
        Args:
            tool_id: ID của công cụ cần xóa
            
        Returns:
            True nếu xóa thành công, False nếu không
        """
        result = self.job_manager.remove_tool(tool_id)
        if result:
            # Xóa widget nếu có
            if tool_id in self.tool_widgets:
                del self.tool_widgets[tool_id]
                
            # Nếu công cụ hiện tại bị xóa, đặt lại
            if self.current_tool_id == tool_id:
                tools = self.get_tools()
                self.current_tool_id = tools[0].tool_id if tools else None
                
            self.tool_removed.emit(tool_id)
            
        return result
        
    def get_tools(self) -> List[BaseTool]:
        """
        Lấy danh sách tất cả các công cụ trong pipeline
        
        Returns:
            Danh sách các công cụ
        """
        return self.job_manager.get_tools()
        
    def get_tool(self, tool_id: int) -> Optional[BaseTool]:
        """
        Lấy công cụ theo ID
        
        Args:
            tool_id: ID của công cụ
            
        Returns:
            Công cụ hoặc None nếu không tìm thấy
        """
        return self.job_manager.get_tool(tool_id)
        
    def move_tool(self, tool_id: int, new_position: int) -> bool:
        """
        Di chuyển công cụ đến vị trí mới trong pipeline
        
        Args:
            tool_id: ID của công cụ cần di chuyển
            new_position: Vị trí mới (index)
            
        Returns:
            True nếu di chuyển thành công, False nếu không
        """
        result = self.job_manager.move_tool(tool_id, new_position)
        if result:
            self.tool_moved.emit(tool_id, new_position)
        return result
        
    def update_tool_config(self, tool_id: int, new_config: Dict[str, Any]) -> bool:
        """
        Cập nhật cấu hình của một công cụ
        
        Args:
            tool_id: ID của công cụ
            new_config: Cấu hình mới
            
        Returns:
            True nếu cập nhật thành công, False nếu không
        """
        result = self.job_manager.update_tool_config(tool_id, new_config)
        if result:
            self.tool_config_changed.emit(tool_id)
        return result
        
    def enable_tool(self, tool_id: int, enabled: bool = True) -> bool:
        """
        Bật/tắt công cụ
        
        Args:
            tool_id: ID của công cụ
            enabled: True để bật, False để tắt
            
        Returns:
            True nếu thành công, False nếu không
        """
        result = self.job_manager.enable_tool(tool_id, enabled)
        if result:
            self.tool_enabled_changed.emit(tool_id, enabled)
        return result
        
    def show_tool(self, tool_id: int, visible: bool = True) -> bool:
        """
        Hiển thị/ẩn công cụ trong UI
        
        Args:
            tool_id: ID của công cụ
            visible: True để hiển thị, False để ẩn
            
        Returns:
            True nếu thành công, False nếu không
        """
        result = self.job_manager.show_tool(tool_id, visible)
        if result:
            self.tool_visibility_changed.emit(tool_id, visible)
        return result
        
    def set_current_tool(self, tool_id: Optional[int]) -> bool:
        """
        Đặt công cụ hiện tại
        
        Args:
            tool_id: ID của công cụ cần đặt làm hiện tại, hoặc None để bỏ chọn
            
        Returns:
            True nếu thành công, False nếu không
        """
        if tool_id is None:
            self.current_tool_id = None
            return True
            
        tool = self.get_tool(tool_id)
        if tool:
            self.current_tool_id = tool_id
            return True
        return False
        
    def get_current_tool(self) -> Optional[BaseTool]:
        """
        Lấy công cụ hiện tại
        
        Returns:
            Công cụ hiện tại hoặc None nếu không có
        """
        if self.current_tool_id is not None:
            return self.get_tool(self.current_tool_id)
        return None
        
    def register_tool_factory(self, tool_name: str, factory_func: Callable) -> None:
        """
        Đăng ký factory function cho một loại công cụ
        
        Args:
            tool_name: Tên hiển thị của loại công cụ
            factory_func: Hàm factory để tạo công cụ
        """
        self.job_manager.register_tool_factory(tool_name, factory_func)
        
    def register_tool_widget(self, tool_id: int, widget: Any) -> None:
        """
        Đăng ký widget cho một công cụ
        
        Args:
            tool_id: ID của công cụ
            widget: Widget quản lý công cụ
        """
        self.tool_widgets[tool_id] = widget
        
    def get_tool_widget(self, tool_id: int) -> Optional[Any]:
        """
        Lấy widget của một công cụ
        
        Args:
            tool_id: ID của công cụ
            
        Returns:
            Widget của công cụ hoặc None nếu không có
        """
        return self.tool_widgets.get(tool_id)
        
    def run_pipeline(self, input_image=None):
        """
        Chạy toàn bộ pipeline với ảnh đầu vào
        
        Args:
            input_image: Ảnh đầu vào (nếu None, sẽ lấy từ camera)
            
        Returns:
            Tuple chứa (ảnh đầu ra, kết quả)
        """
        return self.job_manager.run_pipeline(input_image)
        
    def cleanup(self) -> None:
        """Giải phóng tài nguyên"""
        self.job_manager.cleanup()
        self.tool_widgets.clear()
        self.current_tool_id = None
