#!/usr/bin/env python3
"""
Test Classification Tool Model Loading
"""
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_model_manager():
    """Test ModelManager for classification models"""
    print("=== Testing ModelManager ===")
    
    from tools.detection.model_manager import ModelManager
    
    # Point to classification directory
    models_dir = project_root / "model" / "classification"
    print(f"Models directory: {models_dir}")
    print(f"Directory exists: {models_dir.exists()}")
    
    if models_dir.exists():
        files = list(models_dir.iterdir())
        print(f"Files in directory: {[f.name for f in files]}")
    
    # Create ModelManager
    model_manager = ModelManager(str(models_dir))
    
    # Test get_available_models
    print("\n--- Testing get_available_models ---")
    models = model_manager.get_available_models()
    print(f"Available models: {models}")
    
    # Test get_model_info for each model
    for model_name in models:
        print(f"\n--- Testing model info for: {model_name} ---")
        info = model_manager.get_model_info(model_name)
        if info:
            print(f"Model info: {info}")
            print(f"Classes: {info.get('classes', [])}")
        else:
            print(f"Failed to get info for {model_name}")

def test_classification_tool_manager():
    """Test ClassificationToolManager directly"""
    print("\n=== Testing ClassificationToolManager ===")
    
    # Mock main window
    class MockMainWindow:
        pass
    
    main_window = MockMainWindow()
    
    from gui.classification_tool_manager import ClassificationToolManager
    
    # Create manager
    ctm = ClassificationToolManager(main_window)
    
    print(f"Model manager initialized: {ctm.model_manager is not None}")
    if ctm.model_manager:
        print(f"Models directory: {ctm.model_manager.models_dir}")
        
        # Test get_available_models
        models = ctm.model_manager.get_available_models()
        print(f"Available models from ClassificationToolManager: {models}")
        
        # Test model info
        for model_name in models:
            info = ctm.model_manager.get_model_info(model_name)
            if info:
                print(f"Model '{model_name}' classes: {info.get('classes', [])}")

if __name__ == "__main__":
    test_model_manager()
    test_classification_tool_manager()