# Testing Guide: TCP First, Then Job Result

## 🧪 Test Cases

### Test 1: Normal Flow (TCP Before Job)

**Setup**:
- Application running
- Camera ready
- TCP connection open

**Steps**:
1. Manual trigger camera button
2. Wait 2 seconds
3. Pico sends: `start_rising||36247640`
4. Watch Result Tab
5. Wait for job to complete
6. Pico sends: `end_rising||36261996`

**Expected**:
```
[T=0ms]    Click trigger
[T=2s]     TCP start_rising received
           ✓ Frame appears in table
           - Frame ID: 1
           - Frame Status: PENDING (yellow)
           - Sensor IN: 36247640
           - Sensor OUT: (empty)
           - Completion Status: PENDING (yellow)

[T=2.5s]   Job completes (e.g., result = NG)
           ✓ Frame updated
           - Frame Status: NG (red)
           - Sensor IN: 36247640
           - Sensor OUT: (empty)
           - Completion Status: PENDING (yellow)

[T=2.8s]   TCP end_rising received
           ✓ Frame finalized
           - Frame Status: NG (red)
           - Sensor IN: 36247640
           - Sensor OUT: 36261996
           - Completion Status: DONE (cyan)
```

**Logs Expected**:
```
[ResultTabManager] TCP Sensor IN received: sensor_id_in=36247640
[ResultTabManager] Frame created and waiting for job result: frame_id=1
[ResultTabManager] Sensor IN added - frame_id=1
[CameraManager] Attached job result to frame: status=NG
[ResultTabManager] Attached job result to frame 1: status=NG
[FIFOResultQueue] Sensor OUT: frame_id=1, sensor_id_out=36261996, completion=DONE
```

---

### Test 2: Job Completes Before TCP

**Setup**:
- Same as Test 1

**Steps**:
1. Manual trigger camera button
2. Wait for job to complete (~0.3 seconds)
3. THEN Pico sends: `start_rising||36247640` (after job)
4. Watch Result Tab

**Expected**:
```
[T=0ms]    Click trigger
[T=300ms]  Job completes
           ❌ Result not attached (no frame yet)
           [CameraManager] No waiting frame warning

[T=3s]     TCP start_rising received
           ✓ Frame created with status=PENDING
           - Frame ID: 1
           - Frame Status: PENDING (yellow)  ⚠️ Job result was lost!
           - Sensor IN: 36247640
           - Completion Status: PENDING (yellow)
```

**Logs Expected**:
```
[CameraManager] No waiting frame (TCP signal not received yet?)
[ResultTabManager] TCP Sensor IN received: sensor_id_in=36247640
[ResultTabManager] Frame created and waiting for job result: frame_id=1
```

**Issue**: Job result lost because frame wasn't created yet
**Status**: ⚠️ Expected behavior (frame must exist first)

---

### Test 3: Frame Status Color Coding

**Setup**:
- Run Test 1

**Expected Visuals in Result Tab**:

| Step | Frame Status | Color | Completion Status | Color |
|------|--------------|-------|-------------------|-------|
| After TCP start_rising | PENDING | 🟡 Yellow | PENDING | 🟡 Yellow |
| After job (OK result) | OK | 🟢 Green | PENDING | 🟡 Yellow |
| After TCP end_rising | OK | 🟢 Green | DONE | 🔵 Cyan |

---

### Test 4: Multiple Frames in Sequence

**Setup**:
- Application running

**Steps**:
```
T=0ms:     Trigger 1
T=2s:      TCP start_rising||A → Frame 1 created
T=2.5s:    Job 1 completes → Frame 1 updated
T=2.8s:    TCP end_rising||A → Frame 1 finalized

T=3s:      Trigger 2
T=5s:      TCP start_rising||B → Frame 2 created
T=5.5s:    Job 2 completes → Frame 2 updated
T=5.8s:    TCP end_rising||B → Frame 2 finalized
```

**Expected**:
```
Result Tab shows:
├─ Row 1: Frame 1, OK, A, A, DONE (cyan)
└─ Row 2: Frame 2, NG, B, B, DONE (cyan)
```

**Logs Check**:
- Frame 1 and 2 tracked separately
- Job results attached to correct frames
- FIFO matching works correctly

---

### Test 5: Concurrent Job & TCP Operations

**Setup**:
- Two triggers in quick succession

**Steps**:
```
T=0ms:     Trigger 1
T=100ms:   Trigger 2
T=2s:      TCP start_rising||A
T=2.1s:    TCP start_rising||B
T=2.3s:    Job 1 completes
T=2.4s:    Job 2 completes
```

**Expected**:
```
Result Tab shows:
├─ Row 1: Frame 1, ?, A, (empty), PENDING
└─ Row 2: Frame 2, ?, B, (empty), PENDING

Then after jobs complete:
├─ Row 1: Frame 1, OK, A, (empty), PENDING
└─ Row 2: Frame 2, NG, B, (empty), PENDING
```

**⚠️ Issue**: 
- Job 1 result might go to Frame 2 (wrong!)
- Current implementation only tracks ONE waiting frame
- Need queue for multiple concurrent operations

---

## 🔍 Debug Checklist

### Startup Checks
- [ ] ResultTabManager initialized
- [ ] `frame_id_waiting_for_result = None` initially
- [ ] Table displays empty or previous data
- [ ] TCP connection established

### After TCP start_rising
- [ ] Log: "TCP Sensor IN received"
- [ ] Log: "Frame created and waiting for job result"
- [ ] Frame appears in table
- [ ] `frame_id_waiting_for_result = <frame_id>` set
- [ ] Frame status shows PENDING (yellow)

### After Job Completes
- [ ] Log: "Attached job result to frame"
- [ ] Frame status updated (OK or NG)
- [ ] `frame_id_waiting_for_result = None` reset
- [ ] Detection data stored

### After TCP end_rising
- [ ] Log: "Sensor OUT received"
- [ ] Frame completion status = DONE (cyan)
- [ ] Sensor OUT ID displayed

---

## 📝 Log Messages to Watch

### Success Scenario
```
✅ [ResultTabManager] TCP Sensor IN received: sensor_id_in=36247640
✅ [ResultTabManager] Frame created and waiting for job result: frame_id=1, sensor_id_in=36247640
✅ [CameraManager] Attached job result to frame: status=NG
✅ [ResultTabManager] Attached job result to frame 1: status=NG
✅ [FIFOResultQueue] Sensor OUT: frame_id=1, sensor_id_out=36261996, completion=DONE
```

### No Waiting Frame (Job First)
```
⚠️ [CameraManager] No waiting frame (TCP signal not received yet?)
⚠️ [ResultTabManager] No frame waiting for result
```

### Errors
```
❌ [ResultTabManager] Failed to create frame for sensor_id_in=36247640
❌ [ResultTabManager] Error attaching job result: <exception>
❌ [ResultTabManager] Error in on_sensor_in_received: <exception>
```

---

## 🎬 Manual Test Procedure

### Quick Test (5 minutes)

1. Start application
2. Open Result Tab
3. Click "Trigger Camera" button
4. Send from Pico (using TCP terminal):
   ```
   start_rising||12345678
   ```
5. Verify: Frame appears in table with PENDING status
6. Wait ~1-2 seconds for job to complete
7. Verify: Frame status changes to OK or NG
8. Send from Pico:
   ```
   end_rising||87654321
   ```
9. Verify: Completion status changes to DONE (cyan)

---

## 🐛 Known Issues

### Issue 1: Concurrent Operations
**Problem**: Only tracks one waiting frame
**Impact**: Multiple concurrent triggers will lose job results
**Workaround**: Test with one trigger at a time
**Future**: Implement queue of waiting frames

### Issue 2: Frame Status PENDING
**Problem**: If job never arrives, frame stays PENDING
**Impact**: Misleading status display
**Workaround**: Not applicable (TCP signal required)
**Future**: Add timeout handling

---

## ✅ Success Criteria

- [ ] Frame created immediately when TCP signal arrives
- [ ] Frame status updated when job completes
- [ ] Color coding shows correct status
- [ ] Multiple frames handled sequentially
- [ ] Logs show correct sequence
- [ ] No errors in console
- [ ] Detection data stored correctly
- [ ] FIFO queue matching works

---

**Created**: 2025-11-11  
**Last Updated**: 2025-11-11  
**Status**: Ready for Testing
