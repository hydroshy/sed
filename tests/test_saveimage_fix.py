#!/usr/bin/env python3
"""
Quick test to verify SaveImage tool name attribute fix
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_saveimage_tool_attributes():
    """Test that SaveImageTool has all required attributes"""
    try:
        from tools.saveimage_tool import SaveImageTool
        
        # Test 1: Create tool with default name
        tool1 = SaveImageTool()
        print(f"Tool1 - name: {getattr(tool1, 'name', 'MISSING')}")
        print(f"Tool1 - display_name: {getattr(tool1, 'display_name', 'MISSING')}")
        
        # Test 2: Create tool with custom name
        tool2 = SaveImageTool("Custom Save Image")
        print(f"Tool2 - name: {getattr(tool2, 'name', 'MISSING')}")
        print(f"Tool2 - display_name: {getattr(tool2, 'display_name', 'MISSING')}")
        
        # Test 3: Create tool with config
        config = {
            "directory": "/tmp",
            "structure_file": "test",
            "image_format": "PNG"
        }
        tool3 = SaveImageTool("Test Tool", config=config)
        print(f"Tool3 - name: {getattr(tool3, 'name', 'MISSING')}")
        print(f"Tool3 - display_name: {getattr(tool3, 'display_name', 'MISSING')}")
        print(f"Tool3 - directory: {tool3.directory}")
        print(f"Tool3 - structure_file: {tool3.structure_file}")
        print(f"Tool3 - image_format: {tool3.image_format}")
        
        # Verify all required attributes exist
        required_attrs = ['name', 'display_name', 'tool_id', 'config']
        for attr in required_attrs:
            if not hasattr(tool1, attr):
                print(f"ERROR: Missing attribute: {attr}")
                return False
            else:
                print(f"✓ Has attribute: {attr}")
        
        print("✓ All tests passed!")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_saveimage_tool_attributes()
    print(f"\nTest result: {'SUCCESS' if success else 'FAILED'}")
