# Double Trigger Click Fix

## Problem
When trigger button was pressed on Raspberry Pi, it detected as 2 clicks, causing:
- 2 jobs executed per single button press
- Job pipeline ran twice  
- NG/OK evaluation happened twice
- System detected rapid trigger events

## Root Cause
The trigger button remained **enabled during processing**. On the Raspberry Pi with touchscreen/mouse input:
- User clicks trigger
- Job processing starts (takes ~250ms with delay)
- Button is still enabled
- Any input noise or double-tap gets registered as second click
- Second click executes same flow again

## Solution Implemented

### Before (Vulnerable):
```python
if current_mode == 'trigger' and button_is_enabled:
    # Process trigger (takes ~250ms)
    self._trigger_capturing = True
    self.activate_capture_request()
    time.sleep(0.2)
    self._trigger_capturing = False
    # Button stays ENABLED during entire process!
```

### After (Fixed):
```python
if current_mode == 'trigger' and button_is_enabled:
    # DISABLE BUTTON IMMEDIATELY
    if self.trigger_camera_btn:
        self.trigger_camera_btn.setEnabled(False)
        self.trigger_camera_btn.repaint()
    
    # Process trigger (takes ~250ms)
    self._trigger_capturing = True
    self.activate_capture_request()
    time.sleep(0.2)
    self._trigger_capturing = False
    
    # RE-ENABLE BUTTON AFTER PROCESSING
    if self.trigger_camera_btn:
        self.trigger_camera_btn.setEnabled(True)
        self.trigger_camera_btn.repaint()
```

##Effect

**Timeline Before Fix:**
```
T=0ms    : User clicks trigger button
T=0ms    : Button handler called, button STILL ENABLED
T=~50ms  : Noise/ghost input detected on touchscreen
T=~50ms  : Button click handler called AGAIN (button still enabled)
T=250ms  : First job finishes
T=300ms  : Second job finishes
Result   : 2 jobs executed, user only clicked once
```

**Timeline After Fix:**
```
T=0ms    : User clicks trigger button
T=0ms    : Button handler called
T=0ms    : Button IMMEDIATELY DISABLED (repaint)
T=~50ms  : Noise/ghost input on touchscreen - REJECTED (button disabled)
T=250ms  : First job finishes
T=250ms  : Button RE-ENABLED
Result   : 1 job executed, user only clicked once
```

## Files Modified
- `gui/camera_manager.py` - `on_trigger_camera_clicked()` method
  - Added button disable before processing
  - Added button re-enable after processing

## Testing
Expected behavior on Raspberry Pi:
1. Click trigger button once
2. Button becomes grayed out / disabled
3. Wait ~250ms for processing
4. Button re-enables
5. Only 1 job executed

If user clicks fast or double-taps during processing:
- Second click is ignored (button disabled)
- No double execution
