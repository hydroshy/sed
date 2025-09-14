#!/usr/bin/env python3
"""
Test ClassificationToolManager with QComboBox Mock
"""
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_with_mock_combos():
    """Test ClassificationToolManager with mock QComboBox"""
    print("=== Testing ClassificationToolManager with Mock QComboBox ===")
    
    # Mock QComboBox
    class MockComboBox:
        def __init__(self, name):
            self.name = name
            self.items = []
            self.current_index = 0
            self.signals_blocked = False
            
            # Mock signal connections
            class MockSignal:
                def __init__(self, combo_name, signal_name):
                    self.combo_name = combo_name
                    self.signal_name = signal_name
                    
                def connect(self, func):
                    print(f"  {self.combo_name}: connected {self.signal_name}")
                    
                def disconnect(self):
                    print(f"  {self.combo_name}: disconnected {self.signal_name}")
            
            self.currentTextChanged = MockSignal(self.name, "currentTextChanged")
            self.activated = MockSignal(self.name, "activated")
            
        def clear(self):
            self.items = []
            self.current_index = 0
            print(f"  {self.name}: cleared")
            
        def addItem(self, text):
            self.items.append(text)
            print(f"  {self.name}: added '{text}' (total: {len(self.items)})")
            
        def count(self):
            return len(self.items)
            
        def itemText(self, index):
            return self.items[index] if 0 <= index < len(self.items) else ""
            
        def setCurrentIndex(self, index):
            if 0 <= index < len(self.items):
                self.current_index = index
                print(f"  {self.name}: set current index to {index} ('{self.items[index]}')")
                
        def currentText(self):
            return self.items[self.current_index] if 0 <= self.current_index < len(self.items) else ""
            
        def blockSignals(self, block):
            self.signals_blocked = block
            print(f"  {self.name}: signals blocked = {block}")

    # Mock main window
    class MockMainWindow:
        pass
    
    main_window = MockMainWindow()
    
    from gui.classification_tool_manager import ClassificationToolManager
    
    # Create manager
    ctm = ClassificationToolManager(main_window)
    
    # Create mock combos
    model_combo = MockComboBox("ModelComboBox")
    class_combo = MockComboBox("ClassComboBox")
    
    print(f"Created ClassificationToolManager with models dir: {ctm.model_manager.models_dir}")
    
    # Setup UI components
    print("\n--- Setting up UI components ---")
    ctm.setup_ui_components(model_combo, class_combo)
    
    print("\n--- Final state ---")
    print(f"ModelComboBox items: {model_combo.items}")
    print(f"ClassComboBox items: {class_combo.items}")
    
    # Simulate model selection
    if len(model_combo.items) > 1:
        print("\n--- Simulating model selection ---")
        model_name = model_combo.items[1]  # First real model (skip "Select Model...")
        print(f"Selecting model: {model_name}")
        
        # Call the method directly
        ctm._on_model_changed(model_name)
        
        print(f"ClassComboBox after model selection: {class_combo.items}")

if __name__ == "__main__":
    test_with_mock_combos()