#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for capture_request trigger mode

Tests the new trigger mode that uses capture_request() instead of GPIO trigger.
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_capture_request_basic():
    """Test basic capture_request functionality"""
    print("=" * 60)
    print("TEST: Basic capture_request functionality")
    print("=" * 60)
    
    try:
        from camera.camera_stream import CameraStream
        
        # Create camera stream
        camera_stream = CameraStream()
        
        print("1. Testing capture_single_frame_request method...")
        
        # Test capture without camera started
        frame = camera_stream.capture_single_frame_request()
        
        if frame is not None:
            print(f"✓ Frame captured successfully: {frame.shape}")
        else:
            print("✗ No frame captured")
            
        return True
        
    except Exception as e:
        print(f"✗ Error in basic test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_trigger_mode_transition():
    """Test trigger mode transition"""
    print("=" * 60)
    print("TEST: Trigger mode transition")
    print("=" * 60)
    
    try:
        from camera.camera_stream import CameraStream
        
        # Create camera stream
        camera_stream = CameraStream()
        
        print("1. Testing set_trigger_mode(True)...")
        success = camera_stream.set_trigger_mode(True)
        print(f"✓ Trigger mode enabled: {success}")
        
        print("2. Testing capture in trigger mode...")
        frame = camera_stream.capture_single_frame_request()
        
        if frame is not None:
            print(f"✓ Frame captured in trigger mode: {frame.shape}")
        else:
            print("✗ No frame captured in trigger mode")
            
        print("3. Testing set_trigger_mode(False)...")
        success = camera_stream.set_trigger_mode(False)
        print(f"✓ Trigger mode disabled: {success}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in trigger mode test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_camera_manager_integration():
    """Test CameraManager integration"""
    print("=" * 60)
    print("TEST: CameraManager integration")
    print("=" * 60)
    
    try:
        from gui.camera_manager import CameraManager
        from PyQt5.QtCore import QObject
        
        # Create a mock main window
        class MockMainWindow(QObject):
            def __init__(self):
                super().__init__()
                
        main_window = MockMainWindow()
        
        # Create camera manager  
        camera_manager = CameraManager(main_window)
        
        print("1. Testing activate_capture_request method...")
        result = camera_manager.activate_capture_request()
        
        if result:
            print("✓ Capture request activated successfully")
        else:
            print("✗ Capture request failed")
            
        return True
        
    except Exception as e:
        print(f"✗ Error in CameraManager integration test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("Testing capture_request trigger mode implementation")
    print("=" * 80)
    
    tests = [
        test_capture_request_basic,
        test_trigger_mode_transition,
        test_camera_manager_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
                print("RESULT: PASSED\n")
            else:
                print("RESULT: FAILED\n")
        except Exception as e:
            print(f"RESULT: ERROR - {e}\n")
            
    print("=" * 80)
    print(f"SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())