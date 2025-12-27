#!/usr/bin/env python
"""Test script để kiểm tra logging optimization"""

import logging
import sys

# Simulate the logging setup from main.py
class DebugOnlyStreamHandler(logging.StreamHandler):
    """Custom handler that only outputs DEBUG level messages to terminal"""
    def emit(self, record):
        # Only show DEBUG level messages to console, everything else goes to file only
        if record.levelno >= logging.DEBUG and record.levelno < logging.INFO:
            super().emit(record)

# Setup logging like main.py does
file_handler = logging.FileHandler('test_logging.log')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[file_handler]
)

# Test with --debug flag
if '--debug' in sys.argv:
    print("=== DEBUG MODE ON ===")
    debug_stream_handler = DebugOnlyStreamHandler()
    debug_formatter = logging.Formatter('DEBUG: %(message)s')
    debug_stream_handler.setFormatter(debug_formatter)
    logging.getLogger().addHandler(debug_stream_handler)
else:
    print("=== NORMAL MODE (No terminal output) ===")

logger = logging.getLogger(__name__)

# Test different log levels
print("\nLogging test messages...")
print("(Check test_logging.log for all messages)")
print()

logger.debug("This is a DEBUG message")
logger.info("This is an INFO message")
logger.warning("This is a WARNING message")
logger.error("This is an ERROR message")

print("\nTest complete. Check test_logging.log for full output.")
print("In DEBUG mode, you should see: 'DEBUG: This is a DEBUG message'")
print("In NORMAL mode, you should see: nothing above (only in log file)")
