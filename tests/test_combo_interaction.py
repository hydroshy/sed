#!/usr/bin/env python3
"""
Debug Classification UI Interaction
Kiểm tra chi tiết combo boxes có thể tương tác được không
"""
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_combo_interaction():
    """Test combo box interaction capabilities"""
    print("=== Testing Combo Box Interaction ===")
    
    try:
        from PyQt5.QtWidgets import QApplication, QComboBox
        from PyQt5.QtCore import Qt
        
        app = QApplication(sys.argv)
        
        # Create a simple test combo box
        test_combo = QComboBox()
        test_combo.addItem("Test Item 1")
        test_combo.addItem("Test Item 2")
        test_combo.addItem("Test Item 3")
        
        print(f"Test combo enabled: {test_combo.isEnabled()}")
        print(f"Test combo visible: {test_combo.isVisible()}")
        print(f"Test combo count: {test_combo.count()}")
        
        # Test main window combo boxes
        from gui.main_window import MainWindow
        main_window = MainWindow()
        
        # Find the combo boxes
        model_combo = main_window.findChild(QComboBox, 'modelComboBox')
        class_combo = main_window.findChild(QComboBox, 'classComboBox')
        
        print(f"\n=== Model ComboBox Status ===")
        if model_combo:
            print(f"Found: True")
            print(f"Enabled: {model_combo.isEnabled()}")
            print(f"Visible: {model_combo.isVisible()}")
            print(f"Count: {model_combo.count()}")
            print(f"Parent enabled: {model_combo.parent().isEnabled() if model_combo.parent() else 'No parent'}")
            print(f"Items: {[model_combo.itemText(i) for i in range(model_combo.count())]}")
            
            # Check if widget accepts focus
            print(f"Focus policy: {model_combo.focusPolicy()}")
            print(f"Can get focus: {model_combo.focusPolicy() != Qt.NoFocus}")
            
            # Check geometry
            rect = model_combo.geometry()
            print(f"Geometry: x={rect.x()}, y={rect.y()}, w={rect.width()}, h={rect.height()}")
            
        else:
            print("Model combo not found!")
            
        print(f"\n=== Class ComboBox Status ===")
        if class_combo:
            print(f"Found: True")
            print(f"Enabled: {class_combo.isEnabled()}")
            print(f"Visible: {class_combo.isVisible()}")
            print(f"Count: {class_combo.count()}")
            print(f"Parent enabled: {class_combo.parent().isEnabled() if class_combo.parent() else 'No parent'}")
            print(f"Items: {[class_combo.itemText(i) for i in range(class_combo.count())]}")
            
            # Check if widget accepts focus
            print(f"Focus policy: {class_combo.focusPolicy()}")
            print(f"Can get focus: {class_combo.focusPolicy() != Qt.NoFocus}")
            
            # Check geometry
            rect = class_combo.geometry()
            print(f"Geometry: x={rect.x()}, y={rect.y()}, w={rect.width()}, h={rect.height()}")
        else:
            print("Class combo not found!")
            
        # Check classification page
        classification_page = main_window.findChild(main_window.__class__, 'classificationSettingPage')
        if classification_page:
            print(f"\n=== Classification Page Status ===")
            print(f"Page enabled: {classification_page.isEnabled()}")
            print(f"Page visible: {classification_page.isVisible()}")
            
            # Check stacked widget
            if hasattr(main_window, 'settingStackedWidget'):
                current_index = main_window.settingStackedWidget.currentIndex()
                print(f"Current stacked widget index: {current_index}")
                current_widget = main_window.settingStackedWidget.currentWidget()
                print(f"Current widget: {current_widget.objectName() if current_widget else 'None'}")
                
        print("\n=== Recommendations ===")
        if model_combo and class_combo:
            if not model_combo.isEnabled():
                print("❌ Model combo is disabled - check parent widgets")
            if not class_combo.isEnabled():
                print("❌ Class combo is disabled - check parent widgets")
            if model_combo.count() == 0:
                print("❌ Model combo is empty - models not loaded")
            if class_combo.count() == 0:
                print("ℹ️ Class combo is empty - normal until model selected")
            if model_combo.isEnabled() and model_combo.count() > 0:
                print("✅ Model combo should be interactive")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_combo_interaction()