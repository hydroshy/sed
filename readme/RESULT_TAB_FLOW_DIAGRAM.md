# Result Tab TCP Integration - Visual Flow Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PICO (TCP Client)                        │
│                                                                   │
│  Sends TCP Messages:                                             │
│  - "start_sensor:5"    (when starting inspection)                │
│  - "end_sensor:10"     (when done with inspection)               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ TCP Network
                             │
┌────────────────────────────┴────────────────────────────────────┐
│              CAMERA MANAGER (SED Application)                    │
│                                                                   │
│  1. Captures frame continuously                                  │
│  2. Runs detection/classification job                            │
│  3. Gets result (OK/NG)                                          │
│  4. CACHES result (waits for sensor IN signal)                   │
│                                                                   │
│  Cache Structure:                                                │
│  ┌──────────────────────────────────────────┐                   │
│  │ _pending_job_result {                    │                   │
│  │   'status': 'OK',                        │                   │
│  │   'detection_data': {...},               │                   │
│  │   'timestamp': 123456.789                │                   │
│  │ }                                        │                   │
│  └──────────────────────────────────────────┘                   │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         │ Job Result Cached
                         │
┌────────────────────────┴───────────────────────────────────────┐
│            TCP CONTROLLER MANAGER                                │
│                                                                   │
│  Receives TCP Message:                                           │
│  ┌──────────────────────────────────────────┐                   │
│  │ _on_message_received(message)            │                   │
│  │ ├─ Display message in UI                 │                   │
│  │ ├─ Parse sensor ID                       │                   │
│  │ └─ Route to sensor handler               │                   │
│  └──────────────────────────────────────────┘                   │
│                                                                   │
│  Pattern Detection:                                              │
│  - "start_sensor" / "start" → Sensor IN                          │
│  - "end_sensor" / "end"     → Sensor OUT                         │
│                                                                   │
│  ┌─────────────────────────────────────────┐  ┌─────────────┐  │
│  │ _on_sensor_in_event(sensor_id)          │  │ Sensor IN   │  │
│  │ 1. Create frame                         │  │ Signal      │  │
│  │ 2. Add to FIFO queue                    │  │ Handler     │  │
│  │ 3. Check cached result                  │  │             │  │
│  │ 4. If cached: apply it                  │  │             │  │
│  │ 5. Clear cache                          │  │ Returns:    │  │
│  │                                         │  │ Frame ID    │  │
│  │ Returns: frame_id                       │  │ (assigned)  │  │
│  └─────────────────────────────────────────┘  └─────────────┘  │
│                                                                   │
│  ┌─────────────────────────────────────────┐  ┌─────────────┐  │
│  │ _on_sensor_out_event(sensor_id)         │  │ Sensor OUT  │  │
│  │ 1. Find pending frame (FIFO)            │  │ Signal      │  │
│  │ 2. Set sensor_out value                 │  │ Handler     │  │
│  │ 3. Update frame status                  │  │             │  │
│  │ 4. Refresh table                        │  │ Returns:    │  │
│  │                                         │  │ success     │  │
│  │ Returns: success (bool)                 │  │ (boolean)   │  │
│  └─────────────────────────────────────────┘  └─────────────┘  │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         │ Create/Update Frame
                         │
┌────────────────────────┴───────────────────────────────────────┐
│            RESULT TAB MANAGER (FIFO Queue)                       │
│                                                                   │
│  FIFO Queue Operations:                                          │
│  ┌──────────────────────────────────────────┐                   │
│  │ add_sensor_in_event(sensor_id)           │                   │
│  │ └─ Create: frame_id, sensor_id_in        │                   │
│  │ └─ Returns: new frame_id                 │                   │
│  └──────────────────────────────────────────┘                   │
│                                                                   │
│  ┌──────────────────────────────────────────┐                   │
│  │ add_sensor_out_event(sensor_id)          │                   │
│  │ └─ Update: Most recent pending frame     │                   │
│  │ └─ Set: sensor_id_out                    │                   │
│  │ └─ Returns: success                      │                   │
│  └──────────────────────────────────────────┘                   │
│                                                                   │
│  ┌──────────────────────────────────────────┐                   │
│  │ set_frame_status(frame_id, status)       │                   │
│  │ └─ Update frame status (OK/NG/PENDING)   │                   │
│  └──────────────────────────────────────────┘                   │
│                                                                   │
│  ┌──────────────────────────────────────────┐                   │
│  │ set_frame_detection_data(frame_id, data) │                   │
│  │ └─ Store detection/classification data   │                   │
│  └──────────────────────────────────────────┘                   │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         │ Refresh
                         │
┌────────────────────────┴───────────────────────────────────────┐
│            QTABLEWIDGET (UI Display)                             │
│                                                                   │
│  ┌────────────┬───────────┬───────────┬────────┐               │
│  │ Frame ID   │ Sensor IN │ Sensor OUT│ Status │               │
│  ├────────────┼───────────┼───────────┼────────┤               │
│  │     1      │     5     │    10     │  OK 🟢 │               │
│  │     2      │     6     │     -     │ PEND 🟡│               │
│  │     3      │     7     │    11     │  NG 🔴 │               │
│  └────────────┴───────────┴───────────┴────────┘               │
│                                                                   │
│  User can:                                                       │
│  - Click Delete button to remove row                            │
│  - Click Clear button to clear all rows                         │
│  - Export/filter/search (future enhancements)                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow - Step by Step

### Step 1: Sensor IN Signal

```
PICO sends: "start_sensor:5"
        │
        ↓
TCPController receives message
        │
        ↓
_on_message_received("start_sensor:5")
        │
        ├─ Display in UI message list: "RX: start_sensor:5"
        │
        └─ Call: _handle_result_tab_sensor_events("start_sensor:5")
                 │
                 ├─ Detect "start_sensor" keyword
                 │
                 ├─ Parse sensor ID: _parse_sensor_id() → 5
                 │
                 └─ Call: _on_sensor_in_event(5)
                          │
                          ├─ Get result_tab_manager
                          │
                          ├─ Call: add_sensor_in_event(sensor_id_in=5)
                          │        │
                          │        ├─ Create ResultQueueItem
                          │        ├─ Assign frame_id = 1
                          │        ├─ Set sensor_id_in = 5
                          │        ├─ Set status = PENDING
                          │        └─ Return frame_id = 1
                          │
                          ├─ Check: _pending_job_result
                          │         └─ If exists:
                          │            ├─ Apply status
                          │            ├─ Apply detection_data
                          │            └─ Clear cache
                          │
                          └─ Refresh table
                             │
                             └─ Result Tab displays new row:
                                Frame 1 | Sensor 5 | - | OK
```

### Step 2: Job Processing (Parallel)

```
Job runs independently:
  Camera captures frame
        │
        ↓
  Detection/Classification
        │
        ↓
  Result available (OK/NG)
        │
        ↓
  CameraManager._update_execution_label()
        │
        ├─ Update ResultManager history
        │
        └─ Cache result:
           main_window._pending_job_result = {
               'status': 'OK',
               'detection_data': {...}
           }
           
  Waiting for sensor IN signal...
```

### Step 3: Sensor OUT Signal

```
PICO sends: "end_sensor:10"
        │
        ↓
TCPController receives message
        │
        ↓
_on_message_received("end_sensor:10")
        │
        ├─ Display in UI: "RX: end_sensor:10"
        │
        └─ Call: _handle_result_tab_sensor_events("end_sensor:10")
                 │
                 ├─ Detect "end_sensor" keyword
                 │
                 ├─ Parse sensor ID: _parse_sensor_id() → 10
                 │
                 └─ Call: _on_sensor_out_event(10)
                          │
                          ├─ Get result_tab_manager
                          │
                          ├─ Call: add_sensor_out_event(sensor_id_out=10)
                          │        │
                          │        ├─ Find pending frame (FIFO)
                          │        │  └─ Found: Frame 1
                          │        │
                          │        ├─ Set sensor_id_out = 10
                          │        │
                          │        └─ Return success = True
                          │
                          └─ Refresh table
                             │
                             └─ Result Tab updates:
                                Frame 1 | Sensor 5 | 10 | OK ✓
```

---

## Complete Timeline Example

```
TIME 1 ms:  TCP: "start_sensor:5"
            └─ Frame 1 created
            └─ Table: [1 | 5 | - | PENDING]

TIME 5 ms:  TCP: "start_sensor:6"
            └─ Frame 2 created
            └─ Table: [1 | 5 | - | PENDING]
                      [2 | 6 | - | PENDING]

TIME 10 ms: Job 1 completes (OK)
            └─ Result cached
            └─ Applied to Frame 1 (already exists)
            └─ Table: [1 | 5 | - | OK] ✓
                      [2 | 6 | - | PENDING]

TIME 15 ms: Job 2 completes (NG)
            └─ Result cached
            └─ Applied to Frame 2 (already exists)
            └─ Table: [1 | 5 | - | OK]
                      [2 | 6 | - | NG] ✓

TIME 20 ms: TCP: "end_sensor:10"
            └─ Matches Frame 2 (most recent)
            └─ Table: [1 | 5 | - | OK]
                      [2 | 6 | 10 | NG] ✓

TIME 25 ms: TCP: "end_sensor:9"
            └─ Matches Frame 1
            └─ Table: [1 | 5 | 9 | OK] ✓
                      [2 | 6 | 10 | NG] ✓
```

---

## State Transitions

### Frame States

```
                    add_sensor_in_event()
                           │
                           ↓
                    ┌─────────────┐
                    │  PENDING    │ ← Frame just created
                    │  (yellow)   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │                         │
    set_frame_status()    set_frame_status()
    ('OK')                ('NG')
              │                         │
              ↓                         ↓
        ┌─────────┐            ┌──────────┐
        │   OK    │            │   NG     │
        │(green)  │            │ (red)    │
        └─────────┘            └──────────┘
              │                         │
              └────────────┬────────────┘
                           │
              add_sensor_out_event()
                           │
                           ↓
                      ┌──────────┐
                      │ COMPLETE │ ← Sensor OUT set
                      │          │
                      └──────────┘
```

### Queue Size Management

```
Queue has 100 items (max)
        │
        ↓
New frame arrives
        │
        ├─ Is queue full?
        │  ├─ NO: Add new frame
        │  │       └─ Queue size = 99+1 = 100
        │  │
        │  └─ YES: Remove oldest frame
        │          └─ Add new frame
        │          └─ Queue size = 100 (no change)
        │
        └─ Refresh table
```

---

## Error Handling Flow

```
Exception in sensor event handling
        │
        ├─ Log error with full traceback
        │
        ├─ Print debug message to console
        │
        ├─ Continue execution (graceful degradation)
        │
        └─ Result Tab remains stable
           (previous state unchanged)
```

---

## Signal Processing Priority

```
TCP Message Received
        │
        ├─ [1] Add to UI message list
        │
        ├─ [2] Handle Result Tab sensor events
        │       ├─ Detect pattern
        │       ├─ Parse sensor ID
        │       └─ Create/Match frame
        │
        └─ [3] Check trigger camera if needed
                └─ (Only in trigger mode)
```

---

## Queue Matching Logic (FIFO)

```
Multiple pending frames:
  Frame 1: sensor_in=5, sensor_out=NULL (PENDING)
  Frame 2: sensor_in=6, sensor_out=NULL (PENDING)
  Frame 3: sensor_in=7, sensor_out=NULL (PENDING)

Sensor OUT arrives: "end_sensor:10"
        │
        └─ Match to MOST RECENT pending frame
           │
           └─ Frame 3 (most recent)
              ├─ Set sensor_out = 10
              └─ Status = OK
        
Sensor OUT arrives: "end_sensor:9"
        │
        └─ Match to next pending frame
           │
           └─ Frame 2 (next recent)
              ├─ Set sensor_out = 9
              └─ Status = NG
        
Sensor OUT arrives: "end_sensor:8"
        │
        └─ Match to remaining pending frame
           │
           └─ Frame 1 (first)
              ├─ Set sensor_out = 8
              └─ Status = OK

Result Table:
┌──────────┬───────────┬───────────┬────────┐
│ Frame ID │ Sensor IN │ Sensor OUT│ Status │
├──────────┼───────────┼───────────┼────────┤
│    1     │     5     │     8     │  OK 🟢 │
│    2     │     6     │     9     │  NG 🔴 │
│    3     │     7     │    10     │  OK 🟢 │
└──────────┴───────────┴───────────┴────────┘
```

---

## Debug Output Flow

```
User Action or TCP Event
        │
        ├─ logging.info() → Log file
        │
        ├─ print() → Console
        │
        └─ Result displayed
           
Example Output:
[TCPControllerManager] Sensor IN event - sensor_id=5, frame_id=1
DEBUG: [TCP] Sensor IN #5 → Frame ID #1
DEBUG: [TCP] Applied cached result - status=OK
```

---

**Status**: 🟢 **Complete Flow Implemented** ✅
