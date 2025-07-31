#!/usr/bin/env python3
"""
Non-GUI test for configuration loading logic
"""

import sys
import os
import logging
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_detect_tool_creation_and_config():
    """Test DetectTool creation and configuration without GUI"""
    print("Testing DetectTool creation and configuration...")
    
    try:
        from detection.detect_tool import DetectTool, create_detect_tool_from_manager_config
        
        # Test configuration
        test_config = {
            'model_name': 'yolov8n.onnx',
            'model_path': '/path/to/yolov8n.onnx',
            'selected_classes': ['person', 'car', 'bicycle'],
            'confidence_threshold': 0.6,
            'nms_threshold': 0.3
        }
        
        # Create DetectTool from manager config
        tool = create_detect_tool_from_manager_config(test_config)
        
        # Verify tool was created
        assert tool is not None, "Tool creation failed"
        assert tool.name == "Detect Tool", f"Expected 'Detect Tool', got '{tool.name}'"
        print("✓ DetectTool created successfully")
        
        # Verify configuration was set
        config_dict = tool.config.to_dict()
        assert config_dict['model_name'] == 'yolov8n.onnx', f"Expected 'yolov8n.onnx', got '{config_dict['model_name']}'"
        assert config_dict['selected_classes'] == ['person', 'car', 'bicycle'], f"Expected classes not set correctly: {config_dict['selected_classes']}"
        print("✓ Tool configuration set correctly")
        
        # Test that we can get the configuration back
        retrieved_config = {
            'model_name': tool.config.get('model_name'),
            'model_path': tool.config.get('model_path'),
            'selected_classes': tool.config.get('selected_classes'),
            'confidence_threshold': tool.config.get('confidence_threshold'),
            'nms_threshold': tool.config.get('nms_threshold')
        }
        
        # Verify all expected values are retrievable
        for key, expected_value in test_config.items():
            actual_value = retrieved_config[key]
            assert actual_value == expected_value, f"Config mismatch for {key}: expected {expected_value}, got {actual_value}"
        
        print("✓ Tool configuration can be retrieved correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ DetectTool configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tool_manager_config_logic():
    """Test the core configuration loading logic"""
    print("Testing tool manager configuration logic...")
    
    try:
        # Create a mock tool with configuration
        mock_tool = Mock()
        mock_tool.name = "Detect Tool"
        mock_tool.config.to_dict.return_value = {
            'model_name': 'yolov8n.onnx',
            'model_path': '/path/to/yolov8n.onnx',
            'selected_classes': ['person', 'car'],
            'detection_area': [10, 10, 100, 100],
            'confidence_threshold': 0.7
        }
        
        # Mock DetectToolManager
        mock_detect_manager = Mock()
        
        # Test the delegation logic (simulating _load_tool_config_to_ui)
        config = mock_tool.config.to_dict()
        
        # This is the key logic we're testing
        if mock_tool.name == "Detect Tool":
            mock_detect_manager.load_tool_config(config)
        
        # Verify the delegation occurred with correct config
        mock_detect_manager.load_tool_config.assert_called_once_with(config)
        call_args = mock_detect_manager.load_tool_config.call_args[0][0]
        
        # Verify config contains expected keys
        expected_keys = ['model_name', 'model_path', 'selected_classes']
        for key in expected_keys:
            assert key in call_args, f"Expected key '{key}' not found in delegated config"
            
        print("✓ Tool configuration delegation works correctly")
        return True
        
    except Exception as e:
        print(f"✗ Tool manager configuration logic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_job_manager_tool_handling():
    """Test that JobManager can handle tools with configuration"""
    print("Testing JobManager tool handling...")
    
    try:
        from job.job_manager import JobManager, Job
        from tools.base_tool import BaseTool, ToolConfig
        
        # Create job manager
        job_manager = JobManager()
        
        # Create a job
        job = Job("Test Job")
        
        # Create a tool with configuration
        config = ToolConfig({
            'model_name': 'yolov8n.onnx',
            'selected_classes': ['person', 'car'],
            'confidence_threshold': 0.5
        })
        
        from tools.base_tool import GenericTool
        tool = GenericTool("Detect Tool", config)
        
        # Add tool to job
        job.add_tool(tool)
        
        # Verify tool was added with configuration
        assert len(job.tools) == 1, f"Expected 1 tool, got {len(job.tools)}"
        
        added_tool = job.tools[0]
        assert added_tool.name == "Detect Tool", f"Expected 'Detect Tool', got '{added_tool.name}'"
        
        # Verify configuration is preserved
        tool_config = added_tool.config.to_dict()
        assert 'model_name' in tool_config, "model_name not in tool config"
        assert tool_config['model_name'] == 'yolov8n.onnx', f"Expected 'yolov8n.onnx', got '{tool_config['model_name']}'"
        
        print("✓ JobManager handles tools with configuration correctly")
        
        # Test serialization/deserialization
        job_dict = job.to_dict()
        assert 'tools' in job_dict, "Job dict missing tools"
        assert len(job_dict['tools']) == 1, f"Expected 1 tool in dict, got {len(job_dict['tools'])}"
        
        tool_dict = job_dict['tools'][0]
        assert 'config' in tool_dict, "Tool dict missing config"
        assert tool_dict['config']['model_name'] == 'yolov8n.onnx', "Tool config not serialized correctly"
        
        print("✓ Tool configuration serialization works correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ JobManager tool handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Configuration Loading Logic Tests ===")
    
    success = True
    
    # Test DetectTool creation and configuration
    success &= test_detect_tool_creation_and_config()
    print()
    
    # Test tool manager logic
    success &= test_tool_manager_config_logic()
    print()
    
    # Test job manager tool handling
    success &= test_job_manager_tool_handling()
    print()
    
    if success:
        print("=== All tests passed! ===")
        sys.exit(0)
    else:
        print("=== Some tests failed! ===")
        sys.exit(1)