#!/usr/bin/env python3
"""
Test Camera Format String Mapping Fix
Kiểm tra xem format mapping từ RGB888→XRGB8888 đã được implement
"""

import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_camera_format_mapping():
    """Test format mapping implementation"""
    print("\n" + "="*70)
    print("TEST: Camera Format String Mapping Fix")
    print("="*70)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Camera Stream Format Mapping
    tests_total += 1
    print(f"\n[Test {tests_total}] Camera Stream Format Mapping")
    try:
        with open(r'e:\PROJECT\sed\camera\camera_stream.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Check for format_map
        if "format_map = {" in content and "'RGB888': 'XRGB8888'" in content:
            print("✅ PASS: Format mapping dictionary found")
            tests_passed += 1
        else:
            print("❌ FAIL: Format mapping dictionary NOT found")
            
        # Check for format string persistence
        if "self._pixel_format = str(pixel_format)" in content:
            print("✅ PASS: Format string persistence found")
            tests_passed += 1
        else:
            print("❌ FAIL: Format string persistence NOT found")
            
        # Check for actual_format usage
        if "actual_format = format_map.get" in content:
            print("✅ PASS: Format mapping lookup found")
            tests_passed += 1
        else:
            print("❌ FAIL: Format mapping lookup NOT found")
            
    except Exception as e:
        print(f"❌ ERROR: Could not read camera_stream.py: {e}")
    
    # Test 2: Camera Tool Default Format
    tests_total += 1
    print(f"\n[Test {tests_total}] Camera Tool Default Format")
    try:
        with open(r'e:\PROJECT\sed\tools\camera_tool.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Check for RGB888 default (not BGR888)
        default_count = content.count('self.config.get("format", "RGB888")')
        if default_count >= 1:
            print(f"✅ PASS: Found RGB888 default ({default_count} occurrence(s))")
            tests_passed += 1
        else:
            print("❌ FAIL: RGB888 default NOT found")
            
        # Check for set_default RGB888
        if 'self.config.set_default("format", "RGB888")' in content:
            print("✅ PASS: set_default uses RGB888")
            tests_passed += 1
        else:
            print("❌ FAIL: set_default does NOT use RGB888")
            
    except Exception as e:
        print(f"❌ ERROR: Could not read camera_tool.py: {e}")
    
    # Test 3: CameraView XRGB Handling
    tests_total += 1
    print(f"\n[Test {tests_total}] CameraView XRGB Handling")
    try:
        with open(r'e:\PROJECT\sed\gui\camera_view.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Check for RGB888 + XRGB8888 handling
        if "str(pixel_format) in ('RGB888', 'XRGB8888')" in content:
            print("✅ PASS: RGB888/XRGB8888 handling found")
            tests_passed += 1
        else:
            print("❌ FAIL: RGB888/XRGB8888 handling NOT found")
            
        # Check for BGR888 + XBGR8888 handling  
        if "str(pixel_format) in ('BGR888', 'XBGR8888')" in content:
            print("✅ PASS: BGR888/XBGR8888 handling found")
            tests_passed += 1
        else:
            print("❌ FAIL: BGR888/XBGR8888 handling NOT found")
            
        # Check for BGRA2RGB conversion
        if "cv2.COLOR_BGRA2RGB" in content and "drop X" in content:
            print("✅ PASS: BGRA->RGB conversion found")
            tests_passed += 1
        else:
            print("❌ FAIL: BGRA->RGB conversion NOT found")
            
    except Exception as e:
        print(f"❌ ERROR: Could not read camera_view.py: {e}")
    
    # Summary
    print("\n" + "="*70)
    print(f"RESULTS: {tests_passed}/{tests_total} checks passed")
    print("="*70)
    
    if tests_passed >= 8:
        print("\n✅ FORMAT MAPPING FIX VERIFIED!")
        print("\nFormat flow:")
        print("  RGB888 (user select)")
        print("    ↓ format_map")
        print("  XRGB8888 (hardware)")
        print("    ↓ capture")
        print("  XRGB8888 frame (4-channel)")
        print("    ↓ BGRA→RGB conversion")
        print("  RGB display ✅")
        return True
    else:
        print("\n❌ Some checks failed.")
        return False

if __name__ == '__main__':
    success = test_camera_format_mapping()
    sys.exit(0 if success else 1)
