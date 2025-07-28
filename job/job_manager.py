
import json
import os
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Union, cast

import numpy as np

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("JobManager")

class ToolConfig:
    """Lớp cấu hình cho công cụ, với khả năng xác thực và mặc định các tham số"""
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        self._config = config_dict or {}  # Sử dụng dict trống nếu None
        self._defaults: Dict[str, Any] = {}
        self._validators: Dict[str, Any] = {}
        
    def set_default(self, key: str, value: Any) -> None:
        """Đặt giá trị mặc định cho một tham số"""
        self._defaults[key] = value
        if key not in self._config:
            self._config[key] = value
            
    def set_validator(self, key: str, validator_func) -> None:
        """Đặt hàm xác thực cho một tham số"""
        self._validators[key] = validator_func
        
    def set(self, key: str, value: Any) -> bool:
        """Đặt giá trị cho một tham số, trả về True nếu hợp lệ"""
        if key in self._validators:
            if not self._validators[key](value):
                logger.warning(f"Giá trị không hợp lệ cho {key}: {value}")
                return False
        self._config[key] = value
        return True
        
    def get(self, key: str, default: Any = None) -> Any:
        """Lấy giá trị của một tham số"""
        return self._config.get(key, default if default is not None else self._defaults.get(key))
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi cấu hình thành từ điển"""
        return self._config.copy()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ToolConfig':
        """Tạo cấu hình từ từ điển"""
        return cls(config_dict)


class Tool:
    """Lớp cơ sở cho tất cả các công cụ xử lý"""
    
    def __init__(self, name: str, config: Optional[Union[Dict[str, Any], ToolConfig]] = None):
        self.name = name
        if config is None:
            self.config = ToolConfig({})
        elif isinstance(config, ToolConfig):
            self.config = config
        else:
            self.config = ToolConfig(config)
        self.setup_config()
        
    def setup_config(self) -> None:
        """Thiết lập các giá trị mặc định và xác thực cho cấu hình"""
        pass
        
    def process(self, image: np.ndarray, context: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Xử lý hình ảnh đầu vào
        
        Args:
            image: Hình ảnh đầu vào (numpy array)
            context: Ngữ cảnh bổ sung từ các công cụ trước đó
            
        Returns:
            Tuple chứa hình ảnh đã xử lý và kết quả bổ sung
        """
        # Lớp cơ sở mặc định trả về hình ảnh không thay đổi
        return image, {"warning": "Không có xử lý được áp dụng"}
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi công cụ thành từ điển để lưu trữ"""
        return {
            'name': self.name,
            'type': self.__class__.__name__,
            'config': self.config.to_dict()
        }
    
    @staticmethod
    def from_dict(d: Dict[str, Any], tool_registry: Dict[str, type]) -> 'Tool':
        """
        Tạo công cụ từ từ điển
        
        Args:
            d: Từ điển mô tả công cụ
            tool_registry: Đăng ký các loại công cụ có sẵn
            
        Returns:
            Công cụ đã được khởi tạo
        """
        tool_type = d.get('type')
        if tool_type in tool_registry:
            return tool_registry[tool_type](d['name'], ToolConfig.from_dict(d.get('config', {})))
        # Fallback cho khả năng tương thích ngược
        return GenericTool(d['name'], ToolConfig.from_dict(d.get('config', {})))


class GenericTool(Tool):
    """Công cụ chung khi không tìm thấy loại công cụ cụ thể"""
    
    def process(self, image: np.ndarray, context: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        ctx = context or {}
        logger.warning(f"Sử dụng công cụ chung cho {self.name}, không có xử lý được áp dụng")
        return image, {"warning": f"Không có xử lý cho công cụ {self.name}"}


class Job:
    """Đại diện cho một chuỗi công cụ xử lý hình ảnh"""
    
    def __init__(self, name: str, tools: Optional[List[Tool]] = None, description: str = ""):
        self.name = name
        self.description = description
        self.tools = tools or []  # Sử dụng list trống nếu None
        self.results: Dict[str, Any] = {}
        self.status = "ready"  # ready, running, completed, failed
        self.last_run_time = 0.0
        self.execution_time = 0.0
        
    def add_tool(self, tool: Tool) -> None:
        """Thêm một công cụ vào chuỗi xử lý"""
        self.tools.append(tool)
        self.status = "ready"
        
    def remove_tool(self, index: int) -> bool:
        """Xóa một công cụ theo chỉ số"""
        if 0 <= index < len(self.tools):
            del self.tools[index]
            self.status = "ready"
            return True
        return False
        
    def move_tool(self, from_index: int, to_index: int) -> bool:
        """Di chuyển một công cụ từ vị trí này sang vị trí khác"""
        if 0 <= from_index < len(self.tools) and 0 <= to_index < len(self.tools):
            tool = self.tools.pop(from_index)
            self.tools.insert(to_index, tool)
            return True
        return False
        
    def edit_tool(self, index: int, new_tool: Tool) -> bool:
        """Chỉnh sửa một công cụ theo chỉ số"""
        if 0 <= index < len(self.tools):
            self.tools[index] = new_tool
            self.status = "ready"
            return True
        return False
        
    def run(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Thực thi chuỗi công cụ xử lý trên hình ảnh
        
        Args:
            image: Hình ảnh đầu vào (numpy array)
            
        Returns:
            Tuple chứa hình ảnh cuối cùng và kết quả tổng hợp
        """
        if not self.tools:
            logger.warning(f"Không có công cụ nào trong job {self.name}")
            return image, {"error": "Không có công cụ nào"}
            
        self.status = "running"
        self.last_run_time = time.time()
        self.results = {}
        
        try:
            start_time = time.time()
            context: Dict[str, Any] = {}
            processed_image = image.copy()
            
            for i, tool in enumerate(self.tools):
                logger.info(f"Đang chạy công cụ {i+1}/{len(self.tools)}: {tool.name}")
                tool_start = time.time()
                
                processed_image, result = tool.process(processed_image, context)
                tool_time = time.time() - tool_start
                
                # Cập nhật ngữ cảnh cho công cụ tiếp theo
                context.update(result)
                
                # Lưu kết quả của công cụ
                self.results[tool.name] = {
                    "data": result,
                    "execution_time": tool_time
                }
                
            self.execution_time = time.time() - start_time
            self.status = "completed"
            logger.info(f"Job {self.name} hoàn thành trong {self.execution_time:.2f}s")
            
            return processed_image, {
                "job_name": self.name,
                "execution_time": self.execution_time,
                "results": self.results
            }
            
        except Exception as e:
            self.status = "failed"
            error_msg = f"Lỗi khi chạy job {self.name}: {str(e)}"
            logger.error(error_msg)
            return image, {"error": error_msg}
            
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi job thành từ điển để lưu trữ"""
        return {
            'name': self.name,
            'description': self.description,
            'tools': [t.to_dict() for t in self.tools],
            'status': self.status,
            'last_run_time': self.last_run_time,
            'execution_time': self.execution_time
        }
    
    @staticmethod
    def from_dict(d: Dict[str, Any], tool_registry: Dict[str, type]) -> 'Job':
        """Tạo job từ từ điển"""
        tools = [Tool.from_dict(td, tool_registry) for td in d.get('tools', [])]
        job = Job(d['name'], tools, d.get('description', ''))
        job.status = d.get('status', 'ready')
        job.last_run_time = d.get('last_run_time', 0)
        job.execution_time = d.get('execution_time', 0)
        return job


class JobManager:
    """Quản lý tất cả các job và công cụ có sẵn"""
    
    def __init__(self):
        self.jobs: List[Job] = []
        self.current_job_index = -1
        self.tool_registry: Dict[str, type] = {}  # map tool_type -> Tool class
        self.register_default_tools()
        
    def register_tool(self, tool_class: type) -> None:
        """Đăng ký một loại công cụ mới"""
        self.tool_registry[tool_class.__name__] = tool_class
        
    def register_default_tools(self) -> None:
        """Đăng ký các loại công cụ mặc định"""
        # Đăng ký công cụ chung trước
        self.register_tool(GenericTool)
        
        # Import các công cụ cụ thể ở đây để tránh import vòng tròn
        try:
            from detection.ocr_tool import OcrTool
            self.register_tool(OcrTool)
        except ImportError:
            logger.warning("Không thể đăng ký OcrTool")
            
        try:
            from detection.edge_detection import EdgeDetectionTool
            self.register_tool(EdgeDetectionTool)
        except ImportError:
            logger.warning("Không thể đăng ký EdgeDetectionTool")
        
    def create_tool(self, tool_type: str, name: str, config: Optional[Dict[str, Any]] = None) -> Optional[Tool]:
        """
        Tạo một công cụ mới từ loại đã đăng ký
        
        Args:
            tool_type: Loại công cụ (tên lớp)
            name: Tên công cụ
            config: Cấu hình công cụ
            
        Returns:
            Công cụ đã được khởi tạo hoặc None nếu loại không tồn tại
        """
        if tool_type in self.tool_registry:
            tool_class = self.tool_registry[tool_type]
            return tool_class(name, ToolConfig(config or {}))
        logger.warning(f"Loại công cụ không hợp lệ: {tool_type}")
        return None
        
    def add_job(self, job: Job) -> None:
        """Thêm một job mới và đặt làm job hiện tại"""
        self.jobs.append(job)
        self.current_job_index = len(self.jobs) - 1
        
    def remove_job(self, index: int) -> bool:
        """Xóa một job theo chỉ số"""
        if 0 <= index < len(self.jobs):
            del self.jobs[index]
            # Cập nhật chỉ số job hiện tại
            if not self.jobs:
                self.current_job_index = -1
            elif index <= self.current_job_index:
                self.current_job_index = max(0, self.current_job_index - 1)
            return True
        return False
        
    def set_current_job(self, index: int) -> bool:
        """Đặt job hiện tại theo chỉ số"""
        if 0 <= index < len(self.jobs):
            self.current_job_index = index
            return True
        return False
        
    def get_current_job(self) -> Optional[Job]:
        """Lấy job hiện tại"""
        if 0 <= self.current_job_index < len(self.jobs):
            return self.jobs[self.current_job_index]
        return None
        
    def run_job(self, job_index: int, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Chạy một job theo chỉ số
        
        Args:
            job_index: Chỉ số của job cần chạy
            image: Hình ảnh đầu vào
            
        Returns:
            Tuple chứa hình ảnh đã xử lý và kết quả
        """
        if 0 <= job_index < len(self.jobs):
            return self.jobs[job_index].run(image)
        return image, {"error": "Chỉ số job không hợp lệ"}
        
    def run_current_job(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Chạy job hiện tại"""
        current_job = self.get_current_job()
        if current_job:
            return current_job.run(image)
        return image, {"error": "Không có job hiện tại"}
        
    def save_job(self, job_index: int, path: str) -> bool:
        """Lưu một job vào file"""
        if not (0 <= job_index < len(self.jobs)):
            logger.error(f"Chỉ số job không hợp lệ: {job_index}")
            return False
            
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.jobs[job_index].to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"Đã lưu job vào {path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu job: {str(e)}")
            return False
            
    def save_current_job(self, path: str) -> bool:
        """Lưu job hiện tại vào file"""
        if self.current_job_index < 0:
            logger.error("Không có job hiện tại để lưu")
            return False
        return self.save_job(self.current_job_index, path)
        
    def save_all_jobs(self, path: str) -> bool:
        """Lưu tất cả các job vào file"""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({
                    'jobs': [job.to_dict() for job in self.jobs],
                    'current_job_index': self.current_job_index
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"Đã lưu tất cả job vào {path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu tất cả job: {str(e)}")
            return False
            
    def load_job(self, path: str) -> Optional[Job]:
        """Tải một job từ file và thêm vào danh sách"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                job = Job.from_dict(data, self.tool_registry)
                self.add_job(job)
                logger.info(f"Đã tải job từ {path}")
                return job
        except Exception as e:
            logger.error(f"Lỗi khi tải job: {str(e)}")
            return None
            
    def load_all_jobs(self, path: str) -> bool:
        """Tải tất cả các job từ file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.jobs = [Job.from_dict(jd, self.tool_registry) for jd in data.get('jobs', [])]
                self.current_job_index = data.get('current_job_index', 0 if self.jobs else -1)
                logger.info(f"Đã tải {len(self.jobs)} job từ {path}")
                return True
        except Exception as e:
            logger.error(f"Lỗi khi tải tất cả job: {str(e)}")
            return False
            
    def get_available_tool_types(self) -> List[str]:
        """Lấy danh sách các loại công cụ có sẵn"""
        return list(self.tool_registry.keys())
        
    def get_job_list(self) -> List[Job]:
        """Lấy danh sách các job"""
        return self.jobs
        
    def create_default_job(self, name: str = "New Job") -> Job:
        """Tạo một job mặc định với tên được chỉ định"""
        job = Job(name)
        self.add_job(job)
        return job
        
    # Hàm tương thích ngược với giao diện cũ
    def get_tool_list(self) -> List[Tool]:
        """Lấy danh sách các công cụ có sẵn (tương thích với giao diện cũ)"""
        tools: List[Tool] = []
        for tool_type in self.get_available_tool_types():
            if tool_type != "GenericTool":
                tool = self.create_tool(tool_type, tool_type)
                if tool:
                    tools.append(tool)
        return tools
