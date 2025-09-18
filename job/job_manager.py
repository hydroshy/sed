import json
import os
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Union, cast

import numpy as np

# Import Qt for threading
try:
    from PyQt5.QtCore import QThread, QObject, pyqtSignal
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("JobManager")

from tools.base_tool import ToolConfig, BaseTool, GenericTool
from utils.debug_utils import debug_log


class JobWorkerThread(QThread if QT_AVAILABLE else object):
    """Worker thread for job execution to avoid blocking UI"""
    
    if QT_AVAILABLE:
        job_completed = pyqtSignal(str, dict)  # job_name, results
        job_error = pyqtSignal(str, str)       # job_name, error_message
    
    def __init__(self, job, image, context=None):
        if QT_AVAILABLE:
            super().__init__()
        self.job = job
        self.image = image
        self.context = context or {}
        
    def run(self):
        """Execute job in background thread"""
        try:
            results = self.job.process_image(self.image, self.context)
            if QT_AVAILABLE:
                self.job_completed.emit(self.job.name, results)
        except Exception as e:
            error_msg = f"Job execution failed: {str(e)}"
            logger.error(error_msg)
            if QT_AVAILABLE:
                self.job_error.emit(self.job.name, error_msg)


class Job:
    """Đại diện cho một chuỗi công cụ xử lý hình ảnh với cấu trúc input/output"""
    
    def __init__(self, name: str, tools: Optional[List[BaseTool]] = None, description: str = ""):
        self.name = name
        self.description = description
        self.tools = tools or []  # Sử dụng list trống nếu None
        self.results: Dict[str, Any] = {}
        self.status = "ready"  # ready, running, completed, failed
        self.last_run_time = 0.0
        self.execution_time = 0.0
        self._next_tool_id = 1  # Counter for tool IDs
        
        # Thông tin cấu trúc workflow
        self.start_tools: List[BaseTool] = []  # Các tools bắt đầu (không có input)
        self.end_tools: List[BaseTool] = []    # Các tools kết thúc (không có output)
        
        # Assign IDs to existing tools
        self._assign_tool_ids()
        
        # Khởi tạo workflow nếu có công cụ
        if tools:
            self._rebuild_workflow()
        
    def _assign_tool_ids(self) -> None:
        """Assign IDs to tools that don't have them"""
        for tool in self.tools:
            if tool.tool_id is None:
                tool.set_tool_id(self._next_tool_id)
                self._next_tool_id += 1
                
    def _rebuild_workflow(self) -> None:
        """Xây dựng lại cấu trúc workflow từ các công cụ hiện có"""
        self.start_tools = []
        self.end_tools = []
        
        # Tìm các công cụ đầu và cuối
        for tool in self.tools:
            if not tool.get_inputs():
                self.start_tools.append(tool)
            if not tool.get_outputs():
                self.end_tools.append(tool)
        
    def add_tool(self, tool: Union[BaseTool, Dict[str, Any]], source_tool_id: Optional[int] = None) -> Optional[BaseTool]:
        """
        Thêm một công cụ vào chuỗi xử lý và kết nối với tool nguồn nếu được chỉ định
        
        Args:
            tool: Công cụ cần thêm hoặc dictionary cấu hình
            source_tool_id: ID của tool nguồn cung cấp dữ liệu đầu vào (optional)
            
        Returns:
            Công cụ đã được thêm hoặc None nếu có lỗi
        """
        # Debug log
        debug_log(f"Adding tool to job: {self.name}", logging.INFO)
        tool_name = getattr(tool, 'name', 'Unknown') if not isinstance(tool, dict) else tool.get('name', 'Unknown dict')
        tool_display_name = getattr(tool, 'display_name', 'No display name') if not isinstance(tool, dict) else tool.get('display_name', 'No display name')
        tool_type = type(tool).__name__
        debug_log(f"Tool details: name={tool_name}, display_name={tool_display_name}, type={tool_type}", logging.INFO)
        
        # Kiểm tra nếu tool là dictionary thay vì BaseTool
        if isinstance(tool, dict):
            # Convert dict to BaseTool
            from tools.base_tool import GenericTool
            if 'model_name' in tool:
                # Có vẻ là DetectTool
                display_name = f"Detect ({tool.get('model_name', 'Unknown')})"
            else:
                display_name = "Generic Tool"
            
            tool_obj = GenericTool(name=display_name, config=tool)
            tool = tool_obj
        
        # Gán ID nếu chưa có
        if not hasattr(tool, 'tool_id') or tool.tool_id is None:
            if hasattr(tool, 'set_tool_id'):
                tool.set_tool_id(self._next_tool_id)
            else:
                # Fallback nếu không có phương thức set_tool_id
                tool.tool_id = self._next_tool_id
            self._next_tool_id += 1
            debug_log(f"Assigned tool ID: {tool.tool_id}", logging.INFO)
        else:
            debug_log(f"Tool already has ID: {tool.tool_id}", logging.INFO)
        
        # Thêm tool vào danh sách
        self.tools.append(tool)
        debug_log(f"Added tool to job. Job now has {len(self.tools)} tools", logging.INFO)
        
        # Kiểm tra xem tool đã được thêm chưa
        found = False
        for idx, t in enumerate(self.tools):
            if hasattr(t, 'tool_id') and hasattr(tool, 'tool_id') and t.tool_id == tool.tool_id:
                found = True
                t_name = getattr(t, 'name', 'Unknown')
                t_display = getattr(t, 'display_name', 'No display')
                debug_log(f"Verified tool in position {idx}: ID={t.tool_id}, name={t_name}, display={t_display}", logging.INFO)
                break
        
        if not found:
            logger.warning(f"Tool was not found in tools list after adding! This is a bug.")
        
        # Kết nối với tool nguồn nếu được chỉ định
        if source_tool_id is not None:
            source_tool = self.get_tool_by_id(source_tool_id)
            if source_tool:
                source_tool.add_output(tool)
                tool.set_source_tool(source_tool)
            else:
                logger.warning(f"Không tìm thấy tool nguồn với ID {source_tool_id}")
        
        # Cập nhật workflow
        self._rebuild_workflow()
        
        self.status = "ready"
        
        # Log với tên hiển thị
        display_name = tool.display_name if hasattr(tool, 'display_name') else "Unknown Tool"
        debug_log(f"Added tool: {display_name} to job {self.name}", logging.INFO)
        
        return tool
        
    def get_tool_by_id(self, tool_id: int) -> Optional[BaseTool]:
        """Get tool by ID"""
        for tool in self.tools:
            if tool.tool_id == tool_id:
                return tool
        return None
        
    def connect_tools(self, source_tool_id: int, target_tool_id: int) -> bool:
        """
        Kết nối hai công cụ với nhau trong workflow
        
        Args:
            source_tool_id: ID của công cụ nguồn
            target_tool_id: ID của công cụ đích
            
        Returns:
            True nếu kết nối thành công, False nếu không
        """
        source_tool = self.get_tool_by_id(source_tool_id)
        target_tool = self.get_tool_by_id(target_tool_id)
        
        if not source_tool or not target_tool:
            logger.warning(f"Không tìm thấy công cụ với ID {source_tool_id} hoặc {target_tool_id}")
            return False
            
        # Tránh kết nối vòng lặp
        if source_tool == target_tool:
            logger.warning(f"Không thể kết nối công cụ với chính nó: {source_tool.display_name}")
            return False
            
        # Tạo kết nối
        source_tool.add_output(target_tool)
        # target_tool.add_input(source_tool) - already handled in add_output
        
        # Cập nhật workflow
        self._rebuild_workflow()
        
        debug_log(f"Đã kết nối: {source_tool.display_name} -> {target_tool.display_name}", logging.INFO)
        return True
        
    def disconnect_tools(self, source_tool_id: int, target_tool_id: int) -> bool:
        """
        Ngắt kết nối giữa hai công cụ trong workflow
        
        Args:
            source_tool_id: ID của công cụ nguồn
            target_tool_id: ID của công cụ đích
            
        Returns:
            True nếu ngắt kết nối thành công, False nếu không
        """
        source_tool = self.get_tool_by_id(source_tool_id)
        target_tool = self.get_tool_by_id(target_tool_id)
        
        if not source_tool or not target_tool:
            logger.warning(f"Không tìm thấy công cụ với ID {source_tool_id} hoặc {target_tool_id}")
            return False
            
        # Xóa kết nối
        if target_tool in source_tool.outputs:
            source_tool.outputs.remove(target_tool)
            
        if source_tool in target_tool.inputs:
            target_tool.inputs.remove(source_tool)
            
        # Nếu source_tool là source_tool của target_tool, đặt lại
        if target_tool.source_tool == source_tool:
            target_tool.source_tool = None
            
        # Cập nhật workflow
        self._rebuild_workflow()
        
        debug_log(f"Đã ngắt kết nối: {source_tool.display_name} -> {target_tool.display_name}", logging.INFO)
        return True
        
    def set_tool_as_source(self, source_tool_id: int, target_tool_id: int) -> bool:
        """
        Thiết lập một công cụ làm nguồn dữ liệu chính cho một công cụ khác
        
        Args:
            source_tool_id: ID của công cụ nguồn
            target_tool_id: ID của công cụ đích
            
        Returns:
            True nếu thiết lập thành công, False nếu không
        """
        source_tool = self.get_tool_by_id(source_tool_id)
        target_tool = self.get_tool_by_id(target_tool_id)
        
        if not source_tool or not target_tool:
            logger.warning(f"Không tìm thấy công cụ với ID {source_tool_id} hoặc {target_tool_id}")
            return False
            
        # Thiết lập source_tool
        target_tool.set_source_tool(source_tool)
        
        # Nếu chưa có kết nối, tạo kết nối
        if source_tool not in target_tool.inputs:
            target_tool.add_input(source_tool)
            
        if target_tool not in source_tool.outputs:
            source_tool.add_output(target_tool)
            
        # Cập nhật workflow
        self._rebuild_workflow()
        
        debug_log(f"Đã đặt {source_tool.display_name} làm nguồn dữ liệu cho {target_tool.display_name}", logging.INFO)
        return True
        
    def get_workflow_structure(self) -> Dict[str, Any]:
        """
        Lấy cấu trúc workflow của job
        
        Returns:
            Dictionary chứa thông tin về cấu trúc workflow
        """
        # Cập nhật workflow trước khi trả về cấu trúc
        self._rebuild_workflow()
        
        connections = []
        for tool in self.tools:
            for output_tool in tool.outputs:
                connections.append({
                    "source_id": tool.tool_id,
                    "source_name": tool.display_name,
                    "target_id": output_tool.tool_id,
                    "target_name": output_tool.display_name,
                    "is_primary": output_tool.source_tool == tool
                })
                
        return {
            "tools": [
                {
                    "id": t.tool_id,
                    "name": t.display_name,
                    "type": t.__class__.__name__,
                    "inputs": [i.tool_id for i in t.inputs],
                    "outputs": [o.tool_id for o in t.outputs],
                    "source_id": t.source_tool.tool_id if t.source_tool else None
                } for t in self.tools
            ],
            "connections": connections,
            "start_tools": [t.tool_id for t in self.start_tools],
            "end_tools": [t.tool_id for t in self.end_tools]
        }
        
    def remove_tool(self, index: int) -> bool:
        """
        Xóa một công cụ theo chỉ số và cập nhật các kết nối
        
        Args:
            index: Vị trí của công cụ trong danh sách
            
        Returns:
            True nếu xóa thành công, False nếu không
        """
        if 0 <= index < len(self.tools):
            tool_to_remove = self.tools[index]
            
            # Cập nhật kết nối của các tool khác
            for tool in self.tools:
                if tool != tool_to_remove:
                    # Xóa tool khỏi danh sách inputs của các tool khác
                    if tool_to_remove in tool.inputs:
                        tool.inputs.remove(tool_to_remove)
                    
                    # Xóa tool khỏi danh sách outputs của các tool khác
                    if tool_to_remove in tool.outputs:
                        tool.outputs.remove(tool_to_remove)
                    
                    # Đặt lại source_tool nếu source_tool là tool bị xóa
                    if tool.source_tool == tool_to_remove:
                        tool.source_tool = None
            
            # Xóa tool khỏi danh sách
            del self.tools[index]
            
            # Cập nhật workflow
            self._rebuild_workflow()
            
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
        
    def edit_tool(self, index: int, new_tool: BaseTool) -> bool:
        """Chỉnh sửa một công cụ theo chỉ số"""
        if 0 <= index < len(self.tools):
            self.tools[index] = new_tool
            self.status = "ready"
            return True
        return False
        
    def run(self, image: np.ndarray, initial_context: Dict[str, Any] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Thực thi chuỗi công cụ xử lý trên hình ảnh theo cấu trúc workflow input/output
        
        Args:
            image: Hình ảnh đầu vào (numpy array)
            initial_context: Context ban đầu để chuyển cho các tools
            
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
            context: Dict[str, Any] = initial_context.copy() if initial_context else {}
            processed_image = image.copy()
            
            # Lưu trữ kết quả từ mỗi tool để sử dụng cho các tool phụ thuộc
            tool_results: Dict[int, Tuple[np.ndarray, Dict[str, Any]]] = {}
            processed_tools: List[int] = []  # Danh sách ID tool đã xử lý
            
            # Khởi chạy từ các công cụ đầu tiên
            queue = list(self.start_tools) if self.start_tools else self.tools.copy()
            
            while queue:
                tool = queue.pop(0)
                tool_id = tool.tool_id
                
                # Nếu tool đã được xử lý, bỏ qua
                if tool_id in processed_tools:
                    continue
                    
                # Kiểm tra xem tất cả các inputs của tool đã được xử lý chưa
                input_tools = tool.get_inputs()
                if input_tools:
                    all_inputs_processed = all(t.tool_id in processed_tools for t in input_tools)
                    if not all_inputs_processed:
                        # Nếu chưa, đặt tool này vào cuối queue để xử lý sau
                        queue.append(tool)
                        continue
                
                debug_log(f"Đang chạy công cụ: {tool.display_name} (ID: {tool_id})", logging.INFO)
                tool_start = time.time()
                
                # Chuẩn bị dữ liệu đầu vào cho tool hiện tại
                current_image = processed_image
                current_context = context.copy()
                
                # Nếu có source_tool, sử dụng kết quả từ source_tool
                source_tool = tool.get_source_tool()
                if source_tool and source_tool.tool_id in tool_results:
                    current_image, source_result = tool_results[source_tool.tool_id]
                    # Cập nhật context với kết quả từ source_tool
                    current_context.update(source_result)
                
                # Thực thi tool
                result_image, result_data = tool.process(current_image, current_context)
                tool_time = time.time() - tool_start
                
                # Lưu kết quả để sử dụng cho các tool tiếp theo
                tool_results[tool_id] = (result_image, result_data)
                processed_tools.append(tool_id)
                
                # Cập nhật ngữ cảnh chung
                context.update(result_data)
                
                # Cập nhật hình ảnh đã xử lý nếu tool này là tool cuối cùng
                if not tool.get_outputs() or tool in self.end_tools:
                    processed_image = result_image
                
                # Lưu kết quả của công cụ
                self.results[tool.display_name] = {
                    "data": result_data,
                    "execution_time": tool_time
                }
                
                # Thêm các output tools vào queue
                for output_tool in tool.get_outputs():
                    if output_tool.tool_id not in processed_tools and output_tool not in queue:
                        queue.append(output_tool)
            
            self.execution_time = time.time() - start_time
            self.status = "completed"
            debug_log(f"Job {self.name} hoàn thành trong {self.execution_time:.2f}s", logging.INFO)
            
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
        tool_dicts = []
        connections = []
        
        # Lưu thông tin các công cụ
        for tool in self.tools:
            tool_dict = tool.to_dict()
            # Lưu ID của tool
            tool_dict['tool_id'] = tool.tool_id
            tool_dicts.append(tool_dict)
            
            # Lưu kết nối giữa các tool
            for output_tool in tool.outputs:
                connections.append({
                    "source_id": tool.tool_id,
                    "target_id": output_tool.tool_id,
                    "is_primary": output_tool.source_tool == tool
                })
        
        return {
            'name': self.name,
            'description': self.description,
            'tools': tool_dicts,
            'connections': connections,
            'status': self.status,
            'last_run_time': self.last_run_time,
            'execution_time': self.execution_time
        }
    
    @staticmethod
    def from_dict(d: Dict[str, Any], tool_registry: Dict[str, type]) -> 'Job':
        """Tạo job từ từ điển"""
        # Tạo các công cụ trước
        tools = [BaseTool.from_dict(td, tool_registry) for td in d.get('tools', [])]
        
        # Tạo job với các công cụ
        job = Job(d['name'], tools, d.get('description', ''))
        job.status = d.get('status', 'ready')
        job.last_run_time = d.get('last_run_time', 0)
        job.execution_time = d.get('execution_time', 0)
        
        # Khôi phục kết nối giữa các công cụ
        connections = d.get('connections', [])
        for conn in connections:
            source_id = conn.get('source_id')
            target_id = conn.get('target_id')
            is_primary = conn.get('is_primary', False)
            
            if source_id is not None and target_id is not None:
                source_tool = job.get_tool_by_id(source_id)
                target_tool = job.get_tool_by_id(target_id)
                
                if source_tool and target_tool:
                    # Tạo kết nối
                    source_tool.add_output(target_tool)
                    
                    # Nếu đây là kết nối chính, thiết lập source_tool
                    if is_primary:
                        target_tool.set_source_tool(source_tool)
        
        # Cập nhật cấu trúc workflow
        job._rebuild_workflow()
        
        return job


class JobManager:
    """Quản lý tất cả các job và công cụ có sẵn"""
    
    def __init__(self):
        self.jobs: List[Job] = []
        self.current_job_index = -1
        self.tool_registry: Dict[str, type] = {}  # map tool_type -> Tool class
        self.register_default_tools()
        
        # Performance optimization attributes
        self.last_detection_time = 0
        self.detection_interval = 1.0 / 12.0  # 12 FPS for detection (instead of 66 FPS)
        self.frame_cache = {}
        self.last_processed_frame = None
        
        # Threading support
        self.worker_thread = None
        self.use_threading = QT_AVAILABLE  # Use threading if PyQt5 is available
        
    def register_tool(self, tool_class: type) -> None:
        """Đăng ký một loại công cụ mới"""
        self.tool_registry[tool_class.__name__] = tool_class
        
    def register_default_tools(self) -> None:
        """Đăng ký các loại công cụ mặc định"""
        # Đăng ký công cụ chung trước
        self.register_tool(GenericTool)

        # Import các công cụ cụ thể ở đây để tránh import vòng tròn
        try:
            from tools.detection.ocr_tool import OcrTool
            self.register_tool(OcrTool)
        except ImportError:
            logger.warning("Không thể đăng ký OcrTool")

        try:
            from tools.detection.edge_detection import EdgeDetectionTool
            self.register_tool(EdgeDetectionTool)
        except ImportError:
            logger.warning("Không thể đăng ký EdgeDetectionTool")

        try:
            from tools.saveimage_tool import SaveImageTool
            self.register_tool(SaveImageTool)
            debug_log("Đã đăng ký SaveImageTool", logging.INFO)
        except ImportError:
            logger.warning("Không thể đăng ký SaveImageTool")

        # ClassificationTool (optional, ONNX-based)
        try:
            from tools.classification_tool import ClassificationTool
            self.register_tool(ClassificationTool)
            debug_log("Đã đăng ký ClassificationTool", logging.INFO)
        except ImportError:
            logger.warning("Không thể đăng ký ClassificationTool")
        
    def create_tool(self, tool_type: str, name: str, config: Optional[Dict[str, Any]] = None) -> Optional[BaseTool]:
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
        
    def run_job(self, job_index: int, image: np.ndarray, initial_context: Dict[str, Any] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Chạy một job theo chỉ số
        
        Args:
            job_index: Chỉ số của job cần chạy
            image: Hình ảnh đầu vào
            initial_context: Context ban đầu để chuyển cho các tools
            
        Returns:
            Tuple chứa hình ảnh đã xử lý và kết quả
        """
        if 0 <= job_index < len(self.jobs):
            return self.jobs[job_index].run(image, initial_context)
        return image, {"error": "Chỉ số job không hợp lệ"}
        
    def run_current_job(self, image: np.ndarray, context: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Chạy job hiện tại với context tùy chọn và frame skipping optimization"""
        current_job = self.get_current_job()
        if current_job:
            # Smart frame skipping for detection jobs
            current_time = time.time()
            has_detect_tool = any('detect' in tool.name.lower() for tool in current_job.tools)
            
            if has_detect_tool:
                # Check if enough time has passed for detection
                if current_time - self.last_detection_time < self.detection_interval:
                    # Return cached result if available
                    if self.last_processed_frame is not None:
                        return self.last_processed_frame, {"cached": True, "skipped_frame": True}
                    # Or return original image with minimal processing
                    return image, {"cached": False, "skipped_frame": True}
                
                # Update last detection time
                self.last_detection_time = current_time
            
            # Base context ensures SaveImageTool can save when desired
            initial_context: Dict[str, Any] = {"force_save": True}
            # Merge additional context from caller (e.g., pixel_format)
            if context:
                try:
                    initial_context.update(context)
                except Exception:
                    pass
            
            # Use threading if available to avoid blocking UI
            if self.use_threading and self.worker_thread is None:
                result = self._run_job_threaded(current_job, image, initial_context)
            else:
                # Fallback to synchronous execution
                result = current_job.run(image, initial_context)
            
            # Cache the result for frame skipping
            if has_detect_tool and result[0] is not None:
                self.last_processed_frame = result[0]
            
            return result
        return image, {"error": "Không có job hiện tại"}
        
    def _run_job_threaded(self, job, image: np.ndarray, context: Dict[str, Any]) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Run job in background thread (non-blocking for UI)"""
        try:
            # For now, still run synchronously but with minimal blocking
            # In the future, this could be fully async with signals
            return job.run(image, context)
        except Exception as e:
            logger.error(f"Threaded job execution failed: {e}")
            return image, {"error": f"Job execution failed: {str(e)}"}
        
    def save_job(self, job_index: int, path: str) -> bool:
        """Lưu một job vào file"""
        if not (0 <= job_index < len(self.jobs)):
            logger.error(f"Chỉ số job không hợp lệ: {job_index}")
            return False
            
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.jobs[job_index].to_dict(), f, ensure_ascii=False, indent=2)
            debug_log(f"Đã lưu job vào {path}", logging.INFO)
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
            debug_log(f"Đã lưu tất cả job vào {path}", logging.INFO)
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
                debug_log(f"Đã tải job từ {path}", logging.INFO)
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
                debug_log(f"Đã tải {len(self.jobs)} job từ {path}", logging.INFO)
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
        
    # Phương thức để làm việc với workflow của job
    def connect_tools_in_current_job(self, source_tool_id: int, target_tool_id: int) -> bool:
        """
        Kết nối hai công cụ trong job hiện tại
        
        Args:
            source_tool_id: ID của công cụ nguồn
            target_tool_id: ID của công cụ đích
            
        Returns:
            True nếu kết nối thành công, False nếu không
        """
        current_job = self.get_current_job()
        if current_job:
            return current_job.connect_tools(source_tool_id, target_tool_id)
        logger.warning("Không có job hiện tại để kết nối công cụ")
        return False
        
    def disconnect_tools_in_current_job(self, source_tool_id: int, target_tool_id: int) -> bool:
        """
        Ngắt kết nối giữa hai công cụ trong job hiện tại
        
        Args:
            source_tool_id: ID của công cụ nguồn
            target_tool_id: ID của công cụ đích
            
        Returns:
            True nếu ngắt kết nối thành công, False nếu không
        """
        current_job = self.get_current_job()
        if current_job:
            return current_job.disconnect_tools(source_tool_id, target_tool_id)
        logger.warning("Không có job hiện tại để ngắt kết nối công cụ")
        return False
        
    def set_source_tool_in_current_job(self, source_tool_id: int, target_tool_id: int) -> bool:
        """
        Thiết lập một công cụ làm nguồn dữ liệu chính cho một công cụ khác trong job hiện tại
        
        Args:
            source_tool_id: ID của công cụ nguồn
            target_tool_id: ID của công cụ đích
            
        Returns:
            True nếu thiết lập thành công, False nếu không
        """
        current_job = self.get_current_job()
        if current_job:
            return current_job.set_tool_as_source(source_tool_id, target_tool_id)
        logger.warning("Không có job hiện tại để thiết lập công cụ nguồn")
        return False
        
    def get_current_job_workflow(self) -> Optional[Dict[str, Any]]:
        """
        Lấy cấu trúc workflow của job hiện tại
        
        Returns:
            Dictionary chứa thông tin về cấu trúc workflow hoặc None nếu không có job hiện tại
        """
        current_job = self.get_current_job()
        if current_job:
            return current_job.get_workflow_structure()
        return None
        
    def add_tool_to_current_job(self, tool: Union[BaseTool, Dict[str, Any]], source_tool_id: Optional[int] = None) -> Optional[BaseTool]:
        """
        Thêm một công cụ vào job hiện tại và kết nối với công cụ nguồn nếu được chỉ định
        
        Args:
            tool: Công cụ cần thêm hoặc dictionary cấu hình
            source_tool_id: ID của công cụ nguồn (optional)
            
        Returns:
            Công cụ đã được thêm hoặc None nếu có lỗi
        """
        debug_log(f"JobManager: add_tool_to_current_job called with tool: {tool}", logging.INFO)
        
        # Log chi tiết về tool
        tool_name = getattr(tool, 'name', 'Unknown') if not isinstance(tool, dict) else tool.get('name', 'Unknown dict')
        tool_display_name = getattr(tool, 'display_name', 'No display name') if not isinstance(tool, dict) else tool.get('display_name', 'No display name')
        tool_id = getattr(tool, 'tool_id', 'No ID') if not isinstance(tool, dict) else tool.get('tool_id', 'No ID')
        
        debug_log(f"JobManager: Tool details - name={tool_name}, display_name={tool_display_name}, ID={tool_id}", logging.INFO)
        
        current_job = self.get_current_job()
        if current_job:
            # Kiểm tra xem có phải Camera Source không
            is_camera_source = False
            if isinstance(tool, BaseTool) and hasattr(tool, 'name') and "camera" in tool.name.lower():
                is_camera_source = True
                debug_log("JobManager: Detected Camera Source tool", logging.INFO)
                
            # Thêm tool vào job
            result = current_job.add_tool(tool, source_tool_id)
            
            # Kiểm tra kết quả
            if result:
                debug_log(f"JobManager: Tool '{tool_name}' added successfully to job '{current_job.name}'", logging.INFO)
                
                # Log danh sách tools trong job
                debug_log(f"JobManager: Current job now has {len(current_job.tools)} tools:", logging.INFO)
                for i, t in enumerate(current_job.tools):
                    t_name = getattr(t, 'name', 'Unknown')
                    t_display = getattr(t, 'display_name', 'No display')
                    t_id = getattr(t, 'tool_id', 'No ID')
                    debug_log(f"JobManager:   Tool {i}: name={t_name}, display_name={t_display}, id={t_id}", logging.INFO)
                    
                # Thông báo job đã thay đổi
                self._notify_job_changed()
                
                # Xử lý đặc biệt cho Camera Source
                if is_camera_source:
                    debug_log("JobManager: Camera Source added successfully to job", logging.INFO)
                
                return result
            else:
                logger.error(f"JobManager: Failed to add tool '{tool_name}' to job")
                return None
        
        logger.warning("JobManager: No current job to add tool to")
        return None
        
    def _notify_job_changed(self):
        """
        Thông báo rằng job đã thay đổi để các đối tượng quan sát có thể cập nhật
        """
        debug_log("JobManager: Job changed notification triggered", logging.INFO)
        # Ở đây có thể thêm code thông báo cho các observer nếu cần
        
        # In danh sách công cụ hiện tại trong job để debug
        current_job = self.get_current_job()
        if current_job:
            debug_log(f"JobManager: Current job '{current_job.name}' has {len(current_job.tools)} tools:", logging.INFO)
            for i, tool in enumerate(current_job.tools):
                tool_name = getattr(tool, 'name', 'Unknown')
                tool_display = getattr(tool, 'display_name', 'No display')
                tool_id = getattr(tool, 'tool_id', 'No ID')
                debug_log(f"JobManager:   Tool {i}: name={tool_name}, display_name={tool_display}, id={tool_id}", logging.INFO)
                
    def get_tool_list(self) -> List[BaseTool]:
        """Lấy danh sách các công cụ có sẵn (tương thích với giao diện cũ)"""
        tools: List[BaseTool] = []
        for tool_type in self.get_available_tool_types():
            if tool_type != "GenericTool":
                tool = self.create_tool(tool_type, tool_type)
                if tool:
                    tools.append(tool)
        return tools

    def addTool(self, tool_info):
        # ...existing code for other tool types...
        if tool_info.get('type', '') == 'save_image':
            from tools.saveimage_tool import SaveImageTool
            directory = tool_info.get('path', '')
            structure = tool_info.get('structure', '')
            image_format = tool_info.get('format', 'JPG')
            save_tool = SaveImageTool(directory, structure, image_format)
            # Add the save image tool instance to the job manager's tool list
            self.tools.append(save_tool)
            # Optionally, log tool integration
            print(f"SaveImageTool added with directory: {directory}, structure: '{structure}', format: {image_format}")
        else:
            # ...existing code for handling other tools...
            pass
        # ...existing code...
