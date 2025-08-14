"""
Test script for JobTreeView with sequential workflow arrows and step numbers
Tests Camera Source �+' Detect Tool 1 �+' Detect Tool 2 workflow
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt
from gui.job_tree_view import JobTreeView
from job.job_manager import JobManager
from tools.camera_tool import CameraTool
from tools.detect_tool import DetectTool

class SequentialWorkflowTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sequential Workflow Test - Camera Source �+' Detect Tool 1 �+' Detect Tool 2")
        self.setGeometry(100, 100, 800, 600)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Create job manager
        self.job_manager = JobManager()
        
        # Create JobTreeView
        self.job_tree_view = JobTreeView()
        layout.addWidget(self.job_tree_view)
        
        # Create control buttons
        button_layout = QHBoxLayout()
        
        self.create_workflow_btn = QPushButton("Create Sequential Workflow")
        self.create_workflow_btn.clicked.connect(self.create_sequential_workflow)
        button_layout.addWidget(self.create_workflow_btn)
        
        self.add_detect_tool_btn = QPushButton("Add Another Detect Tool")
        self.add_detect_tool_btn.clicked.connect(self.add_detect_tool)
        button_layout.addWidget(self.add_detect_tool_btn)
        
        self.clear_workflow_btn = QPushButton("Clear Workflow")
        self.clear_workflow_btn.clicked.connect(self.clear_workflow)
        button_layout.addWidget(self.clear_workflow_btn)
        
        layout.addLayout(button_layout)
        
        # Setup job tree view
        self.setup_job_tree()
        
        print("=== Sequential Workflow Test Window Initialized ===")
        print("Click 'Create Sequential Workflow' to test Camera Source �+' Detect Tool 1 �+' Detect Tool 2")
    
    def setup_job_tree(self):
        """Setup job tree view with job manager"""
        # Create a default job
        from job.job_manager import Job
        test_job = Job("Sequential Workflow Test")
        self.job_manager.add_job(test_job)
        self.job_manager.set_current_job(0)  # Set as current job
        current_job = self.job_manager.get_current_job()
        
        if current_job:
            # Setup the tree view with the job
            self.job_tree_view.setup_with_job_manager(self.job_manager)
            print(f"Job tree setup complete with job: {current_job.name}")
        else:
            print("ERROR: Failed to create default job")
    
    def create_sequential_workflow(self):
        """Create a sequential workflow: Camera Source �+' Detect Tool 1 �+' Detect Tool 2"""
        current_job = self.job_manager.get_current_job()
        if not current_job:
            print("ERROR: No current job available")
            return
        
        # Clear existing tools
        current_job.tools = []
        
        print("\n=== Creating Sequential Workflow ===")
        
        # Step 1: Add Camera Source
        camera_tool = CameraTool(tool_id=1)
        camera_tool.display_name = "Camera Source (Step 1)"
        current_job.add_tool(camera_tool)
        print(f"�o. Added: {camera_tool.display_name}")
        
        # Step 2: Add first Detect Tool
        detect_tool_1 = DetectTool(tool_id=2)
        detect_tool_1.display_name = "Detect Tool 1 (Step 2)"
        current_job.add_tool(detect_tool_1)
        print(f"�o. Added: {detect_tool_1.display_name}")
        
        # Step 3: Add second Detect Tool
        detect_tool_2 = DetectTool(tool_id=3)
        detect_tool_2.display_name = "Detect Tool 2 (Step 3)"
        current_job.add_tool(detect_tool_2)
        print(f"�o. Added: {detect_tool_2.display_name}")
        
        # Update the tree view
        self.job_tree_view.update_from_job_manager()
        
        print(f"\ndYZ_ Sequential workflow created:")
        print(f"   Step 1: {camera_tool.display_name}")
        print(f"   Step 2: {detect_tool_1.display_name}")
        print(f"   Step 3: {detect_tool_2.display_name}")
        print(f"\ndY", Workflow should show arrows: 1�+'2�+'3 with different colors and step numbers")
        
    def add_detect_tool(self):
        """Add another detect tool to extend the workflow"""
        current_job = self.job_manager.get_current_job()
        if not current_job:
            print("ERROR: No current job available")
            return
        
        # Get next tool ID
        next_id = len(current_job.tools) + 1
        next_step = len(current_job.tools) + 1
        
        # Add new detect tool
        detect_tool = DetectTool(tool_id=next_id)
        detect_tool.display_name = f"Detect Tool {next_step - 1} (Step {next_step})"
        current_job.add_tool(detect_tool)
        
        print(f"\n�o. Added: {detect_tool.display_name}")
        
        # Update the tree view
        self.job_tree_view.update_from_job_manager()
        
        print(f"dY", Extended workflow now has {len(current_job.tools)} steps")
        
    def clear_workflow(self):
        """Clear all tools from workflow"""
        current_job = self.job_manager.get_current_job()
        if not current_job:
            print("ERROR: No current job available")
            return
        
        # Clear all tools
        current_job.tools = []
        
        # Update the tree view
        self.job_tree_view.update_from_job_manager()
        
        print("\ndY1 Workflow cleared - no tools remaining")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = SequentialWorkflowTestWindow()
    window.show()
    
    print("\n" + "="*60)
    print("dYs? Sequential Workflow Test Started")
    print("="*60)
    print("Features to test:")
    print("1. Sequential arrows: Camera Source �+' Detect Tool 1 �+' Detect Tool 2")
    print("2. Step numbers displayed with different colors")
    print("3. Workflow step indicators next to each tool")
    print("4. Drag-drop to reorder workflow steps")
    print("="*60)
    
    sys.exit(app.exec_())

