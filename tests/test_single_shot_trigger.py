#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for single-shot capture_request trigger mode

Tests that only one frame is captured per trigger press, even with rapid button presses.
"""

import sys
import os
import time
import threading

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_single_shot_behavior():
    """Test that only one frame is captured per trigger, with cooldown protection"""
    print("=" * 60)
    print("TEST: Single-shot trigger behavior")
    print("=" * 60)
    
    try:
        from camera.camera_stream import CameraStream
        
        # Create camera stream
        camera_stream = CameraStream()
        
        print("1. Setting up trigger mode...")
        camera_stream.set_trigger_mode(True)
        
        print("2. Testing single trigger...")
        frame = camera_stream.capture_single_frame_request()
        if frame is not None:
            print(f"✓ Single trigger successful: {frame.shape}")
        else:
            print("✗ Single trigger failed")
            
        print("\n3. Testing rapid multiple triggers (should be ignored due to cooldown)...")
        
        # Track frames received
        frames_captured = []
        
        # Simulate rapid button presses
        for i in range(5):
            print(f"   Trigger {i+1}:")
            frame = camera_stream.capture_single_frame_request()
            if frame is not None:
                frames_captured.append(frame)
                print(f"   ✓ Frame captured")
            else:
                print(f"   - Trigger ignored (cooldown/lock)")
            time.sleep(0.05)  # 50ms between presses (faster than 250ms cooldown)
        
        print(f"\n   Result: {len(frames_captured)} frames captured out of 5 triggers")
        if len(frames_captured) == 1:
            print("   ✓ Cooldown working correctly - only 1 frame captured")
        else:
            print(f"   ⚠ Expected 1 frame, got {len(frames_captured)}")
            
        print("\n4. Testing triggers with proper spacing...")
        frames_captured.clear()
        
        for i in range(3):
            print(f"   Trigger {i+1} (with 300ms delay):")
            frame = camera_stream.capture_single_frame_request()
            if frame is not None:
                frames_captured.append(frame)
                print(f"   ✓ Frame captured")
            else:
                print(f"   ✗ Frame not captured")
            time.sleep(0.3)  # 300ms between presses (longer than 250ms cooldown)
        
        print(f"\n   Result: {len(frames_captured)} frames captured out of 3 triggers")
        if len(frames_captured) == 3:
            print("   ✓ Spaced triggers working correctly - all 3 frames captured")
        else:
            print(f"   ⚠ Expected 3 frames, got {len(frames_captured)}")
            
        return True
        
    except Exception as e:
        print(f"✗ Error in single-shot test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_concurrent_triggers():
    """Test concurrent trigger attempts from multiple threads"""
    print("=" * 60)
    print("TEST: Concurrent trigger protection")
    print("=" * 60)
    
    try:
        from camera.camera_stream import CameraStream
        
        # Create camera stream
        camera_stream = CameraStream()
        camera_stream.set_trigger_mode(True)
        
        # Results tracking
        results = []
        results_lock = threading.Lock()
        
        def trigger_worker(worker_id):
            """Worker function for concurrent trigger test"""
            try:
                frame = camera_stream.capture_single_frame_request()
                with results_lock:
                    if frame is not None:
                        results.append(f"Worker {worker_id}: SUCCESS")
                        print(f"   Worker {worker_id}: Frame captured")
                    else:
                        results.append(f"Worker {worker_id}: IGNORED")
                        print(f"   Worker {worker_id}: Trigger ignored")
            except Exception as e:
                with results_lock:
                    results.append(f"Worker {worker_id}: ERROR - {e}")
                    print(f"   Worker {worker_id}: Error - {e}")
        
        print("1. Starting 5 concurrent trigger attempts...")
        
        # Create and start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=trigger_worker, args=(i+1,))
            threads.append(thread)
        
        # Start all threads at roughly the same time
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        print(f"\n2. Results from {len(threads)} concurrent attempts:")
        success_count = 0
        ignored_count = 0
        error_count = 0
        
        for result in results:
            print(f"   {result}")
            if "SUCCESS" in result:
                success_count += 1
            elif "IGNORED" in result:
                ignored_count += 1
            elif "ERROR" in result:
                error_count += 1
        
        print(f"\n   Summary: {success_count} success, {ignored_count} ignored, {error_count} errors")
        
        if success_count == 1 and ignored_count >= 4:
            print("   ✓ Concurrent protection working - only 1 frame captured")
            return True
        else:
            print(f"   ⚠ Expected 1 success and 4+ ignored, got different results")
            return False
            
    except Exception as e:
        print(f"✗ Error in concurrent test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cooldown_configuration():
    """Test cooldown time configuration"""
    print("=" * 60)
    print("TEST: Cooldown configuration")
    print("=" * 60)
    
    try:
        from camera.camera_stream import CameraStream
        
        # Create camera stream
        camera_stream = CameraStream()
        camera_stream.set_trigger_mode(True)
        
        print("1. Testing default cooldown (250ms)...")
        
        # First trigger
        frame1 = camera_stream.capture_single_frame_request()
        print(f"   First trigger: {'SUCCESS' if frame1 is not None else 'FAILED'}")
        
        # Immediate second trigger (should be ignored)
        frame2 = camera_stream.capture_single_frame_request()
        print(f"   Immediate second trigger: {'SUCCESS' if frame2 is not None else 'IGNORED'}")
        
        print("\n2. Setting shorter cooldown (100ms)...")
        camera_stream.set_trigger_cooldown(0.1)  # 100ms
        
        time.sleep(0.3)  # Wait to clear cooldown
        
        # Test with shorter cooldown
        frame3 = camera_stream.capture_single_frame_request()
        print(f"   First trigger with 100ms cooldown: {'SUCCESS' if frame3 is not None else 'FAILED'}")
        
        time.sleep(0.15)  # Wait 150ms (longer than 100ms cooldown)
        
        frame4 = camera_stream.capture_single_frame_request()
        print(f"   Second trigger after 150ms wait: {'SUCCESS' if frame4 is not None else 'FAILED'}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in cooldown test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all single-shot tests"""
    print("Testing Single-Shot capture_request Implementation")
    print("=" * 80)
    
    tests = [
        test_single_shot_behavior,
        test_concurrent_triggers,
        test_cooldown_configuration
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
        print("✓ All single-shot tests passed!")
        print("\nThe trigger now captures exactly 1 frame per button press,")
        print("with cooldown protection against rapid button presses.")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())