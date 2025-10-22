# 🎨 Light Controller Architecture & Flow Diagram

## 📐 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GUI (PyQt5)                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  lightControllerTab (UI Tab)                           │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │ │
│  │  │ IP Input     │  │ Port Input   │  │  Connect   │  │ │
│  │  │ (UI element) │  │ (UI element) │  │  Button    │  │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘  │ │
│  │  ┌──────────────┐  ┌──────────────┐                   │ │
│  │  │   Status     │  │  Message     │                   │ │
│  │  │   Label      │  │  List        │                   │ │
│  │  └──────────────┘  └──────────────┘                   │ │
│  │  ┌──────────────┐  ┌──────────────┐                   │ │
│  │  │   Message    │  │    Send      │                   │ │
│  │  │   Input      │  │    Button    │                   │ │
│  │  └──────────────┘  └──────────────┘                   │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           ↑ Update UI
                           ↓ Button click
┌─────────────────────────────────────────────────────────────┐
│              TCPControllerManager                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ tcp_manager.setup_light_controller(...)               │ │
│  │                                                        │ │
│  │ Connects UI signals ↔ Light controller slots          │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           ↑ Signals
                           ↓ Method calls
┌─────────────────────────────────────────────────────────────┐
│         TCPLightController (controller/tcp_light...)        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ • connect(ip, port) → TCP socket connection           │ │
│  │ • send_message(msg) → Send command via socket         │ │
│  │ • _monitor_socket() → Background thread monitors Rx   │ │
│  │ • turn_on() → Send "on" command                       │ │
│  │ • turn_off() → Send "off" command                     │ │
│  │ • set_brightness(0-100) → Send "brightness:X" cmd    │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           ↑ TCP socket
                           ↓ TCP socket
┌─────────────────────────────────────────────────────────────┐
│              Light Hardware Device                          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ • Pico W / Arduino / ESP32 with LED/Lamp control      │ │
│  │ • Listens on TCP port                                 │ │
│  │ • Receives commands: on, off, brightness, etc.        │ │
│  │ • Sends back status: status:on, status:off, etc.      │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 📱 Communication Flow

### 1️⃣ **User Connects Light**

```
User clicks "Connect"
    ↓
GUI validates IP/Port
    ↓
tcp_manager._on_light_connect_button_clicked()
    ↓
light_controller.connect(ip, port)
    ↓
TCP socket created → Device connection attempted
    ↓
✓ Connected → Status label updates green "✓ Connected"
✗ Failed   → Status label updates red   "✗ Error: ..."
```

### 2️⃣ **User Sends Command**

```
User types "on" in message field
    ↓
User clicks "Send"
    ↓
tcp_manager._on_light_send_button_clicked()
    ↓
light_controller.send_message("on")
    ↓
TCP socket sends "on\n" to device
    ↓
Message added to history: "→ on"
Input field cleared
```

### 3️⃣ **Device Responds**

```
Device receives "on\n"
    ↓
Device turns on LED
    ↓
Device sends back "status:on\n"
    ↓
light_controller._monitor_socket() receives data
    ↓
_handle_message("status:on") processes response
    ↓
Signal emitted: message_received("status:on")
    ↓
UI updated: Message added to history "← status:on"
```

### 4️⃣ **Auto-Control in Camera Trigger** (Future)

```
Trigger received: "start_rising"
    ↓
delay_ms = 15ms (from spinbox)
    ↓
💡 light_controller.turn_on()
    ↓
"on\n" sent to light device
    ↓
time.sleep(15ms)
    ↓
camera.capture()  ← Camera captures WHILE light is ON
    ↓
💡 light_controller.turn_off()
    ↓
"off\n" sent to light device
    ↓
✓ Capture complete with proper illumination
```

---

## 🔄 Signal/Slot Connections

```
Light Controller                    UI Updates
────────────────────────────────────────────────

connection_status_changed ─→ _on_light_connection_changed()
                              └─→ Update status label
                              └─→ Enable/disable buttons
                              └─→ Change button text

message_received ──────────→ _on_light_message_received()
                              └─→ Add to message list
                              └─→ Auto-scroll list

light_status_changed ──────→ _on_light_status_changed()
                              └─→ Update light indicator
```

```
UI Button Clicks              Light Controller
────────────────────────────────────────────────

connectButtonClicked ──────→ _on_light_connect_button_clicked()
                              └─→ light_controller.connect()

sendButtonClicked ──────────→ _on_light_send_button_clicked()
                              └─→ light_controller.send_message()
```

---

## 💻 Class Hierarchy

```
QObject (PyQt5)
    ↑
    │ inherits
    │
TCPLightController
    ├─ Properties:
    │   ├─ _socket: TCP socket
    │   ├─ _connected: bool
    │   ├─ _current_ip: str
    │   ├─ _current_port: int
    │   ├─ _monitor_thread: Thread
    │   └─ _light_status: str
    │
    ├─ Signals (Qt):
    │   ├─ connection_status_changed(bool, str)
    │   ├─ message_received(str)
    │   └─ light_status_changed(str)
    │
    └─ Methods:
        ├─ connect(ip, port) → bool
        ├─ send_message(msg) → bool
        ├─ turn_on() → bool
        ├─ turn_off() → bool
        ├─ toggle() → bool
        ├─ set_brightness(level) → bool
        ├─ _monitor_socket() [Thread]
        ├─ _handle_message(msg) [Private]
        └─ _disconnect() [Private]
```

---

## 🔌 Network Protocol

```
┌─────────────────────────────────────────┐
│      Pi ↔ Light Device (TCP/IP)         │
├─────────────────────────────────────────┤
│ Default Port: User-specified            │
│ Timeout: 5 seconds                      │
│ Buffer: 4096 bytes                      │
│ Monitor: Background thread              │
└─────────────────────────────────────────┘

Messages (Pi → Device):
─────────────────────────
on\n                    # Turn on
off\n                   # Turn off
toggle\n                # Toggle
brightness:50\n         # Set brightness to 50%
brightness:100\n        # Set brightness to 100%
brightness:0\n          # Turn off (via brightness)

Responses (Device → Pi):
────────────────────────
status:on\n             # Light is on
status:off\n            # Light is off
brightness:75\n         # Current brightness is 75%
error:...\n             # Error message
```

---

## ⏱️ Timing Diagram

```
Timeline: Camera Trigger with Light Control
═════════════════════════════════════════════

t=0ms    User sends trigger from Pico
         └─→ "start_rising" received

t=0ms    delay_trigger checks enabled → YES (15ms)
         └─→ light_controller.turn_on()

t=1ms    Light ON command sent via TCP
         └─→ Message in queue

t=5ms    Pi network layer sends data
         └─→ Light device receives "on\n"

t=6ms    Light device processes
         └─→ LED turns on (hardware latency ~1ms)

t=7ms    Light device confirms "status:on"

t=15ms   delay_trigger: time.sleep(15ms) expires
         └─→ time to capture!

t=15ms   camera.capture() called
         └─→ ✓ Camera captures WHILE light is ON

t=16ms   light_controller.turn_off()
         └─→ "off\n" sent

t=20ms   Light device receives "off\n"
         └─→ LED turns off

t=21ms   Everything complete
         └─→ Frame saved with proper lighting ✓
```

---

## 📊 Comparison: With vs Without Light Control

### ❌ Without Light Control (Current)
```
Trigger → (delay 15ms) → Camera Captures → Light On
                         ↑                  ↑
                    Camera captures       Light too late!
                    DARK image ✗
```

### ✅ With Light Control (New)
```
Trigger → Light ON → (delay 15ms) → Camera Captures → Light Off
                     ↑ Light        ↑
                     Stabilizes     Captures BRIGHT image ✓
```

---

## 🧵 Threading Model

```
Main Thread (GUI)
    │
    ├─ User interaction (clicks, text input)
    │
    ├─ Signal emissions from TCP light controller
    │
    └─ UI updates

Background Thread (Monitor)
    │
    ├─ Created when connecting
    ├─ Continuously monitors socket for incoming data
    ├─ Calls _handle_message() for each received message
    ├─ Emits signals (cross-thread safe with Qt)
    │
    └─ Destroyed when disconnecting
```

---

## 🚦 State Machine

```
                    ┌──────────────────┐
                    │ DISCONNECTED     │
                    │ is_connected=F   │
                    └──────────────────┘
                            ↑
                            │ connect() failure
                            │ disconnect() called
                            │ connection lost
                            │
                    ┌──────────────────┐
              ┌────→│ CONNECTED        │←────┐
              │     │ is_connected=T   │     │
              │     └──────────────────┘     │
              │             ↑                │
              │             │                │
        connect()      send_message()    turn_on()
     success           successful        turn_off()
                                         toggle()
```

---

## 🎯 Integration Points

```
File: tcp_controller_manager.py
├─ Import TCPLightController
├─ Initialize light_controller instance
├─ setup_light_controller() method
├─ Signal handlers:
│  ├─ _on_light_connection_changed()
│  ├─ _on_light_message_received()
│  └─ _on_light_status_changed()
├─ Button handlers:
│  ├─ _on_light_connect_button_clicked()
│  └─ _on_light_send_button_clicked()
└─ UI state management:
   └─ _update_light_button_states()

File: main.py
└─ Call setup_light_controller() with UI elements

File: Camera Trigger Logic (Future)
├─ Check light_controller.is_connected
├─ Call light_controller.turn_on() before delay
├─ Call light_controller.turn_off() after capture
└─ Update logging with 💡 emoji indicators
```

---

## ✅ Summary

1. **Architecture:** Similar to existing TCP controller, but optimized for light
2. **Communication:** TCP/IP with simple text protocol (on, off, brightness:X)
3. **Threading:** Background monitor thread for responsive UI
4. **Integration:** 3 simple steps (import, init, setup)
5. **Usage:** Turn on → Delay → Capture → Turn off
6. **Protocol:** All commands end with `\n`
7. **Status Tracking:** Light status synced with device
8. **Future:** Can integrate with camera trigger workflow for automatic lighting
