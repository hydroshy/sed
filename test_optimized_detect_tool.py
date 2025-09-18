"""
Test script for OptimizedDetectTool
Tests the new optimized detection tool with testonnx.py approach
"""

import sys
import numpy as np
import cv2
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

try:
    from tools.detection.detect_tool import DetectTool, create_detect_tool_from_manager_config
    print("✓ Successfully imported OptimizedDetectTool")
except Exception as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

def test_optimized_detect_tool():
    """Test optimized detect tool functionality"""
    print("\n=== Testing OptimizedDetectTool ===")
    
    # Test 1: Basic initialization
    print("\n1. Testing basic initialization...")
    try:
        config = {
            'model_path': './model/detect/yolov11n.onnx',  # Adjust path if needed
            'class_names': ['pilsner333', 'saxizero', 'warriorgrape'],
            'selected_classes': ['pilsner333', 'saxizero'],
            'confidence_threshold': 0.5,
            'nms_threshold': 0.45,
            'imgsz': 640
        }
        
        tool = DetectTool("Test Detect Tool", config)
        print("✓ DetectTool initialization successful")
        
        # Check if ONNX is available
        try:
            import onnxruntime as ort
            print("✓ ONNX Runtime available")
        except ImportError:
            print("✗ ONNX Runtime not available - install with: pip install onnxruntime")
            return
            
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        return
    
    # Test 2: Configuration
    print("\n2. Testing configuration...")
    try:
        info = tool.get_info()
        print(f"✓ Tool info: {info['tool_type']}")
        print(f"  - Model path: {info.get('model_path', 'None')}")
        print(f"  - Classes: {info.get('class_count', 0)}")
        print(f"  - Selected: {info.get('selected_classes', 0)}")
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
    
    # Test 3: Model loading (if model exists)
    print("\n3. Testing model loading...")
    try:
        model_path = Path(config['model_path'])
        if model_path.exists():
            success = tool.initialize_detection()
            if success:
                print("✓ Model loaded successfully")
            else:
                print("✗ Model loading failed")
        else:
            print(f"⚠ Model file not found: {model_path}")
            print("  Skipping model-dependent tests")
            return
    except Exception as e:
        print(f"✗ Model loading error: {e}")
        return
    
    # Test 4: Dummy image processing
    print("\n4. Testing image processing...")
    try:
        # Create dummy image
        dummy_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Process image
        result_image, results = tool.process(dummy_image)
        
        print(f"✓ Image processing successful")
        print(f"  - Input shape: {dummy_image.shape}")
        print(f"  - Output shape: {result_image.shape}")
        print(f"  - Status: {results.get('status', 'unknown')}")
        print(f"  - Detections: {results.get('detection_count', 0)}")
        print(f"  - Execution time: {results.get('execution_time', 0):.3f}s")
        
    except Exception as e:
        print(f"✗ Image processing failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Factory function
    print("\n5. Testing factory function...")
    try:
        manager_config = {
            'model_name': 'yolov11n',
            'model_path': './model/detect/yolov11n.onnx',
            'class_names': ['pilsner333', 'saxizero', 'warriorgrape'],
            'selected_classes': ['pilsner333'],
            'confidence_threshold': 0.6,
            'nms_threshold': 0.4
        }
        
        factory_tool = create_detect_tool_from_manager_config(manager_config, tool_id=1)
        print("✓ Factory function successful")
        print(f"  - Tool ID: {factory_tool.tool_id}")
        print(f"  - Name: {factory_tool.name}")
        
    except Exception as e:
        print(f"✗ Factory function failed: {e}")
    
    # Test 6: Performance comparison (if real image available)
    print("\n6. Testing with real image (if available)...")
    try:
        test_image_path = "./image/saxizero/saxizero_1.jpg"  # From testonnx.py
        if Path(test_image_path).exists():
            test_image = cv2.imread(test_image_path)
            if test_image is not None:
                print(f"  - Loading test image: {test_image_path}")
                print(f"  - Image shape: {test_image.shape}")
                
                # Process with optimized tool
                start_time = time.time()
                result_image, results = tool.process(test_image)
                processing_time = time.time() - start_time
                
                print(f"✓ Real image processing successful")
                print(f"  - Processing time: {processing_time:.3f}s")
                print(f"  - Detections found: {results.get('detection_count', 0)}")
                
                # Print detection details
                detections = results.get('detections', [])
                for i, det in enumerate(detections):
                    print(f"    Detection {i+1}: {det['class_name']} ({det['confidence']:.3f})")
                
                # Save result if detections found
                if detections:
                    output_path = "test_optimized_detect_output.jpg"
                    cv2.imwrite(output_path, result_image)
                    print(f"  - Result saved to: {output_path}")
            else:
                print(f"  ⚠ Could not read image: {test_image_path}")
        else:
            print(f"  ⚠ Test image not found: {test_image_path}")
    except Exception as e:
        print(f"✗ Real image test failed: {e}")
    
    # Cleanup
    print("\n7. Testing cleanup...")
    try:
        tool.cleanup()
        print("✓ Cleanup successful")
    except Exception as e:
        print(f"✗ Cleanup failed: {e}")
    
    print("\n=== OptimizedDetectTool Test Complete ===")

if __name__ == "__main__":
    import time
    test_optimized_detect_tool()