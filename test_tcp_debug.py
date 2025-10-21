#!/usr/bin/env python3
"""
TCP Debug Test - Kiểm tra signal emit
"""
import sys
import logging
from PyQt5.QtCore import QCoreApplication, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QListWidget, QLineEdit, QPushButton

# Thêm project path
sys.path.insert(0, r'e:\PROJECT\sed')

from controller.tcp_controller import TCPController

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TCP Test - Signal Debug")
        self.setGeometry(100, 100, 600, 400)
        
        # Create widgets
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        # IP input
        self.ip_input = QLineEdit()
        self.ip_input.setText("192.168.1.190")
        self.ip_input.setPlaceholderText("IP Address")
        layout.addWidget(self.ip_input)
        
        # Port input
        self.port_input = QLineEdit()
        self.port_input.setText("4000")
        self.port_input.setPlaceholderText("Port")
        layout.addWidget(self.port_input)
        
        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.on_connect)
        layout.addWidget(self.connect_btn)
        
        # Send button
        self.send_btn = QPushButton("Send PING")
        self.send_btn.clicked.connect(self.on_send)
        layout.addWidget(self.send_btn)
        
        # Message list
        self.message_list = QListWidget()
        layout.addWidget(self.message_list)
        
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        # Create TCP controller
        self.tcp = TCPController()
        
        # Connect signals (WITH EXTRA LOGGING)
        print("\n=== Connecting signals ===")
        self.tcp.connection_status_changed.connect(self.on_connection_changed)
        print(f"✓ Connected: connection_status_changed")
        
        self.tcp.message_received.connect(self.on_message)
        print(f"✓ Connected: message_received")
        print("=== Signals connected ===\n")
        
    def on_connect(self):
        print("\n=== Connect button clicked ===")
        ip = self.ip_input.text()
        port = self.port_input.text()
        print(f"Connecting to {ip}:{port}")
        result = self.tcp.connect(ip, port)
        print(f"Connection result: {result}")
        print("=== Connect done ===\n")
        
    def on_send(self):
        print("\n=== Send button clicked ===")
        self.tcp.send_message("PING")
        print("=== Send done ===\n")
        
    def on_connection_changed(self, connected, message):
        print(f"\n★★★ on_connection_changed: connected={connected}, message={message}")
        self.message_list.addItem(f"Status: {message}")
        
    def on_message(self, message):
        print(f"\n★★★ on_message: {message!r}")
        self.message_list.addItem(f"RX: {message}")
        self.message_list.scrollToBottom()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TCP TEST WINDOW - Signal Debug")
    print("="*60 + "\n")
    
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec_())
