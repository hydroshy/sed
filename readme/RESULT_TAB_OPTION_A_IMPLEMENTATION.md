# Result Tab FIFO Queue - Option A Implementation

## Architecture Overview

**Kiến trúc chờ TCP sensor IN signal trước khi tạo frame**

```
┌──────────────────────────────────────────────────────────────────┐
│                      JOB COMPLETION                              │
│  (Camera Source → Detect Tool → Result Tool)                     │
└────────────────────┬─────────────────────────────────────────────┘
                     │
                     ↓
         ┌───────────────────────────┐
         │   CameraManager           │
         │  _update_execution_label()│
         └───────────┬───────────────┘
                     │
                     ↓
      ┌──────────────────────────────────┐
      │ ResultTabManager                 │
      │ .save_pending_job_result()       │
      │                                  │
      │ Lưu tạm:                         │
      │ - Status (OK/NG)                 │
      │ - Similarity, reason             │
      │ - Detection data                 │
      │ - Inference time                 │
      │                                  │
      │ self.pending_result = {...}      │
      └────────┬─────────────────────────┘
               │
               ↓
    ┌──────────────────────────┐
    │  WAITING FOR TCP SIGNAL  │
    │  Chờ start_sensor event  │
    └────────────┬─────────────┘
                 │
                 ↓
      ┌──────────────────────────────────┐
      │  TCP Controller                  │
      │  Nhận: "start_sensor,<sensor_id>"│
      └────────┬─────────────────────────┘
               │
               ↓
      ┌──────────────────────────────────┐
      │ ResultTabManager                 │
      │ .on_sensor_in_received(sensor_id)│
      │                                  │
      │ 1. Create frame with sensor_id   │
      │ 2. Set status from pending       │
      │ 3. Store detection data          │
      │ 4. Clear pending_result          │
      │ 5. Display in table              │
      └────────┬─────────────────────────┘
               │
               ↓
      ┌──────────────────────────────────┐
      │  Result Tab (Table Updated)      │
      │                                  │
      │  Frame ID │ Sensor IN │ Status   │
      │  ─────────┼───────────┼──────    │
      │     1     │     5     │  OK 🟢   │
      └──────────────────────────────────┘
```

---

## File Changes

### 1. **New File: `gui/pending_result.py`** ✅
Lớp lưu tạm kết quả job chờ nhận sensor IN từ TCP

```python
@dataclass
class PendingJobResult:
    status: str  # OK, NG, PENDING
    similarity: float
    reason: str
    detection_data: Optional[Dict]
    inference_time: float
    timestamp: float
```

### 2. **Modified: `gui/result_tab_manager.py`** ✅
Thêm 2 methods mới:

- `save_pending_job_result()` - Lưu tạm kết quả job
- `on_sensor_in_received()` - Nhận sensor IN từ TCP, tạo frame

```python
def save_pending_job_result(self, status, similarity, reason, detection_data, inference_time):
    """Lưu tạm - không tạo frame ngay"""
    pending = PendingJobResult(...)
    self.pending_result = pending  # Lưu vào bộ nhớ

def on_sensor_in_received(self, sensor_id_in):
    """Nhận sensor IN từ TCP, tạo frame và ghép result"""
    frame_id = self.add_sensor_in_event(sensor_id_in)  # Tạo frame
    self.set_frame_status(frame_id, self.pending_result.status)  # Ghép status
    self.set_frame_detection_data(frame_id, self.pending_result.detection_data)  # Ghép data
    self.pending_result = None  # Clear
    return frame_id
```

### 3. **Modified: `gui/camera_manager.py`** ✅
Sửa Result Tab integration (dòng ~2800+):

**Before (cũ):**
```python
# Tạo frame ngay khi job hoàn thành
frame_id = result_tab_manager.add_sensor_in_event(sensor_id_in=1)
result_tab_manager.set_frame_status(frame_id, status)
result_tab_manager.set_frame_detection_data(frame_id, detection_data)
```

**After (mới):**
```python
# Lưu tạm, chờ TCP sensor IN signal
result_tab_manager.save_pending_job_result(
    status=status,
    similarity=0.0,
    reason=reason,
    detection_data=detection_data,
    inference_time=inference_time
)
```

### 4. **Modified: `gui/tcp_controller_manager.py`** ✅
Thêm 3 methods mới để xử lý sensor events:

- `_process_sensor_event()` - Parse TCP message
- `_handle_sensor_in_event()` - Xử lý start_sensor
- `_handle_sensor_out_event()` - Xử lý end_sensor

```python
def _on_message_received(self, message):
    # ... display message ...
    self._process_sensor_event(message)  # NEW

def _process_sensor_event(self, message):
    """Parse "start_sensor,<id>" or "end_sensor,<id>" """
    if message.startswith("start_sensor"):
        sensor_id = int(message.split(",")[1])
        self._handle_sensor_in_event(sensor_id)

def _handle_sensor_in_event(self, sensor_id):
    """Gọi result_tab_manager.on_sensor_in_received(sensor_id)"""
    frame_id = result_tab_manager.on_sensor_in_received(sensor_id)
```

---

## Data Flow

### Trường hợp 1: Job hoàn thành với kết quả OK

```
1. User click Trigger button
   ↓
2. Camera captures frame
   ↓
3. Job runs: Camera Source → Detect Tool → Result Tool
   ↓
4. Result Tool returns: status='OK', detection_data={...}
   ↓
5. CameraManager._update_execution_label() called
   ↓
6. save_pending_job_result(status='OK', detection_data={...})
   ├─ pending_result = PendingJobResult(status='OK', ...)
   └─ Log: "Lưu tạm kết quả job OK"
   ↓
7. Waiting for TCP start_sensor signal...
   ↓
8. Pico gửi TCP: "start_sensor,5"
   ↓
9. TCP Controller nhận message
   ↓
10. _process_sensor_event("start_sensor,5")
    ├─ Phân tích: start_sensor, sensor_id=5
    └─ Call: _handle_sensor_in_event(5)
    ↓
11. on_sensor_in_received(5)
    ├─ Check pending_result: OK ✓
    ├─ frame_id = add_sensor_in_event(5) → frame_id=1
    ├─ set_frame_status(1, 'OK')
    ├─ set_frame_detection_data(1, {...})
    ├─ pending_result = None
    └─ Return frame_id=1
    ↓
12. Result Tab displays:
    ┌─────────────────────────────┐
    │ Frame ID │ Sensor IN │ Status│
    │    1     │     5     │  OK 🟢│
    └─────────────────────────────┘
```

### Trường hợp 2: Không có pending result (lỗi hoặc test)

```
1. Pico gửi TCP: "start_sensor,10"
   (nhưng không có job hoàn thành)
   ↓
2. on_sensor_in_received(10)
   ├─ Check pending_result: None
   ├─ Log: "No pending result!"
   ├─ frame_id = add_sensor_in_event(10) → frame_id=1
   ├─ set_frame_status(1, 'PENDING')
   └─ Return frame_id=1
   ↓
3. Result Tab displays:
   ┌──────────────────────────────┐
   │ Frame ID │ Sensor IN │ Status │
   │    1     │     10    │PENDING🟡│
   └──────────────────────────────┘
```

### Trường hợp 3: Sensor OUT event

```
1. Pico gửi TCP: "end_sensor,15"
   ↓
2. TCP Controller nhận
   ↓
3. _process_sensor_event("end_sensor,15")
   ├─ Phân tích: end_sensor, sensor_id=15
   └─ Call: _handle_sensor_out_event(15)
   ↓
4. add_sensor_out_event(15)
   ├─ Match sensor_out=15 to most recent pending frame
   ├─ Update frame: sensor_id_out=15
   └─ Return True/False
   ↓
5. Result Tab updates:
   ┌──────────────────────────────────┐
   │ Frame ID │ Sensor IN │ Sensor OUT│
   │    1     │     5     │    15     │
   └──────────────────────────────────┘
```

---

## TCP Message Format

Expected TCP messages from Pico:

```
Start Sensor (when object enters):
  "start_sensor,<sensor_id>"
  Example: "start_sensor,5"

End Sensor (when object exits):
  "end_sensor,<sensor_id>"
  Example: "end_sensor,10"
```

Parse logic:
```python
parts = message.split(",")
if parts[0] == "start_sensor":
    sensor_id = int(parts[1])
    # Handle sensor IN
elif parts[0] == "end_sensor":
    sensor_id = int(parts[1])
    # Handle sensor OUT
```

---

## Class: PendingJobResult

Lưu tạm kết quả job chờ nhận sensor IN

```python
@dataclass
class PendingJobResult:
    status: str              # 'OK', 'NG', 'PENDING'
    similarity: float        # 0.0-1.0
    reason: str             # Lý do OK/NG
    detection_data: Dict    # Detections/classifications
    inference_time: float   # Thời gian inference
    timestamp: float        # Thời gian job hoàn thành
    
    def to_dict(self):
        """Convert to dictionary for frame"""
        return {...}
```

---

## Method: ResultTabManager.save_pending_job_result()

**Được gọi từ:** `camera_manager._update_execution_label()`

**Khi nào:** Job hoàn thành và có kết quả (OK/NG)

**Làm gì:**
1. Tạo PendingJobResult object
2. Lưu vào `self.pending_result`
3. Log thông tin

**Parameters:**
- `status` (str): 'OK', 'NG', or 'PENDING'
- `similarity` (float): 0-1 (thường 0.0 khi lấy từ ResultTool)
- `reason` (str): Mô tả kết quả
- `detection_data` (dict): {'detections': [...], 'detection_count': N, ...}
- `inference_time` (float): Thời gian inference

**Return:**
- `bool`: True nếu lưu thành công

**Log messages:**
```
[ResultTabManager] Saved pending job result: PendingJobResult(status=OK, ...)
[ResultTabManager] Waiting for TCP sensor IN signal...
  - Status: OK
  - Similarity: 0.00%
  - Detection count: 2
```

---

## Method: ResultTabManager.on_sensor_in_received()

**Được gọi từ:** `tcp_controller_manager._handle_sensor_in_event()`

**Khi nào:** TCP nhận "start_sensor,<id>" từ Pico

**Làm gì:**
1. Kiểm tra `self.pending_result`
2. Tạo frame mới với sensor_id từ TCP
3. Ghép status từ pending_result
4. Ghép detection data
5. Clear pending_result
6. Refresh table

**Parameters:**
- `sensor_id_in` (int): Sensor ID từ TCP (ví dụ: 5, 10, 15)

**Return:**
- `int`: frame_id nếu thành công (>0), -1 nếu lỗi

**Example:**
```python
# TCP nhận "start_sensor,5"
frame_id = result_tab_manager.on_sensor_in_received(5)

# Kết quả:
# - Frame ID: 1 (auto-incrementing)
# - Sensor IN: 5 (từ TCP)
# - Status: OK (từ pending_result)
# - Detection data: {...} (từ pending_result)
```

---

## State Diagram

```
NORMAL STATE:
┌─────────────────┐
│  No Pending     │
│  pending_result │
│  = None         │
└────────┬────────┘
         │ Job completes
         ↓
WAITING STATE:
┌─────────────────────────┐
│  Pending Result Saved   │
│  pending_result = {...} │
│                         │
│  Waiting for:           │
│  "start_sensor,<id>"    │
└────────┬────────────────┘
         │ TCP sensor IN received
         ↓
FRAME CREATED:
┌─────────────────────────┐
│  Frame created          │
│  Status: OK/NG/PENDING  │
│  Detection data stored  │
│  pending_result = None  │
│                         │
│  Table updated ✓        │
└────────┬────────────────┘
         │ 
         ↓
Back to NORMAL STATE
```

---

## Error Handling

### Scenario 1: No pending result when sensor IN received

```python
# Pico sends "start_sensor,5" but no job completed before
result = on_sensor_in_received(5)

# Action:
# 1. Check: pending_result is None
# 2. Log: "No pending result!"
# 3. Create frame anyway with status='PENDING'
# 4. Frame ID: 1, Sensor IN: 5, Status: PENDING🟡
# 5. Return: frame_id=1
```

### Scenario 2: TCP message parsing error

```python
# Invalid message format
message = "invalid,format,x,y"

# Action:
# 1. Parse fails or doesn't match pattern
# 2. _process_sensor_event() ignores it
# 3. Logs warning: "Unknown message format"
# 4. No action taken
```

### Scenario 3: Result Tab Manager not found

```python
# main_window doesn't have result_tab_manager
result_tab_manager = getattr(main_window, 'result_tab_manager', None)

# Action if None:
# 1. Log: "Result Tab Manager not found!"
# 2. Function returns early
# 3. No pending result saved
# 4. No frame created
```

---

## Logging Output

### On Job Completion (OK)
```
[CameraManager] ✅ Saved pending result: status=OK
[CameraManager] Waiting for TCP 'start_sensor' event...
[ResultTabManager] Saved pending job result: PendingJobResult(status=OK, ...)
[ResultTabManager] Waiting for TCP sensor IN signal...
  - Status: OK
  - Similarity: 0.00%
  - Detection count: 2
```

### On TCP Sensor IN Received
```
[TCPController] 🚀 Sensor IN received: sensor_id=5
[ResultTabManager] TCP Sensor IN received: sensor_id_in=5
[ResultTabManager] Created frame: frame_id=1
[ResultTabManager] Set frame status: OK
[ResultTabManager] Stored detection data for frame 1
[ResultTabManager] ✅ Frame 1 completed with sensor_id_in=5, status=OK
[TCPController] ✅ Frame created: frame_id=1, sensor_id=5
```

### On TCP Sensor OUT Received
```
[TCPController] 🔚 Sensor OUT received: sensor_id=15
[ResultTabManager] Sensor OUT added - sensor_id_out=15, success=True
[TCPController] ✅ Sensor OUT matched successfully
```

---

## Testing

### Test Case 1: Job → Wait → Sensor IN
```python
# Simulate job completion
result_tab_manager.save_pending_job_result(
    status='OK',
    similarity=0.0,
    reason='Detection passed',
    detection_data={'detections': [...], 'detection_count': 2},
    inference_time=0.210
)
# pending_result saved

# Simulate TCP sensor IN
frame_id = result_tab_manager.on_sensor_in_received(5)
# frame_id = 1
# Table shows: Frame 1, Sensor IN=5, Status=OK
```

### Test Case 2: Missing pending result
```python
# pending_result = None

# Simulate TCP sensor IN anyway
frame_id = result_tab_manager.on_sensor_in_received(10)
# frame_id = 1
# Table shows: Frame 1, Sensor IN=10, Status=PENDING
```

### Test Case 3: Sensor OUT matching
```python
# After frame created with sensor_in=5

# Simulate TCP sensor OUT
success = result_tab_manager.add_sensor_out_event(15)
# success = True
# Table updates: Frame 1, Sensor IN=5, Sensor OUT=15
```

---

## Advantages of Option A

✅ **Gọn gàng**: Frame chỉ được tạo khi có đủ thông tin  
✅ **Chính xác**: Sensor ID từ TCP (không hardcode)  
✅ **Linh hoạt**: Có thể xử lý multiple pending results nếu cần  
✅ **Rõ ràng**: Flow rõ ràng: Job → Lưu tạm → Chờ sensor → Tạo frame  
✅ **Sạch**: PENDING state khi không có job result

---

## Status: ✅ IMPLEMENTED

- [x] pending_result.py created
- [x] result_tab_manager.py modified (save_pending_job_result, on_sensor_in_received)
- [x] camera_manager.py modified (save instead of create)
- [x] tcp_controller_manager.py modified (sensor parsing, handling)
- [x] Comprehensive logging added
- [x] Error handling implemented
- [x] Documentation complete

**Ready for production!** 🚀
