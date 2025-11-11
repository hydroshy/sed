# Result Tab FIFO Queue - Quick Start Guide

## ⚡ Quick Start (5 minutes)

### 1. View in UI
- Run the application
- Go to "Palette" tab → "Result" tab
- You'll see a table with 4 columns: Frame ID, Sensor IN, Sensor OUT, Status

### 2. Manual Testing

**Add a frame (simulate sensor IN):**
```python
frame_id = main_window.result_tab_manager.add_sensor_in_event(sensor_id_in=5)
print(f"New frame: {frame_id}")  # Output: New frame: 1
```

**Complete the frame (simulate sensor OUT):**
```python
main_window.result_tab_manager.add_sensor_out_event(sensor_id_out=10)
```

**Set status:**
```python
main_window.result_tab_manager.set_frame_status(frame_id=1, status='OK')
```

### 3. Real Integration

**In your TCP controller:**
```python
def on_sensor_message(message):
    if "START" in message:
        frame_id = main_window.result_tab_manager.add_sensor_in_event(sensor_id_in=5)
        # Trigger camera capture with frame_id
    elif "END" in message:
        main_window.result_tab_manager.add_sensor_out_event(sensor_id_out=10)
```

**In your detection pipeline:**
```python
def run_detection(frame_id, frame):
    results = detect_tool.run(frame)
    main_window.result_tab_manager.set_frame_detection_data(frame_id, results)
    
    status = 'NG' if has_defects(results) else 'OK'
    main_window.result_tab_manager.set_frame_status(frame_id, status)
```

## 📊 Table Operations

### Delete Selected Row
- Click on a row in the table
- Click "Delete Object" button
- Confirm deletion

### Clear All Rows
- Click "Clear Queue" button
- Confirm with "Clear all items?"

### View Statistics
```python
# Get queue info
size = main_window.result_tab_manager.get_queue_size()
pending = main_window.result_tab_manager.get_pending_frames()
completed = main_window.result_tab_manager.get_completed_frames()

print(f"Total: {size}, Pending: {len(pending)}, Completed: {len(completed)}")
```

## 🔄 Typical Workflow

```
1. Object enters sensor → add_sensor_in_event()
   │
   ├─ Create new row in Result Tab
   └─ Get frame_id
   
2. Trigger camera capture
   │
   └─ Capture frame with frame_id
   
3. Run detection/classification
   │
   ├─ set_frame_detection_data()
   └─ Store results
   
4. Evaluate OK/NG
   │
   └─ set_frame_status()
   
5. Object exits sensor → add_sensor_out_event()
   │
   └─ Match to pending frame, update Sensor OUT column
   
6. View results in Result Tab table
   │
   └─ Color coded: Green (OK), Red (NG), Yellow (PENDING)
```

## 🎯 Common Tasks

### Task: Automate sensor tracking
```python
class SensorTracker:
    def __init__(self, main_window):
        self.main_window = main_window
        self.pending_frames = {}
    
    def on_sensor_start(self, sensor_id):
        frame_id = self.main_window.result_tab_manager.add_sensor_in_event(sensor_id)
        self.pending_frames[frame_id] = sensor_id
    
    def on_sensor_end(self, sensor_id):
        self.main_window.result_tab_manager.add_sensor_out_event(sensor_id)

# Usage:
tracker = SensorTracker(main_window)
tracker.on_sensor_start(5)   # Object enters
tracker.on_sensor_end(10)    # Object exits
```

### Task: Export results to CSV
```python
import pandas as pd

def export_results(main_window, filename):
    data = main_window.result_tab_manager.fifo_queue.get_queue_as_table_data()
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"Exported to {filename}")

# Usage:
export_results(main_window, "results.csv")
```

### Task: Get statistics
```python
def print_stats(main_window):
    queue = main_window.result_tab_manager.fifo_queue
    completed = queue.get_completed_items()
    
    ok_count = sum(1 for item in completed if item.status == 'OK')
    ng_count = sum(1 for item in completed if item.status == 'NG')
    total = len(completed)
    
    print(f"Total: {total}")
    print(f"OK: {ok_count} ({ok_count/total*100:.1f}%)")
    print(f"NG: {ng_count} ({ng_count/total*100:.1f}%)")

# Usage:
print_stats(main_window)
```

## 🧪 Quick Test Script

Run this in Python console to test functionality:

```python
# Get reference to result tab manager
rtm = main_window.result_tab_manager

# Simulate 3 objects
print("Adding 3 objects...")
frame_1 = rtm.add_sensor_in_event(sensor_id_in=1)
frame_2 = rtm.add_sensor_in_event(sensor_id_in=2)
frame_3 = rtm.add_sensor_in_event(sensor_id_in=3)

# Simulate exits
print("Objects exiting...")
rtm.add_sensor_out_event(sensor_id_out=10)
rtm.add_sensor_out_event(sensor_id_out=11)
rtm.add_sensor_out_event(sensor_id_out=12)

# Set statuses
print("Setting statuses...")
rtm.set_frame_status(frame_1, 'OK')
rtm.set_frame_status(frame_2, 'NG')
rtm.set_frame_status(frame_3, 'OK')

# View results
print(f"Queue size: {rtm.get_queue_size()}")
print(f"Completed: {len(rtm.get_completed_frames())}")

# See table refresh automatically
```

## ❓ FAQ

**Q: How does frame_id work?**
A: Auto-incremented starting from 1. Each sensor IN event gets next ID (1, 2, 3, ...).

**Q: What if sensor OUT arrives before sensor IN?**
A: It will try to match to most recent pending frame. If no pending frames, it's ignored with warning.

**Q: Can I have multiple frames pending?**
A: Yes! Multiple objects can be in the queue simultaneously. Sensor OUT matches to most recent.

**Q: How do I know which status to set?**
A: Use your result_manager to evaluate detection results: `status = result_manager.evaluate_NG_OK(results)`

**Q: Can I undo a deletion?**
A: Not in current version. Deleted rows are gone. Use CSV export to backup data.

**Q: How many rows can the queue hold?**
A: Default max is 100 items. Older items auto-removed when exceeded. Edit `FIFOResultQueue.max_queue_size` to change.

**Q: Can I delete multiple rows at once?**
A: Currently only single row deletion. Use "Clear Queue" for all. Future version will support multi-select.

**Q: How do I export results?**
A: See "Task: Export results to CSV" section above.

## 📚 Full Documentation

- **Complete Guide**: `docs/RESULT_TAB_FIFO_QUEUE.md`
- **Integration Examples**: `docs/RESULT_TAB_INTEGRATION_EXAMPLES.md`
- **Implementation Details**: `docs/RESULT_TAB_IMPLEMENTATION_SUMMARY.md`

## 🧰 API Reference

### ResultTabManager Methods

```python
# Sensor events
frame_id = rtm.add_sensor_in_event(sensor_id_in)      # Returns frame_id
success = rtm.add_sensor_out_event(sensor_id_out)     # Returns bool

# Data storage
rtm.set_frame_detection_data(frame_id, detection_data)  # Returns bool
rtm.set_frame_status(frame_id, 'OK'|'NG'|'PENDING')     # Returns bool

# Queries
size = rtm.get_queue_size()                             # Returns int
pending = rtm.get_pending_frames()                      # Returns list
completed = rtm.get_completed_frames()                  # Returns list

# Auto-refresh
rtm.enable_auto_refresh(interval_ms=1000)
rtm.disable_auto_refresh()

# UI updates
rtm.refresh_table()  # Force immediate table refresh
```

### FIFOResultQueue Methods

```python
queue = rtm.fifo_queue

# Get all data
items = queue.get_queue_items()                      # Returns list
table_data = queue.get_queue_as_table_data()         # Returns list of dicts

# Query methods
pending = queue.get_pending_items()                  # No sensor OUT yet
completed = queue.get_completed_items()              # Has sensor OUT
size = queue.get_queue_size()                        # Current size

# Utility
queue.reset_frame_counter()  # Reset ID counter for new job
```

## 🚀 Next Steps

1. **Integrate with TCP**: Hook sensor events from PicoPython
2. **Connect Detection**: Run detection and store results
3. **Add Alerts**: Notify on NG events
4. **Export Data**: Save results to CSV/database
5. **View Statistics**: Show OK/NG ratios

Happy testing! 🎉
