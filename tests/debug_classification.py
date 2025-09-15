#!/usr/bin/env python3
"""
Debug Classification Tool Output
Kiểm tra model có thực sự output pilsner333 0.73 cho mọi input hay không
"""

import os
import sys
import cv2
import json
import numpy as np
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from tools.classification_tool import ClassificationTool
except ImportError:
    print("❌ Error: Could not import ClassificationTool")
    sys.exit(1)

def debug_classification():
    print("🔍 Debug Classification Tool Output")
    print("=" * 50)
    
    # Setup logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Check model files
    model_name = "yolov11n-cls"
    model_path = f"model/classification/{model_name}.onnx"
    json_path = f"model/classification/{model_name}.json"
    
    print(f"📁 Checking model files:")
    print(f"   Model: {model_path} - {'✅' if os.path.exists(model_path) else '❌'}")
    print(f"   Config: {json_path} - {'✅' if os.path.exists(json_path) else '❌'}")
    
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            model_config = json.load(f)
        print(f"📋 Model config: {model_config}")
    
    # Create minimal config WITHOUT expected_class
    config = {
        'model_name': model_name,
        'draw_result': False,  # Disable drawing to see raw output
        'result_display_enable': False,  # Disable OK/NG to see raw predictions
        'top_k': 5,  # Get top 5 predictions
        'use_rgb': True,
        'normalize': True
    }
    
    print(f"\n🔧 Tool config: {config}")
    
    # Initialize tool
    tool = ClassificationTool("debug_classification", config)
    
    # Test different images
    test_cases = [
        ("Black image", np.zeros((224, 224, 3), dtype=np.uint8)),
        ("White image", np.ones((224, 224, 3), dtype=np.uint8) * 255),
        ("Red image", np.zeros((224, 224, 3), dtype=np.uint8)),
        ("Random image", np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)),
        ("Gradient image", None)  # Will create below
    ]
    
    # Create gradient image
    gradient = np.zeros((224, 224, 3), dtype=np.uint8)
    for i in range(224):
        gradient[i, :] = [i, 255-i, 128]
    test_cases[4] = ("Gradient image", gradient)
    
    # Red image setup
    test_cases[2] = ("Red image", np.zeros((224, 224, 3), dtype=np.uint8))
    test_cases[2][1][:, :, 2] = 255  # Set red channel
    
    print(f"\n🧪 Testing {len(test_cases)} different images...")
    print("-" * 50)
    
    for i, (name, image) in enumerate(test_cases):
        print(f"\n🖼️  Test {i+1}: {name}")
        print(f"   Shape: {image.shape}")
        print(f"   Data range: {image.min()}-{image.max()}")
        print(f"   Sample pixel [0,0]: {image[0,0]}")
        print(f"   Sample pixel [112,112]: {image[112,112]}")
        
        try:
            # Run classification
            result_image, result_data = tool.process(image)
            
            print(f"   📊 Results:")
            if result_data and 'predictions' in result_data:
                predictions = result_data['predictions']
                print(f"      Number of predictions: {len(predictions)}")
                
                for j, pred in enumerate(predictions):
                    if isinstance(pred, dict):
                        class_name = pred.get('class_name', 'unknown')
                        confidence = pred.get('confidence', 0.0)
                        print(f"      {j+1}. {class_name}: {confidence:.6f}")
                    else:
                        print(f"      {j+1}. {pred}")
            else:
                print(f"      ❌ No predictions found")
                print(f"      Raw result_data: {result_data}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n🔍 Summary:")
    print("If all images give the same prediction (pilsner333, 0.73), then:")
    print("1. Model might be corrupted/not loading properly")
    print("2. Model might be returning cached/default values")
    print("3. Input preprocessing might be wrong")
    print("4. Model file might be empty or invalid")
    
    # Check model file size
    if os.path.exists(model_path):
        size = os.path.getsize(model_path)
        print(f"\n📏 Model file size: {size:,} bytes ({size/1024/1024:.1f} MB)")
        if size < 1000:
            print("⚠️  Model file is very small - might be corrupted!")

if __name__ == "__main__":
    debug_classification()