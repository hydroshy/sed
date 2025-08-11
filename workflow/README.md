# Workflow Management Module for SED

This module provides a comprehensive workflow management system for the SED (Smart Eye Detection) application. It enables users to create, edit, save, load, and execute image processing workflows consisting of interconnected tools.

## Overview

The workflow management system consists of two main components:

1. **Base Workflow System** (`workflow_manager.py`): Provides fundamental workflow functionality with tools connected in a directed graph.

2. **Enhanced Workflow System** (`workflow_enhancer.py`): Extends the base system with improved features like:
   - Persistent workflow storage (JSON serialization)
   - Step-based workflow representation
   - Improved error handling and recovery
   - Parallel execution capabilities
   - Better visualization support

## Key Components

### Workflow

A workflow represents a sequence of image processing steps. It contains:
- A set of tools/steps with specific configurations
- Connection information between tools/steps
- Execution state and results

### WorkflowManager

The workflow manager handles:
- Creating and storing workflows
- Registering available tools
- Executing workflows on images
- Managing workflow state

### EnhancedWorkflow

The enhanced workflow adds:
- Explicit step representation with dependencies
- Richer metadata (tags, descriptions, etc.)
- Execution tracking for individual steps
- Retry capabilities for failed steps

### EnhancedWorkflowManager

The enhanced manager adds:
- Persistence to disk as JSON files
- Topological sorting for execution order
- Parallel execution capabilities
- Error handling and recovery
- Search and filtering capabilities

## Usage Examples

### Basic Workflow

```python
# Initialize the workflow manager
manager = WorkflowManager()

# Create a new workflow
workflow = Workflow(name="Image Processing", description="A simple workflow")

# Create and add tools to the workflow
tool1 = GenericTool(name="Grayscale Conversion", config=ToolConfig({
    "operation": "grayscale"
}))

tool2 = GenericTool(name="Blur Filter", config=ToolConfig({
    "operation": "blur",
    "kernel_size": 5
}))

# Add tools to workflow
workflow.add_tool(tool1)
workflow.add_tool(tool2, tool1.tool_id)  # Connect tool2 to tool1

# Add the workflow to the manager
manager.add_workflow(workflow)

# Run the workflow on an image
result_image, results = manager.run_current_workflow(image)
```

### Enhanced Workflow

```python
# Initialize managers
base_manager = WorkflowManager()
manager = EnhancedWorkflowManager(base_manager=base_manager, workflows_dir="workflows")

# Create a new workflow
workflow = manager.create_workflow(
    name="Enhanced Image Processing",
    description="An enhanced workflow with steps and dependencies",
    tags=["example", "image-processing"]
)

# Add steps to the workflow
step1 = manager.add_step_to_workflow(
    workflow_id=workflow.id,
    tool_id=1,
    name="Grayscale Conversion",
    config_overrides={"operation": "grayscale"}
)

step2 = manager.add_step_to_workflow(
    workflow_id=workflow.id,
    tool_id=2,
    name="Blur Filter",
    config_overrides={"operation": "blur", "kernel_size": 5},
    dependencies=[step1.id]  # Depends on step1
)

# Execute the workflow
manager.execute_workflow(workflow.id, image=image, parallel=True)
```

## Workflow Persistence

Enhanced workflows are automatically saved to disk as JSON files in the specified `workflows_dir`:

```python
# Load all workflows from disk
manager = EnhancedWorkflowManager(workflows_dir="workflows")

# Save a specific workflow
manager.save_workflow(workflow)

# Delete a workflow
manager.delete_workflow(workflow_id)
```

## Error Handling and Recovery

The enhanced workflow system includes robust error handling:

- Steps track their execution status
- Failed steps can be automatically retried
- Error messages are captured for debugging
- Workflows can be stopped and resumed

## Workflow Visualization

Workflows store position information for each step, enabling visual representation in a UI:

```python
# Position information for UI display
step = manager.add_step_to_workflow(
    workflow_id=workflow.id,
    tool_id=1,
    name="Tool",
    position={"x": 100, "y": 200}  # UI coordinates
)
```

## Integration

The workflow module integrates with the rest of the SED application:

- Works with existing tool implementations
- Compatible with the camera module for live processing
- Can be used in both GUI and command-line contexts
