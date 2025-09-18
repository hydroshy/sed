from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QObject
from PyQt5.QtGui import QPen, QBrush, QColor, QPainter
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsItem, QGraphicsEllipseItem


class DetectionAreaOverlay(QGraphicsRectItem):
    def mousePressEvent(self, event):
        if not self.edit_mode:
            event.ignore()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.edit_mode:
            event.ignore()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if not self.edit_mode:
            event.ignore()
            return
        super().mouseReleaseEvent(event)
    """
    Overlay để hiển thị và chỉnh sửa detection area
    Chỉ có thể tương tác khi ở edit mode
    """
    
    # Class variable để track ID
    _next_id = 1
    
    def __init__(self, rect, tool_id=None, camera_view=None, parent=None):
        super().__init__(rect, parent)
        
        # Tool ID
        if tool_id is None:
            self.tool_id = DetectionAreaOverlay._next_id
            DetectionAreaOverlay._next_id += 1
        else:
            self.tool_id = tool_id
            
        # Camera view reference for signals
        self.camera_view = camera_view
            
        # Trạng thái
        self.edit_mode = False  # Chỉ có thể tương tác khi edit_mode = True
        self.handles = []
        self.handle_size = 8
        self.selected_handle = None
        self.is_resizing = False
        
        # Style mặc định
        self._setup_style()
        
        # Tạo handles
        self._create_handles()
        
        # Mặc định không thể tương tác
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        
    def _setup_style(self):
        """Thiết lập style cho overlay"""
        # Khung màu đỏ, fill trong suốt
        pen = QPen(QColor(255, 0, 0), 2)
        brush = QBrush(QColor(255, 0, 0, 30))  # Màu đỏ nhạt trong suốt
        self.setPen(pen)
        self.setBrush(brush)
        
        # Z-value cao để hiển thị trên top
        self.setZValue(10)
        
    def paint(self, painter, option, widget):
        """Override paint để vẽ ID lên overlay"""
        # Vẽ rectangle bình thường
        super().paint(painter, option, widget)
        
        # Vẽ ID text
        rect = self.rect()
        painter.setPen(QPen(QColor(255, 255, 255), 1))  # Chữ trắng
        painter.setFont(painter.font())
        font = painter.font()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        
        # Vẽ ID ở góc trên trái
        id_text = f"#{self.tool_id}"
        text_rect = rect.adjusted(5, 5, -5, -5)  # Padding 5px
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, id_text)
        
    def set_edit_mode(self, enabled):
        """Bật/tắt edit mode"""
        self.edit_mode = enabled
        
        if enabled:
            # Cho phép tương tác
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
            
            # Hiển thị handles
            self._show_handles(True)
            
            # Style khi edit (khung dày hơn)
            pen = QPen(QColor(255, 0, 0), 3)
            brush = QBrush(QColor(255, 0, 0, 50))
            self.setPen(pen)
            self.setBrush(brush)
            
        else:
            # Tắt tương tác với error handling
            try:
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, False)
                
                # Ẩn handles
                self._show_handles(False)
                
                # Style khi không edit (khung mỏng hơn)
                pen = QPen(QColor(255, 0, 0), 2)
                brush = QBrush(QColor(255, 0, 0, 20))
                self.setPen(pen)
                self.setBrush(brush)
            except RuntimeError as e:
                print(f"DEBUG: DetectionAreaOverlay already deleted: {e}")
                return  # Object đã bị delete, không thể thao tác
            
        print(f"DEBUG: DetectionAreaOverlay edit mode: {enabled}")
        
    def _create_handles(self):
        """Tạo các handle để resize"""
        self.handles.clear()
        
        # 8 handles: 4 góc + 4 cạnh
        handle_positions = [
            'top-left', 'top-center', 'top-right',
            'middle-left', 'middle-right',
            'bottom-left', 'bottom-center', 'bottom-right'
        ]
        
        for pos in handle_positions:
            handle = ResizeHandle(self.handle_size, pos, self)
            self.handles.append(handle)
            
        self._update_handle_positions()
        
    def _update_handle_positions(self):
        """Cập nhật vị trí các handle"""
        rect = self.rect()
        
        positions = {
            'top-left': (rect.left(), rect.top()),
            'top-center': (rect.center().x(), rect.top()),
            'top-right': (rect.right(), rect.top()),
            'middle-left': (rect.left(), rect.center().y()),
            'middle-right': (rect.right(), rect.center().y()),
            'bottom-left': (rect.left(), rect.bottom()),
            'bottom-center': (rect.center().x(), rect.bottom()),
            'bottom-right': (rect.right(), rect.bottom())
        }
        
        for handle in self.handles:
            pos = positions[handle.position]
            handle.setPos(pos[0] - self.handle_size/2, pos[1] - self.handle_size/2)
            
    def _show_handles(self, visible):
        """Hiển thị/ẩn handles"""
        for handle in self.handles:
            handle.setVisible(visible and self.edit_mode)
            
    def setRect(self, rect):
        """Override setRect để cập nhật handles"""
        super().setRect(rect)
        self._update_handle_positions()
        
    def itemChange(self, change, value):
        """Override để handle thay đổi"""
        if not self.edit_mode:
            # Không cho phép thay đổi nếu không ở edit mode
            return super().itemChange(change, value)
            
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._update_handle_positions()
            self._notify_change()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._show_handles(value and self.edit_mode)
            
        return super().itemChange(change, value)
        
    def _notify_change(self):
        """Thông báo khi area thay đổi"""
        try:
            if self.camera_view and hasattr(self.camera_view, 'area_changed'):
                coords = self.get_area_coords()
                print(f"DEBUG: DetectionAreaOverlay notifying change: {coords}")
                self.camera_view.area_changed.emit(*coords)
        except Exception as e:
            print(f"DEBUG: Error in _notify_change: {e}")
            
    def get_area_coords(self):
        """Lấy tọa độ area (x1, y1, x2, y2)"""
        rect = self.rect()
        pos = self.pos()
        
        x1 = pos.x() + rect.left()
        y1 = pos.y() + rect.top()
        x2 = pos.x() + rect.right()
        y2 = pos.y() + rect.bottom()
        
        return (int(x1), int(y1), int(x2), int(y2))
        
    def update_from_coords(self, x1, y1, x2, y2):
        """Cập nhật area từ tọa độ"""
        # Đảm bảo x1 < x2 và y1 < y2
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        
        rect = QRectF(x1, y1, x2-x1, y2-y1)
        self.setPos(0, 0)  # Reset position
        self.setRect(rect)
        print(f"DEBUG: DetectionAreaOverlay updated to: ({x1}, {y1}) to ({x2}, {y2})")


class ResizeHandle(QGraphicsEllipseItem):
    """Handle để resize overlay"""
    
    def __init__(self, size, position, parent_item):
        super().__init__(0, 0, size, size)
        
        self.position = position
        self.parent_overlay = parent_item
        self.setParentItem(parent_item)
        
        # Style handle
        pen = QPen(QColor(255, 0, 0), 1)
        brush = QBrush(QColor(255, 255, 255))
        self.setPen(pen)
        self.setBrush(brush)
        
        # Thiết lập flags - chỉ movable khi parent ở edit mode
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        
        # Cursor cho resize
        self._set_cursor()
        
        # Mặc định ẩn
        self.setVisible(False)
        
    def _set_cursor(self):
        """Thiết lập cursor tương ứng với vị trí handle"""
        cursor_map = {
            'top-left': Qt.CursorShape.SizeFDiagCursor,
            'top-center': Qt.CursorShape.SizeVerCursor,
            'top-right': Qt.CursorShape.SizeBDiagCursor,
            'middle-left': Qt.CursorShape.SizeHorCursor,
            'middle-right': Qt.CursorShape.SizeHorCursor,
            'bottom-left': Qt.CursorShape.SizeBDiagCursor,
            'bottom-center': Qt.CursorShape.SizeVerCursor,
            'bottom-right': Qt.CursorShape.SizeFDiagCursor
        }
        
        self.setCursor(cursor_map.get(self.position, Qt.CursorShape.ArrowCursor))
        
    def itemChange(self, change, value):
        """Handle resize khi di chuyển handle"""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self.parent_overlay:
            if self.parent_overlay.edit_mode:  # Chỉ resize khi edit mode
                self._resize_parent_overlay(value)
                
        return super().itemChange(change, value)
        
    def _resize_parent_overlay(self, new_pos):
        """Resize parent overlay dựa trên vị trí handle mới"""
        rect = self.parent_overlay.rect()
        handle_size = self.rect().width()
        
        # Tính toán vị trí handle center
        handle_center_x = new_pos.x() + handle_size / 2
        handle_center_y = new_pos.y() + handle_size / 2
        
        # Cập nhật rectangle dựa trên position
        if self.position == 'top-left':
            rect.setTopLeft(QRectF(handle_center_x, handle_center_y, 0, 0).topLeft())
        elif self.position == 'top-center':
            rect.setTop(handle_center_y)
        elif self.position == 'top-right':
            rect.setTopRight(QRectF(handle_center_x, handle_center_y, 0, 0).topRight())
        elif self.position == 'middle-left':
            rect.setLeft(handle_center_x)
        elif self.position == 'middle-right':
            rect.setRight(handle_center_x)
        elif self.position == 'bottom-left':
            rect.setBottomLeft(QRectF(handle_center_x, handle_center_y, 0, 0).bottomLeft())
        elif self.position == 'bottom-center':
            rect.setBottom(handle_center_y)
        elif self.position == 'bottom-right':
            rect.setBottomRight(QRectF(handle_center_x, handle_center_y, 0, 0).bottomRight())
        
        # Đảm bảo rectangle có kích thước tối thiểu
        min_size = 20
        if rect.width() < min_size:
            if handle_center_x < rect.center().x():
                rect.setLeft(rect.right() - min_size)
            else:
                rect.setRight(rect.left() + min_size)
                
        if rect.height() < min_size:
            if handle_center_y < rect.center().y():
                rect.setTop(rect.bottom() - min_size)
            else:
                rect.setBottom(rect.top() + min_size)
        
        # Cập nhật parent overlay
        self.parent_overlay.setRect(rect)
        # Trigger change notification
        self.parent_overlay._notify_change()
