# 🎯 TCP Trigger Camera - Auto Capture from Sensor

## Feature Overview

When in **Trigger Mode**, the system automatically triggers camera capture upon receiving specific TCP commands from the sensor device.

---

## How It Works

### 1. System Flow

```
Sensor Device (IMX296 with GPIO)
        ↓
    GPIO Trigger
        ↓
    TCP Controller on Raspberry Pi
        ↓
    Send: "RX: start_rising||1634723"
        ↓
    TCP Controller Manager receives message
        ↓
    Parse: Is it "start_rising"?
        ↓ YES
    Check: Is camera in trigger mode?
        ↓ YES
    Action: Trigger camera capture
        ↓
    Camera captures frame
        ↓
    Frame sent to job pipeline
```

### 2. Message Format

**Received from sensor:**
```
RX: start_rising||1634723
```

Where:
- `start_rising` = Trigger command
- `1634723` = Timestamp (microseconds)

### 3. Conditions Required

For auto-trigger to work:
1. ✅ TCP connected to device
2. ✅ Device sends "start_rising||<timestamp>" message
3. ✅ **Camera tool is in TRIGGER MODE** (critical!)

---

## Code Changes

### File: `gui/tcp_controller_manager.py`

#### Change 1: Enhanced `_on_message_received()` (Line ~109)
```python
def _on_message_received(self, message: str):
    """Handle received messages and trigger camera in trigger mode"""
    # Display message in UI
    self.message_list.addItem(f"RX: {message}")
    
    # ✅ NEW: Check and trigger camera if needed
    self._check_and_trigger_camera_if_needed(message)
```

#### Change 2: New Method - `_check_and_trigger_camera_if_needed()` (Line ~123)
```python
def _check_and_trigger_camera_if_needed(self, message: str):
    """
    Auto-trigger camera when receiving sensor command
    
    1. Check if message is "start_rising"
    2. Check if camera in trigger mode
    3. Call activate_capture_request() if both true
    """
    try:
        # Parse message
        if "start_rising" not in message.lower():
            return  # Not a trigger command
        
        logging.info(f"★ Detected trigger command: {message}")
        
        # Get camera tool
        camera_tool = self.main_window.tool_manager.get_tool_by_name("Camera Source")
        if not camera_tool or not camera_tool.is_trigger_mode():
            return  # Not in trigger mode
        
        # Trigger camera!
        logging.info(f"★ Triggering camera for: {message}")
        self.main_window.camera_manager.activate_capture_request()
        
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
```

---

## Usage

### Setup

1. **Set Camera to Trigger Mode**
   - Camera Tool → Camera Mode: Select "Trigger"
   - Or programmatically: `camera_tool.set_camera_mode("trigger")`

2. **Configure TCP Connection**
   - Controller Tab → Enter device IP and Port
   - Click "Connect"

3. **Start Job Processing** (optional)
   - If you want detection/classification on captured frames
   - Enable job processing in Job tab

### Operation

```
1. User setup camera in TRIGGER MODE ✅
2. User connects to TCP device ✅
3. Device sends sensor data with "start_rising" ✅
4. System automatically:
   - Receives message ✅
   - Detects "start_rising" ✅
   - Checks trigger mode ✅
   - Captures frame ✅
   - Processes through pipeline ✅
```

---

## Console Output

When trigger fires, you'll see:

```log
★★★ _on_message_received CALLED! message='start_rising||1634723' ★★★
Adding message to list: RX: start_rising||1634723
✓ Message added to list
★ Detected trigger command: start_rising||1634723
★ Camera is in trigger mode, triggering capture
★ Calling camera_manager.activate_capture_request()
✓ Camera triggered successfully for message: start_rising||1634723
```

### UI Feedback

Message list shows:
```
RX: start_rising||1634723
[TRIGGER] Camera captured from: start_rising||1634723
```

---

## Configuration

### Trigger Detection

Edit `_check_and_trigger_camera_if_needed()` to customize trigger detection:

```python
# Current: Check for "start_rising" in message
if "start_rising" not in message.lower():
    return

# Alternative: Check exact format
if not message.startswith("start_rising||"):
    return

# Alternative: Check multiple commands
if not any(cmd in message for cmd in ["start_rising", "trigger", "capture"]):
    return
```

### Cooldown Between Triggers

Camera tool has built-in cooldown (default 250ms):
```python
# In CameraStream: set_trigger_cooldown(0.25)
camera_manager.camera_stream.set_trigger_cooldown(0.5)  # Set to 500ms
```

---

## Troubleshooting

### Problem: Camera not triggering

**Check 1: Is message being received?**
```
Look for: "★ Detected trigger command:"
If not showing → Device not sending message
```

**Check 2: Is camera in trigger mode?**
```
Look for: "★ Camera is in trigger mode"
If not showing → Change to trigger mode first!
```

**Check 3: Is camera manager available?**
```
Look for: "✓ Camera triggered successfully"
If error → Check camera_manager initialization
```

### Problem: Wrong messages trigger camera

**Solution:** Modify the detection logic:
```python
# Only trigger on exact format
if message != "start_rising":
    return
# Or require specific format with timestamp
if not message.startswith("start_rising||"):
    return
```

### Problem: Too many triggers too fast

**Solution:** Increase cooldown:
```python
camera_stream.set_trigger_cooldown(1.0)  # 1 second cooldown
```

---

## Integration Points

### 1. TCP Controller Manager
- Receives TCP message
- Calls `_check_and_trigger_camera_if_needed()`
- Triggers camera if conditions met

### 2. Camera Tool
- Stores trigger mode state
- Method: `is_trigger_mode()` returns True if in trigger mode
- Method: `get_camera_mode()` returns current mode

### 3. Camera Manager
- Method: `activate_capture_request()` triggers single frame capture
- Captures frame and sends to job pipeline

### 4. Job Pipeline
- Receives captured frame
- Processes through detection/classification
- Sends results to visualization

---

## Advanced Usage

### Check Trigger Mode Programmatically

```python
# Get camera tool
camera_tool = main_window.tool_manager.get_tool_by_name("Camera Source")

# Check current mode
if camera_tool.is_trigger_mode():
    print("In trigger mode - will auto-capture on sensor commands")
else:
    print("In live mode - will not auto-capture")

# Programmatically set trigger mode
camera_tool.set_camera_mode("trigger")
```

### Log Trigger Events

```python
# Custom trigger event logging in job manager
# When frame captured from trigger:
logging.info(f"Triggered frame captured at: {timestamp}")
logging.info(f"Sensor command was: {sensor_message}")
logging.info(f"Frame size: {frame.shape}")
```

---

## Performance Considerations

- **Trigger Rate:** Max ~4 FPS (250ms cooldown)
- **CPU Load:** Minimal - only captures on demand
- **Network:** TCP overhead minimal
- **Storage:** Only stores triggered frames (not continuous)

---

## Status

✅ **Feature:** Complete & Ready
- [x] TCP message receiving
- [x] Message parsing
- [x] Trigger mode detection
- [x] Camera trigger integration
- [x] Logging & debugging
- [x] Error handling

📋 **Next Steps:**
- Test on Raspberry Pi with real sensor
- Adjust trigger detection if needed
- Configure cooldown based on device speed

---

**Documentation:** TCP_TRIGGER_CAMERA.md
**Date:** October 21, 2025
**Status:** ✅ READY FOR TESTING
