#!/usr/bin/env python3
"""
Quick Classification Test Script
Simple wrapper for testing classification with image path input
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    print("🧪 Quick Classification Tool Test")
    print("=" * 40)
    
    # Get image path from user
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = input("📷 Enter image path (or press Enter for test image): ").strip()
    
    # If no path provided, create test image
    if not image_path:
        print("🎨 No image path provided, creating test image...")
        cmd = f'python "{project_root}/test_classification_tool.py" --create-test pilsner --output result.jpg'
    else:
        # Check if file exists
        if not os.path.exists(image_path):
            print(f"❌ File not found: {image_path}")
            return
        
        print(f"📷 Processing image: {image_path}")
        cmd = f'python "{project_root}/test_classification_tool.py" --image "{image_path}" --output result.jpg'
    
    # Run classification
    print("🚀 Running classification...")
    os.system(cmd)
    
    # Check if result exists
    if os.path.exists("result.jpg"):
        print("\n✅ Classification completed!")
        print("📁 Results:")
        print("   - result.jpg (processed image)")
        
        # Try to open result (Windows)
        try:
            os.system("start result.jpg")
        except:
            print("   (Open result.jpg to view the processed image)")
    else:
        print("\n❌ Classification failed - no result generated")

if __name__ == "__main__":
    main()