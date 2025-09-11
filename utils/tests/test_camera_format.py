import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QComboBox, QLabel, 
                           QFrame, QVBoxLayout, QWidget, QPushButton, QHBoxLayout)
from PyQt5.QtCore import Qt
from camera.camera_stream import CameraStream

class CameraFormatTest(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera Format Test")
        self.setGeometry(100, 100, 600, 400)
        
        # Central widget and main layout
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        
        # Create control panel
        control_panel = QFrame()
        control_panel.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        control_layout = QHBoxLayout(control_panel)
        
        # Format selection
        format_group = QFrame()
        format_layout = QVBoxLayout(format_group)
        
        format_label = QLabel("Pixel Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["RGB888", "BGR888", "XRGB8888"])
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        
        # Info display
        info_group = QFrame()
        info_layout = QVBoxLayout(info_group)
        
        self.channel_label = QLabel("Channels: -")
        self.shape_label = QLabel("Frame Shape: -")
        self.format_label = QLabel("Current Format: -")
        
        info_layout.addWidget(self.channel_label)
        info_layout.addWidget(self.shape_label)
        info_layout.addWidget(self.format_label)
        
        # Control buttons
        button_group = QFrame()
        button_layout = QVBoxLayout(button_group)
        
        self.start_button = QPushButton("Start Camera")
        self.start_button.clicked.connect(self.toggle_camera)
        self.test_button = QPushButton("Test Frame")
        self.test_button.clicked.connect(self.test_frame)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.test_button)
        
        # Add all groups to control panel
        control_layout.addWidget(format_group)
        control_layout.addWidget(info_group)
        control_layout.addWidget(button_group)
        
        # Status label at bottom
        self.status_label = QLabel("Status: Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # Add everything to main layout
        main_layout.addWidget(control_panel)
        main_layout.addWidget(self.status_label)
        
        # Initialize camera
        self.camera = None
        self.camera_running = False
        
    def toggle_camera(self):
        if not self.camera_running:
            self.start_camera()
        else:
            self.stop_camera()
            
    def start_camera(self):
        try:
            self.camera = CameraStream()
            # Set initial format
            format = self.format_combo.currentText()
            self.camera.set_format(format)
            self.camera.start_live()
            self.camera.frame_ready.connect(self.on_frame)
            
            self.camera_running = True
            self.start_button.setText("Stop Camera")
            self.status_label.setText("Status: Camera running")
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            
    def stop_camera(self):
        if self.camera:
            self.camera.stop_live()
            self.camera = None
        self.camera_running = False
        self.start_button.setText("Start Camera")
        self.status_label.setText("Status: Camera stopped")
        
    def on_format_changed(self, format):
        if self.camera and self.camera_running:
            try:
                self.camera.set_format(format)
                self.status_label.setText(f"Format changed to {format}")
            except Exception as e:
                self.status_label.setText(f"Error changing format: {str(e)}")
                
    def on_frame(self, frame):
        if frame is None:
            return
            
        try:
            # Update info labels
            channels = frame.shape[2] if len(frame.shape) > 2 else 1
            self.channel_label.setText(f"Channels: {channels}")
            self.shape_label.setText(f"Frame Shape: {frame.shape}")
            
            if self.camera:
                current_format = self.camera.get_pixel_format()
                self.format_label.setText(f"Current Format: {current_format}")
        except Exception as e:
            self.status_label.setText(f"Error processing frame: {str(e)}")
            
    def test_frame(self):
        """Generate a test frame to verify color channels"""
        if not self.camera:
            return
            
        try:
            # Create a test pattern that clearly shows RGB/BGR difference
            h, w = 480, 640
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            
            # Draw R, G, B rectangles
            frame[h//4:3*h//4, 0:w//3, 0] = 255  # Red in BGR
            frame[h//4:3*h//4, w//3:2*w//3, 1] = 255  # Green in BGR
            frame[h//4:3*h//4, 2*w//3:w, 2] = 255  # Blue in BGR
            
            # Process test frame
            self.on_frame(frame)
            
            # Show current format
            if self.camera:
                format = self.camera.get_pixel_format()
                self.status_label.setText(f"Test frame generated ({format})")
        except Exception as e:
            self.status_label.setText(f"Error generating test frame: {str(e)}")
            
def main():
    app = QApplication(sys.argv)
    window = CameraFormatTest()
    window.show()
    sys.exit(app.exec_())
    
if __name__ == "__main__":
    main()
