from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QLineEdit, QListWidget
from PyQt5.QtCore import Qt
from controller.tcp_controller import TCPController
from gui.tcp_optimized_trigger import OptimizedTCPControllerManager
import logging

class TCPControllerManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.tcp_controller = TCPController()
        
        # ✅ OPTIMIZATION: Initialize optimized trigger handler
        self.optimized_manager = None
        
        # UI components
        self.ip_edit: QLineEdit = None
        self.port_edit: QLineEdit = None
        self.connect_button: QPushButton = None
        self.status_label: QLabel = None
        self.message_list: QListWidget = None
        self.message_edit: QLineEdit = None
        self.send_button: QPushButton = None
        
    def setup(self, ip_edit: QLineEdit, port_edit: QLineEdit,
             connect_button: QPushButton, status_label: QLabel,
             message_list: QListWidget, message_edit: QLineEdit,
             send_button: QPushButton):
        """Setup UI components"""
        try:
            # Store UI components
            self.ip_edit = ip_edit
            self.port_edit = port_edit
            self.connect_button = connect_button
            self.status_label = status_label
            self.message_list = message_list
            self.message_edit = message_edit
            self.send_button = send_button
            
            # Set initial states
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: red")
            self._update_button_states(False)
            
            # Debug trạng thái widget trước khi kết nối
            logging.info(f"Widget states before connecting signals:")
            logging.info(f"ip_edit: enabled={ip_edit.isEnabled()}")
            logging.info(f"port_edit: enabled={port_edit.isEnabled()}")
            logging.info(f"connect_button: enabled={connect_button.isEnabled()}")
            
            # Connect signals with debug
            try:
                # ✅ OPTIMIZATION: Initialize optimized trigger handler
                if hasattr(self.main_window, 'camera_manager'):
                    self.optimized_manager = OptimizedTCPControllerManager(
                        self.tcp_controller,
                        self.main_window.camera_manager
                    )
                    logging.info("✓ Optimized TCP trigger handler initialized")
                else:
                    logging.warning("Camera manager not found, optimized handler disabled")
                
                # Connect TCP controller signals
                self.tcp_controller.connection_status_changed.connect(self._on_connection_status)
                self.tcp_controller.message_received.connect(self._on_message_received)
                logging.info("TCP controller signals connected")
                
                # Connect button signals with debug info
                before_count = self.connect_button.receivers(self.connect_button.clicked)
                self.connect_button.clicked.connect(self._on_connect_click)
                after_count = self.connect_button.receivers(self.connect_button.clicked)
                logging.info(f"Connect button signal connections: before={before_count}, after={after_count}")
                
                # Connect other UI signals
                self.send_button.clicked.connect(self._on_send_click)
                self.message_edit.returnPressed.connect(self._on_send_click)  # Enter to send
                
                # Log thành công
                logging.info("TCP Controller Manager setup completed successfully")
                
                # Đảm bảo các widget được enable
                self.ip_edit.setEnabled(True)
                self.port_edit.setEnabled(True)
                self.connect_button.setEnabled(True)
                
                # Debug trạng thái cuối
                logging.info(f"Final widget states:")
                logging.info(f"ip_edit: enabled={self.ip_edit.isEnabled()}")
                logging.info(f"port_edit: enabled={self.port_edit.isEnabled()}")
                logging.info(f"connect_button: enabled={self.connect_button.isEnabled()}")
                
            except Exception as e:
                logging.error(f"Error during signal connection: {str(e)}")
                raise  # Re-raise để main window có thể xử lý
            
        except Exception as e:
            logging.error(f"Error during TCP controller setup: {str(e)}")
            
    def _update_button_states(self, connected: bool):
        """Update UI states based on connection status"""
        # Connection controls
        self.ip_edit.setEnabled(not connected)
        self.port_edit.setEnabled(not connected)
        self.connect_button.setText("Disconnect" if connected else "Connect")
        
        # Message controls
        self.message_edit.setEnabled(connected)
        self.send_button.setEnabled(connected)
        
    def _on_connection_status(self, connected: bool, message: str):
        """Handle connection status changes"""
        self._update_button_states(connected)
        
        # Update status label
        self.status_label.setText(message)
        self.status_label.setStyleSheet(
            "color: green" if connected else "color: red"
        )
        
        # Add status message to list
        self.message_list.addItem(f"Status: {message}")
        self.message_list.scrollToBottom()
        
    def _on_message_received(self, message: str):
        """Handle received messages and trigger camera in trigger mode"""
        logging.info(f"★★★ _on_message_received CALLED! message={message!r} ★★★")
        
        # Add message to UI
        if self.message_list:
            logging.info(f"Adding message to list: RX: {message}")
            self.message_list.addItem(f"RX: {message}")
            self.message_list.scrollToBottom()
            logging.info(f"✓ Message added to list")
        else:
            logging.error("✗ message_list is None!")
        
        # Check if in trigger mode and trigger camera if needed
        self._check_and_trigger_camera_if_needed(message)
        
    def _on_connect_click(self):
        """Handle connect/disconnect button clicks"""
        logging.info("=== Connect button clicked! ===")
        logging.info(f"Current connection state: {self.tcp_controller.is_connected}")
        logging.info(f"Button text: {self.connect_button.text() if self.connect_button else 'None'}")
        
        # Kiểm tra chi tiết về button
        if self.connect_button:
            logging.info(f"Connect button properties:")
            logging.info(f"- Enabled: {self.connect_button.isEnabled()}")
            logging.info(f"- Visible: {self.connect_button.isVisible()}")
            logging.info(f"- Signal connections: {self.connect_button.receivers(self.connect_button.clicked)}")
        
        if not self.tcp_controller.is_connected:
            # Kiểm tra các widget input
            for name, widget in [("IP Edit", self.ip_edit), ("Port Edit", self.port_edit)]:
                if widget:
                    logging.info(f"{name} properties:")
                    logging.info(f"- Text: '{widget.text()}'")
                    logging.info(f"- Enabled: {widget.isEnabled()}")
                    logging.info(f"- Visible: {widget.isVisible()}")
                else:
                    logging.error(f"{name} widget not found!")
            
            # Try to connect
            ip = self.ip_edit.text().strip() if self.ip_edit else ""
            port = self.port_edit.text().strip() if self.port_edit else ""
            
            logging.info(f"Attempting to connect with IP: '{ip}', Port: '{port}'")
            
            if not ip or not port:
                error_msg = "Error: IP and port required"
                logging.error(error_msg)
                if self.status_label:
                    self.status_label.setText(error_msg)
                    self.status_label.setStyleSheet("color: red")
                return
            
            try:
                result = self.tcp_controller.connect(ip, port)
                logging.info(f"Connection attempt result: {result}")
            except Exception as e:
                logging.error(f"Error during connection: {str(e)}")
                if self.status_label:
                    self.status_label.setText(f"Error: {str(e)}")
                    self.status_label.setStyleSheet("color: red")
        else:
            # Disconnect
            logging.info("Disconnecting from current connection")
            try:
                self.tcp_controller._disconnect()
                logging.info("Disconnected successfully")
            except Exception as e:
                logging.error(f"Error during disconnect: {str(e)}")
                if self.status_label:
                    self.status_label.setText(f"Error: {str(e)}")
                    self.status_label.setStyleSheet("color: red")
            
    def _on_send_click(self):
        """Handle send button clicks"""
        if not self.tcp_controller.is_connected:
            return
            
        message = self.message_edit.text().strip()
        if message:
            if self.tcp_controller.send_message(message):
                # Add sent message to list
                self.message_list.addItem(f"TX: {message}")
                self.message_list.scrollToBottom()
                # Clear input field
                self.message_edit.clear()
            else:
                self.message_list.addItem("Error: Failed to send message")
                self.message_list.scrollToBottom()
    
    def _check_and_trigger_camera_if_needed(self, message: str):
        """
        Check if message is a sensor trigger command and trigger camera if in trigger mode
        
        Message format from sensor: "start_rising||1634723"
        This method will:
        1. Parse the message
        2. Check if camera is in trigger mode
        3. Trigger camera capture if needed
        """
        try:
            # Parse message - expected format: "start_rising||<timestamp>"
            if "start_rising" not in message.lower():
                logging.debug(f"Message '{message}' is not a start_rising trigger, ignoring")
                return
            
            logging.info(f"★ Detected trigger command: {message}")
            
            # Check if camera_manager exists
            if not hasattr(self.main_window, 'camera_manager') or not self.main_window.camera_manager:
                logging.warning("camera_manager not found, cannot trigger camera")
                return
            
            camera_manager = self.main_window.camera_manager
            
            # Check if in trigger mode (camera_manager.current_mode == 'trigger')
            if not hasattr(camera_manager, 'current_mode'):
                logging.warning("camera_manager.current_mode not found")
                return
            
            if camera_manager.current_mode != 'trigger':
                logging.debug(f"Camera not in trigger mode (current mode: {camera_manager.current_mode}), skipping trigger")
                return
            
            logging.info(f"★ Camera is in trigger mode, triggering capture for: {message}")
            
            # Trigger camera capture
            logging.info(f"★ Calling camera_manager.activate_capture_request()")
            try:
                # Trigger capture
                result = camera_manager.activate_capture_request()
                if result:
                    logging.info(f"✓ Camera triggered successfully for message: {message}")
                    # Add trigger event to message list for user feedback
                    self.message_list.addItem(f"[TRIGGER] Camera captured from: {message}")
                    self.message_list.scrollToBottom()
                else:
                    logging.warning(f"✗ Failed to trigger camera for message: {message}")
            except Exception as e:
                logging.error(f"✗ Error triggering camera: {e}", exc_info=True)
                
        except Exception as e:
            logging.error(f"Error in _check_and_trigger_camera_if_needed: {e}", exc_info=True)
    
    def cleanup(self):
        """
        Clean up TCP controller and optimized handler resources
        Called during application shutdown to prevent threading hangs
        """
        try:
            # Cleanup optimized trigger handler first
            if self.optimized_manager:
                try:
                    self.optimized_manager.cleanup()
                except Exception as e:
                    logging.debug(f"Error cleaning up optimized manager: {e}")
            
            # Cleanup TCP controller
            if self.tcp_controller:
                try:
                    if hasattr(self.tcp_controller, 'disconnect'):
                        self.tcp_controller.disconnect()
                except Exception as e:
                    logging.debug(f"Error disconnecting TCP controller: {e}")
            
            logging.info("✓ TCPControllerManager cleanup completed")
        
        except Exception as e:
            logging.error(f"Error during TCPControllerManager cleanup: {e}")