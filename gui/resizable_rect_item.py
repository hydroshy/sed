from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QObject
from PyQt5.QtGui import QPen, QBrush, QColor, QPainter
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsItem, QGraphicsEllipseItem

class ResizableRectItem(QGraphicsRectItem):
    """
    Hình chữ nhật có thể di chuyển và resize với các handle
    """
    
    # Signal được emit khi area thay đổi (position hoặc size)
    area_changed = pyqtSignal(int, int, int, int)  # x1, y1, x2, y2
    
    def __init__(self, rect, parent=None):
        super().__init__(rect, parent)
        
        # Thiết lập thuộc tính
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        
        # Thiết lập style - chỉ có viền, không có nền
        pen = QPen(QColor(255, 0, 0), 2)  # Viền đỏ, độ dày 2px
        brush = QBrush(Qt.BrushStyle.NoBrush)  # Không có nền
        self.setPen(pen)
        self.setBrush(brush)
        
        # Resize handles
        self.handles = []
        self.handle_size = 8
        self.selected_handle = None
        self.is_resizing = False
        
        # Tạo các handle
        self._create_handles()
        
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
    
    def setRect(self, rect):
        """Override setRect để cập nhật handles"""
        super().setRect(rect)
        self._update_handle_positions()
        # Notify about size change
        self._notify_change()
    
    def itemChange(self, change, value):
        """Override để cập nhật handles khi item thay đổi"""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._update_handle_positions()
            # Notify parent about position change
            self._notify_change()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            # Show/hide handles based on selection
            self.set_selected(value)
        return super().itemChange(change, value)
    
    def _notify_change(self):
        """Notify about area changes"""
        try:
            if hasattr(self.scene(), 'views') and self.scene().views():
                view = self.scene().views()[0]
                if hasattr(view.parent(), 'area_changed'):
                    coords = self.get_area_coords()
                    print(f"DEBUG: ResizableRectItem notifying change: {coords}")
                    view.parent().area_changed.emit(*coords)
                else:
                    print("DEBUG: view.parent() doesn't have area_changed signal")
            else:
                print("DEBUG: No scene views found")
        except Exception as e:
            print(f"DEBUG: Error in _notify_change: {e}")
    
    def set_selected(self, selected):
        """Hiển thị/ẩn handles khi select/deselect"""
        print(f"DEBUG: Setting selected={selected}, handles count={len(self.handles)}")
        for handle in self.handles:
            handle.setVisible(selected)
            print(f"DEBUG: Handle {handle.position} visible: {handle.isVisible()}")
        self.setSelected(selected)
        
    def set_style(self, border_color=None, fill_color=None, border_width=None, fill_opacity=None, transparent_fill=True):
        """Tùy chỉnh style của rectangle"""
        if border_color is None:
            border_color = QColor(255, 0, 0)  # Đỏ
        if border_width is None:
            border_width = 2
            
        pen = QPen(border_color, border_width)
        
        if transparent_fill:
            # Không có nền - chỉ khung
            brush = QBrush(Qt.BrushStyle.NoBrush)
        else:
            # Có nền mờ
            if fill_color is None:
                fill_color = QColor(255, 255, 255)  # Trắng
            if fill_opacity is None:
                fill_opacity = 30  # Mờ nhẹ
            brush = QBrush(QColor(fill_color.red(), fill_color.green(), fill_color.blue(), fill_opacity))
            
        self.setPen(pen)
        self.setBrush(brush)
        
    def get_area_coords(self):
        """Lấy tọa độ area (x1, y1, x2, y2)"""
        rect = self.rect()
        pos = self.pos()
        
        x1 = pos.x() + rect.left()
        y1 = pos.y() + rect.top()
        x2 = pos.x() + rect.right()
        y2 = pos.y() + rect.bottom()
        
        return (int(x1), int(y1), int(x2), int(y2))


class ResizeHandle(QGraphicsEllipseItem):
    """Handle để resize rectangle"""
    
    def __init__(self, size, position, parent_item):
        super().__init__(0, 0, size, size)
        
        self.position = position
        self.parent_rect = parent_item
        self.setParentItem(parent_item)
        
        # Style handle
        pen = QPen(QColor(255, 0, 0), 1)
        brush = QBrush(QColor(255, 255, 255))
        self.setPen(pen)
        self.setBrush(brush)
        
        # Thiết lập flags
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        
        # Cursor cho resize
        self._set_cursor()
        
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
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self.parent_rect:
            self._resize_parent_rect(value)
            
        return super().itemChange(change, value)
    
    def _resize_parent_rect(self, new_pos):
        """Resize parent rectangle dựa trên vị trí handle mới"""
        rect = self.parent_rect.rect()
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
        
        # Cập nhật parent rectangle
        self.parent_rect.setRect(rect)
