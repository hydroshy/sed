#!/usr/bin/env python3
"""
Focused test for DetectToolManager configuration loading
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

def test_detect_tool_manager_only():
    """Test DetectToolManager configuration loading in isolation"""
    print("Testing DetectToolManager configuration loading...")
    
    try:
        # Import only what we need to avoid picamera2 dependency
        sys.path.insert(0, str(project_root / 'gui'))
        from detect_tool_manager import DetectToolManager
        from PyQt5.QtWidgets import QApplication, QComboBox, QPushButton, QTableView
        from PyQt5.QtGui import QStandardItemModel
        
        # Create minimal Qt application
        app = QApplication([])
        
        # Create mock main window
        main_window = Mock()
        
        # Create DetectToolManager
        manager = DetectToolManager(main_window)
        
        # Create real UI components
        algorithm_combo = QComboBox()
        classification_combo = QComboBox()
        add_btn = QPushButton()
        remove_btn = QPushButton()
        table_view = QTableView()
        
        # Manually setup the classification model since setup_ui_components might fail
        manager.classification_model = QStandardItemModel(0, 2)
        manager.classification_model.setHorizontalHeaderLabels(["Class Name", "Threshold"])
        table_view.setModel(manager.classification_model)
        
        # Set the UI components manually
        manager.algorithm_combo = algorithm_combo
        manager.classification_combo = classification_combo
        manager.add_classification_btn = add_btn
        manager.remove_classification_btn = remove_btn
        manager.classification_table = table_view
        
        # Simulate having some models available
        algorithm_combo.addItem("Select Model...")
        algorithm_combo.addItem("yolov8n.onnx")
        algorithm_combo.addItem("yolov8s.onnx")
        
        # Mock the model manager to return test data
        manager.model_manager = Mock()
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
        current_text = algorithm_combo.currentText()
        assert current_text == 'yolov8n.onnx', f"Expected 'yolov8n.onnx', got '{current_text}'"
        print("✓ Model selection loaded correctly")
        
        # Verify selected classes were set
        expected_classes = ['person', 'car', 'bicycle']
        assert manager.selected_classes == expected_classes, f"Expected {expected_classes}, got {manager.selected_classes}"
        print("✓ Selected classes loaded correctly")
        
        # Verify table was populated
        row_count = manager.classification_model.rowCount()
        assert row_count == 3, f"Expected 3 rows in table, got {row_count}"
        
        # Check table contents
        table_classes = []
        for row in range(row_count):
            item = manager.classification_model.item(row, 0)
            if item:
                table_classes.append(item.text())
        
        for class_name in expected_classes:
            assert class_name in table_classes, f"Class '{class_name}' not found in table. Table has: {table_classes}"
            
        print("✓ Classification table populated correctly")
        print(f"Table contents: {table_classes}")
        
        print("✓ DetectToolManager configuration loading test passed!")
        return True
        
    except Exception as e:
        print(f"✗ DetectToolManager configuration loading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== DetectToolManager Configuration Loading Test ===")
    
    success = test_detect_tool_manager_only()
    
    if success:
        print("=== Test passed! ===")
        sys.exit(0)
    else:
        print("=== Test failed! ===")
        sys.exit(1)