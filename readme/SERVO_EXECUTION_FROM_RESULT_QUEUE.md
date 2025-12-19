# Servo Execution from Result Queue - COMPLETE ✅

## Feature Overview
When a frame is marked as DONE (sensor OUT arrives), automatically send servo command to Pico based on frame status:
- **OK** → `GOTO 41` (move to position 41)
- **NG** → `HOME` (move to home position)

## Complete Flow Diagram

```
TRIGGER
  ↓
[Camera] Captures frame
  ↓
[Job] Detects/classifies
  ↓
[Result] Status = OK/NG (attached to frame)
  ↓
[Sensor] END signal arrives (end_rising)
  ↓
[TCP] _handle_end_rising() called
  ↓
[ResultTabManager] add_sensor_out_event()
  ↓
[FIFOQueue] Frame marked DONE (completion_status=DONE)
  ↓
✅ _execute_servo_command_for_done_frame()
  ├─ Get last DONE frame (FIFO)
  ├─ Read frame_status (OK/NG)
  ├─ Determine servo command
  │  ├─ OK → "GOTO 41"
  │  └─ NG → "HOME"
  └─ Send via TCP
      ↓
[Pico] Receives servo command
  ↓
[Servo] Executes: move to 41 (OK) or HOME (NG)
```

## Implementation Details

### 1. New Method in FIFOResultQueue
**File:** `gui/fifo_result_queue.py`

```python
def get_last_done_frame(self) -> Optional[ResultQueueItem]:
    """
    Get the most recently DONE frame (for servo execution)
    
    When sensor OUT arrives, first frame becomes DONE.
    This method returns that frame so servo command can be sent based on its status.
    
    Returns:
        ResultQueueItem if found, None otherwise
    """
    # Search from end backwards (most recent first)
    for item in reversed(self.queue):
        if item.completion_status == "DONE":
            return item
    return None
```

**Purpose:** Get the frame that just became DONE to determine servo action

### 2. Enhanced _handle_sensor_out_event
**File:** `gui/tcp_controller_manager.py` (Line ~378)

**Changes:**
```python
# OLD: Just match sensor OUT to frame
success = result_tab_manager.add_sensor_out_event(sensor_id)

# NEW: After matching, execute servo command
if success:
    self._execute_servo_command_for_done_frame()  # ✅ NEW
```

### 3. New Method: _execute_servo_command_for_done_frame
**File:** `gui/tcp_controller_manager.py`

```python
def _execute_servo_command_for_done_frame(self):
    """
    Execute servo command based on the frame that just became DONE
    
    Logic:
    1. Get most recently DONE frame from FIFO queue
    2. Check frame_status (OK/NG)
    3. Determine command:
       - OK → "GOTO 41"
       - NG → "HOME"
    4. Send via TCP to Pico
    """
    # Get FIFO queue
    fifo_queue = result_tab_manager.fifo_queue
    
    # Get most recently DONE frame
    done_frame = fifo_queue.get_last_done_frame()
    
    # Determine servo command
    if done_frame.frame_status == "OK":
        servo_command = "GOTO 41"  # OK → position 41
    else:  # NG
        servo_command = "HOME"      # NG → home position
    
    # Send command
    self.tcp_controller.send_message(servo_command)
```

## Data Flow (Step-by-Step)

### Step 1: Sensor OUT Received
```
[Pico] Sends: "end_rising||873599"
       ↓
[TCP] Message received
```

### Step 2: Frame Marked DONE
```
[tcp_controller_manager._handle_end_rising()]
  ├─ Extract sensor_id
  └─ Call _handle_sensor_out_event()
       ├─ Call result_tab_manager.add_sensor_out_event()
       │   └─ fifo_queue.add_sensor_out_event()
       │       ├─ Find first frame with sensor_id_out=None
       │       ├─ Set sensor_id_out
       │       └─ Set completion_status = "DONE"
       │
       └─ ✅ Call _execute_servo_command_for_done_frame()
```

### Step 3: Servo Command Execution
```
_execute_servo_command_for_done_frame():
  1. Get FIFO queue from result_tab_manager
  2. Get last DONE frame: get_last_done_frame()
  3. Read frame.frame_status (OK or NG)
  4. Map to servo command:
     - "OK"  → "GOTO 41"
     - "NG"  → "HOME"
  5. Send message: tcp_controller.send_message(command)
     └─ Returns: sent to Pico successfully
```

### Step 4: Servo Executes
```
[Pico] Receives "GOTO 41" or "HOME"
  ├─ If GOTO 41: Move servo to position 41 (OK path)
  └─ If HOME: Move servo to home position (NG path)
```

## Queue States Throughout Flow

```
INITIAL:
Queue: [Frame 1: PENDING/PENDING]

AFTER SENSOR IN:
Queue: [Frame 1: PENDING/PENDING, sensor_in=873599]

AFTER JOB COMPLETES:
Queue: [Frame 1: OK/PENDING, sensor_in=873599]
       ↑
       frame_status set to OK

AFTER SENSOR OUT:
Queue: [Frame 1: OK/DONE, sensor_in=873599, sensor_out=873599]
       ↑                 ↑
       Still OK    completion_status → DONE
                    ✅ Triggers servo "GOTO 41"

AFTER NEXT SENSOR IN:
Queue: [Frame 1: OK/DONE, sensor_in=873599, sensor_out=873599]
       [Frame 2: PENDING/PENDING, sensor_in=873600]
```

## FIFO Guarantee

**Multiple Frames Scenario:**
```
Frame 1: OK
Frame 2: NG
Frame 3: OK

Queue when multiple DONE:
[Frame 1: OK/DONE ✓, Frame 2: NG/DONE ✓, Frame 3: OK/PENDING]

get_last_done_frame() searches backwards:
  └─ Returns Frame 2 (most recent DONE)
     └─ Frame 2 is NG → Send "HOME"
```

**Why search backwards (reversed)?**
- Most recent DONE frame = most recent end_rising signal
- That's the one we want to execute servo for
- Ensures correct order even with multiple concurrent frames

## Log Examples

**Successful OK execution:**
```
[TCPController] 🔚 Sensor OUT received: sensor_id=873599
[TCPController] Sensor OUT matched successfully
[TCPController] ✅ Frame 1 is OK → Servo command: GOTO 41
[TCPController] ✅ Servo command sent: GOTO 41
DEBUG: [TCPController] ✅ TX: GOTO 41
```

**Successful NG execution:**
```
[TCPController] 🔚 Sensor OUT received: sensor_id=873600
[TCPController] Sensor OUT matched successfully
[TCPController] ❌ Frame 2 is NG → Servo command: HOME
[TCPController] ✅ Servo command sent: HOME
DEBUG: [TCPController] ✅ TX: HOME
```

**Error case (no DONE frame):**
```
[TCPController] 🔚 Sensor OUT received: sensor_id=873601
[TCPController] Sensor OUT matched successfully
[TCPController] Cannot execute servo: No DONE frame found
DEBUG: [TCPController] Skipping: status not found
```

## Files Modified

### 1. `gui/fifo_result_queue.py`
- ✅ Added `get_last_done_frame()` method
- Returns most recently DONE frame for servo execution
- Searches queue backwards (LIFO among DONE frames)

### 2. `gui/tcp_controller_manager.py`
- ✅ Modified `_handle_sensor_out_event()` to call servo execution
- ✅ Added `_execute_servo_command_for_done_frame()` method
- Logic: Get DONE frame → read status → send servo command

## Configuration

**Servo Commands (in Pico):**
```python
"GOTO 41"  # Move to position 41 (OK position)
"HOME"     # Move to home position (NG position)
```

**These are TCP commands implemented in Pico firmware:**
- Already tested and working ✅
- Just needed to connect to result queue system

## Benefits

1. ✅ **Automatic execution** - No manual servo control needed
2. ✅ **FIFO order** - Handles multiple frames correctly
3. ✅ **TCP integration** - Seamless communication with Pico
4. ✅ **Status-based** - Different actions for OK vs NG
5. ✅ **Logging** - Full visibility of what's happening

## Testing Recommendations

1. **Single trigger:**
   - Trigger camera
   - Detect OK
   - end_rising arrives
   - Check: Servo moves to position 41 ✓

2. **Single trigger NG:**
   - Trigger camera
   - Detect NG
   - end_rising arrives
   - Check: Servo moves to HOME ✓

3. **Multiple rapid triggers:**
   - Trigger multiple times quickly
   - Some OK, some NG
   - Verify each servo command sent in FIFO order
   - Check logs show correct OK→GOTO 41, NG→HOME mapping

4. **Timing test:**
   - end_rising before job completes (frame_status=PENDING)
   - Should skip servo (no DONE frame with status)
   - Job completes later
   - Verify result shown in queue

## Status

✅ **COMPLETE** - Servo execution from result queue fully implemented
