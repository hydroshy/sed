#!/usr/bin/env python3
"""
Test script to demonstrate JobTreeView arrows and connections
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from gui.job_tree_view import JobTreeView

class MockTool:
    def __init__(self, name, tool_id=1):
        self.name = name
        self.display_name = name
        self.tool_id = tool_id

class MockJob:
    def __init__(self, name="Test Job"):
        self.name = name
        self.tools = []
    
    def add_tool(self, tool):
        self.tools.append(tool)

class JobTreeTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JobTreeView Arrow Test - Cognex Vision Pro Style")
        self.setGeometry(100, 100, 800, 600)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Create JobTreeView
        self.job_tree = JobTreeView()
        layout.addWidget(self.job_tree)
        
        # Create control buttons
        button_layout = QHBoxLayout()
        
        self.demo_btn = QPushButton("Create Demo Connections")
        self.demo_btn.clicked.connect(self.job_tree.create_demo_connections)
        button_layout.addWidget(self.demo_btn)
        
        self.toggle_btn = QPushButton("Toggle Parallel/Sequential")
        self.toggle_btn.clicked.connect(self.job_tree.toggle_parallel_sequential)
        button_layout.addWidget(self.toggle_btn)
        
        self.debug_btn = QPushButton("Print Debug Info")
        self.debug_btn.clicked.connect(self.job_tree.print_debug_info)
        button_layout.addWidget(self.debug_btn)
        
        self.clear_btn = QPushButton("Clear Connections")
        self.clear_btn.clicked.connect(self.job_tree.clear_all_connections)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        # Create test job with tools
        self.setup_test_job()
        
        # Connect signals
        self.job_tree.tool_connected.connect(self.on_tool_connected)
        self.job_tree.tool_disconnected.connect(self.on_tool_disconnected)
        self.job_tree.tool_selected.connect(self.on_tool_selected)
        
        print("=== JobTreeView Test Window Ready ===")
        print("Click 'Create Demo Connections' to see arrows!")
        print("Click 'Toggle Parallel/Sequential' to switch modes")
        print("=====================================")
    
    def setup_test_job(self):
        """Create a test job with camera source and detect tools"""
        # Create mock job
        job = MockJob("Cognex Test Job")
        
        # Add tools
        camera = MockTool("Camera Source", 1)
        detect1 = MockTool("Detect Tool 1", 2) 
        detect2 = MockTool("Detect Tool 2", 3)
        other_tool = MockTool("Analysis Tool", 4)
        
        job.add_tool(camera)
        job.add_tool(detect1)
        job.add_tool(detect2)
        job.add_tool(other_tool)
        
        # Update the job tree view
        self.job_tree.update_job_view(job)
        
        print(f"Created test job with {len(job.tools)} tools:")
        for i, tool in enumerate(job.tools):
            print(f"  {i}: {tool.display_name}")
    
    def on_tool_connected(self, source_idx, target_idx):
        print(f"SIGNAL: Tool {source_idx} connected to tool {target_idx}")
    
    def on_tool_disconnected(self, source_idx, target_idx):
        print(f"SIGNAL: Tool {source_idx} disconnected from tool {target_idx}")
    
    def on_tool_selected(self, tool_idx):
        print(f"SIGNAL: Tool {tool_idx} selected")

def main():
    app = QApplication(sys.argv)
    
    # Create and show test window
    window = JobTreeTestWindow()
    window.show()
    
    # Run the application
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
