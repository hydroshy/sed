#!/usr/bin/env python3
"""
Test the exact scenario that's failing in the GUI
"""

import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging to match the application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_exact_scenario():
    """Test the exact scenario from the error log"""
    print("=== Testing Exact Scenario ===")
    
    try:
        # Import exactly as in the tool manager
        from tools.saveimage_tool import SaveImageTool
        
        # Create config exactly as in the error log
        config = {
            'directory': '/home/pi/Desktop/project/image', 
            'structure_file': 'test', 
            'image_format': 'JPG'
        }
        
        print(f"Creating SaveImageTool with config: {config}")
        
        # Create tool exactly as in tool manager
        tool = SaveImageTool("Save Image", config=config)
        
        print(f"Tool created successfully!")
        print(f"Tool type: {type(tool)}")
        
        # Test the exact access that's failing
        print(f"Testing tool.name access...")
        name_value = tool.name
        print(f"✓ tool.name = '{name_value}'")
        
        print(f"Testing tool.display_name access...")
        display_name_value = tool.display_name
        print(f"✓ tool.display_name = '{display_name_value}'")
        
        # Test hasattr like in the tool manager
        print(f"Testing hasattr(tool, 'name')...")
        has_name = hasattr(tool, 'name')
        print(f"✓ hasattr(tool, 'name') = {has_name}")
        
        if not has_name:
            print("ERROR: Tool doesn't have name attribute!")
            return False
            
        # Test the exact debug print from tool manager
        print(f"Testing exact debug print from tool manager...")
        debug_msg = f"DEBUG: Created SaveImage tool: name={tool.name}, display_name={tool.display_name}"
        print(debug_msg)
        
        print("✓ All tests passed!")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tool_manager_scenario():
    """Test the tool manager scenario"""
    print("\n=== Testing Tool Manager Scenario ===")
    
    try:
        # Simulate the tool manager scenario
        from gui.tool_manager import ToolManager
        from job.job_manager import JobManager
        
        # Create managers
        job_manager = JobManager()
        tool_manager = ToolManager()
        tool_manager.job_manager = job_manager
        
        # Set pending tool and config like in the real scenario
        tool_manager._pending_tool = "Save Image"
        tool_manager._pending_tool_config = {
            'directory': '/home/pi/Desktop/project/image', 
            'structure_file': 'test', 
            'image_format': 'JPG'
        }
        
        print(f"Calling tool_manager.on_apply_setting()...")
        
        # This should replicate the exact error
        result = tool_manager.on_apply_setting()
        
        print(f"✓ Tool manager call successful! Result: {result}")
        return True
        
    except Exception as e:
        print(f"ERROR in tool manager scenario: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing SaveImage tool integration...")
    
    success1 = test_exact_scenario()
    success2 = test_tool_manager_scenario()
    
    if success1 and success2:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Some tests failed!")
