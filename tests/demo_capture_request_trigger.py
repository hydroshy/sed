#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Demonstration of capture_request() trigger mode

This script demonstrates how the new trigger mode works:
1. Camera stays in preview mode (started and configured)
2. capture_request() is called to get a single frame when needed
3. No GPIO trigger or sysfs parameters needed

Usage Example:
1. Switch to trigger mode: camera stays running but doesn't stream to UI
2. Press "Trigger Camera" button: calls capture_single_frame_request()
3. Frame is captured and displayed
"""

import sys
import os
import time
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def demonstrate_capture_request():
    """Demonstrate the capture_request workflow"""
    print("Capture_Request Trigger Mode Demonstration")
    print("=" * 60)
    
    try:
        from camera.camera_stream import CameraStream
        
        # Create camera stream
        print("1. Creating CameraStream...")
        camera_stream = CameraStream()
        
        # Simulate camera mode changes
        print("\n2. Live Mode (continuous streaming):")
        print("   - Camera streams continuously")
        print("   - set_trigger_mode(False)")
        camera_stream.set_trigger_mode(False)
        
        # Simulate some live frames
        for i in range(3):
            print(f"   Live frame {i+1} would be displayed")
            time.sleep(0.1)
        
        print("\n3. Switching to Trigger Mode:")
        print("   - Camera continues running (still configured and started)")
        print("   - No more continuous streaming to UI")
        print("   - set_trigger_mode(True)")
        camera_stream.set_trigger_mode(True)
        
        print("   - Camera is now ready for capture_request() calls")
        
        print("\n4. Trigger Capture (when button pressed):")
        print("   - User presses 'Trigger Camera' button")
        print("   - CameraManager.activate_capture_request() is called")
        print("   - This calls camera_stream.capture_single_frame_request()")
        
        for i in range(3):
            print(f"\n   Trigger {i+1}:")
            frame = camera_stream.capture_single_frame_request()
            if frame is not None:
                print(f"   ✓ Frame captured: {frame.shape}")
                print(f"   ✓ Frame displayed in UI")
            else:
                print("   ✗ No frame captured")
            time.sleep(0.5)
        
        print("\n5. Key Differences from GPIO Trigger:")
        print("   OLD GPIO Method:")
        print("   - Required: echo 1 | sudo tee /sys/module/imx296/parameters/trigger_mode")
        print("   - Used GPIO pin 17 to trigger camera hardware")
        print("   - Camera waited for external electrical signal")
        print("")
        print("   NEW capture_request() Method:")
        print("   - No GPIO/sysfs interaction needed")
        print("   - Camera runs continuously in preview mode")
        print("   - capture_request() blocks until frame ready")
        print("   - Software trigger instead of hardware trigger")
        
        print("\n6. Benefits:")
        print("   - No need for root privileges")
        print("   - No GPIO wiring required")
        print("   - More reliable (software vs hardware)")
        print("   - Better integration with Picamera2")
        print("   - Immediate metadata access")
        
        return True
        
    except Exception as e:
        print(f"Error in demonstration: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_code_flow():
    """Show the code flow for the new trigger mode"""
    print("\nCode Flow Diagram:")
    print("=" * 60)
    
    flow = [
        "1. User clicks 'Trigger Camera Mode' button:",
        "   └─ on_trigger_camera_mode_clicked()",
        "   └─ set_trigger_mode(True)",
        "   └─ camera_stream.set_trigger_mode(True)",
        "   └─ Camera stays running, stops UI streaming",
        "",
        "2. User clicks 'Trigger Camera' button:",
        "   └─ on_trigger_camera_clicked()",
        "   └─ activate_capture_request()  # NEW METHOD",
        "   └─ camera_stream.capture_single_frame_request()  # NEW METHOD",
        "   └─ request = picam2.capture_request()  # CORE CHANGE",
        "   └─ frame = request.make_array('main')",
        "   └─ request.release()",
        "   └─ frame_ready.emit(frame)",
        "",
        "3. Previous GPIO method (now unused):",
        "   └─ activate_gpio_trigger()  # OLD METHOD",
        "   └─ trigger_camera(gpio_pin=17)  # OLD METHOD",
        "   └─ GPIO pulse to pin 17  # OLD METHOD",
        "   └─ Hardware trigger  # OLD METHOD",
    ]
    
    for line in flow:
        print(line)

def main():
    """Main demonstration"""
    print("capture_request() Trigger Mode Implementation")
    print("=" * 80)
    
    if demonstrate_capture_request():
        show_code_flow()
        
        print("\n" + "=" * 80)
        print("✓ Demonstration completed successfully!")
        print("\nThe trigger mode now uses capture_request() instead of GPIO trigger.")
        print("This provides better integration and no hardware dependencies.")
        return 0
    else:
        print("\n" + "=" * 80)
        print("✗ Demonstration failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())