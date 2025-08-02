#!/usr/bin/env python3
"""
Test complete format workflow: load formats -> select format -> apply
"""

import sys
import os

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt5.QtWidgets import QApplication, QComboBox
    from PyQt5.QtCore import QTimer
    
    def test_format_workflow():
        app = QApplication(sys.argv)
        
        # Import and create main window
        from gui.main_window import MainWindow
        
        window = MainWindow()
        
        def test_sequence():
            print("\n=== Format Workflow Test ===")
            
            # 1. Check if formats are loaded
            if hasattr(window, 'formatCameraComboBox') and window.formatCameraComboBox:
                combo = window.formatCameraComboBox
                print(f"✓ formatCameraComboBox found")
                print(f"  Items count: {combo.count()}")
                
                if combo.count() > 0:
                    for i in range(combo.count()):
                        print(f"  Item {i}: {combo.itemText(i)}")
                    
                    # 2. Test selecting a different format
                    if combo.count() > 1:
                        print(f"\n--- Testing Format Selection ---")
                        print(f"Current selection: {combo.currentText()}")
                        
                        # Select RGB888 if available
                        rgb_index = combo.findText("RGB888")
                        if rgb_index >= 0:
                            combo.setCurrentIndex(rgb_index)
                            print(f"Changed selection to: {combo.currentText()}")
                            
                            # 3. Test apply setting
                            print(f"\n--- Testing Apply Setting ---")
                            if hasattr(window, '_apply_camera_settings'):
                                window._apply_camera_settings()
                                print("✓ Apply camera settings called")
                            else:
                                print("✗ _apply_camera_settings method not found")
                        else:
                            print("RGB888 format not found in combo")
                    else:
                        print("Not enough formats to test selection")
                else:
                    print("✗ No formats loaded in combo box")
                    # Try to reload formats
                    if hasattr(window, '_load_camera_formats'):
                        print("Trying to reload formats...")
                        window._load_camera_formats()
                        print(f"After reload: {combo.count()} items")
            else:
                print("✗ formatCameraComboBox not found")
            
            app.quit()
        
        # Run test after delay
        QTimer.singleShot(3000, test_sequence)
        
        app.exec_()
        
    if __name__ == "__main__":
        test_format_workflow()
        
except Exception as e:
    print(f"Test failed: {e}")
    import traceback
    traceback.print_exc()
