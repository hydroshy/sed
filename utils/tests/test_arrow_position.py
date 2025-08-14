#!/usr/bin/env python3
"""
Test script to verify JobTreeView arrow positioning
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import Qt
from gui.job_tree_view import JobTreeView
from job.job_manager import JobManager

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Arrow Position - JobTreeView")
        self.setGeometry(100, 100, 400, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create JobTreeView
        self.job_tree_view = JobTreeView(self)
        layout.addWidget(self.job_tree_view)
        
        # Add test button
        test_btn = QPushButton("Add Test Tools")
        test_btn.clicked.connect(self.add_test_tools)
        layout.addWidget(test_btn)
        
        # Create job manager and test job
        self.job_manager = JobManager()
        self.add_test_tools()
        
    def add_test_tools(self):
        """Add test tools to see Cognex-style arrow positioning"""
        # Create a test job with multiple tools
        current_job = self.job_manager.get_current_job()
        
        # Clear existing tools
        if current_job:
            current_job.tools = []
            
            # Add test tools - Cognex Vision Pro style workflow
            tool1 = type('Tool', (), {
                'name': 'Camera Source',
                'display_name': 'dY"� Camera Source #1',
                'tool_id': 1,
                'config': {}
            })()
            
            tool2 = type('Tool', (), {
                'name': 'Detect Tool', 
                'display_name': 'dY"? Detect (yolov11n) #2',
                'tool_id': 2,
                'config': {'model_name': 'yolov11n'}
            })()
            
            tool3 = type('Tool', (), {
                'name': 'Detect Tool',
                'display_name': 'dY"? Detect (yolov11n) #3', 
                'tool_id': 3,
                'config': {'model_name': 'yolov11n'}
            })()
            
            tool4 = type('Tool', (), {
                'name': 'Detect Tool',
                'display_name': 'dY"? Detect (yolov11n) #4', 
                'tool_id': 4,
                'config': {'model_name': 'yolov11n'}
            })()
            
            current_job.tools = [tool1, tool2, tool3, tool4]
            
            # Update the tree view
            self.job_tree_view.update_job_view(current_job)
            print("dYZ_ Added Cognex-style test tools!")
            print("dY"� Camera Source should connect to ALL Detect Tools simultaneously")
            print("dY"? Multiple arrows should point from Camera Source to each Detect Tool")
        else:
            print("�?O Could not get current job")

def main():
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    print("dYs? Test window created - Testing Cognex Vision Pro style arrows!")
    print("dY"� Camera Source should have multiple arrows pointing to ALL Detect Tools")
    print("dY"? This demonstrates parallel workflow connections, not just sequential")
    print("�o" Look for curved arrows connecting Camera Source to multiple Detect Tools!")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

