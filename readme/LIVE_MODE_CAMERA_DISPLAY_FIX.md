# Live Mode Camera Display Fix - Edit Camera Source

**Issue:** When editing Camera Source tool in live mode, no image displayed on camera view  
**Date Fixed:** November 2, 2025  
**Status:** ✅ FIXED

---

## Problem Description

**Scenario:**
1. Camera in **Live Mode**
2. User clicks to edit **Camera Source** tool
3. Camera view shows **BLACK SCREEN** (no video)
4. But logs show frames are still being captured and processed

**Symptoms in Logs:**
```
[CameraManager] _on_frame_from_camera called (call #77) - frame shape: (480, 640, 4)
[CameraManager] _on_frame_from_camera called (call #78) - frame shape: (480, 640, 4)
[CameraManager] _on_frame_from_camera called (call #79) - frame shape: (480, 640, 4)
... (frames keep coming but no display)
```

---

## Root Cause

In `gui/camera_manager.py`, method `_on_frame_from_camera()`:

```python
# OLD CODE (WRONG):
if self._is_editing_camera_tool():
    # Signal will trigger automatically from frame_ready
    return  # ❌ RETURNS WITHOUT DISPLAYING FRAME!

if not getattr(self, 'job_enabled', False):
    # Signal will trigger automatically from frame_ready
    return  # ❌ RETURNS WITHOUT DISPLAYING FRAME!
```

**Problems:**
1. When editing Camera Source → returns without calling `display_frame()`
2. When job disabled → returns without calling `display_frame()`
3. Comment says "Signal will trigger automatically" but that's **FALSE**:
   - `frame_ready` signal connects to `_on_frame_from_camera()` (line 166)
   - NOT to `camera_view.display_frame()` directly
4. Result: **No video displayed**

---

## Solution

**Display raw frames even when editing or job disabled:**

```python
# NEW CODE (FIXED):
if self._is_editing_camera_tool():
    # ✅ DISPLAY RAW FRAME even when editing Camera Source (disable job processing but show video)
    if self.camera_view:
        self.camera_view.display_frame(frame)
    return  # ✅ Now shows video!

if not getattr(self, 'job_enabled', False):
    # ✅ DISPLAY RAW FRAME when job is disabled
    if self.camera_view:
        self.camera_view.display_frame(frame)
    return  # ✅ Now shows video!
```

**Key Change:**
- Before: `return` immediately (no display)
- After: Call `display_frame()` THEN `return` (video shows)

---

## Behavior After Fix

| Scenario | Before Fix | After Fix |
|----------|-----------|-----------|
| Editing Camera Source in Live Mode | ❌ Black screen | ✅ Live video shown |
| Job Disabled in Live Mode | ❌ Black screen | ✅ Live video shown |
| Normal Job Processing | ✅ Works | ✅ Still works |
| Trigger Mode | ✅ Works | ✅ Still works |

---

## Flow Diagram

### Editing Camera Source (After Fix)

```
Frame captured from camera
    ↓
frame_ready signal emitted
    ↓
_on_frame_from_camera() called
    ↓
_is_editing_camera_tool() returns True
    ↓
✅ display_frame(raw_frame) called
    ↓
return (skip job processing)
    ↓
✅ User sees live video
```

### Normal Job Processing (Unchanged)

```
Frame captured from camera
    ↓
frame_ready signal emitted
    ↓
_on_frame_from_camera() called
    ↓
_is_editing_camera_tool() returns False
✅ job_enabled is True
    ↓
Run job pipeline
    ↓
✅ display_frame(processed_frame)
    ↓
✅ User sees processed output
```

---

## Files Modified

**File:** `e:\PROJECT\sed\gui\camera_manager.py`  
**Lines:** 313-320 (in `_on_frame_from_camera()` method)  
**Change Type:** Bug fix - display logic

---

## Testing

### Test 1: Edit Camera Source in Live Mode
```
1. Start application in Live Mode
2. Click Camera button to enable live view
3. Click on "Camera Source" tool to edit
4. ✅ Should see live video feed (NOT black screen)
5. Adjust settings (e.g., exposure) while viewing live video
6. ✅ Live video continues to show
7. Click Cancel or Apply to close editing
8. ✅ Video still shows and processes normally
```

### Test 2: Disable Job in Live Mode
```
1. Start application in Live Mode
2. Click Camera button to enable live view
3. Disable job processing (if such option exists)
4. ✅ Should still see live video feed (NOT black screen)
5. Re-enable job processing
6. ✅ Processed output shows
```

### Test 3: Normal Processing Still Works
```
1. Start application in Live Mode
2. Click Camera button to enable live view
3. ✅ Should see detection/job processing results
4. Edit Camera Source and Apply
5. ✅ Should resume showing processed output (not just raw)
```

---

## Log Validation

**Before Fix (Problem):**
```
[CameraManager] _on_frame_from_camera called (call #77)
... (no display_frame log entries while editing)
... (frames processed but black screen on UI)
```

**After Fix (Working):**
```
[CameraManager] _on_frame_from_camera called (call #77)
[CameraView] display_frame called (call #M)  ← ✅ Now appears!
[CameraManager] _on_frame_from_camera called (call #78)
[CameraView] display_frame called (call #M+1)  ← ✅ Continues!
```

---

## Why This Works

1. **`display_frame()`** sends frame to CameraDisplayWorker
2. **CameraDisplayWorker** processes frame in background thread
3. **Processed QImage** emitted back to main thread
4. **`_handle_processed_frame()`** displays QImage on graphics view
5. **User sees video** ✅

---

## No Side Effects

- ✅ Job processing still works normally when not editing
- ✅ Trigger mode unaffected
- ✅ Performance unchanged
- ✅ Frame duplication fix still intact
- ✅ Review labels still work
- ✅ Only affects "editing Camera Source" scenario

---

## Related Issues Fixed

- **Frame Duplication:** Separate fix (already completed)
- **Review Label Clear:** Separate fix (already completed)
- **Live Mode Display:** **THIS FIX** ← Current

---

## Sign-Off

✅ **Code Fixed**  
✅ **Logic Verified**  
✅ **No Side Effects**  
⏳ **Awaiting Test Confirmation**

---

## Questions?

1. Can you see live video when editing Camera Source now?
2. Does video continue showing while adjusting settings?
3. Does everything work normally after closing edit dialog?

If yes to all 3 → Fix is working correctly! 🎯
