"""
Job Tool Manager - Unified interface for adding tools to job workflow
Allows adding tools separately to build flexible detection pipelines
"""

import logging
from typing import Dict, List, Optional, Any
from PyQt5.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)


class JobToolManager:
    """Manager for adding tools to job workflow"""
    
    def __init__(self, main_window):
        """
        Initialize JobToolManager
        
        Args:
            main_window: Reference to MainWindow instance
        """
        self.main_window = main_window
        self.available_tools = {
            'DetectTool': {
                'name': 'DetectTool',
                'description': 'YOLO Object Detection',
                'manager_attr': 'detect_tool_manager',
                'apply_method': 'apply_detect_tool_to_job',
                'icon': '🔍'
            },
            'ResultTool': {
                'name': 'ResultTool',
                'description': 'NG/OK Evaluation',
                'manager_attr': 'result_tool_manager',
                'apply_method': 'apply_result_tool_to_job',
                'icon': '✓'
            }
        }
        
        logger.info("JobToolManager initialized")
    
    def get_available_tools(self) -> Dict[str, Dict[str, str]]:
        """Get list of available tools"""
        return self.available_tools
    
    def add_tool(self, tool_type: str) -> bool:
        """
        Add a specific tool to the current job
        
        Args:
            tool_type: Type of tool to add ('DetectTool', 'ResultTool', etc.)
            
        Returns:
            bool: True if tool was added successfully
        """
        if tool_type not in self.available_tools:
            logger.error(f"Unknown tool type: {tool_type}")
            return False
        
        tool_info = self.available_tools[tool_type]
        logger.info(f"Adding tool: {tool_info['name']}")
        
        try:
            # Get manager
            manager_attr = tool_info['manager_attr']
            if not hasattr(self.main_window, manager_attr):
                logger.error(f"Manager not found: {manager_attr}")
                return False
            
            manager = getattr(self.main_window, manager_attr)
            
            # Apply tool
            apply_method = tool_info['apply_method']
            if not hasattr(manager, apply_method):
                logger.error(f"Method not found: {apply_method}")
                return False
            
            apply_func = getattr(manager, apply_method)
            result = apply_func()
            
            if result:
                logger.info(f"✓ Successfully added {tool_info['name']}")
                self._show_success_message(tool_info['name'])
            else:
                logger.error(f"Failed to add {tool_info['name']}")
                self._show_error_message(f"Failed to add {tool_info['name']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error adding tool {tool_type}: {e}")
            self._show_error_message(f"Error adding tool: {str(e)}")
            return False
    
    def get_current_workflow(self) -> List[str]:
        """Get list of tools in current job workflow"""
        if hasattr(self.main_window, 'job_manager'):
            job_manager = self.main_window.job_manager
            current_job = job_manager.get_current_job()
            
            if current_job:
                return [tool.name for tool in current_job.tools]
        
        return []
    
    def print_workflow(self):
        """Print current workflow to console"""
        workflow = self.get_current_workflow()
        logger.info(f"Current workflow ({len(workflow)} tools):")
        for i, tool_name in enumerate(workflow, 1):
            logger.info(f"  [{i}] {tool_name}")
    
    def _show_success_message(self, tool_name: str):
        """Show success message to user"""
        workflow = self.get_current_workflow()
        message = f"✓ Added {tool_name}\n\nCurrent workflow:\n"
        for i, tool in enumerate(workflow, 1):
            message += f"  [{i}] {tool}\n"
        
        logger.info(f"Success: {message}")
    
    def _show_error_message(self, message: str):
        """Show error message to user"""
        logger.error(f"Error: {message}")


class DetectToolPanel:
    """Panel for managing DetectTool configuration"""
    
    def __init__(self, main_window):
        """Initialize DetectToolPanel"""
        self.main_window = main_window
        self.job_tool_manager = JobToolManager(main_window)
        
        logger.info("DetectToolPanel initialized")
    
    def show_panel(self):
        """Show DetectTool configuration panel"""
        logger.info("Showing DetectTool panel")
    
    def apply_tool(self) -> bool:
        """Apply DetectTool to workflow"""
        return self.job_tool_manager.add_tool('DetectTool')


class ResultToolPanel:
    """Panel for managing ResultTool configuration"""
    
    def __init__(self, main_window):
        """Initialize ResultToolPanel"""
        self.main_window = main_window
        self.job_tool_manager = JobToolManager(main_window)
        
        logger.info("ResultToolPanel initialized")
    
    def show_panel(self):
        """Show ResultTool configuration panel"""
        logger.info("Showing ResultTool panel")
    
    def apply_tool(self) -> bool:
        """Apply ResultTool to workflow"""
        return self.job_tool_manager.add_tool('ResultTool')


class WorkflowBuilder:
    """Builder for constructing job workflows"""
    
    def __init__(self, main_window):
        """Initialize WorkflowBuilder"""
        self.main_window = main_window
        self.job_tool_manager = JobToolManager(main_window)
        
        logger.info("WorkflowBuilder initialized")
    
    def build_detection_workflow(self) -> bool:
        """Build detection + evaluation workflow: DetectTool → ResultTool"""
        logger.info("Building detection workflow...")
        
        # Step 1: Add DetectTool
        logger.info("Step 1: Adding DetectTool...")
        if not self.job_tool_manager.add_tool('DetectTool'):
            logger.error("Failed to add DetectTool")
            return False
        
        # Step 2: Add ResultTool
        logger.info("Step 2: Adding ResultTool...")
        if not self.job_tool_manager.add_tool('ResultTool'):
            logger.error("Failed to add ResultTool")
            return False
        
        logger.info("✓ Detection workflow built successfully")
        self.job_tool_manager.print_workflow()
        return True
    
    def build_detect_only_workflow(self) -> bool:
        """Build detection only workflow: DetectTool"""
        logger.info("Building detection-only workflow...")
        
        if not self.job_tool_manager.add_tool('DetectTool'):
            logger.error("Failed to add DetectTool")
            return False
        
        logger.info("✓ Detection-only workflow built successfully")
        self.job_tool_manager.print_workflow()
        return True
    
    def build_eval_only_workflow(self) -> bool:
        """Build evaluation only workflow: ResultTool"""
        logger.info("Building evaluation-only workflow...")
        
        if not self.job_tool_manager.add_tool('ResultTool'):
            logger.error("Failed to add ResultTool")
            return False
        
        logger.info("✓ Evaluation-only workflow built successfully")
        self.job_tool_manager.print_workflow()
        return True
