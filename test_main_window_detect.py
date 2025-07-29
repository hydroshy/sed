#!/usr/bin/env python3
"""
Test script to verify DetectToolManager in real main window
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def test_main_window_detect():
    """Test DetectToolManager in actual main window"""
    print("✓ Creating QApplication...")
    app = QApplication(sys.argv)
    
    try:
        print("✓ Creating MainWindow...")
        window = MainWindow()
        
        # Check if widgets were found
        print(f"✓ algorithmComboBox found: {window.algorithmComboBox is not None}")
        print(f"✓ classificationComboBox found: {window.classificationComboBox is not None}")
        
        if window.algorithmComboBox:
            print(f"✓ algorithmComboBox item count: {window.algorithmComboBox.count()}")
            for i in range(window.algorithmComboBox.count()):
                print(f"  - Item {i}: {window.algorithmComboBox.itemText(i)}")
        else:
            print("✗ algorithmComboBox is None!")
            
        # Check DetectToolManager
        if hasattr(window, 'detect_tool_manager'):
            dtm = window.detect_tool_manager
            print(f"✓ DetectToolManager exists: {dtm is not None}")
            
            if dtm:
                print(f"✓ ModelManager exists: {dtm.model_manager is not None}")
                if dtm.model_manager:
                    models = dtm.model_manager.get_available_models()
                    print(f"✓ Available models: {models}")
                    
                    for model_name in models:
                        model_info = dtm.model_manager.get_model_info(model_name)
                        if model_info:
                            classes = model_info.get('classes', [])
                            print(f"  - {model_name}: {len(classes)} classes")
                        else:
                            print(f"  - {model_name}: Could not load model info")
                        
                # Try to manually load models
                print("✓ Manually calling load_available_models...")
                dtm.load_available_models()
                
                if window.algorithmComboBox:
                    print(f"✓ After manual load - algorithmComboBox count: {window.algorithmComboBox.count()}")
                    for i in range(window.algorithmComboBox.count()):
                        print(f"  - Item {i}: {window.algorithmComboBox.itemText(i)}")
        else:
            print("✗ DetectToolManager not found!")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("Test completed - window created successfully!")
    return app, window

if __name__ == "__main__":
    app, window = test_main_window_detect()
    # Don't call app.exec_() so we can see the output immediately
