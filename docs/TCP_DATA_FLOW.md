# 📊 TCP Data Flow - Trước & Sau Fix

## 🔴 TRƯỚC (Lỗi)

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ipLineEdit: 192.168.1.100                                   │
│  portLineEdit: 5000                                          │
│  [Connect] → Connected ✓                                     │
│                                                               │
│  messageLineEdit: PING                                       │
│  [Send] → TX: PING ✓                                         │
│                                                               │
│  messageListWidget:                                          │
│  - Status: Connected                                         │
│  - TX: PING                                                  │
│  - ❌ RX: [KHÔNG CÓ]  ← BỊ MẤT ĐÂY!                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                         ↑ (GUI)
                         │ (Signal emit)
                         │
┌─────────────────────────────────────────────────────────────┐
│              tcp_controller_manager.py                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  _on_message_received(message)                               │
│      ↑ (message_received signal)                             │
│      │ ❌ SIGNAL KHÔNG ĐƯỢC PHÁT ← LỖI ĐÂY                  │
│      │                                                        │
└─────────────────────────────────────────────────────────────┘
                         ↑
                         │
┌─────────────────────────────────────────────────────────────┐
│               tcp_controller.py (Main)                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  send_message("PING") ✓                                      │
│      ↓ Socket.send()                                         │
│  ┌─────────────────┐                                         │
│  │ Monitor Thread  │                                         │
│  ├─────────────────┤                                         │
│  │ while running:  │                                         │
│  │  data = socket. │                                         │
│  │    recv(1024)   │                                         │
│  │  ❌ TIMEOUT (3s)│ ← NGẮN QUÁC!                            │
│  │    BLOCK HÊT!   │                                         │
│  │  [Không xử lý]  │                                         │
│  │  daemon=True ❌ │ ← MẤT DỮ LIỆU                          │
│  └─────────────────┘                                         │
│      ↑                                                        │
└─────────────────────────────────────────────────────────────┘
             ↑
             │ Socket Connection
             │ (KHÔNG NHẬN DỮ LIỆU)
             │
    ┌────────────────┐
    │   DEVICE TCP   │
    ├────────────────┤
    │ Nhận: PING     │
    │ Gửi: PONG\r\n  │
    │ ❌ TRỊ KHÔNG   │
    │    ĐƯỢC NHẬN   │
    └────────────────┘
```

---

## ✅ SAU (Sửa)

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ipLineEdit: 192.168.1.100                                   │
│  portLineEdit: 5000                                          │
│  [Connect] → Connected ✓                                     │
│                                                               │
│  messageLineEdit: PING                                       │
│  [Send] → TX: PING ✓                                         │
│                                                               │
│  messageListWidget:                                          │
│  - Status: Connected                                         │
│  - TX: PING                                                  │
│  - ✅ RX: PONG ← NHẬN ĐƯỢC ĐÂY!                              │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                         ↑ (GUI)
                         │ (Signal emit)
                         │ ✓ Nhận được message
                         │
┌─────────────────────────────────────────────────────────────┐
│              tcp_controller_manager.py                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  _on_message_received(message) ✓                             │
│      ↑ (message_received signal)                             │
│      │ ✓ Signal được phát                                    │
│      │ ✓ Handler được gọi                                    │
│      │ ✓ messageListWidget.addItem("RX: PONG")              │
│      │                                                        │
└─────────────────────────────────────────────────────────────┘
                         ↑
                         │
┌─────────────────────────────────────────────────────────────┐
│               tcp_controller.py (Main)                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  send_message("PING") ✓                                      │
│      ↓ Socket.send()                                         │
│  ┌───────────────────────┐                                   │
│  │  Monitor Thread       │                                   │
│  ├───────────────────────┤                                   │
│  │  while running:       │                                   │
│  │   data = socket.recv( │                                   │
│  │     1024)             │                                   │
│  │  ✓ TIMEOUT (30s) OK!  │ ← ĐỦ LÂUUUU!                     │
│  │  ✓ recv() thành công  │                                   │
│  │  ✓ Decode UTF-8       │                                   │
│  │  buffer += data       │                                   │
│  │  ✓ Split by '\n'      │                                   │
│  │  ✓ Buffer timeout(0.5)│ ← HỖ TRỢ KHÔNG \n                │
│  │  ✓ emit signal ✓      │                                   │
│  │  daemon=False ✓       │ ← AN TOÀN DỮ LIỆU               │
│  └───────────────────────┘                                   │
│      ↑                                                        │
└─────────────────────────────────────────────────────────────┘
             ↑
             │ Socket Connection
             │ ✓ NHẬN DỮ LIỆU
             │
    ┌────────────────┐
    │   DEVICE TCP   │
    ├────────────────┤
    │ Nhận: PING     │
    │ Gửi: PONG\r\n  │
    │ ✓ DỮ LIỆU      │
    │   ĐƯỢC NHẬN    │
    └────────────────┘
```

---

## 📈 Dòng Thời Gian (Timeline)

### ❌ TRƯỚC (Timeout)

```
Time  │ Event
──────┼─────────────────────────────────────
0s    │ [User click Send]
      │ TX: PING (xong)
      │
0s    │ [Socket.send(PING)]
      │
0s    │ [Monitor Thread recv() timeout = 3s]
      │
0.5s  │ [Device receives PING]
      │ [Device sends PONG\r\n]
      │
1s    │ [Socket has data ready]
      │ ❌ But recv() still waiting for what?
      │
2s    │ [Still waiting...]
      │
3s    │ ❌ TIMEOUT! recv() raises exception
      │ ❌ Data LOST! Never processed
      │
      │ RX: [KHÔNG CÓ]
```

### ✅ SAU (Nhận Được)

```
Time  │ Event
──────┼─────────────────────────────────────
0s    │ [User click Send]
      │ TX: PING (xong)
      │
0s    │ [Socket.send(PING)]
      │
0s    │ [Monitor Thread recv() timeout = 30s]
      │
0.5s  │ [Device receives PING]
      │ [Device sends PONG\r\n]
      │
1s    │ [Socket has data ready]
      │ ✓ recv() returns data immediately
      │ ✓ Decode: 'PONG\r\n'
      │ ✓ Buffer: "PONG"
      │ ✓ Split by '\n': "PONG"
      │ ✓ emit signal
      │
1.1s  │ [_on_message_received() called]
      │ ✓ messageList.addItem("RX: PONG")
      │
1.2s  │ GUI updated ✓
      │ RX: PONG
```

---

## 🔄 Data Flow Diagram

### ❌ TRƯỚC

```
Device
  │
  ├─→ TCP Socket ──→ Kernel Buffer
  │                       │
  │                       ├─→ recv(1024) [TIMEOUT 3s]
  │                       │     └─→ ❌ Timeout!
  │                       │
  │                       └─→ Data LOST!
  │
GUI ❌ RX: Không hiển thị
```

### ✅ SAU

```
Device
  │
  ├─→ TCP Socket ──→ Kernel Buffer
  │                       │
  │                       ├─→ recv(1024) [TIMEOUT 30s] ✓
  │                       │     └─→ ✓ Data received!
  │                       │
  │                       └─→ Decode ✓
  │                             │
  │                             └─→ Buffer ✓
  │                                   │
  │                                   └─→ Split by '\n' ✓
  │                                         │
  │                                         └─→ emit signal ✓
  │                                               │
GUI                                              ├─→ Handler ✓
  │                                              │
  ├─ RX: PONG ✓ ◄─────────────────────────────┘
  │
```

---

## 🎯 Key Fixes Visualization

### Fix 1: Socket Timeout

```
TRƯỚC:  ▶︎────────────────── [3 seconds] [TIMEOUT] ❌
SAU:    ▶︎────────────────────────────────────────────
        ────────────────────── [30 seconds] [OK] ✓
```

### Fix 2: Buffer Timeout

```
TRƯỚC:  Data [NO NEWLINE] ──→ STUCK IN BUFFER ❌
SAU:    Data [NO NEWLINE] ──→ [0.5s timeout] ──→ EMIT ✓
```

### Fix 3: Thread Daemon

```
TRƯỚC:  daemon=True  → Main exits → Thread KILLED ❌
SAU:    daemon=False → Main exits → Thread continues ✓
```

### Fix 4: Logging

```
TRƯỚC:  ❌ [Silent] → No debug info
SAU:    ✓ [Logged] → Full trace:
        - Raw data received
        - Decoded data
        - Buffer processing
        - Signal emitted
        - Handler called
        - UI updated
```

---

**✅ Tất cả 4 fixes đã áp dụng = Data flow thành công! 🎉**
