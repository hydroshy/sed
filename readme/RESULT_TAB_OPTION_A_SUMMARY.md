# Result Tab Option A - Quick Summary

## ✅ IMPLEMENTED: Lưu tạm job result, chờ TCP sensor IN

---

## Flow

```
Job Done (OK/NG)
  ↓
save_pending_job_result()
  └─ Lưu: status, similarity, reason, detection_data
  └─ pending_result = PendingJobResult(...)
  
Waiting for TCP "start_sensor,<sensor_id>"
  
TCP start_sensor received
  ↓
on_sensor_in_received(sensor_id)
  ├─ Create frame with sensor_id from TCP ✓
  ├─ Set status from pending ✓
  ├─ Store detection data ✓
  ├─ Clear pending ✓
  └─ Table updates ✓
```

---

## Files Created

| File | Purpose |
|------|---------|
| `gui/pending_result.py` | PendingJobResult dataclass |

---

## Files Modified

| File | Changes |
|------|---------|
| `gui/result_tab_manager.py` | Added: save_pending_job_result(), on_sensor_in_received() |
| `gui/camera_manager.py` | Changed: save pending instead of create frame immediately |
| `gui/tcp_controller_manager.py` | Added: _process_sensor_event(), _handle_sensor_in_event(), _handle_sensor_out_event() |

---

## Key Methods

### 1. save_pending_job_result()
**Called from:** camera_manager (khi job hoàn thành)

```python
result_tab_manager.save_pending_job_result(
    status='OK',
    similarity=0.0,
    reason='Detection passed',
    detection_data={...},
    inference_time=0.210
)
```

**Làm gì:** Lưu tạm result chờ nhận sensor IN từ TCP

---

### 2. on_sensor_in_received(sensor_id)
**Called from:** tcp_controller_manager (khi nhận "start_sensor,<id>")

```python
frame_id = result_tab_manager.on_sensor_in_received(5)
```

**Làm gì:**
- Tạo frame mới với sensor_id từ TCP
- Ghép status từ pending
- Ghép detection data
- Clear pending_result
- Table refreshes tự động

**Return:** frame_id (1, 2, 3, ...) hoặc -1 nếu lỗi

---

## TCP Message Format

```
"start_sensor,<sensor_id>"   → Creates frame
"end_sensor,<sensor_id>"     → Matches to frame
```

Example:
```
TCP sends: "start_sensor,5"
  → frame_id = 1, sensor_in = 5, status = OK

TCP sends: "end_sensor,10"
  → frame_id = 1, sensor_out = 10
```

---

## Logging

### Job Completes
```
[ResultTabManager] Saved pending job result: PendingJobResult(status=OK, ...)
[ResultTabManager] Waiting for TCP sensor IN signal...
```

### Sensor IN Received
```
[TCPController] 🚀 Sensor IN received: sensor_id=5
[ResultTabManager] Created frame: frame_id=1
[ResultTabManager] ✅ Frame 1 completed with sensor_id_in=5, status=OK
```

---

## Data Structure

```python
class PendingJobResult:
    status: str                    # 'OK', 'NG', 'PENDING'
    similarity: float              # 0-1
    reason: str                    # Mô tả
    detection_data: Dict           # Detections
    inference_time: float          # Thời gian
    timestamp: float               # Khi lưu
```

---

## Edge Cases

| Case | Action |
|------|--------|
| No pending result when sensor IN arrives | Create frame with PENDING status |
| Invalid TCP message | Ignore, log warning |
| ResultTabManager not found | Log error, skip |

---

## Status: ✅ READY TO TEST

All code implemented and ready for:
1. Manual testing with TCP messages
2. Integration with Pico sensor events
3. Production deployment

---

**Implementation Date:** 2025-11-06  
**Status:** Complete ✅  
**Ready for:** Live testing with TCP sensors
