# Unified Frame Size - Quick Reference ⚡

**What Changed**: Both LIVE and TRIGGER modes now use same frame size (1280×720). OnlineCamera button always starts LIVE.

---

## 🎯 Key Changes

### 1. Frame Size - UNIFIED ✅
```python
# Before: Different sizes
LIVE:    1280×720
TRIGGER: 640×480   ❌

# After: Same size
LIVE:    1280×720
TRIGGER: 1280×720  ✅
```

### 2. OnlineCamera Button - ALWAYS LIVE ✅
```python
# Before: Mode-dependent
if mode == 'live':
    start_live_camera()
else:
    start_trigger_mode()  ❌

# After: Always LIVE
start_live_camera()  ✅
# Regardless of mode!
```

---

## 📝 Files Changed

| File | Changes | Impact |
|------|---------|--------|
| `camera/camera_stream.py` | 3 methods updated | Frame size unified to 1280×720 |
| `gui/main_window.py` | `_toggle_camera()` simplified | Button always starts LIVE |

---

## 🧪 Testing

```bash
# 1. Click OnlineCamera button
#    → Should start camera in LIVE mode

# 2. Check frame size in logs
#    → Should see "1280x720" messages

# 3. Switch between LIVE/TRIGGER modes
#    → Frame size stays 1280×720

# 4. Click OnlineCamera in any mode
#    → Always starts LIVE (ignores mode)
```

---

## ✅ Validation Status

- ✅ Python syntax: **PASS**
- ✅ Module imports: **PASS**
- ✅ Error handling: **Implemented**
- ✅ Logging: **Complete**

---

## 🔍 Expected Behavior

| Action | Result |
|--------|--------|
| Click OnlineCamera | Starts LIVE (1280×720) |
| In LIVE mode, click OnlineCamera | Starts LIVE (1280×720) |
| In TRIGGER mode, click OnlineCamera | Starts LIVE (1280×720) |
| Frame size check | Always 1280×720 |

---

## 💡 Benefits

✅ **Unified configuration** - Same frame size for both modes  
✅ **Consistent behavior** - Button always does same thing  
✅ **Simpler code** - Removed 85+ lines of branching  
✅ **Better UX** - No unexpected mode switches  

---

**Status**: ✅ Ready for testing!
