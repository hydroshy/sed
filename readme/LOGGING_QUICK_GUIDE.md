# Quick Guide - Logging Optimization

## TL;DR (Tóm tắt nhanh)

**Trước**: Terminal đầy logs lộn xộn
```
BUG: [ResultTabManager] No frame waiting for result
2025-12-19 15:31:44,855 - root - INFO - [CameraManager] No waiting frame
DEBUG: [CameraManager] Buffering result...
2025-12-19 15:31:44,855 - gui.result_tab_manager - INFO - [ResultTabManager] Saved...
...
```

**Sau**: Terminal sạch khi chạy bình thường, DEBUG khi cần debug
```bash
# Chạy bình thường
$ python main.py
# → Terminal sạch, logs vào sed_app.log

# Chạy debug
$ python main.py --debug  
# → Terminal chỉ show DEBUG messages
DEBUG: [CameraManager] Frame processing...
DEBUG: [CameraView] Display mode: camera
```

## Cách sử dụng

### 1. Chạy bình thường (Production)
```bash
python main.py
```
- Terminal sạch sẽ ✨
- Logs lưu vào `sed_app.log`
- Errors vẫn được show qua dialogs

### 2. Debug khi có vấn đề
```bash
python main.py --debug
```
- Chỉ DEBUG messages lên terminal
- Format ngắn gọn: `DEBUG: [message]`
- Logs đầy đủ trong `sed_app.log`

### 3. Xem logs đầy đủ
```bash
# Xem file log
tail -f sed_app.log

# Hoặc dùng editor
cat sed_app.log
```

## Ưu điểm

| Aspekt | Trước | Sau |
|--------|-------|-----|
| Terminal khi chạy | 🔴 Lộn xộn | 🟢 Sạch |
| Khi debug | 🟡 Quá nhiều noise | 🟢 Chỉ DEBUG |
| Log file | ✅ Đầy đủ | ✅ Đầy đủ |
| Dễ sử dụng | 🟡 Phức tạp | 🟢 Đơn giản |

## Thay đổi chi tiết

### main.py
- ✨ Thêm `DebugOnlyStreamHandler` class
- ✨ Filter console output based on `--debug` flag
- ✨ File logging luôn on

### camera_view.py
- ✨ Xóa `basicConfig` call
- ✨ Sử dụng module logger

### main_window.py
- ✨ Xóa `basicConfig` call
- ✨ Sử dụng module logger

## Test

```bash
# Test script đã tạo
python test_logging_opt.py          # Normal mode
python test_logging_opt.py --debug  # Debug mode

# Check log file
cat test_logging.log
```

**Kết quả**:
- ✅ Normal: Terminal sạch, log file có logs
- ✅ Debug: Terminal show DEBUG, log file có logs
- ✅ File: Luôn có tất cả logs với timestamps

## Files Modified

- `main.py` - Main logging configuration
- `camera_view.py` - Remove basicConfig
- `main_window.py` - Remove basicConfig
- `LOGGING_OPTIMIZATION.md` - Documentation
- `LOGGING_TECHNICAL_DETAILS.md` - Technical details
- `test_logging_opt.py` - Test script

## Backward Compatible

✅ Không break existing code
✅ Logger calls không cần thay đổi
✅ Chỉ cấu hình console output thay đổi

## Troubleshooting

**Q: Không thấy DEBUG messages?**
A: Chắc chắn chạy với flag: `python main.py --debug`

**Q: Logs đâu?**
A: Xem file `sed_app.log` (được tạo tự động)

**Q: Terminal vẫn có INFO messages?**
A: Kiểm tra có process khác in ra không, hoặc chạy lại setup logging

**Q: Muốn xem logs realtime?**
A: `tail -f sed_app.log` (Linux/Mac) hoặc dùng editor

## Chạy command

```bash
# Chạy bình thường - terminal sạch
python main.py

# Chạy debug - xem DEBUG messages
python main.py --debug

# Xem logs
tail -f sed_app.log

# Xem toàn bộ logs
cat sed_app.log

# Xóa logs cũ  
rm sed_app.log
```

---
**Tóm lại**: 
- 📱 Normal: Terminal sạch
- 🐛 Debug: `--debug` để xem DEBUG logs
- 📝 Files: Xem `sed_app.log` cho tất cả details
