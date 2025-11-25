# Pending Frame Status Fix - COMPLETE ✅

## Problem
Frame status was showing **PENDING** instead of **OK/NG** immediately after trigger, because:
1. Job completes before TCP `start_rising` arrives (timing issue)
2. Result tries to attach to waiting frame but queue is empty
3. Result is discarded without being buffered
4. Frame created later shows default PENDING status

**Log evidence:**
```
17:52:09,100 - [CameraManager] Job completed → status=OK
[ResultTabManager] ❌ No frame waiting for result (queue empty!)

17:52:09,458 - [TCPController] start_rising received (too late!)
Frame created with status=PENDING (default)
```

## Root Cause Analysis

**Timing sequence (WRONG):**
```
JOB PIPELINE                    TCP SIGNAL
==================             ===========
Frame captured
Run detection
Run classification
Job completes (result=OK)
Try to attach result ❌
(no waiting frame)

                                start_rising arrives (LATE!)
                                Frame created (PENDING)
```

The **result is lost** because:
- Only one `attach_job_result_to_waiting_frame()` attempt
- No buffering mechanism if frame not ready yet
- Result discarded with warning

## Solution Implemented

**Two-part fix:**

### 1. Buffer Result in Camera Manager (when no waiting frame)
**File: `gui/camera_manager.py` (Line ~3015)**

Instead of just warning when no frame is waiting, now **buffer the result** using the pending result mechanism:

```python
# OLD (BROKEN):
if success:
    print("Attached to frame")
else:
    print("No waiting frame")  # ❌ RESULT LOST!

# NEW (FIXED):
if success:
    print("Attached to frame")
else:
    # ✅ Buffer result for later
    result_tab_manager.save_pending_job_result(
        status=status,
        detection_data=detection_data,
        inference_time=...,
        reason=reason
    )
    print("Result buffered successfully")
```

### 2. Auto-Attach Buffered Result When Frame Arrives (on_sensor_in_received)
**File: `gui/result_tab_manager.py` (Line ~265)**

When `start_rising` arrives and frame is created, check if result was buffered earlier and attach it **immediately**:

```python
# When frame created from TCP start_rising:
if self.pending_result:
    # ✅ CRITICAL FIX: Attach pending result from earlier job
    frame_id = add_sensor_in_event(sensor_id_in)
    
    success = self.fifo_queue.set_frame_status(frame_id, pending.status)
    # Result attached immediately - NO PENDING status!
    self.refresh_table()  # Show OK/NG right away
else:
    # No pending result - add to waiting queue
    self.waiting_frames_queue.append(frame_id)
```

## Result Flow (FIXED)

```
JOB PIPELINE                    TCP SIGNAL
==================             ===========
Frame captured
Run detection
Run classification
Job completes (result=OK)
Try to attach ❌ (no frame)

✅ BUFFER result
save_pending_job_result(OK)

                                start_rising arrives
                                Frame created
                                
                                ✅ Check pending_result
                                ✅ Attach buffered result
                                ✅ set_frame_status(frame_id, OK)
                                ✅ refresh_table()
                                
                                Frame shows: OK ✅ (NOT pending!)
```

## Changes Made

### File: `gui/camera_manager.py`
**Location:** Lines ~3015-3065 (attach_job_result_to_waiting_frame section)

- ✅ When `attach_job_result_to_waiting_frame()` returns False (no waiting frame)
- ✅ Call `save_pending_job_result()` to buffer the result instead
- ✅ Log "Result buffered successfully"

### File: `gui/result_tab_manager.py`
**Location:** Lines ~265-330 (on_sensor_in_received method)

- ✅ Check if `self.pending_result` exists when frame is created
- ✅ If pending result exists:
  - Attach to frame immediately
  - Set frame_status to OK/NG
  - Clear pending_result buffer
  - Refresh table
- ✅ If no pending result:
  - Add frame to waiting_frames_queue (normal flow)

## Key Implementation Details

**Buffer mechanism:**
```python
# ResultTabManager initialization (Line ~50)
self.pending_result: Optional[PendingJobResult] = None

# When job finishes with no waiting frame (camera_manager)
self.save_pending_job_result(
    status='OK',
    similarity=0.0,
    reason='...',
    detection_data={...},
    inference_time=0.2
)

# When frame arrives (result_tab_manager)
if self.pending_result:
    pending = self.pending_result
    set_frame_status(frame_id, pending.status)  # OK/NG attached!
    self.pending_result = None  # Clear buffer
```

## Expected Behavior (After Fix)

**Scenario: Trigger camera**

1. ✅ Job runs → completes with status=OK
2. ✅ No waiting frame yet → **Buffer result** (FIXED!)
3. ✅ TCP start_rising arrives
4. ✅ Frame created (frame_id=1)
5. ✅ **Pending result attached immediately**
6. ✅ **Frame shows: OK** (NOT PENDING!)
7. ✅ Result Tab updated right away

**Previous behavior (BROKEN):**
1. Job completed with result=OK
2. No frame waiting → Result **DISCARDED**
3. TCP start_rising arrives too late
4. Frame created with default PENDING status
5. Frame stuck showing PENDING forever

## Status

✅ **COMPLETE** - Result buffering and auto-attachment implemented

### Files Modified
- ✅ `gui/camera_manager.py` - Buffer result when no waiting frame
- ✅ `gui/result_tab_manager.py` - Auto-attach buffered result to new frames

### Testing Recommendations
1. Trigger camera and observe frame status immediately
2. Frame should show **OK** or **NG** instantly (not PENDING)
3. Check logs for "✅ Result buffered" and "✅ Attached pending result" messages
4. Verify with multiple rapid triggers

## Technical Details

**PendingJobResult structure** (from `pending_result.py`):
```python
class PendingJobResult:
    status: str          # 'OK' or 'NG'
    similarity: float    # 0.0-1.0
    reason: str         # Why OK/NG
    detection_data: Dict  # Detection info
    inference_time: float  # Processing time
    timestamp: float    # When result created
```

**Queue mechanism** (unchanged but now with buffering):
- `waiting_frames_queue` - Frames waiting for job results
- `pending_result` - **NEW**: Buffered result waiting for frame (solves timing issue!)
- FIFO + Buffer = Robust handling of timing mismatches
