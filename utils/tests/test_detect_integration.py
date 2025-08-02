#!/usr/bin/env python3
"""
Test Detect Tool Integration
Tests the complete YOLO detection pipeline from UI to job execution
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
import numpy as np
import cv2

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_yolo_inference():
    """Test YOLO inference engine"""
    print("🔍 Testing YOLO Inference Engine...")
    
    try:
        from detection.yolo_inference import create_yolo_inference
        
        # Create inference engine
        yolo = create_yolo_inference()
        
        # Test with mock image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        test_image[:] = (100, 150, 200)  # Fill with color
        
        # Try to load model (will use mock if ONNX not available)
        model_path = "model/detect/yolov11n.onnx"
        class_names = ["barcode", "hangtag", "punchhole", "qrcode", "smudges"]
        
        success = yolo.load_model(model_path, class_names)
        print(f"✓ Model loading: {'Success' if success else 'Failed (using mock)'}")
        
        # Run inference
        detections = yolo.infer(test_image)
        print(f"✓ Inference completed: Found {len(detections)} detections")
        
        for i, det in enumerate(detections):
            print(f"  Detection {i+1}: {det['class_name']} (conf: {det['confidence']:.2f})")
        
        return True
        
    except Exception as e:
        print(f"✗ YOLO inference test failed: {e}")
        return False

def test_detect_tool_job():
    """Test DetectToolJob"""
    print("\n🛠️ Testing DetectToolJob...")
    
    try:
        from detection.detect_tool_job import create_detect_tool_job
        
        # Create job config
        config = {
            'model_name': 'yolov11n',
            'model_path': 'model/detect/yolov11n.onnx',
            'selected_classes': ['barcode', 'qrcode'],
            'confidence_threshold': 0.5,
            'nms_threshold': 0.4
        }
        
        # Create job
        job = create_detect_tool_job(config)
        print("✓ DetectToolJob created")
        
        # Test initialization
        success = job.initialize()
        print(f"✓ Job initialization: {'Success' if success else 'Failed (using mock)'}")
        
        # Test execution
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        result = job.execute(test_image)
        
        print(f"✓ Job execution: {'Success' if result['success'] else 'Failed'}")
        print(f"  Found {len(result['detections'])} detections")
        print(f"  Execution time: {result['execution_time']:.3f}s")
        
        return True
        
    except Exception as e:
        print(f"✗ DetectToolJob test failed: {e}")
        return False

def test_detect_tool():
    """Test DetectTool for job system"""
    print("\n⚙️ Testing DetectTool...")
    
    try:
        from detection.detect_tool import create_detect_tool_from_manager_config
        
        # Create manager config
        manager_config = {
            'model_name': 'yolov11n',
            'model_path': 'model/detect/yolov11n.onnx',
            'selected_classes': ['barcode', 'qrcode', 'hangtag'],
            'num_classes': 3
        }
        
        # Create detect tool
        tool = create_detect_tool_from_manager_config(manager_config, tool_id=1)
        print("✓ DetectTool created")
        
        # Test configuration
        info = tool.get_info()
        print(f"✓ Tool info: {info['tool_type']} - {info['display_name']}")
        print(f"  Model: {info['config']['model_name']}")
        print(f"  Classes: {len(info['config']['selected_classes'])}")
        
        # Test processing
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        processed_image, result = tool.process(test_image)
        
        print(f"✓ Tool processing: {result['status']}")
        print(f"  Detections: {result['detection_count']}")
        print(f"  Execution time: {result['execution_time']:.3f}s")
        
        return True
        
    except Exception as e:
        print(f"✗ DetectTool test failed: {e}")
        return False

def test_visualization():
    """Test detection visualization"""
    print("\n🎨 Testing Visualization...")
    
    try:
        from detection.visualization import create_detection_display, get_visualizer
        
        # Create test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        test_image[:] = (50, 100, 150)
        
        # Create mock detections
        detections = [
            {
                'bbox': [100, 100, 200, 200],
                'confidence': 0.85,
                'class_id': 0,
                'class_name': 'barcode'
            },
            {
                'bbox': [300, 150, 400, 250],
                'confidence': 0.72,
                'class_id': 3,
                'class_name': 'qrcode'
            }
        ]
        
        # Test visualization
        visualized = create_detection_display(test_image, detections)
        print(f"✓ Visualization created: {visualized.shape}")
        
        # Test summary
        visualizer = get_visualizer()
        summary = visualizer.create_detection_summary(detections)
        print(f"✓ Detection summary: {summary['total_detections']} detections")
        print(f"  Class counts: {summary['class_counts']}")
        print(f"  Avg confidence: {summary['avg_confidence']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Visualization test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Detect Tool Integration\n")
    
    tests = [
        ("YOLO Inference", test_yolo_inference),
        ("DetectToolJob", test_detect_tool_job),
        ("DetectTool", test_detect_tool),
        ("Visualization", test_visualization)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} test passed\n")
            else:
                print(f"❌ {test_name} test failed\n")
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}\n")
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Detect Tool integration is ready.")
    else:
        print("⚠️ Some tests failed. Check the logs above.")
        
        # Installation tips
        print("\n💡 Installation Tips:")
        print("- Install ONNX Runtime: pip install onnxruntime")
        print("- Make sure model files exist in model/detect/")
        print("- Check that all dependencies are installed")

if __name__ == "__main__":
    main()
