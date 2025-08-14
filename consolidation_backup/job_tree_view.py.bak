"""
Custom QTreeView for Job Manager with drag-drop support and arrow indicators
Inspired by Cognex Vision Pro interface
"""
import logging
import math
from typing import Optional, Union
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QPoint, QRect
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QPainter, QPen, QBrush, QColor, QFont, QDragEnterEvent, QDropEvent, QMouseEvent, QPaintEvent, QDragMoveEvent
from PyQt5.QtWidgets import QTreeView, QAbstractItemView, QStyle, QStyleOptionViewItem

logger = logging.getLogger(__name__)

class JobTreeView(QTreeView):
    """
    Custom TreeView with drag-drop support and visual flow indicators
    """
    
    # Signals
    tool_moved = pyqtSignal(int, int)  # from_index, to_index
    tool_selected = pyqtSignal(int)    # tool_index
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_drag_drop()
        self.setAlternatingRowColors(True)
        self.setIndentation(20)
        
    def setup_drag_drop(self):
        """Setup drag and drop functionality"""
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        
    def paintEvent(self, e: Optional[QPaintEvent]):
        """Override paint event to draw arrows between tools"""
        super().paintEvent(e)
        
        model = self.model()
        if not isinstance(model, QStandardItemModel):
            return
            
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw flow arrows between tools
        self.draw_flow_arrows(painter, model)
        
    def draw_flow_arrows(self, painter: QPainter, model: QStandardItemModel):
        """Draw arrows indicating flow between tools"""
        if model.rowCount() == 0:
            return
            
        # Get job root item
        job_item = model.item(0)
        if not job_item:
            return
            
        tool_count = job_item.rowCount()
        if tool_count < 2:
            return
            
        # Set up pen for arrows
        pen = QPen(QColor(70, 130, 180), 2)  # Steel blue
        painter.setPen(pen)
        
        # Draw arrows between consecutive tools
        for i in range(tool_count - 1):
            current_tool = job_item.child(i)
            next_tool = job_item.child(i + 1)
            
            if current_tool and next_tool:
                current_index = model.indexFromItem(current_tool)
                next_index = model.indexFromItem(next_tool)
                
                current_rect = self.visualRect(current_index)
                next_rect = self.visualRect(next_index)
                
                # Calculate arrow positions
                start_point = QPoint(
                    current_rect.right() - 10,
                    current_rect.center().y()
                )
                end_point = QPoint(
                    next_rect.left() + 10,
                    next_rect.center().y()
                )
                
                # Draw arrow line
                painter.drawLine(start_point, end_point)
                
                # Draw arrowhead
                self.draw_arrowhead(painter, start_point, end_point)
                
    def draw_arrowhead(self, painter: QPainter, start_point: QPoint, end_point: QPoint):
        """Draw arrowhead at the end of the line"""
        # Calculate arrow direction
        dx = end_point.x() - start_point.x()
        dy = end_point.y() - start_point.y()
        length = math.sqrt(dx*dx + dy*dy)
        
        if length == 0:
            return
            
        # Normalize direction
        unit_x = dx / length
        unit_y = dy / length
        
        # Arrow properties
        arrow_length = 8
        arrow_angle = math.pi / 6  # 30 degrees
        
        # Calculate arrowhead points
        cos_angle = math.cos(arrow_angle)
        sin_angle = math.sin(arrow_angle)
        
        # Left point of arrowhead
        left_x = end_point.x() - arrow_length * (unit_x * cos_angle + unit_y * sin_angle)
        left_y = end_point.y() - arrow_length * (unit_y * cos_angle - unit_x * sin_angle)
        
        # Right point of arrowhead
        right_x = end_point.x() - arrow_length * (unit_x * cos_angle - unit_y * sin_angle)
        right_y = end_point.y() - arrow_length * (unit_y * cos_angle + unit_x * sin_angle)
        
        # Draw arrowhead lines
        painter.drawLine(end_point, QPoint(int(left_x), int(left_y)))
        painter.drawLine(end_point, QPoint(int(right_x), int(right_y)))
        
    def startDrag(self, supportedActions):
        """Override to customize drag behavior"""
        indexes = self.selectedIndexes()
        if not indexes:
            return
            
        # Only allow dragging tool items, not job root
        index = indexes[0]
        if not index.parent().isValid():
            return  # Don't drag root item
            
        super().startDrag(supportedActions)
        
    def dragEnterEvent(self, e):
        """Handle drag enter event"""
        try:
            if e and e.mimeData() and hasattr(e.mimeData(), 'hasFormat'):
                if e.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
                    e.acceptProposedAction()
                else:
                    e.ignore()
            else:
                if e:
                    e.ignore()
        except Exception:
            if e:
                e.ignore()
            
    def dragMoveEvent(self, event):
        """Handle drag move event"""
        try:
            if event and event.mimeData() and hasattr(event.mimeData(), 'hasFormat'):
                if event.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
                    event.acceptProposedAction()
                else:
                    event.ignore()
            else:
                if event:
                    event.ignore()
        except Exception:
            if event:
                event.ignore()
            
    def dropEvent(self, e):
        """Handle drop event and emit signal for reordering"""
        try:
            if not e or not e.mimeData() or not hasattr(e.mimeData(), 'hasFormat'):
                if e:
                    e.ignore()
                return
                
            if not e.mimeData().hasFormat('application/x-qabstractitemmodeldatalist'):
                e.ignore()
                return
        except Exception:
            if e:
                e.ignore()
            return
            
        # Get drop position
        drop_index = self.indexAt(e.pos())
        if not drop_index.isValid():
            e.ignore()
            return
            
        # Get source indexes
        source_indexes = self.selectedIndexes()
        if not source_indexes:
            e.ignore()
            return
            
        source_index = source_indexes[0]
        
        # Only allow reordering within the same job
        if source_index.parent() != drop_index.parent():
            e.ignore()
            return
            
        # Calculate positions
        source_row = source_index.row()
        target_row = drop_index.row()
        
        if source_row != target_row:
            # Emit signal for tool reordering
            self.tool_moved.emit(source_row, target_row)
            e.acceptProposedAction()
        else:
            e.ignore()
            
    def mousePressEvent(self, e: Optional[QMouseEvent]):
        """Handle mouse press to emit selection signal"""
        super().mousePressEvent(e)
        
        if e and e.button() == Qt.MouseButton.LeftButton:
            index = self.indexAt(e.pos())
            if index.isValid() and index.parent().isValid():
                # Tool item clicked
                tool_row = index.row()
                self.tool_selected.emit(tool_row)
                
    def update_job_view(self, job):
        """Update the tree view with job data and flow indicators"""
        if not job:
            self.setModel(None)
            return
            
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Workflow Tools"])
        
        # Create job root item
        job_item = QStandardItem(f"📋 {job.name}")
        job_item.setEditable(False)
        job_item.setSelectable(False)
        
        # Add tools as children with enhanced display
        for i, tool in enumerate(job.tools):
            tool_item = self.create_tool_item(tool, i)
            job_item.appendRow(tool_item)
            
        model.appendRow(job_item)
        self.setModel(model)
        self.expandAll()
        
        # Update viewport to redraw arrows
        viewport = self.viewport()
        if viewport:
            viewport.update()
        
    def create_tool_item(self, tool, index: int) -> QStandardItem:
        """Create a standard item for a tool with proper formatting"""
        # Determine tool display info
        if isinstance(tool, dict):
            tool_name = tool.get('display_name', tool.get('name', f"Tool #{index+1}"))
            tool_id = tool.get('tool_id', index+1)
            
            if 'model_name' in tool:
                # DetectTool
                model_name = tool.get('model_name', 'Unknown')
                display_text = f"🔍 Detect ({model_name}) #{tool_id}"
            elif tool_name and tool_name.lower() == "camera source":
                display_text = f"📷 Camera Source #{tool_id}"
            else:
                display_text = f"⚙️ {tool_name} #{tool_id}"
        else:
            # Object tool
            tool_name = getattr(tool, 'display_name', 
                              getattr(tool, 'name', f"Tool #{index+1}"))
            tool_id = getattr(tool, 'tool_id', index+1)
            
            if tool_name and tool_name.lower() == "camera source":
                display_text = f"📷 Camera Source #{tool_id}"
            elif hasattr(tool, 'display_name') and tool.display_name:
                display_text = f"🔧 {tool.display_name} #{tool_id}"
            else:
                display_text = f"⚙️ Tool #{tool_id}"
        
        # Add flow indicator for non-first tools
        if index > 0:
            display_text = f"↓ {display_text}"
        
        tool_item = QStandardItem(display_text)
        tool_item.setEditable(False)
        tool_item.setData(tool, role=256)  # Store tool reference
        
        # Add visual styling based on tool type
        if isinstance(tool, dict) and 'model_name' in tool:
            # DetectTool - blue color
            tool_item.setForeground(QBrush(QColor(70, 130, 180)))
        elif ((isinstance(tool, dict) and tool.get('name', '').lower() == "camera source") or
              (hasattr(tool, 'name') and getattr(tool, 'name', '').lower() == "camera source")):
            # Camera Source - green color
            tool_item.setForeground(QBrush(QColor(34, 139, 34)))
        
        return tool_item
        
    def get_selected_tool_index(self) -> int:
        """Get the index of the currently selected tool"""
        indexes = self.selectedIndexes()
        if indexes and indexes[0].parent().isValid():
            return indexes[0].row()
        return -1
        
    def select_tool(self, tool_index: int):
        """Programmatically select a tool by index"""
        model = self.model()
        if not isinstance(model, QStandardItemModel) or model.rowCount() == 0:
            return
            
        job_item = model.item(0)
        if not job_item or tool_index >= job_item.rowCount():
            return
            
        tool_item = job_item.child(tool_index)
        if tool_item:
            tool_model_index = model.indexFromItem(tool_item)
            self.setCurrentIndex(tool_model_index)
            self.scrollTo(tool_model_index)
