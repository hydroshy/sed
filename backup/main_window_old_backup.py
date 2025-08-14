from camera.camera_stream import CameraStream
from PyQt5.QtGui import QImage, QPixmap, QIntValidator, QDoubleValidator
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsScene,QGraphicsPixmapItem,QWidget,QStackedWidget,QComboBox,QGraphicsView, QPushButton, QSlider, QLineEdit, QProgressBar, QLCDNumber, QTabWidget, QListView, QTreeView
import numpy as np
import cv2
from PyQt5.QtWidgets import QMainWindow, QPushButton
from PyQt5 import uic
import os
from job.job_manager import JobManager, Job
from tools.base_tool import BaseTool
from PyQt5.QtCore import QStringListModel
from detection.ocr_tool import OcrTool
from PyQt5.QtGui import QPen, QColor, QPainter, QFont
import logging
from gui.camera_view import CameraView

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MainWindow(QMainWindow):
    # ==== CAMERA PARAMETER UI LOGIC ====
    def setup_camera_param_signals(self):
        # Exposure
        self.exposureSlider.valueChanged.connect(self.on_exposure_slider_changed)
        self.exposureEdit.editingFinished.connect(self.on_exposure_edit_changed)
        # Gain
        self.gainSlider.valueChanged.connect(self.on_gain_slider_changed)
        self.gainEdit.editingFinished.connect(self.on_gain_edit_changed)
        # EV
        self.evSlider.valueChanged.connect(self.on_ev_slider_changed)
        self.evEdit.editingFinished.connect(self.on_ev_edit_changed)

    def set_exposure(self, value):
        self.exposureEdit.setText(str(value))
        self.exposureSlider.setValue(int(value))
        if hasattr(self.camera_stream, 'set_exposure'):
            self.camera_stream.set_exposure(value)

    def set_gain(self, value):
        self.gainEdit.setText(str(value))
        self.gainSlider.setValue(int(value))
        if hasattr(self.camera_stream, 'set_gain'):
            self.camera_stream.set_gain(value)

    def set_ev(self, value):
        self.evEdit.setText(str(value))
        self.evSlider.setValue(int(value))
        if hasattr(self.camera_stream, 'set_ev'):
            self.camera_stream.set_ev(value)

    def on_exposure_slider_changed(self, value):
        self.exposureEdit.setText(str(value))
        if hasattr(self.camera_stream, 'set_exposure'):
            self.camera_stream.set_exposure(value)

    def on_exposure_edit_changed(self):
        try:
            value = int(self.exposureEdit.text())
            self.exposureSlider.setValue(value)
            if hasattr(self.camera_stream, 'set_exposure'):
                self.camera_stream.set_exposure(value)
        except ValueError:
            pass

    def on_gain_slider_changed(self, value):
        self.gainEdit.setText(str(value))
        if hasattr(self.camera_stream, 'set_gain'):
            self.camera_stream.set_gain(value)

    def on_gain_edit_changed(self):
        try:
            value = int(self.gainEdit.text())
            self.gainSlider.setValue(value)
            if hasattr(self.camera_stream, 'set_gain'):
                self.camera_stream.set_gain(value)
        except ValueError:
            pass

    def on_ev_slider_changed(self, value):
        self.evEdit.setText(str(value))
        if hasattr(self.camera_stream, 'set_ev'):
            self.camera_stream.set_ev(value)

    def on_ev_edit_changed(self):
        try:
            value = int(self.evEdit.text())
            self.evSlider.setValue(value)
            if hasattr(self.camera_stream, 'set_ev'):
                self.camera_stream.set_ev(value)
        except ValueError:
            pass

    def update_camera_params_from_camera(self):
        # Lấy giá trị thực tế từ camera nếu có API
        if hasattr(self.camera_stream, 'get_exposure'):
            exposure = self.camera_stream.get_exposure()
            self.set_exposure(exposure)
        if hasattr(self.camera_stream, 'get_gain'):
            gain = self.camera_stream.get_gain()
            self.set_gain(gain)
        if hasattr(self.camera_stream, 'get_ev'):
            ev = self.camera_stream.get_ev()
            self.set_ev(ev)

    def __init__(self):
        # Initialize FPS counter variables early to avoid AttributeError
        self._fps_count = 0
        self._fps_last_update = 0
        self._fps_value = 0
        super().__init__()
        ui_path = os.path.join(os.path.dirname(__file__), '..', 'mainUI.ui')
        uic.loadUi(ui_path, self)

        # Kết nối các widget chính
        self.cameraView = self.findChild(QGraphicsView, 'cameraView')
        self.liveCamera = self.findChild(QPushButton, 'liveCamera')
        self.triggerCamera = self.findChild(QPushButton, 'triggerCamera')
        self.zoomIn = self.findChild(QPushButton, 'zoomIn')
        self.zoomOut = self.findChild(QPushButton, 'zoomOut')
        self.focusBar = self.findChild(QProgressBar, 'focusBar')
        self.executionTime = self.findChild(QLCDNumber, 'executionTime')
        self.fpsNum = self.findChild(QLCDNumber, 'fpsNum')
        self.runJob = self.findChild(QPushButton, 'runJob')
        self.paletteTab = self.findChild(QTabWidget, 'paletteTab')
        self.jobTab = self.findChild(QTreeView, 'jobTab')
        self.jobView = self.findChild(QTreeView, 'jobView')
        self.removeJob = self.findChild(QPushButton, 'removeJob')
        self.editJob = self.findChild(QPushButton, 'editJob')
        self.addJob = self.findChild(QPushButton, 'addJob')
        self.loadJob = self.findChild(QPushButton, 'loadJob')
        self.saveJob = self.findChild(QPushButton, 'saveJob')
        self.toolView = self.findChild(QListView, 'toolView')
        self.addTool = self.findChild(QPushButton, 'addTool')
        self.cancleTool = self.findChild(QPushButton, 'cancleTool')
        self.toolComboBox = self.findChild(QComboBox, 'toolComboBox')
        
        # Tạo StackedWidget và các trang cài đặt tool vì chúng không có trong file UI
        self._create_stacked_widget_and_pages()
        
        self.removeJob = self.findChild(QPushButton, 'removeJob')
        self.editJob = self.findChild(QPushButton, 'editJob')
        self.exposureEdit = self.findChild(QLineEdit, 'exposureEdit')
        self.exposureSlider = self.findChild(QSlider, 'exposureSlider')
        self.gainEdit = self.findChild(QLineEdit, 'gainEdit')
        self.gainSlider = self.findChild(QSlider, 'gainSlider')
        self.evEdit = self.findChild(QLineEdit, 'evEdit')
        self.evSlider = self.findChild(QSlider, 'evSlider')
        # Thêm validator cho các QLineEdit
        self.exposureEdit.setValidator(QDoubleValidator(0.03, 10000, 2, self))  # ms, cho phép 0.03-10000 ms
        self.gainEdit.setValidator(QIntValidator(0, 100, self))        # gain, cho phép 0-100
        self.evEdit.setValidator(QIntValidator(-1, 1, self))           # EV, chỉ cho phép -1, 0, 1
        # Đặt lại range cho các slider
        self.exposureSlider.setMinimum(1)  # 1 = 0.03ms, scale slider to ms*100
        self.exposureSlider.setMaximum(10000*100)  # 10000ms
        self.gainSlider.setMinimum(0)
        self.gainSlider.setMaximum(100)
        self.evSlider.setMinimum(-1)
        self.evSlider.setMaximum(1)
        
        # Don't redefine these buttons as they're already set up in _create_stacked_widget_and_pages
        # self.applySetting = self.findChild(QPushButton, 'applySetting')
        # self.cancleSetting = self.findChild(QPushButton, 'cancleSetting')
        
        self.triggerCameraMode = self.findChild(QPushButton, 'triggerCameraMode')
        self.liveCameraMode = self.findChild(QPushButton, 'liveCameraMode')
        self.rotateLeft = self.findChild(QPushButton, 'rotateLeft')
        self.rotateRight = self.findChild(QPushButton, 'rotateRight')
        self.manualExposure = self.findChild(QPushButton, 'manualExposure')
        self.autoExposure = self.findChild(QPushButton, 'autoExposure')
        self._is_auto_exposure = True  # Mặc định auto
        if self.manualExposure:
            self.manualExposure.clicked.connect(self.set_manual_exposure_mode)
        if self.autoExposure:
            self.autoExposure.clicked.connect(self.set_auto_exposure_mode)

        # Khởi tạo camera stream
        self.camera_stream = CameraStream()

        # Khởi tạo camera view
        self.camera_view = CameraView(self.cameraView)
        self.camera_stream.frame_ready.connect(self.camera_view.display_frame)
        self.camera_view.focus_calculated.connect(self.update_focus_value)
        self.camera_view.fps_updated.connect(self.update_fps_display)
        
        # Bật hiển thị FPS
        self.camera_view.toggle_fps_display(True)
        
        # Khởi tạo mặc định auto exposure sau khi đã có camera_stream
        self.set_auto_exposure_mode()

        # Kết nối nút
        # Kết nối signal cho các tham số camera
        self.setup_camera_param_signals()
        self.liveCamera.setCheckable(True)
        self.liveCamera.clicked.connect(self.toggle_live_camera)
        self.triggerCamera.clicked.connect(self.camera_stream.trigger_capture)
        self.zoomIn.clicked.connect(self.camera_view.zoom_in)
        self.zoomOut.clicked.connect(self.camera_view.zoom_out)
        self.liveCamera.setEnabled(True)
        self.triggerCamera.setEnabled(True)
        self.zoomIn.setEnabled(True)
        self.zoomOut.setEnabled(True)
        if self.rotateLeft:
            self.rotateLeft.clicked.connect(self.camera_view.rotate_left)
            self.rotateLeft.setEnabled(True)
        if self.rotateRight:
            self.rotateRight.clicked.connect(self.camera_view.rotate_right)
            self.rotateRight.setEnabled(True)

        # Ensure addTool button is connected to _on_add_tool
        if self.addTool:
            self.addTool.clicked.connect(self._on_add_tool)
            logging.info("addTool button connected to _on_add_tool.")

        # Initialize job_manager
        self.job_manager = JobManager()
        logging.info("JobManager initialized.")
        
        # Set up the tool and job views
        self._setup_tool_and_job_views()
        logging.info("Tool and job views setup completed.")

    def _create_stacked_widget_and_pages(self):
        """Kết nối các widget từ giao diện UI có sẵn"""
        from PyQt5.QtWidgets import QSpinBox, QDoubleSpinBox
        
        logging.info("_create_stacked_widget_and_pages: Starting to find UI widgets")
        
        # Tìm các widget đã được tạo trong file UI
        self.settingStackedWidget = self.findChild(QStackedWidget, 'settingStackedWidget')
        logging.info(f"settingStackedWidget found: {self.settingStackedWidget is not None}")
        
        self.cameraSettingPage = self.findChild(QWidget, 'cameraSettingPage')
        logging.info(f"cameraSettingPage found: {self.cameraSettingPage is not None}")
        
        self.detectSettingPage = self.findChild(QWidget, 'detectSettingPage')
        logging.info(f"detectSettingPage found: {self.detectSettingPage is not None}")
        
        self.cameraSettingFrame = self.findChild(QWidget, 'cameraSettingFrame')
        logging.info(f"cameraSettingFrame found: {self.cameraSettingFrame is not None}")
        
        self.detectSettingFrame = self.findChild(QWidget, 'detectSettingFrame')
        logging.info(f"detectSettingFrame found: {self.detectSettingFrame is not None}")
        
        # Tìm các nút Apply và Cancel
        self.applySetting = self.findChild(QPushButton, 'applySetting')
        logging.info(f"applySetting button found: {self.applySetting is not None}")
        
        self.cancleSetting = self.findChild(QPushButton, 'cancleSetting')
        logging.info(f"cancleSetting button found: {self.cancleSetting is not None}")
        
        # Log current state of settingStackedWidget
        if self.settingStackedWidget:
            current_index = self.settingStackedWidget.currentIndex()
            count = self.settingStackedWidget.count()
            logging.info(f"settingStackedWidget state: index={current_index}, count={count}")
            
            # Log pages in the stacked widget
            for i in range(count):
                widget = self.settingStackedWidget.widget(i)
                widget_name = widget.objectName() if widget else "None"
                logging.info(f"Page {i}: {widget_name}")
        
        # Tìm các widget cài đặt cho Detect Tool trong detectSettingFrame
        if self.detectSettingFrame:
            self.thresholdSlider = self.findChild(QSlider, 'thresholdSlider')
            self.thresholdSpinBox = self.findChild(QSpinBox, 'thresholdSpinBox')
            self.minConfidenceEdit = self.findChild(QDoubleSpinBox, 'minConfidenceEdit')
            
            # Kết nối slider và spinbox nếu cả hai đều tồn tại
            if self.thresholdSlider and self.thresholdSpinBox:
                self.thresholdSlider.valueChanged.connect(self.thresholdSpinBox.setValue)
                self.thresholdSpinBox.valueChanged.connect(self.thresholdSlider.setValue)
        
        # Kết nối nút Apply và Cancel
        if self.applySetting:
            self.applySetting.clicked.connect(self._on_apply_setting)
        if self.cancleSetting:
            self.cancleSetting.clicked.connect(self._on_cancel_setting)

    def eventFilter(self, obj, event):
        # Handle mouse events for dragging
        if obj == self.cameraView.viewport():
            if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
                self._is_panning = True
                self._pan_start_pos = event.pos()
                self.cameraView.viewport().setCursor(Qt.ClosedHandCursor)
            elif event.type() == event.MouseMove and self._is_panning:
                delta = event.pos() - self._pan_start_pos
                self._pan_start_pos = event.pos()
                scale_factor = 1 / self.zoom_level  # Adjust movement based on zoom level

                # Adjust delta based on rotation angle
                angle_rad = np.radians(self.rotation_angle)
                cos_angle = np.cos(angle_rad)
                sin_angle = np.sin(angle_rad)
                adjusted_delta_x = delta.x() * cos_angle + delta.y() * sin_angle
                adjusted_delta_y = -delta.x() * sin_angle + delta.y() * cos_angle

                self.cameraView.horizontalScrollBar().setValue(
                    int(self.cameraView.horizontalScrollBar().value() - adjusted_delta_x * scale_factor)
                )
                self.cameraView.verticalScrollBar().setValue(
                    int(self.cameraView.verticalScrollBar().value() - adjusted_delta_y * scale_factor)
                )
            elif event.type() == event.MouseButtonRelease and event.button() == Qt.LeftButton:
                self._is_panning = False
                self.cameraView.viewport().setCursor(Qt.OpenHandCursor)
        return super().eventFilter(obj, event)


    def _on_add_tool_combo(self):
        tool_name = self.toolComboBox.currentText() if self.toolComboBox else None
        if not tool_name:
            return

        # Use the refactored helper function
        self.add_tool_to_job(tool_name)

        # If the tool is "Detect Tool", switch pages
        if tool_name == "Detect Tool" and self.stackedWidget and self.detectSettingPage and self.cameraSettingPage:
            detect_index = self.stackedWidget.indexOf(self.detectSettingPage)
            camera_index = self.stackedWidget.indexOf(self.cameraSettingPage)

            if detect_index != -1 and camera_index != -1:
                logging.info(f"Switching from cameraSettingPage (index {camera_index}) to detectSettingPage (index {detect_index}).")
                self.stackedWidget.setCurrentIndex(detect_index)
                logging.info("Switched to detectSettingPage in stackedWidget.")
            else:
                if detect_index == -1:
                    logging.error("detectSettingPage not found in stackedWidget.")
                if camera_index == -1:
                    logging.error("cameraSettingPage not found in stackedWidget.")

    def _on_remove_tool_from_job(self):
        # Xóa tool được chọn trong jobView
        index = self.jobView.currentIndex().row()
        job = self.job_manager.get_current_job()
        if job and 0 <= index < len(job.tools):
            job.tools.pop(index)
            self._update_job_view()

    def _on_edit_tool_in_job(self):
        # Chỉnh sửa tool được chọn trong jobView (demo: chỉ in ra tên tool)
        index = self.jobView.currentIndex().row()
        job = self.job_manager.get_current_job()
        if job and 0 <= index < len(job.tools):
            tool = job.tools[index]
            print(f"Edit tool: {tool.name}")
        self.ocr_tool = OcrTool()
        self.runJob.clicked.connect(self.run_current_job)


    def _setup_tool_and_job_views(self):
        # Load available tools into toolComboBox
        available_tools = ["Detect Tool", "Other Tool"]  # Add more tools as needed
        self.toolComboBox.addItems(available_tools)

        # Connect addTool button to add tool logic
        self.addTool.clicked.connect(self._on_add_tool)

        # Connect applySetting and cancleSetting buttons 
        self.applySetting.clicked.connect(self._on_apply_setting)
        self.cancleSetting.clicked.connect(self._on_cancel_setting)
        
        # Khởi tạo biến cho tool đang chờ xử lý
        self._pending_tool = None
        self._pending_tool_config = None

    def _on_add_tool(self):
        logging.info("_on_add_tool invoked.")
        tool_name = self.toolComboBox.currentText() if self.toolComboBox else None
        logging.info(f"Selected tool: {tool_name}")
        if not tool_name:
            logging.warning("No tool selected in toolComboBox.")
            return

        # Lưu tool được chọn vào biến tạm để xử lý sau khi nhấn applySetting
        self._pending_tool = tool_name
        logging.info(f"Saved pending tool: {self._pending_tool}")

        # Chuyển đến trang cài đặt tool tương ứng
        self._switch_to_tool_setting_page(tool_name)
    def _switch_to_tool_setting_page(self, tool_name):
        """Chuyển đến trang cài đặt tương ứng với tool được chọn"""
        logging.info(f"_switch_to_tool_setting_page called with tool: {tool_name}")
        
        if not tool_name:
            logging.error("tool_name is empty")
            return
            
        if not hasattr(self, 'settingStackedWidget') or self.settingStackedWidget is None:
            logging.error("settingStackedWidget not found")
            return
            
        # Log current state of the stacked widget
        current_index = self.settingStackedWidget.currentIndex()
        count = self.settingStackedWidget.count()
        logging.info(f"Current settingStackedWidget state: index={current_index}, count={count}")
            
        # Xác định trang cài đặt dựa trên tên tool
        target_page = None
        if tool_name == "Detect Tool" and hasattr(self, 'detectSettingPage'):
            target_page = self.detectSettingPage
            logging.info("Target page is detectSettingPage")
        elif tool_name == "Other Tool" and hasattr(self, 'otherToolSettingPage'):
            target_page = self.otherToolSettingPage
            logging.info("Target page is otherToolSettingPage")
        else:
            logging.error(f"No matching page found for tool: {tool_name}")
        # Thêm các tool khác tại đây
            
        # Chuyển đến trang cài đặt nếu tìm thấy
        if target_page:
            index = self.settingStackedWidget.indexOf(target_page)
            logging.info(f"Found target page at index: {index}")
            if index != -1:
                logging.info(f"Switching to {tool_name} setting page with index {index}.")
                self.settingStackedWidget.setCurrentIndex(index)
                # Verify the switch
                new_index = self.settingStackedWidget.currentIndex()
                logging.info(f"After switch, current index is: {new_index}")
            else:
                logging.error(f"Setting page for {tool_name} not found in settingStackedWidget.")
        else:
            logging.error(f"No setting page defined for {tool_name}")

    def add_tool_to_job(self, tool_name):
        if not tool_name:
            return

        # Ensure job_manager is initialized
        if not hasattr(self, 'job_manager') or not self.job_manager:
            logging.error("JobManager is not initialized.")
            return

        # If no current job, create a new one
        current_job = self.job_manager.get_current_job()
        if not current_job:
            logging.info("No current job found. Creating a new job.")
            current_job = Job("Job 1")
            self.job_manager.add_job(current_job)

        # Add the selected tool to the current job
        from tools.base_tool import GenericTool
        current_job.add_tool(GenericTool(tool_name))
        self._update_job_view()
        logging.info(f"Tool '{tool_name}' added to the current job.")

        return tool_name

    def _return_to_camera_setting_page(self):
        # Switch back to cameraSettingPage
        if hasattr(self, 'settingStackedWidget') and self.settingStackedWidget and hasattr(self, 'cameraSettingPage') and self.cameraSettingPage:
            index = self.settingStackedWidget.indexOf(self.cameraSettingPage)
            if index != -1:
                logging.info(f"Returning to camera setting page with index {index}.")
                self.settingStackedWidget.setCurrentIndex(index)
            else:
                logging.error("cameraSettingPage not found in settingStackedWidget.")
        else:
            logging.error("settingStackedWidget or cameraSettingPage not available.")

    def _on_apply_setting(self):
        """
        Xử lý khi người dùng nhấn nút Apply trong trang cài đặt tool.
        - Thêm tool và cấu hình vào job hiện tại
        - Quay lại trang cài đặt camera
        """
        if self._pending_tool:
            logging.info(f"Applying settings for tool: {self._pending_tool}")
            
            # Thu thập cấu hình từ UI tương ứng với tool
            config = self._collect_tool_config(self._pending_tool)
            
            # Tạo đối tượng Tool với cấu hình đã thu thập
            tool = self._create_tool_with_config(self._pending_tool, config)
            
            # Thêm tool vào job hiện tại
            if tool:
                self.add_tool_to_job_with_tool(tool)
                logging.info(f"Tool '{self._pending_tool}' with configuration added to job")
            
            # Reset biến tạm
            self._pending_tool = None
            self._pending_tool_config = None
        
        # Quay lại trang cài đặt camera
        self._return_to_camera_setting_page()
    
    def _on_cancel_setting(self):
        """
        Xử lý khi người dùng nhấn nút Cancel trong trang cài đặt tool.
        - Hủy bỏ thao tác thêm tool
        - Quay lại trang cài đặt camera
        """
        logging.info("Cancelling tool settings")
        
        # Reset biến tạm
        self._pending_tool = None
        self._pending_tool_config = None
        
        # Quay lại trang cài đặt camera
        self._return_to_camera_setting_page()
    
    def _collect_tool_config(self, tool_name):
        """Thu thập cấu hình từ UI tương ứng với từng loại tool"""
        config = {}
        
        # Thu thập cấu hình dựa trên loại tool
        if tool_name == "Detect Tool":
            # Ví dụ: Thu thập cấu hình từ UI cho Detect Tool
            if hasattr(self, 'thresholdSlider'):
                config['threshold'] = self.thresholdSlider.value()
            if hasattr(self, 'minConfidenceEdit'):
                try:
                    config['min_confidence'] = float(self.minConfidenceEdit.text())
                except (ValueError, AttributeError):
                    config['min_confidence'] = 0.5  # Giá trị mặc định
        
        # Thêm xử lý cho các loại tool khác tại đây
        
        logging.info(f"Collected config for {tool_name}: {config}")
        return config
    
    def _create_tool_with_config(self, tool_name, config):
        """Tạo đối tượng Tool với cấu hình đã thu thập"""
        from tools.base_tool import BaseTool, ToolConfig
        
        # Tạo đối tượng ToolConfig
        tool_config = ToolConfig(config)
        
        # Tạo đối tượng Tool tương ứng
        if tool_name == "Detect Tool":
            from detection.ocr_tool import OcrTool
            tool = OcrTool(config=tool_config)
        else:
            # Mặc định sử dụng Tool cơ bản
            from tools.base_tool import GenericTool
            tool = GenericTool(tool_name, config=tool_config)
        
        return tool
    
    def add_tool_to_job_with_tool(self, tool):
        """Thêm đối tượng Tool đã tạo vào job hiện tại"""
        # Ensure job_manager is initialized
        if not hasattr(self, 'job_manager') or not self.job_manager:
            logging.error("JobManager is not initialized.")
            return False

        # If no current job, create a new one
        current_job = self.job_manager.get_current_job()
        if not current_job:
            logging.info("No current job found. Creating a new job.")
            current_job = Job("Job 1")
            self.job_manager.add_job(current_job)

        # Add the tool to the current job
        current_job.add_tool(tool)
        self._update_job_view()
        logging.info(f"Tool '{tool.name}' added to the current job.")
        return True

    # This method has been merged with the one above
    # def _setup_tool_and_job_views(self):
    #     # Không can thiệp vào toolComboBox, giữ nguyên các item mặc định từ file .ui
    #     # Chỉ cập nhật jobView
    #     self._update_job_view()


    def _update_job_view(self):
        job = self.job_manager.get_current_job()
        if job:
            tool_names = [tool.name for tool in job.tools]
        else:
            tool_names = []
        self.job_model = QStringListModel(tool_names)
        self.jobView.setModel(self.job_model)

    def _on_add_tool(self):
        logging.info("_on_add_tool invoked.")
        tool_name = self.toolComboBox.currentText() if self.toolComboBox else None
        logging.info(f"Selected tool: {tool_name}")
        if not tool_name:
            logging.warning("No tool selected in toolComboBox.")
            return

        # Lưu tool được chọn vào biến tạm để xử lý sau khi nhấn applySetting
        self._pending_tool = tool_name
        logging.info(f"Saved pending tool: {self._pending_tool}")

        # Chuyển đến trang cài đặt tool tương ứng
        self._switch_to_tool_setting_page(tool_name)

    def rotate_left(self):
        self.rotation_angle = (self.rotation_angle - 90) % 360
        self._show_frame_with_zoom()

    def rotate_right(self):
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self._show_frame_with_zoom()
    def update_focus_value(self, value):
        """Cập nhật giá trị độ sắc nét trên thanh focusBar"""
        self.focusBar.setValue(value)
        
    def update_fps_display(self, fps_value):
        """Cập nhật giá trị FPS lên LCD display"""
        if hasattr(self, 'fpsNum') and self.fpsNum is not None:
            self.fpsNum.display(f"{fps_value:.1f}")

    def resizeEvent(self, event):
        """Xử lý sự kiện khi cửa sổ thay đổi kích thước"""
        super().resizeEvent(event)
        if hasattr(self, 'camera_view'):
            self.camera_view.handle_resize_event()
    # Đã hợp nhất các hàm __init__ thành 1 hàm duy nhất phía trên
    def toggle_live_camera(self):
        """Bật/tắt chế độ camera trực tiếp"""
        if self.liveCamera.isChecked():
            self.camera_stream.start_live()
            self.triggerCamera.setEnabled(False)
            self.liveCamera.setText("Stop Live Camera")
        else:
            self.camera_stream.stop_live()
            self.triggerCamera.setEnabled(True)
            self.liveCamera.setText("Live Camera")

    def run_current_job(self):
        """Chạy job hiện tại"""
        logging.info("Running current job")
        # Kiểm tra và thực hiện công việc
        # Phần xử lý job sẽ được thêm vào sau

    def display_frame(self, frame):
        """
        Phương thức xử lý frame từ camera
        Phương thức này không còn được sử dụng sau khi tách CameraView
        """
        logging.debug("This method is deprecated - use camera_view.display_frame() instead")
        pass
        self._show_frame_with_zoom()

        try:
            # Calculate sharpness using variance of Laplacian
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness_norm = min(int(sharpness / 10), 100)  # Normalize to 0-100
            self.focusBar.setValue(sharpness_norm)
            logging.debug("Sharpness calculated: %d", sharpness_norm)
        except Exception as e:
            logging.error("Error calculating sharpness: %s", e)

        # Update FPS counter
        if self.liveCamera.isChecked():
            self._fps_count += 1

    def _update_fps_display(self):
        if self.liveCamera.isChecked():
            self._fps_value = self._fps_count
            self._fps_count = 0
            if self.fpsNum:
                self.fpsNum.display(self._fps_value)
        else:
            if self.fpsNum:
                self.fpsNum.display(0)

    def _show_frame_with_zoom(self):
        if self.current_frame is None:
            logging.warning("No current frame to display")
            return

        try:
            # Convert the current frame to QPixmap
            h, w, ch = self.current_frame.shape
            bytes_per_line = ch * w
            rgb_image = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)

            # Ensure the scene exists and clear it
            if self._scene is None:
                self._scene = QGraphicsScene()
                self.cameraView.setScene(self._scene)

            # Safely manage _pixmap_item
            if hasattr(self, '_pixmap_item') and self._pixmap_item is not None:
                if self._pixmap_item.scene() is not None:
                    self._scene.removeItem(self._pixmap_item)
                self._pixmap_item = None

            self._pixmap_item = QGraphicsPixmapItem(pixmap)
            self._pixmap_item.setTransformationMode(Qt.SmoothTransformation)
            self._scene.addItem(self._pixmap_item)

            # Ensure the transform origin point is set to the center of the pixmap
            self._pixmap_item.setTransformOriginPoint(self._pixmap_item.boundingRect().width() / 2, self._pixmap_item.boundingRect().height() / 2)

            # Apply the rotation angle
            self._pixmap_item.setRotation(self.rotation_angle)

            # Adjust the scene rectangle to match the pixmap's bounding rectangle
            self._scene.setSceneRect(self._pixmap_item.boundingRect())

            # Center the view on the pixmap's center
            pixmap_center = self._pixmap_item.boundingRect().center()
            self.cameraView.centerOn(pixmap_center)

            # Ensure alignment is set to center the content
            self.cameraView.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

            # Adjust cursor and drag mode based on zoom level
            if self.zoom_level > 1.0:
                self.cameraView.setDragMode(QGraphicsView.ScrollHandDrag)
                self.cameraView.viewport().setCursor(Qt.OpenHandCursor)
            else:
                self.cameraView.setDragMode(QGraphicsView.NoDrag)
                self.cameraView.viewport().setCursor(Qt.ArrowCursor)

            # Fit the view if required
            if self._fit_on_next_frame:
                self.cameraView.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
                self.zoom_level = 1.0
                self._fit_on_next_frame = False
            else:
                self.cameraView.resetTransform()
                self.cameraView.scale(self.zoom_level, self.zoom_level)

            logging.debug("Frame displayed with zoom level: %f and rotation angle: %d", self.zoom_level, self.rotation_angle)
        except Exception as e:
            logging.error("Error displaying frame: %s", e)

    def zoom_in(self):
        self.zoom_level += self.zoom_step
        self.cameraView.scale(1 + self.zoom_step, 1 + self.zoom_step)

    def zoom_out(self):
        self.zoom_level -= self.zoom_step
        # Ensure zoom level does not go below a minimum value
        self.zoom_level -= self.zoom_step
        if self.zoom_level < 0.01:
            self.zoom_level = 0.01

        # Refresh the frame with the updated zoom level
        self._show_frame_with_zoom()

    def set_manual_exposure_mode(self):
        """Chuyển sang chế độ phơi sáng thủ công"""
        self._is_auto_exposure = False
        self.camera_stream.set_auto_exposure(False)
        self.exposureEdit.setEnabled(True)
        self.exposureSlider.setEnabled(True)
        if self.manualExposure:
            self.manualExposure.setEnabled(False)
        if self.autoExposure:
            self.autoExposure.setEnabled(True)

    def set_auto_exposure_mode(self):
        """Chuyển sang chế độ phơi sáng tự động"""
        self._is_auto_exposure = True
        self.camera_stream.set_auto_exposure(True)
        self.exposureEdit.setEnabled(False)
        self.exposureSlider.setEnabled(False)
        if self.manualExposure:
            self.manualExposure.setEnabled(True)
        if self.autoExposure:
            self.autoExposure.setEnabled(False)

    def run_current_job(self):
        """Chạy job hiện tại với frame hiện tại"""
        # Lấy job hiện tại
        job = self.job_manager.get_current_job()
        if not job or not job.tools:
            logging.warning("Không có job hoặc job không có công cụ nào")
            return
            
        # Lấy frame hiện tại từ camera view
        current_frame = self.camera_view.get_current_frame()
        if current_frame is None:
            logging.warning("Không có frame để xử lý")
            return
            
        # Nếu tool đầu tiên là OCR thì chạy nhận diện
        if job.tools[0].name == 'OCR':
            frame = current_frame.copy()
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            boxes = self.ocr_tool.detect(rgb)
            self._show_frame_with_ocr_boxes(frame, boxes)

    def _show_frame_with_ocr_boxes(self, frame, boxes):
        """Hiển thị frame với các box OCR"""
        self.camera_view.display_frame_with_ocr_boxes(frame, boxes)
