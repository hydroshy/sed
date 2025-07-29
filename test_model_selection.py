#!/usr/bin/env python3
"""
Test script to check model selection and class loading
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def test_model_selection():
    """Test model selection and class loading"""
    print("✓ Creating QApplication...")
    app = QApplication(sys.argv)
    
    try:
        print("✓ Creating MainWindow...")
        window = MainWindow()
        
        # Check algorithm combo box
        if window.algorithmComboBox:
            print(f"✓ Algorithm combo items: {window.algorithmComboBox.count()}")
            for i in range(window.algorithmComboBox.count()):
                print(f"  - Item {i}: {window.algorithmComboBox.itemText(i)}")
                
            # Try to select yolov11n if available
            for i in range(window.algorithmComboBox.count()):
                if window.algorithmComboBox.itemText(i) == "yolov11n":
                    print(f"✓ Selecting yolov11n at index {i}")
                    window.algorithmComboBox.setCurrentIndex(i)
                    
                    # Wait a moment for signal processing
                    app.processEvents()
                    
                    # Force signal trigger if it didn't fire automatically
                    print("Debug: Manually triggering model change...")
                    if hasattr(window, 'detect_tool_manager'):
                        window.detect_tool_manager._on_model_changed("yolov11n")
                    
                    # Check classification combo box from main window
                    if hasattr(window, 'classificationComboBox') and window.classificationComboBox:
                        print(f"✓ Classification combo items after selection: {window.classificationComboBox.count()}")
                        print(f"MainWindow classificationComboBox address: {hex(id(window.classificationComboBox))}")
                        
                        # Check DetectToolManager classification_combo address
                        if hasattr(window, 'detect_tool_manager') and window.detect_tool_manager.classification_combo:
                            dtm_combo = window.detect_tool_manager.classification_combo
                            print(f"DetectToolManager classification_combo address: {hex(id(dtm_combo))}")
                            print(f"Same object? {window.classificationComboBox is dtm_combo}")
                            print(f"DetectToolManager combo items: {dtm_combo.count()}")
                        
                        for j in range(window.classificationComboBox.count()):
                            print(f"  - Class {j}: {window.classificationComboBox.itemText(j)}")
                            
                        # Also check DetectToolManager directly
                        if hasattr(window, 'detect_tool_manager'):
                            dtm = window.detect_tool_manager
                            if dtm.current_model:
                                print(f"✓ DetectToolManager current model: {dtm.current_model['name']}")
                                print(f"✓ Model classes: {dtm.current_model['classes']}")
                            else:
                                print("✗ DetectToolManager has no current model")
                    else:
                        print("✗ Classification combo box not found!")
                        
                        # Debug: Try to find it again
                        print("Debug: Searching for classificationComboBox...")
                        from PyQt5.QtWidgets import QComboBox
                        combo = window.findChild(QComboBox, 'classificationComboBox')
                        print(f"Found via findChild: {combo is not None}")
                        
                        # Also check if it exists but is None
                        print(f"window.classificationComboBox exists: {hasattr(window, 'classificationComboBox')}")
                        if hasattr(window, 'classificationComboBox'):
                            print(f"window.classificationComboBox value: {window.classificationComboBox}")
                            
                        # Check DetectToolManager classification_combo directly
                        if hasattr(window, 'detect_tool_manager') and window.detect_tool_manager.classification_combo:
                            cc = window.detect_tool_manager.classification_combo
                            print(f"DetectToolManager classification_combo items: {cc.count()}")
                            for k in range(cc.count()):
                                print(f"  - Item {k}: {cc.itemText(k)}")
                    break
            else:
                print("✗ yolov11n not found in algorithm combo box")
        else:
            print("✗ Algorithm combo box not found!")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("Test completed!")
    return app, window

if __name__ == "__main__":
    app, window = test_model_selection()
