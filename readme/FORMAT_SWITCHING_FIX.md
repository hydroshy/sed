# Format Switching Fix - XRGB8888 ↔ XBGR8888

## Issue
User reported: "Giờ chuyển qua lại giữa XBGR8888 và XRGB888 không được nữa" 
(Now switching between XBGR8888 and XRGB8888 doesn't work anymore)

## Root Cause
In `camera_stream.py` `set_format()` method, the `format_map` was mapping ALL formats to `XBGR8888`:
```python
format_map = {
    'RGB888': 'XBGR8888',      # ❌ WRONG
    'BGR888': 'XBGR8888',      # ✓ OK
    'XRGB8888': 'XBGR8888',    # ❌ WRONG - couldn't select XRGB8888
    'XBGR8888': 'XBGR8888',    # ✓ OK
}
```

This made it impossible to actually switch to XRGB8888 format.

## Solution
Fixed the format_map to properly support both formats:
```python
format_map = {
    'RGB888': 'XRGB8888',      # ✓ FIXED - RGB888 → XRGB8888
    'BGR888': 'XBGR8888',      # ✓ OK - BGR888 → XBGR8888
    'XRGB8888': 'XRGB8888',    # ✓ FIXED - now can select XRGB8888
    'XBGR8888': 'XBGR8888',    # ✓ OK - XBGR8888 stays XBGR8888
    'YUV420': 'YUV420',
    'NV12': 'NV12',
}
```

## Files Modified
- **`camera/camera_stream.py`** Line 1177-1182
  - Updated format_map to properly support XRGB8888 and XBGR8888 switching

## How Format Switching Works Now

### In camera_stream.py:set_format()
1. User selects format in comboBox (e.g., "XRGB8888")
2. `set_format("XRGB8888")` is called
3. `_pixel_format` is set to user's selection: `"XRGB8888"`
4. `actual_format` is mapped: `"XRGB8888"` → `"XRGB8888"` (via format_map)
5. Camera config updated with actual_format
6. Camera reconfigured and restarted if needed

### In gui/camera_view.py:_process_frame_to_qimage()
When frame is received:
1. Get pixel format from camera: `get_pixel_format()` → e.g., "XRGB8888"
2. For 4-channel formats: always use `cv2.cvtColor(BGRA2RGB)` because:
   - Picamera2 returns BGRA byte order regardless of format name
   - Both XRGB8888 and XBGR8888 come out as BGRA in OpenCV
3. Frame converted to RGB for display

### In gui/main_window.py:_load_camera_formats()
ComboBox shows both formats:
```
[XRGB8888] (selected if camera using XRGB8888)
[XBGR8888] (selected if camera using XBGR8888)
```

## Testing
To verify format switching works:
1. Launch app
2. ComboBox shows XBGR8888 (default)
3. Click to select XRGB8888
4. Verify:
   - ComboBox updates to XRGB8888
   - Colors display correctly (should look same either way due to color conversion)
5. Switch back to XBGR8888
6. Verify comboBox updates

## Design Notes

**Why both formats look the same after conversion:**
- XRGB8888: Picamera2 returns BGRA data
- XBGR8888: Picamera2 also returns BGRA data
- Both are converted BGRA→RGB for display
- Result: identical appearance, but different internal representation

**Default format strategy:**
- Default to XBGR8888 (set in __init__ and all config creation)
- But user can switch to XRGB8888 if needed
- Format persists across selections (via _pixel_format and get_pixel_format)

## Related Changes Previously Made
- Changed all default format assignments from XRGB8888 to XBGR8888 (Phase 1)
- Added format sync methods to ensure comboBox reflects actual camera format (Phase 2)
- Fixed color conversion to handle both formats (Phase 3)
- Now fixed format switching to allow toggling between both (Phase 4)
