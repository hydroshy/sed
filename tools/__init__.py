#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tools package initialization
"""

# Cài đặt để đảm bảo modules luôn được reload 
# khi có thay đổi trong quá trình phát triển
import sys
import importlib
import logging

# Cấu hình logging nếu chưa được cấu hình
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, 
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Force reload module button_trigger_camera nếu đã import trước đó
if 'tools.button_trigger_camera' in sys.modules:
    try:
        # Đảm bảo mọi tài nguyên GPIO được giải phóng trước khi reload
        if hasattr(sys.modules['tools.button_trigger_camera'], 'cleanup_trigger'):
            try:
                sys.modules['tools.button_trigger_camera'].cleanup_trigger()
                logging.info("Cleaned up GPIO resources before reloading button_trigger_camera")
            except Exception as e:
                logging.warning(f"Error cleaning up before reload: {e}")
        
        # Reload module
        importlib.reload(sys.modules['tools.button_trigger_camera'])
        logging.info("Reloaded button_trigger_camera module successfully")
    except Exception as e:
        logging.error(f"Error reloading button_trigger_camera: {e}")

# Xuất các modules quan trọng để dễ sử dụng
from . import button_trigger_camera