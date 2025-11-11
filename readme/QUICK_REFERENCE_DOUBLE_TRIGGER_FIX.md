# Quick Reference - Double Trigger Fix

## Problem Fixed
**Before:** Single trigger click executed 2 jobs
**After:** Single trigger click executes exactly 1 job

## Root Cause
PyQt5 on Raspberry Pi: `button.setEnabled(False)` does NOT prevent clicked signal emission

## Solution Implemented
**Flag-based click blocking** - software level, not UI level

## How It Works

```python
# Guard check at handler start
if self._trigger_processing:
    return  # Block click if already processing

# Set processing flag
self._trigger_processing = True

# ... do work (capture + 250ms) ...

# Clear flag when done
self._trigger_processing = False
```

## Key Changes

| File | Change | Result |
|------|--------|--------|
| `gui/camera_manager.py` | Added `_trigger_processing` flag | Blocks overlapping clicks |
| `gui/camera_manager.py` | Increased timeout: 100ms → 500ms | Covers entire processing window |
| `gui/camera_manager.py` | Always clear flag | Prevents stuck state |

## Guard Layers (3-Layer Defense)

```
Layer 1: if self._trigger_processing: return
         ↓ (blocks current processing)
Layer 2: if time_since_last < 500: return
         ↓ (blocks rapid retrigger)
Layer 3: if not button_is_enabled: return
         ↓ (blocks disabled state)
Proceed to process trigger
```

## Console Output Evidence

```
✅ Working:
   Click 1: SET _trigger_processing = True
   Click 2: BLOCKED: Trigger clicked too fast
   Result: 1 job, 1 label update

❌ What Doesn't Work:
   button.setEnabled(False) alone - signals still emit on Raspberry Pi
```

## Testing Checklist

- [x] Single click = 1 job
- [x] Double-click = 1st processed, 2nd blocked
- [x] Button disable/enable works
- [x] No stuck states
- [x] NG/OK evaluation correct
- [x] Label shows correct status

## Deployment Verified

✅ Tested on: Raspberry Pi 5
✅ Date: October 23, 2025, 15:38
✅ Status: OPERATIONAL
✅ Ready: PRODUCTION

## If Issues Occur

**Problem:** Click still executes 2 jobs
**Check:**
- Line 1905: Is `_trigger_processing` flag check present?
- Line 1912: Is flag set before processing?
- Line 1980: Is flag cleared after processing?

**Debug:**
```python
# Look for these messages in console:
"SET _trigger_processing = True"      # ✅ Should appear once per click
"BLOCKED: Trigger clicked too fast"   # ✅ Should appear for blocked clicks
"CLEARED _trigger_processing = False" # ✅ Should appear after processing
```

---

**Bottom Line:** Double click issue RESOLVED. System working perfectly. 🎉
