#!/usr/bin/env python3
"""
Test script to verify SaveImage tool integration with the GUI system
"""

import sys
import os
import tempfile
import numpy as np
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_saveimage_tool_creation():
    """Test SaveImage tool creation and basic functionality"""
    logger.info("Testing SaveImage tool creation...")
    
    try:
        from tools.saveimage_tool import SaveImageTool
        from tools.base_tool import ToolConfig
        
        # Test 1: Basic tool creation
        tool = SaveImageTool()
        assert tool.display_name == "Save Image"
        assert tool.config.get("image_format") == "JPG"
        logger.info("✓ Basic tool creation successful")
        
        # Test 2: Tool creation with config
        config = {
            "directory": tempfile.gettempdir(),
            "structure_file": "test_image",
            "image_format": "PNG"
        }
        tool_with_config = SaveImageTool("Test Save Image", config=config)
        assert tool_with_config.directory == tempfile.gettempdir()
        assert tool_with_config.structure_file == "test_image"
        assert tool_with_config.image_format == "PNG"
        logger.info("✓ Tool creation with config successful")
        
        # Test 3: Process method
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        result_image, result_data = tool_with_config.process(test_image)
        assert result_data["tool_name"] == "Test Save Image"
        assert "saved" in result_data
        logger.info("✓ Process method works")
        
        return True
        
    except Exception as e:
        logger.error(f"SaveImage tool creation test failed: {e}")
        return False

def test_tool_registration():
    """Test SaveImage tool registration in JobManager"""
    logger.info("Testing SaveImage tool registration...")
    
    try:
        from job.job_manager import JobManager
        from tools.saveimage_tool import SaveImageTool
        
        # Create job manager (should auto-register tools)
        job_manager = JobManager()
        
        # Check if SaveImageTool is registered
        assert "SaveImageTool" in job_manager.tool_registry
        logger.info("✓ SaveImageTool is registered in JobManager")
        
        # Test tool creation through registry
        tool = job_manager.create_tool("SaveImageTool", "Test Save", {})
        assert tool is not None
        assert isinstance(tool, SaveImageTool)
        logger.info("✓ Tool creation through registry works")
        
        return True
        
    except Exception as e:
        logger.error(f"Tool registration test failed: {e}")
        return False

def test_settings_manager_integration():
    """Test SaveImage tool integration with SettingsManager"""
    logger.info("Testing SettingsManager integration...")
    
    try:
        from gui.settings_manager import SettingsManager
        
        # Create settings manager
        settings_manager = SettingsManager()
        
        # Check tool mapping
        assert "Save Image" in settings_manager.tool_to_page_mapping
        assert settings_manager.tool_to_page_mapping["Save Image"] == "save_image"
        logger.info("✓ Tool mapping exists in SettingsManager")
        
        return True
        
    except Exception as e:
        logger.error(f"SettingsManager integration test failed: {e}")
        return False

def test_filename_generation():
    """Test filename generation functionality"""
    logger.info("Testing filename generation...")
    
    try:
        from tools.saveimage_tool import SaveImageTool
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "directory": temp_dir,
                "structure_file": "test",
                "image_format": "JPG"
            }
            
            tool = SaveImageTool("Test", config=config)
            
            # Test filename generation
            filename1 = tool.get_next_filename()
            assert filename1.endswith("test_1.jpg")
            logger.info(f"✓ First filename: {os.path.basename(filename1)}")
            
            # Create a dummy file to test increment
            with open(filename1, 'w') as f:
                f.write("dummy")
            
            filename2 = tool.get_next_filename()
            assert filename2.endswith("test_2.jpg")
            logger.info(f"✓ Second filename: {os.path.basename(filename2)}")
            
        return True
        
    except Exception as e:
        logger.error(f"Filename generation test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting SaveImage tool integration tests...")
    
    tests = [
        test_saveimage_tool_creation,
        test_tool_registration,
        test_settings_manager_integration,
        test_filename_generation
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
                logger.info(f"✓ {test.__name__} PASSED")
            else:
                failed += 1
                logger.error(f"✗ {test.__name__} FAILED")
        except Exception as e:
            failed += 1
            logger.error(f"✗ {test.__name__} FAILED with exception: {e}")
    
    logger.info(f"\nTest Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        logger.info("🎉 All tests passed! SaveImage tool integration is working correctly.")
        return True
    else:
        logger.error("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
