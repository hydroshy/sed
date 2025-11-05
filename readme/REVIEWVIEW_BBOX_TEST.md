# ReviewView Bounding Box - Testing Guide

## Setup
1. Make sure detection job is configured and enabled
2. Draw detection region if needed (optional)
3. Start camera/job processing

## Test Cases

### Test 1: Basic Bounding Box Display
**Objective:** Verify boxes appear on review thumbnails

**Steps:**
1. Start detection job (trigger or continuous)
2. Wait for frame to be detected
3. Check main camera view → should see green boxes
4. Check reviewView_1 (most recent) → should see same green boxes
5. Objects should have red background labels

**Expected Result:**
- ✅ Boxes appear on both main view and review thumbnails
- ✅ Same objects detected in both views
- ✅ Labels show class name and confidence (e.g., "person: 0.95")

**Pass Criteria:** Boxes visible on all active review views with detections

---

### Test 2: Frame History Bounding Boxes
**Objective:** Verify all 5 review frames show correct boxes

**Steps:**
1. Let system capture 5 consecutive frames with detections
2. Wait ~2-3 seconds to let all 5 frames populate
3. Look at all 5 reviewView windows:
   - reviewView_1 (most recent - top)
   - reviewView_2
   - reviewView_3
   - reviewView_4
   - reviewView_5 (oldest - bottom)
4. Each should show appropriate boxes for that frame

**Expected Result:**
- ✅ Each review frame shows boxes corresponding to detections in that frame
- ✅ Recent frames have more/different objects than older frames (if scene changed)
- ✅ No "cross-contamination" (reviewView_1 boxes not appearing in reviewView_5)

**Pass Criteria:** Each review frame displays its own unique detection boxes

---

### Test 3: Empty Detection Handling
**Objective:** Verify no errors when frame has no detections

**Steps:**
1. Point camera at area with no detectable objects
2. Run detection job
3. Check logs for errors
4. Check all review frames display without crashing

**Expected Result:**
- ✅ Review frames display cleanly without boxes
- ✅ No "cannot draw" errors in logs
- ✅ No application crashes
- ✅ Labels still show NG/OK status

**Pass Criteria:** Clean display with no error messages when detections are empty

---

### Test 4: Box Scaling on Resized Frames
**Objective:** Verify bounding boxes scale correctly for review frames

**Steps:**
1. Ensure detection region is off-center (not at origin 0,0)
2. Detect object
3. Check if box position matches main camera view but scaled to 320x240

**Expected Result:**
- ✅ Boxes position matches when accounting for 320x240 resize
- ✅ Box doesn't jump or misalign
- ✅ Object center roughly in same relative position

**Pass Criteria:** Boxes align correctly in resized views

---

### Test 5: Label Display Quality
**Objective:** Verify labels are readable on thumbnails

**Steps:**
1. Trigger detection
2. Look at review frame boxes
3. Read label text (class name + confidence)

**Expected Result:**
- ✅ Text is readable (not too small, contrasts with background)
- ✅ Shows correct class name
- ✅ Shows confidence 0.00 to 1.00
- ✅ Red background doesn't blend with green box

**Pass Criteria:** Labels are clear and informative

---

### Test 6: Continuous Mode
**Objective:** Verify boxes update continuously in live mode

**Steps:**
1. Enable continuous detection mode (not trigger)
2. Watch review frames update
3. Move objects or change scene
4. Observe boxes update in real-time

**Expected Result:**
- ✅ Review boxes update every 300ms (refresh interval)
- ✅ New objects appear as they're detected
- ✅ Old objects disappear from history after 5 frames
- ✅ Smooth transitions between frames

**Pass Criteria:** Live update works smoothly

---

### Test 7: Performance Impact
**Objective:** Verify no UI freezing from box drawing

**Steps:**
1. Enable box drawing on reviews
2. Run detection at max FPS
3. Monitor main UI responsiveness
4. Try moving windows, clicking buttons
5. Check FPS counter

**Expected Result:**
- ✅ Main UI remains responsive
- ✅ No 100-300ms freezes
- ✅ FPS counter shows expected frame rate
- ✅ No lag when moving windows

**Pass Criteria:** No noticeable performance degradation

---

## Debug Logging

Check logs for these messages when boxes should appear:

```
[ReviewLabel] reviewLabel_1 - Displaying frame #X, shape=(...), detections=5
[ReviewView 1] Drawing 5 detections
```

If boxes don't appear, check:
```
[ReviewLabel] reviewLabel_1 - ... detections=0
```

If detections=0, check:
- Detection job is running
- Objects are actually detected in main view
- Frame has content (not blank/black)

---

## Common Issues & Fixes

| Issue | Symptom | Fix |
|-------|---------|-----|
| No boxes on review | Frame visible but no boxes | Check if main view has boxes; if not, detection job issue |
| Boxes in wrong position | Boxes offset from objects | Check resize_scale calculation, verify frame actually resized |
| Labels unreadable | Text too small or invisible | Adjust cv2 font_scale in drawing code (line ~1985) |
| Only some reviews show boxes | reviewView_3 has boxes but reviewView_2 doesn't | Check if detections_history has right length, clear history |
| Performance lag | System slow when boxes drawn | Check if drawing in wrong thread, verify no double-drawing |

---

## Automated Check Script

Add this to logs to verify setup:

```python
# After detection, add to logs:
logging.debug(f"Frame history size: {len(self.frame_history)}")
logging.debug(f"Detections history size: {len(self.detections_history)}")
logging.debug(f"Histories in sync: {len(self.frame_history) == len(self.detections_history)}")
```

Should show equal sizes.

---

## Sign-Off Checklist

- [ ] Test 1: Basic boxes appear ✓
- [ ] Test 2: All 5 frames show correct boxes ✓
- [ ] Test 3: No errors with empty detections ✓
- [ ] Test 4: Box positions scale correctly ✓
- [ ] Test 5: Labels are readable ✓
- [ ] Test 6: Continuous mode updates ✓
- [ ] Test 7: No performance impact ✓
- [ ] Logs show correct history sizes ✓

**Result:** ✅ READY FOR PRODUCTION
