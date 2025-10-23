# Frame History NG/OK Status Display - Implementation Guide

## Overview

Enhanced the review frame system to display the NG/OK status alongside each historical frame in `reviewLabel_1` through `reviewLabel_5`. This provides visual feedback on the quality assessment (OK/NG) for each captured frame.

**User Request (Vietnamese):**
> "Tôi đang có reviewLabel_1,reviewLabel_2,reviewLabel_3,reviewLabel_4,reviewLabel_5 ứng với reviewView_1,reviewView_2,reviewView_3,reviewView_4,reviewView_5 hiển thị các frame đã qua ứng với các NG / OK của frame đó cho cơ chế result"

**Translation:**
> "I have reviewLabel_1 through reviewLabel_5 corresponding to reviewView_1 through reviewView_5 showing past frames with their NG/OK status for the result mechanism"

---

## Architecture

### Data Flow

```
Camera Frame
    ↓
ResultManager.evaluate_detect_results()
    ↓
Store frame status in frame_status_history
    ├─ status: 'OK' or 'NG'
    ├─ similarity: 0.0-1.0
    └─ timestamp: time.time()
    ↓
CameraView._update_review_views_with_frames()
    ├─ Display frame in reviewView_X
    └─ Display status in reviewLabel_X
        ├─ Text: "✓ OK (95%)" or "✗ NG (45%)"
        ├─ Color: GREEN (#00AA00) for OK, RED (#AA0000) for NG
        └─ Font: Bold 11px
```

### Component Responsibilities

| Component | Responsibility |
|-----------|-----------------|
| **ResultManager** | Track frame evaluation results (status, similarity) |
| **CameraView** | Store frame history + retrieve status history |
| **MainWindow** | Connect reviewLabels to CameraView |
| **ReviewLabel** | Display frame NG/OK status visually |
| **ReviewView** | Display actual frame content |

---

## Implementation Details

### 1. ResultManager Enhancement (`gui/result_manager.py`)

**New Attributes:**
```python
self.frame_status_history = []        # Track last 5 frame results
self.max_frame_history = 5            # Keep only 5 recent frames
```

**New Methods:**

#### `_add_frame_status_to_history(timestamp, status, similarity)`
Adds frame evaluation result to history queue
```python
# Called automatically from evaluate_detect_results()
# Stores: timestamp, status ('OK'/'NG'), similarity (0.0-1.0)
# Maintains: Maximum 5 frames
```

#### `get_frame_status_history() -> List[Dict]`
Returns frame status history for display
```python
# Returns list of dicts with keys: 'timestamp', 'status', 'similarity'
# Index 0 = oldest, Index 4 = newest
```

**Integration Point:**
```python
# In evaluate_detect_results()
status = 'OK' if similarity >= self.similarity_threshold else 'NG'
# ... NEW: Add to frame history
self._add_frame_status_to_history(time.time(), status, similarity)
```

### 2. CameraView Enhancement (`gui/camera_view.py`)

**New Attributes:**
```python
self.review_labels = None  # Reference to review label widgets
```

**New Methods:**

#### `set_review_labels(review_labels)`
Configures review labels for NG/OK status display
```python
# Parameters: list of QLabel widgets [reviewLabel_1, ..., reviewLabel_5]
# Configures: Text alignment, font weight, color
```

#### `_update_review_label(label, status, similarity, label_number)`
Updates individual label with NG/OK status and color
```python
# Updates:
#   - Text: "✓ OK (95%)" or "✗ NG (45%)"
#   - Background: GREEN (#00AA00) or RED (#AA0000)
#   - Font: Bold 11px white
```

**Enhanced Method:**
```python
# _update_review_views_with_frames(frame_history)
# NEW: Also retrieves status history from ResultManager
# NEW: Calls _update_review_label() for each frame
# NEW: Clears label text if no frame available
```

### 3. MainWindow Integration (`gui/main_window.py`)

**Enhanced Method:**
```python
# _setup_review_views()
# OLD: Only collected review views
# NEW: Also collects review labels (reviewLabel_1 to reviewLabel_5)
# NEW: Passes both to camera_view via set_review_labels()
```

---

## Visual Display

### Review Label Layout

```
[reviewView_1]    [reviewLabel_1]     <- Most Recent Frame
  (Frame)         ✓ OK
                  (95%)
                  GREEN BG

[reviewView_2]    [reviewLabel_2]     <- Frame 2
  (Frame)         ✗ NG
                  (45%)
                  RED BG

[reviewView_3]    [reviewLabel_3]     <- Frame 3
  (Frame)         ✓ OK
                  (88%)
                  GREEN BG

[reviewView_4]    [reviewLabel_4]     <- Frame 4
  (Frame)         ✗ NG
                  (32%)
                  RED BG

[reviewView_5]    [reviewLabel_5]     <- Oldest Frame
  (Frame)         ✓ OK
                  (92%)
                  GREEN BG
```

### Label Styling

**OK Status (GREEN):**
```
✓ OK
(95%)

Background: #00AA00 (Green)
Text Color: White
Font: Bold 11px
Border: 1px solid #555
```

**NG Status (RED):**
```
✗ NG
(45%)

Background: #AA0000 (Red)
Text Color: White
Font: Bold 11px
Border: 1px solid #555
```

---

## Frame Status Calculation

### Status Determination

```python
# Default: Always NG
if no_reference_set:
    status = 'NG'
    reason = 'No reference set'
    
# NG: No detections found
if no_detections:
    status = 'NG'
    reason = 'No detections found'
    
# Compare with reference
similarity = calculate_similarity(current, reference)

# Threshold: 80% (configurable)
if similarity >= 0.80:
    status = 'OK'
else:
    status = 'NG'
```

### Similarity Calculation

```python
# Based on:
# 1. Detection count (must match reference)
# 2. Bounding box IoU (Intersection over Union >= 0.3)
# 3. Class name matching
# 4. Confidence score averaging
# 5. Position consistency

# Formula: Average of all matching scores
similarity = (count_score + iou_score + class_score + 
              confidence_score + position_score) / 5
```

---

## Data Flow Timeline

### Frame 1 (Most Recent - reviewView_1)
```
1. Frame captured from camera
2. DetectTool processes frame → finds 3 objects
3. ResultManager evaluates: similarity = 0.95 → OK
4. _add_frame_status_to_history(time.time(), 'OK', 0.95)
5. Frame added to history[4]
6. _update_review_views_with_frames() called
7. reviewLabel_1 updated: "✓ OK (95%)" + GREEN
8. Frame displayed in reviewView_1
```

### Frame 2 (Previous - reviewView_2)
```
1. Same process...
2. similarity = 0.42 → NG
3. _add_frame_status_to_history(time.time(), 'NG', 0.42)
4. Frame added to history[3]
5. reviewLabel_2 updated: "✗ NG (42%)" + RED
6. Frame displayed in reviewView_2
```

### Frame 5 (Oldest - reviewView_5)
```
1. Stored 4 frames ago
2. Still in frame_status_history[0]
3. reviewLabel_5 displays its stored status
4. When Frame 6 arrives: history[0] removed, new frame added to history[4]
```

---

## User Workflow

### 1. Setup Phase
```
1. Start application
2. Add DetectTool to job
3. Click Apply
4. Start Live mode
5. System automatically initializes:
   - ResultManager created
   - ReviewLabels connected
   - ReviewViews connected
   - Frame history tracking enabled
```

### 2. Reference Setting Phase
```
1. Point camera at reference object
2. Press Ctrl+R (or click Set Reference button)
3. Console: "Reference set from DetectTool: 3 objects"
4. ResultManager enabled for comparison
5. ReviewLabels ready to show status
```

### 3. Real-time Evaluation Phase
```
1. Point camera at different objects
2. For each frame:
   a. DetectTool finds objects
   b. ResultManager compares with reference
   c. Frame stored in history
   d. Status (OK/NG) calculated and stored
   e. ReviewView displays frame
   f. ReviewLabel displays status + color
3. User can see 5-frame history with status
```

### 4. Quality Feedback Loop
```
User sees:
- reviewView: Visual confirmation of frame content
- reviewLabel: Quick OK/NG status at a glance
- Color coding: Green for pass, Red for fail
- Similarity: Confidence level (0-100%)

This helps user:
- Understand why frame was marked OK/NG
- Adjust reference if needed (press Ctrl+R again)
- Improve camera positioning
- Validate result quality
```

---

## Configuration

### Adjustable Parameters

**In ResultManager:**
```python
self.similarity_threshold = 0.8  # Change from 0.8 to other values (0.0-1.0)
```

**In CameraView:**
```python
self.max_history_frames = 5  # Keep 5 most recent frames
self._review_update_interval = 0.3  # Update labels every 300ms
```

**In Label Styling:**
```python
# Colors:
GREEN_BG = "#00AA00"  # OK
RED_BG = "#AA0000"    # NG

# Font:
font_size = "11px"
font_weight = "bold"
text_color = "white"
```

---

## Testing Checklist

- [ ] Application starts without errors
- [ ] ReviewLabels found and connected (check console logs)
- [ ] Set reference with Ctrl+R
- [ ] Point at reference object → reviewLabel_1 shows "✓ OK" (GREEN)
- [ ] Point at different object → reviewLabel_1 shows "✗ NG" (RED)
- [ ] Move to show 5 different frames
- [ ] All 5 reviewLabels show status with correct colors
- [ ] Similarity percentage displays correctly
- [ ] Labels update smoothly (no lag)
- [ ] Clear reference with Ctrl+Shift+R (if implemented)
- [ ] All labels show "✗ NG" when no reference
- [ ] Console shows no errors for review label operations

---

## Console Output

### Initialization
```
DEBUG: [MainWindow] Found reviewView_1: True
DEBUG: [MainWindow] Found reviewLabel_1: True
DEBUG: [MainWindow] Found reviewLabel_2: True
DEBUG: [MainWindow] Found reviewLabel_3: True
DEBUG: [MainWindow] Found reviewLabel_4: True
DEBUG: [MainWindow] Found reviewLabel_5: True
INFO: Review views and labels connected to camera view for frame history display
INFO: Frame history: Connected to 5 review labels for NG/OK display
```

### Operation
```
DEBUG: [ResultManager] Reference set from DetectTool: 3 objects
DEBUG: [CameraManager] Execution status: OK (from ResultManager) - similarity=95%
DEBUG: [CameraView] Updated reviewLabel_1: OK (95%)
DEBUG: [CameraView] Updated reviewLabel_2: NG (42%)
DEBUG: [CameraView] Updated reviewLabel_3: OK (88%)
```

---

## Files Modified

### `gui/result_manager.py`
- Added: `frame_status_history` attribute
- Added: `_add_frame_status_to_history()` method
- Added: `get_frame_status_history()` method
- Enhanced: `evaluate_detect_results()` to track frame status

### `gui/camera_view.py`
- Added: `review_labels` attribute
- Added: `set_review_labels()` method
- Added: `_update_review_label()` method
- Enhanced: `_update_review_views_with_frames()` to update labels
- Enhanced: Label clearing when frames unavailable

### `gui/main_window.py`
- Enhanced: `_setup_review_views()` to collect and set review labels

---

## Integration with Existing Features

### ResultManager
✅ Works with existing reference setting (Ctrl+R)
✅ Uses existing evaluation logic (similarity calculation)
✅ Maintains frame history separately

### CameraManager
✅ No changes needed
✅ ResultManager handles NG/OK evaluation
✅ CameraView handles display

### CameraView
✅ Reuses existing frame history system
✅ Adds new label display layer
✅ No changes to existing frame display

---

## Performance Considerations

### Memory Usage
- Frame status history: ~5 entries × 100 bytes = 0.5 KB
- Minimal impact on memory

### Update Frequency
- Labels update every 300ms max (configurable)
- Prevents excessive UI updates
- Smooth visual experience

### Threading
- Frame history processing: Background thread
- Label updates: Main thread (via QTimer)
- No blocking operations

---

## Future Enhancements

1. **Export History**
   - Save frame + status to file
   - Generate quality report

2. **Statistical Display**
   - Show OK% vs NG% for session
   - Track similarity trend

3. **Historical Playback**
   - Replay last 5 frames with status
   - Slow motion replay option

4. **Alert Thresholds**
   - Beep/notification on NG
   - Highlight OK/NG streaks

5. **Advanced Filtering**
   - Show only OK frames
   - Show only NG frames

---

## Status Summary

✅ **IMPLEMENTATION COMPLETE**

| Feature | Status |
|---------|--------|
| Frame status tracking | ✅ Done |
| ResultManager integration | ✅ Done |
| CameraView label display | ✅ Done |
| MainWindow setup | ✅ Done |
| Visual styling | ✅ Done |
| Python syntax | ✅ Verified |
| Console logging | ✅ Complete |
| Error handling | ✅ Comprehensive |

**Ready for testing!** 🎉

