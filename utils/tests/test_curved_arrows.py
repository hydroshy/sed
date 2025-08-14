#!/usr/bin/env python3
"""
Test script to verify curved arrow functionality in JobTreeView
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import Qt
from gui.job_tree_view import JobTreeView
from job.job_manager import JobManager

class CurvedArrowTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("dY� Test Curved Arrows - Cognex Style")
        self.setGeometry(100, 100, 500, 700)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create JobTreeView
        self.job_tree_view = JobTreeView(self)
        layout.addWidget(self.job_tree_view)
        
        # Add test buttons
        test_btn = QPushButton("dYZ_ Add Cognex Test Workflow")
        test_btn.clicked.connect(self.add_cognex_workflow)
        layout.addWidget(test_btn)
        
        clear_btn = QPushButton("dY1 Clear All")
        clear_btn.clicked.connect(self.clear_workflow)
        layout.addWidget(clear_btn)
        
        # Create job manager
        self.job_manager = JobManager()
        
        # Create a default job first
        from job.job_manager import Job
        default_job = Job("Test Job", [], "Test job for curved arrows")
        self.job_manager.jobs.append(default_job)
        self.job_manager.current_job_index = 0
        
        # Add initial test
        self.add_cognex_workflow()
        
    def add_cognex_workflow(self):
        """Add Cognex Vision Pro style workflow for testing curved arrows"""
        current_job = self.job_manager.get_current_job()
        
        if current_job:
            # Clear existing tools
            current_job.tools = []
            
            # Create Cognex-style workflow: 1 Camera Source �+' 3 Detect Tools
            camera_tool = type('Tool', (), {
                'name': 'Camera Source',
                'display_name': 'dY"� Camera Source #1',
                'tool_id': 1,
                'config': {}
            })()
            
            detect_tool1 = type('Tool', (), {
                'name': 'Detect Tool', 
                'display_name': 'dY"? Object Detection #2',
                'tool_id': 2,
                'config': {'model_name': 'yolov11n'}
            })()
            
            detect_tool2 = type('Tool', (), {
                'name': 'Detect Tool',
                'display_name': 'dY"? Text Detection #3', 
                'tool_id': 3,
                'config': {'model_name': 'yolov11n'}
            })()
            
            detect_tool3 = type('Tool', (), {
                'name': 'Detect Tool',
                'display_name': 'dY"? Defect Detection #4', 
                'tool_id': 4,
                'config': {'model_name': 'yolov11n'}
            })()
            
            # Add tools to job
            current_job.tools = [camera_tool, detect_tool1, detect_tool2, detect_tool3]
            
            # Update the tree view
            self.job_tree_view.update_job_view(current_job)
            
            print("dYZ_ Cognex workflow created!")
            print("dY"� Camera Source should have curved arrows pointing to ALL 3 Detect Tools")
            print("dY"' Look for THICK RED curved lines connecting the tools")
        else:
            print("�?O Could not get current job")
            
    def clear_workflow(self):
        """Clear the workflow"""
        current_job = self.job_manager.get_current_job()
        if current_job:
            current_job.tools = []
            self.job_tree_view.update_job_view(current_job)
            print("dY1 Workflow cleared")

def main():
    app = QApplication(sys.argv)
    
    window = CurvedArrowTestWindow()
    window.show()
    
    print("dY� Curved Arrow Test Window launched!")
    print("dY"' RED thick lines = U-shaped arrows being drawn")
    print("dY"� Right control area (light gray) = Arrow management zone")
    print("dYZ_ Arrows point INTO tools (end inside target, not outside)")
    print("dY"� U-shaped arrows (right angles) pointing INTO targets �S"�+'dY"�")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

