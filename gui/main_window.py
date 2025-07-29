from PyQt5.QtGui import QCloseEvent
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsView, QWidget, QStackedWidget, QComboBox, QPushButton, QSlider, QLineEdit, QProgressBar, QLCDNumber, QTabWidget, QListView, QTreeView, QMainWindow, QSpinBox, QDoubleSpinBox
from PyQt5 import uic
import os
import logging
from job.job_manager import JobManager
from gui.tool_manager import ToolManager
from gui.settings_manager import SettingsManager
from gui.camera_manager import CameraManager

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Khởi tạo các biến thành viên
        self.tool_manager = ToolManager(self)
        self.settings_manager = SettingsManager(self)
        self.camera_manager = CameraManager(self)
        self.job_manager = JobManager()
        
        # Load UI từ file .ui
        ui_path = os.path.join(os.path.dirname(__file__), '..', 'mainUI.ui')
        uic.loadUi(ui_path, self)
        
        # Tìm và kết nối các widget chính
        self._find_widgets()
        
        # Thiết lập các manager và kết nối signals/slots
        self._setup_managers()
        
        # Kết nối các widget với các hàm xử lý sự kiện
        self._connect_signals()
        
        logging.info("MainWindow initialized successfully")
        
    def _find_widgets(self):
        """Tìm tất cả các widget cần thiết từ UI file"""
        # Camera view widgets
        self.cameraView = self.findChild(QGraphicsView, 'cameraView')
        self.focusBar = self.findChild(QProgressBar, 'focusBar')
        self.fpsNum = self.findChild(QLCDNumber, 'fpsNum')
        self.executionTime = self.findChild(QLCDNumber, 'executionTime')
        
        # Camera control buttons
        self.liveCamera = self.findChild(QPushButton, 'liveCamera')
        self.triggerCamera = self.findChild(QPushButton, 'triggerCamera')
        self.zoomIn = self.findChild(QPushButton, 'zoomIn')
        self.zoomOut = self.findChild(QPushButton, 'zoomOut')
        self.rotateLeft = self.findChild(QPushButton, 'rotateLeft')
        self.rotateRight = self.findChild(QPushButton, 'rotateRight')
        self.triggerCameraMode = self.findChild(QPushButton, 'triggerCameraMode')
        self.liveCameraMode = self.findChild(QPushButton, 'liveCameraMode')
        
        # Camera settings widgets
        self.exposureEdit = self.findChild(QDoubleSpinBox, 'exposureEdit')  # Changed to QDoubleSpinBox
        self.exposureSlider = self.findChild(QSlider, 'exposureSlider')
        self.gainEdit = self.findChild(QDoubleSpinBox, 'gainEdit')  # Also change to QDoubleSpinBox
        self.gainSlider = self.findChild(QSlider, 'gainSlider')
        self.evEdit = self.findChild(QDoubleSpinBox, 'evEdit')  # Also change to QDoubleSpinBox
        self.evSlider = self.findChild(QSlider, 'evSlider')
        self.manualExposure = self.findChild(QPushButton, 'manualExposure')
        self.autoExposure = self.findChild(QPushButton, 'autoExposure')
        
        # Settings control buttons
        self.applySetting = self.findChild(QPushButton, 'applySetting')
        self.cancelSetting = self.findChild(QPushButton, 'cancelSetting')
        
        # Frame size control widgets
        self.widthCameraFrameSpinBox = self.findChild(QSpinBox, 'widthCameraFrameSpinBox')
        self.heightCameraFrameSpinBox = self.findChild(QSpinBox, 'heightCameraFrameSpinBox')
        
        # Job management widgets
        self.paletteTab = self.findChild(QTabWidget, 'paletteTab')
        self.jobTab = self.findChild(QTreeView, 'jobTab')
        self.jobView = self.findChild(QTreeView, 'jobView')
        self.removeJob = self.findChild(QPushButton, 'removeJob')
        self.editJob = self.findChild(QPushButton, 'editJob')
        self.addJob = self.findChild(QPushButton, 'addJob')
        self.loadJob = self.findChild(QPushButton, 'loadJob')
        self.saveJob = self.findChild(QPushButton, 'saveJob')
        self.runJob = self.findChild(QPushButton, 'runJob')
        
        # Tool management widgets
        self.toolView = self.findChild(QListView, 'toolView')
        self.addTool = self.findChild(QPushButton, 'addTool')
        self.editTool = self.findChild(QPushButton, 'editTool')
        self.removeTool = self.findChild(QPushButton, 'removeTool')
        self.cancleTool = self.findChild(QPushButton, 'cancleTool')
        self.toolComboBox = self.findChild(QComboBox, 'toolComboBox')
        
        # Settings widgets
        self.settingStackedWidget = self.findChild(QStackedWidget, 'settingStackedWidget')
        self.cameraSettingPage = self.findChild(QWidget, 'cameraSettingPage')
        self.detectSettingPage = self.findChild(QWidget, 'detectSettingPage')
        self.cameraSettingFrame = self.findChild(QWidget, 'cameraSettingFrame')
        self.detectSettingFrame = self.findChild(QWidget, 'detectSettingFrame')
        
        # Detect tool widgets
        self.drawAreaButton = self.findChild(QPushButton, 'drawAreaButton')
        self.xPositionLineEdit = self.findChild(QLineEdit, 'xPositionLineEdit')
        self.yPositionLineEdit = self.findChild(QLineEdit, 'yPositionLineEdit')
        
        # Thiết lập cấu hình cho DoubleSpinBox thay vì validators
        if self.exposureEdit:
            self.exposureEdit.setMinimum(1.0)  # 1μs minimum
            self.exposureEdit.setMaximum(10000000.0)  # 10s maximum  
            self.exposureEdit.setValue(10000.0)  # 10ms default (10000μs)
            self.exposureEdit.setDecimals(1)  # 1 decimal place
            self.exposureEdit.setSuffix(" μs")  # Microseconds unit suffix
            
        if self.gainEdit:
            self.gainEdit.setMinimum(1.0)  # 1.0 minimum gain
            self.gainEdit.setMaximum(16.0)  # 16.0 maximum gain
            self.gainEdit.setValue(1.0)  # 1.0 default gain
            self.gainEdit.setDecimals(2)  # 2 decimal places
            
        if self.evEdit:
            self.evEdit.setMinimum(-2.0)  # -2.0 minimum EV
            self.evEdit.setMaximum(2.0)  # 2.0 maximum EV
            self.evEdit.setValue(0.0)  # 0.0 default EV
            self.evEdit.setDecimals(1)  # 1 decimal place
            
        # Thiết lập range cho các slider (bỏ exposureSlider vì không dùng nữa)
        if self.gainSlider:
            self.gainSlider.setMinimum(0)
            self.gainSlider.setMaximum(100)
        if self.evSlider:
            self.evSlider.setMinimum(-1)
            self.evSlider.setMaximum(1)
            
        # Tìm các widget Detect Tool settings
        if self.detectSettingFrame:
            self.thresholdSlider = self.findChild(QSlider, 'thresholdSlider')
            self.thresholdSpinBox = self.findChild(QSlider, 'thresholdSpinBox')  # Note: This might need to be changed to QSpinBox
            self.minConfidenceEdit = self.findChild(QLineEdit, 'minConfidenceEdit')  # Note: This might need to be changed to QDoubleSpinBox
        
    def _setup_managers(self):
        """Thiết lập và kết nối các manager"""
        # Setup ToolManager
        self.tool_manager.setup(
            self.job_manager,
            self.toolView,
            self.jobView,
            self.toolComboBox
        )
        
        # Setup SettingsManager
        self.settings_manager.setup(
            self.settingStackedWidget,
            self.cameraSettingPage,
            self.detectSettingPage,
            self.applySetting,
            self.cancleSetting
        )
        
        # Setup CameraManager
        self.camera_manager.setup(
            self.cameraView,
            self.exposureEdit,
            self.gainSlider,
            self.gainEdit,
            self.evSlider,
            self.evEdit,
            self.focusBar,
            self.fpsNum
        )
        
        # Setup frame size spinboxes if they exist
        if hasattr(self, 'widthCameraFrameSpinBox') and hasattr(self, 'heightCameraFrameSpinBox'):
            self.camera_manager.setup_frame_size_spinboxes(
                self.widthCameraFrameSpinBox,
                self.heightCameraFrameSpinBox
            )
        
        # Setup camera control buttons (handle missing widgets gracefully)
        self.camera_manager.setup_camera_buttons(
            live_camera_btn=getattr(self, 'liveCamera', None),
            trigger_camera_btn=getattr(self, 'triggerCamera', None),
            auto_exposure_btn=getattr(self, 'autoExposure', None),
            manual_exposure_btn=getattr(self, 'manualExposure', None),
            apply_settings_btn=getattr(self, 'applySetting', None),
            cancel_settings_btn=getattr(self, 'cancelSetting', None),
            job_toggle_btn=getattr(self, 'runJob', None)  # Use runJob as toggle button
        )
        
        # Link CameraManager with SettingsManager for synchronization
        self.camera_manager.set_settings_manager(self.settings_manager)
        
        # Setup area change connections
        if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
            if hasattr(self.camera_manager.camera_view, 'area_changed'):
                self.camera_manager.camera_view.area_changed.connect(self._on_area_changed)
        
        # Enable UI after setup is complete
        self.camera_manager.set_ui_enabled(True)
        
    def _connect_signals(self):
        """Kết nối các signal với các slot tương ứng"""
        # Tool management connections
        if self.addTool:
            self.addTool.clicked.connect(self._on_add_tool)
            logging.info("addTool button connected to _on_add_tool.")
        
        if self.editTool:
            self.editTool.clicked.connect(self._on_edit_tool)
            logging.info("editTool button connected to _on_edit_tool.")
            
        if self.removeTool:
            self.removeTool.clicked.connect(self._on_remove_tool)
            logging.info("removeTool button connected to _on_remove_tool.")
        
        if self.cancleTool:
            self.cancleTool.clicked.connect(self.tool_manager.on_remove_tool_from_job)
            
        if self.editJob:
            self.editJob.clicked.connect(self._on_edit_job)
            
        if self.removeJob:
            self.removeJob.clicked.connect(self.tool_manager.on_remove_tool_from_job)
            
        # Settings connections
        if self.applySetting:
            self.applySetting.clicked.connect(self._on_apply_setting)
            
        if self.cancleSetting:
            self.cancleSetting.clicked.connect(self._on_cancel_setting)
            
        # Detect tool connections
        if self.drawAreaButton:
            self.drawAreaButton.clicked.connect(self._on_draw_area_clicked)
            
        # Camera connections
        if self.liveCamera:
            self.liveCamera.setCheckable(True)
            self.liveCamera.clicked.connect(self.camera_manager.on_live_camera_clicked)
            
        if self.triggerCamera:
            self.triggerCamera.clicked.connect(self.camera_manager.on_trigger_camera_clicked)
            
        if self.zoomIn:
            self.zoomIn.clicked.connect(self.camera_manager.zoom_in)
            
        if self.zoomOut:
            self.zoomOut.clicked.connect(self.camera_manager.zoom_out)
            
        if self.rotateLeft:
            self.rotateLeft.clicked.connect(self.camera_manager.rotate_left)
            
        if self.rotateRight:
            self.rotateRight.clicked.connect(self.camera_manager.rotate_right)
            
        if self.manualExposure:
            self.manualExposure.clicked.connect(self.camera_manager.set_manual_exposure_mode)
            
        if self.autoExposure:
            self.autoExposure.clicked.connect(self.camera_manager.set_auto_exposure_mode)
            
        # runJob button is now handled by camera_manager as job_toggle_btn
        # if self.runJob:
        #     self.runJob.clicked.connect(self.run_current_job)
            
        # Job save/load connections
        if self.saveJob:
            self.saveJob.clicked.connect(self.save_current_job)
            
        if self.loadJob:
            self.loadJob.clicked.connect(self.load_job_file)
            
        if self.addJob:
            self.addJob.clicked.connect(self.add_new_job)
            
        if self.removeJob:
            self.removeJob.clicked.connect(self.remove_current_job)
    
    def _on_add_tool(self):
        """Xử lý khi người dùng nhấn nút Add Tool"""
        # Lấy công cụ được chọn
        tool_name = self.tool_manager.on_add_tool()
        if tool_name:
            # Chuyển đến trang cài đặt tương ứng
            self.settings_manager.switch_to_tool_setting_page(tool_name)
    
    def _on_edit_tool(self):
        """Xử lý khi người dùng nhấn nút Edit Tool"""
        # Get selected tool from tool view
        selected_tool = self.tool_manager.get_selected_tool()
        if selected_tool:
            # Edit tool overlay in camera view
            if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                overlay = self.camera_manager.camera_view.edit_tool_overlay(selected_tool.tool_id)
                if overlay:
                    print(f"DEBUG: Editing tool #{selected_tool.tool_id}")
                else:
                    print(f"DEBUG: Tool #{selected_tool.tool_id} overlay not found")
            
            # Switch to detect settings page for editing
            self.settings_manager.switch_to_tool_setting_page(selected_tool.name)
            self._load_tool_config_to_ui(selected_tool)
        else:
            print("DEBUG: No tool selected for editing")
    
    def _on_remove_tool(self):
        """Xử lý khi người dùng nhấn nút Remove Tool"""
        # Get selected tool from tool view
        selected_tool = self.tool_manager.get_selected_tool()
        if selected_tool:
            # Remove tool overlay from camera view
            if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                self.camera_manager.camera_view.remove_tool_overlay(selected_tool.tool_id)
            
            # Remove tool from job
            self.tool_manager.remove_tool_from_job(selected_tool)
            print(f"DEBUG: Removed tool #{selected_tool.tool_id}")
        else:
            print("DEBUG: No tool selected for removal")
    
    def _on_apply_setting(self):
        """Xử lý khi người dùng nhấn nút Apply trong trang cài đặt"""
        
        # Synchronize settings across all pages before applying
        print("DEBUG: Synchronizing settings across pages...")
        self.settings_manager.sync_settings_across_pages()
        
        # Get current page type to handle page-specific logic
        current_page = self.settings_manager.get_current_page_type()
        print(f"DEBUG: Applying settings for page type: {current_page}")
        
        # Handle camera settings page
        if current_page == "camera":
            # Apply camera settings through camera manager
            self.camera_manager.on_apply_settings_clicked()
        
        # Handle detection settings page
        elif current_page == "detection":
            # Thu thập cấu hình từ UI
            ui_widgets = {
                'threshold_slider': getattr(self, 'thresholdSlider', None),
                'min_confidence_edit': getattr(self, 'minConfidenceEdit', None),
                'x_position_edit': self.xPositionLineEdit,
                'y_position_edit': self.yPositionLineEdit
            }
            
            # Collect detection area coordinates
            detection_area = self._collect_detection_area()
            if detection_area:
                ui_widgets['detection_area'] = detection_area
                
                # Add detection area to camera view for visualization with tool ID
                if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                    x1, y1, x2, y2 = detection_area
                    # Use current overlay and update its tool_id, or create new one
                    if self.camera_manager.camera_view.current_overlay:
                        # Update existing overlay from drawing
                        overlay = self.camera_manager.camera_view.current_overlay
                    else:
                        # Create new overlay
                        overlay = self.camera_manager.camera_view.add_tool_overlay(x1, y1, x2, y2)
                    
                    # Disable edit mode after applying
                    overlay.set_edit_mode(False)
                    print(f"DEBUG: Added detection area to camera view: {detection_area}")
                    print("DEBUG: Disabled overlay edit mode after apply")
            
            # Check if we're editing an existing tool or adding a new one
            editing_tool = self.tool_manager.get_current_editing_tool()
            
            if editing_tool:
                # Update existing tool configuration
                print(f"DEBUG: Updating existing tool: {editing_tool.display_name}")
                
                # Update tool config directly
                if detection_area:
                    editing_tool.config.set('detection_area', detection_area)
                
                if ui_widgets.get('threshold_slider'):
                    editing_tool.config.set('threshold', ui_widgets['threshold_slider'].value())
                
                if ui_widgets.get('min_confidence_edit'):
                    editing_tool.config.set('min_confidence', ui_widgets['min_confidence_edit'].value())
                
                print(f"DEBUG: Updated tool config: {editing_tool.config.to_dict()}")
                
                # Clear editing mode
                self.tool_manager.clear_current_editing_tool()
                
            else:
                # Adding new tool
                print("DEBUG: Adding new tool")
                
                # Lưu cấu hình vào tool_manager
                if hasattr(self.tool_manager, '_pending_tool') and self.tool_manager._pending_tool:
                    config = self.settings_manager.collect_tool_config(
                        self.tool_manager._pending_tool,
                        ui_widgets
                    )
                    self.tool_manager.set_tool_config(config)
                
                # Áp dụng cài đặt detection và get added tool
                added_tool = self.tool_manager.on_apply_setting()
                
                # Update overlay with tool_id if tool was added
                if added_tool and hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                    if self.camera_manager.camera_view.current_overlay:
                        overlay = self.camera_manager.camera_view.current_overlay
                        # Update overlay with tool ID and add to overlays dict
                        old_id = overlay.tool_id
                        overlay.tool_id = added_tool.tool_id
                        overlay.update()  # Trigger repaint to show new ID
                        
                        # Move to overlays dict with new tool_id
                        if old_id in self.camera_manager.camera_view.overlays:
                            del self.camera_manager.camera_view.overlays[old_id]
                        self.camera_manager.camera_view.overlays[added_tool.tool_id] = overlay
                        
                        # Disable edit mode
                        overlay.set_edit_mode(False)
                        self.camera_manager.camera_view.current_overlay = None
                        print(f"DEBUG: Updated overlay with tool ID #{added_tool.tool_id}")
            
            # Quay lại trang cài đặt camera
            self.settings_manager.return_to_camera_setting_page()
        
        # Clear pending changes after successful apply
        self.settings_manager.clear_pending_changes()
        print("DEBUG: Settings applied and synchronized successfully")
    
    def _on_cancel_setting(self):
        """Xử lý khi người dùng nhấn nút Cancel trong trang cài đặt"""
        # Disable overlay edit mode when canceling
        if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
            self.camera_manager.camera_view.set_overlay_edit_mode(False)
            print("DEBUG: Disabled overlay edit mode on cancel")
        
        # Hủy bỏ thao tác thêm tool
        self.tool_manager.on_cancel_setting()
        
        # Quay lại trang cài đặt camera
        self.settings_manager.return_to_camera_setting_page()
    
    def _on_edit_job(self):
        """Xử lý khi người dùng nhấn nút Edit Job"""
        print("DEBUG: Edit Job button clicked")
        
        # Get selected tool for editing
        editing_tool = self.tool_manager.on_edit_tool_in_job()
        if not editing_tool:
            print("DEBUG: No tool selected for editing")
            return
        
        print(f"DEBUG: Editing tool: {editing_tool.display_name}")
        
        # Switch to detect settings page
        tool_name = editing_tool.name
        if self.settings_manager.switch_to_tool_setting_page(tool_name):
            # Load tool configuration into UI
            self._load_tool_config_to_ui(editing_tool)
            print(f"DEBUG: Switched to settings page for {tool_name}")
        else:
            print(f"DEBUG: Failed to switch to settings page for {tool_name}")
    
    def _load_tool_config_to_ui(self, tool):
        """Load tool configuration into UI for editing"""
        try:
            config = tool.config.to_dict()
            print(f"DEBUG: Loading tool config: {config}")
            
            # Load detection area if exists
            if 'detection_area' in config:
                x1, y1, x2, y2 = config['detection_area']
                
                # Update position line edits
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                
                if self.xPositionLineEdit:
                    self.xPositionLineEdit.setText(str(center_x))
                if self.yPositionLineEdit:
                    self.yPositionLineEdit.setText(str(center_y))
                
                # Add detection area to camera view for editing
                if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                    # Clear existing areas first
                    self.camera_manager.camera_view.clear_detection_areas()
                    # Add the area for editing with edit mode enabled
                    overlay = self.camera_manager.camera_view.show_detection_area(x1, y1, x2, y2, editable=True)
                    print(f"DEBUG: Loaded detection area for editing: ({x1}, {y1}) to ({x2}, {y2})")
                    print("DEBUG: Enabled overlay edit mode for tool editing")
            
            # Load other settings (threshold, confidence, etc.)
            if 'threshold' in config and hasattr(self, 'thresholdSlider'):
                self.thresholdSlider.setValue(config['threshold'])
            
            if 'min_confidence' in config and hasattr(self, 'minConfidenceEdit'):
                self.minConfidenceEdit.setValue(config['min_confidence'])
                
        except Exception as e:
            print(f"DEBUG: Error loading tool config: {e}")
    
    def _on_draw_area_clicked(self):
        """Xử lý khi người dùng nhấn nút Draw Area"""
        print("DEBUG: Draw Area button clicked")
        
        # Check if there's already an area drawn
        if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
            current_coords = self.camera_manager.camera_view.get_current_area_coords()
            
            if current_coords:
                # If area exists, clear it and allow drawing new one
                print("DEBUG: Existing area found, clearing for new drawing")
                self.camera_manager.camera_view.clear_all_areas()
            
            # Enable drawing mode in camera view
            self.camera_manager.camera_view.set_draw_mode(True)
            
            # Connect area drawing signals
            if hasattr(self.camera_manager.camera_view, 'area_drawn'):
                self.camera_manager.camera_view.area_drawn.connect(self._on_area_drawn)
            
            # Update button state
            if self.drawAreaButton:
                self.drawAreaButton.setText("Drawing...")
                self.drawAreaButton.setEnabled(False)
                
            print("DEBUG: Enabled drawing mode in camera view")
        else:
            print("DEBUG: Camera view not available")
    
    def _on_area_drawn(self, x1, y1, x2, y2):
        """Xử lý khi user đã vẽ xong area"""
        print(f"DEBUG: Area drawn: ({x1}, {y1}) to ({x2}, {y2})")
        
        # Calculate center coordinates
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)
        
        # Update position line edits with center coordinates
        if self.xPositionLineEdit:
            self.xPositionLineEdit.setText(str(center_x))
        if self.yPositionLineEdit:
            self.yPositionLineEdit.setText(str(center_y))
            
        # Reset button state
        if self.drawAreaButton:
            self.drawAreaButton.setText("Draw area")
            self.drawAreaButton.setEnabled(True)
            
        # Disable drawing mode but keep overlay editable in pending state
        if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
            self.camera_manager.camera_view.set_draw_mode(False)
            # Keep overlay editable until applied/canceled
            self.camera_manager.camera_view.set_overlay_edit_mode(True)
            
            print(f"DEBUG: Updated position fields: X={center_x}, Y={center_y}")
    
    def _on_area_changed(self, x1, y1, x2, y2):
        """Xử lý khi area thay đổi (move/resize)"""
        print(f"DEBUG: Area changed: ({x1}, {y1}) to ({x2}, {y2})")
        
        # Calculate center coordinates
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)
        
        # Update position line edits with center coordinates
        if self.xPositionLineEdit:
            self.xPositionLineEdit.setText(str(center_x))
        if self.yPositionLineEdit:
            self.yPositionLineEdit.setText(str(center_y))
            
        print(f"DEBUG: Updated position fields from area change: X={center_x}, Y={center_y}")
    
    def _collect_detection_area(self):
        """Collect detection area coordinates from UI or current drawn area"""
        # First try to get from current drawn area
        if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
            current_coords = self.camera_manager.camera_view.get_current_area_coords()
            if current_coords:
                print(f"DEBUG: Got coordinates from drawn area: {current_coords}")
                return current_coords
        
        # Fallback to text input
        try:
            if self.xPositionLineEdit and self.yPositionLineEdit:
                x_text = self.xPositionLineEdit.text().strip()
                y_text = self.yPositionLineEdit.text().strip()
                
                if x_text and y_text:
                    center_x = int(x_text)
                    center_y = int(y_text)
                    
                    # For now, create a 100x100 area around the center point
                    # Later this can be made configurable
                    area_size = 100
                    x1 = center_x - area_size // 2
                    y1 = center_y - area_size // 2
                    x2 = center_x + area_size // 2
                    y2 = center_y + area_size // 2
                    
                    return (x1, y1, x2, y2)
        except ValueError as e:
            print(f"DEBUG: Error parsing coordinates: {e}")
        
        return None
    
    def save_current_job(self):
        """Lưu job hiện tại vào file"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Save Job", 
                "job.json", 
                "JSON files (*.json)"
            )
            
            if file_path:
                if self.job_manager.save_current_job(file_path):
                    logging.info(f"Job saved successfully to {file_path}")
                else:
                    logging.error("Failed to save job")
                    
        except Exception as e:
            logging.error(f"Error saving job: {str(e)}")
            
    def load_job_file(self):
        """Tải job từ file"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "Load Job", 
                "", 
                "JSON files (*.json)"
            )
            
            if file_path:
                job = self.job_manager.load_job(file_path)
                if job:
                    # Cập nhật UI
                    self.tool_manager._update_job_view()
                    logging.info(f"Job loaded successfully from {file_path}")
                else:
                    logging.error("Failed to load job")
                    
        except Exception as e:
            logging.error(f"Error loading job: {str(e)}")
            
    def add_new_job(self):
        """Tạo job mới"""
        try:
            from PyQt5.QtWidgets import QInputDialog
            
            job_name, ok = QInputDialog.getText(
                self, 
                "New Job", 
                "Enter job name:",
                text="New Job"
            )
            
            if ok and job_name:
                new_job = self.job_manager.create_default_job(job_name)
                self.tool_manager._update_job_view()
                logging.info(f"New job '{job_name}' created")
                
        except Exception as e:
            logging.error(f"Error creating new job: {str(e)}")
            
    def remove_current_job(self):
        """Xóa job hiện tại"""
        try:
            from PyQt5.QtWidgets import QMessageBox
            
            current_job = self.job_manager.get_current_job()
            if not current_job:
                logging.warning("No current job to remove")
                return
                
            reply = QMessageBox.question(
                self, 
                "Remove Job", 
                f"Are you sure you want to remove job '{current_job.name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                current_index = self.job_manager.current_job_index
                if self.job_manager.remove_job(current_index):
                    self.tool_manager._update_job_view()
                    logging.info(f"Job '{current_job.name}' removed")
                else:
                    logging.error("Failed to remove job")
                    
        except Exception as e:
            logging.error(f"Error removing job: {str(e)}")
        
    def run_current_job(self):
        """Chạy job hiện tại"""
        try:
            current_job = self.job_manager.get_current_job()
            if not current_job:
                logging.warning("No current job to run")
                return
                
            if not current_job.tools:
                logging.warning("Current job has no tools")
                return
                
            # Lấy frame hiện tại từ camera
            if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                # TODO: Implement getting current frame from camera view
                # Tạm thời sử dụng test image
                import numpy as np
                test_image = np.zeros((480, 640, 3), dtype=np.uint8)
                
                # Chạy job
                processed_image, results = current_job.run(test_image)
                
                # Hiển thị kết quả
                if 'error' not in results:
                    logging.info(f"Job '{current_job.name}' completed successfully")
                    logging.info(f"Execution time: {results.get('execution_time', 0):.2f}s")
                    
                    # Cập nhật execution time display
                    if self.executionTime:
                        self.executionTime.display(results.get('execution_time', 0))
                else:
                    logging.error(f"Job failed: {results['error']}")
                    
        except Exception as e:
            logging.error(f"Error running job: {str(e)}")
        
    def resizeEvent(self, a0):
        """Xử lý sự kiện khi cửa sổ thay đổi kích thước"""
        super().resizeEvent(a0)
        if hasattr(self, 'camera_manager') and self.camera_manager:
            self.camera_manager.handle_resize_event()
    
    def closeEvent(self, event):
        """Xử lý sự kiện đóng cửa sổ - dọn dẹp tài nguyên"""
        logger = logging.getLogger(__name__)
        try:
            logger.info("Main window closing - cleaning up resources...")
            
            # Dọn dẹp camera manager
            if hasattr(self, 'camera_manager') and self.camera_manager:
                self.camera_manager.cleanup()
                
            # Chấp nhận sự kiện đóng cửa sổ
            event.accept()
            logger.info("Main window cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during window close cleanup: {str(e)}")
            # Vẫn chấp nhận sự kiện để thoát ứng dụng
            event.accept()
