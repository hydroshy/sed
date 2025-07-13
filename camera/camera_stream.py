import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from picamera2 import Picamera2

class CameraStream(QObject):
    frame_ready = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.picam2 = Picamera2()
        self.timer = QTimer()
        self.timer.timeout.connect(self._query_frame)
        self.is_live = False
        # Đặt độ phân giải đồng bộ cho cả preview và still
        self.frame_size = (1440, 1080)  # Crop nhỏ để tăng fps, bạn có thể chỉnh lại
        # Đặt FrameRate cao cho Global Shutter (nếu camera hỗ trợ)
        self.preview_config = self.picam2.create_preview_configuration(
            main={"size": self.frame_size},
            controls={"FrameRate": 60}
        )
        self.still_config = self.picam2.create_still_configuration(main={"size": self.frame_size})
        self.picam2.configure(self.preview_config)

    def start_live(self):
        if not self.is_live:
            self.picam2.stop()
            self.picam2.configure(self.preview_config)
            self.picam2.start()
            self.timer.start(1)  # 5 ms ~ 200 FPS (nếu phần cứng hỗ trợ)
            self.is_live = True

    def stop_live(self):
        if self.timer.isActive():
            self.timer.stop()
        if self.is_live:
            self.picam2.stop()
            self.is_live = False

    def _query_frame(self):
        frame = self.picam2.capture_array()
        if frame is not None:
            self.frame_ready.emit(frame)

    def trigger_capture(self):
        # Chuyển sang chế độ still, chụp ảnh, sau đó về preview
        was_live = self.is_live
        self.picam2.stop()
        self.picam2.configure(self.still_config)
        self.picam2.start()
        frame = self.picam2.capture_array()
        if frame is not None:
            self.frame_ready.emit(frame)
        self.picam2.stop()
        self.picam2.configure(self.preview_config)
        if was_live:
            self.picam2.start()

    def set_zoom(self, value):
        pass  # Có thể cấu hình zoom qua Picamera2 nếu cần

    def set_focus(self, value):
        pass  # Có thể cấu hình focus qua Picamera2 nếu cần

    def set_exposure(self, value):
        pass

    def set_gain(self, value):
        pass

    def set_ev(self, value):
        pass
