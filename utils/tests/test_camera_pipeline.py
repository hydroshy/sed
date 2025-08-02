#!/usr/bin/env python3
"""
Demo script để test Picamera2 pipeline features
Chạy script này để test camera trước khi chạy ứng dụng chính
"""

import sys
import time
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_basic_camera():
    """Test basic camera functionality"""
    print("Testing basic Picamera2 functionality...")
    
    try:
        from camera.camera_stream import CameraStream
        
        # Create camera stream
        camera = CameraStream()
        
        if not camera.is_camera_available:
            print("❌ Camera not available")
            return False
            
        print("✅ Camera initialized successfully")
        
        # Get camera info
        info = camera.get_camera_info()
        print(f"📷 Camera Model: {info.get('model', 'Unknown')}")
        print(f"📐 Sensor Resolution: {info.get('sensor_resolution', 'Unknown')}")
        print(f"🖼️  Preview Size: {info.get('preview_size', 'Unknown')}")
        print(f"📸 Still Size: {info.get('still_size', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing camera: {e}")
        return False

def test_live_preview():
    """Test live preview"""
    print("\nTesting live preview...")
    
    try:
        from camera.camera_stream import CameraStream
        
        camera = CameraStream()
        if not camera.is_camera_available:
            return False
            
        # Start live preview
        success = camera.start_live()
        if success:
            print("✅ Live preview started")
            
            # Let it run for a few seconds
            time.sleep(3)
            
            # Check FPS
            fps = camera.get_fps()
            print(f"📊 Current FPS: {fps:.1f}")
            
            # Stop live
            camera.stop_live()
            print("⏹️  Live preview stopped")
            
        camera.cleanup()
        return success
        
    except Exception as e:
        print(f"❌ Error testing live preview: {e}")
        return False

def test_camera_controls():
    """Test camera control functions"""
    print("\nTesting camera controls...")
    
    try:
        from camera.camera_stream import CameraStream
        
        camera = CameraStream()
        if not camera.is_camera_available:
            return False
            
        camera.start_live()
        time.sleep(1)  # Let camera stabilize
        
        # Test exposure control
        print("🔆 Testing exposure control...")
        camera.set_exposure(20)  # 20ms
        time.sleep(0.5)
        exposure = camera.get_exposure()
        print(f"   Exposure set to 20ms, actual: {exposure}ms")
        
        # Test gain control
        print("📈 Testing gain control...")
        camera.set_gain(2.0)
        time.sleep(0.5)
        gain = camera.get_gain()
        print(f"   Gain set to 2.0, actual: {gain}")
        
        # Test auto exposure
        print("🤖 Testing auto exposure...")
        camera.set_auto_exposure(True)
        time.sleep(1)
        print("   Auto exposure enabled")
        
        camera.stop_live()
        camera.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Error testing camera controls: {e}")
        return False

def test_still_capture():
    """Test still image capture"""
    print("\nTesting still capture...")
    
    try:
        from camera.camera_stream import CameraStream
        import cv2
        
        camera = CameraStream()
        if not camera.is_camera_available:
            return False
            
        frame_captured = False
        
        def on_frame_ready(frame):
            nonlocal frame_captured
            print(f"📸 Frame captured: {frame.shape}")
            
            # Save test image
            if len(frame.shape) == 3:
                # Convert RGB to BGR for OpenCV
                bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                cv2.imwrite("test_capture.jpg", bgr_frame)
                print("💾 Test image saved as test_capture.jpg")
            
            frame_captured = True
        
        # Connect signal
        camera.frame_ready.connect(on_frame_ready)
        
        # Trigger capture
        camera.trigger_capture("still")
        
        # Wait for capture
        timeout = 5  # 5 seconds timeout
        start_time = time.time()
        while not frame_captured and (time.time() - start_time) < timeout:
            time.sleep(0.1)
            
        if frame_captured:
            print("✅ Still capture successful")
        else:
            print("❌ Still capture timeout")
            
        camera.cleanup()
        return frame_captured
        
    except Exception as e:
        print(f"❌ Error testing still capture: {e}")
        return False

def test_raw_capture():
    """Test RAW image capture"""
    print("\nTesting RAW capture...")
    
    try:
        from camera.camera_stream import CameraStream
        
        camera = CameraStream()
        if not camera.is_camera_available:
            return False
            
        frame_captured = False
        
        def on_frame_ready(frame):
            nonlocal frame_captured
            print(f"📸 RAW Frame captured: {frame.shape}")
            frame_captured = True
        
        # Connect signal
        camera.frame_ready.connect(on_frame_ready)
        
        # Trigger RAW capture
        camera.trigger_capture("raw")
        
        # Wait for capture
        timeout = 5
        start_time = time.time()
        while not frame_captured and (time.time() - start_time) < timeout:
            time.sleep(0.1)
            
        if frame_captured:
            print("✅ RAW capture successful")
        else:
            print("❌ RAW capture timeout")
            
        camera.cleanup()
        return frame_captured
        
    except Exception as e:
        print(f"❌ Error testing RAW capture: {e}")
        return False

def main():
    """Main test function"""
    print("🎥 Picamera2 Pipeline Test Suite")
    print("=" * 40)
    
    tests = [
        ("Basic Camera", test_basic_camera),
        ("Live Preview", test_live_preview),
        ("Camera Controls", test_camera_controls),
        ("Still Capture", test_still_capture),
        ("RAW Capture", test_raw_capture),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 40)
    print("📋 Test Results Summary:")
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Camera pipeline is working correctly.")
    else:
        print("⚠️  Some tests failed. Check camera connection and dependencies.")
        
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
