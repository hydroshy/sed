"""
Custom QTreeView for Job Manager with drag-drop support and arrow indicators
Inspired by Cognex Vision Pro interface
"""
import logging
import math
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QPoint
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QPainter, QPen, QBrush, QColor, QDrag
from PyQt5.QtWidgets import QTreeView, QAbstractItemView, QApplication

logger = logging.getLogger(__name__)

class JobTreeView(QTreeView):
    """
    Custom TreeView with connection-based workflow like Cognex Vision Pro
    """
    
    # Signals
    tool_moved = pyqtSignal(int, int)  # from_index, to_index
    tool_selected = pyqtSignal(int)    # tool_index
    tool_connected = pyqtSignal(int, int)  # source_tool_index, target_tool_index
    tool_disconnected = pyqtSignal(int, int)  # source_tool_index, target_tool_index
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_drag_drop()
        self.setAlternatingRowColors(True)
        self.setIndentation(20)
        self.setHeaderHidden(False)
        self.setUniformRowHeights(True)  # Better for drag-drop performance
        
        # Set up right margin for arrow control area (Cognex style)
        self.arrow_control_width = 100  # Wider for better visibility
        self.setViewportMargins(0, 0, self.arrow_control_width, 0)
        
        # Enhanced visual feedback
        self.setStyleSheet("""
            QTreeView {
                show-decoration-selected: 1;
                border: 1px solid #d0d0d0;
                background-color: #fafafa;
            }
            QTreeView::item {
                border: none;
                padding: 4px 8px;
                min-height: 24px;
            }
            QTreeView::item:selected {
                background-color: #3daee9;
                color: white;
            }
            QTreeView::item:hover {
                background-color: #e6f3ff;
            }
            QTreeView::drop-indicator {
                background-color: #3daee9;
                height: 3px;
                border-radius: 1px;
            }
        """)
        
        # Drag state tracking
        self.drag_start_position = None
        self.is_dragging = False
        self.connection_dragging = False
        self.drag_source_tool = None
        self.drag_target_tool = None
        
        # Connection management
        self.tool_connections = {}  # {source_tool_index: [target_tool_indices]}
        self.port_size = 12  # Larger ports for better visibility
        self.port_margin = 4
        
        # Demo connections for testing
        self.demo_mode = True
        
    def setup_drag_drop(self):
        """Setup drag and drop functionality"""
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        print(f"DEBUG: JobTreeView drag-drop setup complete:")
        print(f"  - Drag enabled: {self.dragEnabled()}")
        print(f"  - Accept drops: {self.acceptDrops()}")
        print(f"  - Drop indicator shown: {self.showDropIndicator()}")
        print(f"  - Drag drop mode: {self.dragDropMode()}")
        
    def paintEvent(self, event):
        """Override paint event to draw connection-based workflow"""
        super().paintEvent(event)
        
        model = self.model()
        if not isinstance(model, QStandardItemModel):
            return
            
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw input/output ports on tools
        self.draw_tool_ports(painter, model)
        
        # Draw connections between tools
        self.draw_tool_connections(painter, model)
        
        # Draw temporary connection during dragging
        if self.connection_dragging and self.drag_start_position:
            self.draw_temp_connection(painter)
        
    def draw_arrow_control_area(self, painter):
        """Draw the right control area background (Cognex style)"""
        viewport_rect = self.viewport().rect()
        control_area_rect = viewport_rect.adjusted(
            viewport_rect.width() - self.arrow_control_width, 0, 0, 0
        )
        
        # Fill with light gray background to show control area
        painter.fillRect(control_area_rect, QColor(248, 248, 248))
        
        # Draw border
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawRect(control_area_rect)
        
    def draw_flow_arrows_in_control_area(self, painter, model):
        """Draw arrows in the right control area - Cognex Vision Pro style"""
        if model.rowCount() == 0:
            return
            
        # Get job root item
        job_item = model.item(0)
        if not job_item:
            return
            
        tool_count = job_item.rowCount()
        if tool_count < 2:
            return
        
        # Get control area bounds
        viewport_rect = self.viewport().rect()
        control_x_start = viewport_rect.width() - self.arrow_control_width + 10  # 10px margin from left edge
        control_width = self.arrow_control_width - 100  # 10px margin on each side
        
        # Collect tools information  
        tools = []
        for i in range(tool_count):
            tool_item = job_item.child(i)
            if tool_item:
                # Get tool rectangle for vertical positioning
                tool_index = model.indexFromItem(tool_item)
                tool_rect = self.visualRect(tool_index)
                
                tools.append({
                    'index': i,
                    'item': tool_item,
                    'name': tool_item.text(),
                    'type': self.get_tool_type(tool_item.text()),
                    'rect': tool_rect,
                    'y_center': tool_rect.center().y()
                })
        
        # Set up pen for arrows in control area
        pen = QPen(QColor(255, 0, 0), 1)  # Thick red for debugging
        painter.setPen(pen)
        
        # Draw connections in the control area
        self.draw_control_area_connections(painter, tools, control_x_start, control_width)
        
    def draw_control_area_connections(self, painter, tools, control_x_start, control_width):
        """Draw sequential workflow connections within the right control area"""
        print(f"DEBUG: Drawing sequential workflow for {len(tools)} tools:")
        print(f"  Control area: x={control_x_start}, width={control_width}")
        
        if len(tools) < 2:
            print("  Need at least 2 tools for connections")
            return
        
        # Sort tools by their vertical position (index) to maintain order
        sorted_tools = sorted(tools, key=lambda t: t['index'])
        
        # Draw sequential connections: tool[i] → tool[i+1]
        for i in range(len(sorted_tools) - 1):
            source_tool = sorted_tools[i]
            target_tool = sorted_tools[i + 1]
            
            source_y = source_tool['y_center']
            target_y = target_tool['y_center']
            
            # Position arrows in control area
            source_x = control_x_start + 30  # Start point
            target_x = control_x_start + control_width - 30  # End point INSIDE control area
            
            print(f"  Step {i+1}: {source_tool['name']} → {target_tool['name']}")
            print(f"    Source y={source_y}, Target y={target_y}")
            
            # Draw sequential connection with step number
            self.draw_control_area_curve_with_step(painter, source_x, source_y, target_x, target_y, i + 1)
            
        # Draw workflow step numbers on the left side
        self.draw_workflow_step_numbers(painter, sorted_tools, control_x_start)
                
    def draw_control_area_curve_with_step(self, painter, start_x, start_y, end_x, end_y, step_number):
        """Draw a right-angle U-shaped arrow with step number that points INTO the target tool"""
        start_point = QPoint(start_x, start_y)
        end_point = QPoint(end_x, end_y)
        
        # Calculate U-shape path with right angles (like Cognex Vision Pro)
        mid_x = (start_x + end_x) // 2  # Midpoint for vertical segment
        
        # Create U-shape with three segments: horizontal out, vertical, horizontal into target
        point1 = QPoint(mid_x, start_y)     # Horizontal out from source
        point2 = QPoint(mid_x, end_y)       # Vertical down/up
        
        print(f"    Step {step_number} Arrow INTO target: ({start_x},{start_y}) → ({mid_x},{start_y}) → ({mid_x},{end_y}) → ({end_x},{end_y})")
        
        # Use different colors for different steps
        step_colors = [QColor(255, 0, 0), QColor(0, 150, 0), QColor(0, 0, 255), QColor(255, 165, 0)]  # Red, Green, Blue, Orange
        color = step_colors[(step_number - 1) % len(step_colors)]
        pen = QPen(color, 2)  # Thicker lines for better visibility
        painter.setPen(pen)
        
        # Draw the three line segments to form U-shape pointing INTO the target
        painter.drawLine(start_point, point1)  # Horizontal out
        painter.drawLine(point1, point2)       # Vertical segment  
        painter.drawLine(point2, end_point)    # Horizontal INTO target
        
        # Draw arrowhead pointing INTO the target (leftward)
        self.draw_leftward_arrowhead_colored(painter, end_point, color)
        
        # Draw step number near the middle of the arrow
        self.draw_step_number(painter, mid_x, (start_y + end_y) // 2, step_number, color)
        
    def draw_leftward_arrowhead_colored(self, painter, end_point, color):
        """Draw an arrowhead pointing INTO the target (leftward) with specific color"""
        arrow_size = 8
        
        # Set brush and pen for filled arrowhead
        brush = QBrush(color)
        pen = QPen(color, 2)
        painter.setBrush(brush)
        painter.setPen(pen)
        
        # Calculate arrowhead points (pointing left INTO the target)
        p1 = QPoint(end_point.x() + arrow_size, end_point.y() - arrow_size//2)  # Upper point
        p2 = QPoint(end_point.x() + arrow_size, end_point.y() + arrow_size//2)  # Lower point
        
        # Draw filled triangle arrowhead pointing left (INTO target)
        points = [end_point, p1, p2]
        painter.drawPolygon(points)
        
        print(f"    Colored arrowhead pointing INTO target at {end_point} with color {color.name()}")
        
    def draw_step_number(self, painter, x, y, step_number, color):
        """Draw step number on the workflow arrow"""
        # Save current pen
        old_pen = painter.pen()
        
        # Set font and color for step number
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        
        pen = QPen(color, 2)
        painter.setPen(pen)
        
        # Draw step number in a small circle
        circle_radius = 12
        circle_rect = QPoint(x - circle_radius//2, y - circle_radius//2)
        
        # Draw white background circle
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(x - circle_radius, y - circle_radius, circle_radius * 2, circle_radius * 2)
        
        # Draw step number
        painter.setPen(QPen(color, 2))
        painter.drawText(x - 5, y + 4, str(step_number))
        
        # Restore pen
        painter.setPen(old_pen)
        
    def draw_workflow_step_numbers(self, painter, sorted_tools, control_x_start):
        """Draw workflow step numbers next to each tool"""
        # Save current pen and font
        old_pen = painter.pen()
        old_font = painter.font()
        
        # Set font for step labels
        font = painter.font()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        
        for i, tool in enumerate(sorted_tools):
            step_number = i + 1
            y_pos = tool['y_center']
            
            # Position step number just inside the control area
            x_pos = control_x_start + 10
            
            # Use different colors for different tool types
            if tool['type'] == 'source':
                color = QColor(255, 0, 0)  # Red for source
            elif tool['type'] == 'detect':
                color = QColor(0, 150, 0)  # Green for detect
            else:
                color = QColor(0, 0, 255)  # Blue for other
            
            # Draw background circle
            painter.setBrush(QBrush(QColor(255, 255, 255, 200)))  # Semi-transparent white
            painter.setPen(QPen(color, 2))
            painter.drawEllipse(x_pos - 8, y_pos - 8, 16, 16)
            
            # Draw step number
            painter.setPen(QPen(color, 2))
            painter.drawText(x_pos - 4, y_pos + 4, str(step_number))
            
        # Restore pen and font
        painter.setPen(old_pen)
        painter.setFont(old_font)
        
    def get_tool_type(self, tool_text):
        """Determine tool type from display text"""
        if 'camera source' in tool_text.lower():
            return 'source'
        elif 'detect' in tool_text.lower():
            return 'detect'
        else:
            return 'other'
            
    def draw_cognex_style_connections(self, painter, model, tools):
        """Draw connections using Cognex Vision Pro logic - simplified for debugging"""
        print(f"DEBUG: Drawing connections for {len(tools)} tools:")
        for tool in tools:
            print(f"  - Tool {tool['index']}: {tool['name']} (type: {tool['type']})")
        
        # Find source tools (Camera Source, etc.)
        source_tools = [t for t in tools if t['type'] == 'source']
        detect_tools = [t for t in tools if t['type'] == 'detect']
        other_tools = [t for t in tools if t['type'] == 'other']
        
        print(f"DEBUG: Found {len(source_tools)} source tools, {len(detect_tools)} detect tools")
        
        # Force curved arrows for testing - connect each source to all detect tools
        for source in source_tools:
            source_index = model.indexFromItem(source['item'])
            source_rect = self.visualRect(source_index)
            
            print(f"DEBUG: Source tool '{source['name']}' at position {source_rect}")
            
            for detect in detect_tools:
                detect_index = model.indexFromItem(detect['item'])
                detect_rect = self.visualRect(detect_index)
                
                print(f"DEBUG: Drawing curved arrow from source to '{detect['name']}' at {detect_rect}")
                
                # Always use curved arrows for source-to-detect connections
                self.draw_curved_arrow_simple(painter, source_rect, detect_rect)
        
        # If no sources found, use sequential connections for debugging
        if not source_tools and len(tools) > 1:
            print("DEBUG: No source tools found, using sequential connections")
            for i in range(len(tools) - 1):
                current_index = model.indexFromItem(tools[i]['item'])
                next_index = model.indexFromItem(tools[i + 1]['item'])
                
                current_rect = self.visualRect(current_index)
                next_rect = self.visualRect(next_index)
                
                print(f"DEBUG: Sequential arrow from tool {i} to {i+1}")
                self.draw_arrow_between_tools(painter, current_rect, next_rect, f"seq_{i}")
                
    def draw_curved_arrow_simple(self, painter, source_rect, target_rect):
        """Draw a simple curved arrow that's easy to see and debug - pointing left"""
        print(f"DEBUG: draw_curved_arrow_simple called")
        print(f"  Source rect: {source_rect}")
        print(f"  Target rect: {target_rect}")
        
        # Start point on the right edge of target tool (arrow starts from right)
        start_x = target_rect.right() - 5
        start_y = target_rect.center().y()
        start_point = QPoint(start_x, start_y)
        
        # End point on the left edge of source tool (arrow points to left)
        end_x = source_rect.left() + 5
        end_y = source_rect.center().y()
        end_point = QPoint(end_x, end_y)
        
        print(f"  Start point (right side): {start_point}")
        print(f"  End point (left side): {end_point}")
        
        # Use a much stronger curve for visibility
        control_offset = 60  # Increased for more visible curve
        
        # Control points for bezier curve - curve going LEFT
        ctrl1_x = start_x + control_offset  # Go out to the right first
        ctrl1_y = start_y
        ctrl1 = QPoint(ctrl1_x, ctrl1_y)
        
        ctrl2_x = end_x - control_offset  # Then curve back to the left
        ctrl2_y = end_y
        ctrl2 = QPoint(ctrl2_x, ctrl2_y)
        
        print(f"  Control point 1 (right): {ctrl1}")
        print(f"  Control point 2 (left): {ctrl2}")
        
        # Set a thicker pen for visibility during testing
        pen = QPen(QColor(255, 0, 0), 3)  # Thick red line for debugging
        painter.setPen(pen)
        
        # Draw the curve using multiple line segments
        segments = 30
        prev_point = start_point
        
        for i in range(1, segments + 1):
            t = i / segments
            
            # Calculate point on cubic bezier curve
            point = self.bezier_point_simple(start_point, ctrl1, ctrl2, end_point, t)
            
            # Draw line segment
            painter.drawLine(prev_point, point)
            prev_point = point
        
        # Draw arrowhead at end (pointing LEFT)
        self.draw_leftward_arrowhead(painter, end_point)
        
        print(f"  Curved arrow drawn with {segments} segments")
        
    def bezier_point_simple(self, p0, p1, p2, p3, t):
        """Calculate point on cubic bezier curve - simplified version"""
        # Cubic bezier: B(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃
        u = 1 - t
        tt = t * t
        uu = u * u
        uuu = uu * u
        ttt = tt * t
        
        # Calculate x and y coordinates
        x = uuu * p0.x() + 3 * uu * t * p1.x() + 3 * u * tt * p2.x() + ttt * p3.x()
        y = uuu * p0.y() + 3 * uu * t * p1.y() + 3 * u * tt * p2.y() + ttt * p3.y()
        
        return QPoint(int(x), int(y))
    def draw_arrow_between_tools(self, painter, source_rect, target_rect, connection_id):
        """Draw an arrow between two tool rectangles - simplified for testing"""
        print(f"DEBUG: draw_arrow_between_tools called with connection_id: {connection_id}")
        
        # For now, always use curved arrows to test the functionality
        print(f"DEBUG: Using curved arrow for connection {connection_id}")
        self.draw_curved_arrow_simple(painter, source_rect, target_rect)
        
    def draw_horizontal_arrowhead(self, painter, end_point):
        """Draw rightward pointing arrowhead for horizontal connections"""
        arrow_size = 8  # Slightly larger for visibility
        
        # Draw arrowhead pointing right with thicker red line for debugging
        top_point = QPoint(end_point.x() - arrow_size, end_point.y() - arrow_size)
        bottom_point = QPoint(end_point.x() - arrow_size, end_point.y() + arrow_size)
        
        # Use thick red pen for debugging
        pen = QPen(QColor(255, 0, 0), 3)  # Thick red
        painter.setPen(pen)
        
    def draw_leftward_arrowhead(self, painter, end_point):
        """Draw leftward pointing arrowhead for connections pointing left - pointing INTO the target"""
        arrow_size = 8  # Slightly larger for visibility
        
        # Draw arrowhead pointing LEFT (into the target) with thicker red line for debugging
        top_point = QPoint(end_point.x() + arrow_size, end_point.y() - arrow_size)
        bottom_point = QPoint(end_point.x() + arrow_size, end_point.y() + arrow_size)
        
        # Use thick red pen for debugging
        pen = QPen(QColor(255, 0, 0), 1)  # Thick red
        painter.setPen(pen)
        
        # Draw the arrowhead triangle pointing LEFT (INTO the target tool)
        painter.drawLine(end_point, top_point)
        painter.drawLine(end_point, bottom_point)
        painter.drawLine(top_point, bottom_point)  # Close the triangle
        
        print(f"DEBUG: Leftward arrowhead drawn pointing INTO target at {end_point}")
        
        painter.drawLine(end_point, top_point)
        painter.drawLine(end_point, bottom_point)
        
        print(f"DEBUG: Drew arrowhead at {end_point}")
                
    def draw_vertical_arrowhead(self, painter, end_point):
        """Draw downward pointing arrowhead with better visibility"""
        arrow_size = 6  # Increased size for better visibility
        
        # Draw arrowhead pointing down with thicker lines
        left_point = QPoint(end_point.x() - arrow_size, end_point.y() - arrow_size)
        right_point = QPoint(end_point.x() + arrow_size, end_point.y() - arrow_size)
        
        # Draw arrowhead lines with thicker pen
        pen = painter.pen()
        old_width = pen.width()
        pen.setWidth(2)  # Thicker line for arrowhead
        painter.setPen(pen)
        
        painter.drawLine(end_point, left_point)
        painter.drawLine(end_point, right_point)
        
        # Restore original pen width
        pen.setWidth(old_width)
        painter.setPen(pen)
        
    def startDrag(self, supportedActions):
        """Override to customize drag behavior with custom MIME data"""
        print("DEBUG: JobTreeView.startDrag called")
        indexes = self.selectedIndexes()
        if not indexes:
            print("DEBUG: No indexes selected")
            return
            
        # Only allow dragging tool items, not job root
        index = indexes[0]
        if not index.parent().isValid():
            print("DEBUG: Cannot drag root item")
            return  # Don't drag root item
            
        print(f"DEBUG: Starting drag for index: row={index.row()}, parent valid={index.parent().isValid()}")
        
        # Create custom MIME data with just the row number instead of full object
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Store only the row index as text to avoid pickling issues
        row_data = str(index.row())
        mime_data.setText(row_data)
        mime_data.setData("application/x-jobtool-row", row_data.encode())
        
        drag.setMimeData(mime_data)
        
        print(f"DEBUG: Created custom MIME data for row {index.row()}")
        
        # Execute drag operation
        drop_action = drag.exec_(Qt.DropAction.MoveAction)
        
    def dragEnterEvent(self, e):
        """Handle drag enter event"""
        print(f"DEBUG: JobTreeView.dragEnterEvent called")
        if e:
            print(f"  - Event source: {e.source()}")
            print(f"  - Event actions: {e.possibleActions()}")
            print(f"  - Event position: {e.pos()}")
            try:
                e.acceptProposedAction()
                print("DEBUG: Drag enter accepted")
            except Exception as ex:
                print(f"DEBUG: Drag enter error: {ex}")
                e.ignore()
        
    def dragMoveEvent(self, event):
        """Handle drag move event"""
        # Don't spam debug messages for move events
        if event:
            try:
                event.acceptProposedAction()  
            except Exception as ex:
                print(f"DEBUG: Drag move error: {ex}")
                event.ignore()
            
    def dropEvent(self, e):
        """Handle drop event and emit signal for reordering"""
        print(f"DEBUG: JobTreeView.dropEvent called")
        print(f"  - Event source: {e.source()}")
        print(f"  - Event position: {e.pos()}")
        
        try:
            # Check if we have our custom MIME data
            if not e.mimeData().hasFormat("application/x-jobtool-row"):
                print("DEBUG: No custom MIME data found")
                e.ignore()
                return
                
            # Get drop position
            drop_index = self.indexAt(e.pos())
            if not drop_index.isValid():
                print("DEBUG: Drop index invalid")
                e.ignore()
                return
                
            # Get source row from MIME data
            try:
                row_data = e.mimeData().data("application/x-jobtool-row").data().decode()
                source_row = int(row_data)
                print(f"DEBUG: Source row from MIME: {source_row}")
            except (ValueError, AttributeError) as ex:
                print(f"DEBUG: Failed to parse row data: {ex}")
                e.ignore()
                return
                
            # Calculate target position
            target_row = drop_index.row()
            
            # Only allow reordering within the same job (tools)
            if not drop_index.parent().isValid():
                print("DEBUG: Cannot drop on root item")
                e.ignore()
                return
                
            print(f"DEBUG: Moving tool from row {source_row} to row {target_row}")
            
            if source_row != target_row:
                # Emit signal for tool reordering
                self.tool_moved.emit(source_row, target_row)
                e.acceptProposedAction()
                print("DEBUG: Drop accepted and signal emitted")
            else:
                print("DEBUG: Source and target are same")
                e.ignore()
        except Exception as ex:
            print(f"DEBUG: Drop event error: {ex}")
            e.ignore()
            
    def mousePressEvent(self, e):
        """Handle mouse press to emit selection signal and start drag detection"""
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = e.pos()
            
        super().mousePressEvent(e)
        
        try:
            if e and hasattr(e, 'button') and e.button() == Qt.MouseButton.LeftButton:
                index = self.indexAt(e.pos())
                if index.isValid() and index.parent().isValid():
                    # Tool item clicked
                    tool_row = index.row()
                    self.tool_selected.emit(tool_row)
                    print(f"DEBUG: Tool selected at row {tool_row}")
        except Exception as ex:
            logger.error(f"Mouse press error: {ex}")
    
    def mouseMoveEvent(self, e):
        """Handle mouse move for drag detection"""
        if not (e.buttons() & Qt.MouseButton.LeftButton):
            return
            
        if not self.drag_start_position:
            return
            
        # Check if we should start dragging
        if ((e.pos() - self.drag_start_position).manhattanLength() < 
            QApplication.startDragDistance()):
            return
            
        # Only drag tool items, not the job root
        index = self.indexAt(self.drag_start_position)
        if not index.isValid() or not index.parent().isValid():
            return
            
        self.is_dragging = True
        self.startDrag(Qt.DropAction.MoveAction)
                
    def setup_with_job_manager(self, job_manager):
        """Setup tree view with job manager and update display"""
        self.job_manager = job_manager
        current_job = job_manager.get_current_job()
        if current_job:
            self.update_job_view(current_job)
            print(f"DEBUG: JobTreeView setup with job: {current_job.name}")
        else:
            print("DEBUG: No current job available for setup")
            
    def update_from_job_manager(self):
        """Update tree view from current job manager state"""
        if hasattr(self, 'job_manager') and self.job_manager:
            current_job = self.job_manager.get_current_job()
            if current_job:
                self.update_job_view(current_job)
                print(f"DEBUG: Updated JobTreeView from job manager: {len(current_job.tools)} tools")
            else:
                print("DEBUG: No current job to update from")
        else:
            print("DEBUG: No job manager available for update")
                
    def update_job_view(self, job):
        """Update the tree view with job data and flow indicators"""
        if not job:
            self.setModel(None)
            return
            
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Sequential Workflow"])
        
        # Create job root item
        job_item = QStandardItem(f"📋 {job.name}")
        job_item.setEditable(False)
        job_item.setSelectable(False)
        
        # Add tools as children with enhanced display including step numbers
        for i, tool in enumerate(job.tools):
            tool_item = self.create_tool_item_with_step(tool, i)
            job_item.appendRow(tool_item)
            
        model.appendRow(job_item)
        self.setModel(model)
        self.expandAll()
        
        # Update viewport to redraw arrows
        try:
            viewport = self.viewport()
            if viewport:
                viewport.update()
                print(f"DEBUG: Viewport updated for {len(job.tools)} tools")
        except Exception as ex:
            print(f"DEBUG: Viewport update error: {ex}")
            pass
        
    def create_tool_item_with_step(self, tool, index):
        """Create a standard item for a tool with step number and proper formatting"""
        try:
            step_number = index + 1
            
            # Get display name with fallback
            if hasattr(tool, 'display_name') and tool.display_name:
                display_name = tool.display_name
            elif hasattr(tool, 'name') and tool.name:
                display_name = tool.name
            else:
                display_name = f"Tool {tool.tool_id}" if hasattr(tool, 'tool_id') else f"Tool {index}"
            
            # Format with step number and appropriate icon
            if 'camera' in display_name.lower() or 'source' in display_name.lower():
                icon = "📹"
                tool_type = "source"
            elif 'detect' in display_name.lower():
                icon = "🔍"
                tool_type = "detect"
            else:
                icon = "⚙️"
                tool_type = "other"
            
            # Create item text with step number
            item_text = f"{step_number}. {icon} {display_name}"
            
            tool_item = QStandardItem(item_text)
            tool_item.setEditable(False)
            tool_item.setData(tool, Qt.ItemDataRole.UserRole)  # Store tool reference
            tool_item.setData(index, Qt.ItemDataRole.UserRole + 1)  # Store original index
            tool_item.setData(tool_type, Qt.ItemDataRole.UserRole + 2)  # Store tool type
            
            return tool_item
            
        except Exception as ex:
            logger.error(f"Error creating tool item: {ex}")
            fallback_item = QStandardItem(f"{index + 1}. ❓ Unknown Tool")
            fallback_item.setEditable(False)
            return fallback_item
        # Determine tool display info
        if isinstance(tool, dict):
            tool_name = tool.get('display_name', tool.get('name', f"Tool #{index+1}"))
            tool_id = tool.get('tool_id', index+1)
            
            if 'model_name' in tool:
                # DetectTool
                model_name = tool.get('model_name', 'Unknown')
                display_text = f"🔍 Detect ({model_name}) #{tool_id}"
                icon = "🔍"
            elif tool_name and str(tool_name).lower() == "camera source":
                display_text = f"📷 Camera Source #{tool_id}"
                icon = "📷"
            else:
                display_text = f"⚙️ {tool_name} #{tool_id}"
                icon = "⚙️"
        else:
            # Object tool
            tool_name = getattr(tool, 'display_name', 
                              getattr(tool, 'name', f"Tool #{index+1}"))
            tool_id = getattr(tool, 'tool_id', index+1)
            
            if tool_name and str(tool_name).lower() == "camera source":
                display_text = f"📷 Camera Source #{tool_id}"
                icon = "📷"
            elif hasattr(tool, 'display_name') and tool.display_name:
                display_text = f"🔧 {tool.display_name} #{tool_id}"
                icon = "🔧"
            else:
                display_text = f"⚙️ Tool #{tool_id}"
                icon = "⚙️"
        
        tool_item = QStandardItem(display_text)
        tool_item.setEditable(False)
        tool_item.setData(tool, role=256)  # Store tool reference
        
        # Add visual styling based on tool type
        if isinstance(tool, dict) and 'model_name' in tool:
            # DetectTool - blue color
            tool_item.setForeground(QBrush(QColor(70, 130, 180)))
        elif icon == "📷":
            # Camera Source - green color
            tool_item.setForeground(QBrush(QColor(34, 139, 34)))
        
        return tool_item
        
    def get_selected_tool_index(self):
        """Get the index of the currently selected tool"""
        indexes = self.selectedIndexes()
        if indexes and indexes[0].parent().isValid():
            return indexes[0].row()
        return -1
        
    def select_tool(self, tool_index):
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
            
    def move_tool(self, from_index, to_index):
        """Move tool from one position to another"""
        model = self.model()
        if not isinstance(model, QStandardItemModel) or model.rowCount() == 0:
            return False
            
        job_item = model.item(0)
        if not job_item or from_index >= job_item.rowCount() or to_index >= job_item.rowCount():
            return False
            
        # Get the tool item to move
        tool_item = job_item.takeChild(from_index)
        if not tool_item:
            return False
            
        # Insert at new position
        job_item.insertRow(to_index, tool_item)
        
        # Update viewport
        try:
            viewport = self.viewport()
            if viewport:
                viewport.update()
        except Exception as ex:
            print(f"DEBUG: Viewport update error: {ex}")
            pass
            
        return True
    
    # Connection Management Methods
    def add_connection(self, source_tool_index, target_tool_index):
        """Add a connection between two tools"""
        if source_tool_index not in self.tool_connections:
            self.tool_connections[source_tool_index] = []
        
        if target_tool_index not in self.tool_connections[source_tool_index]:
            self.tool_connections[source_tool_index].append(target_tool_index)
            self.tool_connected.emit(source_tool_index, target_tool_index)
            print(f"DEBUG: Added connection from tool {source_tool_index} to tool {target_tool_index}")
            
            # Update viewport to redraw connections
            self.viewport().update()
            return True
        return False
    
    def remove_connection(self, source_tool_index, target_tool_index):
        """Remove a connection between two tools"""
        if (source_tool_index in self.tool_connections and 
            target_tool_index in self.tool_connections[source_tool_index]):
            
            self.tool_connections[source_tool_index].remove(target_tool_index)
            if not self.tool_connections[source_tool_index]:
                del self.tool_connections[source_tool_index]
            
            self.tool_disconnected.emit(source_tool_index, target_tool_index)
            print(f"DEBUG: Removed connection from tool {source_tool_index} to tool {target_tool_index}")
            
            # Update viewport to redraw connections
            self.viewport().update()
            return True
        return False
    
    def get_connections(self):
        """Get all current connections"""
        return dict(self.tool_connections)
    
    def clear_all_connections(self):
        """Clear all connections"""
        self.tool_connections.clear()
        self.viewport().update()
        print("DEBUG: Cleared all connections")
    
    def get_tool_rect_with_ports(self, tool_index):
        """Get tool rectangle with input/output port positions"""
        model = self.model()
        if not isinstance(model, QStandardItemModel) or model.rowCount() == 0:
            return None
            
        job_item = model.item(0)
        if not job_item or tool_index >= job_item.rowCount():
            return None
            
        tool_item = job_item.child(tool_index)
        if not tool_item:
            return None
            
        tool_model_index = model.indexFromItem(tool_item)
        tool_rect = self.visualRect(tool_model_index)
        
        # Calculate port positions
        input_port = QPoint(tool_rect.left() - self.port_size // 2, tool_rect.center().y())
        output_port = QPoint(tool_rect.right() + self.port_size // 2, tool_rect.center().y())
        
        return {
            'rect': tool_rect,
            'input_port': input_port,
            'output_port': output_port,
            'tool_type': self.get_tool_type(tool_item.text())
        }
    
    def get_port_at_position(self, pos):
        """Get the port (input/output) at the given position"""
        model = self.model()
        if not isinstance(model, QStandardItemModel) or model.rowCount() == 0:
            return None
            
        job_item = model.item(0)
        if not job_item:
            return None
            
        for i in range(job_item.rowCount()):
            tool_info = self.get_tool_rect_with_ports(i)
            if not tool_info:
                continue
                
            # Check if click is near input port
            input_distance = (pos - tool_info['input_port']).manhattanLength()
            if input_distance <= self.port_size:
                return {'tool_index': i, 'port_type': 'input'}
                
            # Check if click is near output port
            output_distance = (pos - tool_info['output_port']).manhattanLength()
            if output_distance <= self.port_size:
                return {'tool_index': i, 'port_type': 'output'}
                
        return None
    
    def draw_tool_ports(self, painter, model):
        """Draw input/output ports on each tool (Cognex Vision Pro style)"""
        if model.rowCount() == 0:
            return
            
        job_item = model.item(0)
        if not job_item:
            return
            
        for i in range(job_item.rowCount()):
            tool_info = self.get_tool_rect_with_ports(i)
            if not tool_info:
                continue
                
            tool_type = tool_info['tool_type']
            
            # Draw input port (left side) - not for source tools
            if tool_type != 'source':
                self.draw_port(painter, tool_info['input_port'], 'input', tool_type)
                
            # Draw output port (right side) - for all tools
            self.draw_port(painter, tool_info['output_port'], 'output', tool_type)
    
    def draw_port(self, painter, port_pos, port_type, tool_type):
        """Draw a single input or output port"""
        # Port colors based on type
        if port_type == 'input':
            port_color = QColor(0, 120, 215)  # Blue for input
        else:
            port_color = QColor(0, 150, 0)    # Green for output
            
        # Draw port circle
        painter.setBrush(QBrush(port_color))
        painter.setPen(QPen(QColor(0, 0, 0), 1))  # Black border
        
        port_rect = port_pos - QPoint(self.port_size//2, self.port_size//2)
        painter.drawEllipse(port_rect.x(), port_rect.y(), self.port_size, self.port_size)
    
    def draw_tool_connections(self, painter, model):
        """Draw all connections between tools based on connection graph"""
        if not self.tool_connections:
            return
            
        for source_index, target_indices in self.tool_connections.items():
            source_info = self.get_tool_rect_with_ports(source_index)
            if not source_info:
                continue
                
            for target_index in target_indices:
                target_info = self.get_tool_rect_with_ports(target_index)
                if not target_info:
                    continue
                    
                # Draw connection arrow from source output to target input
                self.draw_connection_arrow(
                    painter, 
                    source_info['output_port'], 
                    target_info['input_port'],
                    source_index,
                    target_index
                )
    
    def draw_connection_arrow(self, painter, start_port, end_port, source_idx, target_idx):
        """Draw a curved arrow connection between two ports"""
        # Connection colors based on tool types
        connection_colors = [
            QColor(255, 100, 100),  # Red
            QColor(100, 255, 100),  # Green  
            QColor(100, 100, 255),  # Blue
            QColor(255, 255, 100),  # Yellow
            QColor(255, 100, 255),  # Magenta
            QColor(100, 255, 255),  # Cyan
        ]
        
        color_index = (source_idx + target_idx) % len(connection_colors)
        arrow_color = connection_colors[color_index]
        
        painter.setPen(QPen(arrow_color, 2))
        
        # Calculate control points for smooth curve
        control_offset = 50
        
        # Control points for bezier curve
        ctrl1 = QPoint(start_port.x() + control_offset, start_port.y())
        ctrl2 = QPoint(end_port.x() - control_offset, end_port.y())
        
        # Draw the curve using multiple line segments
        segments = 20
        prev_point = start_port
        
        for i in range(1, segments + 1):
            t = i / segments
            point = self.bezier_point_simple(start_port, ctrl1, ctrl2, end_port, t)
            painter.drawLine(prev_point, point)
            prev_point = point
        
        # Draw arrowhead at end point
        self.draw_connection_arrowhead(painter, end_port, start_port, arrow_color)
    
    def draw_connection_arrowhead(self, painter, end_point, start_point, color):
        """Draw arrowhead for connection pointing into target port"""
        arrow_size = 6
        
        # Calculate arrow direction
        dx = end_point.x() - start_point.x()
        dy = end_point.y() - start_point.y()
        length = math.sqrt(dx*dx + dy*dy)
        
        if length == 0:
            return
            
        # Normalize direction
        dx /= length
        dy /= length
        
        # Calculate arrowhead points
        p1 = QPoint(
            int(end_point.x() - arrow_size * dx + arrow_size * dy * 0.5),
            int(end_point.y() - arrow_size * dy - arrow_size * dx * 0.5)
        )
        p2 = QPoint(
            int(end_point.x() - arrow_size * dx - arrow_size * dy * 0.5),
            int(end_point.y() - arrow_size * dy + arrow_size * dx * 0.5)
        )
        
        # Draw filled arrowhead
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color, 1))
        painter.drawPolygon([end_point, p1, p2])
    
    def draw_temp_connection(self, painter):
        """Draw temporary connection line during dragging"""
        if not hasattr(self, 'temp_connection_end') or not self.drag_start_position:
            return
            
        # Draw temporary connection line
        painter.setPen(QPen(QColor(255, 0, 0, 128), 2))  # Semi-transparent red
        painter.drawLine(self.drag_start_position, self.temp_connection_end)
    
    # Demo and Test Methods
    def create_demo_connections(self):
        """Create demo connections for testing visibility"""
        print("DEBUG: Creating demo connections for testing...")
        
        model = self.model()
        if not isinstance(model, QStandardItemModel) or model.rowCount() == 0:
            print("DEBUG: No model available for demo connections")
            return
            
        job_item = model.item(0)
        if not job_item or job_item.rowCount() < 2:
            print("DEBUG: Need at least 2 tools for demo connections")
            return
        
        # Clear existing connections
        self.tool_connections.clear()
        
        # Find tools by type
        source_tools = []
        detect_tools = []
        other_tools = []
        
        for i in range(job_item.rowCount()):
            tool_item = job_item.child(i)
            if tool_item:
                tool_type = self.get_tool_type(tool_item.text())
                if tool_type == 'source':
                    source_tools.append(i)
                elif tool_type == 'detect':
                    detect_tools.append(i)
                else:
                    other_tools.append(i)
        
        print(f"DEBUG: Found {len(source_tools)} source, {len(detect_tools)} detect, {len(other_tools)} other tools")
        
        # Create parallel connections: camera source -> multiple detect tools
        if source_tools and detect_tools:
            source_idx = source_tools[0]
            for detect_idx in detect_tools:
                self.add_connection(source_idx, detect_idx)
                print(f"DEBUG: Demo connection added: {source_idx} -> {detect_idx}")
        
        # If no specific types, create sequential connections
        elif job_item.rowCount() >= 2:
            for i in range(job_item.rowCount() - 1):
                self.add_connection(i, i + 1)
                print(f"DEBUG: Sequential demo connection added: {i} -> {i + 1}")
        
        # Force repaint
        self.viewport().update()
        print(f"DEBUG: Demo connections created. Total connections: {len(self.tool_connections)}")
    
    def toggle_parallel_sequential(self):
        """Toggle between parallel and sequential workflow modes"""
        model = self.model()
        if not isinstance(model, QStandardItemModel) or model.rowCount() == 0:
            return
            
        job_item = model.item(0)
        if not job_item or job_item.rowCount() < 2:
            return
        
        # Clear existing connections
        self.tool_connections.clear()
        
        # Check current mode by looking at connections
        has_parallel = False
        for source_idx, targets in self.tool_connections.items():
            if len(targets) > 1:
                has_parallel = True
                break
        
        # Find tools
        source_tools = []
        detect_tools = []
        all_tools = []
        
        for i in range(job_item.rowCount()):
            tool_item = job_item.child(i)
            if tool_item:
                all_tools.append(i)
                tool_type = self.get_tool_type(tool_item.text())
                if tool_type == 'source':
                    source_tools.append(i)
                elif tool_type == 'detect':
                    detect_tools.append(i)
        
        if not has_parallel:
            # Switch to parallel: camera source -> multiple detect tools
            print("DEBUG: Switching to PARALLEL mode")
            if source_tools and len(detect_tools) >= 2:
                source_idx = source_tools[0]
                for detect_idx in detect_tools:
                    self.add_connection(source_idx, detect_idx)
                    print(f"DEBUG: Parallel connection: {source_idx} -> {detect_idx}")
            else:
                print("DEBUG: Need camera source and 2+ detect tools for parallel mode")
        else:
            # Switch to sequential: tool1 -> tool2 -> tool3...
            print("DEBUG: Switching to SEQUENTIAL mode")
            for i in range(len(all_tools) - 1):
                self.add_connection(all_tools[i], all_tools[i + 1])
                print(f"DEBUG: Sequential connection: {all_tools[i]} -> {all_tools[i + 1]}")
        
        # Force repaint
        self.viewport().update()
        print(f"DEBUG: Workflow mode switched. Total connections: {len(self.tool_connections)}")
    
    def print_debug_info(self):
        """Print debug information about current state"""
        print("\n=== JobTreeView Debug Info ===")
        print(f"Demo mode: {self.demo_mode}")
        print(f"Port size: {self.port_size}")
        print(f"Current connections: {self.tool_connections}")
        
        model = self.model()
        if isinstance(model, QStandardItemModel) and model.rowCount() > 0:
            job_item = model.item(0)
            if job_item:
                print(f"Tools in job: {job_item.rowCount()}")
                for i in range(job_item.rowCount()):
                    tool_item = job_item.child(i)
                    if tool_item:
                        tool_type = self.get_tool_type(tool_item.text())
                        print(f"  Tool {i}: {tool_item.text()} (type: {tool_type})")
        
        print("==============================\n")
