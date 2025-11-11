# TCP First, Then Job Result - New Flow Architecture

## 🎯 Overview

**New Logic**: Frame entry is created **BEFORE** job result is ready.

```
TCP Signal (start_rising)
        ↓
   Create Frame Entry
   (frame_status=PENDING, waiting for job)
        ↓
  Job Processes Frame
        ↓
   Job Result Ready
        ↓
   Attach Result to Frame
   (frame_status→OK/NG)
        ↓
  Frame Complete ✅
```

---

## 📋 Flow Sequence

### Step 1: TCP Receives start_rising Signal
```
Pico sends: start_rising||36247640
         ↓
TCP receives message
         ↓
_handle_start_rising() called
```

### Step 2: Create Frame Entry (TCP First)
```
_handle_start_rising()
    ↓
_handle_sensor_in_event(sensor_id=36247640)
    ↓
on_sensor_in_received(sensor_id_in=36247640)
    ↓
add_sensor_in_event(36247640)
    ├─ frame_id = 1 (auto-incremented)
    ├─ sensor_id_in = 36247640
    ├─ frame_status = PENDING (default)
    ├─ completion_status = PENDING
    └─ Table refreshed
    
frame_id_waiting_for_result = 1  ← Store frame ID
```

**Result**: Frame appears in table with:
- Frame ID: 1
- Frame Status: PENDING (yellow)
- Sensor IN: 36247640
- Sensor OUT: (empty)
- Completion Status: PENDING (yellow)

### Step 3: Job Processes (In Parallel)
```
Manual trigger initiated
    ↓
Camera captures frame
    ↓
Job pipeline runs:
  - Camera Source
  - Detect Tool
  - Result Tool
    ↓
Result: OK or NG
```

### Step 4: Attach Job Result to Waiting Frame
```
camera_manager._update_execution_label(job_results)
    ↓
Status = OK (or NG)
Reason = "Detection passed"
Detection data = {...}
    ↓
attach_job_result_to_waiting_frame(
    status='OK',
    detection_data={...},
    inference_time=0.210,
    reason='Detection passed'
)
    ├─ frame_id = self.frame_id_waiting_for_result (= 1)
    ├─ set_frame_status(frame_id=1, status='OK')
    │   └─ frame_status = OK ✓
    ├─ set_frame_detection_data(frame_id=1, data)
    │   └─ Store detection results
    ├─ refresh_table()
    │   └─ Table updated with new status
    └─ frame_id_waiting_for_result = None
```

**Result**: Frame updated in table:
- Frame ID: 1
- Frame Status: OK (green) ✅
- Sensor IN: 36247640
- Sensor OUT: (empty)
- Completion Status: PENDING (yellow)

### Step 5: TCP Receives end_rising Signal
```
Pico sends: end_rising||36261996
         ↓
TCP receives message
         ↓
_handle_end_rising() called
         ↓
add_sensor_out_event(sensor_id_out=36261996)
    ├─ Find first frame with completion_status=PENDING
    ├─ Set sensor_id_out = 36261996
    ├─ Mark completion_status = DONE (cyan)
    └─ Table refreshed
```

**Final Result**: Frame in table:
- Frame ID: 1
- Frame Status: OK (green)
- Sensor IN: 36247640
- Sensor OUT: 36261996
- Completion Status: DONE (cyan) ✅

---

## 🔄 Key Variables

### In ResultTabManager

```python
# Track which frame is waiting for job result
frame_id_waiting_for_result: Optional[int] = None

# When TCP start_rising arrives:
frame_id_waiting_for_result = 1  # Store frame ID

# When job result arrives:
attach_job_result_to_waiting_frame(status='OK', ...)
    └─ Update frame 1 with result
    └─ Reset to None
```

---

## 📦 Method Changes

### New Method: `attach_job_result_to_waiting_frame()`

**Location**: `gui/result_tab_manager.py`

**Purpose**: Attach job result to frame created by TCP signal

**Parameters**:
- `status`: Job result ('OK', 'NG')
- `detection_data`: Detection/classification data
- `inference_time`: Processing time
- `reason`: Result reason

**Process**:
1. Check if `frame_id_waiting_for_result` exists
2. Set frame_status from job result
3. Store detection data
4. Refresh table
5. Reset `frame_id_waiting_for_result`

**Returns**: bool (success/failure)

---

## ✅ Advantages

| Old Flow | New Flow |
|----------|----------|
| Job result → Save pending | TCP signal → Create frame |
| TCP signal → Merge result | Job result → Fill frame |
| Frame depends on job order | Frame created from TCP |
| Pending result can be lost | Frame always created |

**Benefits**:
- ✅ Frame created immediately on TCP signal
- ✅ Matches real hardware timing
- ✅ No pending result needed
- ✅ Cleaner state management
- ✅ TCP signal is primary trigger

---

## 🚨 Edge Cases

### Case 1: Job Completes Before TCP Signal
```
Job Done → attach_job_result_to_waiting_frame()
    └─ frame_id_waiting_for_result is None
    └─ Returns False (warning logged)
    └─ Result discarded
```
**Action**: Job result is lost until TCP signal creates frame

### Case 2: TCP Signal Before Job Completes
```
TCP start_rising → Frame created
    └─ frame_id_waiting_for_result = 1
    └─ Frame shows: status=PENDING
    
Job completes → attach_job_result_to_waiting_frame()
    └─ Found frame 1
    └─ Updates status to OK/NG
```
**Result**: ✅ Frame properly updated

### Case 3: Multiple TCP Signals
```
start_rising||1 → frame_id=1, waiting=1
start_rising||2 → frame_id=2, waiting=2 (overwrites!)
    
Job 1 result → attach to frame 2 (wrong!) ❌
```
**Issue**: Only tracks latest frame

**Solution**: Need queue of waiting frames for concurrent operations

---

## 📝 Logging

### When TCP Signal Arrives:
```
[ResultTabManager] TCP Sensor IN received: sensor_id_in=36247640
[ResultTabManager] Frame created and waiting for job result: frame_id=1, sensor_id_in=36247640
[ResultTabManager] Sensor IN added - frame_id=1, sensor_id_in=36247640
```

### When Job Result Arrives:
```
[CameraManager] Attached job result to frame: status=OK
[ResultTabManager] Attached job result to frame 1: status=OK
[ResultTabManager] Detection data stored
[ResultTabManager] Frame 1 updated with job result
```

### When No Frame Waiting:
```
[CameraManager] No waiting frame (TCP signal not received yet?)
[ResultTabManager] No frame waiting for result
```

---

## 🔧 Implementation Details

### File: `gui/result_tab_manager.py`

**Modified Methods**:
- `on_sensor_in_received()` - Always creates frame, no pending check
- Added `attach_job_result_to_waiting_frame()` - New method

**New Variable**:
- `frame_id_waiting_for_result` - Tracks frame awaiting job result

### File: `gui/camera_manager.py`

**Modified Method**:
- `_update_execution_label()` - Changed from `save_pending_job_result()` to `attach_job_result_to_waiting_frame()`

**Logic Change**:
- From: Job result → pending → TCP signal → frame
- To: TCP signal → frame → Job result → attach

---

## ⚠️ Future Improvements

For concurrent operations (multiple frames):
1. Use queue of waiting frames instead of single variable
2. Match job results by timestamp or sequence number
3. Handle out-of-order job completions
4. Track frame lifecycle more granularly

---

**Status**: ✅ Implemented  
**Date**: 2025-11-11  
**Version**: 1.0
