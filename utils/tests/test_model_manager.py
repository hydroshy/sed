#!/usr/bin/env python3
"""
Test script for ModelManager to verify model loading functionality
"""

import sys
import os
import json
import logging
from pathlib import Path

# Import test utilities
from utils.tests.test_utils import setup_test_path
setup_test_path()

from tools.detection.model_manager import ModelManager

def test_model_manager():
    """Test ModelManager functionality"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("Testing ModelManager...")
    
    # Initialize model manager
    model_manager = ModelManager()
    print(f"Models directory: {model_manager.models_dir}")
    print(f"Directory exists: {model_manager.models_dir.exists()}")
    
    # List files in directory
    if model_manager.models_dir.exists():
        files = list(model_manager.models_dir.iterdir())
        print(f"Files in directory: {[f.name for f in files]}")
    
    # Get available models
    models = model_manager.get_available_models()
    print(f"Available models: {models}")
    
    # Test each model
    for model_name in models:
        print(f"\nTesting model: {model_name}")
        model_info = model_manager.get_model_info(model_name)
        if model_info:
            print(f"  Classes: {len(model_info['classes'])} classes")
            print(f"  First 5 classes: {model_info['classes'][:5]}")
            print(f"  Path: {model_info['path']}")
            
            # Show JSON file if exists
            json_file = model_manager.models_dir / f"{model_name}.json"
            if json_file.exists():
                print(f"  JSON metadata: {json_file}")
        else:
            print(f"  Failed to load model info")
    
    # Test specific JSON format parsing
    print("\nTesting JSON format parsing...")
    test_json_formats = [
        # Format 1: List in 'classes' key
        {"classes": ["class1", "class2", "class3"]},
        # Format 2: Dict in 'classes' key
        {"classes": {"0": "class1", "1": "class2", "2": "class3"}},
        # Format 3: Root level dict
        {"0": "class1", "1": "class2", "2": "class3"}
    ]
    
    for i, test_format in enumerate(test_json_formats):
        test_file = model_manager.models_dir / f"test_format_{i}.json"
        try:
            with open(test_file, 'w') as f:
                json.dump(test_format, f)
            print(f"  Test format {i+1}: Created {test_file}")
        except Exception as e:
            print(f"  Test format {i+1}: Error - {e}")
    
    # Auto-generate metadata for models that don't have JSON files
    print("\nAuto-generating metadata for models without JSON files...")
    for model_name in models:
        json_file = model_manager.models_dir / f"{model_name}.json"
        if not json_file.exists():
            print(f"Creating metadata for {model_name}...")
            model_manager.auto_generate_metadata(model_name)
    
    print("\nTest completed.")

if __name__ == "__main__":
    test_model_manager()
