#!/usr/bin/env python3
"""
Test script for format camera combo box functionality
"""

import sys
import os

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt5.QtWidgets import QApplication
    from gui.main_window import MainWindow
    
    def test_format_combo():
        app = QApplication(sys.argv)
        
        # Create main window
        window = MainWindow()
        
        # Check if formatCameraComboBox exists
        if hasattr(window, 'formatCameraComboBox') and window.formatCameraComboBox:
            print("✓ formatCameraComboBox found")
            print(f"  Items count: {window.formatCameraComboBox.count()}")
            for i in range(window.formatCameraComboBox.count()):
                print(f"  Item {i}: {window.formatCameraComboBox.itemText(i)}")
            print(f"  Current selection: {window.formatCameraComboBox.currentText()}")
        else:
            print("✗ formatCameraComboBox not found")
        
        # Check camera stream
        if hasattr(window, 'camera_manager') and window.camera_manager:
            if hasattr(window.camera_manager, 'camera_stream') and window.camera_manager.camera_stream:
                camera_stream = window.camera_manager.camera_stream
                print("✓ Camera stream found")
                print(f"  Current format: {getattr(camera_stream, 'current_format', 'Unknown')}")
                print(f"  Available formats: {camera_stream.get_available_formats()}")
            else:
                print("✗ Camera stream not found")
        else:
            print("✗ Camera manager not found")
        
        # Don't show window, just test
        # window.show()
        # app.exec_()
        
        print("Test completed")
        
    if __name__ == "__main__":
        test_format_combo()
        
except Exception as e:
    print(f"Test failed: {e}")
    import traceback
    traceback.print_exc()
