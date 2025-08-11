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
                
                # Add dependencies for each input
                input_tools = tool.get_inputs()
                for input_tool in input_tools:
                    if input_tool.tool_id in tool_to_step_map:
                        input_step_id = tool_to_step_map[input_tool.tool_id]
                        workflow.add_dependency(step_id, input_step_id)
        
        self.save_workflow(workflow)
        logger.info(f"Created enhanced workflow from base workflow: {workflow.name}")
        return workflow
    
    def execute_workflow(self, 
                      workflow_id: str, 
                      image: Optional[np.ndarray] = None,
                      parallel: bool = False) -> bool:
        """
        Execute a workflow
        
        Args:
            workflow_id: ID of the workflow to execute
            image: Optional input image for the workflow
            parallel: Whether to execute steps in parallel where possible
            
        Returns:
            True if execution started successfully, False otherwise
        """
        # Check if another workflow is already running
        if not self.execution_lock.acquire(blocking=False):
            logger.warning("Another workflow is already running")
            return False
            
        try:
            workflow = self.workflows.get(workflow_id)
            if not workflow:
                logger.warning(f"Workflow not found: {workflow_id}")
                return False
                
            # Reset workflow status
            workflow.reset_status()
            workflow.status = "running"
            self.running_workflow = workflow
            self.stop_requested = False
            
            # Execute in a separate thread
            execution_thread = threading.Thread(
                target=self._execute_workflow_thread,
                args=(workflow, image, parallel),
                daemon=True
            )
            execution_thread.start()
            
            logger.info(f"Started execution of workflow: {workflow.name}")
            return True
        except Exception as e:
            logger.error(f"Error starting workflow execution: {e}")
            self.execution_lock.release()
            return False
    
    def _execute_workflow_thread(self, 
                              workflow: EnhancedWorkflow, 
                              image: Optional[np.ndarray] = None,
                              parallel: bool = False) -> None:
        """
        Thread function to execute a workflow
        
        Args:
            workflow: The workflow to execute
            image: Optional input image for the workflow
            parallel: Whether to execute steps in parallel where possible
        """
        start_time = time.time()
        
        try:
            # Convert to base workflow for compatibility if needed
            base_workflow = workflow.to_base_workflow(self.base_manager.tool_registry)
            
            # If not using parallel execution, use the base workflow's run method
            if not parallel and image is not None:
                result_image, results = base_workflow.run(image)
                # Update step statuses based on results
                for step in workflow.steps:
                    # Look for corresponding tool result
                    if step.tool_id in results:
                        step.status = WorkflowStepStatus.COMPLETED
                    else:
                        step.status = WorkflowStepStatus.SKIPPED
                workflow.status = "completed"
            else:
                # Execute using the step-based approach with topological sort
                self._execute_steps(workflow, image, parallel)
                
        except Exception as e:
            workflow.status = "failed"
            logger.error(f"Workflow execution failed: {workflow.name} - {e}")
        finally:
            # Calculate total execution time
            workflow.execution_time = time.time() - start_time
            self.running_workflow = None
            self.execution_lock.release()
            logger.info(f"Workflow execution finished: {workflow.name} - Status: {workflow.status}")
    
    def _execute_steps(self, 
                     workflow: EnhancedWorkflow, 
                     image: Optional[np.ndarray] = None,
                     parallel: bool = False) -> None:
        """
        Execute workflow steps in topological order
        
        Args:
            workflow: The workflow to execute
            image: Optional input image for the workflow
            parallel: Whether to execute steps in parallel where possible
        """
        # Get execution order
        execution_order = self._get_execution_order(workflow)
        
        # Create a copy of the image if provided
        input_image = image.copy() if image is not None else None
        
        # Track step results
        step_results: Dict[str, Tuple[Optional[np.ndarray], Dict[str, Any]]] = {}
        
        # For parallel execution
        if parallel:
            # Group steps by level (steps that can be executed in parallel)
            levels = self._group_steps_by_level(workflow)
            
            # Execute levels in sequence, steps within a level in parallel
            for level_steps in levels:
                if self.stop_requested:
                    workflow.status = "stopped"
                    return
                
                # Execute steps in this level in parallel
                threads = []
                for step in level_steps:
                    if not step.enabled:
                        step.status = WorkflowStepStatus.SKIPPED
                        continue
                        
                    thread = threading.Thread(
                        target=self._execute_step,
                        args=(workflow, step, input_image, step_results),
                        daemon=True
                    )
                    threads.append(thread)
                    thread.start()
                
                # Wait for all threads in this level to complete
                for thread in threads:
                    thread.join()
                    
                # Check if any step failed
                failed_steps = [s for s in level_steps if s.status == WorkflowStepStatus.FAILED]
                if failed_steps:
                    workflow.status = "failed"
                    return
        else:
            # Sequential execution
            for step in execution_order:
                if self.stop_requested:
                    workflow.status = "stopped"
                    return
                    
                if not step.enabled:
                    step.status = WorkflowStepStatus.SKIPPED
                    continue
                    
                self._execute_step(workflow, step, input_image, step_results)
                
                # Check if step failed
                if step.status == WorkflowStepStatus.FAILED:
                    workflow.status = "failed"
                    return
        
        # Update final status
        if workflow.status != "stopped":
            workflow.status = "completed"
    
    def _execute_step(self, 
                    workflow: EnhancedWorkflow, 
                    step: WorkflowStep,
                    input_image: Optional[np.ndarray],
                    step_results: Dict[str, Tuple[Optional[np.ndarray], Dict[str, Any]]]) -> None:
        """
        Execute a single workflow step
        
        Args:
            workflow: The workflow being executed
            step: The step to execute
            input_image: The input image (if available)
            step_results: Dictionary to store step results
        """
        try:
            # Update step status
            step.status = WorkflowStepStatus.RUNNING
            workflow.current_step = step.id
            step_start_time = time.time()
            
            # Find the tool for this step
            tool = None
            for tool_type, tool_class in self.base_manager.tool_registry.items():
                try:
                    # Create a tool with the step's configuration
                    tool = tool_class(name=step.name, config=ToolConfig(step.config_overrides))
                    tool.tool_id = step.tool_id
                    break
                except Exception:
                    continue
            
            if not tool:
                raise ValueError(f"Could not find a compatible tool for step {step.name}")
            
            # Prepare context from dependencies
            context: Dict[str, Any] = {}
            current_image = input_image
            
            # Get input from dependencies
            for dep_id in step.dependencies:
                if dep_id in step_results:
                    dep_image, dep_result = step_results[dep_id]
                    if dep_image is not None:
                        current_image = dep_image
                    context.update(dep_result)
            
            # Execute the tool
            if current_image is not None:
                result_image, result_data = tool.process(current_image, context)
                step_results[step.id] = (result_image, result_data)
            else:
                result_data = {}
                step_results[step.id] = (None, result_data)
            
            # Update step status
            step.status = WorkflowStepStatus.COMPLETED
            step.execution_time = time.time() - step_start_time
            
        except Exception as e:
            # Handle step failure
            step.status = WorkflowStepStatus.FAILED
            step.error_message = str(e)
            step.execution_time = time.time() - step_start_time
            logger.error(f"Step execution failed: {step.name} - {e}")
            
            # Increment retry count and retry if possible
            step.retry_count += 1
            if step.retry_count <= step.max_retries:
                logger.info(f"Retrying step {step.name} (attempt {step.retry_count}/{step.max_retries})")
                # Recursive retry
                self._execute_step(workflow, step, input_image, step_results)
    
    def _get_execution_order(self, workflow: EnhancedWorkflow) -> List[WorkflowStep]:
        """
        Get the execution order for workflow steps using topological sort
        
        Args:
            workflow: The workflow to sort
            
        Returns:
            List of steps in execution order
        """
        # Create a copy of all steps
        steps = workflow.steps.copy()
        
        # Create dependency graph
        graph = {step.id: set(step.dependencies) for step in steps}
        
        # Track visited and temporary marks for cycle detection
        visited = set()
        temp_marks = set()
        
        # Result list
        result = []
        
        def visit(node_id):
            """Visit a node in the graph for topological sort"""
            if node_id in visited:
                return
            if node_id in temp_marks:
                # This indicates a cycle, which is invalid for a workflow
                logger.warning(f"Cyclic dependency detected in workflow: {workflow.name}")
                return
                
            temp_marks.add(node_id)
            
            # Visit dependencies
            for dep_id in graph.get(node_id, set()):
                visit(dep_id)
                
            temp_marks.remove(node_id)
            visited.add(node_id)
            
            # Add to result (in reverse order)
            step = workflow.get_step(node_id)
            if step:
                result.insert(0, step)
        
        # Visit all nodes
        for step in steps:
            if step.id not in visited:
                visit(step.id)
                
        return result
    
    def _group_steps_by_level(self, workflow: EnhancedWorkflow) -> List[List[WorkflowStep]]:
        """
        Group steps by level for parallel execution
        
        Args:
            workflow: The workflow to analyze
            
        Returns:
            List of lists of steps, where each list contains steps that can be executed in parallel
        """
        # Create a copy of all steps
        steps = workflow.steps.copy()
        
        # Create dependency graph
        graph = {step.id: set(step.dependencies) for step in steps}
        
        # Track steps in each level
        levels: List[List[WorkflowStep]] = []
        
        # Steps without dependencies go in the first level
        remaining_steps = {s.id: s for s in steps}
        
        while remaining_steps:
            # Find steps that have all dependencies satisfied
            current_level = []
            completed_step_ids = set()
            
            for step_id, step in remaining_steps.items():
                # Check if all dependencies are in previous levels
                deps = graph.get(step_id, set())
                if all(dep not in remaining_steps for dep in deps):
                    current_level.append(step)
                    completed_step_ids.add(step_id)
            
            # If no steps can be executed, there's a cycle
            if not current_level:
                logger.warning(f"Cyclic dependency detected in workflow: {workflow.name}")
                break
                
            # Add this level and remove steps from remaining
            levels.append(current_level)
            for step_id in completed_step_ids:
                remaining_steps.pop(step_id)
                
        return levels
    
    def stop_workflow_execution(self) -> bool:
        """
        Stop the currently running workflow
        
        Returns:
            True if stop was requested, False if no workflow is running
        """
        if self.running_workflow:
            self.stop_requested = True
            logger.info(f"Requested stop for workflow: {self.running_workflow.name}")
            return True
        return False
    
    def get_workflow(self, workflow_id: str) -> Optional[EnhancedWorkflow]:
        """Get a workflow by ID"""
        return self.workflows.get(workflow_id)
        
    def get_all_workflows(self) -> List[EnhancedWorkflow]:
        """Get all workflows"""
        return list(self.workflows.values())
        
    def set_active_workflow(self, workflow_id: str) -> bool:
        """Set the active workflow"""
        if workflow_id in self.workflows:
            self.active_workflow = self.workflows[workflow_id]
            return True
        return False
        
    def get_active_workflow(self) -> Optional[EnhancedWorkflow]:
        """Get the currently active workflow"""
        return self.active_workflow
        
    def find_workflows_by_tag(self, tag: str) -> List[EnhancedWorkflow]:
        """Find workflows with a specific tag"""
        return [w for w in self.workflows.values() if tag in w.tags]
        
    def search_workflows(self, query: str) -> List[EnhancedWorkflow]:
        """Search workflows by name or description"""
        query = query.lower()
        return [w for w in self.workflows.values() 
                if query in w.name.lower() or query in w.description.lower()]
