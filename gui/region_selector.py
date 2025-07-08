from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QTimer
from camera.camera_stream import CameraStream
from detection.edge_detection import detect_edges
import cv2

class RegionSelectorWidget(QWidget):
    def __init__(self, camera_index=0):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.view = QGraphicsView()
        self.scene = QGraphicsScene(self)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        self.view.setScene(self.scene)
        self.layout.addWidget(self.view)

        self.camera = CameraStream(src=camera_index, use_picamera=True)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.current_frame = None
        self.edge_detection_enabled = False

    def start_camera(self):
        self.camera.start()
        self.timer.start(30)

    def set_edge_detection(self, enabled: bool):
        self.edge_detection_enabled = enabled

    def update_frame(self):
        frame = self.camera.get_frame()
        if frame is not None:
            self.current_frame = frame
            if self.edge_detection_enabled:
                edges = detect_edges(frame)
                rgb_image = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
            else:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            self.pixmap_item.setPixmap(pixmap)
            self.scene.setSceneRect(0, 0, w, h)

    def get_selected_roi(self):
        # TODO: Implement actual ROI selection logic
        return None