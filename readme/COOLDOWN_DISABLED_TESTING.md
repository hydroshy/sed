# ⚠️ TESTING MODE: Cooldown Disabled (Temporary)

**Date:** October 22, 2025  
**Status:** ⚠️ **EXPERIMENTAL - TESTING ONLY**

---

## 🔧 What Changed

### File: camera/camera_stream.py (Line 182)

**Before (Normal):**
```python
self._cooldown_s = 0.25  # 250ms cooldown between triggers
```

**After (Testing):**
```python
self._cooldown_s = 0.0  # ⚠️ TESTING: Cooldown disabled
```

---

## 📊 Expected Behavior Changes

### With Cooldown (Normal) ✅
```
Trigger: 0ms    → Frame 1 captured ✓
Trigger: 50ms   → IGNORED (cooldown active)
Trigger: 100ms  → IGNORED (cooldown active)
Trigger: 250ms  → Frame 2 captured ✓
Trigger: 300ms  → Frame 3 captured ✓

Throttling: ~4 frames/second (1000ms / 250ms)
```

### Without Cooldown (Testing) ⚠️
```
Trigger: 0ms    → Frame 1 captured (processing)
Trigger: 50ms   → Frame 2 captured (processing) ← Xung đột!
Trigger: 100ms  → Frame 3 captured (processing) ← Xung đột!
Trigger: 150ms  → Frame 4 captured (processing) ← Xung đột!

Throttling: NONE - As fast as possible
Success Rate: May decrease due to conflicts
```

---

## ⚡ What To Expect

### ✅ Positive (Nếu camera xử lý được)
- Faster trigger response
- No ignored triggers
- More frames captured per second
- Test real-world performance limits

### ❌ Negative (Nguy hiểm)
- Camera may hang/freeze
- Frame drops / lost data
- Pi5 CPU overload (95-100%)
- Memory leak
- "Trigger ignored" from internal conflicts
- Picamera2 buffer overflow
- Emergency restart needed

---

## 📋 Testing Checklist

### Before Testing
```
□ Backup current state
□ Have SSH access to Pi5 (for emergency kill)
□ Monitor system resource (top, htop)
□ Record success/failure rate
```

### During Testing
```
□ Send slow triggers first (1 per second)
□ Gradually increase trigger rate
□ Monitor logs for errors
□ Watch CPU/Memory usage
□ Check frame quality
```

### What To Watch For
```
❌ STOP if you see:
   - "Frame dropped" repeated
   - CPU > 90%
   - Memory increasing continuously
   - Camera freezing
   - Command timeout
   - "buffer full" errors
```

---

## 📝 Console Log Differences

### With Cooldown
```
✓ Camera triggered successfully
✓ Frame captured: (480, 640, 3)
[Next trigger ignored until 250ms passes]
```

### Without Cooldown
```
✓ Camera triggered successfully
✓ Frame captured: (480, 640, 3)
[Immediate next trigger allowed]
⚠️ May see conflicts or frame drops
```

---

## 🎯 How To Restore

### If Something Goes Wrong

**Option 1: Restore Original Value**
```python
# In camera/camera_stream.py, line 182:
self._cooldown_s = 0.25  # Back to 250ms
```

**Option 2: Set Custom Value**
```python
self._cooldown_s = 0.15  # 150ms (middle ground)
self._cooldown_s = 0.10  # 100ms (lower limit)
self._cooldown_s = 0.05  # 50ms (dangerous)
```

---

## 📊 Test Results Template

**When you test, please record:**

```
Trigger Rate: ___ triggers/second
Success Rate: ___ % (successful / total)
Frame Quality: Good / Degraded / Poor
CPU Usage: ___% 
Memory Usage: ___ MB
Errors Seen: ___

Observations:
- 
- 
-

Conclusion: Works / Needs to restore cooldown
```

---

## ⚠️ Important Notes

1. **This is TEMPORARY** - Not for production
2. **For testing purposes only** - Not recommended for real use
3. **Monitor closely** - Be ready to stop if problems occur
4. **Document results** - Record what you find
5. **Restore when done** - Set cooldown back to 0.25

---

## 🔄 How To Switch Back

When done testing:

```python
# Restore normal operation:
self._cooldown_s = 0.25  # 250ms (default)
```

---

## 📌 Remember

- ✅ **Cooldown protects camera hardware**
- ⚠️ **Removing it is experimental**
- ❌ **Problems may require Pi restart**
- ✅ **You can always restore the original value**

**Test safely and document your findings!** 🚀

