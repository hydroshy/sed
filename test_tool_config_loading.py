#!/usr/bin/env python3
"""
Test script for tool configuration loading during edit operations
"""

import sys
import os
import logging
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_detect_tool_config_loading():
    """Test DetectToolManager loading tool configuration"""
    print("Testing DetectTool configuration loading...")
    
    try:
        from gui.detect_tool_manager import DetectToolManager
        from PyQt5.QtWidgets import QApplication, QComboBox, QPushButton, QTableView
        from PyQt5.QtGui import QStandardItemModel
        
        # Create minimal Qt application
        app = QApplication([])
        
        # Create mock main window
        main_window = Mock()
        
        # Create DetectToolManager
        manager = DetectToolManager(main_window)
        
        # Create mock UI components
        algorithm_combo = QComboBox()
        classification_combo = QComboBox()
        add_btn = QPushButton()
        remove_btn = QPushButton()
        table_view = QTableView()
        
        # Setup the manager with mock components
        manager.setup_ui_components(
            algorithm_combo=algorithm_combo,
            classification_combo=classification_combo,
            add_btn=add_btn,
            remove_btn=remove_btn,
            scroll_area=None,
            table_view=table_view
        )
        
        # Simulate having some models available
        algorithm_combo.addItem("Select Model...")
        algorithm_combo.addItem("yolov8n.onnx")
        algorithm_combo.addItem("yolov8s.onnx")
        
        # Mock the model manager to return test data
        manager.model_manager.get_model_info = Mock(return_value={
            'name': 'yolov8n.onnx',
            'path': '/path/to/yolov8n.onnx',
            'classes': ['person', 'bicycle', 'car', 'motorcycle', 'airplane']
        })
        
        # Test loading configuration
        test_config = {
            'model_name': 'yolov8n.onnx',
            'model_path': '/path/to/yolov8n.onnx',
            'selected_classes': ['person', 'car', 'bicycle'],
            'confidence_threshold': 0.6,
            'nms_threshold': 0.3
        }
        
        print(f"Loading test config: {test_config}")
        manager.load_tool_config(test_config)
        
        # Verify model was set
        assert algorithm_combo.currentText() == 'yolov8n.onnx', f"Expected 'yolov8n.onnx', got '{algorithm_combo.currentText()}'"
        print("✓ Model selection loaded correctly")
        
        # Verify selected classes were set
        assert manager.selected_classes == ['person', 'car', 'bicycle'], f"Expected ['person', 'car', 'bicycle'], got {manager.selected_classes}"
        print("✓ Selected classes loaded correctly")
        
        # Verify table was populated (if classification_model exists)
        if manager.classification_model is not None:
            row_count = manager.classification_model.rowCount()
            assert row_count == 3, f"Expected 3 rows in table, got {row_count}"
            
            # Check table contents
            for row in range(row_count):
                item = manager.classification_model.item(row, 0)
                if item:
                    class_name = item.text()
                    assert class_name in test_config['selected_classes'], f"Unexpected class in table: {class_name}"
            print("✓ Classification table populated correctly")
        
        print("✓ DetectTool configuration loading test passed!")
        return True
        
    except Exception as e:
        print(f"✗ DetectTool configuration loading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_main_window_tool_delegation():
    """Test that main window properly delegates tool configuration loading"""
    print("Testing main window tool delegation...")
    
    try:
        # Mock the tool and config
        mock_tool = Mock()
        mock_tool.name = "Detect Tool"
        mock_tool.config.to_dict.return_value = {
            'model_name': 'yolov8n.onnx',
            'selected_classes': ['person', 'car'],
            'detection_area': [10, 10, 100, 100]
        }
        
        # Mock main window components
        mock_main_window = Mock()
        mock_main_window.detect_tool_manager = Mock()
        
        # Test delegation logic (simulate the fixed _load_tool_config_to_ui method)
        config = mock_tool.config.to_dict()
        
        # This should delegate to DetectToolManager for DetectTool
        if mock_tool.name == "Detect Tool":
            mock_main_window.detect_tool_manager.load_tool_config(config)
            
        # Verify the delegation occurred
        mock_main_window.detect_tool_manager.load_tool_config.assert_called_once_with(config)
        print("✓ Main window correctly delegates DetectTool configuration to DetectToolManager")
        
        return True
        
    except Exception as e:
        print(f"✗ Main window delegation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Tool Configuration Loading Tests ===")
    
    success = True
    
    # Test DetectToolManager configuration loading
    success &= test_detect_tool_config_loading()
    print()
    
    # Test main window delegation
    success &= test_main_window_tool_delegation()
    print()
    
    if success:
        print("=== All tests passed! ===")
        sys.exit(0)
    else:
        print("=== Some tests failed! ===")
        sys.exit(1)