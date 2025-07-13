from camera.camera_stream import CameraStream
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsView, QPushButton, QSlider, QLineEdit, QProgressBar, QLCDNumber, QTabWidget, QListView, QTreeView
import numpy as np
import cv2
from PyQt5.QtWidgets import QMainWindow
from PyQt5 import uic
import os

class MainWindow(QMainWindow):
    def __init__(self):
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
        # FPS counter
        self._fps_count = 0
        self._fps_last_update = 0
        self._fps_value = 0
        from PyQt5.QtCore import QTimer
        self._fps_timer = QTimer()
        self._fps_timer.timeout.connect(self._update_fps_display)
        self._fps_timer.start(1000)  # update mỗi giây

        self.paletteTab = self.findChild(QTabWidget, 'paletteTab')
        self.jobTab = self.findChild(QTreeView, 'jobTab')  # jobTab là QWidget, nhưng jobView là QTreeView
        self.jobView = self.findChild(QTreeView, 'jobView')
        self.removeJob = self.findChild(QPushButton, 'removeJob')
        self.editJob = self.findChild(QPushButton, 'editJob')
        self.addJob = self.findChild(QPushButton, 'addJob')
        self.loadJob = self.findChild(QPushButton, 'loadJob')
        self.saveJob = self.findChild(QPushButton, 'saveJob')

        self.toolView = self.findChild(QListView, 'toolView')
        self.addTool = self.findChild(QPushButton, 'addTool')
        self.cancleTool = self.findChild(QPushButton, 'cancleTool')

        self.exposureEdit = self.findChild(QLineEdit, 'exposureEdit')
        self.exposureSlider = self.findChild(QSlider, 'exposureSlider')
        self.gainEdit = self.findChild(QLineEdit, 'gainEdit')
        self.gainSlider = self.findChild(QSlider, 'gainSlider')
        self.evEdit = self.findChild(QLineEdit, 'evEdit')
        self.evSlider = self.findChild(QSlider, 'evSlider')
        self.applySetting = self.findChild(QPushButton, 'applySetting')
        self.cancleSetting = self.findChild(QPushButton, 'cancleSetting')

        # Các nút mode
        self.triggerCameraMode = self.findChild(QPushButton, 'triggerCameraMode')
        self.liveCameraMode = self.findChild(QPushButton, 'liveCameraMode')

        # TODO: Kết nối signal-slot cho các nút, slider, v.v.


        # Khởi tạo camera stream
        self.camera_stream = CameraStream()
        self.camera_stream.frame_ready.connect(self.display_frame)

        # Zoom state
        self.zoom_level = 1.0
        self.max_zoom = 3.0
        self.min_zoom = 1.0
        self.zoom_step = 0.1
        self.current_frame = None  # Lưu frame cuối cùng để zoom lại

        # Kết nối nút
        self.liveCamera.setCheckable(True)
        self.liveCamera.clicked.connect(self.toggle_live_camera)
        self.triggerCamera.clicked.connect(self.camera_stream.trigger_capture)
        self.zoomIn.clicked.connect(self.zoom_in)
        self.zoomOut.clicked.connect(self.zoom_out)
        self.liveCamera.setEnabled(True)
        self.triggerCamera.setEnabled(True)
        self.zoomIn.setEnabled(True)
        self.zoomOut.setEnabled(True)

    def toggle_live_camera(self):
        if self.liveCamera.isChecked():
            self.camera_stream.start_live()
            self.triggerCamera.setEnabled(False)
            self.liveCamera.setText("Stop Live Camera")
        else:
            self.camera_stream.stop_live()
            self.triggerCamera.setEnabled(True)
            self.liveCamera.setText("Live Camera")

    def display_frame(self, frame):
        self.current_frame = frame.copy()  # Lưu lại frame cuối cùng
        self._show_frame_with_zoom()
        # Tính sharpness bằng variance of Laplacian
        import cv2
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        # Chuẩn hóa về 0-100 (giới hạn max cho mượt)
        sharpness_norm = min(int(sharpness / 10), 100)
        self.focusBar.setValue(sharpness_norm)
        # FPS counter
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
            return
        frame = self.current_frame.copy()
        h, w, _ = frame.shape
        if self.zoom_level > 1.0:
            center_x, center_y = w // 2, h // 2
            new_w = int(w / self.zoom_level)
            new_h = int(h / self.zoom_level)
            x1 = max(center_x - new_w // 2, 0)
            y1 = max(center_y - new_h // 2, 0)
            x2 = min(center_x + new_w // 2, w)
            y2 = min(center_y + new_h // 2, h)
            frame = frame[y1:y2, x1:x2]
            frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        self.cameraView.setSceneRect(0, 0, w, h)
        from PyQt5.QtWidgets import QGraphicsScene
        scene = QGraphicsScene()
        scene.addPixmap(pixmap)
        self.cameraView.setScene(scene)

    def zoom_in(self):
        if self.zoom_level < self.max_zoom:
            self.zoom_level += self.zoom_step
            self._show_frame_with_zoom()

    def zoom_out(self):
        if self.zoom_level > self.min_zoom:
            self.zoom_level -= self.zoom_step
            self._show_frame_with_zoom()
