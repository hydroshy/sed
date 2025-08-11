"""
Module hiển thị biểu đồ workflow với các mũi tên kết nối giữa các công cụ,
tương tự như giao diện Cognex Vision Pro
"""

from PyQt5.QtWidgets import (QGraphicsScene, QGraphicsView, QGraphicsItem, 
                            QGraphicsLineItem, QGraphicsRectItem, QGraphicsTextItem,
                            QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QDialog)
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal, QTimer
from PyQt5.QtGui import QPen, QBrush, QColor, QFont, QPainterPath, QPainter, QPolygonF

import logging
logger = logging.getLogger(__name__)

class ToolNode(QGraphicsRectItem):
    """Đại diện cho một công cụ trong luồng công việc"""
    
    def __init__(self, tool_id, name, x, y, width=120, height=60):
        super().__init__(0, 0, width, height)
        self.tool_id = tool_id
        self.name = name
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        
        # Tạo hiệu ứng tương tác và ngoại hình
        self.setPen(QPen(QColor(70, 70, 70), 2))
        self.setBrush(QBrush(QColor(220, 220, 220)))
        
        # Thêm văn bản vào node
        self.text = QGraphicsTextItem(name, self)
        self.text.setPos(10, 20)
        self.text.setFont(QFont("Arial", 9))
        
        # Điểm kết nối đầu vào/đầu ra
        self.input_points = []
        self.output_points = []
        
        # Thêm điểm kết nối mặc định
        self.add_input_point(0, height / 2)
        self.add_output_point(width, height / 2)
        
    def add_input_point(self, x_rel, y_rel):
        """Thêm điểm kết nối đầu vào"""
        self.input_points.append((x_rel, y_rel))
        
    def add_output_point(self, x_rel, y_rel):
        """Thêm điểm kết nối đầu ra"""
        self.output_points.append((x_rel, y_rel))
        
    def get_input_pos(self, index=0):
        """Lấy vị trí tuyệt đối của điểm đầu vào"""
        if index < len(self.input_points):
            x_rel, y_rel = self.input_points[index]
            return self.pos() + QPointF(x_rel, y_rel)
        return self.pos() + QPointF(0, self.rect().height() / 2)
    
    def get_output_pos(self, index=0):
        """Lấy vị trí tuyệt đối của điểm đầu ra"""
        if index < len(self.output_points):
            x_rel, y_rel = self.output_points[index]
            return self.pos() + QPointF(x_rel, y_rel)
        return self.pos() + QPointF(self.rect().width(), self.rect().height() / 2)
        
    def itemChange(self, change, value):
        """Xử lý khi node thay đổi (ví dụ: di chuyển)"""
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            # Thông báo cho scene cập nhật lại tất cả các kết nối
            QTimer.singleShot(0, self.scene().update_all_connections)
        return super().itemChange(change, value)


class ConnectionArrow(QGraphicsLineItem):
    """Mũi tên kết nối giữa các công cụ"""
    
    def __init__(self, source_node, target_node, source_index=0, target_index=0, is_primary=False):
        super().__init__()
        self.source_node = source_node
        self.target_node = target_node
        self.source_index = source_index
        self.target_index = target_index
        self.is_primary = is_primary
        
        # Thiết lập kiểu đường dựa vào loại kết nối
        if is_primary:
            self.setPen(QPen(QColor(50, 100, 200), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        else:
            self.setPen(QPen(QColor(100, 150, 200), 1.5, Qt.DashLine, Qt.RoundCap, Qt.RoundJoin))
        
        # Tạo đường và mũi tên
        self.arrow_head = None
        self.update_position()
        
    def update_position(self):
        """Cập nhật vị trí đường kết nối và mũi tên"""
        start_pos = self.source_node.get_output_pos(self.source_index)
        end_pos = self.target_node.get_input_pos(self.target_index)
        
        # Tạo đường cong thay vì đường thẳng
        path = QPainterPath()
        path.moveTo(start_pos)
        
        # Tính điểm kiểm soát cho đường cong Bezier
        dx = end_pos.x() - start_pos.x()
        control_x = start_pos.x() + dx * 0.5
        
        # Tạo đường cong
        path.cubicTo(
            QPointF(control_x, start_pos.y()),  # điểm kiểm soát 1
            QPointF(control_x, end_pos.y()),    # điểm kiểm soát 2
            end_pos                            # điểm cuối
        )
        
        # Vẽ đường
        self.setLine(start_pos.x(), start_pos.y(), end_pos.x(), end_pos.y())
        
        # Tạo mũi tên
        self.arrow_head = self._create_arrow_head(start_pos, end_pos)
        
    def _create_arrow_head(self, start_pos, end_pos):
        """Tạo mũi tên ở cuối đường kết nối"""
        arrow_size = 10.0
        
        # Tính vector hướng của đường
        dx = end_pos.x() - start_pos.x()
        dy = end_pos.y() - start_pos.y()
        line_length = (dx**2 + dy**2)**0.5
        
        if line_length == 0:
            return QPolygonF()
            
        # Chuẩn hóa vector
        dx /= line_length
        dy /= line_length
        
        # Tính các điểm cho mũi tên
        arrow_p1 = QPointF(end_pos.x() - arrow_size * dx - arrow_size * 0.5 * dy, 
                         end_pos.y() - arrow_size * dy + arrow_size * 0.5 * dx)
        arrow_p2 = QPointF(end_pos.x() - arrow_size * dx + arrow_size * 0.5 * dy, 
                         end_pos.y() - arrow_size * dy - arrow_size * 0.5 * dx)
        
        # Tạo đa giác mũi tên
        polygon = QPolygonF()
        polygon.append(end_pos)
        polygon.append(arrow_p1)
        polygon.append(arrow_p2)
        
        return polygon
        
    def paint(self, painter, option, widget):
        """Vẽ đường kết nối và mũi tên"""
        super().paint(painter, option, widget)
        
        # Vẽ mũi tên
        if self.arrow_head:
            painter.setPen(self.pen())
            painter.setBrush(QBrush(self.pen().color()))
            painter.drawPolygon(self.arrow_head)


class WorkflowScene(QGraphicsScene):
    """Scene chứa và quản lý các node và kết nối workflow"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes = {}  # tool_id -> node
        self.connections = []  # danh sách các kết nối
        
    def update_all_connections(self):
        """Cập nhật vị trí tất cả các kết nối"""
        for connection in self.connections:
            connection.update_position()
        self.update()


class WorkflowView(QGraphicsView):
    """Widget hiển thị luồng công việc với các nút và kết nối"""
    
    node_clicked = pyqtSignal(int)  # Phát ra tool_id khi node được click
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.workflow_scene = WorkflowScene(self)
        self.setScene(self.workflow_scene)
        
        # Cấu hình view
        self.setRenderHint(QPainter.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Thiết lập background
        self.setBackgroundBrush(QBrush(QColor(240, 240, 240)))
        
    def build_workflow_from_job(self, job):
        """Xây dựng biểu đồ từ Job hiện tại"""
        # Xóa scene hiện tại
        self.workflow_scene.clear()
        self.workflow_scene.nodes = {}
        self.workflow_scene.connections = []
        
        if not job:
            return
            
        # Lấy cấu trúc workflow từ job
        workflow = job.get_workflow_structure()
        if not workflow:
            return
            
        # Sắp xếp tools theo cấp độ (level) dựa trên dependencies
        levels = self._arrange_tools_by_level(job.tools)
        
        # Thêm các node
        x_pos = 50
        level_width = 200
        
        for level, tools in enumerate(levels):
            y_pos = 50
            y_step = 100
            
            for tool in tools:
                # Tạo node
                node = self._add_node(tool.tool_id, tool.display_name, x_pos, y_pos)
                y_pos += y_step
                
            x_pos += level_width
        
        # Thêm các kết nối
        for tool in job.tools:
            source_node = self.workflow_scene.nodes.get(tool.tool_id)
            if not source_node:
                continue
                
            for output_tool in tool.outputs:
                target_node = self.workflow_scene.nodes.get(output_tool.tool_id)
                if target_node:
                    is_primary = output_tool.source_tool == tool
                    self._add_connection(source_node, target_node, is_primary=is_primary)
        
        # Tự động điều chỉnh view để hiển thị toàn bộ đồ thị
        self.fitInView(self.workflow_scene.itemsBoundingRect().adjusted(-50, -50, 50, 50), Qt.KeepAspectRatio)
    
    def _arrange_tools_by_level(self, tools):
        """Sắp xếp các công cụ theo cấp độ dựa trên dependencies"""
        levels = []
        processed = set()
        
        # Bắt đầu với các công cụ không có input
        current_level = [tool for tool in tools if not tool.inputs]
        
        while current_level:
            levels.append(current_level)
            
            # Đánh dấu các công cụ đã xử lý
            for tool in current_level:
                processed.add(tool.tool_id)
                
            # Tìm công cụ tiếp theo có thể được xử lý
            next_level = []
            for tool in tools:
                if tool.tool_id in processed:
                    continue
                    
                # Kiểm tra xem tất cả các input đã được xử lý chưa
                if all(input_tool.tool_id in processed for input_tool in tool.inputs):
                    next_level.append(tool)
                    
            current_level = next_level
            
        # Kiểm tra công cụ chưa được xử lý (có thể do vòng lặp)
        remaining = [tool for tool in tools if tool.tool_id not in processed]
        if remaining:
            levels.append(remaining)
            
        return levels
            
    def _add_node(self, tool_id, name, x, y):
        """Thêm một node mới vào biểu đồ"""
        node = ToolNode(tool_id, name, x, y)
        self.workflow_scene.addItem(node)
        self.workflow_scene.nodes[tool_id] = node
        return node
        
    def _add_connection(self, source_node, target_node, source_index=0, target_index=0, is_primary=False):
        """Thêm kết nối giữa hai node"""
        connection = ConnectionArrow(source_node, target_node, source_index, target_index, is_primary)
        self.workflow_scene.addItem(connection)
        self.workflow_scene.connections.append(connection)
        return connection
        
    def wheelEvent(self, event):
        """Xử lý sự kiện cuộn chuột để zoom in/out"""
        zoom_factor = 1.15
        
        if event.angleDelta().y() > 0:
            # Zoom in
            self.scale(zoom_factor, zoom_factor)
        else:
            # Zoom out
            self.scale(1.0 / zoom_factor, 1.0 / zoom_factor)
            
    def mousePressEvent(self, event):
        """Xử lý sự kiện nhấn chuột"""
        if event.button() == Qt.LeftButton:
            # Lấy item dưới chuột
            item = self.itemAt(event.pos())
            
            # Kiểm tra xem có phải là ToolNode không
            if isinstance(item, ToolNode):
                self.node_clicked.emit(item.tool_id)
                
        super().mousePressEvent(event)


class WorkflowWidget(QWidget):
    """Widget tổng hợp hiển thị workflow với các điều khiển"""
    
    node_selected = pyqtSignal(int)  # Phát ra tool_id khi node được chọn
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_job = None
        self._setup_ui()
        
    def _setup_ui(self):
        """Thiết lập giao diện người dùng"""
        # Layout chính
        main_layout = QVBoxLayout(self)
        
        # Thêm các nút điều khiển
        top_control_layout = QHBoxLayout()
        
        self.connect_tools_button = QPushButton("Connect Tools")
        self.disconnect_tools_button = QPushButton("Disconnect Tools")
        self.auto_layout_button = QPushButton("Auto Layout")
        
        top_control_layout.addWidget(self.connect_tools_button)
        top_control_layout.addWidget(self.disconnect_tools_button)
        top_control_layout.addWidget(self.auto_layout_button)
        top_control_layout.addStretch(1)
        
        main_layout.addLayout(top_control_layout)
        
        # Thêm view workflow
        self.workflow_view = WorkflowView(self)
        main_layout.addWidget(self.workflow_view)
        
        # Thêm các nút điều khiển zoom
        bottom_control_layout = QHBoxLayout()
        
        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_out_button = QPushButton("Zoom Out")
        self.fit_view_button = QPushButton("Fit View")
        
        bottom_control_layout.addWidget(self.zoom_in_button)
        bottom_control_layout.addWidget(self.zoom_out_button)
        bottom_control_layout.addWidget(self.fit_view_button)
        bottom_control_layout.addStretch(1)
        
        main_layout.addLayout(bottom_control_layout)
        
        # Kết nối các sự kiện
        self.zoom_in_button.clicked.connect(self._on_zoom_in)
        self.zoom_out_button.clicked.connect(self._on_zoom_out)
        self.fit_view_button.clicked.connect(self._on_fit_view)
        self.workflow_view.node_clicked.connect(self.node_selected)
        self.connect_tools_button.clicked.connect(self._on_connect_tools)
        self.disconnect_tools_button.clicked.connect(self._on_disconnect_tools)
        self.auto_layout_button.clicked.connect(self._on_auto_layout)
        
    def build_workflow_from_job(self, job):
        """Xây dựng biểu đồ từ Job hiện tại"""
        self.current_job = job
        self.workflow_view.build_workflow_from_job(job)
        
        # Cập nhật trạng thái các nút điều khiển
        has_job = job is not None and len(job.tools) > 0
        self.connect_tools_button.setEnabled(has_job)
        self.disconnect_tools_button.setEnabled(has_job)
        self.auto_layout_button.setEnabled(has_job)
        
    def _on_zoom_in(self):
        """Xử lý sự kiện nút Zoom In"""
        self.workflow_view.scale(1.2, 1.2)
        
    def _on_zoom_out(self):
        """Xử lý sự kiện nút Zoom Out"""
        self.workflow_view.scale(1/1.2, 1/1.2)
        
    def _on_fit_view(self):
        """Xử lý sự kiện nút Fit View"""
        self.workflow_view.fitInView(
            self.workflow_view.workflow_scene.itemsBoundingRect().adjusted(-50, -50, 50, 50),
            Qt.KeepAspectRatio
        )
        
    def _on_connect_tools(self):
        """Xử lý sự kiện nút Connect Tools"""
        if not self.current_job:
            return
            
        from gui.connection_dialog import ConnectToolsDialog
        dialog = ConnectToolsDialog(self.current_job, self)
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_result()
            if result:
                source_tool, target_tool, is_primary = result
                
                # Thực hiện kết nối
                if is_primary:
                    self.current_job.set_tool_as_source(source_tool.tool_id, target_tool.tool_id)
                else:
                    self.current_job.connect_tools(source_tool.tool_id, target_tool.tool_id)
                    
                # Cập nhật view
                self.workflow_view.build_workflow_from_job(self.current_job)
                logger.info(f"Connected: {source_tool.display_name} -> {target_tool.display_name}")
        
    def _on_disconnect_tools(self):
        """Xử lý sự kiện nút Disconnect Tools"""
        if not self.current_job:
            return
            
        from gui.connection_dialog import DisconnectToolsDialog
        dialog = DisconnectToolsDialog(self.current_job, self)
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_result()
            if result:
                source_tool, target_tool = result
                
                # Thực hiện ngắt kết nối
                self.current_job.disconnect_tools(source_tool.tool_id, target_tool.tool_id)
                
                # Cập nhật view
                self.workflow_view.build_workflow_from_job(self.current_job)
                logger.info(f"Disconnected: {source_tool.display_name} -> {target_tool.display_name}")
                
    def _on_auto_layout(self):
        """Tự động sắp xếp lại các node trong workflow"""
        if not self.current_job:
            return
            
        # Sắp xếp lại và cập nhật view
        self.workflow_view.build_workflow_from_job(self.current_job)
        self._on_fit_view()
