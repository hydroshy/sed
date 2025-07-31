#!/usr/bin/env python3
"""
Test script for tool configuration fixes
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

def test_position_field_loading():
    """Test that position fields are loaded correctly during tool edit"""
    print("Testing position field loading...")
    
    try:
        from job.job_manager import JobManager, Job, Tool, ToolConfig
        
        # Create a job with a tool that has position configuration
        job_manager = JobManager()
        job = Job("Test Job")
        
        # Create tool with position config
        tool_config = ToolConfig({
            'xPosition': 150,
            'yPosition': 200,
            'detection_area': [100, 150, 200, 250],
            'threshold': 0.7
        })
        
        tool = Tool("Test Tool", tool_config)
        job.add_tool(tool)
        job_manager.add_job(job)
        
        # Test loading configuration
        config = tool.config.to_dict()
        print(f"Tool config: {config}")
        
        # Verify position values exist
        assert config.get('xPosition') == 150, f"Expected xPosition=150, got {config.get('xPosition')}"
        assert config.get('yPosition') == 200, f"Expected yPosition=200, got {config.get('yPosition')}"
        
        # Verify detection area exists
        assert config.get('detection_area') == [100, 150, 200, 250], f"Detection area mismatch"
        
        print("✓ Position field loading test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Position field loading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_detect_tool_classification_config():
    """Test DetectTool classification configuration with thresholds"""
    print("Testing DetectTool classification configuration...")
    
    try:
        from detection.detect_tool import create_detect_tool_from_manager_config
        
        # Create DetectTool with classification configuration
        config = {
            'model_name': 'yolov8n.onnx',
            'model_path': '/path/to/yolov8n.onnx',
            'selected_classes': ['person', 'car', 'bicycle'],
            'class_thresholds': {
                'person': 0.7,
                'car': 0.6,
                'bicycle': 0.8
            },
            'confidence_threshold': 0.5
        }
        
        # Create tool
        detect_tool = create_detect_tool_from_manager_config(config)
        
        # Verify configuration
        tool_config = detect_tool.config.to_dict()
        print(f"DetectTool config: {tool_config}")
        
        # Check that configuration is preserved
        assert tool_config['model_name'] == 'yolov8n.onnx'
        assert tool_config['selected_classes'] == ['person', 'car', 'bicycle']
        assert tool_config['class_thresholds']['person'] == 0.7
        assert tool_config['class_thresholds']['car'] == 0.6
        assert tool_config['class_thresholds']['bicycle'] == 0.8
        
        print("✓ DetectTool classification configuration test passed!")
        return True
        
    except Exception as e:
        print(f"✗ DetectTool classification configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tool_config_serialization():
    """Test that tool configuration survives serialization/deserialization"""
    print("Testing tool configuration serialization...")
    
    try:
        from job.job_manager import JobManager, Job
        from detection.detect_tool import create_detect_tool_from_manager_config
        
        # Create job manager and job
        job_manager = JobManager()
        job = Job("Serialization Test Job")
        
        # Create DetectTool with comprehensive configuration
        config = {
            'model_name': 'yolov8s.onnx',
            'model_path': '/path/to/yolov8s.onnx',
            'selected_classes': ['person', 'car'],
            'class_thresholds': {
                'person': 0.75,
                'car': 0.65
            },
            'confidence_threshold': 0.6,
            'detection_area': [50, 50, 150, 150]
        }
        
        detect_tool = create_detect_tool_from_manager_config(config)
        job.add_tool(detect_tool)
        job_manager.add_job(job)
        
        # Serialize job
        job_dict = job.to_dict()
        print(f"Serialized job: {job_dict['tools'][0]['config']}")
        
        # Deserialize job
        restored_job = Job.from_dict(job_dict, job_manager.tool_registry)
        restored_tool = restored_job.tools[0]
        restored_config = restored_tool.config.to_dict()
        
        print(f"Restored config: {restored_config}")
        
        # Verify all configuration survived
        assert restored_config['model_name'] == 'yolov8s.onnx'
        assert restored_config['selected_classes'] == ['person', 'car']
        assert restored_config['class_thresholds']['person'] == 0.75
        assert restored_config['class_thresholds']['car'] == 0.65
        assert restored_config['detection_area'] == [50, 50, 150, 150]
        
        print("✓ Tool configuration serialization test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Tool configuration serialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_overlay_preservation_simulation():
    """Test overlay preservation logic (simulation)"""
    print("Testing overlay preservation logic...")
    
    try:
        # Simulate camera view with multiple overlays
        mock_camera_view = Mock()
        mock_camera_view.overlays = {}
        
        # Simulate adding overlays for different tools
        tool_1_overlay = Mock()
        tool_1_overlay.tool_id = 1
        tool_1_overlay.update_from_coords = Mock()
        tool_1_overlay.set_edit_mode = Mock()
        
        tool_2_overlay = Mock()
        tool_2_overlay.tool_id = 2
        tool_2_overlay.update_from_coords = Mock()
        tool_2_overlay.set_edit_mode = Mock()
        
        mock_camera_view.overlays[1] = tool_1_overlay
        mock_camera_view.overlays[2] = tool_2_overlay
        
        # Simulate editing tool 1 (should preserve tool 2's overlay)
        editing_tool_id = 1
        if editing_tool_id in mock_camera_view.overlays:
            # Update existing overlay
            overlay = mock_camera_view.overlays[editing_tool_id]
            overlay.update_from_coords(10, 10, 100, 100)
            overlay.set_edit_mode(True)
            mock_camera_view.current_overlay = overlay
        
        # Verify tool 1's overlay was updated
        tool_1_overlay.update_from_coords.assert_called_once_with(10, 10, 100, 100)
        tool_1_overlay.set_edit_mode.assert_called_once_with(True)
        
        # Verify tool 2's overlay was not touched
        tool_2_overlay.update_from_coords.assert_not_called()
        
        # Verify both overlays still exist
        assert len(mock_camera_view.overlays) == 2
        assert 1 in mock_camera_view.overlays
        assert 2 in mock_camera_view.overlays
        
        print("✓ Overlay preservation simulation test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Overlay preservation simulation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Tool Configuration Fixes Tests ===")
    
    success = True
    
    # Test position field loading
    success &= test_position_field_loading()
    print()
    
    # Test DetectTool classification configuration
    success &= test_detect_tool_classification_config()
    print()
    
    # Test tool configuration serialization
    success &= test_tool_config_serialization()
    print()
    
    # Test overlay preservation simulation
    success &= test_overlay_preservation_simulation()
    print()
    
    if success:
        print("=== All tool configuration fixes tests passed! ===")
        sys.exit(0)
    else:
        print("=== Some tests failed! ===")
        sys.exit(1)