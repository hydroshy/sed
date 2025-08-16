"""
Workflow enhancement module for SED (Smart Eye Detection).

This module extends the existing workflow system with more advanced features:
- Enhanced workflow persistence (JSON serialization)
- Step-based workflow representation
- Improved error handling and recovery
- Parallel execution options
"""

import json
import os
import logging
import time
import uuid
import threading
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

import numpy as np

from workflow.workflow_manager import Workflow as BaseWorkflow
from workflow.workflow_manager import WorkflowManager as BaseWorkflowManager
from tools.base_tool import BaseTool, ToolConfig

# Configure logging
logger = logging.getLogger("WorkflowEnhancer")


class WorkflowStepStatus(Enum):
    """Status enum for workflow steps"""
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow"""
    id: str
    name: str
    tool_id: int
    description: str = ""
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})
    dependencies: List[str] = field(default_factory=list)
    enabled: bool = True
    status: WorkflowStepStatus = WorkflowStepStatus.WAITING
    config_overrides: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    execution_time: float = 0.0
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary for serialization"""
        data = asdict(self)
        data["status"] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStep':
        """Create step from dictionary"""
        # Convert status string to enum
        status_str = data.pop("status", "waiting")
        try:
            status = WorkflowStepStatus(status_str)
        except ValueError:
            status = WorkflowStepStatus.WAITING
            
        return cls(**data, status=status)


@dataclass
class EnhancedWorkflow:
    """An enhanced workflow implementation with step-based processing"""
    id: str
    name: str
    description: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    status: str = "ready"  # ready, running, completed, failed
    current_step: Optional[str] = None
    execution_time: float = 0.0
    version: str = "1.0"
    
    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to the workflow"""
        self.steps.append(step)
        self.modified_at = time.time()
    
    def remove_step(self, step_id: str) -> bool:
        """Remove a step from the workflow"""
        for i, step in enumerate(self.steps):
            if step.id == step_id:
                self.steps.pop(i)
                # Update dependencies in other steps
                for other_step in self.steps:
                    if step_id in other_step.dependencies:
                        other_step.dependencies.remove(step_id)
                self.modified_at = time.time()
                return True
        return False
    
    def update_step(self, step_id: str, **kwargs) -> bool:
        """Update a step's properties"""
        for step in self.steps:
            if step.id == step_id:
                for key, value in kwargs.items():
                    if hasattr(step, key):
                        setattr(step, key, value)
                self.modified_at = time.time()
                return True
        return False
    
    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a step by ID"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None
    
    def add_dependency(self, step_id: str, depends_on_id: str) -> bool:
        """Add a dependency between steps"""
        step = self.get_step(step_id)
        depends_on = self.get_step(depends_on_id)
        
        if not step or not depends_on:
            return False
            
        if depends_on_id not in step.dependencies:
            step.dependencies.append(depends_on_id)
            self.modified_at = time.time()
            return True
        return False
    
    def remove_dependency(self, step_id: str, depends_on_id: str) -> bool:
        """Remove a dependency between steps"""
        step = self.get_step(step_id)
        
        if not step:
            return False
            
        if depends_on_id in step.dependencies:
            step.dependencies.remove(depends_on_id)
            self.modified_at = time.time()
            return True
        return False
    
    def get_entry_steps(self) -> List[WorkflowStep]:
        """Get steps that don't have dependencies (entry points)"""
        return [step for step in self.steps if not step.dependencies]
    
    def get_exit_steps(self) -> List[WorkflowStep]:
        """Get steps that aren't dependencies for any other steps (exit points)"""
        dependent_step_ids = set()
        for step in self.steps:
            dependent_step_ids.update(step.dependencies)
        
        return [step for step in self.steps if step.id not in dependent_step_ids]
    
    def reset_status(self) -> None:
        """Reset the status of all steps to WAITING"""
        for step in self.steps:
            step.status = WorkflowStepStatus.WAITING
            step.error_message = ""
            step.execution_time = 0.0
        
        self.status = "ready"
        self.current_step = None
        self.execution_time = 0.0
        self.modified_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow to dictionary for serialization"""
        data = asdict(self)
        data["steps"] = [step.to_dict() for step in self.steps]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnhancedWorkflow':
        """Create workflow from dictionary"""
        steps_data = data.pop("steps", [])
        workflow = cls(**data)
        workflow.steps = [WorkflowStep.from_dict(step) for step in steps_data]
        return workflow
    
    def to_json(self) -> str:
        """Convert workflow to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'EnhancedWorkflow':
        """Create workflow from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def to_base_workflow(self, tool_registry) -> BaseWorkflow:
        """Convert to base Workflow for compatibility"""
        # Create a new base workflow
        base_workflow = BaseWorkflow(name=self.name, description=self.description)
        
        # Map step IDs to tools
        step_to_tool_map = {}
        
        # First pass: Create and add all tools
        for step in self.steps:
            if not step.enabled:
                continue
                
            # Find the tool in the registry or create a generic one
            tool = None
            for tool_class_name, tool_class in tool_registry.items():
                try:
                    # Create a tool instance with config overrides
                    tool = tool_class(name=step.name, config=step.config_overrides)
                    break
                except Exception as e:
                    logger.warning(f"Error creating tool {tool_class_name}: {e}")
            
            # Add the tool to the workflow if created
            if tool:
                base_workflow.add_tool(tool)
                step_to_tool_map[step.id] = tool
        
        # Second pass: Connect tools based on dependencies
        for step in self.steps:
            if step.id in step_to_tool_map:
                target_tool = step_to_tool_map[step.id]
                
                # Connect with dependencies
                for dep_id in step.dependencies:
                    if dep_id in step_to_tool_map:
                        source_tool = step_to_tool_map[dep_id]
                        # Connect the tools
                        source_tool.add_output(target_tool)
                        target_tool.add_input(source_tool)
        
        return base_workflow


class EnhancedWorkflowManager:
    """
    Enhanced workflow manager with persistence and improved execution capabilities
    """
    
    def __init__(self, base_manager: BaseWorkflowManager = None, workflows_dir: str = "workflows"):
        """
        Initialize the enhanced workflow manager
        
        Args:
            base_manager: The base workflow manager to extend
            workflows_dir: Directory to store workflow files
        """
        self.base_manager = base_manager or BaseWorkflowManager()
        self.workflows_dir = workflows_dir
        os.makedirs(workflows_dir, exist_ok=True)
        
        self.workflows: Dict[str, EnhancedWorkflow] = {}
        self.active_workflow: Optional[EnhancedWorkflow] = None
        self.running_workflow: Optional[EnhancedWorkflow] = None
        self.execution_lock = threading.Lock()
        self.stop_requested = False
        self._load_workflows()

    def _load_workflows(self) -> None:
        """Load all workflows from the workflows directory"""
        try:
            workflow_files = [f for f in os.listdir(self.workflows_dir) 
                             if f.endswith('.workflow.json')]
            
            for filename in workflow_files:
                filepath = os.path.join(self.workflows_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        workflow_json = f.read()
                        workflow = EnhancedWorkflow.from_json(workflow_json)
                        self.workflows[workflow.id] = workflow
                        logger.info(f"Loaded workflow: {workflow.name} ({workflow.id})")
                except Exception as e:
                    logger.error(f"Error loading workflow from {filepath}: {e}")
        except Exception as e:
            logger.error(f"Error scanning workflows directory: {e}")

    def save_workflow(self, workflow: EnhancedWorkflow) -> bool:
        """
        Save a workflow to disk
        
        Args:
            workflow: The workflow to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            filepath = os.path.join(self.workflows_dir, f"{workflow.id}.workflow.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(workflow.to_json())
            
            # Update workflows dictionary
            self.workflows[workflow.id] = workflow
            logger.info(f"Saved workflow: {workflow.name} ({workflow.id})")
            return True
        except Exception as e:
            logger.error(f"Error saving workflow {workflow.name}: {e}")
            return False

    def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete a workflow from disk and memory
        
        Args:
            workflow_id: ID of the workflow to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if workflow_id not in self.workflows:
            return False
            
        try:
            filepath = os.path.join(self.workflows_dir, f"{workflow_id}.workflow.json")
            if os.path.exists(filepath):
                os.remove(filepath)
            
            # Remove from workflows dictionary
            del self.workflows[workflow_id]
            
            # Reset active workflow if it was deleted
            if self.active_workflow and self.active_workflow.id == workflow_id:
                self.active_workflow = None
                
            logger.info(f"Deleted workflow: {workflow_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting workflow {workflow_id}: {e}")
            return False

    def create_workflow(self, name: str, description: str = "", tags: Optional[List[str]] = None) -> EnhancedWorkflow:
        """
        Create a new workflow
        
        Args:
            name: Name of the workflow
            description: Description of the workflow
            tags: Tags for categorizing the workflow
            
        Returns:
            The newly created workflow
        """
        workflow_id = str(uuid.uuid4())
        workflow = EnhancedWorkflow(
            id=workflow_id,
            name=name,
            description=description,
            tags=tags or []
        )
        
        self.workflows[workflow_id] = workflow
        self.active_workflow = workflow
        
        # Save the new workflow
        self.save_workflow(workflow)
        
        logger.info(f"Created new workflow: {name} ({workflow_id})")
        return workflow

    def add_step_to_workflow(self, 
                           workflow_id: str, 
                           tool_id: int,
                           name: Optional[str] = None,
                           description: str = "", 
                           position: Optional[Dict[str, float]] = None,
                           config_overrides: Optional[Dict[str, Any]] = None,
                           dependencies: Optional[List[str]] = None) -> Optional[WorkflowStep]:
        """
        Add a step to a workflow
        
        Args:
            workflow_id: ID of the workflow
            tool_id: ID of the tool to use for this step
            name: Name of the step (defaults to tool name)
            description: Description of the step
            position: Visual position of the step in the workflow diagram
            config_overrides: Tool configuration overrides for this step
            dependencies: IDs of steps this step depends on
            
        Returns:
            The newly created step, or None if workflow not found
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            logger.warning(f"Workflow not found: {workflow_id}")
            return None
            
        step_id = str(uuid.uuid4())
        step = WorkflowStep(
            id=step_id,
            name=name or f"Step {len(workflow.steps) + 1}",
            tool_id=tool_id,
            description=description,
            position=position or {"x": 0, "y": 0},
            dependencies=dependencies or [],
            config_overrides=config_overrides or {},
        )
        
        workflow.add_step(step)
        self.save_workflow(workflow)
        
        logger.info(f"Added step {step.name} to workflow {workflow.name}")
        return step

    def create_workflow_from_base(self, base_workflow: BaseWorkflow, name: Optional[str] = None) -> EnhancedWorkflow:
        """
        Create an enhanced workflow from a base workflow
        
        Args:
            base_workflow: The base workflow to convert
            name: Optional name for the enhanced workflow (defaults to base workflow name)
            
        Returns:
            The newly created enhanced workflow
        """
        workflow_name = name or f"Enhanced {base_workflow.name}"
        workflow = self.create_workflow(
            name=workflow_name,
            description=base_workflow.description
        )
        
        # Add steps for each tool in the base workflow
        tool_to_step_map = {}
        
        # First pass: create steps for all tools
        for tool in base_workflow.tools:
            step = self.add_step_to_workflow(
                workflow_id=workflow.id,
                tool_id=tool.tool_id,
                name=tool.display_name if hasattr(tool, 'display_name') else f"Step {tool.tool_id}",
                config_overrides=tool.config.to_dict() if hasattr(tool, 'config') else {}
            )
            if step:
                tool_to_step_map[tool.tool_id] = step.id
        
        # Second pass: add dependencies based on tool connections
        for tool in base_workflow.tools:
            if tool.tool_id in tool_to_step_map:
                step_id = tool_to_step_map[tool.tool_id]
                
        
*** End File
