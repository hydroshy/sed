"""
WorkflowManager - quản lý các workflow và công cụ xử lý hình ảnh
Thay thế cho JobManager cũ với mô hình workflow mới giống Cognex Vision Pro
"""

import json
import os
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Union, cast

import numpy as np

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WorkflowManager")

from tools.base_tool import ToolConfig, BaseTool, GenericTool


class Workflow:
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
        
        # Thêm tool vào danh sách
        self.tools.append(tool)
        
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
        logger.info(f"Added tool: {display_name} to workflow {self.name}")
        
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
        
        logger.info(f"Đã kết nối: {source_tool.display_name} -> {target_tool.display_name}")
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
        
        logger.info(f"Đã ngắt kết nối: {source_tool.display_name} -> {target_tool.display_name}")
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
        
        logger.info(f"Đã đặt {source_tool.display_name} làm nguồn dữ liệu cho {target_tool.display_name}")
        return True
        
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
            # Lưu các kết nối hiện tại
            old_tool = self.tools[index]
            inputs = old_tool.inputs.copy()
            outputs = old_tool.outputs.copy()
            source_tool = old_tool.source_tool
            
            # Cập nhật tool mới
            self.tools[index] = new_tool
            
            # Khôi phục kết nối
            for input_tool in inputs:
                new_tool.add_input(input_tool)
                if input_tool in output.outputs:
                    continue  # Không cần thêm nếu đã có
                input_tool.add_output(new_tool)
                
            for output_tool in outputs:
                new_tool.add_output(output_tool)
                
            if source_tool:
                new_tool.set_source_tool(source_tool)
                
            # Cập nhật workflow
            self._rebuild_workflow()
            
            self.status = "ready"
            return True
        return False
        
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
        
    def run(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Thực thi chuỗi công cụ xử lý trên hình ảnh theo cấu trúc workflow input/output
        
        Args:
            image: Hình ảnh đầu vào (numpy array)
            
        Returns:
            Tuple chứa hình ảnh cuối cùng và kết quả tổng hợp
        """
        if not self.tools:
            logger.warning(f"Không có công cụ nào trong workflow {self.name}")
            return image, {"error": "Không có công cụ nào"}
            
        self.status = "running"
        self.last_run_time = time.time()
        self.results = {}
        
        try:
            start_time = time.time()
            context: Dict[str, Any] = {}
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
                
                logger.info(f"Đang chạy công cụ: {tool.display_name} (ID: {tool_id})")
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
            logger.info(f"Workflow {self.name} hoàn thành trong {self.execution_time:.2f}s")
            
            return processed_image, {
                "workflow_name": self.name,
                "execution_time": self.execution_time,
                "results": self.results
            }
            
        except Exception as e:
            self.status = "failed"
            error_msg = f"Lỗi khi chạy workflow {self.name}: {str(e)}"
            logger.error(error_msg)
            return image, {"error": error_msg}
            
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi workflow thành từ điển để lưu trữ"""
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
    def from_dict(d: Dict[str, Any], tool_registry: Dict[str, type]) -> 'Workflow':
        """Tạo workflow từ từ điển"""
        # Tạo các công cụ trước
        tools = [BaseTool.from_dict(td, tool_registry) for td in d.get('tools', [])]
        
        # Tạo workflow với các công cụ
        workflow = Workflow(d['name'], tools, d.get('description', ''))
        workflow.status = d.get('status', 'ready')
        workflow.last_run_time = d.get('last_run_time', 0)
        workflow.execution_time = d.get('execution_time', 0)
        
        # Khôi phục kết nối giữa các công cụ
        connections = d.get('connections', [])
        for conn in connections:
            source_id = conn.get('source_id')
            target_id = conn.get('target_id')
            is_primary = conn.get('is_primary', False)
            
            if source_id is not None and target_id is not None:
                source_tool = workflow.get_tool_by_id(source_id)
                target_tool = workflow.get_tool_by_id(target_id)
                
                if source_tool and target_tool:
                    # Tạo kết nối
                    source_tool.add_output(target_tool)
                    
                    # Nếu đây là kết nối chính, thiết lập source_tool
                    if is_primary:
                        target_tool.set_source_tool(source_tool)
        
        # Cập nhật cấu trúc workflow
        workflow._rebuild_workflow()
        
        return workflow


class WorkflowManager:
    """Quản lý tất cả các workflow và công cụ có sẵn"""
    
    def __init__(self):
        self.workflows: List[Workflow] = []
        self.current_workflow_index = -1
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
            from tools.detection.ocr_tool import OcrTool
            self.register_tool(OcrTool)
        except ImportError:
            logger.warning("Không thể đăng ký OcrTool")
            
        try:
            from tools.detection.edge_detection import EdgeDetectionTool
            self.register_tool(EdgeDetectionTool)
        except ImportError:
            logger.warning("Không thể đăng ký EdgeDetectionTool")
        
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
        
    def add_workflow(self, workflow: Workflow) -> None:
        """Thêm một workflow mới và đặt làm workflow hiện tại"""
        self.workflows.append(workflow)
        self.current_workflow_index = len(self.workflows) - 1
        
    def remove_workflow(self, index: int) -> bool:
        """Xóa một workflow theo chỉ số"""
        if 0 <= index < len(self.workflows):
            del self.workflows[index]
            # Cập nhật chỉ số workflow hiện tại
            if not self.workflows:
                self.current_workflow_index = -1
            elif index <= self.current_workflow_index:
                self.current_workflow_index = max(0, self.current_workflow_index - 1)
            return True
        return False
        
    def set_current_workflow(self, index: int) -> bool:
        """Đặt workflow hiện tại theo chỉ số"""
        if 0 <= index < len(self.workflows):
            self.current_workflow_index = index
            return True
        return False
        
    def get_current_workflow(self) -> Optional[Workflow]:
        """Lấy workflow hiện tại"""
        if 0 <= self.current_workflow_index < len(self.workflows):
            return self.workflows[self.current_workflow_index]
        return None
        
    def run_workflow(self, workflow_index: int, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Chạy một workflow theo chỉ số
        
        Args:
            workflow_index: Chỉ số của workflow cần chạy
            image: Hình ảnh đầu vào
            
        Returns:
            Tuple chứa hình ảnh đã xử lý và kết quả
        """
        if 0 <= workflow_index < len(self.workflows):
            return self.workflows[workflow_index].run(image)
        return image, {"error": "Chỉ số workflow không hợp lệ"}
        
    def run_current_workflow(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Chạy workflow hiện tại"""
        current_workflow = self.get_current_workflow()
        if current_workflow:
            return current_workflow.run(image)
        return image, {"error": "Không có workflow hiện tại"}
        
    def save_workflow(self, workflow_index: int, path: str) -> bool:
        """Lưu một workflow vào file"""
        if not (0 <= workflow_index < len(self.workflows)):
            logger.error(f"Chỉ số workflow không hợp lệ: {workflow_index}")
            return False
            
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.workflows[workflow_index].to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"Đã lưu workflow vào {path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu workflow: {str(e)}")
            return False
            
    def save_current_workflow(self, path: str) -> bool:
        """Lưu workflow hiện tại vào file"""
        if self.current_workflow_index < 0:
            logger.error("Không có workflow hiện tại để lưu")
            return False
        return self.save_workflow(self.current_workflow_index, path)
        
    def save_all_workflows(self, path: str) -> bool:
        """Lưu tất cả các workflow vào file"""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({
                    'workflows': [workflow.to_dict() for workflow in self.workflows],
                    'current_workflow_index': self.current_workflow_index
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"Đã lưu tất cả workflow vào {path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu tất cả workflow: {str(e)}")
            return False
            
    def load_workflow(self, path: str) -> Optional[Workflow]:
        """Tải một workflow từ file và thêm vào danh sách"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                workflow = Workflow.from_dict(data, self.tool_registry)
                self.add_workflow(workflow)
                logger.info(f"Đã tải workflow từ {path}")
                return workflow
        except Exception as e:
            logger.error(f"Lỗi khi tải workflow: {str(e)}")
            return None
            
    def load_all_workflows(self, path: str) -> bool:
        """Tải tất cả các workflow từ file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.workflows = [Workflow.from_dict(wd, self.tool_registry) for wd in data.get('workflows', [])]
                self.current_workflow_index = data.get('current_workflow_index', 0 if self.workflows else -1)
                logger.info(f"Đã tải {len(self.workflows)} workflow từ {path}")
                return True
        except Exception as e:
            logger.error(f"Lỗi khi tải tất cả workflow: {str(e)}")
            return False
            
    def get_available_tool_types(self) -> List[str]:
        """Lấy danh sách các loại công cụ có sẵn"""
        return list(self.tool_registry.keys())
        
    def get_workflow_list(self) -> List[Workflow]:
        """Lấy danh sách các workflow"""
        return self.workflows
        
    def create_default_workflow(self, name: str = "New Workflow") -> Workflow:
        """Tạo một workflow mặc định với tên được chỉ định"""
        workflow = Workflow(name)
        self.add_workflow(workflow)
        return workflow

    # Phương thức để làm việc với workflow
    def connect_tools_in_current_workflow(self, source_tool_id: int, target_tool_id: int) -> bool:
        """
        Kết nối hai công cụ trong workflow hiện tại
        
        Args:
            source_tool_id: ID của công cụ nguồn
            target_tool_id: ID của công cụ đích
            
        Returns:
            True nếu kết nối thành công, False nếu không
        """
        current_workflow = self.get_current_workflow()
        if current_workflow:
            return current_workflow.connect_tools(source_tool_id, target_tool_id)
        logger.warning("Không có workflow hiện tại để kết nối công cụ")
        return False
        
    def disconnect_tools_in_current_workflow(self, source_tool_id: int, target_tool_id: int) -> bool:
        """
        Ngắt kết nối giữa hai công cụ trong workflow hiện tại
        
        Args:
            source_tool_id: ID của công cụ nguồn
            target_tool_id: ID của công cụ đích
            
        Returns:
            True nếu ngắt kết nối thành công, False nếu không
        """
        current_workflow = self.get_current_workflow()
        if current_workflow:
            return current_workflow.disconnect_tools(source_tool_id, target_tool_id)
        logger.warning("Không có workflow hiện tại để ngắt kết nối công cụ")
        return False
        
    def set_source_tool_in_current_workflow(self, source_tool_id: int, target_tool_id: int) -> bool:
        """
        Thiết lập một công cụ làm nguồn dữ liệu chính cho một công cụ khác trong workflow hiện tại
        
        Args:
            source_tool_id: ID của công cụ nguồn
            target_tool_id: ID của công cụ đích
            
        Returns:
            True nếu thiết lập thành công, False nếu không
        """
        current_workflow = self.get_current_workflow()
        if current_workflow:
            return current_workflow.set_tool_as_source(source_tool_id, target_tool_id)
        logger.warning("Không có workflow hiện tại để thiết lập công cụ nguồn")
        return False
        
    def get_current_workflow_structure(self) -> Optional[Dict[str, Any]]:
        """
        Lấy cấu trúc workflow của workflow hiện tại
        
        Returns:
            Dictionary chứa thông tin về cấu trúc workflow hoặc None nếu không có workflow hiện tại
        """
        current_workflow = self.get_current_workflow()
        if current_workflow:
            return current_workflow.get_workflow_structure()
        return None
        
    def add_tool_to_current_workflow(self, tool: Union[BaseTool, Dict[str, Any]], source_tool_id: Optional[int] = None) -> Optional[BaseTool]:
        """
        Thêm một công cụ vào workflow hiện tại và kết nối với công cụ nguồn nếu được chỉ định
        
        Args:
            tool: Công cụ cần thêm hoặc dictionary cấu hình
            source_tool_id: ID của công cụ nguồn (optional)
            
        Returns:
            Công cụ đã được thêm hoặc None nếu có lỗi
        """
        current_workflow = self.get_current_workflow()
        if current_workflow:
            return current_workflow.add_tool(tool, source_tool_id)
        logger.warning("Không có workflow hiện tại để thêm công cụ")
        return None
        
    def get_tool_list(self) -> List[BaseTool]:
        """Lấy danh sách các công cụ có sẵn (tương thích với giao diện cũ)"""
        tools: List[BaseTool] = []
        for tool_type in self.get_available_tool_types():
            if tool_type != "GenericTool":
                tool = self.create_tool(tool_type, tool_type)
                if tool:
                    tools.append(tool)
        return tools
