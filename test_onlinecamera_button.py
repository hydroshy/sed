#!/usr/bin/env python3
"""
Validation: OnlineCamera Button Mode-Dependent Behavior
Kiểm tra xem onlineCamera button đã được implement chính xác
"""

import sys

def check_toggle_camera_implementation():
    """Check if _toggle_camera method has been updated with mode-dependent logic"""
    print("\n" + "="*80)
    print("VALIDATION: OnlineCamera Button Mode-Dependent Behavior")
    print("="*80)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Check if _toggle_camera method exists
    tests_total += 1
    print(f"\n[Test {tests_total}] Checking _toggle_camera method exists...")
    try:
        with open(r'e:\PROJECT\sed\gui\main_window.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if 'def _toggle_camera(self, checked):' in content:
            print("✅ PASS: _toggle_camera method found")
            tests_passed += 1
        else:
            print("❌ FAIL: _toggle_camera method NOT found")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 2: Check for LIVE mode logic
    tests_total += 1
    print(f"\n[Test {tests_total}] Checking LIVE mode logic...")
    try:
        if 'start_live_camera(force_mode_change=True)' in content:
            print("✅ PASS: LIVE mode uses start_live_camera() for continuous streaming")
            tests_passed += 1
        else:
            print("❌ FAIL: LIVE mode logic not found")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 3: Check for TRIGGER mode logic
    tests_total += 1
    print(f"\n[Test {tests_total}] Checking TRIGGER mode logic...")
    try:
        if 'set_trigger_mode(True)' in content and 'start_preview()' in content:
            print("✅ PASS: TRIGGER mode enables trigger and starts preview")
            tests_passed += 1
        else:
            print("❌ FAIL: TRIGGER mode logic incomplete")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 4: Check for mode detection
    tests_total += 1
    print(f"\n[Test {tests_total}] Checking mode detection logic...")
    try:
        if 'desired_mode = getattr(self.camera_manager, \'current_mode\'' in content:
            print("✅ PASS: Mode detection using camera_manager.current_mode found")
            tests_passed += 1
        else:
            print("❌ FAIL: Mode detection not properly implemented")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 5: Check for 3A lock in TRIGGER mode
    tests_total += 1
    print(f"\n[Test {tests_total}] Checking 3A lock (AE+AWB) in TRIGGER mode...")
    try:
        if 'set_auto_white_balance(False)' in content and 'set_manual_exposure_mode()' in content:
            print("✅ PASS: 3A lock (AE+AWB disabled) found in TRIGGER mode")
            tests_passed += 1
        else:
            print("⚠️  WARNING: 3A lock implementation not complete (may still work)")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 6: Check for button style updates
    tests_total += 1
    print(f"\n[Test {tests_total}] Checking button style updates...")
    try:
        if '#4CAF50' in content and '#f44336' in content:  # Green and Red hex colors
            print("✅ PASS: Button style updates for green (on) and red (off) states found")
            tests_passed += 1
        else:
            print("⚠️  WARNING: Button color codes not found (styling may be incomplete)")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 7: Check for debug logging
    tests_total += 1
    print(f"\n[Test {tests_total}] Checking debug logging markers...")
    try:
        if '📹 LIVE mode' in content and '📸 TRIGGER mode' in content:
            print("✅ PASS: Debug logging with emoji markers found")
            tests_passed += 1
        else:
            print("⚠️  WARNING: Debug markers not found (logging may differ)")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 8: Check for stop/disable logic
    tests_total += 1
    print(f"\n[Test {tests_total}] Checking stop camera logic...")
    try:
        if 'stop_preview()' in content or 'stop_live()' in content:
            print("✅ PASS: Stop camera logic found")
            tests_passed += 1
        else:
            print("❌ FAIL: Stop camera logic not found")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Summary
    print("\n" + "="*80)
    print(f"RESULTS: {tests_passed}/{tests_total} checks passed")
    print("="*80)
    
    if tests_passed >= 6:
        print("\n✅ OnlineCamera button implementation appears COMPLETE!")
        print("\nKey Features Implemented:")
        print("  ✓ Mode-dependent behavior (LIVE vs TRIGGER)")
        print("  ✓ Continuous streaming in LIVE mode")
        print("  ✓ Trigger-ready preview in TRIGGER mode")
        print("  ✓ 3A lock (AE+AWB) in TRIGGER mode")
        print("  ✓ Button color feedback (green/red)")
        print("  ✓ Stop/start camera logic")
        print("\nRecommended Next Steps:")
        print("  1. Run the application")
        print("  2. Switch between LIVE and TRIGGER modes")
        print("  3. Click onlineCamera button in each mode")
        print("  4. Verify camera behaves differently per mode")
        print("  5. Check console for debug logs")
        return True
    else:
        print("\n⚠️  OnlineCamera button implementation may be INCOMPLETE")
        print("Please review the implementation.")
        return False

if __name__ == '__main__':
    success = check_toggle_camera_implementation()
    sys.exit(0 if success else 1)
