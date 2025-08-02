#!/usr/bin/env python3
"""
Test script for DetectToolManager
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    # Test PyQt5 import
    from PyQt5.QtWidgets import QApplication, QWidget, QComboBox, QPushButton, QScrollArea, QVBoxLayout, QLabel
    from PyQt5.QtCore import Qt
    print("✓ PyQt5 imported successfully")
    
    # Test DetectToolManager import
    from gui.detect_tool_manager import DetectToolManager
    print("✓ DetectToolManager imported successfully")
    
    # Test ModelManager
    from detection.model_manager import ModelManager
    model_manager = ModelManager()
    models = model_manager.get_available_models()
    print(f"✓ Found {len(models)} models: {models}")
    
    # Test model info
    for model_name in models:
        info = model_manager.get_model_info(model_name)
        if info:
            print(f"  {model_name}: {len(info['classes'])} classes")
        else:
            print(f"  {model_name}: Failed to load")
    
    # Create a simple test UI
    app = QApplication(sys.argv)
    
    # Create main widget
    main_widget = QWidget()
    main_widget.setWindowTitle("Detect Tool Test")
    main_widget.resize(400, 300)
    
    layout = QVBoxLayout(main_widget)
    
    # Create test widgets
    algorithm_combo = QComboBox()
    classification_combo = QComboBox()
    add_btn = QPushButton("Add Class")
    remove_btn = QPushButton("Remove Class")
    scroll_area = QScrollArea()
    
    # Add to layout
    layout.addWidget(QLabel("Algorithm:"))
    layout.addWidget(algorithm_combo)
    layout.addWidget(QLabel("Classification:"))
    layout.addWidget(classification_combo)
    layout.addWidget(add_btn)
    layout.addWidget(remove_btn)
    layout.addWidget(QLabel("Selected Classes:"))
    layout.addWidget(scroll_area)
    
    # Create DetectToolManager
    detect_manager = DetectToolManager(None)
    detect_manager.setup_ui_components(
        algorithm_combo=algorithm_combo,
        classification_combo=classification_combo,
        add_btn=add_btn,
        remove_btn=remove_btn,
        scroll_area=scroll_area
    )
    
    print("✓ DetectToolManager setup completed")
    print(f"✓ Algorithm combo items: {[algorithm_combo.itemText(i) for i in range(algorithm_combo.count())]}")
    
    main_widget.show()
    
    # Run for a short time to test
    print("Test UI created. Check the combo box contents.")
    sys.exit(app.exec_())
    
except ImportError as e:
    print(f"✗ Import error: {e}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
