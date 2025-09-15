#!/usr/bin/env python3
"""
YOLO-style Classification Test using existing project tools
No external dependencies required
"""

import os
import sys
import cv2
import json
import argparse
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from tools.classification_tool import ClassificationTool
    print("✅ Using project ClassificationTool")
except ImportError:
    print("❌ Could not import ClassificationTool")
    sys.exit(1)


class YOLOStyleClassifier:
    """YOLO-style interface for project ClassificationTool"""
    
    def __init__(self, model_path, imgsz=224, device='cpu'):
        self.model_path = model_path
        self.imgsz = imgsz
        self.device = device
        self.names = {}
        
        # Extract model name from path
        self.model_name = os.path.basename(model_path).replace('.onnx', '')
        
        # Setup tool
        self._setup_tool()
        self._load_class_names()
    
    def _setup_tool(self):
        """Setup ClassificationTool"""
        try:
            print(f"🔧 Setting up ClassificationTool: {self.model_name}")
            
            config = {
                'model_name': self.model_name,
                'draw_result': False,
                'result_display_enable': False,
                'top_k': 10,  # Get more results for top-k selection
                'use_rgb': True,
                'normalize': True
            }
            
            self.tool = ClassificationTool("yolo_test", config)
            print("✅ ClassificationTool setup successful")
            
        except Exception as e:
            print(f"❌ Failed to setup ClassificationTool: {e}")
            raise
    
    def _load_class_names(self):
        """Load class names in YOLO format"""
        try:
            json_path = f"model/classification/{self.model_name}.json"
            
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    class_mapping = json.load(f)
                
                # Convert to YOLO-style names dict
                for k, v in class_mapping.items():
                    self.names[int(k)] = v
                
                print(f"📋 Loaded {len(self.names)} classes: {self.names}")
            else:
                print(f"⚠️  Class mapping not found: {json_path}")
                self.names = {0: "class_0", 1: "class_1"}
                
        except Exception as e:
            print(f"❌ Error loading class names: {e}")
            self.names = {0: "unknown", 1: "pilsner333"}
    
    def predict(self, image_path, top_k=5):
        """Run prediction with YOLO-style output"""
        try:
            print(f"🧪 Processing: {os.path.basename(image_path)}")
            
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Failed to load image: {image_path}")
            
            print(f"📷 Image shape: {image.shape}")
            
            # Resize to target size if specified
            if self.imgsz != image.shape[0] or self.imgsz != image.shape[1]:
                image = cv2.resize(image, (self.imgsz, self.imgsz))
                print(f"📐 Resized to: {image.shape}")
            
            # Run classification through tool
            result_image, result_data = self.tool.process(image)
            
            # Parse results
            predictions = []
            if result_data and 'results' in result_data:
                for result in result_data['results']:
                    if 'predictions' in result:
                        predictions.extend(result['predictions'])
            
            if not predictions:
                print("⚠️  No predictions found")
                return None
            
            # Sort by confidence (descending)
            predictions.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            # Limit to top_k
            top_predictions = predictions[:top_k]
            
            # Create YOLO-style result
            result = YOLOResult()
            result.probs = YOLOProbs()
            result.names = self.names
            
            # Fill top-k data
            result.probs.top5 = [pred.get('class_id', 0) for pred in top_predictions]
            result.probs.top5conf = [pred.get('confidence', 0.0) for pred in top_predictions]
            result.probs.data = predictions  # Store all predictions
            
            return result
            
        except Exception as e:
            print(f"❌ Prediction failed: {e}")
            import traceback
            traceback.print_exc()
            return None


class YOLOResult:
    """Mock YOLO result object"""
    def __init__(self):
        self.probs = None
        self.names = {}


class YOLOProbs:
    """Mock YOLO probabilities object"""
    def __init__(self):
        self.top5 = []
        self.top5conf = []
        self.data = []


def classify_image_yolo_style(model_path, image_path, imgsz=224, device='cpu', top_k=5):
    """Main classification function - YOLO style"""
    
    print(f"🧪 YOLO-style Classification")
    print(f"Model: {model_path}")
    print(f"Image: {image_path}")
    print(f"Image Size: {imgsz}x{imgsz}")
    print(f"Device: {device}")
    print("-" * 50)
    
    # Check if files exist
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return None
    
    if not os.path.exists(model_path):
        print(f"❌ Model not found: {model_path}")
        return None
    
    try:
        # Initialize classifier
        classifier = YOLOStyleClassifier(model_path, imgsz, device)
        
        # Run prediction
        result = classifier.predict(image_path, top_k)
        
        if result is None:
            print("❌ Prediction failed")
            return None
        
        # Extract results
        top5_idx = result.probs.top5
        top5_conf = result.probs.top5conf
        names = result.names
        
        # Print YOLO-style results
        print(f"\n🎯 Results for: {os.path.basename(image_path)}")
        print(f"Top-{len(top5_idx)} indices: {top5_idx}")
        print(f"Top-{len(top5_idx)} labels : {[names.get(int(i), f'class_{i}') for i in top5_idx]}")
        print(f"Top-{len(top5_idx)} scores : {[f'{conf:.4f}' for conf in top5_conf]}")
        
        print(f"\n📋 Detailed Results:")
        for i, (idx, conf) in enumerate(zip(top5_idx, top5_conf)):
            class_name = names.get(int(idx), f'class_{idx}')
            print(f"   #{i+1}: {class_name} ({conf:.4f})")
        
        return result
        
    except Exception as e:
        print(f"❌ Classification failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description="YOLO-style Classification using project tools")
    parser.add_argument('--model', '-m', type=str, 
                       default='model/classification/yolov11n-cls.onnx',
                       help='Path to ONNX model file')
    parser.add_argument('--image', '-i', type=str, required=True,
                       help='Path to test image')
    parser.add_argument('--imgsz', type=int, default=224,
                       help='Image size for inference (default: 224)')
    parser.add_argument('--device', type=str, default='cpu',
                       help='Device (default: cpu)')
    parser.add_argument('--top-k', type=int, default=5,
                       help='Number of top predictions (default: 5)')
    
    args = parser.parse_args()
    
    # Run classification
    result = classify_image_yolo_style(args.model, args.image, args.imgsz, args.device, args.top_k)
    
    if result:
        print("\n✅ Classification completed successfully!")
        return True
    else:
        print("\n❌ Classification failed!")
        return False


def quick_test():
    """Quick test function - YOLO style like your example"""
    
    # ============ CONFIGURATION ============
    MODEL_PATH = r"model/classification/yolov11n-cls.onnx"  # <--- CHANGE THIS
    TEST_IMG = r"test_data/pilsner333_sample.jpg"  # <--- CHANGE THIS
    IMGSZ = 224
    DEVICE = 'cpu'
    # =======================================
    
    print("🚀 Quick YOLO Classification Test")
    print("=" * 40)
    
    # Check model exists
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Model not found: {MODEL_PATH}")
        
        # Show available models
        model_dir = "model/classification"
        if os.path.exists(model_dir):
            print("Available models:")
            models = [f for f in os.listdir(model_dir) if f.endswith('.onnx')]
            for model in models:
                full_path = os.path.join(model_dir, model)
                print(f"   - {full_path}")
                # Auto-select first available model
                if not TEST_IMG or not os.path.exists(TEST_IMG):
                    MODEL_PATH = full_path
                    print(f"   → Using: {MODEL_PATH}")
                    break
        else:
            print("Model directory not found!")
            return False
    
    # Check or find test image
    if not os.path.exists(TEST_IMG):
        print(f"⚠️  Test image not found: {TEST_IMG}")
        print("Looking for available images...")
        
        # Search for images
        found_image = None
        search_dirs = ['test_data', 'examples', '.', 'model']
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                for root, dirs, files in os.walk(search_dir):
                    for file in files:
                        if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                            found_image = os.path.join(root, file)
                            print(f"   Found: {found_image}")
                            break
                    if found_image:
                        break
                if found_image:
                    break
        
        if found_image:
            TEST_IMG = found_image
            print(f"   → Using: {TEST_IMG}")
        else:
            print("❌ No test images found!")
            print("Creating synthetic test image...")
            
            # Create a simple test image
            test_img = np.ones((IMGSZ, IMGSZ, 3), dtype=np.uint8) * 128
            test_img[:, :IMGSZ//2] = [30, 215, 255]  # Golden color for pilsner
            TEST_IMG = "synthetic_test.jpg"
            cv2.imwrite(TEST_IMG, test_img)
            print(f"   → Created: {TEST_IMG}")
    
    # Simulate your exact code style
    print(f"\n🔧 YOLO Classification Setup:")
    print(f"model = ClassificationTool('{MODEL_PATH}')")
    print(f"test_img = '{TEST_IMG}'")
    print(f"if os.path.exists(test_img):")
    
    if os.path.exists(TEST_IMG):
        print(f"    # Running classification...")
        
        # Run classification
        result = classify_image_yolo_style(MODEL_PATH, TEST_IMG, IMGSZ, DEVICE)
        
        if result:
            # YOLO-style output like your example
            print(f"\n🎯 YOLO-style Output:")
            print("-" * 30)
            
            top5_idx = result.probs.top5
            print(f"Top-5 indices: {top5_idx}")
            print(f"Top-5 labels : {[result.names.get(int(i), f'class_{i}') for i in top5_idx]}")
            print(f"Top-5 scores : {[f'{conf:.4f}' for conf in result.probs.top5conf]}")
            
            return True
        else:
            print("❌ Classification failed!")
            return False
    else:
        print(f"❌ Set test_img to a valid path. Current: {TEST_IMG}")
        return False


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Run quick test like your example
        success = quick_test()
        if not success:
            sys.exit(1)
    else:
        # Run with command line arguments
        success = main()
        if not success:
            sys.exit(1)