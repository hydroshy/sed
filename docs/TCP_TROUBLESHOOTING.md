# 🐛 TCP Troubleshooting Guide

## 📋 Danh Sách Vấn Đề Phổ Biến

### Vấn Đề 1: Không Nhận Được Phản Hồi (🔴 FIXED)

#### Triệu Chứng
```
✓ Kết nối OK
✓ Gửi lệnh OK (TX: hiển thị)
❌ Không nhận phản hồi (RX: không hiển thị)
```

#### Nguyên Nhân
- Socket timeout quá ngắn (3s)
- Buffer không xử lý dữ liệu không có newline
- Thread daemon = True (mất dữ liệu)

#### Giải Pháp
```python
# 1. Tăng timeout
self._socket.settimeout(30)

# 2. Tắt daemon
self._monitor_thread.daemon = False

# 3. Thêm buffer timeout
if buffer and (time.time() - last_data_time) > 0.5:
    self._handle_message(buffer)
```

#### Kiểm Tra
```
Xem console có log "Raw data received" không
✓ Có → Dữ liệu đến
❌ Không → Lỗi kết nối
```

---

### Vấn Đề 2: Kết Nối Không Được

#### Triệu Chứng
```
❌ Status label: "Error: Connection refused"
❌ Không thể kết nối tới thiết bị
```

#### Nguyên Nhân
- IP sai
- Port sai
- Thiết bị không lắng nghe
- Firewall chặn
- Thiết bị chưa bật

#### Giải Pháp
```python
# 1. Kiểm tra IP/Port
telnet 192.168.1.100 5000

# 2. Kiểm tra thiết bị
ping 192.168.1.100

# 3. Xem log console để có chi tiết
logging.basicConfig(level=logging.DEBUG)
```

---

### Vấn Đề 3: Dữ Liệu Bị Cắt (Partial Data)

#### Triệu Chứng
```
TX: "PING\r\nPONG\r\n"
RX: "PING"
RX: "PONG"
❌ Một dòng hoặc nhiều ký tự bị mất
```

#### Nguyên Nhân
- Dữ liệu tới từng phần
- Buffer không đủ lớn
- Encoding error

#### Giải Pháp
```python
# 1. Tăng buffer size
data = self._socket.recv(4096)  # Từ 1024 → 4096

# 2. Xử lý dữ liệu từng phần
buffer += data.decode('utf-8')
while '\n' in buffer:
    line, buffer = buffer.split('\n', 1)
    self._handle_message(line)

# 3. Thêm error handling
try:
    decoded = data.decode('utf-8')
except UnicodeDecodeError:
    logging.error(f"Decode error: {data!r}")
```

---

### Vấn Đề 4: GUI Hang/Freeze

#### Triệu Chứng
```
❌ GUI không phản ứng
❌ Ứng dụng freeze
```

#### Nguyên Nhân
- recv() blocking main thread
- Signals không kết nối đúng
- GUI update từ thread sai

#### Giải Pháp
```python
# 1. Monitor socket trong thread riêng (đã có)
self._monitor_thread = threading.Thread(target=self._monitor_socket)

# 2. Emit signals từ thread (đã có)
self.message_received.emit(message)

# 3. Xử lý signal trong main thread
# PyQt tự xử lý, không cần lo
```

---

### Vấn Đề 5: Lỗi Unicode

#### Triệu Chứng
```
❌ "Unicode decode error"
❌ Dữ liệu biến thành ký tự lạ
```

#### Nguyên Nhân
- Dữ liệu là binary, không phải UTF-8
- Encoding không đúng

#### Giải Pháp
```python
# 1. Thử encoding khác
try:
    data.decode('utf-8')
except UnicodeDecodeError:
    data.decode('latin-1')
    # hoặc 'gbk', 'ascii', etc

# 2. Nếu binary, xử lý khác
if is_binary:
    hex_str = data.hex()
    self.message_received.emit(hex_str)
```

---

### Vấn Đề 6: Kết Nối Bị Đứt Giữa Chừng

#### Triệu Chứng
```
✓ Kết nối OK lúc đầu
✓ Gửi/nhận OK
❌ Sau 30 giây: "Connection closed"
```

#### Nguyên Nhân
- Timeout socket (30s)
- Thiết bị tự ngắt kết nối
- Network timeout

#### Giải Pháp
```python
# 1. Tăng timeout nếu cần
self._socket.settimeout(60)

# 2. Implement keep-alive
def _send_keep_alive(self):
    if self._connected:
        self.send_message("\n")  # Gửi newline để keep-alive

# 3. Reconnect tự động
if not self._connected:
    self.connect(self._current_ip, str(self._current_port))
```

---

### Vấn Đề 7: Dữ Liệu Không Có Newline

#### Triệu Chứng
```
❌ Thiết bị gửi dữ liệu không kết thúc bằng \n
❌ Dữ liệu tồn tại trong buffer không được emit
```

#### Nguyên Nhân
- Thiết bị không gửi newline
- Protocol không dùng newline

#### Giải Pháp
```python
# ✅ Đã fix: Thêm buffer timeout
if buffer and (time.time() - last_data_time) > 0.5:
    self._handle_message(buffer)
    buffer = ""

# Hoặc: Dùng delimiter khác
if '|' in buffer:
    line, buffer = buffer.split('|', 1)
    self._handle_message(line)
```

---

## 🔍 Debug Checklist

| Bước | Kiểm Tra | Cách Làm |
|------|----------|---------|
| 1 | Kết nối? | Xem status label (xanh/đỏ) |
| 2 | Gửi OK? | TX: hiển thị trong list |
| 3 | Nhận OK? | RX: hiển thị trong list |
| 4 | Log console? | `python run.py` và xem console |
| 5 | Network? | `ping` và `telnet` từ cmd |

---

## 📊 Debug Log Interpretation

### Log: Kết Nối Thành Công
```
Attempting to connect to 192.168.1.100:5000
Successfully connected to 192.168.1.100:5000
Monitor thread started
```

### Log: Nhận Dữ Liệu
```
Raw data received (10 bytes): b'PONG\r\n'
Decoded data: 'PONG\r\n'
Processing line from buffer: 'PONG'
_handle_message called with: 'PONG'
Emitting message_received signal: 'PONG'
_on_message_received called with: 'PONG'
Added message to list: RX: PONG
```

### Log: Lỗi Decode
```
Unicode decode error: 'utf-8' codec can't decode byte 0xff
Raw data: b'\xff\xfe\x00\x01'
```

---

## 🛠️ Công Cụ Debug

### 1. Telnet
```bash
telnet 192.168.1.100 5000
# Gõ lệnh và nhấn Enter
# Xem phản hồi
```

### 2. Netcat
```bash
nc -l 5000  # Listen
nc 192.168.1.100 5000  # Connect
```

### 3. Python Socket Test
```python
import socket
s = socket.socket()
s.connect(('192.168.1.100', 5000))
s.send(b'PING\n')
data = s.recv(1024)
print(data)
s.close()
```

### 4. Wireshark
- Capture network traffic
- Xem dữ liệu thực tế gửi/nhận

---

## 🎯 Giải Pháp Nhanh

### Dữ Liệu Đến Nhưng GUI Không Hiển Thị
```
→ Kiểm tra signals kết nối đúng chưa
→ Xem console có log không
→ Check message_list widget có None không
```

### GUI Không Nhận Dữ Liệu
```
→ Kiểm tra socket timeout (phải ≥ dữ liệu delay)
→ Check buffer timeout (0.5s)
→ Xem console có "Raw data received" không
```

### Kết Nối Nhưng Không Gửi/Nhận
```
→ Kiểm tra send_message() có error không
→ Xem socket connected không
→ Check port/IP đúng không
```

---

## ✅ Checklist Hoàn Chỉnh

- [x] Socket timeout: 30s
- [x] Thread daemon: False
- [x] Buffer timeout: 0.5s
- [x] Unicode handling: đúng
- [x] Logging: chi tiết
- [x] Signal: kết nối
- [x] Handler: cập nhật UI

---

**Nếu vẫn có vấn đề, kiểm tra console log để debug! 🔍**
