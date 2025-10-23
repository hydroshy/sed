# 🎓 Delay Trigger - Hướng Dẫn Chi Tiết Cho Người Dùng

**Ngôn ngữ:** Tiếng Việt  
**Cấp độ:** Cơ bản  
**Thời gian đọc:** 10 phút

---

## 📚 Mục Lục

1. [Khái Niệm Cơ Bản](#khái-niệm-cơ-bản)
2. [Hướng Dẫn Từng Bước](#hướng-dẫn-từng-bước)
3. [Các Ví Dụ Thực Tế](#các-ví-dụ-thực-tế)
4. [Ghi Log & Debug](#ghi-log--debug)
5. [Tình Huống Thường Gặp](#tình-huống-thường-gặp)
6. [Mẹo & Thủ Thuật](#mẹo--thủ-thuật)

---

## 🎯 Khái Niệm Cơ Bản

### Delay Trigger Là Gì?

**Delay Trigger** (Kích hoạt Có Độ Trễ) là một tính năng cho phép bạn **chờ một khoảng thời gian** trước khi thực hiện chụp ảnh khi nhận được tín hiệu từ cảm biến Pico.

### Tại Sao Cần Delay?

```
Trường hợp 1: Cảm biến phát hiện sự kiện sớm
→ Bạn cần chờ một chút để lấy góc tốt nhất
→ Dùng delay 50ms để đợi

Trường hợp 2: Xử lý mạng chậm
→ Dùng delay để bù đắp độ trễ mạng

Trường hợp 3: Đợi môi trường ổn định
→ Ánh sáng, nhiệt độ, độ ẩm ổn định hơn
→ Dùng delay 100ms
```

### Đơn Vị: Millisecond (ms)

- **1 second = 1000 milliseconds**
- **1 ms = 0.001 second**
- **Ví dụ:**
  - 5 ms = 0.005 second (rất nhanh)
  - 10 ms = 0.01 second (gần như không cảm nhận)
  - 100 ms = 0.1 second (có thể cảm nhận)

---

## 🎛️ Hướng Dẫn Từng Bước

### Bước 1️⃣: Mở Ứng Dụng

```
1. Chạy ứng dụng
2. Giao diện hiện lên
3. Chọn Tab "Control" ở bên phải
```

**Kết quả:**
- Bạn thấy giao diện điều khiển TCP
- Có một checkbox: "☐ Delay Trigger"
- Bên cạnh có spinbox: [0.0 ms]

### Bước 2️⃣: Bật Tính Năng Delay

```
1. Tìm checkbox "Delay Trigger"
2. Tích vào ☑️ để bật
```

**Kết quả:**
```
Trước: ☐ Delay Trigger    [0.0 ms] (grayed out - không thể dùng)
Sau:   ☑ Delay Trigger    [0.0 ms] (bình thường - có thể dùng)
```

**Console Log:**
```
✓ Delay trigger enabled - delay: 0.0ms
```

### Bước 3️⃣: Nhập Giá Trị Delay

```
1. Click vào spinbox [0.0 ms]
2. Double-click để chỉnh sửa
3. Xóa giá trị cũ
4. Gõ giá trị mới (ví dụ: 10.5)
5. Nhấn Enter
```

**Ví dụ nhập:**
```
Spinbox cũ: [0.0 ms]
Gõ vào:     10.5
Kết quả:    [10.5 ms] ✓
```

### Bước 4️⃣: Dùng Tính Năng

```
1. Đảm bảo camera ở chế độ "Trigger"
2. Gửi tín hiệu trigger từ Pico
3. Hệ thống sẽ:
   - Chờ delay được chỉ định (10.5ms)
   - Sau đó trigger camera
```

### Bước 5️⃣: Xem Kết Quả

**Message List sẽ hiển thị:**
```
[TRIGGER+10.5ms] Camera captured from: start_rising||1634723
```

**Console Log sẽ hiển thị:**
```
★ Detected trigger command: start_rising||1634723
⏱️  Applying delay: 10.5ms (0.0105s)
✓ Delay completed, triggering camera now...
✓ Camera triggered successfully (after 10.5ms delay)
```

---

## 💻 Các Ví Dụ Thực Tế

### Ví Dụ 1: Không Dùng Delay (Trigger Ngay)

**Thiết Lập:**
```
☐ Delay Trigger        (bỏ tích)
  [10.0 ms]            (không quan trọng vì tắt)
```

**Quy Trình:**
```
t=0ms    : Nhận tín hiệu từ Pico "start_rising||1234567"
t=0ms    : Trigger camera ngay lập tức
t=<1ms   : Ảnh được chụp
```

**Kết Quả:**
```
Console:      [TRIGGER] Camera captured from: start_rising||1234567
Message List: [TRIGGER] Camera captured from: start_rising||1234567
Delay:        0ms (không delay)
```

### Ví Dụ 2: Delay 5 Milliseconds

**Thiết Lập:**
```
☑ Delay Trigger        (tích)
  [5.0 ms]             (nhập giá trị 5.0)
```

**Quy Trình:**
```
t=0ms    : Nhận tín hiệu từ Pico
t=0ms    : Bắt đầu chờ 5.0ms
t=5ms    : Kết thúc chờ, trigger camera
t=<6ms   : Ảnh được chụp
```

**Kết Quả:**
```
Console:      ⏱️  Applying delay: 5.0ms (0.0050s)
              [TRIGGER+5.0ms] Camera captured...
Message List: [TRIGGER+5.0ms] Camera captured...
Delay:        5ms (đã được chờ)
```

### Ví Dụ 3: Delay 50 Milliseconds (Nhất Tế Hơn)

**Thiết Lập:**
```
☑ Delay Trigger        (tích)
  [50.0 ms]            (nhập giá trị 50.0)
```

**Quy Trình:**
```
t=0ms    : Nhận tín hiệu "cảm biến phát hiện sự kiện"
t=0ms    : Bắt đầu chờ 50ms để vật thể ổn định
t=50ms   : Kết thúc chờ, trigger camera
t=<51ms  : Ảnh được chụp
```

**Console Log Chi Tiết:**
```
INFO: ★ Detected trigger command: start_rising||1634723
INFO: ★ Camera is in trigger mode
INFO: ⏱️  Applying delay: 50.0ms (0.0500s)
INFO: ✓ Delay completed, triggering camera now...
INFO: ★ Calling camera_manager.activate_capture_request()
INFO: ✓ Camera triggered successfully (after 50.0ms delay)
```

### Ví Dụ 4: Thay Đổi Giá Trị Động

**Kịch Bản:**
```
Lần 1: [5.0 ms]   → Delay 5ms
      (Thấy kết quả không tốt)

Lần 2: [15.0 ms]  → Thay giá trị thành 15ms
      (Kết quả tốt hơn)

Lần 3: [25.5 ms]  → Thay giá trị thành 25.5ms
      (Tìm được giá trị tối ưu)
```

**Cách Thay Đổi:**
```
1. Spinbox: [5.0 ms]
2. Double-click vào spinbox
3. Xóa 5.0
4. Gõ 15.0
5. Enter → [15.0 ms] ✓
```

---

## 🔍 Ghi Log & Debug

### Hiểu Các Dòng Log

#### Khi Bật Delay

**Log Bước 1: Phát Hiện Trigger**
```
★ Detected trigger command: start_rising||1634723
```
- Nghĩa: Nhận được tín hiệu từ Pico ✓

**Log Bước 2: Kiểm Tra Chế Độ**
```
★ Camera is in trigger mode
```
- Nghĩa: Camera đang ở chế độ trigger (có thể trigger) ✓

**Log Bước 3: Lấy Delay Setting**
```
⏱️  Applying delay: 10.0ms (0.0100s)
```
- Nghĩa: Hệ thống đang chờ 10ms ⏳

**Log Bước 4: Hoàn Thành Delay**
```
✓ Delay completed, triggering camera now...
```
- Nghĩa: Chờ xong, bây giờ trigger camera ✓

**Log Bước 5: Trigger Ảnh**
```
★ Calling camera_manager.activate_capture_request()
✓ Camera triggered successfully (after 10.0ms delay)
```
- Nghĩa: Camera đã chụp ảnh (sau 10ms delay) ✓

#### Khi Tắt Delay

**Log:**
```
★ Detected trigger command: start_rising||1634723
★ Camera is in trigger mode
★ Calling camera_manager.activate_capture_request()
✓ Camera triggered successfully
```
- Lưu ý: **Không có** "⏱️  Applying delay" → Trigger ngay ✓

### Hệ Thống Log

| Ký Hiệu | Nghĩa | Mức |
|---------|-------|-----|
| ★ | Bắt đầu | INFO |
| ✓ | Thành công | INFO |
| ✗ | Lỗi | ERROR |
| ⏱️ | Đang chờ | INFO |
| ⚠️ | Cảnh báo | WARNING |

---

## 🛠️ Tình Huống Thường Gặp

### Tình Huống 1: Spinbox Bị Vô Hiệu Hóa (Grayed Out)

**Hiện Tượng:**
```
☐ Delay Trigger    [10.0 ms]
                   ↑
                   Màu xám, không thể click
```

**Nguyên Nhân:** Checkbox chưa được tích

**Giải Pháp:**
```
1. Tích checkbox ☑️
2. Spinbox sẽ được bật (màu bình thường)
```

### Tình Huống 2: Delay Không Được Áp Dụng

**Hiện Tượng:**
```
☑ Delay Trigger [10.0 ms]
(Ticked)
Nhưng camera trigger ngay, không delay
```

**Nguyên Nhân:** Camera không ở chế độ "trigger"

**Giải Pháp:**
```
1. Kiểm tra chế độ camera
2. Đặt camera ở chế độ "Trigger"
3. Retry trigger từ Pico
```

### Tình Huống 3: Giá Trị Spinbox Không Thay Đổi

**Hiện Tượng:**
```
Double-click spinbox, gõ giá trị, nhưng giá trị không đổi
```

**Nguyên Nhân:** Giá trị ngoài phạm vi (< 0 hoặc > 100)

**Giải Pháp:**
```
Phạm vi hợp lệ: 0.0 - 100.0 ms
Nếu gõ: 150 → Sẽ bị tự động điều chỉnh thành 100.0
Nếu gõ: -5  → Sẽ bị tự động điều chỉnh thành 0.0
```

### Tình Huống 4: Delay Quá Lâu

**Hiện Tượng:**
```
[100.0 ms] quá lâu, không muốn chờ lâu
```

**Giải Pháp:**
```
Giảm giá trị:
- Thay từ 100.0 ms → 50.0 ms
- Hoặc 50.0 ms → 25.0 ms
- Hoặc 25.0 ms → 10.0 ms
```

---

## 💡 Mẹo & Thủ Thuật

### Mẹo 1: Tìm Giá Trị Delay Tối Ưu

**Quy Trình:**
```
1. Bắt đầu với 0ms (không delay)
2. Nếu không tốt, tăng thêm 5ms
3. Thử: [5ms] → [10ms] → [15ms] → [20ms]
4. Khi được kết quả tốt, dừng
5. Giá trị đó là tối ưu
```

**Ví Dụ:**
```
[5ms]  - Trigger quá sớm → Ảnh xấu
[10ms] - Tốt hơn
[15ms] - Tốt nhất! ✓ ← Sử dụng giá trị này
[20ms] - Trigger muộn → Ảnh xấu
```

### Mẹo 2: Nhập Nhanh Giá Trị

**Cách 1: Double-click và gõ**
```
[5.0 ms] → Double-click → Xóa → Gõ "10" → Enter
```

**Cách 2: Dùng mũi tên**
```
[5.0 ms] → Click ▲ (tăng 0.1) → [5.1 ms]
[5.0 ms] → Click ▼ (giảm 0.1) → [4.9 ms]
```

**Cách 3: Scroll chuột**
```
Di chỉ trỏ lên spinbox, scroll up (tăng) hoặc down (giảm)
```

### Mẹo 3: Sử Dụng Log Để Debug

**Nếu trigger không hoạt động:**
```
1. Mở Console (xem log)
2. Tìm dòng "★ Detected trigger command"
3. Nếu không có → Pico không gửi trigger
4. Nếu có nhưng không trigger camera:
   - Kiểm tra "✓ Camera triggered"
   - Nếu không → Camera không ở chế độ trigger
```

### Mẹo 4: Ghi Chú Giá Trị Tốt

```
Nếu tìm được giá trị tối ưu, hãy ghi chú:
- Điều kiện: ánh sáng, vật thể, etc.
- Giá trị delay: 15.5 ms
- Kết quả: Ảnh rõ ràng ✓

Lần sau có điều kiện tương tự, sử dụng giá trị này
```

### Mẹo 5: Tắt Nhanh Để So Sánh

```
So sánh kết quả với/không delay:
1. ☑ Delay [15.0 ms] → Trigger → Xem ảnh
2. ☐ Delay [15.0 ms] → Trigger → Xem ảnh
3. So sánh ảnh, chọn cách tốt hơn
```

---

## 📊 Bảng Giá Trị Khuyến Nghị

| Tình Huống | Giá Trị | Lý Do |
|-----------|--------|------|
| Trigger ngay | 0.0 ms | Không delay |
| Bù cổng | 2-5 ms | Xử lý mạng |
| Đợi vật ổn định | 10-20 ms | Vật ổn định |
| Đợi ánh sáng | 20-50 ms | Cảm biến ổn định |
| Đợi độ ẩm/nhiệt | 50-100 ms | Môi trường ổn định |
| Quá an toàn | >100 ms | Không khuyến khích |

---

## ✅ Checklist Sử Dụng

```
□ Mở ứng dụng
□ Tab "Control"
□ Tích ☑️ "Delay Trigger"
□ Nhập giá trị ms
□ Đặt camera ở chế độ "Trigger"
□ Gửi trigger từ Pico
□ Xem Message List "[TRIGGER+Xms]"
□ Xem Console log
□ Kiểm tra ảnh chụp
□ Điều chỉnh giá trị nếu cần
□ Ghi chú giá trị tốt
```

---

## 🎉 Tóm Tắt

| Khía Cạnh | Chi Tiết |
|-----------|---------|
| **Chức Năng** | Thêm delay trước trigger camera |
| **Đơn Vị** | Millisecond (ms) |
| **Phạm Vi** | 0.0 - 100.0 ms |
| **Độ Chính Xác** | 0.1 ms |
| **Bật/Tắt** | Checkbox |
| **Nhập Giá Trị** | Spinbox |
| **Feedback** | Console log + Message list |
| **Khó Độ** | Rất dễ |

---

**Chúc bạn sử dụng tính năng delay trigger một cách hiệu quả!** 🚀

