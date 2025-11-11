# ✅ Trigger Mode Fix - Testing & Validation Checklist

## Pre-Testing Checklist

### Prerequisites
- [ ] Raspberry Pi with GS Camera (IMX296) connected
- [ ] External trigger source available (GPIO, sensor, or pulse generator)
- [ ] Python application downloaded/updated
- [ ] All dependencies installed (`requirements.txt`)
- [ ] Camera permissions set correctly

### Code Verification
- [ ] File `gui/main_window.py` updated with thread wait code
  - [ ] Lines 995-1020 contain `operation_thread.wait(5000)`
  - [ ] Verify syntax is correct (no errors on startup)
  - [ ] Verify logging statements are present

### Configuration Check
- [ ] sudo configured for sysfs access (one-time setup):
  ```bash
  sudo visudo
  # Add line: pi ALL=(ALL) NOPASSWD: /usr/bin/tee
  ```
- [ ] sysfs path exists: `/sys/module/imx296/parameters/trigger_mode`
  ```bash
  ls -la /sys/module/imx296/parameters/trigger_mode
  # Should show: rw-r--r-- pi root
  ```
- [ ] Can read current value:
  ```bash
  cat /sys/module/imx296/parameters/trigger_mode
  # Should show: 0 (disabled) or 1 (enabled)
  ```

---

## Test Case 1: Trigger Mode Activation

### Test 1A: Verify Automatic Trigger Mode Enable

**Steps:**
1. [ ] Start application
2. [ ] Load job with Camera Source tool
3. [ ] In logs, confirm: `_has_camera_source_in_job: Found Camera Source by display_name`
4. [ ] Click "onlineCamera" button
5. [ ] Monitor logs for (in order):

```
✅ MUST SEE (In This Order):
├─ "ℹ️ Enabling trigger mode automatically when starting camera..."
├─ ">>> CALLING: camera_manager.set_trigger_mode(True)"
├─ ">>> RESULT: set_trigger_mode(True) returned: True"
├─ "⏳ Waiting for trigger mode command to complete..."
├─ "DEBUG: [CameraStream] Running external trigger command: echo 1 | sudo tee /sys/module/imx296/parameters/trigger_mode"
├─ "✅ [CameraStream] External trigger ENABLED"
│  └─ "Output: 1"
├─ "✅ Trigger mode command completed (sysfs executed)"
├─ "✅ Trigger mode enabled automatically"
├─ "Camera stream started successfully"
├─ "🔒 Locking 3A (AE + AWB) for trigger mode..."
├─ "✅ AWB locked"
└─ "✅ 3A locked (AE + AWB disabled)"

❌ MUST NOT SEE:
├─ "⚠️ Trigger mode command timeout" (unless rare)
├─ "ERROR" or "Failed" messages
├─ "❌ External trigger" message
└─ Any exception messages
```

**Expected Result:** ✅ All success messages appear in correct order

**Pass/Fail:** ___________

---

## Test Case 2: Hardware Trigger Reception

### Test 2A: Single Hardware Trigger

**Setup:**
- [ ] Camera started from Test 1A (still running in trigger mode)
- [ ] External trigger source ready
- [ ] Camera view visible on screen

**Steps:**
1. [ ] Send ONE hardware trigger signal from external source
   - [ ] GPIO pulse, OR
   - [ ] Sensor trigger signal, OR
   - [ ] Manual pulse generator button
2. [ ] Observe camera view for frame
3. [ ] Check logs for new frame event
4. [ ] Check Result Tab for detection result

**Expected Result:**
- [ ] Frame appears in camera view ✅
- [ ] Result Tab shows detection ✅
- [ ] NO manual "Trigger Camera" button click needed ✅

**Pass/Fail:** ___________

### Test 2B: Multiple Hardware Triggers

**Steps:**
1. [ ] Send 5 hardware trigger signals (with 1-2 sec delay between each)
2. [ ] Observe 5 frames captured automatically
3. [ ] Each frame should appear in Result Tab
4. [ ] NO manual button clicks needed

**Expected Result:** ✅ All 5 frames captured, displayed in Result Tab

**Pass/Fail:** ___________

### Test 2C: Rapid Hardware Triggers

**Steps:**
1. [ ] Send hardware trigger signals as fast as possible (10+ triggers)
2. [ ] Monitor for frames and detections
3. [ ] Check logs for any dropped frames or errors

**Expected Result:** ✅ Most/all frames captured (some may be dropped due to processing time)

**Pass/Fail:** ___________

---

## Test Case 3: 3A Lock Verification

### Test 3A: Exposure Consistency

**Steps:**
1. [ ] Camera started with trigger mode active
2. [ ] Send 3 hardware trigger signals
3. [ ] All 3 frames should have identical brightness/exposure
4. [ ] Compare frames in Result Tab
5. [ ] Verify no exposure variation between captures

**Expected Result:** ✅ All frames have same exposure (3A locked)

**Pass/Fail:** ___________

**Visual Check:**
- [ ] Frame 1 brightness: ___________
- [ ] Frame 2 brightness: ___________
- [ ] Frame 3 brightness: ___________
- [ ] Are they identical? ✅ / ❌

### Test 3B: White Balance Consistency

**Steps:**
1. [ ] With trigger mode active
2. [ ] Send 3 hardware trigger signals with varied lighting
3. [ ] All 3 frames should have identical white balance
4. [ ] Compare color tone in Result Tab

**Expected Result:** ✅ All frames have same white balance (locked)

**Pass/Fail:** ___________

---

## Test Case 4: Mode Switching

### Test 4A: Trigger → Live Mode Switch

**Steps:**
1. [ ] Start in trigger mode (onlineCamera checked)
2. [ ] Click "liveCameraMode" button (if available)
3. [ ] Or click "onlineCamera" to stop trigger mode
4. [ ] Check logs for trigger mode disable

**Expected Result:**
- [ ] Trigger mode disabled ✅
- [ ] Camera switches to live mode ✅
- [ ] Logs show mode change ✅

**Pass/Fail:** ___________

### Test 4B: Live → Trigger Mode Switch

**Steps:**
1. [ ] Start in live mode
2. [ ] Stop camera (click onlineCamera to uncheck)
3. [ ] Start in trigger mode (click onlineCamera again)
4. [ ] Verify trigger mode activation logs appear

**Expected Result:** ✅ Same logs as Test 1A appear

**Pass/Fail:** ___________

---

## Test Case 5: Error Handling

### Test 5A: sysfs Permission Denied

**Setup:**
- [ ] Temporarily remove sudo permission (for testing only)
- [ ] Comment out sudoers line temporarily

**Steps:**
1. [ ] Click "onlineCamera"
2. [ ] Check logs for error handling

**Expected Result:**
- [ ] Error message: "❌ Failed to set external trigger" ✅
- [ ] Error details shown ✅
- [ ] Application doesn't crash ✅

**Pass/Fail:** ___________

**Cleanup:**
- [ ] Restore sudoers permission immediately

### Test 5B: Camera Not Available

**Setup:**
- [ ] Disconnect/disable camera hardware temporarily

**Steps:**
1. [ ] Click "onlineCamera"
2. [ ] Check logs for graceful error handling

**Expected Result:**
- [ ] Appropriate error message ✅
- [ ] Application handles gracefully ✅
- [ ] No crash ✅

**Pass/Fail:** ___________

**Cleanup:**
- [ ] Reconnect camera

### Test 5C: Thread Timeout (Rare)

**Setup:**
- [ ] Artificially slow down sysfs command (if possible)
- [ ] Or just monitor for timeout handling

**Steps:**
1. [ ] Click "onlineCamera"
2. [ ] If wait takes >5 seconds, should see timeout warning
3. [ ] Application should proceed anyway

**Expected Result:**
- [ ] Either: Normal completion ✅
- [ ] Or: "⚠️ Trigger mode command timeout" warning ✅
- [ ] Camera proceeds to start ✅

**Pass/Fail:** ___________

---

## Test Case 6: Log Verification

### Test 6A: All Expected Logs Present

**Checklist of Required Logs:**
- [ ] "Simple camera toggle: True"
- [ ] "ℹ️ Enabling trigger mode automatically when starting camera..."
- [ ] ">>> CALLING: camera_manager.set_trigger_mode(True)"
- [ ] ">>> RESULT: set_trigger_mode(True) returned: True"
- [ ] "⏳ Waiting for trigger mode command to complete..."
- [ ] "Running external trigger command: echo 1 | sudo tee..."
- [ ] "✅ External trigger ENABLED"
- [ ] "✅ Trigger mode command completed (sysfs executed)"
- [ ] "Camera stream started successfully"
- [ ] "🔒 Locking 3A (AE + AWB) for trigger mode..."
- [ ] "✅ 3A locked (AE + AWB disabled)"

**Result:** ✅ All found / ❌ Missing: _____________

**Pass/Fail:** ___________

### Test 6B: No Error Logs

**Checklist of Forbidden Error Logs:**
- [ ] NO "ERROR" messages
- [ ] NO "Failed" messages
- [ ] NO "❌" error indicators
- [ ] NO exception tracebacks
- [ ] NO "Permission denied"
- [ ] NO "No such file or directory"

**Result:** ✅ No errors / ❌ Found errors: _____________

**Pass/Fail:** ___________

---

## Test Case 7: Performance

### Test 7A: Response Time

**Measurement:**
- [ ] Time from "onlineCamera" click to "Camera ready" log
- [ ] Should be ~1-2 seconds (mostly thread wait time)

**Steps:**
1. [ ] Click "onlineCamera"
2. [ ] Record time from click to: "✅ 3A locked"
3. [ ] Compare with expected: 1-2 seconds

**Result:** Total time: ___________ seconds

**Acceptable:** ✅ < 3 seconds / ❌ > 3 seconds

**Pass/Fail:** ___________

### Test 7B: Frame Capture Rate

**Measurement:**
- [ ] Send 10 hardware trigger signals in 10 seconds (1 per second)
- [ ] Measure time to capture all 10 frames
- [ ] Should capture all or most without delays

**Steps:**
1. [ ] Camera in trigger mode
2. [ ] Send 10 triggers at 1Hz rate
3. [ ] Check Result Tab for 10 detections
4. [ ] Measure total time taken

**Result:** Total time: ___________ seconds | Frames captured: ___________ / 10

**Acceptable:** ✅ 10+ seconds / ❌ Much slower

**Pass/Fail:** ___________

---

## Test Case 8: Complete Workflow

### Test 8A: Full Production Workflow

**Steps (Complete End-to-End):**
1. [ ] Start application
2. [ ] Load job with Camera Source tool
3. [ ] Add detection tool to job (e.g., Classification)
4. [ ] Click "onlineCamera" button
5. [ ] Wait for logs to complete
6. [ ] Send hardware trigger signal
7. [ ] Verify frame captured in camera view
8. [ ] Verify detection result in Result Tab
9. [ ] Send 5 more trigger signals
10. [ ] Verify all 6 results in Result Tab with consistent 3A

**Expected Result:** ✅ Complete workflow without manual trigger clicks

**Pass/Fail:** ___________

---

## Summary Scoring

| Test Case | Status | Pass/Fail |
|-----------|--------|-----------|
| Test 1A: Trigger Mode Activation | ✅ / ❌ | ___________|
| Test 2A: Single Hardware Trigger | ✅ / ❌ | ___________|
| Test 2B: Multiple Hardware Triggers | ✅ / ❌ | ___________|
| Test 2C: Rapid Hardware Triggers | ✅ / ❌ | ___________|
| Test 3A: Exposure Consistency | ✅ / ❌ | ___________|
| Test 3B: White Balance Consistency | ✅ / ❌ | ___________|
| Test 4A: Trigger → Live Switch | ✅ / ❌ | ___________|
| Test 4B: Live → Trigger Switch | ✅ / ❌ | ___________|
| Test 5A: Permission Error Handling | ✅ / ❌ | ___________|
| Test 5B: Camera Error Handling | ✅ / ❌ | ___________|
| Test 5C: Thread Timeout Handling | ✅ / ❌ | ___________|
| Test 6A: All Expected Logs | ✅ / ❌ | ___________|
| Test 6B: No Error Logs | ✅ / ❌ | ___________|
| Test 7A: Response Time | ✅ / ❌ | ___________|
| Test 7B: Frame Capture Rate | ✅ / ❌ | ___________|
| Test 8A: Complete Workflow | ✅ / ❌ | ___________|

**Total Passed:** _____ / 16

**Overall Result:** ✅ PASS / ❌ FAIL

---

## Issues Found During Testing

### Issue #1
**Description:** _____________________________________________________________
**Steps to Reproduce:** _______________________________________________________
**Expected vs Actual:** _______________________________________________________
**Severity:** 🔴 Critical / 🟡 High / 🟢 Medium / 🔵 Low
**Resolution:** ______________________________________________________________

### Issue #2
**Description:** _____________________________________________________________
**Steps to Reproduce:** _______________________________________________________
**Expected vs Actual:** _______________________________________________________
**Severity:** 🔴 Critical / 🟡 High / 🟢 Medium / 🔵 Low
**Resolution:** ______________________________________________________________

---

## Testing Sign-Off

**Tester Name:** ___________________________

**Date:** ___________________________

**Overall Status:** ✅ PASSED / 🔴 FAILED

**Ready for Production:** ✅ YES / ❌ NO (Issues: _______)

**Notes:** __________________________________________________________________

__________________________________________________________________________

---

## Quick Troubleshooting Guide

### Symptom 1: No "External trigger ENABLED" message
```
Causes:
├─ sysfs path doesn't exist
├─ Permission denied
└─ sudo not configured

Solution:
1. Check: cat /sys/module/imx296/parameters/trigger_mode
2. If error: wrong kernel module or Raspberry Pi
3. If permission: sudo visudo → add sudoers line
```

### Symptom 2: Still need manual "Trigger Camera" clicks
```
Causes:
├─ Sysfs command failed
├─ 3A not locked
└─ Camera still in preview mode

Solution:
1. Check logs for: "✅ External trigger ENABLED"
2. If missing: check sysfs permissions
3. Check: "✅ 3A locked" message present
```

### Symptom 3: "⏳ Waiting..." but never completes
```
Causes:
├─ Thread hanging
├─ sysfs command stuck
└─ System overload

Solution:
1. Wait 5 seconds (timeout will trigger)
2. Check system resources: top, htop
3. Restart application
```

### Symptom 4: Frame capture very slow
```
Causes:
├─ Detection tool slow
├─ Result Tab slow
└─ Hardware trigger rate limited

Solution:
1. Profile detection tool performance
2. Check Result Tab optimization
3. Verify hardware trigger source can send faster
```

---

**Test Plan Created:** November 7, 2025  
**Status:** Ready for Testing  
**Next Step:** Execute all test cases on GS Camera hardware  

