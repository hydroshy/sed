"""
Workflow management module for SED (Smart Eye Detection).

This module provides workflow management capabilities, allowing users to
create, save, load, and execute workflows consisting of multiple processing tools.
"""

from .workflow_manager import WorkflowManager, Workflow, WorkflowStep

__all__ = ['WorkflowManager', 'Workflow', 'WorkflowStep']
