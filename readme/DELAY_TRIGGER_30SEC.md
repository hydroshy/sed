# ⚡ Delay Trigger - 30 Giây Giải Thích

**Status:** ✅ Hoàn Tất & Sẵn Dùng

---

## 🎯 Là Gì?

Tính năng **Delay Trigger** giúp bạn **chờ một khoảng thời gian** trước khi chụp ảnh khi nhận trigger từ cảm biến.

---

## 🎛️ Cách Dùng

### 1️⃣ Bật Tính Năng
```
Tab "Control" → Tích ☑️ "Delay Trigger"
```

### 2️⃣ Nhập Delay (ms)
```
Spinbox → Gõ giá trị (ví dụ: 10.5)
Đơn vị: milliseconds (0.1ms precision)
```

### 3️⃣ Sử Dụng
```
Trigger từ Pico → Hệ thống chờ delay → Chụp ảnh
```

---

## 📊 Ví Dụ

| Setting | Kết Quả |
|---------|---------|
| ☐ (Tắt) | [TRIGGER] - Chụp ngay |
| ☑ [5.0 ms] | [TRIGGER+5.0ms] - Chờ 5ms rồi chụp |
| ☑ [10.5 ms] | [TRIGGER+10.5ms] - Chờ 10.5ms rồi chụp |
| ☑ [50.0 ms] | [TRIGGER+50.0ms] - Chờ 50ms rồi chụp |

---

## 🔧 Kỹ Thuật

| Thành Phần | Chi Tiết |
|-----------|---------|
| **File** | gui/main_window.py, gui/tcp_controller_manager.py |
| **Dòng Thêm** | ~150 lines |
| **Lỗi** | 0 errors ✅ |
| **Status** | Production ready ✅ |

---

## ✅ Hoàn Tất

```
✅ UI (Checkbox + Spinbox)
✅ Logic (Delay application)
✅ Logging (Console debug)
✅ Feedback (Message list)
✅ Testing (All pass)
✅ Documentation (Complete)
```

---

## 🚀 Sẵn Dùng

Chỉ cần chạy app và vào Tab "Control" → "Delay Trigger"!

---

**Chi tiết:** Xem DELAY_TRIGGER_USER_GUIDE.md (Tiếng Việt)

