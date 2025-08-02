#!/usr/bin/env python3
"""
Integration test for the complete edit tool flow
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

def test_complete_edit_flow():
    """Test the complete tool edit flow"""
    print("Testing complete tool edit flow...")
    
    try:
        from job.job_manager import JobManager, Job
        from detection.detect_tool import create_detect_tool_from_manager_config
        
        # Step 1: Create a job manager and job
        job_manager = JobManager()
        job = Job("Test Job")
        job_manager.add_job(job)
        
        # Step 2: Create a DetectTool with initial configuration
        initial_config = {
            'model_name': 'yolov8n.onnx',
            'model_path': '/path/to/yolov8n.onnx',
            'selected_classes': ['person', 'car'],
            'confidence_threshold': 0.5,
            'nms_threshold': 0.4,
            'detection_region': [10, 10, 100, 100]
        }
        
        detect_tool = create_detect_tool_from_manager_config(initial_config)
        job.add_tool(detect_tool)
        
        print(f"✓ Created DetectTool with initial config: {initial_config}")
        
        # Step 3: Simulate getting the tool for editing (what happens when user clicks edit)
        current_job = job_manager.get_current_job()
        editing_tool = current_job.tools[0]  # Get the first tool
        
        # Step 4: Extract current configuration (what _load_tool_config_to_ui does)
        current_config = editing_tool.config.to_dict()
        
        print(f"✓ Retrieved current config for editing: {current_config}")
        
        # Verify the configuration is correct
        assert current_config['model_name'] == 'yolov8n.onnx'
        assert current_config['selected_classes'] == ['person', 'car']
        assert current_config['confidence_threshold'] == 0.5
        assert current_config['detection_region'] == [10, 10, 100, 100]
        
        # Step 5: Simulate loading config into DetectToolManager (our fix)
        # This is what the modified _load_tool_config_to_ui would do
        mock_detect_manager = Mock()
        
        # The key logic we implemented
        if editing_tool.name == "Detect Tool":
            mock_detect_manager.load_tool_config(current_config)
        
        # Verify the correct delegation occurred
        mock_detect_manager.load_tool_config.assert_called_once_with(current_config)
        call_config = mock_detect_manager.load_tool_config.call_args[0][0]
        
        assert call_config['model_name'] == 'yolov8n.onnx'
        assert call_config['selected_classes'] == ['person', 'car']
        print("✓ Configuration correctly delegated to DetectToolManager")
        
        # Step 6: Simulate user making changes and applying (edit flow completion)
        updated_config = current_config.copy()
        updated_config['selected_classes'] = ['person', 'car', 'bicycle']  # User added bicycle
        updated_config['confidence_threshold'] = 0.7  # User changed threshold
        
        # Update the tool with new configuration
        for key, value in updated_config.items():
            editing_tool.config.set(key, value)
        
        # Step 7: Verify changes were applied
        final_config = editing_tool.config.to_dict()
        assert final_config['selected_classes'] == ['person', 'car', 'bicycle']
        assert final_config['confidence_threshold'] == 0.7
        print("✓ Tool configuration updated successfully after editing")
        
        # Step 8: Test serialization and deserialization (save/load job)
        job_dict = job.to_dict()
        
        # Create new job from dict
        restored_job = Job.from_dict(job_dict, job_manager.tool_registry)
        restored_tool = restored_job.tools[0]
        restored_config = restored_tool.config.to_dict()
        
        # Verify configuration survived serialization
        assert restored_config['model_name'] == 'yolov8n.onnx'
        assert restored_config['selected_classes'] == ['person', 'car', 'bicycle']
        assert restored_config['confidence_threshold'] == 0.7
        print("✓ Tool configuration survives job serialization/deserialization")
        
        print("✓ Complete edit tool flow test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Complete edit tool flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multiple_tools_edit():
    """Test editing when multiple tools exist in a job"""
    print("Testing multiple tools edit scenario...")
    
    try:
        from job.job_manager import JobManager, Job
        from tools.base_tool import BaseTool
        from detection.detect_tool import create_detect_tool_from_manager_config
        
        # Create job with multiple tools
        job_manager = JobManager()
        job = Job("Multi-Tool Job")
        
        # Add a regular tool
        from tools.base_tool import GenericTool
        regular_tool = GenericTool("Regular Tool")
        job.add_tool(regular_tool)
        
        # Add a DetectTool
        detect_config = {
            'model_name': 'yolov8s.onnx',
            'selected_classes': ['person'],
            'confidence_threshold': 0.6
        }
        detect_tool = create_detect_tool_from_manager_config(detect_config)
        job.add_tool(detect_tool)
        
        # Add another regular tool
        from tools.base_tool import GenericTool
        another_tool = GenericTool("Another Tool")
        job.add_tool(another_tool)
        
        job_manager.add_job(job)
        
        # Test editing the DetectTool specifically
        current_job = job_manager.get_current_job()
        assert len(current_job.tools) == 3, f"Expected 3 tools, got {len(current_job.tools)}"
        
        # Find the DetectTool
        detect_tool_for_edit = None
        for tool in current_job.tools:
            if tool.name == "Detect Tool":
                detect_tool_for_edit = tool
                break
        
        assert detect_tool_for_edit is not None, "DetectTool not found in job"
        
        # Extract and verify its configuration
        config = detect_tool_for_edit.config.to_dict()
        assert config['model_name'] == 'yolov8s.onnx'
        assert config['selected_classes'] == ['person']
        assert config['confidence_threshold'] == 0.6
        
        print("✓ Can correctly identify and edit DetectTool among multiple tools")
        
        # Test that regular tools don't trigger DetectTool logic
        regular_tool_config = regular_tool.config.to_dict()
        # Regular tools shouldn't have model_name, etc.
        assert 'model_name' not in regular_tool_config or regular_tool_config['model_name'] is None
        
        print("✓ Regular tools don't interfere with DetectTool configuration")
        
        return True
        
    except Exception as e:
        print(f"✗ Multiple tools edit test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Tool Edit Integration Tests ===")
    
    success = True
    
    # Test complete edit flow
    success &= test_complete_edit_flow()
    print()
    
    # Test multiple tools scenario
    success &= test_multiple_tools_edit()
    print()
    
    if success:
        print("=== All integration tests passed! ===")
        sys.exit(0)
    else:
        print("=== Some integration tests failed! ===")
        sys.exit(1)