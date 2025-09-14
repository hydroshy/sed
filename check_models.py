#!/usr/bin/env python3
"""
Kiểm tra các model files trong project
"""
import os
from pathlib import Path

def check_models():
    """Kiểm tra tất cả model files"""
    project_root = Path(__file__).parent
    
    print("=== Checking Model Files ===")
    
    # Check detection models
    detect_dir = project_root / "model" / "detect"
    print(f"\n📁 Detection models ({detect_dir}):")
    if detect_dir.exists():
        for file in sorted(detect_dir.iterdir()):
            print(f"  ✓ {file.name}")
    else:
        print("  ❌ Directory not found")
    
    # Check classification models  
    class_dir = project_root / "model" / "classification"
    print(f"\n📁 Classification models ({class_dir}):")
    if class_dir.exists():
        for file in sorted(class_dir.iterdir()):
            print(f"  ✓ {file.name}")
    else:
        print("  ❌ Directory not found")
    
    # Search for yolov11n-cls anywhere
    print(f"\n🔍 Searching for yolov11n-cls files:")
    found_cls = []
    for root, dirs, files in os.walk(project_root):
        for file in files:
            if 'yolov11n-cls' in file:
                found_cls.append(os.path.join(root, file))
    
    if found_cls:
        for file in found_cls:
            print(f"  ✓ Found: {file}")
    else:
        print("  ❌ No yolov11n-cls files found")
    
    # Check what ModelManager sees
    print(f"\n🤖 ModelManager results:")
    try:
        import sys
        sys.path.insert(0, str(project_root))
        
        from tools.detection.model_manager import ModelManager
        
        # Detection models
        detect_mm = ModelManager(str(detect_dir))
        detect_models = detect_mm.get_available_models()
        print(f"  Detection models: {detect_models}")
        
        # Classification models
        class_mm = ModelManager(str(class_dir))  
        class_models = class_mm.get_available_models()
        print(f"  Classification models: {class_models}")
        
    except Exception as e:
        print(f"  ❌ Error testing ModelManager: {e}")

if __name__ == "__main__":
    check_models()