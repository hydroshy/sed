# -*- coding: utf-8 -*-
# Ưu tiên sử dụng stub pykms nếu có (tránh lỗi import pykms)
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "stubs")))

# Giảm ồn log libcamera (tránh spam khi chỉ là timeout do chưa có frame)
os.environ.setdefault("LIBCAMERA_LOG_LEVELS", "*:ERROR")

import time
import numpy as np
import argparse
from PyQt5 import QtCore, QtGui, QtWidgets

# Đặt XDG_RUNTIME_DIR trước khi import Picamera2 để tránh cảnh báo Qt
def ensure_xdg_runtime_dir():
    xdg = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    try:
        st = os.stat(xdg)
        if (st.st_mode & 0o777) != 0o700:
            raise PermissionError("bad mode")
    except Exception:
        xdg = f"/tmp/xdg-runtime-{os.getuid()}"
        os.makedirs(xdg, exist_ok=True)
        os.chmod(xdg, 0o700)
    os.environ["XDG_RUNTIME_DIR"] = xdg

ensure_xdg_runtime_dir()
from picamera2 import Picamera2

class StreamWorker(QtCore.QObject):
    frame_ready = QtCore.pyqtSignal(QtGui.QImage, dict)
    info = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)

    def __init__(self, size=(1280, 720), target_fps=30.0,
                 # —— Tham số 3A (đặt mặc định hợp lý) ——
                 ae_enable=False, awb_enable=False,
                 exposure_us=5000, gain=1.5, colour_gains=(1.8, 1.8),
                 prime_lock=False, prime_ms=400):
        super().__init__()
        self.size = size
        self.target_fps = float(target_fps)
        self._running = False
        self._cancelled = False
        self.rx_id = 0
        self.picam2 = None

        # 3A & tham số cố định
        self.ae_enable = bool(ae_enable)
        self.awb_enable = bool(awb_enable)
        self.exposure_us = int(max(1, exposure_us))
        self.gain = float(max(0.0, gain))
        self.colour_gains = (float(colour_gains[0]), float(colour_gains[1]))
        self.prime_lock = bool(prime_lock)     # tự học 3A ngắn rồi khoá
        self.prime_ms = int(max(0, prime_ms))
        # Luôn luôn no-flush-on-start
        self.flush_on_start = False

        # Xử lý timeout mềm:
        self.timeout_count = 0
        self.MAX_TIMEOUTS_BEFORE_RESTART = 5   # quá số này thì auto-restart camera
        self.BACKOFF_MS = 100                  # nghỉ nhẹ giữa các lần timeout

    def _configure(self):
        cfg = self.picam2.create_video_configuration(
            main={"format": "RGB888", "size": self.size},
            buffer_count=4,
        )
        self.picam2.configure(cfg)

    def _apply_controls(self, force_fixed=False):
        """
        force_fixed=True để tắt 3A và áp thông số cố định ngay trước start()
        """
        if force_fixed or (not self.ae_enable and not self.awb_enable):
            controls = {
                "AeEnable": False,
                "AwbEnable": False,
                "ExposureTime": self.exposure_us,
                "AnalogueGain": self.gain,
                "ColourGains": self.colour_gains,
            }
        else:
            # Cho phép 3A nếu người dùng bật
            controls = {
                "AeEnable": self.ae_enable,
                "AwbEnable": self.awb_enable,
            }
        self.picam2.set_controls(controls)

    def _prime_and_lock(self):
        """
        Chạy free-run ngắn để AE/AWB hội tụ, đọc metadata rồi khoá thông số.
        """
        self._configure()
        # Bật 3A trong giai đoạn prime
        self.picam2.set_controls({"AeEnable": True, "AwbEnable": True})
        self.picam2.start()
        self.info.emit(f"Priming {self.prime_ms} ms for AE/AWB to settle...")
        QtCore.QThread.msleep(self.prime_ms)
        md = self.picam2.capture_metadata()
        exp = int(md.get("ExposureTime", self.exposure_us))
        gain = float(md.get("AnalogueGain", self.gain))
        cg = md.get("ColourGains", self.colour_gains)
        try:
            cg = (float(cg[0]), float(cg[1]))
        except Exception:
            cg = self.colour_gains
        self.picam2.stop()

        # Start lại với thông số đã khoá
        self.exposure_us, self.gain, self.colour_gains = exp, gain, cg
        self._configure()
        self._apply_controls(force_fixed=True)
        self.picam2.start()
        self.info.emit(f"Locked: Exp={exp}us Gain={gain:.2f} CG={cg}")

    @QtCore.pyqtSlot()
    def run(self):
        self._running = True
        try:
            self.picam2 = Picamera2()

            if self.prime_lock:
                self._prime_and_lock()
            else:
                # Debug trace: configuration and start sequence can take time
                ts = time.monotonic()
                try:
                    self.info.emit(f"[DBG] run: before _configure (t={ts:.3f})")
                except Exception:
                    pass
                self._configure()
                try:
                    self.info.emit(f"[DBG] run: after _configure (t={time.monotonic():.3f})")
                except Exception:
                    pass

                # Áp controls TRƯỚC start() để có hiệu lực từ khung đầu tiên
                try:
                    self.info.emit(f"[DBG] run: before _apply_controls (t={time.monotonic():.3f})")
                except Exception:
                    pass
                self._apply_controls(force_fixed=not (self.ae_enable or self.awb_enable))
                try:
                    self.info.emit(f"[DBG] run: after _apply_controls (t={time.monotonic():.3f})")
                except Exception:
                    pass

                try:
                    self.info.emit(f"[DBG] run: before picam2.start() (t={time.monotonic():.3f})")
                except Exception:
                    pass
                self.picam2.start()
                try:
                    self.info.emit(f"[DBG] run: after picam2.start() (t={time.monotonic():.3f})")
                except Exception:
                    pass

            self.info.emit("Streaming started...")
        except Exception as e:
            self.error.emit(f"Failed to open/start camera: {e}")
            self._running = False
            return

        period = 1.0 / max(1.0, self.target_fps)
        next_t = time.monotonic()

        while self._running:
            try:
                arr = self.picam2.capture_array()   # blocking
            except Exception as e:
                if not self._running or self._cancelled:
                    break

                msg = str(e).lower()
                is_timeout = ("timeout" in msg or "timed out" in msg or
                              "frontend has timed out" in msg or "dequeue timer" in msg)
                if is_timeout:
                    self.timeout_count += 1
                    if self.timeout_count % 10 == 0:
                        self.info.emit(f"Waiting for frames... (timeouts: {self.timeout_count})")
                    QtCore.QThread.msleep(self.BACKOFF_MS)
                    if self.timeout_count >= self.MAX_TIMEOUTS_BEFORE_RESTART:
                        try:
                            self.info.emit("Auto-recover: restarting camera after repeated timeouts...")
                            self.picam2.stop()
                            QtCore.QThread.msleep(100)
                            self.picam2.start()
                            self.timeout_count = 0
                        except Exception as e2:
                            self.error.emit(f"restart error: {e2}")
                            QtCore.QThread.msleep(200)
                    continue
                else:
                    self.error.emit(f"capture_array error: {e}")
                    QtCore.QThread.msleep(50)
                    continue

            if not self._running or self._cancelled:
                break

            self.timeout_count = 0

            self.rx_id += 1
            h, w = arr.shape[:2]
            if arr.ndim == 2:
                arr = np.repeat(arr[:, :, None], 3, axis=2)
            qimg = QtGui.QImage(arr.data, w, h, 3 * w, QtGui.QImage.Format_RGB888).copy()
            meta = {"rx_id": self.rx_id, "size": (w, h)}
            self.frame_ready.emit(qimg, meta)

            now = time.monotonic()
            if now < next_t:
                time.sleep(max(0, next_t - now))
            next_t = now + period

        # Cleanup
        if self.picam2 is not None:
            try: self.picam2.stop()
            except Exception: pass
            try: self.picam2.close()
            except Exception: pass
            self.picam2 = None
        self.info.emit("Streaming stopped.")

    @QtCore.pyqtSlot()
    def cancel(self):
        # Huỷ ngay: đặt cờ + cancel_all_and_flush + stop camera để phá block capture_array()
        self._running = False
        self._cancelled = True
        try:
            if self.picam2 is not None:
                try: self.picam2.cancel_all_and_flush()
                except Exception: pass
                try: self.picam2.stop()
                except Exception: pass
        except Exception:
            pass

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, debug=False, args=None):
        super().__init__()
        self.debug = debug
        self.args = args or argparse.Namespace()
        self.setWindowTitle("Picamera2 – Start / Cancel")
        self.resize(1100, 740)

        self.view = QtWidgets.QGraphicsView()
        self.scene = QtWidgets.QGraphicsScene(self)
        self.view.setScene(self.scene)
        self.pixitem = self.scene.addPixmap(QtGui.QPixmap(960, 540))
        self.setCentralWidget(self.view)
        self.status = self.statusBar()

        tb = self.addToolBar("Controls")
        self.startAct = QtWidgets.QAction("Start", self)
        self.cancelAct = QtWidgets.QAction("Cancel", self)
        self.startAct.triggered.connect(self.start_stream)
        self.cancelAct.triggered.connect(self.cancel_stream)
        tb.addAction(self.startAct)
        tb.addAction(self.cancelAct)

        self.thread = None
        self.worker = None
        self.running = False

    @QtCore.pyqtSlot()
    def start_stream(self):
        if self.debug:
            print("[DEBUG] Starting stream...")
        if self.thread and self.thread.isRunning():
            self.status.showMessage("Already running")
            return
        self.thread = QtCore.QThread(self)
        self.worker = StreamWorker(
            size=(self.args.width, self.args.height),
            target_fps=self.args.fps,
            ae_enable=self.args.ae,
            awb_enable=self.args.awb,
            exposure_us=self.args.exposure_us,
            gain=self.args.gain,
            colour_gains=(self.args.cg_r, self.args.cg_b),
            prime_lock=self.args.prime_lock,
            prime_ms=self.args.prime_ms,
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.frame_ready.connect(self.on_frame, type=QtCore.Qt.QueuedConnection)
        self.worker.info.connect(self.on_info, type=QtCore.Qt.QueuedConnection)
        self.worker.error.connect(self.on_error, type=QtCore.Qt.QueuedConnection)
        self.running = True
        self.thread.start()
        self.status.showMessage("Starting...")

    @QtCore.pyqtSlot()
    def cancel_stream(self):
        if self.debug:
            print("[DEBUG] Cancelling stream...")
        if not self.thread:
            return
        self.running = False
        try:
            self.worker.cancel()
        except Exception:
            pass
        self.thread.quit(); self.thread.wait(2000)
        self.thread = None
        self.worker = None
        self.status.showMessage("Cancelled")

    @QtCore.pyqtSlot(QtGui.QImage, dict)
    def on_frame(self, img: QtGui.QImage, meta: dict):
        if not self.running:
            return
        if self.debug:
            print(f"[DEBUG] Frame received: rx_id={meta['rx_id']}, size={meta['size']}")
        pix = QtGui.QPixmap.fromImage(img)
        self.pixitem.setPixmap(pix)
        self.view.fitInView(self.pixitem, QtCore.Qt.KeepAspectRatio)
        self.status.showMessage(f"Live rx:{meta['rx_id']} size:{meta['size'][0]}x{meta['size'][1]}")

    @QtCore.pyqtSlot(str)
    def on_info(self, msg: str):
        if self.debug:
            print(f"[INFO] {msg}")
        self.status.showMessage(msg)

    @QtCore.pyqtSlot(str)
    def on_error(self, msg: str):
        if self.debug:
            print(f"[ERROR] {msg}")
        QtWidgets.QMessageBox.critical(self, "Camera error", msg)

    def closeEvent(self, e: QtGui.QCloseEvent):
        self.cancel_stream()
        return super().closeEvent(e)

def main():
    parser = argparse.ArgumentParser(description="Picamera2 Stream Application")
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    # Kích thước & FPS
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=720)
    parser.add_argument('--fps', type=float, default=30.0)

    # 3A controls
    parser.add_argument('--ae', action='store_true', help='Enable Auto-Exposure (default off)')
    parser.add_argument('--awb', action='store_true', help='Enable Auto-White-Balance (default off)')
    parser.add_argument('--exposure-us', dest='exposure_us', type=int, default=10000, help='ExposureTime (us) when AE off')
    parser.add_argument('--gain', type=float, default=1.5, help='AnalogueGain when AE off')
    parser.add_argument('--cg-r', type=float, default=1.8, help='ColourGains red when AWB off')
    parser.add_argument('--cg-b', type=float, default=1.8, help='ColourGains blue when AWB off')

    # Prime & Lock
    parser.add_argument('--prime-lock', action='store_true', help='Prime AE/AWB briefly then lock controls')
    parser.add_argument('--prime-ms', type=int, default=400, help='Prime duration in milliseconds')

    # Always no-flush-on-start: option removed for simplicity

    args = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow(debug=args.debug, args=args)
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
