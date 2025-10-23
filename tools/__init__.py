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

# Import main tool classes
try:
    from .base_tool import BaseTool, ToolConfig
    from .result_tool import ResultTool
except ImportError as e:
    logging.warning(f"Error importing tool modules: {e}")