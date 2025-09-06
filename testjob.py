#!/usr/bin/env python3
"""
Picamera2 + PyQt5: Stream liên tục + Trigger để "bắt" khung gần-nhất
- Camera chạy free‑run, preview mượt trong QGraphicsView (không block GUI)
- Nhấn nút Trigger (hoặc gọi slot) để chụp frame hiện tại (copy từ buffer), hiển thị nhãn TRIGGERED và lưu file (tuỳ chọn)

Cài đặt (khuyến nghị dùng Python hệ thống /usr/bin/python3 trên Raspberry Pi OS):
  sudo apt update
  sudo apt install -y python3-picamera2 python3-pyqt5 libcamera-apps

Nếu bạn đang dùng IMX296 và trước đó bật trigger mode phần cứng, hãy tắt để chạy free‑run:
  echo 0 | sudo tee /sys/module/imx296/parameters/trigger_mode

Chạy:
  /usr/bin/python3 picam2_qt_stream_trigger.py --save-dir /tmp/triggered
"""
import sys
import time
import argparse
from pathlib import Path
from collections import deque

from PyQt5 import QtCore, QtGui, QtWidgets
from picamera2 import Picamera2, Preview


class StreamWorker(QtCore.QObject):
    frame_ready = QtCore.pyqtSignal(QtGui.QImage, dict)     # preview frame
    triggered_frame = QtCore.pyqtSignal(QtGui.QImage, dict) # captured on trigger
    info = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)

    def __init__(self, size=(1280, 720), target_fps=30.0, ring=3):
        super().__init__()
        self.size = size
        self.target_fps = target_fps
        self._running = False
        self._last_frames = deque(maxlen=ring)  # ring buffer các frame gần nhất (numpy)
        self._lock = QtCore.QReadWriteLock()
        self.req_id = 0
        self.rx_id = 0

        # --- Camera ---
        self.picam2 = Picamera2()
        cfg = self.picam2.create_video_configuration(
            main={"format": "RGB888", "size": self.size},
            buffer_count=4,
        )
        self.picam2.configure(cfg)
        # Không mở cửa sổ preview nội bộ để tránh phụ thuộc KMS/Qt của Picamera2
        self.picam2.start_preview(Preview.NULL)
        # Gợi ý: cố định AE nếu cần độ trễ/độ sáng ổn định (kích hoạt nếu muốn)
        # self.picam2.set_controls({"AeEnable": False, "ExposureTime": 8000, "AnalogueGain": 1.5})
        # self.picam2.set_controls({"FrameDurationLimits": (33333, 33333)})  # ~30fps
        self.picam2.start()

    @QtCore.pyqtSlot()
    def run(self):
        self._running = True
        self.info.emit("Streaming started...")
        # Loop đọc liên tục (blocking) nhưng nằm trong worker thread nên không block GUI
        period = 1.0 / max(1.0, self.target_fps)
        next_t = time.monotonic()
        while self._running:
            try:
                arr = self.picam2.capture_array()  # chờ frame tiếp theo
            except Exception as e:
                self.error.emit(f"capture_array error: {e}")
                QtCore.QThread.msleep(5)
                continue

            self.rx_id += 1
            h, w = arr.shape[:2]
            if arr.ndim == 2:
                import numpy as np
                arr = np.repeat(arr[:, :, None], 3, axis=2)

            # Cập nhật ring buffer (copy nhẹ để tách khỏi buffer tạm)
            self._lock.lockForWrite()
            self._last_frames.append(arr.copy())
            self._lock.unlock()

            # Phát preview (QImage copy để an toàn)
            qimg = QtGui.QImage(arr.data, w, h, 3*w, QtGui.QImage.Format_RGB888).copy()
            meta = {"rx_id": self.rx_id, "size": (w, h)}
            self.frame_ready.emit(qimg, meta)

            # Throttle hiển thị nếu nhanh quá
            now = time.monotonic()
            if now < next_t:
                time.sleep(max(0, next_t - now))
            next_t = now + period

        try:
            self.picam2.stop()
        except Exception:
            pass
        self.info.emit("Streaming stopped.")

    @QtCore.pyqtSlot()
    def capture_trigger(self):
        # Lấy frame mới nhất từ ring buffer và emit
        self._lock.lockForRead()
        arr = self._last_frames[-1].copy() if self._last_frames else None
        self._lock.unlock()
        if arr is None:
            self.info.emit("No frame available to trigger yet")
            return
        h, w = arr.shape[:2]
        qimg = QtGui.QImage(arr.data, w, h, 3*w, QtGui.QImage.Format_RGB888).copy()
        meta = {"ts": time.time(), "size": (w, h)}
        self.triggered_frame.emit(qimg, meta)

    @QtCore.pyqtSlot()
    def stop(self):
        self._running = False


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, save_dir: Path):
        super().__init__()
        self.setWindowTitle("Picamera2 – Continuous Stream + Trigger Capture")
        self.resize(1100, 740)
        self.save_dir = save_dir
        if self.save_dir:
            self.save_dir.mkdir(parents=True, exist_ok=True)

        # UI
        self.view = QtWidgets.QGraphicsView()
        self.scene = QtWidgets.QGraphicsScene(self)
        self.view.setScene(self.scene)
        self.pixitem = self.scene.addPixmap(QtGui.QPixmap(960, 540))
        self.setCentralWidget(self.view)
        self.status = self.statusBar()

        tb = self.addToolBar("Controls")
        self.triggerAct = QtWidgets.QAction("Trigger", self)
        self.triggerAct.triggered.connect(self.on_trigger)
        tb.addAction(self.triggerAct)

        self.stopAct = QtWidgets.QAction("Stop", self)
        self.stopAct.triggered.connect(self.on_stop)
        tb.addAction(self.stopAct)

        # Thread & worker
        self.thread = QtCore.QThread(self)
        self.worker = StreamWorker(size=(1280, 720), target_fps=30.0)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.frame_ready.connect(self.on_frame, type=QtCore.Qt.QueuedConnection)
        self.worker.triggered_frame.connect(self.on_triggered_frame, type=QtCore.Qt.QueuedConnection)
        self.worker.info.connect(self.on_info, type=QtCore.Qt.QueuedConnection)
        self.worker.error.connect(self.on_error, type=QtCore.Qt.QueuedConnection)
        self.thread.start()

        self._flash_until = 0.0

    @QtCore.pyqtSlot()
    def on_trigger(self):
        self.worker.capture_trigger()

    @QtCore.pyqtSlot(QtGui.QImage, dict)
    def on_frame(self, img: QtGui.QImage, meta: dict):
        pix = QtGui.QPixmap.fromImage(img)
        # Nếu vừa trigger, vẽ khung viền để dễ nhìn
        if time.time() < self._flash_until:
            p = QtGui.QPainter(pix)
            pen = QtGui.QPen(QtCore.Qt.red)
            pen.setWidth(6)
            p.setPen(pen)
            p.drawRect(pix.rect().adjusted(3, 3, -3, -3))
            p.end()
        self.pixitem.setPixmap(pix)
        self.view.fitInView(self.pixitem, QtCore.Qt.KeepAspectRatio)
        self.status.showMessage(f"Live rx:{meta['rx_id']} size:{meta['size'][0]}x{meta['size'][1]}")

    @QtCore.pyqtSlot(QtGui.QImage, dict)
    def on_triggered_frame(self, img: QtGui.QImage, meta: dict):
        self._flash_until = time.time() + 0.2  # nháy viền 200ms
        if self.save_dir:
            path = self.save_dir / f"trigger_{int(meta['ts']*1000)}.jpg"
            img.save(str(path), "JPG")
            self.status.showMessage(f"Triggered & saved: {path}")
        else:
            self.status.showMessage("Triggered!")

    @QtCore.pyqtSlot(str)
    def on_info(self, msg: str):
        self.status.showMessage(msg)

    @QtCore.pyqtSlot(str)
    def on_error(self, msg: str):
        QtWidgets.QMessageBox.critical(self, "Camera error", msg)

    @QtCore.pyqtSlot()
    def on_stop(self):
        self.worker.stop()
        self.thread.quit(); self.thread.wait(2000)
        self.status.showMessage("Stopped")

    def closeEvent(self, e: QtGui.QCloseEvent):
        try:
            self.worker.stop()
        except Exception:
            pass
        self.thread.quit(); self.thread.wait(2000)
        return super().closeEvent(e)


def main():
    parser = argparse.ArgumentParser(description="Picamera2 continuous stream + trigger capture")
    parser.add_argument("--save-dir", type=str, default="", help="Thư mục lưu ảnh khi trigger (trống = không lưu)")
    args = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow(save_dir=Path(args.save_dir) if args.save_dir else Path())
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
