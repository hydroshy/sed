"""
Debug utilities for controlling debug output
"""
import logging
import os
import sys

# Global debug state - will be set by main.py
_DEBUG_MODE = False

def set_debug_mode(enabled):
    """Set global debug mode"""
    global _DEBUG_MODE
    _DEBUG_MODE = enabled

def is_debug_mode():
    """Check if debug mode is enabled"""
    global _DEBUG_MODE
    
    # Check multiple sources for debug mode
    if _DEBUG_MODE:
        return True
    
    # Check if logging is at DEBUG level
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        return True
    
    # Check command line args
    if '--debug' in sys.argv or '-d' in sys.argv:
        return True
    
    # Check environment variable
    if os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes'):
        return True
    
    return False

def debug_print(message, category="DEBUG"):
    """Print debug message only if debug mode is enabled"""
    if is_debug_mode():
        print(f"{category}: {message}")

def debug_log(message, level=logging.DEBUG):
    """Log debug message using logging system"""
    if is_debug_mode():
        logging.log(level, message)