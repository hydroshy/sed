#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script to verify trigger mode stops continuous streaming

This test verifies that when entering trigger mode:
1. Live streaming stops completely 
2. Only single frames are captured on demand
3. No continuous frame emission occurs
"""

import sys
import os
import time
import threading

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_trigger_mode_stops_streaming():
    """Test that trigger mode stops continuous streaming"""
    print("=" * 60)
    print("TEST: Trigger mode stops continuous streaming")
    print("=" * 60)
    
    try:
        from camera.camera_stream import CameraStream
        
        # Create camera stream
        camera_stream = CameraStream()
        
        # Track frames received
        frames_received = []
        frames_lock = threading.Lock()
        
        def frame_handler(frame):
            """Handler for frame_ready signal"""
            with frames_lock:
                frames_received.append(time.monotonic())
                print(f"   Frame received at {frames_received[-1]:.3f}")
        
        # Connect to frame_ready signal
        camera_stream.frame_ready.connect(frame_handler)
        
        print("1. Starting in live mode...")
        camera_stream.set_trigger_mode(False)
        
        # Simulate live mode streaming
        print("   Simulating live mode for 1 second...")
        start_time = time.monotonic()
        
        # In stub mode, generate a few frames manually to simulate live
        for i in range(3):
            camera_stream._generate_test_frame()  # This should emit frames
            time.sleep(0.2)
        
        live_frames = len(frames_received)
        print(f"   Live mode: {live_frames} frames received")
        
        print("\n2. Switching to trigger mode...")
        frames_received.clear()  # Clear previous frames
        
        camera_stream.set_trigger_mode(True)
        
        print("   Waiting 1 second to check for continuous frames...")
        # Wait and see if any frames are emitted automatically
        time.sleep(1.0)
        
        continuous_frames = len(frames_received)
        print(f"   Trigger mode (automatic): {continuous_frames} frames received")
        
        if continuous_frames == 0:
            print("   ✓ No continuous frames - streaming stopped correctly")
        else:
            print(f"   ✗ Still receiving {continuous_frames} continuous frames")
        
        print("\n3. Manual trigger capture...")
        frames_received.clear()
        
        # Manual trigger
        frame = camera_stream.capture_single_frame_request()
        time.sleep(0.1)  # Give time for signal emission
        
        manual_frames = len(frames_received)
        print(f"   Manual trigger: {manual_frames} frames received")
        
        if manual_frames == 1:
            print("   ✓ Exactly 1 frame captured on manual trigger")
        else:
            print(f"   ⚠ Expected 1 frame, got {manual_frames}")
        
        print("\n4. Multiple manual triggers with spacing...")
        frames_received.clear()
        
        for i in range(3):
            frame = camera_stream.capture_single_frame_request()
            time.sleep(0.3)  # Wait between triggers
        
        time.sleep(0.1)  # Give time for signal emission
        spaced_frames = len(frames_received)
        print(f"   3 spaced triggers: {spaced_frames} frames received")
        
        if spaced_frames == 3:
            print("   ✓ All manual triggers captured correctly")
        else:
            print(f"   ⚠ Expected 3 frames, got {spaced_frames}")
        
        # Summary
        print(f"\nSUMMARY:")
        print(f"   Live mode frames: {live_frames} (should be > 0)")
        print(f"   Trigger mode continuous: {continuous_frames} (should be 0)")
        print(f"   Manual trigger: {manual_frames} (should be 1)")
        print(f"   Spaced triggers: {spaced_frames} (should be 3)")
        
        success = (continuous_frames == 0 and manual_frames == 1 and spaced_frames == 3)
        return success
        
    except Exception as e:
        print(f"✗ Error in streaming test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_trigger_mode_flag():
    """Test the internal trigger mode flag"""
    print("=" * 60)
    print("TEST: Internal trigger mode flag")
    print("=" * 60)
    
    try:
        from camera.camera_stream import CameraStream
        
        camera_stream = CameraStream()
        
        print("1. Initial state...")
        initial_flag = getattr(camera_stream, '_in_trigger_mode', None)
        print(f"   _in_trigger_mode: {initial_flag}")
        
        print("\n2. Setting trigger mode True...")
        camera_stream.set_trigger_mode(True)
        trigger_flag = getattr(camera_stream, '_in_trigger_mode', None)
        print(f"   _in_trigger_mode: {trigger_flag}")
        
        print("\n3. Setting trigger mode False...")
        camera_stream.set_trigger_mode(False)
        live_flag = getattr(camera_stream, '_in_trigger_mode', None)
        print(f"   _in_trigger_mode: {live_flag}")
        
        success = (initial_flag == False and trigger_flag == True and live_flag == False)
        if success:
            print("   ✓ Trigger mode flag working correctly")
        else:
            print("   ✗ Trigger mode flag not working correctly")
        
        return success
        
    except Exception as e:
        print(f"✗ Error in flag test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all streaming stop tests"""
    print("Testing Trigger Mode Streaming Control")
    print("=" * 80)
    
    tests = [
        test_trigger_mode_flag,
        test_trigger_mode_stops_streaming,
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
        print("✓ All streaming control tests passed!")
        print("\nTrigger mode now properly stops continuous streaming")
        print("and only captures frames on manual trigger requests.")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())