# Frame History NG/OK Display - Quick Reference

## What's New

ReviewLabel widgets (reviewLabel_1 through reviewLabel_5) now display NG/OK status for each frame in the history with color coding:
- **✓ OK** = GREEN background, shows similarity %
- **✗ NG** = RED background, shows similarity %

## Visual Example

```
Frame History View:

[Frame 1]    [OK]       <- reviewLabel_1 (most recent)
             (95%)
             GREEN

[Frame 2]    [NG]       <- reviewLabel_2
             (35%)
             RED

[Frame 3]    [OK]       <- reviewLabel_3
             (88%)
             GREEN

[Frame 4]    [OK]       <- reviewLabel_4
             (92%)
             GREEN

[Frame 5]    [NG]       <- reviewLabel_5 (oldest)
             (25%)
             RED
```

## How to Use

### 1. Basic Setup (Automatic)
```
1. Start Application
2. Application auto-connects reviewLabels
3. No manual configuration needed
```

### 2. Set Reference
```
1. Point camera at reference object
2. Press Ctrl+R
3. Console: "Reference set from DetectTool"
4. ReviewLabels ready to show status
```

### 3. Evaluate Objects
```
1. Point camera at object to evaluate
2. Frame captured and evaluated
3. ReviewLabel_1 shows: "✓ OK (95%)" or "✗ NG (45%)"
4. Color: GREEN for OK, RED for NG
5. Keep moving camera to populate all 5 labels
```

## Colors

| Status | Color | Background | Text |
|--------|-------|-----------|------|
| OK | GREEN | #00AA00 | White, Bold |
| NG | RED | #AA0000 | White, Bold |

## Information Displayed

Each reviewLabel shows:
- **Status Symbol:** ✓ (OK) or ✗ (NG)
- **Status Text:** OK or NG
- **Similarity:** Percentage (0-100%)
- **Color:** Green or Red background

## Troubleshooting

### ReviewLabels Not Showing Status

**Check 1: Are reviewLabels found?**
```
Console should show:
"Found reviewLabel_1: True"
"Found reviewLabel_2: True"
...
"Found reviewLabel_5: True"
```

**Check 2: Is reference set?**
```
Console should show:
"Reference set from DetectTool: X objects"

If not set, all labels will show NG by default
```

**Check 3: Are frames being captured?**
```
Should see frames in reviewView_1 through reviewView_5
If no frames, start Live mode first
```

### All Labels Showing NG

**Possible Causes:**
1. Reference not set → Press Ctrl+R
2. No detections → Adjust camera positioning
3. Objects too different → Set new reference

### ReviewLabels Not Updating

**Possible Causes:**
1. Live mode not running
2. DetectTool not applied
3. ResultManager error (check console)

## Console Messages

### Successful Setup
```
✓ Found reviewLabel_1: True
✓ Found reviewLabel_2: True
✓ Found reviewLabel_3: True
✓ Found reviewLabel_4: True
✓ Found reviewLabel_5: True
✓ Review views and labels connected
✓ Frame history connected to 5 review labels
```

### During Operation
```
✓ Reference set from DetectTool: 3 objects
✓ Execution status: OK (from ResultManager) - similarity=95%
✓ Updated reviewLabel_1: OK (95%)
✓ Updated reviewLabel_2: NG (42%)
```

## Key Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+R | Set reference from current frame |
| Live | Capture frames for review display |

## Status Flow

```
No Reference Set
    ↓
All ReviewLabels: ✗ NG (Red)
    ↓
Set Reference (Ctrl+R)
    ↓
    ├→ Same Object → ✓ OK (Green)
    ├→ Similar Object → ✓ OK or ✗ NG (depends on threshold)
    └→ Different Object → ✗ NG (Red)
```

## Frame Position

| Label | Frame Age | Position |
|-------|-----------|----------|
| reviewLabel_1 | Most Recent | Top |
| reviewLabel_2 | 1 frame old | - |
| reviewLabel_3 | 2 frames old | - |
| reviewLabel_4 | 3 frames old | - |
| reviewLabel_5 | Oldest (4+ old) | Bottom |

## Configuration (For Advanced Users)

### Similarity Threshold
```python
# In ResultManager
self.similarity_threshold = 0.8  # 0-1.0 range
# Higher = stricter OK requirement
# Lower = more lenient OK requirement
```

### Update Frequency
```python
# In CameraView
self._review_update_interval = 0.3  # seconds
# Higher = less frequent updates (smoother)
# Lower = more frequent updates (more responsive)
```

### Label Colors
```python
# In CameraView._update_review_label()
GREEN_BG = "#00AA00"  # OK
RED_BG = "#AA0000"    # NG
```

## Files Modified

1. **gui/result_manager.py**
   - Added frame status history tracking
   - Auto-stores status when frame evaluated

2. **gui/camera_view.py**
   - Added reviewLabel display support
   - Auto-updates labels with status + color

3. **gui/main_window.py**
   - Auto-connects reviewLabels on startup
   - Passes labels to CameraView

## Related Documentation

- `FRAME_HISTORY_NG_OK_STATUS_DISPLAY.md` - Full implementation guide
- `RESULT_MANAGER_IMPLEMENTATION.md` - ResultManager details
- `RESULT_TOOL_SETUP.md` - OK/NG mechanism details

## Quick Test

```
1. Start app
2. Apply DetectTool
3. Start Live mode
4. Point at object
5. Press Ctrl+R
6. See reviewLabel_1 turn GREEN with "✓ OK"
7. Point at different object
8. See reviewLabel_1 turn RED with "✗ NG"
9. Generate 5 frames
10. See all reviewLabel_1 through reviewLabel_5 populated
```

✅ **Complete!** All reviewLabels now display frame NG/OK status.

