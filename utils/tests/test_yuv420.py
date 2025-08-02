#!/usr/bin/env python3
"""
Test YUV420 format handling
"""

import sys
import os

# Import test utilities
from utils.tests.test_utils import setup_test_path
setup_test_path()

try:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QTimer
    
    def test_yuv420():
        app = QApplication(sys.argv)
        
        # Import and create main window
        from gui.main_window import MainWindow
        
        window = MainWindow()
        
        def test_sequence():
            print("\n=== YUV420 Format Test ===")
            
            # Check if formats are available
            if hasattr(window, 'formatCameraComboBox') and window.formatCameraComboBox:
                combo = window.formatCameraComboBox
                
                # Select YUV420 if available
                yuv_index = combo.findText("YUV420")
                if yuv_index >= 0:
                    print("Setting format to YUV420...")
                    combo.setCurrentIndex(yuv_index)
                    
                    # Apply the format
                    if hasattr(window, '_apply_camera_settings'):
                        window._apply_camera_settings()
                        print("✓ YUV420 format applied")
                        
                        # Start live camera to test display
                        if hasattr(window, 'camera_manager') and window.camera_manager:
                            # Wait a bit then start live mode
                            QTimer.singleShot(2000, lambda: test_live_mode(window))
                        else:
                            print("✗ Camera manager not available")
                            app.quit()
                    else:
                        print("✗ _apply_camera_settings not available")
                        app.quit()
                else:
                    print("✗ YUV420 format not found")
                    app.quit()
            else:
                print("✗ formatCameraComboBox not found")
                app.quit()
        
        def test_live_mode(window):
            print("Starting live mode with YUV420...")
            try:
                if hasattr(window.camera_manager, 'toggle_live_camera'):
                    window.camera_manager.toggle_live_camera(True)
                    print("✓ Live mode started with YUV420")
                    
                    # Stop after 3 seconds
                    QTimer.singleShot(3000, app.quit)
                else:
                    print("✗ toggle_live_camera not available")
                    app.quit()
            except Exception as e:
                print(f"✗ Error starting live mode: {e}")
                app.quit()
        
        # Run test after delay
        QTimer.singleShot(3000, test_sequence)
        
        app.exec_()
        
    if __name__ == "__main__":
        test_yuv420()
        
except Exception as e:
    print(f"Test failed: {e}")
    import traceback
    traceback.print_exc()
