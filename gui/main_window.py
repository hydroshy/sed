from PyQt5.QtGui import QCloseEvent
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsView, QWidget, QStackedWidget, QComboBox, QPushButton, QSlider, QLineEdit, QProgressBar, QLCDNumber, QTabWidget, QListView, QTreeView, QMainWindow, QSpinBox, QDoubleSpinBox, QTableView
from PyQt5 import uic
import os
import logging
from job.job_manager import JobManager
from gui.tool_manager import ToolManager
from gui.settings_manager import SettingsManager
from gui.camera_manager import CameraManager
from gui.detect_tool_manager import DetectToolManager

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MainWindow(QMainWindow):
    def _clear_tool_config_ui(self):
        """Reset UI cấu hình tool về mặc định khi tạo mới"""
        # Xóa detection area (4 trường)
        if self.x1PositionLineEdit:
            self.x1PositionLineEdit.setText("")
        if self.y1PositionLineEdit:
            self.y1PositionLineEdit.setText("")
        if self.x2PositionLineEdit:
            self.x2PositionLineEdit.setText("")
        if self.y2PositionLineEdit:
            self.y2PositionLineEdit.setText("")
        # Xóa bảng class đã chọn
        if self.classificationTableView and hasattr(self.classificationTableView, 'model'):
            model = self.classificationTableView.model()
            if model:
                model.removeRows(0, model.rowCount())
        # Đặt combobox model về mặc định
        if self.algorithmComboBox:
            if self.algorithmComboBox.count() > 0:
                self.algorithmComboBox.setCurrentIndex(0)
        # Nếu có detect_tool_manager, xóa class đã chọn (nếu có hàm)
        if hasattr(self, 'detect_tool_manager') and hasattr(self.detect_tool_manager, 'selected_classes'):
            self.detect_tool_manager.selected_classes = []
    def _disable_all_overlay_edit_mode(self):
        """Tắt edit mode cho tất cả overlays và current_overlay nếu có camera_view"""
        if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
            camera_view = self.camera_manager.camera_view
            if hasattr(camera_view, 'overlays'):
                for overlay in camera_view.overlays.values():
                    overlay.set_edit_mode(False)
            if hasattr(camera_view, 'current_overlay') and camera_view.current_overlay:
                camera_view.current_overlay.set_edit_mode(False)
                camera_view.current_overlay = None
            camera_view.set_overlay_edit_mode(False)
    def __init__(self):
        super().__init__()
        self._editing_tool = None  # Tool đang được chỉnh sửa
        
        # Khởi tạo các biến thành viên
        self.tool_manager = ToolManager(self)
        self.settings_manager = SettingsManager(self)
        self.camera_manager = CameraManager(self)
        self.job_manager = JobManager()
        self.detect_tool_manager = DetectToolManager(self)
        
        # Load UI từ file .ui
        ui_path = os.path.join(os.path.dirname(__file__), '..', 'mainUI.ui')
        uic.loadUi(ui_path, self)
        
        # Tìm và kết nối các widget chính
        self._find_widgets()
        # Debug: Log all QComboBox objectNames after UI load
        for w in self.findChildren(QComboBox):
            logging.info(f"QComboBox found: {w.objectName()}")
        
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
        self.x1PositionLineEdit = self.findChild(QLineEdit, 'x1PositionLineEdit')
        self.y1PositionLineEdit = self.findChild(QLineEdit, 'y1PositionLineEdit')
        self.x2PositionLineEdit = self.findChild(QLineEdit, 'x2PositionLineEdit')
        self.y2PositionLineEdit = self.findChild(QLineEdit, 'y2PositionLineEdit')
        # Reset detection area fields
        if self.x1PositionLineEdit:
            self.x1PositionLineEdit.setText("")
        if self.y1PositionLineEdit:
            self.y1PositionLineEdit.setText("")
        if self.x2PositionLineEdit:
            self.x2PositionLineEdit.setText("")
        if self.y2PositionLineEdit:
            self.y2PositionLineEdit.setText("")
        self.triggerCameraMode = self.findChild(QPushButton, 'triggerCameraMode')
        self.liveCameraMode = self.findChild(QPushButton, 'liveCameraMode')
        
        # Camera settings widgets
        self.evEdit = self.findChild(QDoubleSpinBox, 'evEdit')  # Also change to QDoubleSpinBox
        self.evSlider = self.findChild(QSlider, 'evSlider')
        self.manualExposure = self.findChild(QPushButton, 'manualExposure')
        self.autoExposure = self.findChild(QPushButton, 'autoExposure')
        
        # Try to find formatCameraComboBox using different methods
        self.formatCameraComboBox = self.findChild(QComboBox, 'formatCameraComboBox')
        if not self.formatCameraComboBox:
            # Alternative method: search through all combo boxes
            all_combos = self.findChildren(QComboBox)
            for combo in all_combos:
                if combo.objectName() == 'formatCameraComboBox':
                    self.formatCameraComboBox = combo
                    break
        
        print(f"DEBUG: formatCameraComboBox found: {self.formatCameraComboBox is not None}")
        if self.formatCameraComboBox:
            print(f"DEBUG: formatCameraComboBox type: {type(self.formatCameraComboBox)}")
        else:
            print("DEBUG: formatCameraComboBox is None - searching for all ComboBoxes")
            all_combos = self.findChildren(QComboBox)
            for combo in all_combos:
                print(f"DEBUG: Found combo: {combo.objectName()}")
        
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
            
        # Tìm các widget Detect Tool settings (không phụ thuộc vào detectSettingFrame)
        self.thresholdSlider = self.findChild(QSlider, 'thresholdSlider')
        self.thresholdSpinBox = self.findChild(QSlider, 'thresholdSpinBox')  # Note: This might need to be changed to QSpinBox
        self.minConfidenceEdit = self.findChild(QLineEdit, 'minConfidenceEdit')  # Note: This might need to be changed to QDoubleSpinBox
        
        # Model and classification widgets
        self.algorithmComboBox = self.findChild(QComboBox, 'algorithmComboBox')
        self.classificationComboBox = self.findChild(QComboBox, 'classificationComboBox')
        self.addClassificationButton = self.findChild(QPushButton, 'addClassificationButton')
        self.removeClassificationButton = self.findChild(QPushButton, 'removeClassificationButton')
        self.classificationScrollArea = self.findChild(QWidget, 'classificationScrollArea')  # QScrollArea or QListWidget
        self.classificationTableView = self.findChild(QTableView, 'classificationTableView')
        
        # Debug logging for widget finding
        logging.info(f"detectSettingFrame found: {self.detectSettingFrame is not None}")
        logging.info(f"Found algorithmComboBox: {self.algorithmComboBox is not None}")
        logging.info(f"Found classificationComboBox: {self.classificationComboBox is not None}")
        logging.info(f"Found addClassificationButton: {self.addClassificationButton is not None}")
        logging.info(f"Found removeClassificationButton: {self.removeClassificationButton is not None}")
        logging.info(f"Found classificationScrollArea: {self.classificationScrollArea is not None}")
        
        # Log actual widget addresses if found
        if self.algorithmComboBox:
            logging.info(f"algorithmComboBox address: {hex(id(self.algorithmComboBox))}")
        if self.classificationComboBox:
            logging.info(f"classificationComboBox address: {hex(id(self.classificationComboBox))}")
        
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
        
        # Setup DetectToolManager
        if hasattr(self, 'detect_tool_manager'):
            logging.info("Setting up DetectToolManager...")
            logging.info(f"algorithmComboBox before setup: {self.algorithmComboBox}")
            logging.info(f"classificationComboBox before setup: {self.classificationComboBox}")
            
            self.detect_tool_manager.setup_ui_components(
                algorithm_combo=self.algorithmComboBox,
                classification_combo=self.classificationComboBox,
                add_btn=self.addClassificationButton,
                remove_btn=self.removeClassificationButton,
                scroll_area=self.classificationScrollArea,
                table_view=self.classificationTableView
            )
        else:
            logging.error("DetectToolManager not initialized!")
        
        # Enable UI after setup is complete
        self.camera_manager.set_ui_enabled(True)
        
        # Load available camera formats
        self._load_camera_formats()
        
    def refresh_detect_tool_manager(self):
        """Refresh DetectToolManager connections when switching to detect page"""
        if hasattr(self, 'detect_tool_manager'):
            logging.info("Refreshing DetectToolManager connections...")
            self.detect_tool_manager._force_refresh_connections()
            
            # Test signal by logging current state
            if self.algorithmComboBox:
                logging.info(f"Current algorithm combo selection: {self.algorithmComboBox.currentText()}")
                logging.info(f"Algorithm combo item count: {self.algorithmComboBox.count()}")
            
            if self.classificationComboBox:
                logging.info(f"Current classification combo count: {self.classificationComboBox.count()}")
                for i in range(self.classificationComboBox.count()):
                    logging.info(f"  Class {i}: {self.classificationComboBox.itemText(i)}")
        else:
            logging.warning("DetectToolManager not available for refresh")
        
    def _connect_signals(self):
        # Job run button
        if self.runJob:
            self.runJob.clicked.connect(self.run_current_job)
            logging.info("runJob button connected to run_current_job.")
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
        # Khi add tool mới, không truyền detection_area từ tool trước đó
        # pending_detection_area chỉ dùng cho preview/crop khi cần
        self.tool_manager._pending_detection_area = None
        if tool_name:
            self.settings_manager.switch_to_tool_setting_page(tool_name)
            self._clear_tool_config_ui()
    
    def _on_edit_tool(self):
        """Xử lý khi người dùng nhấn nút Edit Tool"""
        # Get selected tool from tool view
        selected_tool = self.tool_manager.get_selected_tool()
        if selected_tool:
            self._editing_tool = selected_tool
            self.tool_manager._pending_tool = None
            detection_area = None
            if hasattr(selected_tool, 'config') and hasattr(selected_tool.config, 'get'):
                detection_area = selected_tool.config.get('detection_area')
            self.tool_manager._pending_detection_area = detection_area
            if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                overlay = self.camera_manager.camera_view.edit_tool_overlay(selected_tool.tool_id)
                if overlay:
                    print(f"DEBUG: Editing tool #{selected_tool.tool_id}")
                else:
                    print(f"DEBUG: Tool #{selected_tool.tool_id} overlay not found")
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
            self._apply_camera_settings()
            return
        
        # Handle detection settings page
        if current_page == "detection":
            # Nếu đang ở chế độ chỉnh sửa tool (edit), chỉ cập nhật config tool đó
            if self._editing_tool is not None:
                print(f"DEBUG: Updating config for editing tool: {self._editing_tool.display_name}")
                detection_area = self._collect_detection_area()
                if self._editing_tool.name == "Detect Tool" and hasattr(self, 'detect_tool_manager'):
                    new_config = self.detect_tool_manager.get_tool_config()
                    # Luôn lưu detection_area từ UI nếu có
                    if detection_area:
                        new_config['detection_area'] = detection_area
                    self._editing_tool.config = new_config
                    print(f"DEBUG: Updated DetectTool config: {self._editing_tool.config}")
                else:
                    # For other tools, update config with detection_area if present
                    if hasattr(self._editing_tool, 'config') and detection_area:
                        self._editing_tool.config['detection_area'] = detection_area
                self._editing_tool = None
                if hasattr(self.tool_manager, '_update_job_view'):
                    self.tool_manager._update_job_view()
                self.settings_manager.return_to_camera_setting_page()
                # --- Always robustly disable edit mode for all overlays and current_overlay ---
                if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                    camera_view = self.camera_manager.camera_view
                    # Tắt edit mode cho tất cả overlays
                    if hasattr(camera_view, 'overlays'):
                        for overlay in camera_view.overlays.values():
                            overlay.set_edit_mode(False)
                            print(f"DEBUG: Overlay #{overlay.tool_id} edit_mode after apply: {overlay.edit_mode}")
                    # Tắt edit mode cho current_overlay nếu còn tồn tại
                    if hasattr(camera_view, 'current_overlay'):
                        if camera_view.current_overlay:
                            camera_view.current_overlay.set_edit_mode(False)
                            print(f"DEBUG: Current overlay edit_mode after apply: {camera_view.current_overlay.edit_mode}")
                        camera_view.current_overlay = None
                    camera_view.set_overlay_edit_mode(False)
                print("DEBUG: All overlays and current_overlay are now not editable after apply.")
                return
            # Nếu không phải chế độ edit, xử lý như cũ (thêm mới tool)
            logging.debug(f"Detection page - tool_manager has _pending_tool: {hasattr(self.tool_manager, '_pending_tool')}")
            if hasattr(self.tool_manager, '_pending_tool'):
                logging.debug(f"_pending_tool value: {getattr(self.tool_manager, '_pending_tool', 'None')}")
            if hasattr(self.tool_manager, '_pending_tool') and self.tool_manager._pending_tool == "Detect Tool":
                logging.info("Applying Detect Tool configuration...")
                # --- Always save detection_area from UI to config before applying ---
                detection_area = self._collect_detection_area()
                config = self.detect_tool_manager.get_tool_config() if hasattr(self, 'detect_tool_manager') else {}
                if detection_area:
                    config['detection_area'] = detection_area
                self.tool_manager.set_tool_config(config)
                success = self.detect_tool_manager.apply_detect_tool_to_job()
                if hasattr(self.tool_manager, '_update_job_view'):
                    self.tool_manager._update_job_view()
                self.settings_manager.return_to_camera_setting_page()
                # --- Tắt edit mode cho overlays như cancelSetting ---
                if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                    camera_view = self.camera_manager.camera_view
                    if hasattr(camera_view, 'overlays'):
                        for overlay in camera_view.overlays.values():
                            overlay.set_edit_mode(False)
                    if hasattr(camera_view, 'current_overlay'):
                        camera_view.current_overlay = None
                    camera_view.set_overlay_edit_mode(False)
                    print("DEBUG: Disabled overlay edit mode on apply (after add tool)")
                if success:
                    logging.info("Detect Tool applied to job successfully")
                else:
                    logging.error("Failed to apply Detect Tool to job")
                return
            else:
                logging.debug("Detect Tool not selected or _pending_tool not set correctly")
            
            # Đoạn này đã xử lý cập nhật tool ở trên với self._editing_tool, không cần lặp lại với editing_tool
            # Nếu không phải chế độ edit, xử lý như cũ (thêm mới tool)
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
        # --- Tắt edit mode cho overlays như cancelSetting ---
        if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
            camera_view = self.camera_manager.camera_view
            # Tắt edit mode cho tất cả overlays
            if hasattr(camera_view, 'overlays'):
                for overlay in camera_view.overlays.values():
                    overlay.set_edit_mode(False)
            # Đặt current_overlay = None
            if hasattr(camera_view, 'current_overlay'):
                camera_view.current_overlay = None
            camera_view.set_overlay_edit_mode(False)
            print("DEBUG: Disabled overlay edit mode on apply")
        print("DEBUG: Settings applied and synchronized successfully")
    
    def _on_cancel_setting(self):
        """Xử lý khi người dùng nhấn nút Cancel trong trang cài đặt"""
        # Disable overlay edit mode when canceling
        if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
            camera_view = self.camera_manager.camera_view
            # Tắt edit mode cho tất cả overlays
            if hasattr(camera_view, 'overlays'):
                for overlay in camera_view.overlays.values():
                    overlay.set_edit_mode(False)
            # Đặt current_overlay = None
            if hasattr(camera_view, 'current_overlay'):
                camera_view.current_overlay = None
            camera_view.set_overlay_edit_mode(False)
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
            # Always reset UI before loading tool config
            self._clear_tool_config_ui()
            # Get config as dict
            if hasattr(tool.config, 'to_dict'):
                config = tool.config.to_dict()
            else:
                config = tool.config
            print(f"DEBUG: Loading tool config: {config}")

            # Handle tool-specific configuration loading
            if tool.name == "Detect Tool" and hasattr(self, 'detect_tool_manager'):
                print(f"DEBUG: Loading DetectTool configuration via DetectToolManager")
                self.detect_tool_manager.load_tool_config(config)

            # --- Load detection area (x1, y1, x2, y2) robustly ---
            area = None
            if 'detection_area' in config and config['detection_area'] is not None:
                area = config['detection_area']
            elif 'detection_region' in config and config['detection_region'] is not None:
                area = config['detection_region']

            # If area is still None, try to get from overlay (if exists)
            if (not area or not (isinstance(area, (list, tuple)) and len(area) == 4)) and hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                camera_view = self.camera_manager.camera_view
                overlay = camera_view.overlays.get(tool.tool_id) if hasattr(camera_view, 'overlays') else None
                if overlay and hasattr(overlay, 'get_area_coords'):
                    area = overlay.get_area_coords()
                    # Update config so next time it is available
                    tool.config['detection_area'] = area
                    print(f"DEBUG: Loaded detection_area from overlay: {area}")

            if area and isinstance(area, (list, tuple)) and len(area) == 4:
                x1, y1, x2, y2 = area
                if self.x1PositionLineEdit:
                    self.x1PositionLineEdit.setText(str(x1))
                if self.y1PositionLineEdit:
                    self.y1PositionLineEdit.setText(str(y1))
                if self.x2PositionLineEdit:
                    self.x2PositionLineEdit.setText(str(x2))
                if self.y2PositionLineEdit:
                    self.y2PositionLineEdit.setText(str(y2))
                # Add or update detection area overlay for editing (preserve other overlays)
                if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                    camera_view = self.camera_manager.camera_view
                    if tool.tool_id in camera_view.overlays:
                        overlay = camera_view.overlays[tool.tool_id]
                        overlay.update_from_coords(x1, y1, x2, y2)
                        overlay.set_edit_mode(True)
                        camera_view.current_overlay = overlay
                        print(f"DEBUG: Updated existing overlay for tool #{tool.tool_id}")
                    else:
                        overlay = camera_view.add_tool_overlay(x1, y1, x2, y2, tool.tool_id)
                        overlay.set_edit_mode(True)
                        camera_view.current_overlay = overlay
                        print(f"DEBUG: Added new overlay for tool #{tool.tool_id}")
                    print(f"DEBUG: Loaded detection area for editing: ({x1}, {y1}) to ({x2}, {y2})")
                    print("DEBUG: Enabled overlay edit mode for tool editing")
            else:
                # If no area, clear all fields
                if self.x1PositionLineEdit:
                    self.x1PositionLineEdit.setText("")
                if self.y1PositionLineEdit:
                    self.y1PositionLineEdit.setText("")
                if self.x2PositionLineEdit:
                    self.x2PositionLineEdit.setText("")
                if self.y2PositionLineEdit:
                    self.y2PositionLineEdit.setText("")

            # Load other settings (threshold, confidence, etc.)
            if 'threshold' in config and hasattr(self, 'thresholdSlider'):
                self.thresholdSlider.setValue(config['threshold'])

            if 'min_confidence' in config and hasattr(self, 'minConfidenceEdit'):
                self.minConfidenceEdit.setValue(config['min_confidence'])

        except Exception as e:
            print(f"DEBUG: Error loading tool config: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_draw_area_clicked(self):
        """Xử lý khi người dùng nhấn nút Draw Area"""
        print("DEBUG: Draw Area button clicked")
        
        # Chỉ xóa overlay tạm thời (pending), giữ lại overlay của các tool đã add vào job
        if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
            # Nếu đang có overlay tạm thời (current_overlay) thì xóa, không xóa overlays của tool đã add
            if self.camera_manager.camera_view.current_overlay:
                overlay = self.camera_manager.camera_view.current_overlay
                if overlay.tool_id is None or overlay.tool_id not in self.camera_manager.camera_view.overlays:
                    # Chỉ xóa overlay tạm thời chưa gán tool_id
                    self.camera_manager.camera_view.scene.removeItem(overlay)
                    self.camera_manager.camera_view.current_overlay = None
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

        # Update x1, y1, x2, y2 LineEdits with drawn area coordinates
        if self.x1PositionLineEdit:
            self.x1PositionLineEdit.setText(str(int(x1)))
        if self.y1PositionLineEdit:
            self.y1PositionLineEdit.setText(str(int(y1)))
        if self.x2PositionLineEdit:
            self.x2PositionLineEdit.setText(str(int(x2)))
        if self.y2PositionLineEdit:
            self.y2PositionLineEdit.setText(str(int(y2)))

        # Reset button state
        if self.drawAreaButton:
            self.drawAreaButton.setText("Draw area")
            self.drawAreaButton.setEnabled(True)

        # Disable drawing mode but keep overlay editable in pending state
        if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
            self.camera_manager.camera_view.set_draw_mode(False)
            # Keep overlay editable until applied/canceled
            self.camera_manager.camera_view.set_overlay_edit_mode(True)

        print(f"DEBUG: Updated detection area fields: x1={int(x1)}, y1={int(y1)}, x2={int(x2)}, y2={int(y2)}")
    
    def _on_area_changed(self, x1, y1, x2, y2):
        """Xử lý khi area thay đổi (move/resize)"""
        print(f"DEBUG: Area changed: ({x1}, {y1}) to ({x2}, {y2})")

        # Update x1, y1, x2, y2 LineEdits with changed area coordinates
        if self.x1PositionLineEdit:
            self.x1PositionLineEdit.setText(str(int(x1)))
        if self.y1PositionLineEdit:
            self.y1PositionLineEdit.setText(str(int(y1)))
        if self.x2PositionLineEdit:
            self.x2PositionLineEdit.setText(str(int(x2)))
        if self.y2PositionLineEdit:
            self.y2PositionLineEdit.setText(str(int(y2)))

        print(f"DEBUG: Updated detection area fields from area change: x1={int(x1)}, y1={int(y1)}, x2={int(x2)}, y2={int(y2)}")
    
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
            if self.x1PositionLineEdit and self.y1PositionLineEdit and self.x2PositionLineEdit and self.y2PositionLineEdit:
                x1_text = self.x1PositionLineEdit.text().strip()
                y1_text = self.y1PositionLineEdit.text().strip()
                x2_text = self.x2PositionLineEdit.text().strip()
                y2_text = self.y2PositionLineEdit.text().strip()
                if x1_text and y1_text and x2_text and y2_text:
                    x1 = int(x1_text)
                    y1 = int(y1_text)
                    x2 = int(x2_text)
                    y2 = int(y2_text)
                    return (x1, y1, x2, y2)
        except ValueError as e:
            print(f"DEBUG: Error parsing coordinates: {e}")
        return None
    
    def save_current_job(self):
        self._disable_all_overlay_edit_mode()
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
        self._disable_all_overlay_edit_mode()
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
        self._disable_all_overlay_edit_mode()
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
        self._disable_all_overlay_edit_mode()
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
        
    def _apply_camera_settings(self):
        """Apply camera settings including format"""
        print("DEBUG: Applying camera settings...")
        
        # Apply camera format if formatCameraComboBox exists and has selection
        if self.formatCameraComboBox and self.formatCameraComboBox.currentText():
            selected_format = self.formatCameraComboBox.currentText()
            print(f"DEBUG: Applying camera format: {selected_format}")
            
            # Get camera stream instance
            if hasattr(self.camera_manager, 'camera_stream') and self.camera_manager.camera_stream:
                camera_stream = self.camera_manager.camera_stream
                
                # Apply the new format
                try:
                    camera_stream.set_format(selected_format)
                    print(f"DEBUG: Successfully applied camera format: {selected_format}")
                except Exception as e:
                    print(f"DEBUG: Failed to apply camera format {selected_format}: {e}")
            else:
                print("DEBUG: Camera stream not available for format change")
        
        print("DEBUG: Camera settings applied successfully")
    
    def _load_camera_formats(self):
        """Load available camera formats into formatCameraComboBox"""
        print("DEBUG: _load_camera_formats called")
        
        # Always try to find formatCameraComboBox fresh
        combo_widget = None
        
        # First try findChild
        combo_widget = self.findChild(QComboBox, 'formatCameraComboBox')
        if combo_widget:
            print(f"DEBUG: Found formatCameraComboBox via findChild: {combo_widget}")
        else:
            print("DEBUG: findChild failed, trying findChildren...")
            # Alternative method: search through all combo boxes
            all_combos = self.findChildren(QComboBox)
            for combo in all_combos:
                if combo.objectName() == 'formatCameraComboBox':
                    combo_widget = combo
                    print(f"DEBUG: Found formatCameraComboBox via findChildren: {combo_widget}")
                    print(f"DEBUG: Widget valid: {combo_widget is not None}")
                    print(f"DEBUG: Widget type: {type(combo_widget)}")
                    print(f"DEBUG: Widget objectName: {combo_widget.objectName()}")
                    break
        
        print(f"DEBUG: Final combo_widget value: {combo_widget}")
        print(f"DEBUG: combo_widget is None: {combo_widget is None}")
        
        if combo_widget is None:
            print("DEBUG: formatCameraComboBox not found anywhere")
            return
            
        # Assign to self for future use
        self.formatCameraComboBox = combo_widget
        print("DEBUG: formatCameraComboBox assigned, proceeding with format loading")
        
        # Clear existing items
        combo_widget.clear()
        
        # Get camera stream instance
        if hasattr(self.camera_manager, 'camera_stream') and self.camera_manager.camera_stream:
            camera_stream = self.camera_manager.camera_stream
            print("DEBUG: Got camera stream instance")
            
            # Get available formats from camera
            available_formats = camera_stream.get_available_formats()
            print(f"DEBUG: Available formats: {available_formats}")
            
            if available_formats:
                # Add formats to combo box
                for fmt in available_formats:
                    combo_widget.addItem(fmt)
                    print(f"DEBUG: Added format: {fmt}")
            else:
                # Add common formats as fallback
                common_formats = ["BGR888", "RGB888", "YUV420", "MJPEG"]
                for fmt in common_formats:
                    combo_widget.addItem(fmt)
                    print(f"DEBUG: Added fallback format: {fmt}")
                    
            # Set current format as selected
            current_format = getattr(camera_stream, 'current_format', 'BGR888')
            index = combo_widget.findText(current_format)
            if index >= 0:
                combo_widget.setCurrentIndex(index)
                print(f"DEBUG: Set current format to: {current_format}")
            
            print(f"DEBUG: ComboBox now has {combo_widget.count()} items")
        else:
            print("DEBUG: Camera stream not available, adding fallback formats")
            # Add fallback formats when camera not available
            common_formats = ["BGR888", "RGB888", "YUV420", "MJPEG"]
            for fmt in common_formats:
                combo_widget.addItem(fmt)
                print(f"DEBUG: Added fallback format: {fmt}")
            print(f"DEBUG: ComboBox now has {combo_widget.count()} fallback items")
            for fmt in common_formats:
                self.formatCameraComboBox.addItem(fmt)
                print(f"DEBUG: Added fallback format: {fmt}")
    
    def reload_camera_formats(self):
        """Public method to reload camera formats - can be called by camera_manager"""
        self._load_camera_formats()
    
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
