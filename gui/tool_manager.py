from PyQt5.QtCore import QObject, QStringListModel
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from job.job_manager import Job, JobManager
from tools.base_tool import BaseTool
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
        
        # Setup job view selection
        if self._job_view:
            from PyQt5.QtWidgets import QAbstractItemView
            self._job_view.setSelectionMode(QAbstractItemView.SingleSelection)
            self._job_view.setSelectionBehavior(QAbstractItemView.SelectRows)
            
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
            # Nếu là Detect Tool thì kiểm tra bắt buộc chọn algorithmComboBox (tên mô hình)
            if self._pending_tool == "Detect Tool":
                config = self._pending_tool_config if self._pending_tool_config is not None else {}
                algorithm = config.get('algorithmComboBox', '')
                if not algorithm:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(None, "Thiếu thông tin mô hình", "Bạn phải chọn mô hình (algorithm) trước khi thêm Detect Tool.")
                    logging.warning("ToolManager: User tried to add Detect Tool without algorithm.")
                    return None
                try:
                    from detection.detect_tool import create_detect_tool_from_manager_config
                    tool = create_detect_tool_from_manager_config(config)
                    logging.info("ToolManager: Created DetectTool instance via factory.")
                except Exception as e:
                    logging.error(f"ToolManager: Failed to create DetectTool: {e}")
                    from tools.base_tool import GenericTool
                    tool = GenericTool(self._pending_tool, config=self._pending_tool_config)
            else:
                from tools.base_tool import GenericTool
                config = self._pending_tool_config if self._pending_tool_config is not None else {}
                tool = GenericTool(self._pending_tool, config=config)
            # Thêm tool vào job hiện tại (chỉ khi đã hợp lệ)
            self.add_tool_to_job_with_tool(tool)
            logging.info(f"ToolManager: Tool '{self._pending_tool}' with configuration added to job")
            # Reset biến tạm
            self._pending_tool = None
            self._pending_tool_config = None
            self._pending_detection_area = None
            return tool  # Return Tool object instead of name
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
        from tools.base_tool import GenericTool
        tool = GenericTool(tool_name)
        current_job.add_tool(tool)
        self._update_job_view()
        logging.info(f"ToolManager: Tool '{tool_name}' added to the current job.")

        return tool

    def add_tool_to_job_with_tool(self, tool):
        """Thêm đối tượng Tool đã tạo vào job hiện tại"""
        print(f"DEBUG: add_tool_to_job_with_tool called with tool: {tool.name}")
        
        # Ensure job_manager is initialized
        if not self.job_manager:
            print("DEBUG: JobManager is not initialized!")
            logging.error("ToolManager: JobManager is not initialized.")
            return False

        # If no current job, create a new one
        current_job = self.job_manager.get_current_job()
        print(f"DEBUG: Current job before adding: {current_job}")

        if not current_job:
            print("DEBUG: No current job found. Creating a new job.")
            logging.info("ToolManager: No current job found. Creating a new job.")
            current_job = Job("Job 1")
            self.job_manager.add_job(current_job)
            print(f"DEBUG: Created new job: {current_job.name}")

        # Add the tool to the current job
        print(f"DEBUG: Adding tool to job. Current tools count: {len(current_job.tools)}")
        current_job.add_tool(tool)
        print(f"DEBUG: After adding tool. Tools count: {len(current_job.tools)}")
        print(f"DEBUG: Tool added: {tool.display_name}")

        self._update_job_view()
        logging.info(f"ToolManager: Tool '{tool.name}' added to the current job.")
        return True

    def _update_job_view(self):
        """Cập nhật hiển thị job trong UI với QTreeView"""
        print(f"DEBUG: _update_job_view called")
        print(f"DEBUG: _job_view exists: {self._job_view is not None}")
        print(f"DEBUG: job_manager exists: {self.job_manager is not None}")
        
        if not self._job_view or not self.job_manager:
            print("DEBUG: Missing job_view or job_manager")
            return
            
        # Create tree model
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Tools"])
        
        job = self.job_manager.get_current_job()
        print(f"DEBUG: Current job: {job}")
        
        if job:
            # Create job root item
            job_item = QStandardItem(f"📁 {job.name}")
            job_item.setEditable(False)
            
            # Add tools as children
            for tool in job.tools:
                # Hiển thị id dạng têntool#id
                tool_id_str = f"{tool.display_name}#{tool.tool_id}" if hasattr(tool, 'tool_id') and tool.tool_id is not None else tool.display_name
                tool_item = QStandardItem(f"🔧 {tool_id_str}")
                tool_item.setEditable(False)
                # Store tool reference for later use
                tool_item.setData(tool, role=256)  # Custom role
                job_item.appendRow(tool_item)
                print(f"DEBUG: Added tool item: {tool_id_str}")
            
            model.appendRow(job_item)
            print(f"DEBUG: Added job item with {len(job.tools)} tools")
        else:
            # Create empty job item
            empty_item = QStandardItem("📁 No Job")
            empty_item.setEditable(False)
            model.appendRow(empty_item)
            print("DEBUG: No current job, added empty item")
            
        self._job_view.setModel(model)
        # Expand all items to show tools
        self._job_view.expandAll()
        print(f"DEBUG: Updated tree view model")
        
    def on_remove_tool_from_job(self):
        """Xóa tool được chọn trong jobView"""
        if not self._job_view or not self.job_manager:
            return
            
        # Get selected index from tree view
        selection = self._job_view.selectionModel()
        if not selection.hasSelection():
            print("DEBUG: No item selected for removal")
            return
            
        index = selection.currentIndex()
        model = self._job_view.model()
        
        if not model:
            return
            
        # Get item from model
        item = model.itemFromIndex(index)
        if not item:
            return
        
        # Check if it's a tool item
        tool = item.data(role=256)
        if tool:
            job = self.job_manager.get_current_job()
            if job:
                # Find and remove tool from job
                for i, job_tool in enumerate(job.tools):
                    if job_tool.tool_id == tool.tool_id:
                        removed_tool = job.tools.pop(i)
                        self._update_job_view()
                        logging.info(f"ToolManager: Removed tool: {removed_tool.display_name}")
                        break
            
    def on_edit_tool_in_job(self):
        """Chỉnh sửa tool được chọn trong jobView"""
        if not self._job_view or not self.job_manager:
            return None
            
        # Get selected index from tree view
        selection = self._job_view.selectionModel()
        if not selection.hasSelection():
            print("DEBUG: No item selected in job view")
            return None
            
        index = selection.currentIndex()
        model = self._job_view.model()
        
        if not model:
            print("DEBUG: No model set for job view")
            return None
            
        # Get item from model
        item = model.itemFromIndex(index)
        if not item:
            print("DEBUG: No item found at selected index")
            return None
        
        # Check if it's a tool item (has tool data)
        tool = item.data(role=256)  # Custom role where we stored tool reference
        if tool:
            logging.info(f"ToolManager: Edit tool: {tool.display_name}")
            
            # Set as current editing tool
            self._current_editing_tool = tool
            self._current_editing_index = None  # Not needed for tree view
            
            return tool
        else:
            print("DEBUG: Selected item is not a tool")
            return None
    
    def get_current_editing_tool(self):
        """Get currently editing tool"""
        return getattr(self, '_current_editing_tool', None)
    
    def clear_current_editing_tool(self):
        """Clear current editing tool"""
        self._current_editing_tool = None
        self._current_editing_index = None
        
    def get_selected_tool(self):
        """Get currently selected tool from tool view"""
        if not self._job_view:
            return None
            
        model = self._job_view.model()
        if not model:
            return None
            
        selection_model = self._job_view.selectionModel()
        if not selection_model:
            return None
            
        selected_indexes = selection_model.selectedIndexes()
        if not selected_indexes:
            return None
            
        # Get the selected item
        index = selected_indexes[0]
        item = model.itemFromIndex(index)
        
        if item:
            # Try to get tool data from custom role
            tool_data = item.data(role=256)  # Custom role where we stored tool
            if tool_data:
                return tool_data
                
            # Also check for tool_data attribute for backward compatibility
            if hasattr(item, 'tool_data'):
                return item.tool_data
        return None
        
    def remove_tool_from_job(self, tool):
        """Remove tool from current job"""
        if not self.job_manager:
            return False
            
        current_job = self.job_manager.get_current_job()
        if not current_job:
            return False
            
        # Remove tool from job
        if tool in current_job.tools:
            current_job.tools.remove(tool)
            self._update_job_view()
            print(f"DEBUG: Removed tool {tool.name} from job")
            return True
        return False
