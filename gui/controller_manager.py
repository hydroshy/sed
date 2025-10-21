import logging
from PyQt5.QtWidgets import (
    QComboBox, QPushButton, QLabel,
    QMessageBox
)
from PyQt5.QtCore import Qt
from controller.uart_controller import UARTController

class ControllerManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.uart_controller = None
        
        # UI components
        self.device_combo: QComboBox = None
        self.baudrate_combo: QComboBox = None
        self.connect_button: QPushButton = None
        self.status_label: QLabel = None
        self.refresh_button: QPushButton = None
        
    def setup(self, device_combo: QComboBox, baudrate_combo: QComboBox,
             connect_button: QPushButton, status_label: QLabel, refresh_button: QPushButton = None):
        """Setup controller UI components"""
        try:
            self.device_combo = device_combo
            self.baudrate_combo = baudrate_combo
            self.connect_button = connect_button
            self.status_label = status_label
            self.refresh_button = refresh_button
            
            # Initialize UI components
            self._setup_ui()
            logging.info("Controller components setup completed")
        except Exception as e:
            logging.error(f"Error during controller setup: {str(e)}")
        
    def _setup_ui(self):
        """Initialize UI components"""
        try:
            # Check for required components first
            if not all([self.device_combo, self.baudrate_combo,
                       self.connect_button, self.status_label]):
                logging.error("Controller UI components not properly initialized")
                logging.error(f"device_combo: {self.device_combo is not None}")
                logging.error(f"baudrate_combo: {self.baudrate_combo is not None}")
                logging.error(f"connect_button: {self.connect_button is not None}")
                logging.error(f"status_label: {self.status_label is not None}")
                return

            # Initialize UART controller
            if not self.uart_controller:
                self.uart_controller = UARTController()
                self.uart_controller.connection_status_changed.connect(self._handle_connection_status)
                self.uart_controller.ports_updated.connect(self._update_ports_list)
                logging.info("UART Controller initialized successfully")

            # Initialize UI components
            self.status_label.setText("Ready")
            self.status_label.setStyleSheet("color: black")
            self.connect_button.setText("Connect")
            
            # Setup baudrate combo box
            self.baudrate_combo.clear()
            self.baudrate_combo.addItems(self.uart_controller.available_baudrates)
            self.baudrate_combo.setCurrentText('115200')  # Default baudrate
            
            # Connect signals
            self.connect_button.clicked.connect(self._handle_connect_click)
            if self.refresh_button:
                self.refresh_button.clicked.connect(self._handle_refresh_click)
                logging.info("Refresh button connected")
            
            # Initial port refresh
            self._refresh_ports()
            logging.info("UI setup completed successfully")
        except Exception as e:
            logging.error(f"Error during UI setup: {str(e)}")
            if self.status_label:
                self.status_label.setText("Setup Error")
                self.status_label.setStyleSheet("color: red")
                
    def _refresh_ports(self):
        """Refresh available serial ports"""
        try:
            if not self.device_combo:
                logging.error("Device combo box not initialized")
                return
                
            if not self.uart_controller:
                logging.error("UART controller not initialized")
                return
                
            self.device_combo.clear()
            ports = self.uart_controller.get_available_ports()
            
            if not ports:
                self.status_label.setText("No ports found")
                self.status_label.setStyleSheet("color: orange")
            else:
                self.device_combo.addItems(ports)
                self.status_label.setText("Ports refreshed")
                self.status_label.setStyleSheet("color: black")
                logging.info(f"Found {len(ports)} serial ports")
                
        except Exception as e:
            logging.error(f"Error refreshing ports: {str(e)}")
            self.status_label.setText("Refresh Error")
            self.status_label.setStyleSheet("color: red")

    def _handle_refresh_click(self):
        """Handle refresh button click"""
        self._refresh_ports()

    def _handle_connect_click(self):
        """Handle connect/disconnect button click"""
        try:
            # Verify UI components are available
            if not all([self.device_combo, self.baudrate_combo, 
                       self.connect_button, self.status_label]):
                logging.error("Controller UI components not properly initialized")
                return
                
            if not self.uart_controller:
                logging.error("UART controller not initialized")
                return
                
            if not self.uart_controller.is_connected:
                # Get selected port and baudrate
                port = self.device_combo.currentText()
                baudrate = self.baudrate_combo.currentText()
                
                if not port:
                    QMessageBox.warning(
                        self.main_window,
                        "Connection Error",
                        "No serial port selected"
                    )
                    return
                    
                logging.info(f"Attempting to connect to {port} at {baudrate} baud")
                
                # Attempt to connect
                if self.uart_controller.connect(port, baudrate):
                    self.connect_button.setText("Disconnect")
                    self._disable_connection_controls()
                    logging.info("Connection successful")
                else:
                    self._refresh_ports()  # Refresh ports list on failed connection
                    logging.error("Connection failed")
            else:
                # Disconnect
                self.uart_controller._disconnect()
                self.connect_button.setText("Connect")
                self._enable_connection_controls()
                logging.info("Disconnected successfully")
                
        except Exception as e:
            logging.error(f"Error during connection operation: {str(e)}")
            self.status_label.setText("Connection Error")
            self.status_label.setStyleSheet("color: red")
            self._refresh_ports()
            
    def _handle_connection_status(self, connected: bool, message: str):
        """Handle connection status changes"""
        if self.status_label:
            self.status_label.setText(message)
            
            # Set color based on connection status
            if connected:
                self.status_label.setStyleSheet("color: green")
            else:
                self.status_label.setStyleSheet("color: red")
                
    def _update_ports_list(self, ports: list):
        """Update ports list in combo box"""
        if self.device_combo:
            current_port = self.device_combo.currentText()
            self.device_combo.clear()
            self.device_combo.addItems(ports)
            
            # Try to restore previous selection
            index = self.device_combo.findText(current_port)
            if index >= 0:
                self.device_combo.setCurrentIndex(index)
                
    def _disable_connection_controls(self):
        """Disable connection controls when connected"""
        self.device_combo.setEnabled(False)
        self.baudrate_combo.setEnabled(False)
        
    def _enable_connection_controls(self):
        """Enable connection controls when disconnected"""
        self.device_combo.setEnabled(True)
        self.baudrate_combo.setEnabled(True)