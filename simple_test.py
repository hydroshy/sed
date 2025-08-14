#!/usr/bin/env python3

# Simple test without complex imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing SaveImageTool...")

try:
    from tools.saveimage_tool import SaveImageTool
    print("Import OK")
    
    tool = SaveImageTool()
    print("Creation OK")
    
    print(f"name: {getattr(tool, 'name', 'MISSING')}")
    print(f"display_name: {getattr(tool, 'display_name', 'MISSING')}")
    
    # Test with config
    config = {'directory': '/tmp', 'structure_file': 'test', 'image_format': 'JPG'}
    tool2 = SaveImageTool("Test", config=config)
    print("Creation with config OK")
    
    print(f"tool2.name: {getattr(tool2, 'name', 'MISSING')}")
    print(f"tool2.display_name: {getattr(tool2, 'display_name', 'MISSING')}")
    
    print("SUCCESS")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
