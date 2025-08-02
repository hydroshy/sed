import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QComboBox, QLabel, QFrame, QVBoxLayout, QWidget
from PyQt5 import uic
import os

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FormatCameraComboBox Test")
        
        # Central widget
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        # Create a layout
        layout = QVBoxLayout(self.central_widget)
        
        # Create a frame to simulate cameraSettingFrame
        self.camera_setting_frame = QFrame(self.central_widget)
        self.camera_setting_frame.setObjectName("cameraSettingFrame")
        self.camera_setting_frame.setFrameShape(QFrame.StyledPanel)
        self.camera_setting_frame.setFrameShadow(QFrame.Raised)
        self.camera_setting_frame.setGeometry(10, 10, 500, 400)
        layout.addWidget(self.camera_setting_frame)
        
        # Create a label for format
        self.format_label = QLabel(self.camera_setting_frame)
        self.format_label.setObjectName("formatCameraLabel")
        self.format_label.setText("Format:")
        self.format_label.setGeometry(20, 20, 100, 25)
        
        # Create a combobox for format
        self.format_combobox = QComboBox(self.camera_setting_frame)
        self.format_combobox.setObjectName("formatCameraComboBox")
        self.format_combobox.setGeometry(130, 20, 150, 25)
        self.format_combobox.addItem("BGR")
        self.format_combobox.addItem("RGB")
        
        # Debug info
        print(f"formatCameraComboBox created, enabled: {self.format_combobox.isEnabled()}")
        print(f"formatCameraComboBox visible: {self.format_combobox.isVisible()}")
        print(f"formatCameraComboBox geometry: {self.format_combobox.geometry().x()}, {self.format_combobox.geometry().y()}, {self.format_combobox.geometry().width()}, {self.format_combobox.geometry().height()}")
        
        # Connect signals
        self.format_combobox.currentIndexChanged.connect(self.on_format_changed)
        
    def on_format_changed(self, index):
        print(f"Format changed to: {self.format_combobox.currentText()}")
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())
