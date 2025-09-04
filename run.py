#!/usr/bin/env python3
"""
Convenient script to run SED application with different configurations
"""

import os
import sys
import subprocess
import argparse

def check_dependencies():
    """Check if required dependencies are installed"""
    required = ['PyQt5', 'numpy', 'cv2']
    missing = []
    
    for module in required:
        try:
            if module == 'cv2':
                import cv2
            elif module == 'PyQt5':
                import PyQt5
            elif module == 'numpy':
                import numpy
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print("Please install them using: pip install -r requirements.txt")
        return False
    
    # Check for Raspberry Pi and verify picamera2/pykms
    is_raspberry_pi = os.path.exists('/proc/device-tree/model') and 'Raspberry Pi' in open('/proc/device-tree/model', 'r').read()
    if is_raspberry_pi:
        print("Detected Raspberry Pi environment")
        try:
            # Try importing picamera2
            import picamera2
            print("✓ picamera2 is available")
            
            # Check if pykms is available without errors
            try:
                # Add stubs directory to path if it exists
                stubs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stubs')
                if os.path.exists(stubs_dir):
                    sys.path.insert(0, stubs_dir)
                    print(f"Added stubs directory to path: {stubs_dir}")
                
                # Try importing pykms
                import pykms
                print("✓ pykms is available")
            except Exception as e:
                print(f"! pykms error: {e}")
                print("! Using stubs or fallbacks for pykms")
                
                # Ensure the QT_QPA_PLATFORM env var is set for the subprocess
                os.environ['QT_QPA_PLATFORM'] = 'xcb'
                print("✓ Set QT_QPA_PLATFORM=xcb for compatibility")
        except ImportError:
            print("! picamera2 is not available - camera functionality may be limited")
            
    return True

def main():
    parser = argparse.ArgumentParser(description='Run SED Application')
    parser.add_argument('--debug', '-d', 
                       action='store_true',
                       help='Enable debug mode')
    parser.add_argument('--no-camera', 
                       action='store_true',
                       help='Run without camera for testing')
    parser.add_argument('--install-deps', 
                       action='store_true',
                       help='Install dependencies and exit')
    
    args = parser.parse_args()
    
    if args.install_deps:
        print("Installing dependencies...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        return
    
    if not check_dependencies():
        return
    
    # Build command
    cmd = [sys.executable, 'main.py']
    
    if args.debug:
        cmd.append('--debug')
        
    if args.no_camera:
        cmd.append('--no-camera')
        
    # On Raspberry Pi, suggest using xcb platform if not already set
    is_raspberry_pi = os.path.exists('/proc/device-tree/model') and 'Raspberry Pi' in open('/proc/device-tree/model', 'r').read()
    if is_raspberry_pi and 'QT_QPA_PLATFORM' not in os.environ:
        cmd.append('--platform')
        cmd.append('xcb')
        print("Using --platform xcb for better compatibility on Raspberry Pi")
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
    except Exception as e:
        print(f"Error running application: {e}")

if __name__ == "__main__":
    main()
