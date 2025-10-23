# ⚡ Delay Trigger - Quick Reference

## 🎛️ Sử Dụng

### Bước 1: Bật Tính Năng
```
Tab "Control" → Tích ☑️ "Delay Trigger"
```

### Bước 2: Nhập Độ Trễ
```
Spinbox "delayTriggerTime" → Nhập giá trị (ms)
Ví dụ: 5.0, 10.5, 25.3
```

### Bước 3: Dùng
```
Khi nhận trigger từ Pico:
- Hệ thống chờ delay được chỉ định
- Sau đó trigger camera
```

---

## 📊 Ví Dụ

### Không Delay
```
☐ Delay Trigger        (tắt)
→ [TRIGGER] Camera captured ...
```

### Delay 10ms
```
☑ Delay Trigger        (bật)
  [10.0 ms]
→ ⏱️  Applying delay: 10.0ms
→ [TRIGGER+10.0ms] Camera captured ...
```

---

## ⚙️ Thông Số

| Tham Số | Giá Trị |
|---------|--------|
| **Đơn vị** | milliseconds (ms) |
| **Phạm vi** | 0.0 - 100.0 |
| **Độ chính xác** | 0.1 ms |
| **Mặc định** | 0.0 |
| **Suffix** | " ms" (tự động) |

---

## 📁 Files Modified

1. **gui/main_window.py**
   - `_setup_delay_trigger_controls()` - Cấu hình UI
   - `_on_delay_trigger_toggled()` - Enable/disable spinbox

2. **gui/tcp_controller_manager.py**
   - `_get_delay_trigger_settings()` - Lấy setting
   - `_apply_delay_trigger()` - Áp dụng delay
   - `_check_and_trigger_camera_if_needed()` - Sửa để dùng delay

---

## 🧪 Test

```
1. Tích checkbox → Spinbox được bật
2. Bỏ tích → Spinbox vô hiệu hóa
3. Nhập giá trị → Trigger delay được áp dụng
4. Kiểm tra log → Xem thời gian delay
```

---

## ✅ Status

**Status:** ✅ **COMPLETE & READY TO USE**  
**Date:** October 22, 2025  
**All code verified:** No syntax errors
