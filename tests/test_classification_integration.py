#!/usr/bin/env python3
"""
Test Classification UI Integration
Chạy app và kiểm tra log để xem ClassificationToolManager có hoạt động không
"""
import sys
import logging
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('classification_test.log')
    ]
)

def test_app_startup():
    """Test app startup and classification tool manager"""
    print("=== Testing Classification UI Integration ===")
    
    try:
        # Set up Qt application
        from PyQt5.QtWidgets import QApplication
        import sys
        
        # Create application (needed for Qt widgets)
        app = QApplication(sys.argv)
        
        # Import and create main window
        from gui.main_window import MainWindow
        
        print("Creating MainWindow...")
        main_window = MainWindow()
        
        print("MainWindow created successfully!")
        
        # Check if ClassificationToolManager was set up
        if hasattr(main_window, 'classification_tool_manager'):
            ctm = main_window.classification_tool_manager
            print(f"ClassificationToolManager exists: {ctm is not None}")
            
            if ctm:
                print(f"Model manager initialized: {ctm.model_manager is not None}")
                if ctm.model_manager:
                    models = ctm.model_manager.get_available_models()
                    print(f"Available models: {models}")
                
                # Check if UI components are connected
                print(f"Model combo connected: {ctm.model_combo is not None}")
                print(f"Class combo connected: {ctm.class_combo is not None}")
                
                # Check combo box contents if connected
                if ctm.model_combo:
                    count = ctm.model_combo.count()
                    items = [ctm.model_combo.itemText(i) for i in range(count)]
                    print(f"ModelComboBox items ({count}): {items}")
                
                if ctm.class_combo:
                    count = ctm.class_combo.count()
                    items = [ctm.class_combo.itemText(i) for i in range(count)]
                    print(f"ClassComboBox items ({count}): {items}")
        else:
            print("ClassificationToolManager not found!")
        
        # Check if the combo boxes exist in the UI
        model_combo = main_window.findChild(main_window.__class__, 'modelComboBox')
        class_combo = main_window.findChild(main_window.__class__, 'classComboBox')
        print(f"modelComboBox found in UI: {model_combo is not None}")
        print(f"classComboBox found in UI: {class_combo is not None}")
        
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_app_startup()