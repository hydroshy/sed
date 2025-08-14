#!/usr/bin/env python3
"""
Minimal test to replicate the exact SaveImageTool creation
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def minimal_test():
    """Minimal test of SaveImageTool creation"""
    print("=== Minimal SaveImageTool Test ===")
    
    try:
        # Import
        from tools.saveimage_tool import SaveImageTool
        print("✓ Import successful")
        
        # Create with exact same parameters as in the error
        config = {
            'directory': '/home/pi/Desktop/project/image', 
            'structure_file': 'test', 
            'image_format': 'JPG'
        }
        
        print(f"Creating tool with config: {config}")
        tool = SaveImageTool("Save Image", config=config)
        print("✓ Tool creation successful")
        
        # Check attributes
        print(f"Checking attributes...")
        print(f"  hasattr(tool, 'name'): {hasattr(tool, 'name')}")
        print(f"  hasattr(tool, 'display_name'): {hasattr(tool, 'display_name')}")
        
        if hasattr(tool, 'name'):
            print(f"  tool.name: '{tool.name}'")
        else:
            print("  tool.name: MISSING!")
            
        if hasattr(tool, 'display_name'):
            print(f"  tool.display_name: '{tool.display_name}'")
        else:
            print("  tool.display_name: MISSING!")
            
        # Try the exact access that's failing
        try:
            name_val = tool.name
            print(f"✓ Direct name access successful: '{name_val}'")
        except AttributeError as e:
            print(f"✗ Direct name access failed: {e}")
            return False
            
        print("✓ All checks passed!")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = minimal_test()
    print(f"\nResult: {'SUCCESS' if success else 'FAILURE'}")
