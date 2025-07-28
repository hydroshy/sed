from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsView, QWidget, QStackedWidget, QComboBox, QPushButton, QSlider, QLineEdit, QProgressBar, QLCDNumber, QTabWidget, QListView, QTreeView, QMainWindow
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
        self.exposureEdit = self.findChild(QLineEdit, 'exposureEdit')
        self.exposureSlider = self.findChild(QSlider, 'exposureSlider')
        self.gainEdit = self.findChild(QLineEdit, 'gainEdit')
        self.gainSlider = self.findChild(QSlider, 'gainSlider')
        self.evEdit = self.findChild(QLineEdit, 'evEdit')
        self.evSlider = self.findChild(QSlider, 'evSlider')
        self.manualExposure = self.findChild(QPushButton, 'manualExposure')
        self.autoExposure = self.findChild(QPushButton, 'autoExposure')
        
        # Job management widgets
        self.paletteTab = self.findChild(QTabWidget, 'paletteTab')
        self.jobTab = self.findChild(QTreeView, 'jobTab')
        self.jobView = self.findChild(QListView, 'jobView')
        self.removeJob = self.findChild(QPushButton, 'removeJob')
        self.editJob = self.findChild(QPushButton, 'editJob')
        self.addJob = self.findChild(QPushButton, 'addJob')
        self.loadJob = self.findChild(QPushButton, 'loadJob')
        self.saveJob = self.findChild(QPushButton, 'saveJob')
        self.runJob = self.findChild(QPushButton, 'runJob')
        
        # Tool management widgets
        self.toolView = self.findChild(QListView, 'toolView')
        self.addTool = self.findChild(QPushButton, 'addTool')
        self.cancleTool = self.findChild(QPushButton, 'cancleTool')
        self.toolComboBox = self.findChild(QComboBox, 'toolComboBox')
        
        # Settings widgets
        self.settingStackedWidget = self.findChild(QStackedWidget, 'settingStackedWidget')
        self.cameraSettingPage = self.findChild(QWidget, 'cameraSettingPage')
        self.detectSettingPage = self.findChild(QWidget, 'detectSettingPage')
        self.cameraSettingFrame = self.findChild(QWidget, 'cameraSettingFrame')
        self.detectSettingFrame = self.findChild(QWidget, 'detectSettingFrame')
        self.applySetting = self.findChild(QPushButton, 'applySetting')
        self.cancleSetting = self.findChild(QPushButton, 'cancleSetting')
        
        # Thiết lập validators cho LineEdit
        if self.exposureEdit:
            self.exposureEdit.setValidator(QDoubleValidator(0.03, 10000, 2, self))
        if self.gainEdit:
            self.gainEdit.setValidator(QIntValidator(0, 100, self))
        if self.evEdit:
            self.evEdit.setValidator(QIntValidator(-1, 1, self))
            
        # Thiết lập range cho các slider
        if self.exposureSlider:
            self.exposureSlider.setMinimum(1)  # 1 = 0.03ms
            self.exposureSlider.setMaximum(10000*100)  # 10000ms
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
            self.exposureSlider,
            self.exposureEdit,
            self.gainSlider,
            self.gainEdit,
            self.evSlider,
            self.evEdit,
            self.focusBar,
            self.fpsNum
        )
        
    def _connect_signals(self):
        """Kết nối các signal với các slot tương ứng"""
        # Tool management connections
        if self.addTool:
            self.addTool.clicked.connect(self._on_add_tool)
            logging.info("addTool button connected to _on_add_tool.")
        
        if self.cancleTool:
            self.cancleTool.clicked.connect(self.tool_manager.on_remove_tool_from_job)
            
        if self.editJob:
            self.editJob.clicked.connect(self.tool_manager.on_edit_tool_in_job)
            
        if self.removeJob:
            self.removeJob.clicked.connect(self.tool_manager.on_remove_tool_from_job)
            
        # Settings connections
        if self.applySetting:
            self.applySetting.clicked.connect(self._on_apply_setting)
            
        if self.cancleSetting:
            self.cancleSetting.clicked.connect(self._on_cancel_setting)
            
        # Camera connections
        if self.liveCamera:
            self.liveCamera.setCheckable(True)
            self.liveCamera.clicked.connect(self.camera_manager.toggle_live_camera)
            
        if self.triggerCamera:
            self.triggerCamera.clicked.connect(self.camera_manager.trigger_capture)
            
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
            
        if self.runJob:
            self.runJob.clicked.connect(self.run_current_job)
    
    def _on_add_tool(self):
        """Xử lý khi người dùng nhấn nút Add Tool"""
        # Lấy công cụ được chọn
        tool_name = self.tool_manager.on_add_tool()
        if tool_name:
            # Chuyển đến trang cài đặt tương ứng
            self.settings_manager.switch_to_tool_setting_page(tool_name)
    
    def _on_apply_setting(self):
        """Xử lý khi người dùng nhấn nút Apply trong trang cài đặt"""
        # Thu thập cấu hình từ UI
        if hasattr(self, 'thresholdSlider') and hasattr(self, 'minConfidenceEdit'):
            ui_widgets = {
                'threshold_slider': self.thresholdSlider,
                'min_confidence_edit': self.minConfidenceEdit
            }
            
            # Lưu cấu hình vào tool_manager
            if self.tool_manager._pending_tool:
                config = self.settings_manager.collect_tool_config(
                    self.tool_manager._pending_tool,
                    ui_widgets
                )
                self.tool_manager.set_tool_config(config)
        
        # Áp dụng cài đặt
        self.tool_manager.on_apply_setting()
        
        # Quay lại trang cài đặt camera
        self.settings_manager.return_to_camera_setting_page()
    
    def _on_cancel_setting(self):
        """Xử lý khi người dùng nhấn nút Cancel trong trang cài đặt"""
        # Hủy bỏ thao tác thêm tool
        self.tool_manager.on_cancel_setting()
        
        # Quay lại trang cài đặt camera
        self.settings_manager.return_to_camera_setting_page()
        
    def run_current_job(self):
        """Chạy job hiện tại"""
        # TODO: Implement this
        logging.info("Running current job")
        
    def resizeEvent(self, event):
        """Xử lý sự kiện khi cửa sổ thay đổi kích thước"""
        super().resizeEvent(event)
        self.camera_manager.handle_resize_event()
