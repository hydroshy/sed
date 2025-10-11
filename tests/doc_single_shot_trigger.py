#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Single-Shot Capture Request Trigger Mode Documentation

This document explains how the new single-shot trigger mode works to ensure
only one frame is captured per button press, preventing multiple frames
from rapid button presses.
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def demonstrate_single_shot_mechanism():
    """Demonstrate the single-shot capture mechanism"""
    print("Single-Shot Capture Request Mechanism")
    print("=" * 60)
    
    print("1. PROBLEM SOLVED:")
    print("   - Previous: capture_request() could capture multiple frames")
    print("   - New: Only 1 frame captured per button press")
    print("")
    
    print("2. IMPLEMENTATION PATTERN (based on your example):")
    print("""
   # Global state in CameraStream.__init__():
   self._single_shot_lock = threading.Lock()
   self._cooldown_s = 0.25  # 250ms cooldown
   self._last_trigger_time = 0.0
   
   # In capture_single_frame_request():
   def grab_one_frame():
       global _last
       now = time.monotonic()
       if now - _last < COOLDOWN_S or not _single_shot_lock.acquire(False):
           return  # đang bận hoặc nhấn quá sát
       _last = now
       try:
           req = picam2.capture_request()     # chờ đúng KHUNG KẾ TIẾP
           try:
               img = req.make_array("main")
               meta = req.get_metadata()
               # TODO: xử lý/lưu img (+ meta nếu cần)
           finally:
               req.release()
       finally:
           _single_shot_lock.release()
   """)
    
    print("3. KEY FEATURES:")
    print("   ✓ Threading Lock: Prevents concurrent capture attempts")
    print("   ✓ Cooldown Timer: 250ms minimum between captures")
    print("   ✓ Non-blocking Lock: acquire(False) - doesn't wait if busy")
    print("   ✓ Always Release: Lock released in finally block")
    print("   ✓ Buffer Management: Request always released")
    print("")
    
    print("4. BEHAVIOR EXAMPLES:")
    
    try:
        from camera.camera_stream import CameraStream
        
        camera_stream = CameraStream()
        camera_stream.set_trigger_mode(True)
        
        print("\n   Example 1: Single button press")
        frame = camera_stream.capture_single_frame_request()
        result = "SUCCESS" if frame is not None else "FAILED"
        print(f"   → Result: {result}")
        
        print("\n   Example 2: Rapid button presses (< 250ms apart)")
        frames_captured = 0
        for i in range(3):
            frame = camera_stream.capture_single_frame_request()
            if frame is not None:
                frames_captured += 1
            time.sleep(0.05)  # 50ms between presses
        
        print(f"   → 3 rapid presses: {frames_captured} frame(s) captured")
        print("   → Expected: 1 frame (others ignored due to cooldown)")
        
        print("\n   Example 3: Properly spaced presses (> 250ms apart)")
        time.sleep(0.3)  # Clear cooldown
        frames_captured = 0
        for i in range(2):
            frame = camera_stream.capture_single_frame_request()
            if frame is not None:
                frames_captured += 1
            time.sleep(0.3)  # 300ms between presses
        
        print(f"   → 2 spaced presses: {frames_captured} frame(s) captured")
        print("   → Expected: 2 frames (all captured)")
        
    except Exception as e:
        print(f"   → Error in examples: {e}")
    
    print("\n5. CONFIGURATION:")
    print("   - Default cooldown: 250ms")
    print("   - Configurable via: camera_stream.set_trigger_cooldown(seconds)")
    print("   - Recommended range: 0.1s to 1.0s")
    
    print("\n6. INTEGRATION WITH UI:")
    print("   User Action: Click 'Trigger Camera' button")
    print("   → CameraManager.on_trigger_camera_clicked()")
    print("   → CameraManager.activate_capture_request()")
    print("   → CameraStream.capture_single_frame_request()")
    print("   → [Cooldown check] → [Lock acquire] → [capture_request()]")
    print("   → Frame displayed in UI")

def show_timing_diagram():
    """Show timing diagram for trigger behavior"""
    print("\nTiming Diagram:")
    print("=" * 60)
    
    timing = [
        "Time:    0ms   50ms  100ms  150ms  200ms  250ms  300ms  350ms",
        "Button:   ↓     ↓     ↓      ↓      ↓      ↓      ↓      ↓",
        "Result: CAPTURE IGNORE IGNORE IGNORE IGNORE CAPTURE IGNORE IGNORE",
        "",
        "Legend:",
        "↓        = Button press",
        "CAPTURE  = Frame captured and displayed",
        "IGNORE   = Button press ignored (cooldown active)",
        "",
        "Cooldown period: ├──── 250ms ────┤",
        "",
        "Explanation:",
        "- First press (0ms): Frame captured, cooldown starts",
        "- Presses at 50-200ms: Ignored (within cooldown period)",
        "- Press at 250ms: Frame captured (cooldown expired)",
        "- Presses at 300-350ms: Ignored (new cooldown active)",
    ]
    
    for line in timing:
        print(line)

def main():
    """Main documentation"""
    print("Single-Shot capture_request() Trigger Mode")
    print("=" * 80)
    
    demonstrate_single_shot_mechanism()
    show_timing_diagram()
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("✓ Only 1 frame captured per trigger button press")
    print("✓ 250ms cooldown prevents accidental multiple captures")
    print("✓ Thread-safe with non-blocking lock mechanism")
    print("✓ Configurable cooldown time")
    print("✓ Based on your provided pattern with improvements")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())