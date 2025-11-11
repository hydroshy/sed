# Result Tab: TCP Sensor Integration Guide

## Architecture

The Result Tab now integrates with TCP sensor signals for proper frame management:

```
TCP Pico Sends Signals
  │
  ├─ start_sensor:5  (Sensor IN event)
  │  ↓
  │  TCPControllerManager._on_sensor_in_event()
  │  ├─ Create new frame with sensor_id_in=5
  │  ├─ Apply any cached job result (status/detection data)
  │  └─ Display in Result Tab
  │
  ├─ Job runs independently
  │  ├─ Camera captures frame
  │  ├─ Detection/Classification runs
  │  └─ Result cached (waiting for sensor IN)
  │
  └─ end_sensor:10  (Sensor OUT event)
     ↓
     TCPControllerManager._on_sensor_out_event()
     ├─ Match to pending frame
     ├─ Set sensor_id_out=10
     └─ Update table


Result Tab Table Display:
┌──────────┬───────────┬───────────┬────────┐
│ Frame ID │ Sensor IN │ Sensor OUT│ Status │
├──────────┼───────────┼───────────┼────────┤
│    1     │     5     │    10     │  OK 🟢 │
└──────────┴───────────┴───────────┴────────┘
```

---

## Data Flow

### 1. Job Completes (No TCP Signal Yet)
```
Camera captures frame
  ↓
Job Pipeline (Camera Tool → Detect → Result Tool)
  ↓
Result available (OK/NG status + detection data)
  ↓
CameraManager caches result in main_window._pending_job_result
  ↓
Waiting for TCP start_sensor signal...
```

**Result Tab**: EMPTY (no sensor IN received yet)

### 2. TCP start_sensor Signal Arrives
```
TCP receives: "start_sensor:5"
  ↓
TCPControllerManager._on_message_received()
  ↓
Detects "start_sensor" pattern
  ↓
Parses sensor_id = 5
  ↓
_on_sensor_in_event(5)
  ├─ Creates frame: frame_id=1, sensor_id_in=5, status=PENDING
  ├─ Checks cached result
  ├─ If cached: applies status + detection data
  └─ Clears cache
  ↓
ResultTabManager.add_sensor_in_event(5)
  ↓
Result Tab Table Updated: Frame 1 appears with Sensor IN=5
```

**Result Tab**: NEW ROW
```
┌──────────┬───────────┬───────────┬────────┐
│ Frame ID │ Sensor IN │ Sensor OUT│ Status │
├──────────┼───────────┼───────────┼────────┤
│    1     │     5     │     -     │  OK 🟢 │ ← CREATED
└──────────┴───────────┴───────────┴────────┘
```

### 3. TCP end_sensor Signal Arrives
```
TCP receives: "end_sensor:10"
  ↓
TCPControllerManager._on_message_received()
  ↓
Detects "end_sensor" pattern
  ↓
Parses sensor_id = 10
  ↓
_on_sensor_out_event(10)
  ├─ Matches to most recent pending frame (frame_id=1)
  ├─ Sets sensor_id_out=10
  └─ Signals matched
  ↓
ResultTabManager.add_sensor_out_event(10)
  ↓
Result Tab Table Updated: Sensor OUT set to 10
```

**Result Tab**: ROW UPDATED
```
┌──────────┬───────────┬───────────┬────────┐
│ Frame ID │ Sensor IN │ Sensor OUT│ Status │
├──────────┼───────────┼───────────┼────────┤
│    1     │     5     │    10     │  OK 🟢 │ ← UPDATED
└──────────┴───────────┴───────────┴────────┘
```

---

## TCP Message Formats

### Expected Message Formats

**Sensor IN (start_sensor)**
```
Format: "start_sensor:{sensor_id}"
Examples:
- "start_sensor:5"
- "start_sensor:1"
- "start_sensor:255"

Also accepts:
- "start_sensor 5"
- "start_sensor(5)"
- "start:5"
```

**Sensor OUT (end_sensor)**
```
Format: "end_sensor:{sensor_id}"
Examples:
- "end_sensor:10"
- "end_sensor:1"
- "end_sensor:255"

Also accepts:
- "end_sensor 10"
- "end_sensor(10)"
- "end:10"
```

### Parsing Logic
```python
# Any message with "start_sensor" or "start" and a number:
"start_sensor:5"    → sensor_id = 5 ✓
"start_sensor 5"    → sensor_id = 5 ✓
"start_sensor(5)"   → sensor_id = 5 ✓
"START_SENSOR:5"    → sensor_id = 5 ✓ (case-insensitive)

# Same for end_sensor/end
"end_sensor:10"     → sensor_id = 10 ✓
"end_sensor 10"     → sensor_id = 10 ✓
"end 10"            → sensor_id = 10 ✓
```

---

## Implementation Details

### Code Location: `gui/tcp_controller_manager.py`

#### New Methods Added:

1. **`_handle_result_tab_sensor_events(message)`** (Lines ~296+)
   - Detects sensor IN/OUT patterns in message
   - Calls appropriate handler
   - Error handling & logging

2. **`_parse_sensor_id(message)`** (Lines ~314+)
   - Extracts number from message using regex
   - Returns sensor_id or None
   - Supports various formats

3. **`_on_sensor_in_event(sensor_id)`** (Lines ~324+)
   - Creates new frame in FIFO queue
   - Applies cached job result if available
   - Clears cache after application
   - Comprehensive logging

4. **`_on_sensor_out_event(sensor_id)`** (Lines ~361+)
   - Matches to pending frame
   - Logs success/failure
   - Updates table

### Code Location: `gui/camera_manager.py`

#### Modified: `_update_execution_label()` (Lines ~2807+)
- Now **caches** result instead of creating frame immediately
- Stores in `main_window._pending_job_result`
- Waits for TCP sensor IN signal

**Cache Structure:**
```python
main_window._pending_job_result = {
    'status': 'OK',              # or 'NG' or 'PENDING'
    'reason': 'reason text',
    'timestamp': 1735018523.45,
    'detection_data': {
        'detections': [...],
        'detection_count': 2,
        'inference_time': 0.210,
    }
}
```

---

## Example Scenarios

### Scenario 1: Normal Flow

```
TIME 1:  TCP: "start_sensor:5"
         → Frame created: ID=1, SensorIN=5
         → Result Tab shows: Frame 1 | Sensor 5 | - | PENDING

TIME 2:  Camera: Triggers job
         → Detection runs: Found 1 object (confidence 0.92)
         → Result: OK
         → Cached (waiting for sensor IN)

TIME 3:  TCP: "end_sensor:10"
         → Matches to Frame 1
         → Sets SensorOUT=10
         → Result Tab shows: Frame 1 | Sensor 5 | 10 | OK (green)
```

**Result Tab After Flow:**
```
┌──────────┬───────────┬───────────┬────────┐
│ Frame ID │ Sensor IN │ Sensor OUT│ Status │
├──────────┼───────────┼───────────┼────────┤
│    1     │     5     │    10     │  OK 🟢 │
└──────────┴───────────┴───────────┴────────┘
```

### Scenario 2: Multiple Frames

```
TIME 1:  TCP: "start_sensor:5"
         → Frame 1 created

TIME 2:  TCP: "start_sensor:6"
         → Frame 2 created

TIME 3:  TCP: "end_sensor:10"
         → Matches to Frame 2 (most recent pending)

TIME 4:  TCP: "end_sensor:9"
         → Matches to Frame 1

Result Tab:
┌──────────┬───────────┬───────────┬────────┐
│ Frame ID │ Sensor IN │ Sensor OUT│ Status │
├──────────┼───────────┼───────────┼────────┤
│    1     │     5     │     9     │  OK 🟢 │
│    2     │     6     │    10     │  NG 🔴 │
└──────────┴───────────┴───────────┴────────┘
```

### Scenario 3: Sensor OUT Without Pending Frame

```
TIME 1:  No sensor IN received yet
         → Result Tab: EMPTY

TIME 2:  TCP: "end_sensor:10"
         → No pending frame to match
         → Logged as warning
         → Result Tab: Still EMPTY
         → Sensor OUT signal ignored

TIME 3:  TCP: "start_sensor:5"
         → Frame 1 created with only SensorIN=5
         → SensorOUT remains "-"
```

**Result Tab After Flow:**
```
┌──────────┬───────────┬───────────┬────────┐
│ Frame ID │ Sensor IN │ Sensor OUT│ Status │
├──────────┼───────────┼───────────┼────────┤
│    1     │     5     │     -     │ PENDING🟡│
└──────────┴───────────┴───────────┴────────┘
```

---

## Logging & Debugging

### Console Debug Output

```
DEBUG: [TCP] Sensor IN #5 → Frame ID #1
DEBUG: [TCP] Applied cached result - status=OK
DEBUG: [TCP] Sensor OUT #10 → Matched ✓
```

### Log File Output

```
[TCPControllerManager] Sensor IN event - sensor_id=5, frame_id=1
[TCPControllerManager] Applied cached result to frame_id=1, status=OK
[TCPControllerManager] Sensor OUT event - sensor_id=10, matched successfully
```

### Troubleshooting Commands

```bash
# Show all Result Tab operations:
grep "Result Tab\|sensor_id\|Sensor" logs.txt

# Show TCP sensor events specifically:
grep "Sensor IN\|Sensor OUT" logs.txt

# Show cached result operations:
grep "cached result" logs.txt

# Show Result Tab warnings:
grep "No pending frame\|Result Tab Manager not" logs.txt
```

---

## Tested Message Formats

The parser supports these formats:

✅ `"start_sensor:5"`  
✅ `"start_sensor 5"`  
✅ `"start_sensor(5)"`  
✅ `"start 5"`  
✅ `"START_SENSOR:5"` (case-insensitive)  
✅ `"end_sensor:10"`  
✅ `"end_sensor 10"`  
✅ `"end 10"`  

---

## API Reference

### Method: `_on_sensor_in_event(sensor_id: int)`

**Purpose**: Create new frame when TCP start_sensor signal arrives

**Parameters**:
- `sensor_id` (int): Sensor ID from TCP message

**Process**:
1. Creates new frame with `sensor_id_in=sensor_id`
2. Checks for cached job result
3. If cached: applies status + detection data
4. Clears cache

**Example**:
```python
# When TCP "start_sensor:5" received:
tcp_manager._on_sensor_in_event(5)
# → Frame created with sensor_id_in=5
# → Cached result applied if available
```

### Method: `_on_sensor_out_event(sensor_id: int)`

**Purpose**: Match frame when TCP end_sensor signal arrives

**Parameters**:
- `sensor_id` (int): Sensor ID from TCP message

**Process**:
1. Finds most recent pending frame
2. Sets `sensor_id_out=sensor_id`
3. Logs success or warning

**Example**:
```python
# When TCP "end_sensor:10" received:
tcp_manager._on_sensor_out_event(10)
# → Matches to pending frame
# → Sets sensor_id_out=10
```

### Method: `_parse_sensor_id(message: str) -> int`

**Purpose**: Extract sensor ID from message

**Parameters**:
- `message` (str): TCP message string

**Returns**:
- `int`: Sensor ID (or None if parsing failed)
- Looks for first number in message

**Example**:
```python
tcp_manager._parse_sensor_id("start_sensor:5")  # → 5
tcp_manager._parse_sensor_id("end 10")          # → 10
tcp_manager._parse_sensor_id("no number")       # → None
```

---

## Configuration

### TCP Message Reception

Messages are received in `_on_message_received()` which now calls:
1. `_handle_result_tab_sensor_events()` - Check for sensor signals
2. `_check_and_trigger_camera_if_needed()` - Trigger camera if needed

### Sensor ID Range

- Supports: 0-255 (any positive integer)
- No validation limit (can extend as needed)
- Negative numbers: Not supported by regex parser

### Frame Matching

- **FIFO matching**: Matches to most recent pending frame
- If no pending frame: Logs warning, signal ignored
- Frame remains "PENDING" until sensor OUT arrives

---

## Future Enhancements

1. **Configurable Message Formats**:
   ```python
   SENSOR_IN_PATTERN = r"start_sensor[:\s\(]?(\d+)"
   SENSOR_OUT_PATTERN = r"end_sensor[:\s\(]?(\d+)"
   ```

2. **Sensor ID Validation**:
   ```python
   def _validate_sensor_id(self, sensor_id):
       if sensor_id < 0 or sensor_id > 255:
           raise ValueError(f"Invalid sensor ID: {sensor_id}")
   ```

3. **Queue Timeout**:
   ```python
   # Mark frames as TIMEOUT if sensor OUT doesn't arrive within time_limit
   if frame.age() > TIME_LIMIT and not frame.sensor_out:
       frame.status = 'TIMEOUT'
   ```

4. **Sensor Matching History**:
   ```python
   # Track which sensor IN matched with which sensor OUT
   frame.match_history = {
       'sensor_in': 5,
       'sensor_out': 10,
       'match_time': time.time()
   }
   ```

---

## Summary

The Result Tab now properly integrates with TCP sensor signals:

✅ **Sensor IN** creates frame with sensor_id_in  
✅ **Job Result** cached waiting for sensor IN  
✅ **Sensor OUT** matches frame and sets sensor_id_out  
✅ **Table** updates automatically at each step  
✅ **Logging** comprehensive for debugging  

**Status**: 🟢 **READY FOR PRODUCTION**

---

**Last Updated**: 2025-11-05  
**TCP Integration**: COMPLETE ✅
