# FIFO Queue Matching - Before & After Fix

## 🔄 The Problem

### Scenario: 2 Frames Waiting

```
Time:
T=0ms: TCP start_rising → Frame 7 created
       Frame 7: sensor_in=100, sensor_out=?, status=PENDING

T=1ms: TCP start_rising → Frame 8 created
       Frame 8: sensor_in=101, sensor_out=?, status=PENDING

Queue state now:
┌──────────────────────────────────────┐
│ Queue (in order of creation)         │
├──────────────────────────────────────┤
│ [0] Frame 7 (created first)          │
│ [1] Frame 8 (created second)         │
└──────────────────────────────────────┘

T=2ms: TCP end_rising received
       Need to match to a PENDING frame...
```

---

## ❌ BEFORE FIX (Wrong)

```python
for item in reversed(self.queue):  # Iterate from END to START
    if item.sensor_id_out is None:
        # First iteration: item = Frame 8 (newest)
        item.sensor_id_out = <new_id>
        return True
```

**Result**:
```
After end_rising signal:

Frame 7: sensor_id_in=100, sensor_id_out=?, status=PENDING    ❌ Not matched!
Frame 8: sensor_id_in=101, sensor_id_out=<value>, status=DONE ❌ Wrong frame!

Problem: Frame 8 (newest) matched instead of Frame 7 (oldest)
```

**Illustration**:
```
reversed(queue):
    ↓ Check Frame 8 first ← WRONG!
    ↓ Match to Frame 8 ← WRONG!

Queue:
├─ Frame 7 (should be first) ← Skipped
├─ Frame 8 (matched) ← Should be second
```

---

## ✅ AFTER FIX (Correct)

```python
for item in self.queue:  # Iterate from START to END
    if item.sensor_id_out is None:
        # First iteration: item = Frame 7 (oldest)
        item.sensor_id_out = <new_id>
        return True
```

**Result**:
```
After end_rising signal:

Frame 7: sensor_id_in=100, sensor_id_out=<value>, status=DONE   ✅ Matched first!
Frame 8: sensor_id_in=101, sensor_id_out=?, status=PENDING      ✅ Waiting for next

Success: Frame 7 (oldest) matched first - FIFO works!
```

**Illustration**:
```
normal queue iteration:
    ↓ Check Frame 7 first ✅
    ↓ Match to Frame 7 ✅

Queue:
├─ Frame 7 (matched) ✅ Correct!
├─ Frame 8 (waits for next) ✅ Correct!
```

---

## 📊 Multiple Frames Example

### Setup: 3 Frames Waiting

```
Queue:
┌─────────────────────────────────┐
│ [0] Frame 5 (created T=0ms)     │
│ [1] Frame 6 (created T=1ms)     │
│ [2] Frame 7 (created T=2ms)     │
└─────────────────────────────────┘

All have: sensor_id_out = None (PENDING)
```

### Before Fix ❌

```
Iteration order: Frame 7 → 6 → 5 (reversed)

Event 1 - end_rising:
  ❌ Matches Frame 7 (newest)
  Frame 5 and 6 still waiting

Event 2 - end_rising:
  ❌ Matches Frame 6
  Frame 5 still waiting

Event 3 - end_rising:
  ✅ Finally matches Frame 5

WRONG ORDER: 7 → 6 → 5 (reversed)
```

### After Fix ✅

```
Iteration order: Frame 5 → 6 → 7 (normal)

Event 1 - end_rising:
  ✅ Matches Frame 5 (oldest)
  Frame 6 and 7 waiting

Event 2 - end_rising:
  ✅ Matches Frame 6
  Frame 7 waiting

Event 3 - end_rising:
  ✅ Matches Frame 7

CORRECT ORDER: 5 → 6 → 7 (FIFO)
```

---

## 🎯 FIFO Principle

**FIFO = First In, First Out**

```
Queue:     First item ← Process this first!
┌────────────────────────┐
│ Frame 5 (oldest)  ◄─── Check first
│ Frame 6           ◄─── Check second
│ Frame 7 (newest)  ◄─── Check last
└────────────────────────┘
```

**Order of Processing**:
1. Frame 5 → matched first
2. Frame 6 → matched second
3. Frame 7 → matched third

---

## 🔍 Code Comparison

### Before ❌
```python
def add_sensor_out_event(self, sensor_id_out: int) -> bool:
    # "Matches to most recent frame" - WRONG comment!
    for item in reversed(self.queue):  # ← START FROM END
        if item.sensor_id_out is None:
            item.sensor_id_out = sensor_id_out
            item.completion_status = "DONE"
            return True  # Match to newest frame ❌
```

### After ✅
```python
def add_sensor_out_event(self, sensor_id_out: int) -> bool:
    # "Match to FIRST (oldest) PENDING frame" - CORRECT!
    for item in self.queue:  # ← START FROM BEGINNING
        if item.sensor_id_out is None:
            item.sensor_id_out = sensor_id_out
            item.completion_status = "DONE"
            return True  # Match to oldest frame ✅
```

---

## 📈 State Machine

### Before Fix ❌
```
Frame Creation Order:
  Frame 7 (T=0ms) → Created
  Frame 8 (T=1ms) → Created

end_rising Match Order:
  Frame 8 ← Matched first (WRONG!)
  Frame 7 ← Matched second (should be first!)

Problem: Reverse order!
```

### After Fix ✅
```
Frame Creation Order:
  Frame 7 (T=0ms) → Created
  Frame 8 (T=1ms) → Created

end_rising Match Order:
  Frame 7 ← Matched first ✅
  Frame 8 ← Matched second ✅

Success: Same order (FIFO)!
```

---

## 🧪 Test Case

### Input
```
Queue after start_rising signals:
- Frame ID 7, sensor_in=100, sensor_out=None, status=PENDING
- Frame ID 8, sensor_in=101, sensor_out=None, status=PENDING

end_rising signal arrives:
- sensor_id=200
```

### Expected Output (After Fix)
```
Frame ID 7:
  ✅ sensor_out = 200
  ✅ status = DONE

Frame ID 8:
  ✅ sensor_out = None (not matched)
  ✅ status = PENDING

Log: "Sensor OUT (FIFO): frame_id=7"
```

---

## ✨ Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Iteration** | `reversed()` (newest first) | Normal (oldest first) |
| **First match** | Newest frame ❌ | Oldest frame ✅ |
| **FIFO** | Broken ❌ | Working ✅ |
| **Order** | 8,7,6,5 | 5,6,7,8 ✅ |
| **Status** | Wrong ❌ | Fixed ✅ |

---

**Fixed**: 2025-11-11  
**Status**: ✅ FIFO now works correctly
