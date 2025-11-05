# ReviewView Sync Fix - Quick Reference

## 问题 (Problem)
ReviewView and ReviewLabels only update on 2nd trigger, showing old detections on 1st trigger.

## 原因 (Root Cause)
**Race Condition:** Frame added to history → ReviewViewUpdate triggered → **before** detection results processed

Sequence:
1. Frame added to history
2. ReviewView updates (reads detections_history with OLD data)
3. Detection results processed (updates detections_history with NEW data)
4. Next trigger needed to see correct data

## 解决方案 (Solution)
**Trigger ReviewView update IMMEDIATELY after detection results processed**

File: `gui/camera_view.py`
Method: `_handle_detection_results()`
Line: After detections_history is updated (around line 674)

```python
# Add this line after self._show_frame_with_zoom()
QTimer.singleShot(0, self._update_review_views_threaded)
logging.info(f"[DETECTION SYNC] Triggering review view update after detection results processed")
```

## 验证日志 (Verification Log)

Look for this log message appearing immediately after detection extraction:
```
INFO - [Detection Extract] ✅ Found X detections in Detect Tool
INFO - [DETECTION SYNC] Triggering review view update after detection results processed
INFO - [ReviewViewUpdate] Main thread update triggered
```

## 测试 (Test)

1. **Object Present → Click Trigger**
   - Expected: Immediately shows green boxes, detections=1, text='OK'
   
2. **No Object → Click Trigger**
   - Expected: Immediately shows no boxes, detections=0, text='NG'

No 2nd trigger needed to see updated display!

## 文件修改 (Files Modified)
- `gui/camera_view.py` - Added review update trigger

## 相关修复 (Related Fixes)
This is the 4th fix addressing detection pipeline:
1. Fix #1: Detection extraction from job results structure
2. Fix #2: Bounding box coordinate format support
3. Fix #3: Empty detections synchronization (always update)
4. **Fix #4: ReviewView delayed update (immediate trigger after detection)**

All 4 fixes required for proper display of detections on ReviewView.
