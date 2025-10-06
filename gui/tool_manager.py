from PyQt5.QtCore import QObject, QStringListModel
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from job.job_manager import Job, JobManager
from tools.base_tool import BaseTool
from gui.job_tree_view import JobTreeView
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
        
    def setup(self, job_manager, tool_view, job_view, tool_combo_box, main_window=None):
        """Thiết lập các tham chiếu đến các widget UI và job manager"""
        self.job_manager = job_manager
        self._tool_view = tool_view
        self._job_view = job_view
        self._tool_combo_box = tool_combo_box
        self.main_window = main_window  # Add main_window reference
        
        # Add Camera Source and Classification Tool to tool combo box if not already present
        if self._tool_combo_box:
            camera_source_text = "Camera Source"
            items = [self._tool_combo_box.itemText(i) for i in range(self._tool_combo_box.count())]
            if camera_source_text not in items:
                self._tool_combo_box.addItem(camera_source_text)
                logging.info(f"ToolManager: Added {camera_source_text} to tool combo box")
            classification_text = "Classification Tool"
            if classification_text not in items:
                self._tool_combo_box.addItem(classification_text)
                logging.info(f"ToolManager: Added {classification_text} to tool combo box")
        
        # Setup job view - check if it's our custom JobTreeView
        if self._job_view:
            if isinstance(self._job_view, JobTreeView):
                # Connect signals for custom tree view
                self._job_view.tool_moved.connect(self.on_tool_moved)
                self._job_view.tool_selected.connect(self.on_tool_selected)
                logging.info("ToolManager: Connected to custom JobTreeView")
            else:
                # Standard QTreeView setup
                from PyQt5.QtWidgets import QAbstractItemView
                self._job_view.setSelectionMode(QAbstractItemView.SingleSelection)
                self._job_view.setSelectionBehavior(QAbstractItemView.SelectRows)
            
        self._update_job_view()
        logging.info("ToolManager: Setup completed")
        
    def on_tool_moved(self, from_index, to_index):
        """Handle tool reordering from drag-drop"""
        if not self.job_manager:
            return
            
        job = self.job_manager.get_current_job()
        if not job or from_index >= len(job.tools) or to_index >= len(job.tools):
            return
            
        # Reorder tools in job
        tool = job.tools.pop(from_index)
        job.tools.insert(to_index, tool)
        
        # Update UI
        self._update_job_view()
        logging.info(f"ToolManager: Tool moved from {from_index} to {to_index}")
        
    def on_tool_selected(self, tool_index):
        """Handle tool selection from tree view"""
        if not self.job_manager:
            return
            
        job = self.job_manager.get_current_job()
        if not job or tool_index >= len(job.tools):
            return
            
        tool = job.tools[tool_index]
        logging.info(f"ToolManager: Tool selected at index {tool_index}: {getattr(tool, 'name', 'Unknown')}")
        
        # You can add additional logic here for tool selection
        # For example, updating tool properties panel, etc.
        
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
            print(f"DEBUG: on_apply_setting called for tool: {self._pending_tool}")
            logging.info(f"ToolManager: Applying settings for tool: {self._pending_tool}")
            # Xử lý các loại tool khác nhau
            tool = None
            
            if self._pending_tool == "Detect Tool":
                config = self._pending_tool_config if self._pending_tool_config is not None else {}
                algorithm = config.get('algorithmComboBox', '')
                if not algorithm:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(None, "Thiếu thông tin mô hình", "Bạn phải chọn mô hình (algorithm) trước khi thêm Detect Tool.")
                    logging.warning("ToolManager: User tried to add Detect Tool without algorithm.")
                    return None
                try:
                    from tools.detection.detect_tool import create_detect_tool_from_manager_config
                    tool = create_detect_tool_from_manager_config(config)
                    logging.info("ToolManager: Created DetectTool instance via factory.")
                except Exception as e:
                    logging.error(f"ToolManager: Failed to create DetectTool: {e}")
                    from tools.base_tool import GenericTool
                    tool = GenericTool(self._pending_tool, config=self._pending_tool_config)
            elif self._pending_tool == "Camera Source":
                # Xử lý Camera Source tool
                from tools.camera_tool import CameraTool
                config = self._pending_tool_config if self._pending_tool_config is not None else {}
                
                # Lấy thông tin camera từ camera manager
                if hasattr(self.parent(), 'camera_manager') and self.parent().camera_manager:
                    camera_manager = self.parent().camera_manager
                    
                    # Lấy các thông số của camera
                    exposure_value = camera_manager.get_exposure_value() if hasattr(camera_manager, 'get_exposure_value') else 0
                    gain_value = camera_manager.get_gain_value() if hasattr(camera_manager, 'get_gain_value') else 0
                    ev_value = camera_manager.get_ev_value() if hasattr(camera_manager, 'get_ev_value') else 0
                    is_auto_exposure = camera_manager.is_auto_exposure() if hasattr(camera_manager, 'is_auto_exposure') else False
                    
                    # Lấy thông tin xoay camera
                    rotation_angle = 0
                    if hasattr(camera_manager.camera_view, 'get_rotation_angle'):
                        rotation_angle = camera_manager.camera_view.get_rotation_angle()
                    
                    # Cập nhật config
                    config.update({
                        'exposure': exposure_value,
                        'gain': gain_value,
                        'ev': ev_value,
                        'is_auto_exposure': is_auto_exposure,
                        'rotation_angle': rotation_angle
                    })

                    # Persist current camera mode (live/trigger) into CameraTool config
                    try:
                        mode = None
                        if hasattr(camera_manager, 'current_mode'):
                            mode = camera_manager.current_mode
                        # Fallback to buttons
                        if not mode and hasattr(camera_manager, 'trigger_camera_mode') and camera_manager.trigger_camera_mode and camera_manager.trigger_camera_mode.isChecked():
                            mode = 'trigger'
                        if not mode:
                            mode = 'live'
                        config['camera_mode'] = mode
                        if mode == 'trigger':
                            config['enable_external_trigger'] = True
                    except Exception:
                        pass
                    
                    print(f"DEBUG: Camera settings captured - exposure: {exposure_value}, gain: {gain_value}, rotation_angle: {rotation_angle}")
                    logging.info(f"ToolManager: Camera settings captured - exposure: {exposure_value}, gain: {gain_value}, rotation_angle: {rotation_angle}")
                
                # Tạo Camera Tool
                tool = CameraTool("Camera Source", config=config)
                
                # Đảm bảo camera tool có tên và display_name đúng
                tool.name = "Camera Source"
                tool.display_name = "Camera Source" 
                print(f"DEBUG: Created Camera Source tool with config: {config}")
                print(f"DEBUG: Tool details: name={tool.name}, display_name={tool.display_name}, id={tool.tool_id}")
                logging.info(f"ToolManager: Created CameraTool instance. name={tool.name}, display_name={tool.display_name}, id={tool.tool_id}")
                
                # Register Camera Tool with Camera Manager
                if hasattr(self.parent(), 'camera_manager') and self.parent().camera_manager:
                    camera_manager = self.parent().camera_manager
                    
                    # Set camera_manager reference in CameraTool (Single Source of Truth)
                    tool.camera_manager = camera_manager
                    print(f"DEBUG: Set camera_manager reference in CameraTool")
                    
                    if hasattr(camera_manager, 'register_tool'):
                        print("DEBUG: Registering Camera Tool with Camera Manager")
                        camera_manager.register_tool(tool)
                        logging.info("ToolManager: Registered Camera Tool with Camera Manager")
                
                # Enable camera buttons after adding Camera Source tool
                if hasattr(self.parent(), 'camera_manager') and self.parent().camera_manager:
                    camera_manager = self.parent().camera_manager
                    if hasattr(camera_manager, 'enable_camera_buttons'):
                        camera_manager.enable_camera_buttons()
                        print("DEBUG: Camera buttons enabled")
                        logging.info("ToolManager: Camera buttons enabled after adding Camera Source tool")
            elif self._pending_tool == "Save Image":
                # Handle Save Image tool
                from tools.saveimage_tool import SaveImageTool
                config = self._pending_tool_config if self._pending_tool_config is not None else {}

                print(f"DEBUG: Creating SaveImage tool with config: {config}")
                logging.info(f"ToolManager: Creating SaveImage tool with config: {config}")

                # Create SaveImage tool
                tool = SaveImageTool("Save Image", config=config)

                # Debug: Check if tool has required attributes
                tool_name = getattr(tool, 'name', 'MISSING_NAME')
                tool_display_name = getattr(tool, 'display_name', 'MISSING_DISPLAY_NAME')

                print(f"DEBUG: Created SaveImage tool: name={tool_name}, display_name={tool_display_name}")
                logging.info(f"ToolManager: Created SaveImageTool instance. name={tool_name}, display_name={tool_display_name}")

                # Ensure name attribute exists (fallback)
                if not hasattr(tool, 'name'):
                    tool.name = "Save Image"
                    logging.warning("ToolManager: Added missing 'name' attribute to SaveImageTool")
                if not hasattr(tool, 'display_name'):
                    tool.display_name = "Save Image"
                    logging.warning("ToolManager: Added missing 'display_name' attribute to SaveImageTool")
            elif self._pending_tool == "Classification Tool":
                # Handle Classification Tool
                from tools.classification_tool import ClassificationTool
                config = {}
                # Prefer reading from ClassificationToolManager combos
                mw = self.parent() if hasattr(self, 'parent') else None
                if not mw and hasattr(self, 'main_window'):
                    mw = self.main_window
                model_name = None
                expected_class = None
                result_display = True  # Enable OK/NG display by default
                try:
                    ctm = getattr(mw, 'classification_tool_manager', None) if mw else None
                    model_combo = getattr(ctm, 'model_combo', None) if ctm else None
                    class_combo = getattr(ctm, 'class_combo', None) if ctm else None
                    if model_combo:
                        model_name = model_combo.currentText()
                    if class_combo:
                        expected_class = class_combo.currentText()
                        if expected_class in ("Select Class...", "No classes"):
                            expected_class = None
                    # Try checkbox via main window if present
                    if hasattr(mw, 'class_resultDisplayCheckBox') and mw.class_resultDisplayCheckBox:
                        result_display = mw.class_resultDisplayCheckBox.isChecked()
                except Exception as e:
                    logging.warning(f"ToolManager: Fallback to MW classification widgets failed: {e}")

                # Resolve model_path using ModelManager (classification dir)
                model_path = ''
                try:
                    from tools.detection.model_manager import ModelManager
                    from pathlib import Path
                    project_root = Path(__file__).parent.parent
                    models_dir = project_root / 'model' / 'classification'
                    mm = ModelManager(str(models_dir))
                    if model_name and model_name not in ("Select Model...", "No models found", "Error loading models"):
                        info = mm.get_model_info(model_name)
                        if info:
                            model_path = info.get('path', '')
                except Exception as e:
                    logging.error(f"ToolManager: Error resolving classification model path: {e}")

                # Validate minimal config
                if not model_name or model_name in ("Select Model...", "No models found", "Error loading models") or not model_path:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(None, "Thiếu thông tin mô hình", "Bạn phải chọn mô hình hợp lệ cho Classification Tool.")
                    logging.warning("ToolManager: Invalid model selection for Classification Tool")
                    return None

                config.update({
                    'model_name': model_name,
                    'model_path': model_path,
                    'expected_class_name': expected_class or '',
                    'result_display_enable': bool(result_display),
                })

                tool = ClassificationTool("Classification Tool", config=config)
            else:
                from tools.base_tool import GenericTool
                config = self._pending_tool_config if self._pending_tool_config is not None else {}
                tool = GenericTool(self._pending_tool, config=config)
            
            # Thêm tool vào job hiện tại (chỉ khi đã hợp lệ)
            if tool is not None:
                success = self.add_tool_to_job_with_tool(tool)
                if success:
                    logging.info(f"ToolManager: Tool '{self._pending_tool}' with configuration added to job")
                    # Log danh sách công cụ sau khi thêm
                    current_job = self.job_manager.get_current_job()
                    if current_job:
                        logging.info(f"ToolManager: Current job now has {len(current_job.tools)} tools")
                        for i, t in enumerate(current_job.tools):
                            t_name = getattr(t, 'name', 'Unknown')
                            t_display = getattr(t, 'display_name', 'No display')
                            t_id = getattr(t, 'tool_id', 'No ID')
                            logging.info(f"ToolManager: Job tool {i}: name={t_name}, display_name={t_display}, id={t_id}")
                    
                    # Don't auto-start camera for Camera Source - user must choose manually
                    if self._pending_tool == "Camera Source":
                        print("DEBUG: Camera Source tool added - camera stopped, user must manually restart")
                        logging.info("ToolManager: Camera Source tool added - user must manually restart camera")
                else:
                    logging.error(f"ToolManager: Failed to add tool '{self._pending_tool}' to job")
                
            # Reset biến tạm
            pending_tool_type = self._pending_tool  # Lưu lại loại tool trước khi reset
            self._pending_tool = None
            self._pending_tool_config = None
            self._pending_detection_area = None
            
            # Force update job view
            self._force_update_job_view()

            # Don't auto-restart camera for Camera Source - user must choose manually
            print("DEBUG: Tool apply completed - user must manually start camera if needed")
            
            # For Classification Tool, return to palette page similar to Save Image UX
            try:
                if pending_tool_type == "Classification Tool" and hasattr(self, 'main_window') and self.main_window:
                    if hasattr(self.main_window, 'settings_manager') and self.main_window.settings_manager:
                        self.main_window.settings_manager.return_to_palette_page()
            except Exception:
                pass
            
            return tool  # Return Tool object instead of name
        else:
            logging.error(f"ToolManager: No tool name provided (_pending_tool is None)")
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
        if not hasattr(tool, 'name'):
            print("DEBUG: Tool doesn't have a name attribute!")
            logging.error("ToolManager: Tool doesn't have a name attribute")
            # Kiểm tra xem có phải là dictionary không
            if isinstance(tool, dict):
                print(f"DEBUG: Tool is a dictionary: {tool}")
                from tools.base_tool import GenericTool
                tool = GenericTool("Unknown Tool", config=tool)
                print(f"DEBUG: Converted dictionary to GenericTool: {tool.name}")
            else:
                return False
                
        print(f"DEBUG: add_tool_to_job_with_tool called with tool: {tool.name}")
        print(f"DEBUG: tool type: {type(tool).__name__}, display_name: {getattr(tool, 'display_name', 'N/A')}")
        
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
            from job.job_manager import Job
            current_job = Job("Job 1")
            self.job_manager.add_job(current_job)
            print(f"DEBUG: Created new job: {current_job.name}")

        # Add the tool to the current job
        print(f"DEBUG: Adding tool to job. Current tools count: {len(current_job.tools)}")
        print(f"DEBUG: Adding tool: {getattr(tool, 'display_name', tool.name)}, type: {type(tool).__name__}")
        
        # Make sure the tool has the right name and display_name for Camera Source
        if hasattr(tool, 'name') and "camera" in tool.name.lower():
            tool.name = "Camera Source"
            tool.display_name = "Camera Source"
            print("DEBUG: Normalized Camera Source tool name")
            
            # Kiểm tra đã import tools.camera_tool chưa
            try:
                from tools.camera_tool import CameraTool
                # Nếu tool không phải là instance của CameraTool, chuyển đổi nó
                if not isinstance(tool, CameraTool):
                    print("DEBUG: Converting tool to CameraTool")
                    config = getattr(tool, 'config', {})
                    tool = CameraTool("Camera Source", config=config)
                    print(f"DEBUG: Converted to CameraTool: {tool.name}, display_name: {tool.display_name}")
            except ImportError:
                print("DEBUG: Could not import CameraTool")
        
        # Add tool to job
        added_tool = current_job.add_tool(tool)
        
        print(f"DEBUG: After adding tool. Tools count: {len(current_job.tools)}")
        print(f"DEBUG: Tool added: {getattr(tool, 'display_name', tool.name)}")
        
        # Update camera button state if this is a Camera Tool
        if hasattr(tool, 'name') and tool.name == "Camera Source" and hasattr(self, 'parent'):
            parent = self.parent()
            if parent and hasattr(parent, '_update_camera_button_state'):
                print("DEBUG: Updating camera button state after adding Camera Tool")
                parent._update_camera_button_state()
        
        # Kiểm tra và in danh sách tất cả các tool trong job để debug
        print("DEBUG: LIST OF ALL TOOLS IN JOB:")
        for idx, t in enumerate(current_job.tools):
            tool_id = getattr(t, 'tool_id', idx)
            display_name = getattr(t, 'display_name', t.name if hasattr(t, 'name') else 'Unknown')
            tool_type = type(t).__name__
            print(f"DEBUG:   Tool {idx}: ID={tool_id}, Name='{display_name}', Type={tool_type}")
        
        # Kiểm tra xem có cần kích hoạt camera không
        is_camera_source = False
        if hasattr(tool, 'name') and "camera" in tool.name.lower():
            is_camera_source = True
            print("DEBUG: Added Camera Source tool - enabling camera")
            
            # Kích hoạt camera view và các nút điều khiển
            if hasattr(self.parent(), 'camera_manager') and self.parent().camera_manager:
                camera_manager = self.parent().camera_manager
                
                # Bật các nút điều khiển camera
                if hasattr(camera_manager, 'enable_camera_buttons'):
                    camera_manager.enable_camera_buttons()
                    print("DEBUG: Enabled camera buttons")
                
                # Tự động bật job execution nếu chưa bật
                if hasattr(camera_manager, 'camera_stream') and camera_manager.camera_stream:
                    if not camera_manager.camera_stream.job_enabled:
                        print("DEBUG: Enabling job execution for camera")
                        camera_manager.camera_stream.job_enabled = True
                        if hasattr(camera_manager, 'job_toggle_btn') and camera_manager.job_toggle_btn:
                            camera_manager.job_toggle_btn.setChecked(True)
                            print("DEBUG: Set job toggle button to checked")
                    # If workflow has been disabled globally, immediately turn job off
                    if hasattr(camera_manager, 'workflow_enabled') and (not camera_manager.workflow_enabled):
                        print("DEBUG: Workflow disabled -> forcing job execution OFF")
                        camera_manager.camera_stream.job_enabled = False
                        if hasattr(camera_manager, 'job_toggle_btn') and camera_manager.job_toggle_btn:
                            camera_manager.job_toggle_btn.setChecked(False)
                
                # Tự động bắt đầu preview camera
                if hasattr(camera_manager, 'start_camera_preview'):
                    # Thay vì tự động bắt đầu camera, chỉ đảm bảo UI được cập nhật
                    print("DEBUG: Setting up camera UI without auto-starting camera")
                    # Cập nhật UI mà không bắt đầu camera tự động
                    camera_manager.update_camera_mode_ui()
                    print("DEBUG: Camera UI updated, waiting for user to start camera manually")
                
            # Kích hoạt job view cập nhật để đảm bảo tool hiển thị
            self._force_update_job_view()
            print("DEBUG: Forced job view update after adding Camera Source")
        
        # Print all tools in the job for debugging
        for i, t in enumerate(current_job.tools):
            display_name = getattr(t, 'display_name', getattr(t, 'name', f"Tool {i}"))
            print(f"DEBUG: Tool {i}: {display_name}, type: {type(t).__name__}")

        # Đảm bảo job view được cập nhật
        self._update_job_view()
        self._force_update_job_view()  # Gọi thêm một lần để đảm bảo UI cập nhật
        
        logging.info(f"ToolManager: Tool '{getattr(tool, 'name', 'Unknown')}' added to the current job.")
        return True

    def _update_job_view(self):
        """Cập nhật hiển thị job trong UI với QTreeView hoặc JobTreeView"""
        print(f"DEBUG: _update_job_view called")
        print(f"DEBUG: _job_view exists: {self._job_view is not None}")
        print(f"DEBUG: job_manager exists: {self.job_manager is not None}")
        
        if not self._job_view or not self.job_manager:
            print("DEBUG: Missing job_view or job_manager")
            return
            
        job = self.job_manager.get_current_job()
        print(f"DEBUG: Current job: {job}")
        
        if job:
            # Check if we're using custom JobTreeView
            if isinstance(self._job_view, JobTreeView):
                # Use custom tree view method
                self._job_view.update_job_view(job)
                print(f"DEBUG: Updated custom JobTreeView with {len(job.tools)} tools")
                
                # Refresh source output combo when job tools change
                if (hasattr(self, 'main_window') and self.main_window and 
                    hasattr(self.main_window, 'camera_manager') and self.main_window.camera_manager):
                    self.main_window.camera_manager.refresh_source_output_combo()
                    print("DEBUG: Source output combo refreshed after job update")
                return
                
            # Standard QTreeView implementation
            # Create tree model
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["Tools"])
            
            # Create job root item
            job_item = QStandardItem(f"📁 {job.name}")
            job_item.setEditable(False)
            
            # Add tools as children
            print(f"DEBUG: Building job view with {len(job.tools)} tools")
            for i, tool in enumerate(job.tools):
                # Kiểm tra xem tool có phải là dictionary không
                if isinstance(tool, dict):
                    # Xử lý cho tool dạng dictionary
                    tool_name = tool.get('display_name', tool.get('name', f"Tool #{i+1}"))
                    tool_id = tool.get('tool_id', i+1)
                    tool_type = "Dict"
                    
                    print(f"DEBUG: Processing dictionary tool {i}: {tool_name}, ID={tool_id}, Type={tool_type}")
                else:
                    # Xử lý cho tool là object
                    tool_name = getattr(tool, 'display_name', 
                                      getattr(tool, 'name', f"Tool #{i+1}"))
                    tool_id = getattr(tool, 'tool_id', i+1)
                    tool_type = type(tool).__name__
                    
                    print(f"DEBUG: Processing object tool {i}: {tool_name}, ID={tool_id}, Type={tool_type}")
                
                # Hiển thị tên tool dựa vào loại tool
                if isinstance(tool_name, str) and tool_name.lower() == "camera source":
                    # Special handling for Camera Source
                    tool_id_str = f"📷 Camera Source #{tool_id}"
                    print(f"DEBUG: Creating Camera Source item: {tool_id_str}")
                elif isinstance(tool, dict):
                    # Nếu là dictionary (thường là từ DetectTool)
                    if 'model_name' in tool:
                        # Đây là DetectTool
                        model_name = tool.get('model_name', 'Unknown')
                        tool_id_str = f"🔍 Detect ({model_name}) #{tool_id}"
                        print(f"DEBUG: Creating DetectTool item: {tool_id_str}")
                    else:
                        # Tool khác dưới dạng dictionary
                        tool_id_str = f"⚙️ Tool #{tool_id}"
                        print(f"DEBUG: Creating generic dictionary tool item: {tool_id_str}")
                elif hasattr(tool, 'display_name') and tool.display_name:
                    # Nếu là object BaseTool với display_name
                    tool_id_str = f"🔧 {tool.display_name} #{tool_id}"
                    print(f"DEBUG: Creating named tool item: {tool_id_str}")
                else:
                    # Trường hợp khác
                    tool_id_str = f"⚙️ Tool #{tool_id}"
                    print(f"DEBUG: Creating generic tool item: {tool_id_str}")
                
                # Add flow indicator for non-first tools
                if i > 0:
                    tool_id_str = f"↓ {tool_id_str}"
                
                tool_item = QStandardItem(tool_id_str)
                tool_item.setEditable(False)
                # Store tool reference for later use
                tool_item.setData(tool, role=256)  # Custom role
                job_item.appendRow(tool_item)
                print(f"DEBUG: Added tool item: {tool_id_str}")
            
            model.appendRow(job_item)
            self._job_view.setModel(model)
            self._job_view.expandAll()
            print(f"DEBUG: Job view updated with {len(job.tools)} tools")
            
            # Refresh source output combo when job tools change
            if (hasattr(self, 'main_window') and self.main_window and 
                hasattr(self.main_window, 'camera_manager') and self.main_window.camera_manager):
                self.main_window.camera_manager.refresh_source_output_combo()
                print("DEBUG: Source output combo refreshed after job update")
        else:
            # No job, empty model
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["Tools"])
            self._job_view.setModel(model)
            print("DEBUG: Job view updated with empty model (no job)")
            
            # Still refresh source output combo for empty job
            if (hasattr(self, 'main_window') and self.main_window and 
                hasattr(self.main_window, 'camera_manager') and self.main_window.camera_manager):
                self.main_window.camera_manager.refresh_source_output_combo()
                print("DEBUG: Source output combo refreshed for empty job")
            
    def _force_update_job_view(self):
        """Force UI update and ensure jobView is refreshed"""
        if not self._job_view or not self.job_manager:
            return
            
        from PyQt5.QtWidgets import QApplication
        
        print("DEBUG: _force_update_job_view called - Performing forced UI refresh")
        
        # Lấy thông tin hiện tại về job và tool
        current_job = self.job_manager.get_current_job()
        if current_job:
            print(f"DEBUG: Current job has {len(current_job.tools)} tools:")
            for i, tool in enumerate(current_job.tools):
                tool_name = getattr(tool, 'name', 'Unknown')
                tool_display = getattr(tool, 'display_name', 'No display')
                tool_id = getattr(tool, 'tool_id', 'No ID')
                print(f"DEBUG:   Tool {i}: name={tool_name}, display_name={tool_display}, id={tool_id}")
        
        # Process pending events to ensure UI updates
        QApplication.processEvents()
        
        # Update job view
        self._update_job_view()
        
        # Force expand all items
        self._job_view.expandAll()
        
        # Ensure the view is updated
        self._job_view.viewport().update()
        
        # Process events again
        QApplication.processEvents()
        
        # Notify main window to update workflow view if available
        if self.parent() and hasattr(self.parent(), '_update_workflow_view'):
            self.parent()._update_workflow_view()
            
        logging.info("ToolManager: Forced job view update completed")
        
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
            
        # Remove tool from job using Job.remove_tool to clean connections and rebuild workflow
        try:
            for i, job_tool in enumerate(current_job.tools):
                if job_tool is tool or getattr(job_tool, 'tool_id', None) == getattr(tool, 'tool_id', None):
                    removed = current_job.remove_tool(i)
                    if removed:
                        self._update_job_view()
                        # Lấy tên hiển thị của tool một cách an toàn
                        if hasattr(tool, 'display_name'):
                            tool_name = tool.display_name
                        elif hasattr(tool, 'name'):
                            tool_name = tool.name
                        elif isinstance(tool, dict) and 'model_name' in tool:
                            tool_name = f"Detect ({tool.get('model_name', 'Unknown')})"
                        else:
                            tool_name = str(tool)
                        print(f"DEBUG: Removed tool {tool_name} from job (cleaned connections)")
                        return True
                    break
        except Exception as e:
            logging.warning(f"ToolManager: Error removing tool: {e}")
            return False
        return False
