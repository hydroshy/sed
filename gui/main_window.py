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
        self.ui.addTool.clicked.connect(self.add_tool)
        # Không tạo lại cancleTool, chỉ kết nối sự kiện và disable ban đầu
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
        self.ui.addTool.setEnabled(True)
        self.ui.cancleTool.setEnabled(True)
        if tool_name == "Image source":
            # Lấy danh sách nguồn camera thực tế từ tool_selector
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
        # Khi chọn nguồn camera, enable addTool/cancleTool
        self.selected_source = index.data()
        self.ui.addTool.setEnabled(True)
        self.ui.cancleTool.setEnabled(True)

    def cancel_tool_selection(self):
        # Reset lại toolView về danh sách tool gốc
        self.ui.toolView.setModel(self.tool_model)
        self.ui.addTool.setEnabled(False)
        self.ui.cancleTool.setEnabled(False)
        self.ui.toolView.clearSelection()
        # Kết nối lại sự kiện chọn tool
        self.ui.toolView.clicked.disconnect()
        self.ui.toolView.clicked.connect(self.on_tool_selected)

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
            tool_item = QStandardItem(f"{tool_name} ({source})")
            tool_item.setEditable(False)
            roi_item = QStandardItem(roi_str)
            self.job_model.item(job_row, 0).appendRow([tool_item, roi_item])
            self.jobs[job_row]["tools"].append({"name": tool_name, "source": source, "roi": roi_tuple})
            # Nếu là job đầu tiên và tool đầu tiên là Image source thì enable live/triggerCamera
            if job_row == 0 and len(self.jobs[0]["tools"]) == 1 and tool_name == "Image source":
                self.ui.liveCamera.setEnabled(True)
                self.ui.triggerCamera.setEnabled(True)
            self.cancel_tool_selection()
            self.update_tool_arrows(job_row)
            return
        # Thêm tool vào job đang chọn, kèm ROI
        tool_name = self.ui.toolView.currentIndex().data()
        if not tool_name:
            QMessageBox.warning(self, "Chọn Tool", "Hãy chọn một tool để thêm.")
            return
        roi_tuple = self.region_selector.current_frame is not None and self.region_selector.get_selected_roi() or None
        roi_str = str(roi_tuple) if roi_tuple else ""
        tool_item = QStandardItem(tool_name)
        tool_item.setEditable(False)
        roi_item = QStandardItem(roi_str)
        self.job_model.item(job_row, 0).appendRow([tool_item, roi_item])
        self.jobs[job_row]["tools"].append({"name": tool_name, "roi": roi_tuple})
        self.cancel_tool_selection()
        self.update_tool_arrows(job_row)

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