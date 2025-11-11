#!/usr/bin/env python3
"""
Quick test to verify frame display debugging is in place
Run this to see if console output shows debug messages
"""
import sys
import os

# Add project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_debug_messages():
    """Check if debug messages are in camera_view.py"""
    camera_view_path = os.path.join(os.path.dirname(__file__), 'gui', 'camera_view.py')
    
    debug_markers = [
        "DEBUG: [display_frame]",
        "DEBUG: [CameraDisplayWorker.add_frame]",
        "DEBUG: [CameraDisplayWorker.process_frames]",
        "DEBUG: [_start_camera_display_worker]",
        "DEBUG: [_handle_processed_frame]",
        "DEBUG: [_display_qimage]",
    ]
    
    print(f"Checking {camera_view_path} for debug markers...\n")
    
    with open(camera_view_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    found_count = 0
    for marker in debug_markers:
        if marker in content:
            print(f"✅ Found: {marker}")
            found_count += 1
        else:
            print(f"❌ NOT Found: {marker}")
    
    print(f"\nTotal: {found_count}/{len(debug_markers)} debug markers found")
    
    if found_count == len(debug_markers):
        print("\n✅ All debug markers are in place!")
        print("\nYou can now run main.py and watch for debug output.")
        print("The console should show messages like:")
        print("  - When camera initializes: '_start_camera_display_worker' messages")
        print("  - When frames arrive: 'display_frame' messages")
        print("  - When frames are processed: 'CameraDisplayWorker.process_frames' messages")
        print("  - When frames are displayed: '_display_qimage' messages")
        return True
    else:
        print("\n❌ Some debug markers are missing. Check if modifications were applied correctly.")
        return False

if __name__ == '__main__':
    success = check_debug_messages()
    sys.exit(0 if success else 1)
