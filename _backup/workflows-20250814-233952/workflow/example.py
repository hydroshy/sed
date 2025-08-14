"""
Example script demonstrating the workflow management capabilities.

This script shows how to use both the base workflow system and the
enhanced workflow system side-by-side.
"""

import os
import logging
import time
import numpy as np
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('workflow_example.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("WorkflowExample")

# Add project root to path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflow.workflow_manager import WorkflowManager, Workflow
from workflow.workflow_enhancer import EnhancedWorkflowManager, EnhancedWorkflow
from tools.base_tool import BaseTool, ToolConfig, GenericTool

try:
    from tools.detect_tool import DetectTool
except ImportError:
    logger.warning("DetectTool could not be imported. Some examples may not work.")
    DetectTool = None


def create_sample_image():
    """Create a sample image for testing"""
    # Create a simple 640x480 grayscale image
    image = np.zeros((480, 640), dtype=np.uint8)
    
    # Draw some shapes
    cv2_available = False
    try:
        import cv2
        cv2_available = True
        
        # Draw a rectangle
        cv2.rectangle(image, (100, 100), (300, 300), 255, 2)
        
        # Draw a circle
        cv2.circle(image, (400, 240), 100, 255, 2)
        
        # Add some text
        cv2.putText(image, "Test Image", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2)
        
    except ImportError:
        # Simple fallback if OpenCV is not available
        # Draw a rectangle
        image[100:300, 100:300] = 255
        
        # Draw a circle (approximation)
        for i in range(360):
            angle = i * 3.14159 / 180
            x = int(400 + 100 * np.cos(angle))
            y = int(240 + 100 * np.sin(angle))
            if 0 <= x < 640 and 0 <= y < 480:
                image[y, x] = 255
    
    return image


def create_basic_workflow():
    """Create and demonstrate a basic workflow"""
    logger.info("Creating a basic workflow with the base WorkflowManager")
    
    # Initialize the workflow manager
    manager = WorkflowManager()
    
    # Create a new workflow
    workflow = Workflow(name="Basic Image Processing", description="A simple workflow for testing")
    
    # Create and add tools to the workflow
    tool1 = GenericTool(name="Grayscale Conversion", config=ToolConfig({
        "operation": "grayscale"
    }))
    
    tool2 = GenericTool(name="Blur Filter", config=ToolConfig({
        "operation": "blur",
        "kernel_size": 5
    }))
    
    tool3 = GenericTool(name="Edge Detection", config=ToolConfig({
        "operation": "edges",
        "threshold1": 50,
        "threshold2": 150
    }))
    
    # Add tools to workflow
    workflow.add_tool(tool1)
    workflow.add_tool(tool2, tool1.tool_id)  # Connect tool2 to tool1
    workflow.add_tool(tool3, tool2.tool_id)  # Connect tool3 to tool2
    
    # Add the workflow to the manager
    manager.add_workflow(workflow)
    
    # Get the current workflow
    current_workflow = manager.get_current_workflow()
    
    logger.info(f"Created workflow: {current_workflow.name}")
    logger.info(f"Number of tools: {len(current_workflow.tools)}")
    
    # Create a sample image
    image = create_sample_image()
    
    # Run the workflow
    logger.info("Running the workflow...")
    start_time = time.time()
    result_image, results = manager.run_current_workflow(image)
    execution_time = time.time() - start_time
    
    logger.info(f"Workflow execution completed in {execution_time:.2f} seconds")
    
    return manager, workflow, result_image


def create_enhanced_workflow():
    """Create and demonstrate an enhanced workflow"""
    logger.info("Creating an enhanced workflow with EnhancedWorkflowManager")
    
    # Initialize the base workflow manager (required by the enhanced manager)
    base_manager = WorkflowManager()
    
    # Initialize the enhanced workflow manager
    manager = EnhancedWorkflowManager(base_manager=base_manager, workflows_dir="example_workflows")
    
    # Create a new workflow
    workflow = manager.create_workflow(
        name="Enhanced Image Processing",
        description="An enhanced workflow with steps and dependencies",
        tags=["example", "image-processing"]
    )
    
    # Add steps to the workflow
    step1 = manager.add_step_to_workflow(
        workflow_id=workflow.id,
        tool_id=1,  # Tool IDs are assigned automatically
        name="Grayscale Conversion",
        description="Convert image to grayscale",
        config_overrides={"operation": "grayscale"}
    )
    
    step2 = manager.add_step_to_workflow(
        workflow_id=workflow.id,
        tool_id=2,
        name="Blur Filter",
        description="Apply Gaussian blur",
        config_overrides={"operation": "blur", "kernel_size": 5},
        dependencies=[step1.id]  # Depends on step1
    )
    
    step3 = manager.add_step_to_workflow(
        workflow_id=workflow.id,
        tool_id=3,
        name="Edge Detection",
        description="Detect edges with Canny algorithm",
        config_overrides={"operation": "edges", "threshold1": 50, "threshold2": 150},
        dependencies=[step2.id]  # Depends on step2
    )
    
    # Add a parallel step that depends on step1 but not step2
    step4 = manager.add_step_to_workflow(
        workflow_id=workflow.id,
        tool_id=4,
        name="Threshold",
        description="Apply binary threshold",
        config_overrides={"operation": "threshold", "threshold": 128},
        dependencies=[step1.id]  # Depends on step1 directly
    )
    
    # Add a final step that depends on both edge detection and threshold
    step5 = manager.add_step_to_workflow(
        workflow_id=workflow.id,
        tool_id=5,
        name="Combine Results",
        description="Combine edge detection and threshold results",
        config_overrides={"operation": "combine"},
        dependencies=[step3.id, step4.id]  # Depends on both step3 and step4
    )
    
    logger.info(f"Created enhanced workflow: {workflow.name}")
    logger.info(f"Number of steps: {len(workflow.steps)}")
    
    # Create a sample image
    image = create_sample_image()
    
    # Execute the workflow
    logger.info("Executing the enhanced workflow...")
    manager.execute_workflow(workflow.id, image=image, parallel=True)
    
    # Check workflow status (in a real application, you'd wait for completion)
    time.sleep(1)  # Give it a moment to complete
    
    workflow = manager.get_workflow(workflow.id)
    logger.info(f"Workflow status: {workflow.status}")
    logger.info(f"Execution time: {workflow.execution_time:.2f} seconds")
    
    return manager, workflow


def convert_between_workflow_types():
    """Demonstrate conversion between base and enhanced workflows"""
    logger.info("Demonstrating conversion between workflow types")
    
    # Create a base workflow
    base_manager = WorkflowManager()
    base_workflow = Workflow(name="Base Workflow", description="A simple base workflow")
    
    # Add some tools
    tool1 = GenericTool(name="Tool 1", config=ToolConfig({"param1": "value1"}))
    tool2 = GenericTool(name="Tool 2", config=ToolConfig({"param2": "value2"}))
    
    base_workflow.add_tool(tool1)
    base_workflow.add_tool(tool2, tool1.tool_id)
    
    base_manager.add_workflow(base_workflow)
    
    # Create an enhanced workflow manager
    enhanced_manager = EnhancedWorkflowManager(base_manager=base_manager, workflows_dir="example_workflows")
    
    # Convert the base workflow to an enhanced workflow
    enhanced_workflow = enhanced_manager.create_workflow_from_base(base_workflow, name="Converted Workflow")
    
    logger.info(f"Converted base workflow to enhanced workflow: {enhanced_workflow.name}")
    logger.info(f"Number of steps in enhanced workflow: {len(enhanced_workflow.steps)}")
    
    # You can also convert an enhanced workflow back to a base workflow
    # (This is done internally when executing the workflow)
    base_workflow2 = enhanced_workflow.to_base_workflow(base_manager.tool_registry)
    
    logger.info(f"Converted enhanced workflow back to base workflow")
    logger.info(f"Number of tools in converted base workflow: {len(base_workflow2.tools)}")
    
    return base_workflow, enhanced_workflow


def main():
    """Main function demonstrating workflow capabilities"""
    logger.info("Starting workflow examples")
    
    # Example 1: Basic workflow
    basic_manager, basic_workflow, basic_result = create_basic_workflow()
    
    # Example 2: Enhanced workflow
    enhanced_manager, enhanced_workflow = create_enhanced_workflow()
    
    # Example 3: Convert between workflow types
    base_workflow, converted_workflow = convert_between_workflow_types()
    
    logger.info("Workflow examples completed")


if __name__ == "__main__":
    main()
