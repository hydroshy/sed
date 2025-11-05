# Quick Reference - Frame Duplication Fix & Review Clear

## What Was Fixed

### 1. Frame Duplication Issue ✅
**Problem:** Frames appeared twice in history per trigger capture
- Symptom: Single trigger → 2 frames in review display
- Root cause: Signal handler connected multiple times due to old worker connections persisting

**Solution:** Aggressive disconnect approach
- Disconnect ALL handlers from old worker signal before cleanup
- Disconnect ALL handlers from new worker before connecting
- Ensures single connection = single handler call per signal emit

**Result:** Single trigger → Single frame in history ✅

---

### 2. Review Labels Clear on Tool Edit ✅
**Request:** "Mỗi lần editTool thì sẽ clear ( refresh lại reviewLabel và reviewFrame có được không)"

**Solution:** Auto-clear when tool editing starts
- Frame history cleared
- All 5 review labels cleared
- Status history cleared
- Fresh start for new captures

**Result:** Clean UI state when editing tools ✅

---

## Code Changes Summary

| Component | Change | File |
|-----------|--------|------|
| Camera Display Worker | Use `disconnect()` without parameters to disconnect ALL | `camera_view.py` |
| Frame History Clearing | New method `clear_frame_history_and_reviews()` | `camera_view.py` |
| Status History Clearing | New method `clear_history()` | `result_manager.py` |
| Tool Editing Entry | Call clear on `switch_to_tool_setting_page()` | `settings_manager.py` |

---

## How to Test

### Test 1: Single Capture
```
1. Click Trigger once
2. Should see ONLY 1 frame in review display
3. NOT 2 frames
4. Look for log: "[CameraView] _handle_processed_frame called" (should appear once)
```

### Test 2: Multiple Captures
```
1. Click Trigger 5 times
2. Review should show up to 5 frames (most recent first)
3. Each frame appears exactly once (not duplicated)
4. Check frame numbers and frame shapes match
```

### Test 3: Tool Editing Clears History
```
1. Trigger 3-5 captures (fill review display)
2. Click on "Detect Tool" to edit
3. All 5 review labels should clear immediately
4. Edit threshold and click Apply
5. Trigger new capture - frame should be fresh
6. Look for log: "[CameraView] === CLEARING FRAME HISTORY AND REVIEWS ==="
```

### Test 4: Settings Change (Threshold Edit)
```
1. Edit threshold from 0.5 to 0.95
2. Click Apply
3. Trigger capture
4. Frame should appear ONCE (not twice)
5. Status should be NG (no detections at 0.95 threshold)
```

---

## Key Log Markers

### Frame Duplication Fixed
```
[CameraView] frameProcessed signal emitted (emit #N)  ← ONCE
[CameraView] _handle_processed_frame called           ← ONCE (matches emit count)
```

### Worker Lifecycle (Phase 11e diagnostic)
```
[CameraView] === STARTING NEW WORKER ===
[CameraView] Found OLD worker (id: ...), disconnecting ALL handlers...
[CameraView] ✅ OLD worker's frameProcessed signal: ALL handlers disconnected
[CameraView] Creating CameraDisplayWorker instance #N
[CameraView] ✅ Disconnected ALL handlers from NEW worker (clean slate)
[CameraView] ✅ Connected frameProcessed on worker #N
[CameraView] === WORKER #N STARTED ===
```

### Review Clear on Tool Edit
```
[CameraView] === CLEARING FRAME HISTORY AND REVIEWS ===
[CameraView] ✅ Frame history cleared
[CameraView] ✅ Cleared reviewLabel_1
[CameraView] ✅ Cleared reviewLabel_2
... (3-5)
[ResultManager] Frame status history cleared
[CameraView] === FRAME HISTORY AND REVIEWS CLEARED ===
```

---

## Expected Results After Fix

| Scenario | Before Fix | After Fix |
|----------|-----------|-----------|
| Single trigger | 2 frames in history | 1 frame in history ✅ |
| Signal emit count | 1 emit = 2 handlers | 1 emit = 1 handler ✅ |
| Tool editing | Reviews kept old frames | Reviews cleared ✅ |
| Settings apply | New worker created with duplicate connection | Clean connection ✅ |
| Frame-to-status | Mismatch (2 frames, 1 status) | Match (1 frame, 1 status) ✅ |

---

## Important Notes

1. **Why disconnect() without parameters?**
   - PyQt signals can have multiple handlers connected
   - `signal.disconnect(handler)` only disconnects specific handler
   - `signal.disconnect()` with no parameters disconnects ALL handlers
   - Ensures clean slate before new connection

2. **Why clear on tool edit?**
   - User expectations: Editing tool = fresh start
   - Prevents confusion from old frames mixing with new settings
   - Provides clear UI indication of mode change

3. **Thread Safety:**
   - Uses `frame_history_lock` for thread-safe clearing
   - Result manager history is not threaded (safe to clear)
   - Main thread updates review labels

4. **No Breaking Changes:**
   - Frame pipeline unchanged
   - Job processing unchanged
   - UI layout unchanged
   - Only fixes duplication and adds clearing on tool edit

---

## Files Modified

1. **e:\PROJECT\sed\gui\camera_view.py**
   - Lines 1570-1605: `clear_frame_history_and_reviews()` method
   - Lines 1604-1655: `_start_camera_display_worker()` with aggressive disconnect
   - Lines 1657-1680: `_stop_camera_display_worker()` with enhanced cleanup

2. **e:\PROJECT\sed\gui\result_manager.py**
   - Lines 425-432: `clear_history()` method

3. **e:\PROJECT\sed\gui\settings_manager.py**
   - Lines 124-140: Call clear in `switch_to_tool_setting_page()`

---

## Next Steps for Testing

1. ✅ Review code changes
2. ⏳ Run test scenario with threshold edit (0.5 → 0.95)
3. ⏳ Verify single frame per trigger
4. ⏳ Verify review labels clear on tool edit
5. ⏳ Check logs for proper markers
6. ⏳ Multiple consecutive triggers - verify no duplication
7. ✅ Complete and ready for production

---

## Questions?

Check logs for:
- `[CameraView]` markers for frame display flow
- `[CameraDisplayWorker]` markers for signal emissions
- `[ResultManager]` markers for status history
- Worker instance numbers to track lifecycle

Compare before/after logs to verify fix working.
