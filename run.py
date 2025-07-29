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
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
    except Exception as e:
        print(f"Error running application: {e}")

if __name__ == "__main__":
    main()
