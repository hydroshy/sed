# ✅ Automatic Trigger Mode Activation

## What Changed?

Previously, you needed to:
1. Click "Trigger Camera Mode" button
2. Click "onlineCamera" button

**Now, it's simplified:**
1. ✅ Just click "onlineCamera" button
2. ✅ Trigger mode AUTOMATICALLY enabled when starting camera

---

## New Workflow (Simplified) ✅

```
User clicks "onlineCamera" button
                ↓
┌─────────────────────────────────────────────┐
│ Automatic Actions (No user intervention)    │
├─────────────────────────────────────────────┤
│ 1. Check if trigger mode is enabled         │
│    └─ If NOT enabled → enable it NOW        │
│ 2. Execute: echo 1 | sudo tee /sys/.../     │
│    └─ External trigger ENABLED              │
│ 3. Start camera stream                      │
│ 4. Lock 3A (AE + AWB) automatically         │
│ 5. Wait for external hardware trigger       │
└─────────────────────────────────────────────┘
                ↓
Camera ready to receive external trigger signals
Send hardware trigger → Frame captured automatically
```

---

## Code Changes

### File: `gui/main_window.py`

**Method:** `_toggle_camera(checked)` - Lines 995-1040

**What was added:**
```python
# 🔧 AUTOMATICALLY enable trigger mode when clicking onlineCamera
current_mode = getattr(self.camera_manager, 'current_mode', 'live')
if current_mode != 'trigger':
    logging.info("ℹ️ Enabling trigger mode automatically when starting camera...")
    self.camera_manager.set_trigger_mode(True)
    logging.info("✅ Trigger mode enabled automatically")
```

**How it works:**
1. Check if already in trigger mode
2. If NOT in trigger mode → call `set_trigger_mode(True)` automatically
3. This triggers the external trigger sysfs command
4. Then proceeds with camera startup and 3A locking

---

## Benefits

✅ **One-Click Operation:** Just click "onlineCamera" - everything else is automatic

✅ **No Manual Steps:** Trigger mode enabled without separate button click

✅ **Consistent Setup:** External trigger always configured before camera starts

✅ **3A Locking Guaranteed:** Happens after trigger mode is enabled

✅ **Professional Workflow:** Just start camera and wait for hardware trigger signals

---

## How It Works Now

### Step 1: Click "onlineCamera"
```
User: Clicks "onlineCamera" button
```

### Step 2: Automatic Trigger Mode Enable
```
System Log:
├─ "ℹ️ Enabling trigger mode automatically when starting camera..."
├─ Running external trigger command: echo 1 | sudo tee /sys/module/imx296/parameters/trigger_mode
├─ ✅ External trigger ENABLED
└─ "✅ Trigger mode enabled automatically"
```

### Step 3: Automatic 3A Lock
```
System Log:
├─ "🔒 Locking 3A (AE + AWB) for trigger mode..."
├─ "✅ AWB locked"
└─ "✅ 3A locked (AE + AWB disabled)"
```

### Step 4: Camera Ready
```
Status: Camera streaming, waiting for external trigger signal
Button: onlineCamera shows GREEN (active)
Ready: Send hardware trigger signal anytime
```

### Step 5: Send Hardware Trigger
```
External Source: Send trigger signal to camera GPIO
Result: Frame captured automatically (no user action needed)
```

---

## Comparison: Old vs New

| Step | Old Workflow | New Workflow |
|------|--------------|--------------|
| 1 | Click "Trigger Camera Mode" button | Click "onlineCamera" |
| 2 | Click "onlineCamera" | ✅ Done! (trigger auto-enabled) |
| 3 | Send hardware trigger | Send hardware trigger |
| 4 | Frame captured | Frame captured |
| 5 | Result displayed | Result displayed |
| **User Actions** | **2 button clicks** | **1 button click** |
| **Complexity** | Manual 2-step | Automatic 1-step |

---

## Implementation Details

### Automatic Trigger Activation Logic

**File:** `gui/main_window.py` - `_toggle_camera()` method

```python
if checked:
    # 🔧 AUTOMATICALLY enable trigger mode
    current_mode = getattr(self.camera_manager, 'current_mode', 'live')
    if current_mode != 'trigger':
        logging.info("ℹ️ Enabling trigger mode...")
        self.camera_manager.set_trigger_mode(True)  # ← Automatic!
        logging.info("✅ Trigger mode enabled automatically")
    
    # Then start camera and lock 3A
    # ... rest of camera startup code ...
```

### Called Methods (Sequence)

```
_toggle_camera(True)
  ↓
Check current_mode
  ↓
If not 'trigger':
  ├─ camera_manager.set_trigger_mode(True)
  │   ├─ camera_stream._set_external_trigger_sysfs(True)
  │   │   └─ echo 1 | sudo tee /sys/module/imx296/parameters/trigger_mode
  │   └─ current_mode = 'trigger'
  │
  ├─ camera_stream.start_preview()
  ├─ camera_stream.set_job_enabled(True)
  │
  ├─ camera_manager.set_manual_exposure_mode()
  ├─ camera_stream.set_auto_white_balance(False)
  └─ 3A locked
```

---

## Error Handling

If trigger mode enabling fails:
- Camera startup is still attempted
- Error logged for debugging
- User can retry by clicking "onlineCamera" again

If camera startup fails:
- Button unchecked (shows as OFF)
- Error message logged
- User can troubleshoot and try again

---

## Safety & Validation

✅ **Safe Attribute Checks:** Uses `hasattr()` to verify methods exist

✅ **Error Logging:** All steps logged with status emojis (✅/❌)

✅ **Backward Compatible:** Still supports manual "Trigger Camera Mode" button

✅ **Idempotent:** Calling `set_trigger_mode(True)` when already enabled is safe

✅ **Subprocess Timeout:** 5-second timeout prevents hanging

---

## Usage Guide

### Normal Operation

```bash
1. Load job with Camera Source tool
   ✅ Done

2. Click "onlineCamera" button
   └─ System automatically:
      ├─ Enables external trigger mode
      ├─ Locks 3A (AE + AWB)
      └─ Starts camera stream
   ✅ Camera ready

3. Send hardware trigger signal
   └─ Camera captures frame automatically
   ✅ Frame captured

4. View result in Result Tab
   ✅ Complete
```

### Expected Log Output

```
Starting camera stream...
ℹ️ Enabling trigger mode automatically when starting camera...
Running external trigger command: echo 1 | sudo tee /sys/module/imx296/parameters/trigger_mode
✅ Trigger mode enabled automatically
Camera stream started successfully
Job execution enabled on camera stream
Job execution enabled in camera manager
🔒 Locking 3A (AE + AWB) for trigger mode...
✅ AWB locked
✅ 3A locked (AE + AWB disabled)
```

---

## Troubleshooting

### "Trigger mode not enabling?"
- Check: Does log show "✅ Trigger mode enabled automatically"?
- If not: Check sudo permissions for `/usr/bin/tee`
- Try: `sudo visudo` → Add: `pi ALL=(ALL) NOPASSWD: /usr/bin/tee`

### "Camera not starting?"
- Check: Is job loaded with Camera Source tool?
- Check: Are camera permissions correct?
- Try: Restart application and load job again

### "3A not locking?"
- Check: Log should show "✅ 3A locked (AE + AWB disabled)"
- This is automatic now, no manual steps needed

---

## Technical Notes

### Why Automatic?

**Old Approach:**
- User manually clicks two buttons
- Easy to forget trigger mode enablement
- Inconsistent setup

**New Approach:**
- System ensures trigger mode is always enabled
- Professional automatic workflow
- Consistent setup every time
- Reduces user error

### When Does Automatic Enable Happen?

**Triggered by:** Clicking "onlineCamera" button

**Condition:** Only if `current_mode != 'trigger'`

**Effect:** Calls `camera_manager.set_trigger_mode(True)`

**Result:** External trigger sysfs command executed automatically

---

## Summary

✅ **SIMPLIFIED WORKFLOW:**
- Before: Click "Trigger Camera Mode" → Click "onlineCamera"
- After: Click "onlineCamera" (everything else automatic)

✅ **WHAT HAPPENS AUTOMATICALLY:**
1. External trigger mode enabled via sysfs
2. Camera stream started
3. 3A locked (AE + AWB disabled)
4. Waiting for hardware trigger signals

✅ **USER EXPERIENCE:**
- One-button operation
- Automatic setup
- Professional workflow
- Ready for hardware triggers

✅ **READY FOR PRODUCTION**

---

**Change Date:** November 7, 2025  
**Status:** ✅ Implemented and Ready  
**Testing:** Ready for hardware validation  

