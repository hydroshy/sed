from PyQt5.QtWidgets import QMainWindow, QMessageBox, QVBoxLayout, QListView, QTreeView, QPushButton, QProgressBar, QFileDialog
from PyQt5.QtCore import QStringListModel, QTimer, Qt
from gui.region_selector import RegionSelectorWidget
from gui.ui_mainwindow import Ui_MainWindow
import cv2
import numpy as np
import time
import json
from detection.edge_detection import detect_edges

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

        # Edge detection toggle button
        self.edge_button = QPushButton("Chế độ phát hiện biên: TẮT", self)
        self.edge_button.setCheckable(True)
        self.edge_button.setGeometry(400, 510, 180, 28)
        self.edge_button.toggled.connect(self.toggle_edge_detection)
        self.edge_button.show()

        # Live/Trigger camera logic
        self.live_mode = False
        self.ui.liveCamera.clicked.connect(self.toggle_live_camera)
        self.ui.triggerCamera.clicked.connect(self.trigger_camera)

        # FocusBar update: Timer to poll focus value
        self.focus_timer = QTimer(self)
        self.focus_timer.timeout.connect(self.update_focus_bar)

        # ToolView: QListView
        # Đảm bảo "Phát hiện biên" (Edge Detection) nằm trong toolView
        self.tool_model = QStringListModel([
            "Phát hiện biên",  # Edge Detection
            "ROI Selector"
            # ...bạn có thể thêm các tool khác ở đây...
        ])
        self.ui.toolView.setModel(self.tool_model)
        self.ui.addTool.clicked.connect(self.add_tool)

        # JobView: QTreeView (dạng cây: job cha, tool con)
        from PyQt5.QtGui import QStandardItemModel, QStandardItem
        self.job_model = QStandardItemModel()
        self.job_model.setHorizontalHeaderLabels(["Job/Tool", "ROI"])
        self.ui.jobView.setModel(self.job_model)
        self.ui.addJob.clicked.connect(self.add_job)
        self.ui.editJob.clicked.connect(self.edit_job)
        self.ui.removeJob.clicked.connect(self.remove_job)
        self.ui.runJob.clicked.connect(self.run_job)
        self.ui.saveJob.clicked.connect(self.save_job_file)
        self.ui.loadJob.clicked.connect(self.load_job_file)

        # Lưu trữ job và tool
        self.jobs = []  # [{name:..., tools:[{name:..., roi:...}, ...]}, ...]

    def toggle_live_camera(self):
        self.live_mode = not self.live_mode
        if self.live_mode:
            self.region_selector.start_camera()
            self.focus_timer.start(200)
            self.ui.liveCamera.setStyleSheet("font-weight: bold; background-color: #4caf50; color: white;")
        else:
            self.region_selector.timer.stop()
            self.focus_timer.stop()
            self.ui.liveCamera.setStyleSheet("")
        self.ui.liveCamera.setText("Live Camera (ON)" if self.live_mode else "Live Camera")

    def trigger_camera(self):
        self.region_selector.camera.start()
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
        self.region_selector.camera.stop()

    def update_focus_bar(self):
        frame = self.region_selector.current_frame
        if frame is not None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            focus_measure = cv2.Laplacian(gray, cv2.CV_64F).var()
            value = min(int(focus_measure / 10), 100)
            self.ui.focusBar.setValue(value)

    def add_job(self):
        from PyQt5.QtGui import QStandardItem
        job_name = f"Job {self.job_model.rowCount()+1}"
        job_item = QStandardItem(job_name)
        job_item.setEditable(False)
        roi_item = QStandardItem("")
        self.job_model.appendRow([job_item, roi_item])
        self.jobs.append({"name": job_name, "tools": []})

    def add_tool(self):
        # Thêm tool vào job đang chọn, kèm ROI
        from PyQt5.QtGui import QStandardItem
        selected_indexes = self.ui.jobView.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Chọn Job", "Hãy chọn một job để thêm tool.")
            return
        job_index = selected_indexes[0]
        if job_index.parent().isValid():
            job_index = job_index.parent()  # Đảm bảo chọn node cha (job)
        job_row = job_index.row()
        tool_name = self.ui.toolView.currentIndex().data()
        if not tool_name:
            QMessageBox.warning(self, "Chọn Tool", "Hãy chọn một tool để thêm.")
            return
        roi = self.region_selector.view.scene().selectedItems()  # Không dùng, lấy ROI từ widget
        roi_tuple = self.region_selector.current_frame is not None and self.region_selector.get_selected_roi() or None
        roi_str = str(roi_tuple) if roi_tuple else ""
        tool_item = QStandardItem(tool_name)
        tool_item.setEditable(False)
        roi_item = QStandardItem(roi_str)
        self.job_model.item(job_row, 0).appendRow([tool_item, roi_item])
        # Lưu vào jobs
        self.jobs[job_row]["tools"].append({"name": tool_name, "roi": roi_tuple})

    def edit_job(self):
        # Có thể mở rộng để sửa tên job/tool hoặc ROI
        pass

    def remove_job(self):
        selected_indexes = self.ui.jobView.selectedIndexes()
        if not selected_indexes:
            return
        index = selected_indexes[0]
        if not index.parent().isValid():
            # Xóa job
            self.job_model.removeRow(index.row())
            del self.jobs[index.row()]
        else:
            # Xóa tool trong job
            parent = index.parent()
            self.job_model.item(parent.row(), 0).removeRow(index.row())
            del self.jobs[parent.row()]["tools"][index.row()]

    def run_job(self):
        # Thực thi tuần tự các tool trong job được chọn, đo thời gian
        from PyQt5.QtGui import QStandardItem
        selected_indexes = self.ui.jobView.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Chọn Job", "Hãy chọn một job để chạy.")
            return
        job_index = selected_indexes[0]
        if job_index.parent().isValid():
            job_index = job_index.parent()
        job_row = job_index.row()
        job = self.jobs[job_row]
        tools = job["tools"]
        if not tools:
            QMessageBox.warning(self, "Không có tool", "Job này chưa có tool nào.")
            return

        total_time = 0.0
        tool_times = []
        for idx, tool in enumerate(tools):
            start = time.time()
            # Thực thi tool (ví dụ: phát hiện biên)
            if tool["name"] == "Phát hiện biên":
                frame = self.region_selector.current_frame
                if frame is not None:
                    _ = detect_edges(frame)
            # Có thể mở rộng thêm các tool khác ở đây
            elapsed = time.time() - start
            tool_times.append(elapsed)
            total_time += elapsed

            # Hiển thị mũi tên thứ tự trong QTreeView (bằng cách cập nhật text)
            tool_item = self.job_model.item(job_row, 0).child(idx, 0)
            if tool_item:
                arrow = "→" if idx < len(tools) - 1 else ""
                tool_item.setText(f"{tool['name']} {arrow}")

        # Hiển thị tổng thời gian thực thi lên LCDNumber
        self.ui.executionTime.display(f"{total_time:.3f}")

    def save_job_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Job File", "", "SED Job Files (*.sedjob)")
        if not path:
            return
        if not path.endswith(".sedjob"):
            path += ".sedjob"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.jobs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu file: {e}")

    def load_job_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Job File", "", "SED Job Files (*.sedjob)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                jobs = json.load(f)
            self.jobs = jobs
            self.reload_job_tree()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tải file: {e}")

    def reload_job_tree(self):
        # Xóa model cũ
        self.job_model.removeRows(0, self.job_model.rowCount())
        for job in self.jobs:
            from PyQt5.QtGui import QStandardItem
            job_item = QStandardItem(job["name"])
            job_item.setEditable(False)
            roi_item = QStandardItem("")
            self.job_model.appendRow([job_item, roi_item])
            for tool in job.get("tools", []):
                tool_item = QStandardItem(tool["name"])
                tool_item.setEditable(False)
                roi_item = QStandardItem(str(tool.get("roi", "")))
                job_item.appendRow([tool_item, roi_item])