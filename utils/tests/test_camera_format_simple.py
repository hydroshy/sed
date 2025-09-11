"""
Test script để kiểm tra định dạng và kênh màu của camera
"""
import os
import sys
import time
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

# Thêm đường dẫn project vào PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

try:
    from picamera2 import Picamera2
    print("Picamera2 imported successfully")
except ImportError:
    print("WARNING: Failed to import picamera2. Make sure it's installed:")
    print("sudo apt install -y python3-picamera2")
    sys.exit(1)

from camera.camera_stream import CameraStream

class CameraFormatTest:
    def __init__(self):
        self.cs = None
        self.current_format_index = 0
        self.formats = ['RGB888', 'BGR888', 'XRGB8888']
        self.timer = None
        
    def start_test(self):
        print("\nInitializing camera test...")
        self.cs = CameraStream()
        self.test_next_format()
        
    def test_next_format(self):
        if self.current_format_index >= len(self.formats):
            self.cleanup()
            return
            
        fmt = self.formats[self.current_format_index]
        print(f"\nTesting format: {fmt}")
        
        try:
            # Thiết lập định dạng
            self.cs.set_format(fmt)
            
            # Kết nối signal frame_ready
            self.cs.frame_ready.connect(self.on_frame)
            
            # Khởi động camera
            self.cs.start_live()
            print("Camera started")
            
            # Set timer để chuyển sang format tiếp theo
            QTimer.singleShot(3000, self.move_to_next_format)
            
        except Exception as e:
            print(f"Error testing format {fmt}: {e}")
            self.move_to_next_format()
            
    def on_frame(self, frame):
        if frame is not None:
            print(f"Frame shape: {frame.shape}")
            print(f"Number of channels: {frame.shape[2] if len(frame.shape) > 2 else 1}")
            print(f"Actual format: {self.cs.get_pixel_format()}")
            # Ngắt kết nối signal sau khi nhận frame đầu tiên
            self.cs.frame_ready.disconnect(self.on_frame)
        
    def move_to_next_format(self):
        if self.cs:
            self.cs.stop_live()
            print("Camera stopped")
            
        self.current_format_index += 1
        if self.current_format_index < len(self.formats):
            QTimer.singleShot(1000, self.test_next_format)
        else:
            self.cleanup()
            
    def cleanup(self):
        if self.cs:
            self.cs.stop_live()
        print("\nTest completed")
        # Kết thúc ứng dụng
        QApplication.quit()

def main():
    app = QApplication(sys.argv)
    
    # Kiểm tra Picamera2
    if not hasattr(sys.modules.get('picamera2', None), 'Picamera2'):
        print("ERROR: picamera2 module not found or not properly installed")
        return
        
    test = CameraFormatTest()
    # Khởi động test sau khi event loop bắt đầu
    QTimer.singleShot(0, test.start_test)
    
    # Chạy event loop
    app.exec_()

if __name__ == '__main__':
    main()
