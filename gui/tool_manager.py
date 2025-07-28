from PyQt5.QtCore import QObject, QStringListModel
from job.job_manager import Tool, Job, JobManager
import logging

class ToolManager(QObject):
    """
    Quản lý các Tool trong ứng dụng và xử lý tương tác với UI
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.job_manager = None
        self._pending_tool = None
        self._pending_tool_config = None
        self._tool_view = None
        self._job_view = None
        
    def setup(self, job_manager, tool_view, job_view, tool_combo_box):
        """Thiết lập các tham chiếu đến các widget UI và job manager"""
        self.job_manager = job_manager
        self._tool_view = tool_view
        self._job_view = job_view
        self._tool_combo_box = tool_combo_box
        self._update_job_view()
        logging.info("ToolManager: Setup completed")
        
    def on_add_tool(self):
        """Xử lý sự kiện khi người dùng nhấn nút thêm công cụ"""
        logging.info("ToolManager: on_add_tool invoked.")
        tool_name = self._tool_combo_box.currentText() if self._tool_combo_box else None
        logging.info(f"ToolManager: Selected tool: {tool_name}")
        if not tool_name:
            logging.warning("ToolManager: No tool selected in toolComboBox.")
            return None

        # Lưu tool được chọn vào biến tạm để xử lý sau khi nhấn applySetting
        self._pending_tool = tool_name
        logging.info(f"ToolManager: Saved pending tool: {self._pending_tool}")
        
        return tool_name
        
    def on_apply_setting(self):
        """
        Xử lý khi người dùng nhấn nút Apply trong trang cài đặt tool.
        - Thêm tool và cấu hình vào job hiện tại
        - Quay lại trang cài đặt camera
        """
        if self._pending_tool:
            logging.info(f"ToolManager: Applying settings for tool: {self._pending_tool}")
            
            # Tạo đối tượng Tool
            tool = Tool(self._pending_tool, config=self._pending_tool_config)
            
            # Thêm tool vào job hiện tại
            self.add_tool_to_job_with_tool(tool)
            logging.info(f"ToolManager: Tool '{self._pending_tool}' with configuration added to job")
            
            # Reset biến tạm
            result_tool = self._pending_tool
            self._pending_tool = None
            self._pending_tool_config = None
            
            return result_tool
        
        return None
    
    def on_cancel_setting(self):
        """
        Xử lý khi người dùng nhấn nút Cancel trong trang cài đặt tool.
        - Hủy bỏ thao tác thêm tool
        """
        logging.info("ToolManager: Cancelling tool settings")
        
        # Reset biến tạm
        self._pending_tool = None
        self._pending_tool_config = None
    
    def set_tool_config(self, config):
        """Thiết lập cấu hình cho tool đang chờ xử lý"""
        self._pending_tool_config = config
        
    def add_tool_to_job(self, tool_name):
        """Thêm tool vào job hiện tại dựa trên tên tool"""
        if not tool_name:
            return None

        # Ensure job_manager is initialized
        if not self.job_manager:
            logging.error("ToolManager: JobManager is not initialized.")
            return None

        # If no current job, create a new one
        current_job = self.job_manager.get_current_job()
        if not current_job:
            logging.info("ToolManager: No current job found. Creating a new job.")
            current_job = Job("Job 1")
            self.job_manager.add_job(current_job)

        # Add the selected tool to the current job
        tool = Tool(tool_name)
        current_job.add_tool(tool)
        self._update_job_view()
        logging.info(f"ToolManager: Tool '{tool_name}' added to the current job.")

        return tool

    def add_tool_to_job_with_tool(self, tool):
        """Thêm đối tượng Tool đã tạo vào job hiện tại"""
        # Ensure job_manager is initialized
        if not self.job_manager:
            logging.error("ToolManager: JobManager is not initialized.")
            return False

        # If no current job, create a new one
        current_job = self.job_manager.get_current_job()
        if not current_job:
            logging.info("ToolManager: No current job found. Creating a new job.")
            current_job = Job("Job 1")
            self.job_manager.add_job(current_job)

        # Add the tool to the current job
        current_job.add_tool(tool)
        self._update_job_view()
        logging.info(f"ToolManager: Tool '{tool.name}' added to the current job.")
        return True

    def _update_job_view(self):
        """Cập nhật hiển thị job trong UI"""
        if not self._job_view or not self.job_manager:
            return
            
        job = self.job_manager.get_current_job()
        if job:
            tool_names = [tool.name for tool in job.tools]
        else:
            tool_names = []
        self._job_model = QStringListModel(tool_names)
        self._job_view.setModel(self._job_model)
        
    def on_remove_tool_from_job(self):
        """Xóa tool được chọn trong jobView"""
        if not self._job_view or not self.job_manager:
            return
            
        index = self._job_view.currentIndex().row()
        job = self.job_manager.get_current_job()
        if job and 0 <= index < len(job.tools):
            job.tools.pop(index)
            self._update_job_view()
            
    def on_edit_tool_in_job(self):
        """Chỉnh sửa tool được chọn trong jobView"""
        if not self._job_view or not self.job_manager:
            return
            
        index = self._job_view.currentIndex().row()
        job = self.job_manager.get_current_job()
        if job and 0 <= index < len(job.tools):
            tool = job.tools[index]
            logging.info(f"ToolManager: Edit tool: {tool.name}")
            return tool
        
        return None
