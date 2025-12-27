import logging
import inspect
import os
import sys
from typing import Any, Optional

# Global debug mode flag
_DEBUG_MODE_ENABLED = False

def set_debug_mode(enabled: bool = False):
    """
    Set the logging level to DEBUG or INFO based on the debug flag
    
    Args:
        enabled (bool): True to enable debug logging, False for info level
    """
    global _DEBUG_MODE_ENABLED
    _DEBUG_MODE_ENABLED = bool(enabled)
    logging.getLogger().setLevel(logging.DEBUG if enabled else logging.INFO)
    if enabled:
        logging.debug("Debug logging enabled")

def is_debug_mode() -> bool:
    """Check if debug mode is currently enabled"""
    global _DEBUG_MODE_ENABLED
    return _DEBUG_MODE_ENABLED

def conditional_print(*args, **kwargs):
    """
    Print to console ONLY if debug mode is explicitly enabled via --debug flag.
    
    Args:
        *args: Values to print
        **kwargs: Keyword arguments passed to print function
    """
    if _DEBUG_MODE_ENABLED:
        print(*args, **kwargs)
        sys.stdout.flush()

def debug_log(message: str, value: Any = None, module: Optional[str] = None):
    """
    Log debug message with optional value and module name
    
    Args:
        message (str): Debug message to log
        value (Any, optional): Value to include in debug message
        module (str, optional): Module name to include in debug message. If None,
                              will try to determine from call stack
    """
    logger = logging.getLogger(module or _get_caller_module())
    
    if value is not None:
        logger.debug(f"{message}: {value}")
    else:
        logger.debug(message)

def debug_print(*args, **kwargs):
    """
    Print debug message to stderr. Useful for immediate feedback during development.
    Prints only if debug mode is explicitly enabled via --debug flag.
    
    Args:
        *args: Values to print
        **kwargs: Keyword arguments passed to print function
    """
    # Only print if --debug mode is explicitly enabled
    if _DEBUG_MODE_ENABLED:
        kwargs['file'] = sys.stderr
        print(*args, **kwargs)
        sys.stderr.flush()

def _get_caller_module() -> str:
    """Get the module name of the calling function"""
    frame = inspect.currentframe()
    try:
        # Go up 2 frames to get past debug_log and _get_caller_module
        frame = frame.f_back.f_back
        module = inspect.getmodule(frame)
        if module:
            return module.__name__
        return os.path.basename(frame.f_code.co_filename)
    except (AttributeError, ValueError):
        return "__main__"
    finally:
        del frame  # Avoid circular references