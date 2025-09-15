#!/usr/bin/env python3
"""
Simple YOLO-style Classification Test
Direct ONNX inference without external dependencies
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
    import onnxruntime as ort
    print("✅ Using ONNX Runtime")
except ImportError:
    print("❌ ONNX Runtime not found, install with: pip install onnxruntime")
    sys.exit(1)


def load_model(model_path):
    """Load ONNX classification model - YOLO style"""
    try:
        print(f"🔧 Loading model: {model_path}")
        
        # Load ONNX model
        model = ort.InferenceSession(model_path)
        
        # Load class names from JSON
        json_path = model_path.replace('.onnx', '.json')
        names = {}
        
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                class_mapping = json.load(f)
            
            # Convert to YOLO-style names dict
            for k, v in class_mapping.items():
                names[int(k)] = v
        else:
            print(f"⚠️  Class mapping not found: {json_path}")
            # Get number of classes from model output
            output_shape = model.get_outputs()[0].shape
            num_classes = output_shape[-1]
            names = {i: f"class_{i}" for i in range(num_classes)}
        
        print(f"✅ Model loaded with {len(names)} classes")
        print(f"📋 Classes: {names}")
        
        return model, names
        
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        raise


def preprocess_image(image_path, imgsz=448):
    """Preprocess image for YOLO classification"""
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Failed to load image: {image_path}")
    
    print(f"📷 Original image shape: {img.shape}")
    
    # Convert BGR to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Resize to model input size
    img_resized = cv2.resize(img_rgb, (imgsz, imgsz))
    
    # Normalize to [0, 1]
    img_normalized = img_resized.astype(np.float32) / 255.0
    
    # Transpose to CHW format (channels first)
    img_chw = np.transpose(img_normalized, (2, 0, 1))
    
    # Add batch dimension
    img_batch = np.expand_dims(img_chw, axis=0)
    
    print(f"📊 Preprocessed shape: {img_batch.shape}")
    return img_batch


def run_inference(model, image_batch):
    """Run ONNX inference - YOLO style"""
    try:
        # Get input/output names
        input_name = model.get_inputs()[0].name
        output_name = model.get_outputs()[0].name
        
        print(f"🧠 Input: {input_name}, Output: {output_name}")
        
        # Run inference
        outputs = model.run([output_name], {input_name: image_batch})
        logits = outputs[0][0]  # Remove batch dimension
        
        print(f"📈 Raw logits: {logits}")
        
        # Apply softmax to get probabilities
        exp_logits = np.exp(logits - np.max(logits))  # Numerical stability
        probs = exp_logits / np.sum(exp_logits)
        
        print(f"📊 Probabilities: {probs}")
        
        return probs
        
    except Exception as e:
        print(f"❌ Inference failed: {e}")
        raise


def get_top_predictions(probs, names, top_k=5):
    """Get top-k predictions - YOLO style"""
    # Get top-k indices
    top_indices = np.argsort(probs)[::-1][:top_k]
    top_confidences = probs[top_indices]
    
    # Create results
    results = {
        'top_indices': top_indices.tolist(),
        'top_labels': [names[int(i)] for i in top_indices],
        'top_scores': top_confidences.tolist()
    }
    
    return results


def classify_image(model_path, image_path, imgsz=448, device='cpu', top_k=5):
    """Main classification function - YOLO style"""
    
    print(f"🧪 YOLO Classification")
    print(f"Model: {model_path}")
    print(f"Image: {image_path}")
    print(f"Image Size: {imgsz}x{imgsz}")
    print(f"Device: {device}")
    print("-" * 50)
    
    # Check if image exists
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return None
    
    try:
        # Load model
        model, names = load_model(model_path)
        
        # Preprocess image
        image_batch = preprocess_image(image_path, imgsz)
        
        # Run inference
        probs = run_inference(model, image_batch)
        
        # Get top predictions
        results = get_top_predictions(probs, names, top_k)
        
        # Print YOLO-style results
        print(f"\n🎯 Results for: {os.path.basename(image_path)}")
        print(f"Top-{top_k} indices: {results['top_indices']}")
        print(f"Top-{top_k} labels : {results['top_labels']}")
        print(f"Top-{top_k} scores : {[f'{score:.4f}' for score in results['top_scores']]}")
        
        print(f"\n📋 Detailed Results:")
        for i, (idx, label, score) in enumerate(zip(results['top_indices'], 
                                                   results['top_labels'], 
                                                   results['top_scores'])):
            print(f"   #{i+1}: {label} ({score:.4f})")
        
        return results
        
    except Exception as e:
        print(f"❌ Classification failed: {e}")
        return None


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description="YOLO-style Classification Test")
    parser.add_argument('--model', '-m', type=str, 
                       default='model/classification/yolov11n-cls.onnx',
                       help='Path to ONNX model file')
    parser.add_argument('--image', '-i', type=str, required=True,
                       help='Path to test image')
    parser.add_argument('--imgsz', type=int, default=224,
                       help='Image size for inference (default: 224)')
    parser.add_argument('--device', type=str, default='cpu',
                       help='Device (cpu only for ONNX, default: cpu)')
    parser.add_argument('--top-k', type=int, default=5,
                       help='Number of top predictions (default: 5)')
    
    args = parser.parse_args()
    
    # Run classification
    results = classify_image(args.model, args.image, args.imgsz, args.device, args.top_k)
    
    if results:
        print("\n✅ Classification completed successfully!")
    else:
        print("\n❌ Classification failed!")
        sys.exit(1)


def quick_test():
    """Quick test function - modify paths here"""
    # ============ CONFIGURATION ============
    MODEL_PATH = r"model/classification/yolov11n-cls.onnx"  # <--- CHANGE THIS
    TEST_IMG = r"test_data/pilsner333_sample.jpg"  # <--- CHANGE THIS
    IMGSZ = 224
    DEVICE = 'cpu'
    TOP_K = 5
    # =======================================
    
    print("🚀 Quick YOLO Classification Test")
    print("=" * 40)
    
    # Check if files exist
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Model not found: {MODEL_PATH}")
        print("Available models:")
        model_dir = "model/classification"
        if os.path.exists(model_dir):
            models = [f for f in os.listdir(model_dir) if f.endswith('.onnx')]
            for model in models:
                print(f"   - {os.path.join(model_dir, model)}")
        return
    
    if not os.path.exists(TEST_IMG):
        print(f"❌ Test image not found: {TEST_IMG}")
        print("Looking for available test images...")
        
        # Search for images in common directories
        search_dirs = ['test_data', 'examples', '.']
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                images = []
                for ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                    images.extend([f for f in os.listdir(search_dir) if f.lower().endswith(ext)])
                
                if images:
                    print(f"   {search_dir}/:")
                    for img in images[:5]:  # Show first 5
                        print(f"     - {os.path.join(search_dir, img)}")
                    if len(images) > 5:
                        print(f"     ... and {len(images) - 5} more")
        return
    
    # Run classification
    results = classify_image(MODEL_PATH, TEST_IMG, IMGSZ, DEVICE, TOP_K)
    
    if results:
        print("\n" + "=" * 50)
        print("🎉 YOLO-style Results Summary:")
        print("=" * 50)
        
        # YOLO format output
        r = results  # Simulate YOLO result object
        top5_idx = r['top_indices']
        model_names = dict(enumerate(r['top_labels']))  # Simulate model.names
        
        print('Top-5 indices:', top5_idx)
        print('Top-5 labels :', [model_names[i] if i < len(model_names) else r['top_labels'][i] for i in range(len(top5_idx))])
        print('Top-5 scores :', [f'{score:.4f}' for score in r['top_scores']])


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Run quick test if no arguments provided
        quick_test()
    else:
        # Run with command line arguments
        main()