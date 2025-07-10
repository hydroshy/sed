from PyQt5.QtWidgets import QMainWindow, QMessageBox, QVBoxLayout, QListView, QTreeView, QPushButton, QProgressBar, QFileDialog, QLabel, QSlider, QHBoxLayout, QSpinBox
from PyQt5.QtCore import QStringListModel, QTimer, Qt
from gui.region_selector import RegionSelectorWidget
from gui.ui_mainwindow import Ui_MainWindow
import cv2
import numpy as np
import time
import json
from detection.edge_detection import detect_edges
from job.job_manager import (
    add_job,
    edit_job,
    remove_job,
    run_job,
    save_job_file,
    load_job_file,
    reload_job_tree,
)
from tool.tool_selector import get_camera_sources

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("Smart Eye Detection (SED)")

        # Add RegionSelectorWidget to graphicsView
        self.region_selector = RegionSelectorWidget(camera_index=0)
        layout = self.ui.cameraView.layout()
        if layout is None:
            layout = QVBoxLayout(self.ui.cameraView)
        layout.addWidget(self.region_selector)
        self.region_selector.setVisible(True)

        # --- Không kiểm tra camera khi khởi động, không enable live/triggerCamera ---

        # --- Zoom state ---
        self.zoom_factor = 1.0
        self.zoom_step = 0.1
        self.min_zoom = 0.2
        self.max_zoom = 3.0

        # --- Exposure/Gain/EV controls ---
        # Exposure
        self.ui.exposureSlider.setMinimum(100)
        self.ui.exposureSlider.setMaximum(30000)
        self.ui.exposureSlider.setValue(10000)
        self.ui.exposureEdit.setText(str(10000))
        # Gain
        self.ui.gainSlider.setMinimum(1)
        self.ui.gainSlider.setMaximum(32)
        self.ui.gainSlider.setValue(1)
        self.ui.gainEdit.setText(str(1))
        # EV
        self.ui.evSlider.setMinimum(-8)
        self.ui.evSlider.setMaximum(8)
        self.ui.evSlider.setValue(0)
        self.ui.evEdit.setText(str(0))

        # Exposure sync
        self.ui.exposureSlider.valueChanged.connect(lambda v: self.ui.exposureEdit.setText(str(v)))
        self.ui.exposureEdit.editingFinished.connect(self.on_exposure_edit_changed)
        self.ui.exposureSlider.valueChanged.connect(self.on_exposure_changed)
        # Gain sync
        self.ui.gainSlider.valueChanged.connect(lambda v: self.ui.gainEdit.setText(str(v)))
        self.ui.gainEdit.editingFinished.connect(self.on_gain_edit_changed)
        self.ui.gainSlider.valueChanged.connect(self.on_gain_changed)
        # EV sync
        self.ui.evSlider.valueChanged.connect(lambda v: self.ui.evEdit.setText(str(v)))
        self.ui.evEdit.editingFinished.connect(self.on_ev_edit_changed)
        self.ui.evSlider.valueChanged.connect(self.on_ev_changed)

        # --- Zoom buttons ---
        self.ui.zoomIn.clicked.connect(self.zoom_in)
        self.ui.zoomOut.clicked.connect(self.zoom_out)

        # --- Camera parameter apply on start ---
        self.apply_camera_parameters()

        # Live/Trigger camera logic
        self.live_mode = False
        self.ui.liveCamera.clicked.connect(self.toggle_live_camera)
        self.ui.triggerCamera.clicked.connect(self.trigger_camera)

        # FocusBar update: Timer to poll focus value
        self.focus_timer = QTimer(self)
        self.focus_timer.timeout.connect(self.update_focus_bar)

        # ToolView: QListView
        self.tool_model = QStringListModel([
            "Image source",
            "Phát hiện biên",  # Edge Detection
            "ROI Selector"
            # ...bạn có thể thêm các tool khác ở đây...
        ])
        self.ui.toolView.setModel(self.tool_model)
        # Đảm bảo các nút addTool/cancleTool thuộc toolLayout hoạt động đúng
        try:
            self.ui.addTool.clicked.disconnect(self.add_tool)
        except Exception:
            pass
        self.ui.addTool.clicked.connect(self.add_tool)
        try:
            self.ui.cancleTool.clicked.disconnect()
        except Exception:
            pass
        self.ui.cancleTool.clicked.connect(self.cancel_tool_selection)
        self.ui.addTool.setEnabled(False)
        self.ui.cancleTool.setEnabled(False)

        # Khi chọn tool, enable addTool/cancleTool và xử lý đặc biệt cho Image source
        self.ui.toolView.clicked.connect(self.on_tool_selected)

        # JobView: QTreeView (dạng cây: job cha, tool con)
        from PyQt5.QtGui import QStandardItemModel, QStandardItem
        self.job_model = QStandardItemModel()
        self.job_model.setHorizontalHeaderLabels(["Job/Tool", "ROI"])
        self.ui.jobView.setModel(self.job_model)
        # Không cho phép kéo-thả job/tool trong treeview
        self.ui.jobView.setDragDropMode(self.ui.jobView.NoDragDrop)
        self.ui.jobView.setSelectionMode(self.ui.jobView.SingleSelection)
        self.ui.jobView.setDefaultDropAction(Qt.IgnoreAction)
        self.ui.jobView.setDragEnabled(False)
        self.ui.jobView.setAcceptDrops(False)
        self.ui.jobView.setDropIndicatorShown(False)

        self.ui.addJob.clicked.connect(lambda: add_job(self))
        self.ui.editJob.clicked.connect(lambda: edit_job(self))
        self.ui.removeJob.clicked.connect(lambda: remove_job(self))
        self.ui.runJob.clicked.connect(lambda: run_job(self))
        self.ui.saveJob.clicked.connect(lambda: save_job_file(self))
        self.ui.loadJob.clicked.connect(lambda: load_job_file(self))

        # Lưu trữ job và tool
        self.jobs = []  # [{name:..., tools:[{name:..., roi:...}, ...]}, ...]

        # Tool setting logic
        self.current_setting_frame = None
        self.current_tool_name = None
        self.setting_config = {}
        self.ui.applySettingButton.clicked.connect(self.apply_tool_setting)
        self.ui.cancleSettingButton.clicked.connect(self.cancel_tool_setting)
        
        # Hide settings panel by default
        self.ui.settingFrame.setVisible(False)
        self.ui.applySettingButton.setVisible(False)
        self.ui.cancleSettingButton.setVisible(False)

        # Thêm phần xử lý khi chọn item trong jobView
        self.ui.jobView.clicked.connect(self.on_job_view_clicked)

    def apply_camera_parameters(self):
        # Gọi khi cần áp dụng các tham số camera
        exposure = int(self.ui.exposureSlider.value())
        gain = int(self.ui.gainSlider.value())
        ev = int(self.ui.evSlider.value())
        self.region_selector.camera.set_exposure_time(exposure)
        if hasattr(self.region_selector.camera, "set_gain"):
            self.region_selector.camera.set_gain(gain)
        if hasattr(self.region_selector.camera, "set_ev"):
            self.region_selector.camera.set_ev(ev)

    def on_exposure_changed(self, value):
        self.ui.exposureEdit.setText(str(value))
        self.region_selector.camera.set_exposure_time(value)

    def on_exposure_edit_changed(self):
        try:
            value = int(self.ui.exposureEdit.text())
        except Exception:
            value = self.ui.exposureSlider.value()
        value = max(self.ui.exposureSlider.minimum(), min(self.ui.exposureSlider.maximum(), value))
        self.ui.exposureSlider.setValue(value)
        self.region_selector.camera.set_exposure_time(value)

    def on_gain_changed(self, value):
        self.ui.gainEdit.setText(str(value))
        if hasattr(self.region_selector.camera, "set_gain"):
            self.region_selector.camera.set_gain(value)

    def on_gain_edit_changed(self):
        try:
            value = int(self.ui.gainEdit.text())
        except Exception:
            value = self.ui.gainSlider.value()
        value = max(self.ui.gainSlider.minimum(), min(self.ui.gainSlider.maximum(), value))
        self.ui.gainSlider.setValue(value)
        if hasattr(self.region_selector.camera, "set_gain"):
            self.region_selector.camera.set_gain(value)

    def on_ev_changed(self, value):
        self.ui.evEdit.setText(str(value))
        if hasattr(self.region_selector.camera, "set_ev"):
            self.region_selector.camera.set_ev(value)

    def on_ev_edit_changed(self):
        try:
            value = int(self.ui.evEdit.text())
        except Exception:
            value = self.ui.evSlider.value()
        value = max(self.ui.evSlider.minimum(), min(self.ui.evSlider.maximum(), value))
        self.ui.evSlider.setValue(value)
        if hasattr(self.region_selector.camera, "set_ev"):
            self.region_selector.camera.set_ev(value)

    def zoom_in(self):
        if self.zoom_factor < self.max_zoom:
            self.zoom_factor += self.zoom_step
            self.region_selector.view.resetTransform()
            self.region_selector.view.scale(self.zoom_factor, self.zoom_factor)

    def zoom_out(self):
        if self.zoom_factor > self.min_zoom:
            self.zoom_factor -= self.zoom_step
            self.region_selector.view.resetTransform()
            self.region_selector.view.scale(self.zoom_factor, self.zoom_factor)

    def get_selected_job_source(self):
        # Lấy thông tin nguồn camera từ job đang chọn (nếu có)
        selected_indexes = self.ui.jobView.selectedIndexes()
        if not selected_indexes:
            return None
        job_index = selected_indexes[0]
        if job_index.parent().isValid():
            job_index = job_index.parent()
        job_row = job_index.row()
        if job_row >= len(self.jobs):
            return None
        tools = self.jobs[job_row]["tools"]
        for tool in tools:
            if tool.get("name") == "Image source":
                # tool["source"] có thể là "USB Camera 0", "Raspberry Pi Camera (CSI)", ...
                return tool.get("source")
        return None

    def parse_source_to_index(self, source_str):
        # Chuyển chuỗi nguồn thành index và loại (USB/CSI)
        if source_str is None:
            return None, None
        if source_str.startswith("USB Camera"):
            idx = int(source_str.split()[-1])
            return idx, "usb"
        elif "CSI" in source_str:
            return 0, "csi"
        return None, None

    def set_region_selector_camera(self, source_str):
        idx, typ = self.parse_source_to_index(source_str)
        if typ == "usb":
            # USB camera: dùng OpenCV, không dùng picamera2
            self.region_selector.camera = __import__('camera.camera_stream', fromlist=['CameraStream']).CameraStream(src=idx, use_picamera=False)
        elif typ == "csi":
            # CSI camera: dùng Picamera2
            self.region_selector.camera = __import__('camera.camera_stream', fromlist=['CameraStream']).CameraStream(src=0, use_picamera=True)
        else:
            self.region_selector.camera = None

    def toggle_live_camera(self):
        # Lấy nguồn camera từ job đang chọn
        source_str = self.get_selected_job_source()
        if not source_str:
            QMessageBox.warning(self, "Thiếu nguồn", "Job chưa có Image source. Hãy thêm nguồn camera vào job trước.")
            return
        # Nếu đang bật live_mode, nhấn lần nữa sẽ tắt
        if self.live_mode:
            self.live_mode = False
            self.region_selector.timer.stop()
            self.focus_timer.stop()
            self.ui.liveCamera.setStyleSheet("")
            self.ui.liveCamera.setText("Live Camera")
            if self.region_selector.camera:
                self.region_selector.camera.stop()
            return
        # Nếu đang tắt, nhấn sẽ bật
        self.set_region_selector_camera(source_str)
        self.apply_camera_parameters()
        if self.region_selector.camera is None:
            QMessageBox.critical(self, "Camera Error", "Không thể khởi tạo nguồn camera này.")
            return
        self.region_selector.camera.start()
        if not self.region_selector.camera.available:
            QMessageBox.critical(self, "Camera Error", "Không thể bật camera. Vui lòng kiểm tra kết nối hoặc cấu hình camera.")
            self.ui.liveCamera.setEnabled(False)
            self.ui.triggerCamera.setEnabled(False)
            self.live_mode = False
            self.ui.liveCamera.setText("Live Camera")
            self.region_selector.camera.stop()
            return
        self.ui.liveCamera.setEnabled(True)
        self.ui.triggerCamera.setEnabled(True)
        self.live_mode = True
        self.region_selector.start_camera()
        self.focus_timer.start(200)
        self.ui.liveCamera.setStyleSheet("font-weight: bold; background-color: #4caf50; color: white;")
        self.ui.liveCamera.setText("Live Camera (ON)")

    def trigger_camera(self):
        # Lấy nguồn camera từ job đang chọn
        source_str = self.get_selected_job_source()
        if not source_str:
            QMessageBox.warning(self, "Thiếu nguồn", "Job chưa có Image source. Hãy thêm nguồn camera vào job trước.")
            return
        self.set_region_selector_camera(source_str)
        self.apply_camera_parameters()
        if self.region_selector.camera is None:
            QMessageBox.critical(self, "Camera Error", "Không thể khởi tạo nguồn camera này.")
            return
        self.region_selector.camera.start()
        if not self.region_selector.camera.available:
            QMessageBox.critical(self, "Camera Error", "Không thể bật camera. Vui lòng kiểm tra kết nối hoặc cấu hình camera.")
            self.ui.liveCamera.setEnabled(False)
            self.ui.triggerCamera.setEnabled(False)
            self.region_selector.camera.stop()
            return
        self.ui.liveCamera.setEnabled(True)
        self.ui.triggerCamera.setEnabled(True)
        frame = self.region_selector.camera.get_frame()
        if frame is not None:
            self.region_selector.current_frame = frame
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            from PyQt5.QtGui import QImage, QPixmap
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            self.region_selector.pixmap_item.setPixmap(pixmap)
            self.region_selector.scene.setSceneRect(0, 0, w, h)
            self.region_selector.view.resetTransform()
            self.region_selector.view.scale(self.zoom_factor, self.zoom_factor)
        self.region_selector.camera.stop()

    def update_focus_bar(self):
        frame = self.region_selector.current_frame
        if frame is not None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            focus_measure = cv2.Laplacian(gray, cv2.CV_64F).var()
            value = min(int(focus_measure / 10), 100)
            self.ui.focusBar.setValue(value)

    def on_tool_selected(self, index):
        tool_name = index.data()
        # Chỉ enable nút addTool và cancleTool, không hiển thị setting ngay
        self.ui.addTool.setEnabled(True)
        self.ui.cancleTool.setEnabled(True)
        # Không gọi show_tool_setting ở đây nữa
        
        # Xử lý đặc biệt cho Image source: hiển thị danh sách nguồn camera
        if tool_name == "Image source":
            sources = get_camera_sources()
            if not sources:
                sources = ["Không phát hiện camera"]
            from PyQt5.QtCore import QStringListModel
            self.source_model = QStringListModel(sources)
            self.ui.toolView.setModel(self.source_model)
            self.ui.toolView.clicked.disconnect()
            self.ui.toolView.clicked.connect(self.on_source_selected)
        else:
            if hasattr(self, "source_model"):
                self.ui.toolView.setModel(self.tool_model)
                self.ui.toolView.clicked.disconnect()
                self.ui.toolView.clicked.connect(self.on_tool_selected)

    def on_source_selected(self, index):
        """Xử lý khi chọn nguồn camera từ danh sách"""
        self.selected_source = index.data()
        self.ui.addTool.setEnabled(True)  # Cho phép thêm tool sau khi chọn nguồn
        self.ui.cancleTool.setEnabled(True)

    def clear_tool_setting(self):
        """Xóa tất cả các widget trong settingLayout"""
        try:
            layout = self.ui.settingLayout
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                    
            self.current_setting_frame = None
            self.current_tool_name = None
            self.setting_config = {}
            
            # Hide settings panel when clearing
            self.ui.settingFrame.setVisible(False)
            self.ui.applySettingButton.setVisible(False)
            self.ui.cancleSettingButton.setVisible(False)
        except (AttributeError, RuntimeError):
            print("Warning: Could not clear tool settings")

    def add_tool(self):
        from PyQt5.QtGui import QStandardItem
        selected_indexes = self.ui.jobView.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Chọn Job", "Hãy chọn một job để thêm tool.")
            return
        job_index = selected_indexes[0]
        if job_index.parent().isValid():
            job_index = job_index.parent()
        job_row = job_index.row()
        
        # Nếu đang ở chế độ chọn nguồn camera
        if hasattr(self, "source_model") and self.ui.toolView.model() == self.source_model:
            tool_name = "Image source"
            source = getattr(self, "selected_source", None)
            if not source or source == "Không phát hiện camera":
                QMessageBox.warning(self, "Chọn nguồn", "Hãy chọn một nguồn camera.")
                return
                
            roi_tuple = None
            roi_str = source
            tool_item = QStandardItem(f"{tool_name} ({source}) (Chưa cấu hình)")  # Đánh dấu chưa cấu hình
            tool_item.setEditable(False)
            roi_item = QStandardItem(roi_str)
            self.job_model.item(job_row, 0).appendRow([tool_item, roi_item])
            
            # Thêm tool vào jobs với trạng thái pending
            tool_data = {
                "name": tool_name,
                "source": source,
                "roi": roi_tuple,
                "pending": True,  # Đánh dấu là chưa hoàn tất cấu hình
                "config": {"exposure": 10000, "gain": 1, "ev": 0}  # Giá trị mặc định
            }
            self.jobs[job_row]["tools"].append(tool_data)
            
            # Cập nhật tools trong job
            self.update_tool_arrows(job_row)
            
            # Trước tiên, khởi tạo camera và hiển thị hình ảnh trong chế độ trigger
            self.set_region_selector_camera(source)
            if self.region_selector.camera is None:
                QMessageBox.critical(self, "Camera Error", "Không thể khởi tạo nguồn camera này.")
                return
                
            # Kích hoạt camera để hiển thị hình ảnh
            self.region_selector.camera.start()
            if not self.region_selector.camera.available:
                QMessageBox.critical(self, "Camera Error", "Không thể bật camera. Vui lòng kiểm tra kết nối hoặc cấu hình camera.")
                # Xóa tool vừa thêm nếu camera không khả dụng
                self.job_model.item(job_row, 0).removeRow(tool_item.row())
                self.jobs[job_row]["tools"].pop()
                return
                
            # Hiển thị hình ảnh từ camera
            frame = self.region_selector.camera.get_frame()
            if frame is not None:
                self.region_selector.current_frame = frame
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                from PyQt5.QtGui import QImage, QPixmap
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                self.region_selector.pixmap_item.setPixmap(pixmap)
                self.region_selector.scene.setSceneRect(0, 0, w, h)
                self.region_selector.view.resetTransform()
                self.region_selector.view.scale(self.zoom_factor, self.zoom_factor)
            
            # Sau khi hiển thị hình ảnh, dừng camera để không tiếp tục cập nhật
            self.region_selector.camera.stop()
            
            # Enable các nút liên quan đến camera
            self.ui.liveCamera.setEnabled(True)
            self.ui.triggerCamera.setEnabled(True)
            
            # Chuyển qua tab Settings để người dùng chỉnh sửa
            self.ui.paletteTab.setCurrentIndex(1)
            
            # Trước khi hiển thị setting, đảm bảo UI đã được cập nhật
            from PyQt5.QtCore import QCoreApplication
            QCoreApplication.processEvents()
            
            # Chọn tool mới thêm để hiển thị setting
            tool_index = self.job_model.item(job_row, 0).rowCount() - 1
            tool_model_index = self.job_model.item(job_row, 0).child(tool_index).index()
            self.ui.jobView.setCurrentIndex(tool_model_index)
            
            # Đảm bảo UI đã được cập nhật trước khi hiển thị setting
            QCoreApplication.processEvents()
            
            # Hiển thị setting
            self.show_selected_tool_setting(job_row, tool_index)
            
            # Lưu thông tin để apply setting sau này
            self.current_edit_job_row = job_row
            self.current_edit_tool_index = tool_index
            
            # Đóng chế độ chọn tool
            self.cancel_tool_selection()
            
            return
            
        # Thêm các tool khác...
        tool_name = self.ui.toolView.currentIndex().data()
        if not tool_name:
            QMessageBox.warning(self, "Chọn Tool", "Hãy chọn một tool để thêm.")
            return
        roi_tuple = self.region_selector.current_frame is not None and self.region_selector.get_selected_roi() or None
        roi_str = str(roi_tuple) if roi_tuple else ""
        tool_item = QStandardItem(f"{tool_name} (Chưa cấu hình)")  # Đánh dấu chưa cấu hình
        tool_item.setEditable(False)
        roi_item = QStandardItem(roi_str)
        self.job_model.item(job_row, 0).appendRow([tool_item, roi_item])
        
        # Thêm tool vào jobs với trạng thái pending
        tool_data = {
            "name": tool_name, 
            "roi": roi_tuple,
            "pending": True  # Đánh dấu là chưa hoàn tất cấu hình
        }
        self.jobs[job_row]["tools"].append(tool_data)
        
        # Chuyển qua tab Settings
        self.ui.paletteTab.setCurrentIndex(1)
        
        # Chọn tool mới thêm để hiển thị setting
        tool_index = self.job_model.item(job_row, 0).rowCount() - 1
        tool_model_index = self.job_model.item(job_row, 0).child(tool_index).index()
        self.ui.jobView.setCurrentIndex(tool_model_index)
        self.show_selected_tool_setting(job_row, tool_index)
        
        # Lưu thông tin để apply setting sau này
        self.current_edit_job_row = job_row
        self.current_edit_tool_index = tool_index
        
        self.cancel_tool_selection()
        self.update_tool_arrows(job_row)

    def show_selected_tool_setting(self, job_row, tool_index):
        """Hiển thị setting cho tool được chọn trong job"""
        if job_row < 0 or job_row >= len(self.jobs):
            return
        if tool_index < 0 or tool_index >= len(self.jobs[job_row]["tools"]):
            return
            
        tool = self.jobs[job_row]["tools"][tool_index]
        tool_name = tool.get("name")
        self.show_tool_setting(tool_name, tool)

    def show_tool_setting(self, tool_name, tool_data=None):
        # Safety check - make sure settingFrame exists
        if not hasattr(self, "ui") or not hasattr(self.ui, "settingFrame"):
            return
            
        # Safely access the layout
        try:
            layout = self.ui.settingLayout
            # Clear existing widgets from the layout
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        except (AttributeError, RuntimeError):
            print("Warning: Could not access or clear settingLayout")
            return
            
        self.current_setting_frame = None
        self.current_tool_name = tool_name
        
        # Make sure settingFrame still exists before making it visible
        try:
            self.ui.settingFrame.setVisible(True)
            self.ui.applySettingButton.setVisible(True)
            self.ui.cancleSettingButton.setVisible(True)
        except (AttributeError, RuntimeError):
            print("Warning: Could not show setting UI elements")
            return
        
        # Create specific settings UI for the tool
        if tool_name == "Image source":
            try:
                from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout, QSlider, QLineEdit
                frame = QFrame(self.ui.settingFrame)  # Make it a child of settingFrame
                vbox = QVBoxLayout(frame)
                
                # Lấy giá trị cấu hình hiện tại nếu có
                config = tool_data.get("config", {}) if tool_data else {}
                exposure = config.get("exposure", 10000)
                gain = config.get("gain", 1)
                ev = config.get("ev", 0)
                
                # Exposure
                hbox_exp = QHBoxLayout()
                lbl_exp = QLabel("Exposure")
                slider_exp = QSlider(Qt.Horizontal)
                slider_exp.setMinimum(100)
                slider_exp.setMaximum(30000)
                slider_exp.setValue(exposure)
                edit_exp = QLineEdit(str(exposure))
                hbox_exp.addWidget(lbl_exp)
                hbox_exp.addWidget(slider_exp)
                hbox_exp.addWidget(edit_exp)
                vbox.addLayout(hbox_exp)
                
                # Gain
                hbox_gain = QHBoxLayout()
                lbl_gain = QLabel("Gain")
                slider_gain = QSlider(Qt.Horizontal)
                slider_gain.setMinimum(1)
                slider_gain.setMaximum(32)
                slider_gain.setValue(gain)
                edit_gain = QLineEdit(str(gain))
                hbox_gain.addWidget(lbl_gain)
                hbox_gain.addWidget(slider_gain)
                hbox_gain.addWidget(edit_gain)
                vbox.addLayout(hbox_gain)
                
                # EV
                hbox_ev = QHBoxLayout()
                lbl_ev = QLabel("EV")
                slider_ev = QSlider(Qt.Horizontal)
                slider_ev.setMinimum(-8)
                slider_ev.setMaximum(8)
                slider_ev.setValue(ev)
                edit_ev = QLineEdit(str(ev))
                hbox_ev.addWidget(lbl_ev)
                hbox_ev.addWidget(slider_ev)
                hbox_ev.addWidget(edit_ev)
                vbox.addLayout(hbox_ev)
                
                # Đồng bộ slider <-> edit
                slider_exp.valueChanged.connect(lambda v: edit_exp.setText(str(v)))
                edit_exp.editingFinished.connect(lambda: slider_exp.setValue(int(edit_exp.text()) if edit_exp.text().isdigit() else slider_exp.value()))
                slider_gain.valueChanged.connect(lambda v: edit_gain.setText(str(v)))
                edit_gain.editingFinished.connect(lambda: slider_gain.setValue(int(edit_gain.text()) if edit_gain.text().isdigit() else slider_gain.value()))
                slider_ev.valueChanged.connect(lambda v: edit_ev.setText(str(v)))
                edit_ev.editingFinished.connect(lambda: slider_ev.setValue(int(edit_ev.text()) if edit_ev.text().lstrip('-').isdigit() else slider_ev.value()))
                
                # Lưu tham chiếu để lấy giá trị khi apply
                self.setting_config = {
                    "exposure_slider": slider_exp,
                    "gain_slider": slider_gain,
                    "ev_slider": slider_ev,
                    "exposure_edit": edit_exp,
                    "gain_edit": edit_gain,
                    "ev_edit": edit_ev
                }
                
                # Lưu trữ job row và tool index đang chỉnh sửa
                selected_indexes = self.ui.jobView.selectedIndexes()
                if selected_indexes and selected_indexes[0].parent().isValid():
                    index = selected_indexes[0]
                    self.current_edit_job_row = index.parent().row()
                    self.current_edit_tool_index = index.row()
                
                self.current_setting_frame = frame
                layout.addWidget(frame)
            except Exception as e:
                print(f"Error creating Image source settings: {e}")
        # ...có thể mở rộng cho các tool khác...
        else:
            self.current_setting_frame = None
            
            # If no specific settings for this tool, hide the panels
            try:
                self.ui.settingFrame.setVisible(False)
                self.ui.applySettingButton.setVisible(False)
                self.ui.cancleSettingButton.setVisible(False)
            except (AttributeError, RuntimeError):
                print("Warning: Could not hide setting UI elements")

    def apply_tool_setting(self):
        # Lưu cấu hình tool vào jobs
        if not hasattr(self, "current_edit_job_row") or not hasattr(self, "current_edit_tool_index"):
            return
            
        job_row = self.current_edit_job_row
        tool_index = self.current_edit_tool_index
        
        if job_row < 0 or job_row >= len(self.jobs) or tool_index < 0 or tool_index >= len(self.jobs[job_row]["tools"]):
            return
            
        if self.current_tool_name == "Image source":
            # Lấy giá trị cấu hình
            exposure = self.setting_config["exposure_slider"].value()
            gain = self.setting_config["gain_slider"].value()
            ev = self.setting_config["ev_slider"].value()
            
            # Cập nhật config trong jobs
            self.jobs[job_row]["tools"][tool_index]["config"] = {
                "exposure": exposure,
                "gain": gain,
                "ev": ev
            }
            
            # Đánh dấu là đã hoàn tất cấu hình
            self.jobs[job_row]["tools"][tool_index]["pending"] = False
            
            # Cập nhật tên tool trong treeview (bỏ dấu chưa cấu hình)
            tool_name = self.jobs[job_row]["tools"][tool_index]["name"]
            source = self.jobs[job_row]["tools"][tool_index]["source"]
            tool_item = self.job_model.item(job_row, 0).child(tool_index, 0)
            if tool_item:
                n = self.job_model.item(job_row, 0).rowCount()
                arrow = "→" if tool_index < n - 1 else ""
                tool_item.setText(f"{tool_name} ({source}) {arrow}")
            
            # Hiển thị lại hình ảnh từ camera với cài đặt mới
            source = self.jobs[job_row]["tools"][tool_index]["source"]
            self.set_region_selector_camera(source)
            if self.region_selector.camera:
                # Áp dụng cài đặt mới
                self.region_selector.camera.set_exposure_time(exposure)
                if hasattr(self.region_selector.camera, "set_gain"):
                    self.region_selector.camera.set_gain(gain)
                if hasattr(self.region_selector.camera, "set_ev"):
                    self.region_selector.camera.set_ev(ev)
                
                # Bật camera và chụp ảnh mới
                self.region_selector.camera.start()
                if self.region_selector.camera.available:
                    frame = self.region_selector.camera.get_frame()
                    if frame is not None:
                        self.region_selector.current_frame = frame
                        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = rgb_image.shape
                        bytes_per_line = ch * w
                        from PyQt5.QtGui import QImage, QPixmap
                        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                        pixmap = QPixmap.fromImage(qt_image)
                        self.region_selector.pixmap_item.setPixmap(pixmap)
                        self.region_selector.scene.setSceneRect(0, 0, w, h)
                        self.region_selector.view.resetTransform()
                        self.region_selector.view.scale(self.zoom_factor, self.zoom_factor)
                    self.region_selector.camera.stop()
            
            QMessageBox.information(self, "Áp dụng cấu hình", "Đã áp dụng thành công cấu hình cho tool.")
            
            # Hide settings after apply
            self.ui.settingFrame.setVisible(False)
            self.ui.applySettingButton.setVisible(False)
            self.ui.cancleSettingButton.setVisible(False)
        else:
            # Đánh dấu là đã hoàn tất cấu hình
            self.jobs[job_row]["tools"][tool_index]["pending"] = False
            
            # Cập nhật tên tool trong treeview (bỏ dấu chưa cấu hình)
            tool_name = self.jobs[job_row]["tools"][tool_index]["name"]
            tool_item = self.job_model.item(job_row, 0).child(tool_index, 0)
            if tool_item:
                n = self.job_model.item(job_row, 0).rowCount()
                arrow = "→" if tool_index < n - 1 else ""
                tool_item.setText(f"{tool_name} {arrow}")
            
            QMessageBox.information(self, "Áp dụng cấu hình", "Đã áp dụng thành công cấu hình cho tool.")
            
            # Hide settings after apply
            self.ui.settingFrame.setVisible(False)
            self.ui.applySettingButton.setVisible(False)
            self.ui.cancleSettingButton.setVisible(False)

    def cancel_tool_setting(self):
        self.clear_tool_setting()
        self.ui.addTool.setEnabled(False)
        
        # Hide settings panel
        self.ui.settingFrame.setVisible(False)
        self.ui.applySettingButton.setVisible(False)
        self.ui.cancleSettingButton.setVisible(False)

    def cancel_tool_selection(self):
        # Đưa toolView về danh sách tool gốc, tắt enable các nút, xóa cấu hình setting
        self.ui.toolView.setModel(self.tool_model)
        self.ui.addTool.setEnabled(False)
        self.ui.cancleTool.setEnabled(False)
        self.ui.toolView.clearSelection()
        self.clear_tool_setting()
        # Kết nối lại sự kiện chọn tool
        self.ui.toolView.clicked.disconnect()
        self.ui.toolView.clicked.connect(self.on_tool_selected)

    def update_tool_arrows(self, job_row):
        # Cập nhật lại mũi tên cho các tool trong job
        job_item = self.job_model.item(job_row, 0)
        if job_item is None:
            return
        n = job_item.rowCount()
        for idx in range(n):
            tool_item = job_item.child(idx, 0)
            if tool_item:
                arrow = "→" if idx < n - 1 else ""
                # Hiển thị tên tool kèm mũi tên
                tool_name = self.jobs[job_row]["tools"][idx].get("name", "")
                source = self.jobs[job_row]["tools"][idx].get("source", "")
                if tool_name == "Image source" and source:
                    tool_item.setText(f"{tool_name} ({source}) {arrow}")
                else:
                    tool_item.setText(f"{tool_name} {arrow}")

    def reload_job_tree(self):
        self.job_model.clear()
        self.job_model.setHorizontalHeaderLabels(["Job/Tool", "ROI"])
        for job_idx, job in enumerate(self.jobs):
            job_item = QStandardItem(job.get("name", ""))
            job_item.setEditable(False)
            roi_item = QStandardItem("")
            self.job_model.appendRow([job_item, roi_item])
            for tool in job.get("tools", []):
                tool_name = tool.get("name", "")
                source = tool.get("source", "")
                roi_tuple = tool.get("roi", None)
                roi_str = str(roi_tuple) if roi_tuple else ""
                if tool_name == "Image source" and source:
                    tool_item = QStandardItem(f"{tool_name} ({source})")
                else:
                    tool_item = QStandardItem(tool_name)
                tool_item.setEditable(False)
                roi_item = QStandardItem(roi_str)
                job_item.appendRow([tool_item, roi_item])
            self.update_tool_arrows(job_idx)

    def on_job_view_clicked(self, index):
        if index.parent().isValid():
            # Đây là một tool, hiển thị setting của tool
            job_row = index.parent().row()
            tool_index = index.row()
            self.show_selected_tool_setting(job_row, tool_index)
            
            # Lưu thông tin để apply setting sau này
            self.current_edit_job_row = job_row
            self.current_edit_tool_index = tool_index
            
            # Show settings panel
            self.ui.settingFrame.setVisible(True)
            self.ui.applySettingButton.setVisible(True)
            self.ui.cancleSettingButton.setVisible(True)
        else:
            # Đây là một job, clear setting
            self.clear_tool_setting()
            
            # Hide settings panel
            self.ui.settingFrame.setVisible(False)
            self.ui.applySettingButton.setVisible(False)
            self.ui.cancleSettingButton.setVisible(False)