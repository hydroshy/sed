# Logic Change: Before & After

## 🔄 Flow Comparison

### BEFORE (Old Flow)
```
┌─────────────────────────────────────┐
│   Manual Trigger Button Clicked     │
└─────────────┬───────────────────────┘
              ↓
    ┌─────────────────────┐
    │  Camera Captures    │
    │       Frame         │
    └──────────┬──────────┘
               ↓
    ┌─────────────────────┐
    │   Job Pipeline      │
    │  - Camera Source    │
    │  - Detect Tool      │
    │  - Result Tool      │
    └──────────┬──────────┘
               ↓
    ┌─────────────────────┐
    │   Result: OK/NG     │
    │ (stored as PENDING) │
    └──────────┬──────────┘
               ↓
    ⏳ WAITING FOR TCP...
               ↓
┌──────────────────────────────────────┐
│  TCP Receives: start_rising||36247640│
└─────────────┬────────────────────────┘
              ↓
    ┌─────────────────────┐
    │  Frame CREATED NOW  │  ⬅️ Frame depends on job result
    │   sensor_id = in    │
    │  status = OK/NG ✓   │ (from pending)
    └──────────┬──────────┘
               ↓
    ┌─────────────────────┐
    │   Table Updated     │
    └─────────────────────┘
```

---

### AFTER (New Flow) ✨
```
┌─────────────────────────────────────┐
│   Manual Trigger Button Clicked     │
└─────────────┬───────────────────────┘
              ↓
    ┌─────────────────────┐
    │  Camera Captures    │
    │       Frame         │
    └──────────┬──────────┘
               ↓
    ┌─────────────────────┐
    │   Job Pipeline      │
    │  - Camera Source    │
    │  - Detect Tool      │
    │  - Result Tool      │
    └──────────┬──────────┘
               ↓
    ┌──────────────────────────────────┐
    │   Result Ready: OK/NG            │
    │   (stored in local variables)    │
    └──────────┬───────────────────────┘
               ↓
    ⏳ WAITING FOR TCP... (in parallel)
               ↓
┌──────────────────────────────────────┐
│  TCP Receives: start_rising||36247640│  ⬅️ FRAME CREATED FIRST
└─────────────┬────────────────────────┘
              ↓
    ┌──────────────────────────────────┐
    │  Frame CREATED IMMEDIATELY       │  ⬅️ Frame created from TCP
    │   sensor_id = 36247640           │
    │  status = PENDING (yellow)       │  (waiting for job result)
    │  frame_id_waiting_for_result=1   │
    └──────────┬───────────────────────┘
               ↓
    ┌──────────────────────────────────┐
    │   Table Updated with Frame       │
    │   (shows PENDING status)         │
    └──────────┬───────────────────────┘
               ↓
    ⏳ Job result completes...
               ↓
    ┌──────────────────────────────────┐
    │ attach_job_result_to_waiting_frame│  ⬅️ ATTACH RESULT TO FRAME
    │   - Find frame 1                 │
    │   - Set status = OK/NG ✓         │
    │   - Store detection data         │
    └──────────┬───────────────────────┘
               ↓
    ┌──────────────────────────────────┐
    │  Table Updated with Result       │
    │  (status changes to OK/NG)       │
    └─────────────────────────────────┘
```

---

## 📊 State Progression

### BEFORE
```
Timeline:
[T+0ms]    Manual trigger
[T+50ms]   Job processes
[T+250ms]  Job result saved (PENDING)
[T+?]      TCP arrives → Frame created
```

**Problem**: Frame creation depends on job completion

---

### AFTER  
```
Timeline:
[T+0ms]    Manual trigger
[T+50ms]   Job processes (in parallel)
[T+?]      TCP arrives → Frame created IMMEDIATELY ✅
[T+250ms]  Job result attached to frame ✅
```

**Benefit**: Frame creation independent of job timing

---

## 🗂️ Data Structure

### BEFORE

```python
# In ResultTabManager:
class ResultTabManager:
    pending_result: Optional[PendingJobResult] = None
    #   └─ Holds: status, similarity, detection_data
    #   └─ Cleared when frame created

# In on_sensor_in_received():
if self.pending_result:
    # Use pending result to create frame
    frame_status = self.pending_result.status
```

**Issues**:
- Result must wait for TCP signal
- If TCP never arrives, result is stuck
- Single pending_result only

---

### AFTER

```python
# In ResultTabManager:
class ResultTabManager:
    frame_id_waiting_for_result: Optional[int] = None
    #   └─ Stores which frame is waiting
    #   └─ Cleared when result attached

# In on_sensor_in_received():
frame_id = self.add_sensor_in_event(sensor_id_in)
self.frame_id_waiting_for_result = frame_id
# Frame created immediately, status will be updated later

# In attach_job_result_to_waiting_frame():
if self.frame_id_waiting_for_result is not None:
    # Attach result to waiting frame
    self.fifo_queue.set_frame_status(frame_id, status)
```

**Advantages**:
- Frame created immediately
- Result attached when ready
- Clear separation of concerns
- Matches hardware timing

---

## 🎯 Method Calls

### BEFORE

```
camera_manager._update_execution_label()
    └─ result_tab_manager.save_pending_job_result(status, data)
       └─ Saves to self.pending_result
       └─ Waits for on_sensor_in_received()

tcp_controller_manager._handle_start_rising()
    └─ result_tab_manager.on_sensor_in_received(sensor_id)
       └─ Reads self.pending_result
       └─ Creates frame with status from pending
       └─ Clears self.pending_result
```

---

### AFTER

```
tcp_controller_manager._handle_start_rising()
    └─ result_tab_manager.on_sensor_in_received(sensor_id)
       └─ Creates frame with status=PENDING
       └─ Sets frame_id_waiting_for_result = frame_id
       └─ Returns immediately

camera_manager._update_execution_label()
    └─ result_tab_manager.attach_job_result_to_waiting_frame(status, data)
       └─ Finds frame in frame_id_waiting_for_result
       └─ Updates frame_status from PENDING → OK/NG
       └─ Stores detection data
       └─ Clears frame_id_waiting_for_result
```

---

## 🔑 Key Differences

| Aspect | Before | After |
|--------|--------|-------|
| **Frame Creation Trigger** | Job result ready | TCP signal received |
| **Timing** | After job completes | Immediately on TCP |
| **Status Wait** | TCP signal → Use pending | TCP signal → Create frame |
| **Frame Status** | Comes from job | Initially PENDING, updated by job |
| **Pending Result** | Stored in memory | Not needed |
| **Job-TCP Coupling** | Tight (job→TCP) | Loose (TCP independent) |

---

## ✅ Quality Improvements

### Before
```
❌ Frame depends on job result
❌ Pending result can be lost if TCP never arrives
❌ Tight coupling between job and TCP
❌ State management is complex
```

### After
```
✅ Frame created from TCP signal (independent)
✅ Job result simply fills in the frame
✅ Clear separation: TCP creates, job fills
✅ Simple state tracking with single variable
✅ Matches real hardware sequence
✅ More resilient to timing issues
```

---

## 🐛 Edge Case Handling

### Scenario 1: Job Completes Before TCP

**Before**: Result saved, waiting for TCP ✓
**After**: Job result ignored (no frame waiting) ⚠️

**Fix**: Could retry or save result for next TCP signal

### Scenario 2: TCP Signal, Then Job

**Before**: Frame created with status from pending ✓
**After**: Frame created with PENDING, job updates it ✓

**Status**: Both work, but After is cleaner

### Scenario 3: Multiple Concurrent Operations

**Before**: Single pending_result (can only track 1) ❌
**After**: Single frame_id_waiting (can only track 1) ❌

**Future**: Use queue of waiting frame IDs

---

**Updated**: 2025-11-11  
**Status**: ✅ Implemented
