
"""
Định nghĩa lớp cơ sở cho tất cả các tool trong hệ thống SED
"""
from typing import Dict, Any, Tuple, Optional, List, Union
import logging
import numpy as np

logger = logging.getLogger(__name__)

class ToolConfig:
    """
    Lớp cấu hình cho công cụ, với khả năng xác thực và mặc định các tham số
    """
    def __init__(self, config_dict=None):
        self._config = config_dict or {}
        self._defaults = {}
        self._validators = {}
    def set_default(self, key, value):
        self._defaults[key] = value
        if key not in self._config:
            self._config[key] = value
    def set_validator(self, key, validator_func):
        self._validators[key] = validator_func
    def set(self, key, value):
        if key in self._validators:
            if not self._validators[key](value):
                return False
        self._config[key] = value
        return True
    def get(self, key, default=None):
        return self._config.get(key, default if default is not None else self._defaults.get(key))
    def __contains__(self, key):
        return key in self._config
    def __getitem__(self, key):
        """Allow dictionary-style access for getting values"""
        return self._config[key]
    def __setitem__(self, key, value):
        """Allow dictionary-style access for setting values"""
        self._config[key] = value
    def to_dict(self):
        """Chuyển đổi cấu hình thành dictionary"""
        return self._config.copy()
        
    @classmethod
    def from_dict(cls, config_dict):
        """Tạo cấu hình từ dictionary"""
        return cls(config_dict)


class BaseTool:
    """
    Lớp cơ sở cho tất cả các tool xử lý trong pipeline.
    Mỗi tool đều phải có input và output chuẩn.
    """
    def __init__(self, name: str = None, config: Optional[Union[Dict[str, Any], ToolConfig]] = None, tool_id: Optional[int] = None):
        """
        Khởi tạo công cụ với tên và cấu hình
        
        Args:
            name: Tên hiển thị của công cụ
            config: Cấu hình của công cụ (dict hoặc ToolConfig)
            tool_id: ID của công cụ trong job
        """
        self.display_name = name or self.__class__.__name__
        self.tool_id = tool_id
        
        # Always use ToolConfig for consistent interface
        if isinstance(config, ToolConfig):
            self.config = config
        elif isinstance(config, dict):
            self.config = ToolConfig(config)
        else:
            self.config = ToolConfig()
            
        # Khởi tạo cấu hình mặc định
        self.setup_config()
        
        # Trạng thái của công cụ
        self.enabled = True
        self.visible = True
        self.has_ui = True  # Công cụ này có UI hay không
        
        # Kết nối input/output
        self.inputs = []      # Danh sách các tool đầu vào
        self.outputs = []     # Danh sách các tool đầu ra
        self.input_data = {}  # Dữ liệu đầu vào từ các tool trước đó
        self.output_data = {} # Dữ liệu đầu ra cho các tool tiếp theo
        self.source_tool = None  # Tool nguồn cung cấp input chính
        
    def setup_config(self) -> None:
        """
        Thiết lập cấu hình mặc định cho công cụ.
        Lớp con phải override phương thức này để thiết lập cấu hình mặc định.
        """
        pass
        
    def process(self, image: np.ndarray, context: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Xử lý hình ảnh đầu vào và trả về hình ảnh đã xử lý cùng với kết quả
        
        Args:
            image: Hình ảnh đầu vào (numpy array)
            context: Ngữ cảnh từ các công cụ trước (optional)
            
        Returns:
            Tuple chứa (hình ảnh đã xử lý, kết quả)
        """
        logger.warning(f"Tool {self.display_name} chưa triển khai phương thức process()")
        return image, {"warning": f"Không có xử lý cho công cụ {self.display_name}"}
        
    def set_tool_id(self, tool_id: int) -> None:
        """Thiết lập ID cho công cụ"""
        self.tool_id = tool_id
        
    def get_config(self) -> Dict[str, Any]:
        """Lấy cấu hình của công cụ dưới dạng dictionary"""
        return self.config.to_dict()
        
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """
        Cập nhật cấu hình của công cụ
        
        Args:
            new_config: Cấu hình mới
            
        Returns:
            True nếu cập nhật thành công, False nếu không
        """
        try:
            for key, value in new_config.items():
                if not self.config.set(key, value):
                    logger.warning(f"Invalid config value for {key}: {value}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error updating config for {self.display_name}: {e}")
            return False
            
    def get_info(self) -> Dict[str, Any]:
        """
        Lấy thông tin về công cụ
        
        Returns:
            Dictionary chứa thông tin về công cụ
        """
        return {
            'tool_type': self.__class__.__name__,
            'display_name': self.display_name,
            'tool_id': self.tool_id,
            'enabled': self.enabled,
            'visible': self.visible,
            'has_ui': self.has_ui,
            'config': self.config.to_dict()
        }
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Chuyển đổi công cụ thành dictionary để lưu trữ
        
        Returns:
            Dictionary chứa thông tin về công cụ
        """
        return {
            'tool_type': self.__class__.__name__,
            'display_name': self.display_name,
            'tool_id': self.tool_id,
            'enabled': self.enabled,
            'visible': self.visible,
            'has_ui': self.has_ui,
            'config': self.config.to_dict()
        }
        
    def add_input(self, tool: 'BaseTool') -> None:
        """Thêm một tool làm input cho tool này"""
        if tool not in self.inputs:
            self.inputs.append(tool)
            
    def add_output(self, tool: 'BaseTool') -> None:
        """Thêm một tool làm output cho tool này"""
        if tool not in self.outputs:
            self.outputs.append(tool)
            # Tự động thêm tool này làm input cho tool đầu ra
            tool.add_input(self)
            
    def set_source_tool(self, tool: 'BaseTool') -> None:
        """Đặt tool nguồn cung cấp dữ liệu chính"""
        self.source_tool = tool
        if tool not in self.inputs:
            self.inputs.append(tool)
            
    def get_outputs(self) -> List['BaseTool']:
        """Lấy danh sách các tool đầu ra"""
        return self.outputs
        
    def get_inputs(self) -> List['BaseTool']:
        """Lấy danh sách các tool đầu vào"""
        return self.inputs
        
    def get_source_tool(self) -> Optional['BaseTool']:
        """Lấy tool nguồn cung cấp dữ liệu chính"""
        return self.source_tool
        
    def cleanup(self) -> None:
        """
        Giải phóng tài nguyên nếu cần
        Lớp con có thể override phương thức này để giải phóng tài nguyên
        """
        pass
        
    @staticmethod
    def from_dict(data: Dict[str, Any], tool_registry: Dict[str, type] = None) -> 'BaseTool':
        """
        Tạo công cụ từ dictionary
        
        Args:
            data: Dictionary chứa dữ liệu công cụ
            tool_registry: Registry các loại công cụ có sẵn
            
        Returns:
            Công cụ được tạo
        """
        if not tool_registry:
            return GenericTool(name=data.get('display_name'), config=data.get('config', {}), tool_id=data.get('tool_id'))
            
        tool_type = data.get('tool_type')
        if tool_type in tool_registry:
            # Tạo công cụ cụ thể
            tool_class = tool_registry[tool_type]
            tool = tool_class(
                name=data.get('display_name'),
                config=data.get('config', {}),
                tool_id=data.get('tool_id')
            )
            # Đặt các thuộc tính khác
            tool.enabled = data.get('enabled', True)
            tool.visible = data.get('visible', True)
            tool.has_ui = data.get('has_ui', True)
            return tool
        else:
            # Tạo công cụ generic khi không tìm thấy loại
            logger.warning(f"Tool type {tool_type} not found in registry, creating GenericTool")
            return GenericTool(name=data.get('display_name'), config=data.get('config', {}), tool_id=data.get('tool_id'))

class GenericTool(BaseTool):
    """
    Công cụ chung khi không tìm thấy loại công cụ cụ thể
    """
    def process(self, image: np.ndarray, context: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Trả về hình ảnh không thay đổi"""
        return image, {"warning": f"Không có xử lý cho công cụ {self.display_name}"}
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Chuyển đổi công cụ thành dictionary để lưu trữ
        """
        data = super().to_dict()
        # Add any GenericTool specific fields here
        return data
