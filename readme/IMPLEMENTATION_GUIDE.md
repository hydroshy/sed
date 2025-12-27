# 📋 Logging Optimization - Implementation Guide

## Quick Start

### 1️⃣ For End Users

**Run normally** (production mode):
```bash
python main.py
```
✅ Terminal clean
✅ Logs saved to `sed_app.log`

**Run with debug** (when troubleshooting):
```bash
python main.py --debug
```
✅ DEBUG messages in terminal
✅ Logs saved to `sed_app.log`

---

### 2️⃣ For Developers

**Understanding the changes:**

The logging system now has **two layers**:

1. **File Logging** (Always On)
   - Captures: ALL levels (DEBUG, INFO, WARNING, ERROR)
   - Format: Full timestamps + module names
   - File: `sed_app.log`
   - Purpose: Complete audit trail

2. **Console Logging** (Conditional)
   - Normal mode: OFF (clean terminal)
   - Debug mode: Only DEBUG messages
   - Format: Simple `DEBUG: [message]`
   - Purpose: Development feedback

---

## Architecture

### Handler Flow

```
Logger (root)
├── FileHandler (sed_app.log)
│   ├── Level: DEBUG
│   ├── Format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
│   └── Always ON
│
└── StreamHandler (console) [Only if --debug]
    ├── DebugOnlyStreamHandler (filters DEBUG only)
    ├── Level: DEBUG..INFO (only DEBUG passes)
    ├── Format: "DEBUG: %(message)s"
    └── Conditional (on --debug)
```

### Log Record Flow

```
Logger Call (e.g., logger.debug("message"))
    ↓
Level Check (>= DEBUG ✓)
    ↓
Handlers
├→ FileHandler: Write to file ✅
└→ StreamHandler (if enabled):
   ├→ DebugOnlyStreamHandler.emit()
   ├→ Level Check: >= DEBUG and < INFO ✓
   └→ Print to console ✅
```

---

## Implementation Details

### Custom Handler Class

**Location**: `main.py` (lines 8-13)

```python
class DebugOnlyStreamHandler(logging.StreamHandler):
    """Custom handler that only outputs DEBUG level messages to terminal"""
    def emit(self, record):
        # Only allow DEBUG level (10) but not INFO level (20)
        if record.levelno >= logging.DEBUG and record.levelno < logging.INFO:
            super().emit(record)
```

**Key Points**:
- Inherits from `logging.StreamHandler`
- Overrides `emit()` method
- Filters messages before output
- Level comparison: DEBUG=10, INFO=20

### Logging Setup

**Location**: `main.py` (lines 58-75)

**Step 1**: Create file handler
```python
file_handler = logging.FileHandler('sed_app.log')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
```

**Step 2**: Configure root logger with file handler
```python
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[file_handler]
)
```

**Step 3**: Conditionally add stream handler
```python
if args.debug:
    debug_stream_handler = DebugOnlyStreamHandler()
    debug_formatter = logging.Formatter('DEBUG: %(message)s')
    debug_stream_handler.setFormatter(debug_formatter)
    logging.getLogger().addHandler(debug_stream_handler)
```

---

## Using the System

### Basic Usage

```python
import logging

# Get logger for your module
logger = logging.getLogger(__name__)

# Use it normally - handlers take care of output
logger.debug("Debugging info")
logger.info("Informational message")
logger.warning("Warning message")
logger.error("Error message")
```

### What happens in different modes

**Normal Mode** (`python main.py`):
```
logger.debug("message")   → ✅ Saved to file, ❌ Not on terminal
logger.info("message")    → ✅ Saved to file, ❌ Not on terminal
logger.warning("message") → ✅ Saved to file, ❌ Not on terminal
logger.error("message")   → ✅ Saved to file, ❌ Not on terminal
```

**Debug Mode** (`python main.py --debug`):
```
logger.debug("message")   → ✅ Saved to file, ✅ Terminal: "DEBUG: message"
logger.info("message")    → ✅ Saved to file, ❌ Not on terminal
logger.warning("message") → ✅ Saved to file, ❌ Not on terminal
logger.error("message")   → ✅ Saved to file, ❌ Not on terminal
```

---

## Configuration Changes in Files

### main.py
```python
# OLD: Both file and console handlers, always active
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler('sed_app.log'),
        logging.StreamHandler()  # Always shows everything
    ]
)

# NEW: File always, console only if --debug
file_handler = logging.FileHandler('sed_app.log')
logging.basicConfig(level=logging.DEBUG, handlers=[file_handler])
if args.debug:
    debug_handler = DebugOnlyStreamHandler()
    logging.getLogger().addHandler(debug_handler)
```

### camera_view.py
```python
# OLD: Duplicate basicConfig in module
logging.basicConfig(level=logging.DEBUG, format='...')

# NEW: Use module logger (inherits from root)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
```

### main_window.py
```python
# OLD: Duplicate basicConfig in module
logging.basicConfig(level=logging.DEBUG, format='...')

# NEW: Use module logger (inherits from root)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
```

---

## Testing the System

### Test Script: `test_logging_opt.py`

```bash
# Test normal mode
$ python test_logging_opt.py
=== NORMAL MODE ===
(No log output - logs in file)

# Test debug mode
$ python test_logging_opt.py --debug
=== DEBUG MODE ===
DEBUG: This is a DEBUG message
(Other levels in file only)
```

### Manual Testing

```bash
# Start app normally
$ python main.py &
# Terminal is clean ✨

# Check logs
$ tail -f sed_app.log
2025-12-19 15:31:44,855 - root - INFO - [message]
2025-12-19 15:31:44,855 - root - DEBUG - [message]

# Kill the app and start with debug
$ python main.py --debug
DEBUG: Debug logging enabled...
DEBUG: [message]
DEBUG: [message]
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No DEBUG messages | Run with `--debug` flag |
| Logs not saved | Check if `sed_app.log` is created |
| Still seeing INFO | Make sure using updated main.py |
| Terminal has output | Check if parent process adds logs |

---

## Best Practices

✅ **DO**:
- Use `logger.debug()` for detailed information
- Use `logger.info()` for important milestones  
- Use `logger.warning()` for issues
- Use `logger.error()` for problems
- Always use `logging.getLogger(__name__)` in modules

❌ **DON'T**:
- Don't use `print()` for debugging (use logger.debug)
- Don't call `basicConfig` in modules (only in main.py)
- Don't mix print() and logging calls
- Don't ignore exceptions in logging

---

## Files Overview

| File | Purpose | Modified |
|------|---------|----------|
| `main.py` | Central logging config | ✅ Yes |
| `camera_stream.py` | Camera module | ❌ No |
| `camera_view.py` | Display module | ✅ Yes |
| `main_window.py` | Main UI | ✅ Yes |
| `test_logging_opt.py` | Test script | ✅ New |
| `LOGGING_*.md` | Documentation | ✅ New |

---

## Performance Impact

**Before Optimization**:
- ❌ 2 handlers active always
- ❌ Console I/O every log call
- ❌ Clutter and noise

**After Optimization**:
- ✅ 1 handler in normal mode
- ✅ File I/O only in normal mode
- ✅ Clean output

**Result**: No negative performance impact, actually slightly faster in normal mode!

---

## Migration Checklist

- [x] Add `DebugOnlyStreamHandler` class to main.py
- [x] Configure file handler separately
- [x] Make stream handler conditional on --debug
- [x] Remove basicConfig from camera_view.py
- [x] Remove basicConfig from main_window.py
- [x] Update module loggers to use getLogger()
- [x] Test logging in both modes
- [x] Create documentation
- [x] Verify backward compatibility

---

## Next Steps

1. **Use it**: Run `python main.py --debug` to see DEBUG messages
2. **Monitor**: Check `sed_app.log` for complete history
3. **Maintain**: Keep logging calls as-is, no changes needed
4. **Extend**: Can add email/syslog handlers if needed

---

## Questions?

**Q: Can I customize the format?**
A: Yes, modify formatter in main.py

**Q: Can I add more handlers?**
A: Yes, add them like the debug handler

**Q: How to log only specific modules?**
A: Set level on individual loggers: `logging.getLogger('module').setLevel(logging.DEBUG)`

**Q: Where are old logs?**
A: Appended to `sed_app.log` (file not cleared on startup)

---

## Summary

✨ **Clean terminal** in normal mode
✨ **Focused debugging** with --debug
✨ **Complete history** in file logs
✨ **Professional quality** logging system
✨ **Zero breaking changes**

**You're all set!** 🚀
