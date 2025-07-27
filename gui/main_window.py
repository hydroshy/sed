from camera.camera_stream import CameraStream
from PyQt5.QtGui import QImage, QPixmap, QIntValidator, QDoubleValidator
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsScene,QGraphicsPixmapItem,QWidget,QStackedWidget,QComboBox,QGraphicsView, QPushButton, QSlider, QLineEdit, QProgressBar, QLCDNumber, QTabWidget, QListView, QTreeView
import numpy as np
import cv2
from PyQt5.QtWidgets import QMainWindow, QPushButton
from PyQt5 import uic
import os
from job.job_manager import JobManager, Tool, Job
from PyQt5.QtCore import QStringListModel
from detection.ocr_tool import OcrTool
from PyQt5.QtGui import QPen, QColor, QPainter, QFont
import logging

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
        self.stackedWidget = self.findChild(QStackedWidget, 'stackedWidget')
        self.detectSettingPage = self.findChild(QWidget, 'detectSettingPage')
        self.defectSettingPage = self.findChild(QWidget, 'defectSettingPage')
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
        self.applySetting = self.findChild(QPushButton, 'applySetting')
        self.cancleSetting = self.findChild(QPushButton, 'cancleSetting')
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
        self.camera_stream.frame_ready.connect(self.display_frame)

        # Khởi tạo mặc định auto exposure sau khi đã có camera_stream
        self.set_auto_exposure_mode()

        # Zoom/rotate state
        self.zoom_level = 1.0
        self.zoom_step = 0.1
        self.current_frame = None
        self.rotation_angle = 0  # Góc xoay hiện tại

        # Kết nối nút
        # Kết nối signal cho các tham số camera
        self.setup_camera_param_signals()
        self.liveCamera.setCheckable(True)
        self.liveCamera.clicked.connect(self.toggle_live_camera)
        self.triggerCamera.clicked.connect(self.camera_stream.trigger_capture)
        self.zoomIn.clicked.connect(self.zoom_in)
        self.zoomOut.clicked.connect(self.zoom_out)
        self.liveCamera.setEnabled(True)
        self.triggerCamera.setEnabled(True)
        self.zoomIn.setEnabled(True)
        self.zoomOut.setEnabled(True)
        if self.rotateLeft:
            self.rotateLeft.clicked.connect(self.rotate_left)
            self.rotateLeft.setEnabled(True)
        if self.rotateRight:
            self.rotateRight.clicked.connect(self.rotate_right)
            self.rotateRight.setEnabled(True)

        # Pan/drag state for cameraView
        self._is_panning = False
        self._pan_start_pos = None
        self._scene_offset = [0, 0]
        self._scene_offset_max = [0, 0]
        # Enable dragging for cameraView
        self.cameraView.setDragMode(QGraphicsView.ScrollHandDrag)
        self.cameraView.viewport().setCursor(Qt.OpenHandCursor)
        self.cameraView.viewport().installEventFilter(self)

        # Initialize fit-on-next-frame flag
        self._fit_on_next_frame = False

        # Initialize the QGraphicsScene for the camera view
        self._scene = QGraphicsScene()
        self.cameraView.setScene(self._scene)

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
        # Lấy tên tool được chọn từ ComboBox
        tool_name = self.toolComboBox.currentText() if self.toolComboBox else None
        if not tool_name:
            return
        # Nếu chưa có job, tạo job mới
        if not self.job_manager.get_current_job():
            job = Job('Job 1')
            self.job_manager.add_job(job)
        # Thêm tool vào job hiện tại
        self.job_manager.get_current_job().add_tool(Tool(tool_name))
        self._update_job_view()
        # Nếu là Detect Tool hoặc Defect Detection thì chuyển sang detectSettingPage
        if tool_name in ("Detect Tool", "Defect Detection") and self.stackedWidget and self.detectSettingPage:
            index = self.stackedWidget.indexOf(self.detectSettingPage)
            if index != -1:
                self.stackedWidget.setCurrentIndex(index)

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
        # Không can thiệp vào toolComboBox, giữ nguyên các item mặc định từ file .ui
        # Chỉ cập nhật jobView
        self._update_job_view()




    def _update_job_view(self):
        job = self.job_manager.get_current_job()
        if job:
            tool_names = [tool.name for tool in job.tools]
        else:
            tool_names = []
        self.job_model = QStringListModel(tool_names)
        self.jobView.setModel(self.job_model)

    def _on_add_tool(self):
        # Lấy tool được chọn từ ComboBox
        tool_name = self.toolComboBox.currentText() if self.toolComboBox else None
        if not tool_name:
            return
        # Nếu chưa có job, tạo job mới
        if not self.job_manager.get_current_job():
            job = Job('Job 1')
            self.job_manager.add_job(job)
        # Thêm tool vào job hiện tại
        self.job_manager.get_current_job().add_tool(Tool(tool_name))
        self._update_job_view()

    def rotate_left(self):
        self.rotation_angle = (self.rotation_angle - 90) % 360
        self._show_frame_with_zoom()

    def rotate_right(self):
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self._show_frame_with_zoom()
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Nếu đang ở chế độ fit, fit lại khi resize cửa sổ
        if self._fit_on_next_frame:
            self.cameraView.fitInView(self.cameraView.sceneRect(), Qt.KeepAspectRatio)
            self._fit_on_next_frame = False
    # Đã hợp nhất các hàm __init__ thành 1 hàm duy nhất phía trên
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
        if frame is None or frame.size == 0:
            logging.error("Invalid frame received")
            return

        logging.debug("Frame received with shape: %s", frame.shape)

        # Handle RGBA format if detected
        if frame.shape[2] == 4:  # RGBA format
            logging.debug("Converting RGBA to RGB")
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)

        self.current_frame = frame  # Avoid unnecessary copy
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
        self._is_auto_exposure = False
        self.camera_stream.set_auto_exposure(False)
        self.exposureEdit.setEnabled(True)
        self.exposureSlider.setEnabled(True)
        if self.manualExposure:
            self.manualExposure.setEnabled(False)
        if self.autoExposure:
            self.autoExposure.setEnabled(True)

    def set_auto_exposure_mode(self):
        self._is_auto_exposure = True
        self.camera_stream.set_auto_exposure(True)
        self.exposureEdit.setEnabled(False)
        self.exposureSlider.setEnabled(False)
        if self.manualExposure:
            self.manualExposure.setEnabled(True)
        if self.autoExposure:
            self.autoExposure.setEnabled(False)

    def run_current_job(self):
        # Chỉ demo cho tool OCR đầu tiên trong job
        job = self.job_manager.get_current_job()
        if not job or not job.tools:
            return
        if self.current_frame is None:
            return
        # Nếu tool đầu tiên là OCR thì chạy nhận diện
        if job.tools[0].name == 'OCR':
            frame = self.current_frame.copy()
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            boxes = self.ocr_tool.detect(rgb)
            self._show_frame_with_ocr_boxes(frame, boxes)

    def _show_frame_with_ocr_boxes(self, frame, boxes):
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        painter = QPainter(pixmap)
        pen = QPen(QColor(0, 255, 0), 2)
        painter.setPen(pen)
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)
        for box in boxes:
            pts = [tuple(map(int, pt)) for pt in box]
            # Draw polygon
            for i in range(4):
                painter.drawLine(pts[i][0], pts[i][1], pts[(i+1)%4][0], pts[(i+1)%4][1])
            # Draw text (demo: chỉ số thứ tự)
            painter.drawText(pts[0][0], pts[0][1]-5, f"Text")
        painter.end()
        from PyQt5.QtWidgets import QGraphicsScene, QGraphicsPixmapItem
        if self._scene is None:
            self._scene = QGraphicsScene()
            self.cameraView.setScene(self._scene)
        self._scene.clear()
        self._pixmap_item = QGraphicsPixmapItem(pixmap)
        self._pixmap_item.setTransformationMode(Qt.SmoothTransformation)
        self._pixmap_item.setTransformOriginPoint(w/2, h/2)
        angle = int(getattr(self, 'rotation_angle', 0)) % 360
        self._pixmap_item.setRotation(angle)
        self._scene.addItem(self._pixmap_item)
        self._scene.setSceneRect(0, 0, w, h)
        self.cameraView.setSceneRect(0, 0, w, h)
        self.cameraView.resetTransform()
        # Ensure self._pixmap_item exists and is added to the scene before centering
        if self._pixmap_item and self._scene and self._pixmap_item.scene() == self._scene:
            self.cameraView.centerOn(self._pixmap_item)
