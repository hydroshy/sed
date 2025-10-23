# ⚡ Cooldown Removed - Quick Guide

**File Changed:** `camera/camera_stream.py` (Line 182)

---

## 🔧 What Happened

```python
# Was:
self._cooldown_s = 0.25  # 250ms

# Now:
self._cooldown_s = 0.0   # Disabled ⚠️
```

---

## ✅ You Can Now Test

```
✓ Triggers will NOT be ignored by cooldown
✓ Camera will try to capture every trigger
✓ No waiting between frames
```

---

## ⚠️ Watch Out For

```
❌ Camera may hang
❌ Frames may drop
❌ CPU may spike to 100%
❌ Memory may leak
```

---

## 📊 What You'll See

**Normal (with cooldown):**
```
Trigger → Capture ✓
(wait 250ms)
Trigger → Capture ✓
```

**Now (without cooldown):**
```
Trigger → Capture ✓
Trigger → Capture ✓ (maybe conflicts?)
Trigger → Capture ✓
Trigger → Capture ✓
(faster, but risky!)
```

---

## 🚀 How To Use

1. **Run app** - Works as normal
2. **Send triggers** - Try from Pico
3. **Monitor** - Watch console logs & performance
4. **Record results** - Note success rate, CPU usage, etc.

---

## 🔄 How To Restore

Edit `camera/camera_stream.py` line 182:
```python
self._cooldown_s = 0.25  # Back to normal
```

---

**Test it and let me know what you find!** 🎯

