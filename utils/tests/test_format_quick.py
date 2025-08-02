#!/usr/bin/env python3
"""
Quick test for formatCameraComboBox
"""

import sys
import os

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt5.QtWidgets import QApplication, QComboBox
    from PyQt5.QtCore import QTimer
    
    def test_quick():
        app = QApplication(sys.argv)
        
        # Import and create main window
        from gui.main_window import MainWindow
        
        window = MainWindow()
        
        def delayed_check():
            print("\n=== Delayed Format Check ===")
            if hasattr(window, 'formatCameraComboBox') and window.formatCameraComboBox:
                print(f"✓ formatCameraComboBox found after delay")
                print(f"  Items count: {window.formatCameraComboBox.count()}")
                for i in range(window.formatCameraComboBox.count()):
                    print(f"  Item {i}: {window.formatCameraComboBox.itemText(i)}")
                print(f"  Current selection: {window.formatCameraComboBox.currentText()}")
            else:
                print("✗ formatCameraComboBox still not found after delay")
                
                # Try to find it manually
                all_combos = window.findChildren(QComboBox)
                print(f"Found {len(all_combos)} total combo boxes:")
                for combo in all_combos:
                    print(f"  - {combo.objectName()}")
                    if combo.objectName() == 'formatCameraComboBox':
                        print(f"    Found target combo! Items: {combo.count()}")
                        for i in range(combo.count()):
                            print(f"      Item {i}: {combo.itemText(i)}")
            
            # Force a reload
            if hasattr(window, '_load_camera_formats'):
                print("\n=== Force Reload ===")
                window._load_camera_formats()
            
            app.quit()
        
        # Check after a short delay to let everything initialize
        QTimer.singleShot(2000, delayed_check)
        
        app.exec_()
        
    if __name__ == "__main__":
        test_quick()
        
except Exception as e:
    print(f"Test failed: {e}")
    import traceback
    traceback.print_exc()
