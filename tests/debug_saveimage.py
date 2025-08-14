#!/usr/bin/env python3
"""
Debug script to check SaveImageTool attributes
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_saveimage_tool():
    """Debug SaveImageTool creation and attributes"""
    print("=== Debugging SaveImageTool ===")
    
    try:
        # Import the tool
        from tools.saveimage_tool import SaveImageTool
        print("✓ Successfully imported SaveImageTool")
        
        # Create tool with config like in the error
        config = {
            'directory': '/home/pi/Desktop/project/image', 
            'structure_file': 'test', 
            'image_format': 'JPG'
        }
        
        print(f"Creating tool with config: {config}")
        tool = SaveImageTool("Save Image", config=config)
        print("✓ Successfully created SaveImageTool")
        
        # Check all attributes
        print("\n=== Tool Attributes ===")
        print(f"type(tool): {type(tool)}")
        print(f"tool.__class__.__name__: {tool.__class__.__name__}")
        
        # Check for name attribute
        if hasattr(tool, 'name'):
            print(f"✓ tool.name: {tool.name}")
        else:
            print("✗ tool.name: MISSING")
            
        # Check for display_name attribute
        if hasattr(tool, 'display_name'):
            print(f"✓ tool.display_name: {tool.display_name}")
        else:
            print("✗ tool.display_name: MISSING")
            
        # Check for tool_id attribute
        if hasattr(tool, 'tool_id'):
            print(f"✓ tool.tool_id: {tool.tool_id}")
        else:
            print("✗ tool.tool_id: MISSING")
            
        # Check for config attribute
        if hasattr(tool, 'config'):
            print(f"✓ tool.config: {tool.config}")
        else:
            print("✗ tool.config: MISSING")
            
        # Check configuration values
        print(f"✓ tool.directory: {tool.directory}")
        print(f"✓ tool.structure_file: {tool.structure_file}")
        print(f"✓ tool.image_format: {tool.image_format}")
        
        # Test the exact line that's failing
        print(f"\n=== Testing problematic access ===")
        try:
            name_value = tool.name
            print(f"✓ tool.name access successful: {name_value}")
        except AttributeError as e:
            print(f"✗ tool.name access failed: {e}")
            
        # Check all attributes using dir()
        print(f"\n=== All tool attributes ===")
        attrs = [attr for attr in dir(tool) if not attr.startswith('_')]
        for attr in attrs:
            try:
                value = getattr(tool, attr)
                if not callable(value):
                    print(f"  {attr}: {value}")
            except:
                print(f"  {attr}: <error accessing>")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_saveimage_tool()
