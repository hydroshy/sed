#!/usr/bin/env python3
"""
YOLO ONNX Inference Test using Ultralytics
"""

import os
import sys
import cv2
import numpy as np
import time
from ultralytics import YOLO

def preprocess_image(image_path, imgsz=224):
    """Preprocess image for YOLO ONNX inference (manual preprocessing for comparison)"""
    start_time = time.perf_counter()
    
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Failed to load image: {image_path}")
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(img_rgb, (imgsz, imgsz))
    img_normalized = img_resized.astype(np.float32) / 255.0
    img_chw = np.transpose(img_normalized, (2, 0, 1))
    img_batch = np.expand_dims(img_chw, axis=0)
    
    preprocessing_time = (time.perf_counter() - start_time) * 1000
    print(f"⏱️  Manual preprocessing time: {preprocessing_time:.2f} ms")
    
    return img_batch, preprocessing_time

def run_yolo_onnx(model_path, image_path, imgsz=224, device='cpu'):
    print(f"🔧 Loading YOLO ONNX model: {model_path}")
    
    # Measure model loading time
    model_start_time = time.perf_counter()
    model = YOLO(model_path, task='classify')
    model_load_time = (time.perf_counter() - model_start_time) * 1000
    print(f"✅ Model loaded in {model_load_time:.2f} ms!")

    # Measure image loading time
    img_load_start_time = time.perf_counter()
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Failed to load image: {image_path}")
    img_load_time = (time.perf_counter() - img_load_start_time) * 1000
    print(f"📷 Image loaded in {img_load_time:.2f} ms")

    # Measure total inference time (including preprocessing)
    inference_start_time = time.perf_counter()
    results = model(img, imgsz=imgsz, device=device, verbose=False)
    inference_time = (time.perf_counter() - inference_start_time) * 1000
    
    # Calculate total time
    total_time = model_load_time + img_load_time + inference_time
    
    print("🎯 Results:")
    for i, pred in enumerate(results):
        print(f"Image {i}:")
        print("  Top-1:", pred.names[pred.probs.top1], f"({pred.probs.top1conf:.4f})")
        print("  Top-5:", [pred.names[idx] for idx in pred.probs.top5], [f"{conf:.4f}" for conf in pred.probs.top5conf])
    
    # Print timing summary
    print(f"\n⏱️  Timing Summary (Ultralytics YOLO):")
    print(f"   Model loading:  {model_load_time:8.2f} ms")
    print(f"   Image loading:  {img_load_time:8.2f} ms")
    print(f"   Inference:      {inference_time:8.2f} ms")
    print(f"   Total:          {total_time:8.2f} ms")
    print(f"   FPS:            {1000.0/total_time:8.2f}")
    
    return {
        'results': results,
        'timing': {
            'model_load_ms': model_load_time,
            'image_load_ms': img_load_time,
            'inference_ms': inference_time,
            'total_ms': total_time,
            'fps': 1000.0 / total_time
        }
    }

if __name__ == "__main__":
    # Example usage
    MODEL_PATH = "/home/pi/Desktop/project/sed/model/classification/best.onnx"  # Update path as needed
    IMAGE_PATH = "/home/pi/Desktop/project/image/pilsner333/pilsner333_5.jpg"         # Update path as needed
    IMGSZ = 224
    DEVICE = 'cpu'  # or 'cuda' if available

    if not os.path.exists(MODEL_PATH):
        print(f"❌ Model not found: {MODEL_PATH}")
        sys.exit(1)
    if not os.path.exists(IMAGE_PATH):
        print(f"❌ Image not found: {IMAGE_PATH}")
        sys.exit(1)

    print("🚀 Starting Ultralytics YOLO ONNX Test")
    print("=" * 50)
    
    # Run the test
    test_start_time = time.perf_counter()
    result = run_yolo_onnx(MODEL_PATH, IMAGE_PATH, imgsz=IMGSZ, device=DEVICE)
    test_total_time = (time.perf_counter() - test_start_time) * 1000
    
    print("\n" + "=" * 50)
    print("🎉 Test completed successfully!")
    print(f"⏱️  Total script execution time: {test_total_time:.2f} ms")
    
    if result and 'timing' in result:
        timing = result['timing']
        print(f"\n📊 Performance Summary:")
        print(f"   Pure inference time: {timing['inference_ms']:.2f} ms")
        print(f"   Effective FPS:       {timing['fps']:.2f}")
        print(f"   Model overhead:      {timing['model_load_ms']:.2f} ms")
        print(f"   Image overhead:      {timing['image_load_ms']:.2f} ms")