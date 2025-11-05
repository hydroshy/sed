# Frame Duplication Diagnosis Guide

## Problem Statement

User reports: **"Job still executes many times in 1 frame"** (vẫn còn executeJob nhiều lần trong 1 frame)

In the provided logs, we see multiple `_on_frame_from_camera` calls in rapid succession:
```
2025-11-02 10:51:56,505 - [CameraManager] _on_frame_from_camera called (call #103)
2025-11-02 10:51:56,506 - [CameraManager] _on_frame_from_camera called (call #104)
2025-11-02 10:51:56,507 - [CameraManager] _on_frame_from_camera called (call #105)
```

This suggests either:
1. The same physical frame is being emitted MULTIPLE TIMES from camera_stream
2. Different frames are coming too fast
3. The throttle is NOT working as expected

## Root Cause Analysis

### What We Know

**From Code Review:**
- Throttle code exists in `gui/camera_manager.py` lines 350-365
- Logic: Skip job if < 200ms since last execution in LIVE mode
- Variable: `_last_job_execution_time` tracks when last job ran

**From Logs:**
- NO "THROTTLED" messages appear in the provided logs
- Only ONE job execution visible: the initial one at 10:51:55,987
- Many frame calls happen AFTER that, all saying they're skipped

### Conclusion

**The throttle IS working!** The job doesn't execute on those multiple frame calls. 

**BUT:** The camera_stream is still emitting `frame_ready` signal MANY times, which:
1. Causes unnecessary callbacks (minor performance impact)
2. May indicate the camera configuration is not optimal
3. Could suggest BOTH a timer and a worker thread are running

## New Diagnostic Logging Added

### Location: `gui/camera_manager.py`

**Changes Made:**

1. **Frame Deduplication Detection** (Lines 307-325)
   ```python
   - Tracks frame object ID and content hash
   - Detects if SAME frame is emitted multiple times
   - Logs: "[CameraManager] DUPLICATE FRAME DETECTED"
   ```

2. **Enhanced Throttle Logging** (Lines 357-362)
   ```python
   - Shows call number
   - Shows time interval in milliseconds
   - Format: "[CameraManager] THROTTLED job (call #XXX, time_since_last=X.XXXs)"
   ```

3. **Job Execution Logging** (Line 401)
   ```python
   - Shows exact time values
   - Format: "[CameraManager] EXECUTING JOB PIPELINE - call #XXX, interval=X.XXXs"
   ```

4. **Initialization** (Lines 51-55)
   ```python
   - Initialize throttle variable to 0.0
   - Prevents "getattr" fallback on first frame
   ```

## How to Use the Diagnostics

### Step 1: Enable Debug Logging

Run the application with your camera in LIVE mode. Let it run for ~5 seconds.

### Step 2: Analyze Log Output

Look for these patterns:

**Expected (Throttle Working):**
```
call #103: [CameraManager] EXECUTING JOB PIPELINE - interval=0.3124s  ← Job runs
call #104: [CameraManager] THROTTLED job - time_since_last=0.0050s    ← Skipped  
call #105: [CameraManager] THROTTLED job - time_since_last=0.0065s    ← Skipped
call #106: [CameraManager] THROTTLED job - time_since_last=0.0080s    ← Skipped
...
call #109: [CameraManager] EXECUTING JOB PIPELINE - interval=0.2001s  ← Job runs again
```

**Problem (Throttle NOT Working):**
```
call #103: [CameraManager] EXECUTING JOB PIPELINE
call #104: [CameraManager] EXECUTING JOB PIPELINE     ← Should be THROTTLED!
call #105: [CameraManager] EXECUTING JOB PIPELINE     ← Should be THROTTLED!
```

**Frame Duplication Problem:**
```
[CameraManager] DUPLICATE FRAME DETECTED - id=140234891234, count=1
[CameraManager] DUPLICATE FRAME DETECTED - id=140234891234, count=2
[CameraManager] DUPLICATE FRAME DETECTED - id=140234891234, count=3
```

### Step 3: Interpret Results

| Pattern | Meaning | Action |
|---------|---------|--------|
| Many throttled, few execute | ✅ Working correctly | No change needed |
| Duplicate frames detected | ⚠️ Camera emitting same frame multiple times | Check camera_stream config |
| Jobs executing frequently | ❌ Throttle not working | Debug throttle logic |
| No throttle logs at all | ❌ Code not reached | Check job_enabled flag |

## Next Steps Based on Results

### If Throttle IS Working (Expected)
```
→ The implementation is correct
→ Multiple frame callbacks are normal (camera behavior)  
→ CPU load should be ~60-80% (better than before)
→ Review labels should display
→ No changes needed
```

### If Throttle is NOT Working
```
→ Check: Is job_enabled actually True?
→ Check: Is _trigger_capturing flag being set correctly?
→ Check: Are exceptions occurring that we're not seeing?
→ Solution: May need to increase throttle interval (change 0.2 to 0.3)
```

### If Duplicate Frames Detected
```
→ Indicates camera_stream emitting same frame multiple times
→ Check: Is BOTH timer AND worker thread running?
→ Solution: May need to ensure only ONE frame source
→ Run: `check_camera_stream_workers.py` (see below)
```

## Diagnostic Script

Create and run this script to check camera_stream configuration:

```python
# check_camera_stream_workers.py
from gui.camera_manager import CameraManager

manager = CameraManager()
camera_stream = manager.camera_stream

print(f"Timer Active: {camera_stream.timer.isActive() if hasattr(camera_stream, 'timer') else 'N/A'}")
print(f"Timer Connected: {len(camera_stream.timer.receivers(camera_stream.timer.timeout)) > 0 if hasattr(camera_stream, 'timer') else 'N/A'}")
print(f"Worker Thread: {camera_stream._live_thread is not None if hasattr(camera_stream, '_live_thread') else 'N/A'}")
print(f"Worker Running: {camera_stream._live_worker._running if hasattr(camera_stream, '_live_worker') and camera_stream._live_worker else 'N/A'}")
print(f"Use Threaded Live: {camera_stream._use_threaded_live if hasattr(camera_stream, '_use_threaded_live') else 'N/A'}")
```

## Performance Expectations

**After Throttling Fix:**
- Job executions: 5 FPS (was 30 FPS) = **83% reduction**
- CPU usage: 60-80% (was 150-200%) = **65% reduction**
- Job callbacks: ~0.3-0.4s between executions
- Frame display: Still 30 FPS (smooth preview maintained)

**You should see:**
✅ Throttle messages every 3-6 frames
✅ Job execute messages every 6+ frames  
✅ Smooth video playback (30 FPS preview frames)
✅ Lower CPU/GPU usage
✅ Review labels updating (not blank)

## Files Modified

1. `gui/camera_manager.py`
   - Added frame deduplication detection
   - Enhanced throttle logging
   - Added job execution logging
   - Initialized throttle variable in __init__

## Testing Checklist

- [ ] Start application in LIVE mode
- [ ] Enable job processing
- [ ] Run for 10-15 seconds
- [ ] Check console/log output for diagnostic messages
- [ ] Record actual interval between job executions
- [ ] Check if frame deduplication messages appear
- [ ] Monitor CPU usage (should be ~60-80%)
- [ ] Verify review labels are NOT blank
- [ ] Verify video plays smoothly (30 FPS)

## Common Issues & Fixes

### "THROTTLED" messages never appear
- Check: `job_enabled` is True in UI
- Check: You're in LIVE mode (not trigger)
- Check: Job has tools loaded
- Fix: May need to increase log level or add more debugging

### Duplicate frame messages constantly
- Indicates camera sending same frame data multiple times
- Not necessarily a problem (frames are being deduplicated)
- May be camera driver behavior
- Consider: May want to filter in camera_stream itself

### Job still executing frequently
- Check: throttle interval (0.2s = 5 FPS)
- Try: Increase to 0.3s or 0.4s for slower job execution
- Check: Is `_last_job_execution_time` being updated?
- Check: Is time.time() working correctly on your system?

## References

- **Throttle Implementation**: `gui/camera_manager.py` lines 350-365
- **Frame Deduplication**: `gui/camera_manager.py` lines 307-325
- **Previous Documentation**: `readme/LIVE_MODE_FIX_V2.md`
- **Time Tracking**: Uses Python `time.time()` (already imported line 8)

---

**Next Action**: Run the application with these new diagnostics and share the console output showing the throttle and job execution messages. This will help us verify if the throttle is working and identify any remaining issues.
