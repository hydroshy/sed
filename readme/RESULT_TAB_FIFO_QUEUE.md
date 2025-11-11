# Result Tab FIFO Queue System Documentation

## Overview

Result Tab implements a FIFO (First-In-First-Out) queue system to track objects through the inspection process using sensor signals and frame IDs.

## Architecture

### Components

1. **FIFOResultQueue** (`fifo_result_queue.py`)
   - Core queue data structure
   - Maintains FIFO order of processed objects
   - Handles sensor IN/OUT event matching
   - Stores detection data and status per frame

2. **ResultTabManager** (`result_tab_manager.py`)
   - UI management layer
   - Table view synchronization
   - Button handlers (Delete, Clear Queue)
   - Integration with main window

3. **ResultQueueItem** (dataclass in `fifo_result_queue.py`)
   - Single object representation
   - Stores: frame_id, sensor_id_in, sensor_id_out, status, detection_data

## System Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                  Sensor Start Signal                        │
│            (start_sensor from PicoPython via TCP)           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ Create new Frame Entry:      │
        │ - Assign frame_id (auto)     │
        │ - Set sensor_id_in           │
        │ - Status: PENDING            │
        └──────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ Trigger Camera Capture       │
        │ - Capture frame              │
        │ - Run Detection/Classification│
        │ - Store detection_data       │
        └──────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ Sensor Stop Signal:          │
        │ Match to pending frame       │
        │ - Set sensor_id_out          │
        │ - Calculate status (OK/NG)   │
        └──────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ Result Queue Row:            │
        │ [FrameID | SenIN | SenOUT | Status] │
        └──────────────────────────────┘
```

## Table Columns

| Column | Description | Type | Notes |
|--------|-------------|------|-------|
| **Frame ID** | Unique identifier for this object | int | Auto-incremented, read-only |
| **Sensor IN** | Start sensor ID (from pico) | int | Assigned when object enters |
| **Sensor OUT** | End sensor ID (from pico) | int | "-" until object exits |
| **Status** | OK/NG/PENDING | string | Color coded: Green/Red/Yellow |

## Queue Operations

### 1. Add Sensor IN Event
```python
frame_id = result_tab_manager.add_sensor_in_event(sensor_id_in=5)
# Returns: frame_id for this object
# Result: New row added to table with Frame ID and Sensor IN
```

### 2. Set Frame Detection Data
```python
detection_data = {
    'detections': [...],
    'classifications': [...],
    'timestamp': datetime.now()
}
result_tab_manager.set_frame_detection_data(frame_id=1, detection_data)
# Stores detection data associated with this frame
```

### 3. Set Frame Status
```python
result_tab_manager.set_frame_status(frame_id=1, status='OK')
# or 'NG', or 'PENDING'
# Updates status column and colors table row
```

### 4. Add Sensor OUT Event
```python
success = result_tab_manager.add_sensor_out_event(sensor_id_out=10)
# Matches to most recent pending frame
# Returns: True if matched, False if no pending frame
```

### 5. Delete Single Row
```python
# User selects row and clicks "Delete Object" button
# Confirms deletion with dialog
# Removes row from queue
```

### 6. Clear Entire Queue
```python
# User clicks "Clear Queue" button
# Confirms with "cannot be undone" warning
# Removes all rows, resets frame counter
```

## Integration with Main Pipeline

### TCP Sensor Input
When TCP controller receives sensor signals from PicoPython:

```python
# In tcp_controller_manager or similar:
if start_sensor_signal:
    frame_id = self.main_window.result_tab_manager.add_sensor_in_event(sensor_id)
    # Trigger camera capture using frame_id
    trigger_camera_with_frame_id(frame_id)

if end_sensor_signal:
    self.main_window.result_tab_manager.add_sensor_out_event(sensor_id)
```

### Detection/Classification Pipeline
After running detect/classify tools:

```python
# In job execution:
detection_results = detect_tool.run(frame)
result_tab_manager.set_frame_detection_data(frame_id, detection_results)

# Evaluate OK/NG
status = result_manager.evaluate_NG_OK(detection_results)
result_tab_manager.set_frame_status(frame_id, status)
```

## Data Persistence

The queue data can be:
1. **Exported to CSV** for review/analysis
2. **Logged to database** for traceability
3. **Persisted between sessions** (optional)

### Export Example
```python
def export_queue_to_csv(self, filename):
    queue_data = self.fifo_queue.get_queue_as_table_data()
    df = pd.DataFrame(queue_data)
    df.to_csv(filename, index=False)
```

## Thread Safety

Currently, the queue is **not thread-safe**. For multi-threaded access:

```python
import threading
self.queue_lock = threading.Lock()

def add_sensor_in_event(self, sensor_id_in):
    with self.queue_lock:
        # existing code
```

## Performance Considerations

- Max queue size: 100 items (configurable)
- Older items auto-removed if limit exceeded
- Table refresh on every update (can be optimized)
- Auto-refresh interval: 1000ms (configurable)

## Debugging

Enable debug output:
```python
result_tab_manager.enable_auto_refresh(interval_ms=500)
# Watch for console DEBUG messages:
# DEBUG: [FIFOResultQueue] Sensor IN: frame_id=1, sensor_id_in=5
# DEBUG: [ResultTabManager] Detection data stored: frame_id=1
# DEBUG: [FIFOResultQueue] Status set: frame_id=1, status=OK
```

## Future Enhancements

1. **Batch Operations**: Delete multiple selected rows
2. **Search/Filter**: Filter by status, sensor ID, date range
3. **Export**: CSV, PDF, Database export
4. **Statistics**: Summary of OK/NG ratios, processing speed
5. **Real-time Alerts**: Notify on NG events
6. **Undo/Redo**: For accidental deletions
7. **Thread Safety**: Safe multi-threaded access
