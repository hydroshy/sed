# Visual Architecture - Light Controller Components Connection

## 🎨 Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LIGHT CONTROLLER ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────────────────┘

                              mainUI.ui
                                  │
                  ┌───────────────┼───────────────┐
                  │               │               │
              palettePage    otherPages    lightControllerTab ✨
                  │                               │
            ┌─────┴────┐                    ┌────┴────┐
            │           │                   │         │
       paletteTab   ...                 7 Components:
            │           │              │   
       ┌────┼───┐        │          ┌──┘
       │    │   │        │          │
   Tab0 Tab1 ... Tab_N   │      Component Widgets
       │   │              │      ├─ ipLineEditLightController
       │ controllerTab    │      ├─ portLineEditLightController
       │   │              │      ├─ connectButtonLightController
       │ TCP widgets      │      ├─ statusLabelLightController
       │                  │      ├─ msgListWidgetLightController
       └───────────────────┘      ├─ msgLineEditLightController
                                  └─ sendButtonLightController


                          Application Startup
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
           main.py          MainWindow.__init__()  
                │            _find_widgets()
                │                 │
                │        ┌────────┼────────┐
                │        │                 │
                │    Search TCP          Search Light ✨
                │    Widgets ✓            Widgets ✓
                │        │                 │
                │        └────────┬────────┘
                │                 │
                │          _setup_tcp_controller()
                │                 │
                │        ┌────────┼────────┐
                │        │                 │
                │    Setup TCP ✓      Setup Light ✨
                │    Controller          Controller
                │        │                 │
                └────────┼─────────────────┘
                         │
                    ✓ Application Ready
                         │
        ┌────────────────┼────────────────┐
        │                │                │
     Tab1 (TCP)       Tab2 (Light) ✨    Others
        │                │
    Connected to ─────────► Connected to ✓
    _on_connection_status    _on_light_connection_status


Signal Connection Chain (Example: Connect Button)
═══════════════════════════════════════════════════════════════════════════════

    connectButtonLightController
           │ (QPushButton)
           │
      .clicked signal ◄────────────────────────────────────┐
           │                                               │
           │ emits                                          │
           ├──────────────────────────────────────────────┐│
           │                                              ││
    _on_light_connect_click()   ◄───────── .connect() ──┘│
    (TCPControllerManager)                               │
           │                                              │
      Validates IP/Port                                   │
           │                                              │
      light_controller.connect()                          │
           │                                              │
      TCP Connection Attempt                              │
           │                                              │
      light_controller.connection_status_changed          │
      signal emitted                                      │
           │                                              │
    _on_light_connection_status()  ◄─ .connect() ────────┘
    (TCPControllerManager)
           │
      Update statusLabelLightController (green/red)
           │
      Add message to msgListWidgetLightController
           │
      Update button states
           │
           ▼ ✓ Connection Status Updated on UI


Component State Management
═══════════════════════════════════════════════════════════════════════════════

    ┌──────────────────────────────────────────────────┐
    │           Initial State (Disconnected)            │
    ├──────────────────────────────────────────────────┤
    │ ipLineEditLightController          → ENABLED      │
    │ portLineEditLightController        → ENABLED      │
    │ connectButtonLightController       → ENABLED      │
    │   ├─ Text: "Connect"                             │
    │   └─ Clicked Signal Connected: YES                │
    │ statusLabelLightController         → RED, "Disc"  │
    │ msgListWidgetLightController       → ENABLED      │
    │   └─ Content: (empty)                             │
    │ msgLineEditLightController         → DISABLED      │
    │ sendButtonLightController          → DISABLED      │
    └──────────────────────────────────────────────────┘
                        │
                User enters IP/port
                        │
                User clicks Connect
                        │
                    ▼ (TCP connection successful)
                        │
    ┌──────────────────────────────────────────────────┐
    │          Connected State (TCP Link Active)        │
    ├──────────────────────────────────────────────────┤
    │ ipLineEditLightController          → DISABLED      │
    │ portLineEditLightController        → DISABLED      │
    │ connectButtonLightController       → ENABLED      │
    │   ├─ Text: "Disconnect"                          │
    │   └─ Clicked Signal Connected: YES                │
    │ statusLabelLightController         → GREEN, "OK" │
    │ msgListWidgetLightController       → ENABLED      │
    │   └─ Content: (messages appear here)             │
    │ msgLineEditLightController         → ENABLED      │
    │ sendButtonLightController          → ENABLED      │
    └──────────────────────────────────────────────────┘
                        │
                User sends message
                        │
                    ▼ (message sent & received)
                        │
    ┌──────────────────────────────────────────────────┐
    │        Connected + Message History State          │
    ├──────────────────────────────────────────────────┤
    │ msgListWidgetLightController       → ENABLED      │
    │   └─ Content:                                     │
    │       • "Status: Connection established"          │
    │       • "→ on"                  (sent)             │
    │       • "← OK"                  (received)         │
    │       • "→ brightness:75"       (sent)             │
    │       • "← brightness set"      (received)         │
    │       ...                                          │
    └──────────────────────────────────────────────────┘


UI Component Hierarchy in mainUI.ui
═══════════════════════════════════════════════════════════════════════════════

centralwidget
 └─ mainFrame
     └─ horizontalLayoutWidget
         └─ mainLayout
             ├─ cameraLayout (left side)
             │   └─ cameraFrame (live view)
             │
             └─ settingLayout (right side)
                 └─ settingStackedWidget
                     ├─ palettePage
                     │   └─ paletteTab
                     │       ├─ jobTab
                     │       ├─ controllerTab (TCP)
                     │       │   ├─ ipLineEdit
                     │       │   ├─ portLineEdit
                     │       │   ├─ connectButton
                     │       │   ├─ statusLabel
                     │       │   ├─ messageListWidget
                     │       │   ├─ messageLineEdit
                     │       │   ├─ sendButton
                     │       │   ├─ delayTriggerCheckBox
                     │       │   └─ delayTriggerTime
                     │       │
                     │       └─ lightControllerTab ✨ NEW
                     │           ├─ ipLineEditLightController
                     │           ├─ portLineEditLightController
                     │           ├─ connectButtonLightController
                     │           ├─ statusLabelLightController
                     │           ├─ msgListWidgetLightController
                     │           ├─ msgLineEditLightController
                     │           └─ sendButtonLightController
                     │
                     ├─ cameraSettingPage
                     ├─ detectSettingPage
                     ├─ saveImagePage
                     └─ classificationSettingPage


Python Object Hierarchy After Initialization
═══════════════════════════════════════════════════════════════════════════════

MainWindow (gui/main_window.py)
 ├─ self.tcp_controller (TCPControllerManager)
 │   ├─ self.tcp_controller.tcp_controller (TCPController)
 │   │   └─ signals: connection_status_changed, message_received
 │   │
 │   └─ self.tcp_controller.light_controller ✨ (TCPLightController)
 │       ├─ signals: connection_status_changed, message_received, light_status_changed
 │       └─ methods: connect(), disconnect(), turn_on(), off(), set_brightness()
 │
 ├─ self.ipLineEditLightController ✨ (QLineEdit)
 │   └─ connected to: state management by _update_light_button_states()
 │
 ├─ self.portLineEditLightController ✨ (QLineEdit)
 │   └─ connected to: state management by _update_light_button_states()
 │
 ├─ self.connectButtonLightController ✨ (QPushButton)
 │   └─ clicked signal → _on_light_connect_click()
 │
 ├─ self.statusLabelLightController ✨ (QLabel)
 │   └─ updated by: _on_light_connection_status()
 │
 ├─ self.msgListWidgetLightController ✨ (QListWidget)
 │   └─ updated by: _on_light_message_received(), _on_light_connection_status()
 │
 ├─ self.msgLineEditLightController ✨ (QLineEdit)
 │   ├─ returnPressed signal → _on_light_send_click()
 │   └─ connected to: state management by _update_light_button_states()
 │
 └─ self.sendButtonLightController ✨ (QPushButton)
     └─ clicked signal → _on_light_send_click()


Handler Method Relationships
═══════════════════════════════════════════════════════════════════════════════

TCPControllerManager Methods:

setup_light_controller()
 ├─ Receives all 7 UI components
 ├─ Stores as instance variables
 ├─ Initializes UI state (red, disconnected)
 ├─ Connects signals:
 │   ├─ light_controller.connection_status_changed → _on_light_connection_status
 │   ├─ light_controller.message_received → _on_light_message_received
 │   ├─ light_controller.light_status_changed → _on_light_status_changed
 │   ├─ connectButton.clicked → _on_light_connect_click
 │   ├─ sendButton.clicked → _on_light_send_click
 │   └─ messageLineEdit.returnPressed → _on_light_send_click
 └─ Ready for user interaction

_on_light_connect_click()
 ├─ Get IP and port from UI
 ├─ Validate not empty
 ├─ Call light_controller.connect(ip, port)
 └─ Triggers connection_status_changed signal

_on_light_send_click()
 ├─ Get message from msgLineEdit
 ├─ Call light_controller.send_message(message)
 ├─ Add "→ message" to msgListWidget
 └─ Clear message input

_on_light_connection_status()
 ├─ Update statusLabel (color + text)
 ├─ Update button states
 ├─ Add status message to msgListWidget
 └─ Scroll to bottom

_on_light_message_received()
 ├─ Receive message from light_controller
 ├─ Add "← message" to msgListWidget
 └─ Scroll to bottom

_on_light_status_changed()
 └─ Log status changes

_update_light_button_states()
 ├─ Enable/disable ipEdit and portEdit (disabled when connected)
 ├─ Update connectButton text ("Connect" / "Disconnect")
 ├─ Enable/disable msgLineEdit and sendButton (only when connected)
 └─ Called after connection state changes


Success Criteria Verification Flowchart
═══════════════════════════════════════════════════════════════════════════════

Start Application
      │
      ▼
┌─────────────────────┐
│ Component Discovery │
│ (by _find_widgets)  │
└─────────────────────┘
      │
      ├─ lightControllerTab found? ──NO──> Warn & Continue
      │                                      (Tab still visible)
      │
      └─ YES ◄──────────────┐
             │              │
      Find all 7        Log Success
      components        "💡 Found..."
             │
      ┌──────┴──────┐
      │  All Found? │
      │             │
      └─ YES        └─ SOME MISSING──> Warn & Continue
         │                               (Partial setup)
         │
         ▼
┌─────────────────────────┐
│ Component Setup         │
│ (by _setup_tcp_controller)│
└─────────────────────────┘
         │
      Call setup_light_controller()
         │
         ▼
   ┌──────────────────────┐
   │ Connect All Signals  │
   │ & Initialize UI      │
   └──────────────────────┘
         │
         ├─ IP field: Enabled ✓
         ├─ Port field: Enabled ✓
         ├─ Connect button: Enabled ✓
         ├─ Status label: Red ✓
         ├─ Message list: Enabled ✓
         ├─ Message input: Disabled ✓
         ├─ Send button: Disabled ✓
         │
         ▼
   ┌──────────────────────┐
   │ ✅ READY TO USE       │
   │ Light Tab Working!   │
   └──────────────────────┘
         │
   User can now:
   ├─ Enter IP & port
   ├─ Click Connect
   ├─ See status updates
   ├─ Send messages
   └─ Receive responses
```

---

## 📌 Key Points

✅ **All 7 components discovered and connected**
✅ **Proper state management (enabled/disabled)**
✅ **Signal-slot connections established**
✅ **Error handling for edge cases**
✅ **Logging with 💡 indicators**
✅ **Thread-safe Qt signals used**
✅ **Follows existing TCP pattern**
✅ **Ready for production use**
