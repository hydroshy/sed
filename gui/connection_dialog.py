"""
Module hiển thị hộp thoại kết nối công cụ trong workflow
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QComboBox, QCheckBox, QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt

import logging
logger = logging.getLogger(__name__)

class ConnectToolsDialog(QDialog):
    """Hộp thoại cho phép người dùng kết nối các công cụ trong workflow"""
    
    def __init__(self, job, parent=None):
        super().__init__(parent)
        self.job = job
        self.source_tool = None
        self.target_tool = None
        self.is_primary = False
        self.result = False
        
        self.setWindowTitle("Connect Tools")
        self.setMinimumWidth(400)
        self._setup_ui()
        
    def _setup_ui(self):
        """Thiết lập giao diện người dùng"""
        # Layout chính
        main_layout = QVBoxLayout(self)
        
        # Source tool selection
        source_group = QGroupBox("Source Tool")
        source_layout = QVBoxLayout(source_group)
        source_layout.addWidget(QLabel("Select source tool:"))
        self.source_combo = QComboBox()
        self._populate_tool_combo(self.source_combo)
        source_layout.addWidget(self.source_combo)
        main_layout.addWidget(source_group)
        
        # Target tool selection
        target_group = QGroupBox("Target Tool")
        target_layout = QVBoxLayout(target_group)
        target_layout.addWidget(QLabel("Select target tool:"))
        self.target_combo = QComboBox()
        self._populate_tool_combo(self.target_combo)
        target_layout.addWidget(self.target_combo)
        main_layout.addWidget(target_group)
        
        # Primary connection option
        self.primary_check = QCheckBox("Set as primary source (main input for the target tool)")
        self.primary_check.setChecked(True)
        main_layout.addWidget(self.primary_check)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)
        
        # Connect signals
        self.connect_button.clicked.connect(self._on_connect)
        self.cancel_button.clicked.connect(self.reject)
        self.source_combo.currentIndexChanged.connect(self._update_target_combo)
        
        # Initial update
        self._update_target_combo()
        
    def _populate_tool_combo(self, combo):
        """Điền danh sách công cụ vào combo box"""
        combo.clear()
        for tool in self.job.tools:
            combo.addItem(f"{tool.display_name} (ID: {tool.tool_id})", tool.tool_id)
            
    def _update_target_combo(self):
        """Cập nhật danh sách công cụ đích khi nguồn thay đổi"""
        # Lưu selection hiện tại
        current_target = self.target_combo.currentData()
        
        # Lấy tool nguồn được chọn
        source_id = self.source_combo.currentData()
        source_tool = None
        if source_id is not None:
            source_tool = self.job.get_tool_by_id(source_id)
            
        # Xóa và điền lại target combo
        self.target_combo.clear()
        for tool in self.job.tools:
            # Không cho phép kết nối với chính nó
            if source_tool and tool.tool_id == source_tool.tool_id:
                continue
                
            # Kiểm tra xem đã có kết nối chưa
            already_connected = False
            if source_tool and tool in source_tool.outputs:
                already_connected = True
                
            # Thêm vào combo với trạng thái kết nối
            display_text = f"{tool.display_name} (ID: {tool.tool_id})"
            if already_connected:
                display_text += " [Connected]"
                
            self.target_combo.addItem(display_text, tool.tool_id)
            
        # Khôi phục selection trước đó nếu có thể
        if current_target is not None:
            index = self.target_combo.findData(current_target)
            if index >= 0:
                self.target_combo.setCurrentIndex(index)
                
    def _on_connect(self):
        """Xử lý khi người dùng nhấn nút Connect"""
        source_id = self.source_combo.currentData()
        target_id = self.target_combo.currentData()
        
        if source_id is None or target_id is None:
            QMessageBox.warning(self, "Connection Error", "Please select both source and target tools.")
            return
            
        # Kiểm tra có trùng không
        if source_id == target_id:
            QMessageBox.warning(self, "Connection Error", "Source and target tools cannot be the same.")
            return
            
        # Lấy các tool
        self.source_tool = self.job.get_tool_by_id(source_id)
        self.target_tool = self.job.get_tool_by_id(target_id)
        
        if not self.source_tool or not self.target_tool:
            QMessageBox.warning(self, "Connection Error", "Selected tools not found.")
            return
            
        # Kiểm tra đã kết nối chưa
        if self.target_tool in self.source_tool.outputs:
            reply = QMessageBox.question(
                self,
                "Existing Connection",
                "These tools are already connected. Do you want to modify the connection?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
                
        # Lưu kết quả
        self.is_primary = self.primary_check.isChecked()
        self.result = True
        self.accept()
        
    def get_result(self):
        """Lấy kết quả từ hộp thoại"""
        if self.result:
            return (self.source_tool, self.target_tool, self.is_primary)
        return None


class DisconnectToolsDialog(QDialog):
    """Hộp thoại cho phép người dùng ngắt kết nối các công cụ trong workflow"""
    
    def __init__(self, job, parent=None):
        super().__init__(parent)
        self.job = job
        self.source_tool = None
        self.target_tool = None
        self.result = False
        
        self.setWindowTitle("Disconnect Tools")
        self.setMinimumWidth(400)
        self._setup_ui()
        
    def _setup_ui(self):
        """Thiết lập giao diện người dùng"""
        # Layout chính
        main_layout = QVBoxLayout(self)
        
        # Chọn kết nối để ngắt
        main_layout.addWidget(QLabel("Select connection to disconnect:"))
        
        # Tạo danh sách kết nối
        self.connections_combo = QComboBox()
        self._populate_connections_combo()
        main_layout.addWidget(self.connections_combo)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.disconnect_button = QPushButton("Disconnect")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.disconnect_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)
        
        # Connect signals
        self.disconnect_button.clicked.connect(self._on_disconnect)
        self.cancel_button.clicked.connect(self.reject)
        
    def _populate_connections_combo(self):
        """Điền danh sách kết nối vào combo box"""
        self.connections_combo.clear()
        
        # Lấy tất cả các kết nối
        for source_tool in self.job.tools:
            for target_tool in source_tool.outputs:
                is_primary = target_tool.source_tool == source_tool
                primary_text = " (Primary)" if is_primary else ""
                display_text = f"{source_tool.display_name} -> {target_tool.display_name}{primary_text}"
                
                # Lưu dữ liệu dưới dạng tuple (source_id, target_id)
                self.connections_combo.addItem(display_text, (source_tool.tool_id, target_tool.tool_id))
                
    def _on_disconnect(self):
        """Xử lý khi người dùng nhấn nút Disconnect"""
        connection_data = self.connections_combo.currentData()
        
        if not connection_data:
            QMessageBox.warning(self, "Disconnect Error", "Please select a connection to disconnect.")
            return
            
        # Lấy các tool
        source_id, target_id = connection_data
        self.source_tool = self.job.get_tool_by_id(source_id)
        self.target_tool = self.job.get_tool_by_id(target_id)
        
        if not self.source_tool or not self.target_tool:
            QMessageBox.warning(self, "Disconnect Error", "Selected tools not found.")
            return
            
        # Xác nhận ngắt kết nối
        reply = QMessageBox.question(
            self,
            "Confirm Disconnect",
            f"Are you sure you want to disconnect {self.source_tool.display_name} from {self.target_tool.display_name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.result = True
            self.accept()
            
    def get_result(self):
        """Lấy kết quả từ hộp thoại"""
        if self.result:
            return (self.source_tool, self.target_tool)
        return None
