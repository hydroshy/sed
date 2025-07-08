import cv2

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False

class CameraStream:
    def __init__(self, src=0, use_picamera=True, resolution=(640, 480)):
        self.src = src
        self.use_picamera = use_picamera and PICAMERA2_AVAILABLE
        self.cap = None
        self.camera = None
        self.resolution = resolution

    def start(self):
        if self.use_picamera:
            if self.camera is None:
                self.camera = Picamera2()
                self.camera.configure(self.camera.create_preview_configuration(
                    main={"size": self.resolution, "format": "RGB888"}
                ))
                self.camera.start()

    def get_frame(self):
        if self.use_picamera and self.camera is not None:
            try:
                frame = self.camera.capture_array("main")
                return frame
            except Exception:
                return None
        return None

    def stop(self):
        if self.use_picamera and self.camera is not None:
            self.camera.stop()
            self.camera.close()
            self.camera = None