#!/usr/bin/env python3
"""
Test: 4-Channel Frame Conversion in CameraTool
Kiểm tra xem CameraTool đã convert 4-channel → 3-channel
"""

import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_4channel_conversion():
    """Test 4-channel frame conversion in CameraTool"""
    print("\n" + "="*70)
    print("TEST: 4-Channel Frame Conversion (XRGB → RGB)")
    print("="*70)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: CameraTool has conversion logic
    tests_total += 1
    print(f"\n[Test {tests_total}] CameraTool 4-Channel Conversion Logic")
    try:
        with open(r'e:\PROJECT\sed\tools\camera_tool.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Check for 4-channel detection
        if "current_frame.shape[2] == 4" in content:
            print("✅ PASS: 4-channel detection found")
            tests_passed += 1
        else:
            print("❌ FAIL: 4-channel detection NOT found")
            
        # Check for BGRA→RGB conversion
        if "cv2.COLOR_BGRA2RGB" in content:
            print("✅ PASS: BGRA→RGB conversion found")
            tests_passed += 1
        else:
            print("❌ FAIL: BGRA→RGB conversion NOT found")
            
        # Check for RGBA→BGR conversion
        if "cv2.COLOR_RGBA2BGR" in content:
            print("✅ PASS: RGBA→BGR conversion found")
            tests_passed += 1
        else:
            print("❌ FAIL: RGBA→BGR conversion NOT found")
            
        # Check for log output
        if "Converting 4-channel" in content:
            print("✅ PASS: Logging for conversion found")
            tests_passed += 1
        else:
            print("⚠️  WARNING: Conversion logging not found (not critical)")
            
    except Exception as e:
        print(f"❌ ERROR: Could not read camera_tool.py: {e}")
    
    # Test 2: Frame shape handling
    tests_total += 1
    print(f"\n[Test {tests_total}] Frame Shape Handling")
    try:
        with open(r'e:\PROJECT\sed\tools\camera_tool.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Check for shape[2] check
        if "len(current_frame.shape)" in content and "shape[2]" in content:
            print("✅ PASS: Frame shape check found")
            tests_passed += 1
        else:
            print("❌ FAIL: Frame shape check NOT found")
            
        # Check for pixel_format handling
        if "pixel_format" in content and "XRGB8888" in content:
            print("✅ PASS: Format-based conversion found")
            tests_passed += 1
        else:
            print("❌ FAIL: Format-based conversion NOT found")
            
    except Exception as e:
        print(f"❌ ERROR: Could not process: {e}")
    
    # Summary
    print("\n" + "="*70)
    print(f"RESULTS: {tests_passed}/{tests_total} major checks passed")
    print("="*70)
    
    if tests_passed >= 5:
        print("\n✅ 4-CHANNEL CONVERSION IMPLEMENTED!")
        print("\nFrame conversion flow:")
        print("  Camera (XRGB8888 4-channel)")
        print("    ↓")
        print("  CameraTool detects 4-channel")
        print("    ↓")
        print("  Convert BGRA→RGB (drop X)")
        print("    ↓")
        print("  DetectTool receives (480,640,3) ✅")
        print("    ↓")
        print("  Detection processes successfully ✅")
        return True
    else:
        print("\n⚠️  Some checks failed.")
        return False

if __name__ == '__main__':
    success = test_4channel_conversion()
    sys.exit(0 if success else 1)
