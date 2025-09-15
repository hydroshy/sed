#!/usr/bin/env python3
"""
YOLO Classification Test Script
Test classification model using YOLO inference style
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
    from ultralytics import YOLO
    print("✅ Using ultralytics YOLO")
except ImportError:
    print("❌ ultralytics not found, falling back to ONNX inference")
    YOLO = None

import onnxruntime as ort


class YOLOClassificationTester:
    """YOLO-style classification tester"""
    
    def __init__(self, model_path, imgsz=224, device='cpu'):
        self.model_path = model_path
        self.imgsz = imgsz
        self.device = device
        self.model = None
        self.names = {}
        
        # Load model
        self._load_model()
    
    def _load_model(self):
        """Load YOLO classification model"""
        try:
            if YOLO and self.model_path.endswith('.pt'):
                # Use ultralytics YOLO for .pt files
                print(f"🔧 Loading YOLO model: {self.model_path}")
                self.model = YOLO(self.model_path, task='classify')
                self.names = self.model.names
                print(f"✅ YOLO model loaded with {len(self.names)} classes")
                
            elif self.model_path.endswith('.onnx'):
                # Use ONNX Runtime for .onnx files
                print(f"🔧 Loading ONNX model: {self.model_path}")
                self.model = ort.InferenceSession(self.model_path)
                
                # Load class names from JSON
                json_path = self.model_path.replace('.onnx', '.json')
                if os.path.exists(json_path):
                    with open(json_path, 'r') as f:
                        class_mapping = json.load(f)
                    
                    # Convert to names dict (YOLO style)
                    if isinstance(class_mapping, dict):
                        # Handle both {0: "class0", 1: "class1"} and {"0": "class0", "1": "class1"}
                        self.names = {}
                        for k, v in class_mapping.items():
                            self.names[int(k)] = v
                    
                    print(f"✅ ONNX model loaded with {len(self.names)} classes")
                    print(f"📋 Classes: {self.names}")
                else:
                    print(f"⚠️  Class mapping file not found: {json_path}")
                    self.names = {0: "class_0", 1: "class_1"}  # Default
                    
            else:
                raise ValueError(f"Unsupported model format: {self.model_path}")
                
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise
    
    def _preprocess_image(self, image_path):
        """Preprocess image for classification"""
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Resize to model input size
        img_resized = cv2.resize(img_rgb, (self.imgsz, self.imgsz))
        
        # Normalize to [0, 1]
        img_normalized = img_resized.astype(np.float32) / 255.0
        
        # Transpose to CHW format (channels first)
        img_chw = np.transpose(img_normalized, (2, 0, 1))
        
        # Add batch dimension
        img_batch = np.expand_dims(img_chw, axis=0)
        
        return img_batch
    
    def predict(self, image_path, top_k=5):
        """Run prediction on image"""
        try:
            print(f"🧪 Processing: {image_path}")
            
            if YOLO and hasattr(self.model, 'predict'):
                # Use ultralytics YOLO
                results = self.model(image_path, imgsz=self.imgsz, device=self.device)
                result = results[0]
                
                # Get probabilities
                probs = result.probs
                top5_idx = probs.top5
                top5_conf = probs.top5conf.tolist()
                
                # Create YOLO-style output
                class YOLOResult:
                    def __init__(self, probs, names):
                        self.probs = probs
                        self.names = names
                
                class YOLOProbs:
                    def __init__(self, top5_idx, top5_conf):
                        self.top5 = top5_idx
                        self.top5conf = top5_conf
                
                result_obj = YOLOResult(YOLOProbs(top5_idx, top5_conf), self.names)
                return result_obj
                
            else:
                # Use ONNX Runtime
                img_batch = self._preprocess_image(image_path)
                
                # Get input/output names
                input_name = self.model.get_inputs()[0].name
                output_name = self.model.get_outputs()[0].name
                
                # Run inference
                outputs = self.model.run([output_name], {input_name: img_batch})
                logits = outputs[0][0]  # Remove batch dimension
                
                # Apply softmax to get probabilities
                exp_logits = np.exp(logits - np.max(logits))  # Numerical stability
                probs = exp_logits / np.sum(exp_logits)
                
                # Get top-k indices and confidences
                top_indices = np.argsort(probs)[::-1][:top_k]
                top_confidences = probs[top_indices].tolist()
                
                # Create YOLO-style result object
                class ONNXResult:
                    def __init__(self, top_indices, top_confidences, names):
                        self.probs = self
                        self.names = names
                        self.top5 = top_indices
                        self.top5conf = top_confidences
                
                return ONNXResult(top_indices, top_confidences, self.names)
                
        except Exception as e:
            print(f"❌ Prediction failed: {e}")
            raise
    
    def test_image(self, image_path, top_k=5):
        """Test single image with YOLO-style output"""
        if not os.path.exists(image_path):
            print(f"❌ Image not found: {image_path}")
            return None
        
        try:
            # Run prediction
            result = self.predict(image_path, top_k)
            
            # Print YOLO-style results
            print(f"📊 Results for: {os.path.basename(image_path)}")
            print(f"   Image size: {self.imgsz}x{self.imgsz}")
            print(f"   Device: {self.device}")
            
            top_indices = result.probs.top5[:top_k]
            top_confidences = result.probs.top5conf[:top_k] if hasattr(result.probs, 'top5conf') else result.probs.top5conf
            
            print(f"   Top-{top_k} indices: {top_indices}")
            print(f"   Top-{top_k} labels : {[result.names[int(i)] for i in top_indices]}")
            print(f"   Top-{top_k} scores : {[f'{conf:.4f}' for conf in top_confidences]}")
            
            # Print detailed results
            print(f"\n📋 Detailed Results:")
            for i, (idx, conf) in enumerate(zip(top_indices, top_confidences)):
                class_name = result.names[int(idx)]
                print(f"   #{i+1}: {class_name} ({conf:.4f})")
            
            return result
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return None


def main():
    """Main function with YOLO-style interface"""
    parser = argparse.ArgumentParser(description="YOLO Classification Test")
    parser.add_argument('--model', '-m', type=str, required=True,
                       help='Path to model file (.onnx or .pt)')
    parser.add_argument('--image', '-i', type=str, required=True,
                       help='Path to test image')
    parser.add_argument('--imgsz', type=int, default=224,
                       help='Image size for inference (default: 224)')
    parser.add_argument('--device', type=str, default='cpu',
                       help='Device to use (cpu/cuda, default: cpu)')
    parser.add_argument('--top-k', type=int, default=5,
                       help='Number of top predictions to show (default: 5)')
    
    args = parser.parse_args()
    
    print("🧪 YOLO Classification Test")
    print(f"Model: {args.model}")
    print(f"Image: {args.image}")
    print(f"Image Size: {args.imgsz}")
    print(f"Device: {args.device}")
    print("-" * 50)
    
    # Initialize tester
    try:
        tester = YOLOClassificationTester(args.model, args.imgsz, args.device)
    except Exception as e:
        print(f"❌ Failed to initialize tester: {e}")
        sys.exit(1)
    
    # Test image
    result = tester.test_image(args.image, args.top_k)
    
    if result:
        print("\n✅ Classification completed successfully!")
    else:
        print("\n❌ Classification failed!")
        sys.exit(1)


def quick_test():
    """Quick test function similar to your example"""
    # Configuration
    MODEL_PATH = r"model/classification/yolov11n-cls.onnx"  # <--- CHANGE THIS
    TEST_IMG = r"test_data/pilsner333_sample.jpg"  # <--- CHANGE THIS
    IMGSZ = 224
    DEVICE = 'cpu'
    
    print("🚀 Quick YOLO Classification Test")
    print(f"Model: {MODEL_PATH}")
    print(f"Image: {TEST_IMG}")
    print("-" * 40)
    
    # Initialize model
    try:
        tester = YOLOClassificationTester(MODEL_PATH, IMGSZ, DEVICE)
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        return
    
    # Test image
    if os.path.exists(TEST_IMG):
        result = tester.test_image(TEST_IMG)
        
        if result:
            # YOLO-style output
            top5_idx = result.probs.top5
            print('\n🎯 YOLO-style Results:')
            print('Top-5 indices:', top5_idx)
            print('Top-5 labels :', [tester.names[int(i)] for i in top5_idx])
            
            if hasattr(result.probs, 'top5conf'):
                print('Top-5 scores :', [f'{conf:.4f}' for conf in result.probs.top5conf])
    else:
        print(f'❌ Set TEST_IMG to a valid path. Current: {TEST_IMG}')
        
        # Show available test images
        test_dirs = ['test_data', 'model/test', 'examples']
        print('\n📁 Looking for test images...')
        for test_dir in test_dirs:
            if os.path.exists(test_dir):
                images = [f for f in os.listdir(test_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                if images:
                    print(f'   {test_dir}/: {images[:3]}{"..." if len(images) > 3 else ""}')


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Run quick test if no arguments
        quick_test()
    else:
        # Run with command line arguments
        main()