import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import Qt

class WidgetInspector(QMainWindow):
    def __init__(self, target_window=None):
        super().__init__()
        self.target_window = target_window
        self.setWindowTitle("Widget Inspector")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        
        # Tree widget to display widget hierarchy
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Widget", "Type", "Object Name", "Enabled", "Visible", "Geometry"])
        layout.addWidget(self.tree)
        
        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.populate_tree)
        layout.addWidget(refresh_button)
        
        self.setCentralWidget(central_widget)
        
    def populate_tree(self):
        """Populate the tree with all top-level widgets"""
        self.tree.clear()
        
        if self.target_window:
            # Add target window as root
            self._add_widget_to_tree(self.target_window, None)
        else:
            # Add all top-level widgets
            for widget in QApplication.topLevelWidgets():
                self._add_widget_to_tree(widget, None)
                
        # Expand root items
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item:
                item.setExpanded(True)
            
    def _add_widget_to_tree(self, widget, parent_item):
        """Add a widget and all its children to the tree"""
        if parent_item is None:
            # Top level widget
            item = QTreeWidgetItem(self.tree)
        else:
            # Child widget
            item = QTreeWidgetItem(parent_item)
            
        # Set widget information
        name = widget.objectName() if widget.objectName() else "(no name)"
        item.setText(0, name)
        item.setText(1, widget.__class__.__name__)
        item.setText(2, name)  # Object name again for clarity
        item.setText(3, str(widget.isEnabled()))
        item.setText(4, str(widget.isVisible()))
        geometry = widget.geometry()
        item.setText(5, f"({geometry.x()}, {geometry.y()}, {geometry.width()}, {geometry.height()})")
        
        # Add all child widgets
        for child in widget.findChildren(QWidget, ""):
            if child.parent() == widget:  # Only direct children
                self._add_widget_to_tree(child, item)
            
def show_widget_inspector(target_window=None):
    """Show the widget inspector window"""
    inspector = WidgetInspector(target_window)
    inspector.show()
    inspector.populate_tree()
    return inspector
