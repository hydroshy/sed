#!/usr/bin/env python3
"""
Complete test for SaveImageTool to verify it can save images correctly
"""

import sys
import os
import numpy as np
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_image():
    """Create a test image as numpy array"""
    # Create a simple test image (100x100 RGB)
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    # Add some colored stripes for visual verification
    image[:33, :, 0] = 255  # Red stripe
    image[33:66, :, 1] = 255  # Green stripe
    image[66:, :, 2] = 255  # Blue stripe
    return image

def test_saveimage_tool():
    """Test SaveImageTool functionality"""
    print("=== Testing SaveImageTool ===")
    
    try:
        from tools.saveimage_tool import SaveImageTool
        print("✓ Successfully imported SaveImageTool")
        
        # Create temporary directory for testing
        test_dir = tempfile.mkdtemp(prefix="saveimage_test_")
        print(f"✓ Created test directory: {test_dir}")
        
        # Test configuration
        config = {
            "directory": test_dir,
            "structure_file": "test_image",
            "image_format": "JPG",
            "auto_save": True
        }
        
        # Create SaveImageTool
        tool = SaveImageTool("Test Save Image Tool", config=config)
        print("✓ SaveImageTool created successfully")
        print(f"  - Name: {tool.name}")
        print(f"  - Directory: {tool.directory}")
        print(f"  - Structure file: {tool.structure_file}")
        print(f"  - Format: {tool.image_format}")
        
        # Create test image
        test_image = create_test_image()
        print(f"✓ Created test image with shape: {test_image.shape}")
        
        # Test 1: Direct save_image_array method
        print("\n--- Test 1: Direct save_image_array ---")
        filepath1 = tool.save_image_array(test_image)
        if filepath1 and os.path.exists(filepath1):
            file_size = os.path.getsize(filepath1)
            print(f"✓ Direct save successful: {filepath1} (size: {file_size} bytes)")
        else:
            print(f"✗ Direct save failed: {filepath1}")
            return False
        
        # Test 2: Process method (should auto-save)
        print("\n--- Test 2: Process method ---")
        processed_image, result = tool.process(test_image)
        print(f"Process result: {result}")
        
        if result.get("saved"):
            filepath2 = result.get("filepath")
            if filepath2 and os.path.exists(filepath2):
                file_size = os.path.getsize(filepath2)
                print(f"✓ Process save successful: {filepath2} (size: {file_size} bytes)")
            else:
                print(f"✗ Process save failed: {filepath2}")
                return False
        else:
            print(f"✗ Process method did not save image: {result}")
            return False
        
        # Test 3: Multiple saves (should increment filename)
        print("\n--- Test 3: Multiple saves ---")
        saved_files = []
        for i in range(3):
            filepath = tool.save_image_array(test_image)
            if filepath and os.path.exists(filepath):
                saved_files.append(filepath)
                print(f"✓ Save {i+1}: {os.path.basename(filepath)}")
            else:
                print(f"✗ Save {i+1} failed")
                return False
        
        # Verify all files were created
        total_files = len([f for f in os.listdir(test_dir) if f.endswith('.jpg')])
        print(f"✓ Total JPG files in directory: {total_files}")
        
        # Test 4: Different format (PNG)
        print("\n--- Test 4: PNG format ---")
        tool.update_config({"image_format": "PNG"})
        filepath_png = tool.save_image_array(test_image)
        if filepath_png and os.path.exists(filepath_png) and filepath_png.endswith('.png'):
            file_size = os.path.getsize(filepath_png)
            print(f"✓ PNG save successful: {os.path.basename(filepath_png)} (size: {file_size} bytes)")
        else:
            print(f"✗ PNG save failed: {filepath_png}")
            return False
        
        print(f"\n✓ All tests passed! Files saved in: {test_dir}")
        
        # List all created files
        files = os.listdir(test_dir)
        files.sort()
        print("Created files:")
        for file in files:
            filepath = os.path.join(test_dir, file)
            size = os.path.getsize(filepath)
            print(f"  - {file} ({size} bytes)")
        
        # Clean up
        print(f"\nCleaning up test directory: {test_dir}")
        shutil.rmtree(test_dir)
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to clean up on error
        if 'test_dir' in locals() and os.path.exists(test_dir):
            try:
                shutil.rmtree(test_dir)
                print(f"Cleaned up test directory: {test_dir}")
            except:
                pass
        
        return False

if __name__ == "__main__":
    success = test_saveimage_tool()
    print(f"\nTest result: {'SUCCESS' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
