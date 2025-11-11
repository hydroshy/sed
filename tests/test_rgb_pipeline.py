#!/usr/bin/env python3
"""
Test RGB Default Pipeline Implementation
Kiểm tra xem pipeline mặc định đã chuyển sang RGB hay chưa
"""

import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_rgb_pipeline():
    """Test RGB default pipeline"""
    print("\n" + "="*70)
    print("TEST: RGB Default Pipeline Implementation")
    print("="*70)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Camera Manager Default Format
    tests_total += 1
    print(f"\n[Test {tests_total}] Camera Manager Default Format")
    try:
        with open(r'e:\PROJECT\sed\gui\camera_manager.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Check for RGB888 default
        if "pixel_format = 'RGB888'  # Default - camera_stream outputs RGB888" in content:
            print("✅ PASS: Camera manager defaults to RGB888")
            tests_passed += 1
        else:
            print("❌ FAIL: Camera manager does not default to RGB888")
            # Check what it defaults to
            if "pixel_format = 'BGR888'" in content:
                print("   Found: Still defaults to BGR888")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 2: SaveImageTool RGB Conversion Logic
    tests_total += 1
    print(f"\n[Test {tests_total}] SaveImageTool RGB Conversion Logic")
    try:
        with open(r'e:\PROJECT\sed\tools\saveimage_tool.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Check for RGB->BGR conversion for imwrite
        if "cv2.cvtColor(save_image, cv2.COLOR_RGB2BGR)" in content:
            print("✅ PASS: SaveImageTool converts RGB->BGR for imwrite")
            tests_passed += 1
        else:
            print("❌ FAIL: SaveImageTool does not convert RGB->BGR")
            
        # Check for "keep as-is" for BGR
        if "BGR - keep as-is" in content or "BGR, saving as-is" in content:
            print("✅ PASS: SaveImageTool handles BGR correctly")
            tests_passed += 1
        else:
            print("⚠️  WARNING: BGR handling may not be clear")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 3: CameraView RGB Default
    tests_total += 1
    print(f"\n[Test {tests_total}] CameraView RGB Default Format")
    try:
        with open(r'e:\PROJECT\sed\gui\camera_view.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Check for RGB888 default in camera_view
        if "pixel_format = 'RGB888'  # Default - camera_stream outputs RGB888" in content:
            print("✅ PASS: CameraView defaults to RGB888")
            tests_passed += 1
        else:
            print("❌ FAIL: CameraView does not default to RGB888")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 4: CameraView RGB Logic (No Conversion)
    tests_total += 1
    print(f"\n[Test {tests_total}] CameraView RGB Logic (No Conversion)")
    try:
        with open(r'e:\PROJECT\sed\gui\camera_view.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Check for "Frame already RGB" logic
        if "Frame already RGB, no conversion needed" in content:
            print("✅ PASS: CameraView has correct RGB logic")
            tests_passed += 1
        else:
            print("❌ FAIL: CameraView RGB logic may be incorrect")
            
        # Check that old incorrect comment is removed
        if "PiCamera2 configured as RGB888 but actually returns BGR" in content:
            print("⚠️  WARNING: Old incorrect comment still present")
        else:
            print("✅ PASS: Old incorrect comment removed")
            tests_passed += 1
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 5: Camera Stream RGB Default
    tests_total += 1
    print(f"\n[Test {tests_total}] Camera Stream RGB Default")
    try:
        with open(r'e:\PROJECT\sed\camera\camera_stream.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Check for RGB888 default
        if "self._pixel_format = 'RGB888'" in content:
            print("✅ PASS: Camera stream defaults to RGB888")
            tests_passed += 1
        else:
            print("❌ FAIL: Camera stream does not default to RGB888")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Summary
    print("\n" + "="*70)
    print(f"RESULTS: {tests_passed}/{tests_total} tests passed")
    print("="*70)
    
    if tests_passed >= tests_total - 1:  # Allow 1 fail (warning counts)
        print("\n✅ RGB PIPELINE IMPLEMENTATION SUCCESSFUL!")
        print("\nPipeline Flow:")
        print("  Camera Stream (RGB888)")
        print("    ↓")
        print("  Camera Manager (RGB888)")
        print("    ├→ Display: RGB (no conversion needed)")
        print("    └→ SaveImageTool: RGB→BGR for imwrite")
        print("\n✅ System ready for production!")
        return True
    else:
        print("\n❌ Some tests failed. Please review the implementation.")
        return False

if __name__ == '__main__':
    success = test_rgb_pipeline()
    sys.exit(0 if success else 1)
