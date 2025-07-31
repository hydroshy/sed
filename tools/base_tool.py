
class ToolConfig:
    """Lớp cấu hình cho công cụ, với khả năng xác thực và mặc định các tham số"""
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
    def to_dict(self):
        return self._config.copy()
    @classmethod
    def from_dict(cls, config_dict):
        return cls(config_dict)

class BaseTool:
    def set_tool_id(self, tool_id):
        self.tool_id = tool_id
    """
    Lớp cơ sở cho tất cả các tool xử lý trong pipeline.
    """
    def __init__(self, config=None, name=None):
        self.config = config or {}
        self.name = name or self.__class__.__name__
        self.display_name = self.name
        self.enabled = True

    def setup(self):
        """Khởi tạo tài nguyên nếu cần"""
        pass

    def run(self, frame):
        """Xử lý frame, trả về kết quả"""
        raise NotImplementedError("Tool phải override hàm run")

    def teardown(self):
        """Giải phóng tài nguyên nếu cần"""
        pass

class GenericTool(BaseTool):
    """Công cụ chung khi không tìm thấy loại công cụ cụ thể"""
    def process(self, image, context=None):
        return image, {"warning": f"Không có xử lý cho công cụ {self.name}"}
