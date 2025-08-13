from PyQt5.QtGui import QCloseEvent, QStandardItem, QStandardItemModel
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QGraphicsView, QWidget, QStackedWidget, QComboBox, QPushButton, 
                            QSlider, QLineEdit, QProgressBar, QLCDNumber, QTabWidget, QListView, 
                            QTreeView, QMainWindow, QSpinBox, QDoubleSpinBox, QTableView, QVBoxLayout, QLabel, QFileDialog)
from PyQt5 import uic
import os
import logging
from job.job_manager_new import JobManager
from gui.tool_manager_new import ToolManager
from gui.settings_manager import SettingsManager
from gui.camera_manager import CameraManager
from gui.detect_tool_manager import DetectToolManager
from gui.workflow_view import WorkflowWidget
# Nếu JobEditDialog nằm ở file khác, cần import đúng đường dẫn
try:
    from gui.job_edit_dialog import JobEditDialog
except ImportError:
    # Nếu không có file riêng, comment lại để tránh lỗi
    JobEditDialog = None

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MainWindowNew(QMainWindow):
    # Dummy slot for tool_added signal
    def on_tool_added(self, tool_id=None):
        logging.info(f"Tool added: {tool_id}")

    # Dummy slot for tool_removed signal
    def on_tool_removed(self, tool_id=None):
        logging.info(f"Tool removed: {tool_id}")

    # Dummy slot for classification table changed
    def on_classification_table_changed(self, *args, **kwargs):
        logging.info("Classification table changed")

    # Dummy slot for start job button
    def on_start_job_button_clicked(self):
        logging.info("Start job button clicked")

    # Dummy slot for stop job button
    def on_stop_job_button_clicked(self):
        logging.info("Stop job button clicked")

    # Dummy slot for algorithm combo box changed
    def on_algorithm_changed(self, index=None):
        logging.info(f"Algorithm changed: {index}")

    # Dummy slot for camera combo box changed
    def on_camera_selected(self, index=None):
        logging.info(f"Camera selected: {index}")

    # Dummy slot for slider value changed
    def on_slider_value_changed(self, value=None):
        logging.info(f"Slider value changed: {value}")

    # Dummy slot for line edit text changed
    def on_line_edit_text_changed(self, text=None):
        logging.info(f"Line edit text changed: {text}")
    def __init__(self):
        super().__init__()
        self._editing_tool = None  # Tool đang được chỉnh sửa
        # Khởi tạo các biến thành viên với phiên bản mới
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
        # Không cần gọi _setup_managers vì các class _new không có các hàm liên kết manager
        self._connect_signals()
        logging.info("MainWindowNew initialized successfully")

    def _clear_tool_config_ui(self):
        """Reset UI cấu hình tool về mặc định khi tạo mới"""
        if self.x1PositionLineEdit:
            self.x1PositionLineEdit.setText("")
        if self.y1PositionLineEdit:
            self.y1PositionLineEdit.setText("")
        if self.x2PositionLineEdit:
            self.x2PositionLineEdit.setText("")
        if self.y2PositionLineEdit:
            self.y2PositionLineEdit.setText("")
        if self.classificationTableView and hasattr(self.classificationTableView, 'model'):
            model = self.classificationTableView.model()
            if model:
                model.removeRows(0, model.rowCount())
        if self.algorithmComboBox:
            if self.algorithmComboBox.count() > 0:
                self.algorithmComboBox.setCurrentIndex(0)
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
    def _find_widgets(self):
        """Tìm tất cả các widget cần thiết từ UI file"""
        # Camera view widgets
        self.cameraView = self.findChild(QGraphicsView, 'cameraView')
        self.focusBar = self.findChild(QProgressBar, 'focusBar')
        self.fpsNum = self.findChild(QLCDNumber, 'fpsNum')
        self.executionTime = self.findChild(QLCDNumber, 'executionTime')
        # Tool configuration widgets
        self.algorithmComboBox = self.findChild(QComboBox, 'algorithmComboBox')
        self.x1PositionLineEdit = self.findChild(QLineEdit, 'x1PositionLineEdit')
        self.y1PositionLineEdit = self.findChild(QLineEdit, 'y1PositionLineEdit')
        self.x2PositionLineEdit = self.findChild(QLineEdit, 'x2PositionLineEdit')
        self.y2PositionLineEdit = self.findChild(QLineEdit, 'y2PositionLineEdit')
        self.classificationTableView = self.findChild(QTableView, 'classificationTableView')
        # Job control widgets
        self.jobNameLineEdit = self.findChild(QLineEdit, 'jobNameLineEdit')
        self.jobStatusLabel = self.findChild(QLabel, 'jobStatusLabel')
        self.startJobButton = self.findChild(QPushButton, 'startJobButton')
        self.stopJobButton = self.findChild(QPushButton, 'stopJobButton')
        # Camera control widgets
        self.cameraSelectComboBox = self.findChild(QComboBox, 'cameraSelectComboBox')
        self.brightnessSlider = self.findChild(QSlider, 'brightnessSlider')
        self.contrastSlider = self.findChild(QSlider, 'contrastSlider')
        # Layouts
        self.mainLayout = self.findChild(QVBoxLayout, 'mainLayout')
        self.toolConfigLayout = self.findChild(QVBoxLayout, 'toolConfigLayout')
        self.jobControlLayout = self.findChild(QVBoxLayout, 'jobControlLayout')
        # Debug: Log all found widgets
        logging.info("Widgets found:")
        for widget in [self.cameraView, self.focusBar, self.fpsNum, self.executionTime,
                        self.algorithmComboBox, self.x1PositionLineEdit, self.y1PositionLineEdit,
                        self.x2PositionLineEdit, self.y2PositionLineEdit, self.classificationTableView,
                        self.jobNameLineEdit, self.jobStatusLabel, self.startJobButton, self.stopJobButton,
                        self.cameraSelectComboBox, self.brightnessSlider, self.contrastSlider,
                        self.mainLayout, self.toolConfigLayout, self.jobControlLayout]:
            if widget is not None:
                logging.info(f" - {widget.objectName()} ({type(widget)})")
            else:
                logging.warning(f" - Widget not found (NoneType)")
    # Không cần _setup_managers với các class _new
    def _update_workflow_view(self):
        """Cập nhật workflow view dựa trên cấu hình hiện tại của tools và jobs"""
        if not hasattr(self, 'workflow_view') or not self.workflow_view:
            logging.warning("Workflow view not found")
            return
        # Lấy danh sách các tool đã cấu hình từ ToolManager
        tools = self.tool_manager.get_tools()
        # Cập nhật workflow view
        self.workflow_view.clear()
        for tool in tools:
            self.workflow_view.add_tool(tool)
        logging.info(f"Workflow view updated: {len(tools)} tools")
    def refresh_detect_tool_manager(self):
        """Làm mới danh sách các tool phát hiện trong DetectToolManager"""
        # Không có hàm update_tool_list, có thể cần custom lại logic này
        logging.info("DetectToolManager refresh: no update_tool_list method in new class")
    def _connect_signals(self):
        """Kết nối các tín hiệu và slot giữa các widget và manager"""
        # Không có signal camera_connected/camera_disconnected trong CameraManager mới
        # Kết nối tín hiệu cho tool manager
        self.tool_manager.tool_added.connect(self.on_tool_added)
        self.tool_manager.tool_removed.connect(self.on_tool_removed)
        # Không có signal tool_edited trong ToolManager mới
        # Kết nối tín hiệu cho job manager
        # Không có các signal job_started, job_stopped, job_progress trong JobManager mới
        # Kết nối tín hiệu cho detect tool manager
        # Không có signal tool_list_updated trong DetectToolManager mới
        # Kết nối tín hiệu cho các widget
        if self.startJobButton:
            self.startJobButton.clicked.connect(self.on_start_job_button_clicked)
        if self.stopJobButton:
            self.stopJobButton.clicked.connect(self.on_stop_job_button_clicked)
        if self.algorithmComboBox:
            self.algorithmComboBox.currentIndexChanged.connect(self.on_algorithm_changed)
        if self.cameraSelectComboBox:
            self.cameraSelectComboBox.currentIndexChanged.connect(self.on_camera_selected)
        # Kết nối tín hiệu cho các slider
        for slider in [self.brightnessSlider, self.contrastSlider]:
            if slider is not None:
                slider.valueChanged.connect(self.on_slider_value_changed)
        # Kết nối tín hiệu cho các line edit
        for line_edit in [self.x1PositionLineEdit, self.y1PositionLineEdit, self.x2PositionLineEdit, self.y2PositionLineEdit]:
            line_edit.textChanged.connect(self.on_line_edit_text_changed)
        # Kết nối tín hiệu cho table view
        # Đảm bảo model là QStandardItemModel
        if self.classificationTableView:
            model = self.classificationTableView.model()
            if model is None or not isinstance(model, QStandardItemModel):
                model = QStandardItemModel()
                self.classificationTableView.setModel(model)
            model.dataChanged.connect(self.on_classification_table_changed)
    def _add_camera_source_to_combo_box(self):
        """Thêm các nguồn camera có sẵn vào combo box chọn camera"""
        if not hasattr(self, 'camera_manager') or not self.camera_manager:
            logging.warning("Camera manager not found")
            return
        # Lấy danh sách các camera có sẵn
        # Không có hàm get_available_cameras, cần custom lại logic lấy danh sách camera
        camera_list = []
        # Xóa bỏ các mục cũ trong combo box
        self.cameraSelectComboBox.clear()
        # Thêm các camera mới vào combo box
        for camera in camera_list:
            self.cameraSelectComboBox.addItem(camera)
        logging.info(f"Camera sources updated: {len(camera_list)} cameras")
    def _on_tab_changed(self, index):
        """Xử lý khi tab được thay đổi"""
        logging.info(f"Tab changed: {index}")
        # Cập nhật lại workflow view khi tab thay đổi
        self._update_workflow_view()
    def _on_workflow_node_selected(self, tool_id):
        """Xử lý khi một node trong workflow được chọn"""
        logging.info(f"Workflow node selected: {tool_id}")
        # Tìm tool tương ứng và tải cấu hình vào UI
        tool = self.tool_manager.get_tool(tool_id)
        if tool:
            self._load_tool_config_to_ui(tool)
    def _on_add_tool(self):
        """Xử lý khi thêm tool mới"""
        logging.info("Add tool button clicked")
        # Tạo một tool mới với cấu hình mặc định
        # create_tool cần truyền tên tool, ví dụ 'DetectTool' hoặc lấy từ UI
        new_tool = self.tool_manager.add_tool('DetectTool')
        # Tải cấu hình của tool mới vào UI để chỉnh sửa
        self._load_tool_config_to_ui(new_tool)
    def _on_edit_tool(self):
        """Xử lý khi chỉnh sửa tool"""
        logging.info("Edit tool button clicked")
        if not self._editing_tool:
            logging.warning("No tool is currently being edited")
            return
        # Lưu cấu hình của tool hiện tại trước khi chỉnh sửa
        self._apply_tool_config()
        # Tìm tool cần chỉnh sửa
        tool = self.tool_manager.get_tool(self._editing_tool.id)
        if tool:
            # Tải cấu hình của tool vào UI
            self._load_tool_config_to_ui(tool)
    def _on_remove_tool(self):
        """Xử lý khi xóa tool"""
        logging.info("Remove tool button clicked")
        if not self._editing_tool:
            logging.warning("No tool is currently being edited")
            return
        # Xóa tool khỏi ToolManager
        self.tool_manager.remove_tool(self._editing_tool.id)
        # Xóa thông tin tool đang chỉnh sửa
        self._editing_tool = None
        # Xóa cấu hình tool trên UI
        self._clear_tool_config_ui()
    def _on_apply_setting(self):
        """Xử lý khi áp dụng cài đặt"""
        logging.info("Apply settings button clicked")
        # Lưu cấu hình của tool hiện tại
        self._apply_tool_config()
        # Áp dụng cài đặt camera nếu có thay đổi
        self._apply_camera_settings()
    def _on_cancel_setting(self):
        """Xử lý khi hủy bỏ cài đặt"""
        logging.info("Cancel settings button clicked")
        # Nếu đang chỉnh sửa tool, tải lại cấu hình gốc
        if self._editing_tool:
            self._load_tool_config_to_ui(self._editing_tool)
    def _on_edit_job(self):
        """Xử lý khi chỉnh sửa job"""
        logging.info("Edit job button clicked")
        # Mở dialog chỉnh sửa job
        # Thay thế JobEditDialog bằng một thông báo tạm thời
        logging.warning("JobEditDialog is not implemented. Please create a job edit dialog.")
    def _load_tool_config_to_ui(self, tool):
        """Tải cấu hình của tool vào các widget trên UI"""
        logging.info(f"Loading tool config to UI: {tool.id}")
        # Lưu trữ tool đang được chỉnh sửa
        self._editing_tool = tool
        # Điền thông tin cơ bản của tool
        if self.algorithmComboBox and tool.algorithm:
            index = self.algorithmComboBox.findText(tool.algorithm)
            if index >= 0:
                self.algorithmComboBox.setCurrentIndex(index)
        if self.x1PositionLineEdit:
            self.x1PositionLineEdit.setText(str(tool.x1))
        if self.y1PositionLineEdit:
            self.y1PositionLineEdit.setText(str(tool.y1))
        if self.x2PositionLineEdit:
            self.x2PositionLineEdit.setText(str(tool.x2))
        if self.y2PositionLineEdit:
            self.y2PositionLineEdit.setText(str(tool.y2))
        # Điền thông tin phân loại nếu có
        if self.classificationTableView:
            model = self.classificationTableView.model()
            if model is None or not isinstance(model, QStandardItemModel):
                model = QStandardItemModel()
                self.classificationTableView.setModel(model)
            model.removeRows(0, model.rowCount())
            for cls in getattr(tool, 'classification', []):
                items = [QStandardItem(str(getattr(cls, 'name', ''))), QStandardItem(str(getattr(cls, 'threshold', '')))]
                model.appendRow(items)
    def _on_draw_area_clicked(self):
        """Xử lý khi người dùng nhấp vào vùng vẽ"""
        logging.info("Draw area clicked")
        # Nếu không có camera view, thoát
        if not hasattr(self.camera_manager, 'camera_view') or not self.camera_manager.camera_view:
            logging.warning("No camera view found")
            return
        camera_view = self.camera_manager.camera_view
        # Nếu đang ở chế độ chỉnh sửa overlay, thoát
        # Không có hàm is_overlay_edit_mode, bỏ qua kiểm tra này
        # Chuyển đổi giữa các chế độ vẽ vùng phát hiện
        if not hasattr(self, '_drawing_enabled') or not self._drawing_enabled:
            self._enable_drawing()
        else:
            self._disable_drawing()
    def _on_area_drawn(self, x1, y1, x2, y2):
        """Xử lý khi một vùng được vẽ xong"""
        logging.info(f"Area drawn: ({x1}, {y1}), ({x2}, {y2})")
        # Lưu tọa độ vùng phát hiện
        # Không có hàm set_detection_area, cần custom lại logic này
    def _on_area_changed(self, x1, y1, x2, y2):
        """Xử lý khi tọa độ vùng phát hiện thay đổi"""
        logging.info(f"Area changed: ({x1}, {y1}), ({x2}, {y2})")
        # Cập nhật tọa độ vùng phát hiện
        # Không có hàm update_detection_area, cần custom lại logic này
    def _collect_detection_area(self):
        """Thu thập thông tin vùng phát hiện từ UI"""
        if not self._editing_tool:
            logging.warning("No tool is currently being edited")
            return
        # Lấy tọa độ vùng phát hiện từ UI
        x1 = int(self.x1PositionLineEdit.text()) if self.x1PositionLineEdit.text() else 0
        y1 = int(self.y1PositionLineEdit.text()) if self.y1PositionLineEdit.text() else 0
        x2 = int(self.x2PositionLineEdit.text()) if self.x2PositionLineEdit.text() else 0
        y2 = int(self.y2PositionLineEdit.text()) if self.y2PositionLineEdit.text() else 0
        # Cập nhật vùng phát hiện cho tool đang chỉnh sửa
        self._editing_tool.set_detection_area(x1, y1, x2, y2)
    def save_current_job(self):
        """Lưu job hiện tại vào file"""
        logging.info("Saving current job")
        # Hiển thị hộp thoại lưu file
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Job File", "", "Job Files (*.job);;All Files (*)", options=options)
        if not file_name:
            logging.info("Save job canceled")
            return
        # Lưu job vào file
        # Không có hàm save_job_to_file, cần custom lại logic lưu job
        success = False
        if success:
            logging.info(f"Job saved successfully: {file_name}")
        else:
            logging.error(f"Failed to save job: {file_name}")
    def load_job_file(self):
        """Tải job từ file"""
        logging.info("Loading job file")
        # Hiển thị hộp thoại mở file
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Job File", "", "Job Files (*.job);;All Files (*)", options=options)
        if not file_name:
            logging.info("Load job canceled")
            return
        # Tải job từ file
        # Không có hàm load_job_from_file, cần custom lại logic load job
        success = False
        if success:
            logging.info(f"Job loaded successfully: {file_name}")
            # Cập nhật lại UI sau khi tải job
            self._update_ui_after_job_loaded()
        else:
            logging.error(f"Failed to load job: {file_name}")
    def add_new_job(self):
        """Thêm job mới"""
        logging.info("Adding new job")
        # Tạo một job mới với cấu hình mặc định
        # Không có hàm create_job, cần custom lại logic tạo job
        new_job = None
        # Cập nhật lại UI sau khi thêm job mới
        self._update_ui_after_job_added(new_job)
    def remove_current_job(self):
        """Xóa job hiện tại"""
        logging.info("Removing current job")
        # Không có current_job, cần custom lại logic xóa job
        logging.warning("No current job to remove (API changed)")
    def run_current_job(self):
        """Chạy job hiện tại"""
        logging.info("Running current job")
        # Không có current_job, cần custom lại logic chạy job
        logging.warning("No current job to run (API changed)")
    def _apply_camera_settings(self):
        """Áp dụng các cài đặt camera từ UI"""
        logging.info("Applying camera settings")
        # Không có current_camera, set_camera_brightness, set_camera_contrast
        logging.warning("CameraManager API changed, skipping apply_camera_settings")
    def _load_camera_formats(self):
        """Tải định dạng camera từ SettingsManager và thêm vào combo box chọn định dạng"""
        logging.info("Loading camera formats")
        # Không có camera_formats, cần custom lại logic load camera formats
        logging.warning("SettingsManager API changed, skipping _load_camera_formats")
    def reload_camera_formats(self):
        """Tải lại định dạng camera từ file cấu hình"""
        logging.info("Reloading camera formats")
        # Không có hàm load_camera_formats, bỏ qua
    def resizeEvent(self, a0):
        """Xử lý sự kiện thay đổi kích thước cửa sổ"""
        if a0:
            size = a0.size()
            logging.info(f"Window resized: {size.width()}x{size.height()}")
        # Cập nhật lại kích thước cho các widget nếu cần thiết
    def closeEvent(self, a0):
        """Xử lý sự kiện đóng cửa sổ"""
        logging.info("Main window closing")
        # Không cần disconnect_camera, chỉ accept event
        if a0 is not None:
            a0.accept()
