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
        self.available = False
        self.exposure_time = None  # microseconds

    def start(self):
        self.available = False
        if self.use_picamera:
            try:
                if self.camera is None:
                    print("DEBUG: Khởi tạo Picamera2...")
                    self.camera = Picamera2()
                    config = self.camera.create_preview_configuration(
                        main={"size": self.resolution, "format": "RGB888"}
                    )
                    self.camera.configure(config)
                    self.camera.start()
                    if self.exposure_time is not None:
                        self.set_exposure_time(self.exposure_time)
                self.available = True
            except Exception as e:
                import traceback
                print(f"ERROR: Không thể khởi tạo Picamera2: {e}")
                traceback.print_exc()
                self.available = False
        else:
            print("ERROR: Picamera2 không khả dụng trên hệ thống này.")
            self.available = False

    def set_exposure_time(self, exposure_time_us):
        """Set exposure time in microseconds for Picamera2."""
        self.exposure_time = exposure_time_us
        if self.use_picamera and self.camera is not None:
            try:
                # Picamera2 expects exposure time in microseconds
                controls = {"ExposureTime": int(exposure_time_us)}
                self.camera.set_controls(controls)
            except Exception as e:
                print(f"ERROR: Không thể đặt thời gian phơi sáng: {e}")

    def set_gain(self, gain_value):
        """Set analog gain for Picamera2."""
        if self.use_picamera and self.camera is not None:
            try:
                controls = {"AnalogueGain": float(gain_value)}
                self.camera.set_controls(controls)
            except Exception as e:
                print(f"ERROR: Không thể đặt gain: {e}")

    def set_ev(self, ev_value):
        """Set EV compensation for Picamera2."""
        if self.use_picamera and self.camera is not None:
            try:
                controls = {"ExposureValue": float(ev_value)}
                self.camera.set_controls(controls)
            except Exception as e:
                print(f"ERROR: Không thể đặt EV: {e}")

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
        if self.cap is not None:
            self.cap.release()
            self.cap = None