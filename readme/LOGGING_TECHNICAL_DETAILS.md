# Logging Optimization - Technical Summary

## Problem Statement
Hệ thống logs hiện tại in quá nhiều thông tin lên terminal:
- BUG messages
- Standard INFO level logs với timestamps
- DEBUG messages

Điều này làm cho terminal lộn xộn và khó theo dõi khi chạy bình thường.

## Solution
Tối ưu hóa logging system để:
1. **Normal mode**: Terminal sạch (chỉ show errors khi cần)
2. **Debug mode** (`--debug`): Chỉ hiển thị DEBUG messages

## Implementation Details

### 1. Custom Handler Class (main.py)
```python
class DebugOnlyStreamHandler(logging.StreamHandler):
    """Custom handler that only outputs DEBUG level messages to terminal"""
    def emit(self, record):
        if record.levelno >= logging.DEBUG and record.levelno < logging.INFO:
            super().emit(record)
```

**Giải thích**:
- Kế thừa từ `logging.StreamHandler` (handler cho console)
- Override `emit()` method để filter messages
- Chỉ cho phép messages có level >= DEBUG nhưng < INFO
- Tức là: chỉ DEBUG level (DEBUG=10, INFO=20)

### 2. Logging Configuration (main.py)

**Bước 1**: Setup file handler luôn on
```python
file_handler = logging.FileHandler('sed_app.log')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler]
)
```

**Bước 2**: Khi `--debug` flag được truyền
```python
if args.debug:
    debug_stream_handler = DebugOnlyStreamHandler()
    debug_formatter = logging.Formatter('DEBUG: %(message)s')
    debug_stream_handler.setFormatter(debug_formatter)
    logging.getLogger().addHandler(debug_stream_handler)
```

### 3. Module Logger Updates

**camera_view.py**:
```python
# Old
logging.basicConfig(level=logging.DEBUG, format='...')

# New
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
```

**main_window.py**:
```python
# Old
logging.basicConfig(level=logging.DEBUG, format='...')

# New  
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
```

**Lý do**: Để tránh xung đột giữa nhiều basicConfig calls. Module loggers kế thừa handler từ root logger.

## Logging Levels

| Level | Value | Terminal (Normal) | Terminal (Debug) | File |
|-------|-------|-------------------|------------------|------|
| DEBUG | 10 | ❌ | ✅ | ✅ |
| INFO | 20 | ❌ | ❌ | ✅ |
| WARNING | 30 | ❌ | ❌ | ✅ |
| ERROR | 40 | ❌ | ❌ | ✅ |

## Output Examples

### Normal Mode
```bash
$ python main.py

# Terminal: Completely clean!
# File sed_app.log: Contains all logs with full details
```

### Debug Mode  
```bash
$ python main.py --debug

DEBUG: Debug logging enabled - only DEBUG messages will show in terminal
DEBUG: [CameraManager] Frame pending detected (5 frames), flushing...
DEBUG: [CameraView] No processed frame available for detection_detect_tool
DEBUG: [_process_frame_to_qimage] Processing with format: RGB888
...

# Terminal: Only DEBUG messages, clean format
# File sed_app.log: Complete logs with timestamps
```

## Performance Impact
- **Negligible**: Handler filtering happens at the logging level, not I/O level
- File logging unchanged (same as before)
- Terminal output reduced (only 1 handler instead of 2 in normal mode)

## Advantages

✅ **Clean Terminal**: Normal operation doesn't clutter console
✅ **Easy Debugging**: `--debug` flag shows exactly what you need
✅ **Complete Logging**: File always has everything
✅ **Flexible**: Easy to add more handlers if needed
✅ **Centralized**: All logging config in main.py
✅ **Compatible**: Existing logger calls unchanged

## Files Modified

1. **main.py**
   - Added DebugOnlyStreamHandler class
   - Setup file handler + conditional stream handler
   - Integrated with --debug argument

2. **camera_view.py**
   - Removed basicConfig to use module logger
   - Inherited handlers from root logger

3. **main_window.py**
   - Removed basicConfig to use module logger
   - Inherited handlers from root logger

## Testing

Test script: `test_logging_opt.py`

```bash
# Test normal mode
python test_logging_opt.py
# Output: Clean terminal, all in test_logging.log

# Test debug mode
python test_logging_opt.py --debug
# Output: DEBUG message visible, all in test_logging.log
```

Results:
- ✅ Normal mode: Terminal clean
- ✅ Debug mode: DEBUG message shown
- ✅ File logging: All messages captured with timestamps

## Usage

```bash
# Normal mode - production
python main.py

# Debug mode - development/troubleshooting
python main.py --debug

# View logs
tail -f sed_app.log
```

## Future Enhancements

Có thể mở rộng thêm:
1. Log rotation (FileHandler with RotatingFileHandler)
2. Multiple log files (separate logs for modules)
3. JSON format logging
4. Remote logging (syslog, Elasticsearch)
5. Log level per module (e.g., only debug for camera_view)

## Backward Compatibility

✅ Hoàn toàn backward compatible:
- Existing logger calls không thay đổi
- API không thay đổi
- Chỉ cấu hình output thay đổi
