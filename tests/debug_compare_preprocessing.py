#!/usr/bin/env python3
"""
Debug script to compare preprocessing between test_simple_classification and classification_tool
"""
import numpy as np
import cv2
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import onnxruntime as ort
    print("✅ Using ONNX Runtime")
except ImportError:
    print("❌ ONNX Runtime not found")
    sys.exit(1)

# Import classification tool
from tools.classification.classification_tool import ClassificationTool


def test_script_preprocessing(image, imgsz=448):
    """Preprocessing from test_simple_classification.py"""
    print(f"🔧 Test script preprocessing: {image.shape} -> {imgsz}x{imgsz}")
    
    # Convert BGR to RGB
    img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    print(f"   After BGR->RGB: {img_rgb.shape}")
    
    # Resize to model input size
    img_resized = cv2.resize(img_rgb, (imgsz, imgsz))
    print(f"   After resize: {img_resized.shape}")
    
    # Normalize to [0, 1]
    img_normalized = img_resized.astype(np.float32) / 255.0
    print(f"   After normalize: {img_normalized.shape}, range=[{img_normalized.min():.3f}, {img_normalized.max():.3f}]")
    
    # Transpose to CHW format (channels first)
    img_chw = np.transpose(img_normalized, (2, 0, 1))
    print(f"   After CHW: {img_chw.shape}")
    
    # Add batch dimension
    img_batch = np.expand_dims(img_chw, axis=0)
    print(f"   Final tensor: {img_batch.shape}")
    
    return img_batch


def tool_preprocessing(image):
    """Preprocessing from classification_tool"""
    print(f"🔧 Classification tool preprocessing: {image.shape}")
    
    # Create tool instance
    config = {
        "model_name": "yolov11n-cls",
        "input_width": 448,
        "input_height": 448
    }
    tool = ClassificationTool(config=config)
    tool.setup_config()
    
    # Use tool's preprocessing
    result = tool._preprocess_image(image)
    print(f"   Tool result: {result.shape}")
    
    return result


def run_inference_comparison(tensor1, tensor2, model_path):
    """Compare inference results"""
    print(f"\n🧠 Running inference comparison")
    
    # Load model
    model = ort.InferenceSession(model_path)
    input_name = model.get_inputs()[0].name
    output_name = model.get_outputs()[0].name
    
    # Test script inference
    print(f"📊 Test script inference:")
    outputs1 = model.run([output_name], {input_name: tensor1})
    logits1 = outputs1[0][0]
    print(f"   Raw logits: {logits1}")
    
    # Apply softmax
    exp_logits1 = np.exp(logits1 - np.max(logits1))
    probs1 = exp_logits1 / np.sum(exp_logits1)
    print(f"   Probabilities: {probs1}")
    print(f"   Top class: {np.argmax(probs1)} with confidence {np.max(probs1):.4f}")
    
    # Tool inference
    print(f"📊 Classification tool inference:")
    outputs2 = model.run([output_name], {input_name: tensor2})
    logits2 = outputs2[0][0]
    print(f"   Raw logits: {logits2}")
    
    # Apply softmax
    exp_logits2 = np.exp(logits2 - np.max(logits2))
    probs2 = exp_logits2 / np.sum(exp_logits2)
    print(f"   Probabilities: {probs2}")
    print(f"   Top class: {np.argmax(probs2)} with confidence {np.max(probs2):.4f}")
    
    # Compare
    print(f"\n🔍 Comparison:")
    print(f"   Tensors equal: {np.allclose(tensor1, tensor2, atol=1e-6)}")
    print(f"   Logits equal: {np.allclose(logits1, logits2, atol=1e-6)}")
    print(f"   Probabilities equal: {np.allclose(probs1, probs2, atol=1e-6)}")


def main():
    """Main comparison function"""
    print("🔬 Preprocessing Comparison Debug")
    print("=" * 50)
    
    # Create test image or load real image
    test_image_path = "/home/pi/Desktop/project/image/pilsner333/pilsner333_3.jpg"
    
    try:
        # Load image
        image = cv2.imread(test_image_path)
        if image is None:
            # Create synthetic image
            print("⚠️  Creating synthetic test image")
            image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        else:
            print(f"✅ Loaded image: {test_image_path}")
        
        print(f"📷 Input image shape: {image.shape}")
        
        # Test both preprocessing methods
        tensor1 = test_script_preprocessing(image, 448)
        tensor2 = tool_preprocessing(image)
        
        # Compare tensors
        print(f"\n🔍 Tensor comparison:")
        print(f"   Test script tensor: {tensor1.shape}")
        print(f"   Tool tensor: {tensor2.shape}")
        print(f"   Shapes equal: {tensor1.shape == tensor2.shape}")
        
        if tensor1.shape == tensor2.shape:
            print(f"   Values equal: {np.allclose(tensor1, tensor2, atol=1e-6)}")
            print(f"   Max difference: {np.max(np.abs(tensor1 - tensor2))}")
            
            # Show sample values
            print(f"   Test script sample: {tensor1[0, 0, 0, :5]}")
            print(f"   Tool sample: {tensor2[0, 0, 0, :5]}")
        
        # Run inference comparison
        model_path = "model/classification/yolov11n-cls.onnx"
        if Path(model_path).exists():
            run_inference_comparison(tensor1, tensor2, model_path)
        else:
            print(f"⚠️  Model not found: {model_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()