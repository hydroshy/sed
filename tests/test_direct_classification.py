#!/usr/bin/env python3
"""
Test classification tool directly with the same image used in debug
"""
import sys
import cv2
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tools.classification.classification_tool import ClassificationTool

def main():
    print("🧪 Direct Classification Tool Test")
    print("=" * 50)
    
    # Load the same image used in debug
    image_path = "/home/pi/Desktop/project/image/pilsner333/pilsner333_3.jpg"
    image = cv2.imread(image_path)
    
    if image is None:
        print(f"❌ Failed to load image: {image_path}")
        return
    
    print(f"✅ Loaded image: {image.shape}")
    
    # Create classification tool with same config as debug
    config = {
        "model_name": "yolov11n-cls",
        "input_width": 448,
        "input_height": 448,
        "expected_class_name": "pilsner333"  # For OK/NG evaluation
    }
    
    tool = ClassificationTool(config=config)
    tool.setup_config()
    
    print(f"📋 Tool config:")
    print(f"   Model: {tool.config.get('model_name')}")
    print(f"   Input size: {tool.config.get('input_width')}x{tool.config.get('input_height')}")
    print(f"   Expected class: {tool.config.get('expected_class_name')}")
    
    # Process the image
    try:
        print(f"\n🔄 Processing image...")
        result_image, results = tool.process(image)  # Unpack tuple!
        
        print(f"\n📊 Results:")
        print(f"   Status: {results.get('status')}")
        print(f"   Results count: {results.get('result_count', 0)}")
        
        if 'results' in results and results['results']:
            for i, result in enumerate(results['results']):
                print(f"   Result {i+1}:")
                predictions = result.get('predictions', [])
                print(f"     Predictions count: {len(predictions)}")
                
                for j, pred in enumerate(predictions[:5]):  # Show top 5
                    class_name = pred.get('class_name', 'unknown')
                    confidence = pred.get('confidence', 0.0)
                    class_id = pred.get('class_id', -1)
                    print(f"       #{j+1}: {class_name} (ID:{class_id}) - {confidence:.4f}")
        
        print(f"\n✅ Classification completed!")
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()