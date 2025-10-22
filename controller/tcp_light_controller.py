"""
TCP Light Controller Module
Handles TCP communication with light control hardware
Similar to TCPController but optimized for light command send/receive
"""

import logging
import socket
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from typing import Optional, Dict, Any


class TCPLightController(QObject):
    """TCP controller for light hardware (LED, lamp, etc.)"""
    
    # Signals for UI updates
    connection_status_changed = pyqtSignal(bool, str)  # connected, status message
    message_received = pyqtSignal(str)  # message from device
    light_status_changed = pyqtSignal(str)  # light status: 'on', 'off', 'error'
    
    def __init__(self):
        super().__init__()
        self._socket: Optional[socket.socket] = None
        self._connected = False
        self._current_ip = ""
        self._current_port = 0
        self._stop_monitor = False
        self._monitor_thread = None
        self._light_status = "unknown"  # Track light status: 'on', 'off', 'unknown'
        
        logging.info("TCPLightController initialized")
        
    @pyqtSlot(str, str)
    def connect(self, ip: str, port: str) -> bool:
        """
        Kết nối đến thiết bị điều khiển đèn qua TCP
        
        Args:
            ip: Địa chỉ IP của thiết bị đèn
            port: Port number
            
        Returns:
            bool: True nếu kết nối thành công, False nếu thất bại
        """
        # Validate input
        if not ip or not port:
            self.connection_status_changed.emit(False, "Error: IP and port must be specified")
            logging.error("Connection failed: IP and port not specified")
            return False
            
        try:
            port_num = int(port)
            if port_num < 0 or port_num > 65535:
                self.connection_status_changed.emit(False, "Error: Invalid port number")
                logging.error(f"Invalid port number: {port_num}")
                return False
        except ValueError:
            self.connection_status_changed.emit(False, "Error: Port must be a number")
            logging.error(f"Port conversion failed: {port}")
            return False
            
        try:
            # Close existing connection if any
            if self._socket:
                self._disconnect()
                
            # Create new socket
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # ✅ OPTIMIZATION: Reduce timeout for responsive light control
            self._socket.settimeout(5)  # 5 seconds timeout
            
            # Try to connect
            logging.info(f"💡 Attempting to connect to light controller at {ip}:{port_num}")
            self._socket.connect((ip, port_num))
            logging.info(f"💡 Successfully connected to light controller at {ip}:{port_num}")
            
            self._connected = True
            self._current_ip = ip
            self._current_port = port_num
            self._light_status = "unknown"
            
            # Start monitor thread
            self._stop_monitor = False
            self._monitor_thread = threading.Thread(target=self._monitor_socket, daemon=False)
            self._monitor_thread.start()
            logging.info("💡 Light controller monitor thread started")
            
            self.connection_status_changed.emit(True, "Connected")
            return True
            
        except socket.timeout:
            self.connection_status_changed.emit(False, "Error: Connection timeout")
            logging.error("Light controller connection timeout")
            return False
        except ConnectionRefusedError:
            self.connection_status_changed.emit(False, "Error: Connection refused")
            logging.error("Light controller connection refused")
            return False
        except Exception as e:
            logging.error(f"Light controller connection error: {e}")
            self.connection_status_changed.emit(False, f"Error: {str(e)}")
            return False
            
    def send_message(self, message: str) -> bool:
        """
        Gửi tin nhắn/lệnh đến thiết bị điều khiển đèn
        
        Args:
            message: Lệnh cần gửi (e.g., 'on', 'off', 'toggle', 'brightness:50')
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        if not self._connected or not self._socket:
            logging.error("Cannot send light command: not connected or socket is None")
            self.connection_status_changed.emit(False, "Not connected")
            return False
            
        try:
            # Add newline để device biết kết thúc message
            data = (message + '\n').encode('utf-8')
            logging.info(f"💡 Sending light command: {message!r}")
            self._socket.sendall(data)
            logging.info(f"✓ Light command sent successfully: {message!r}")
            
            # Update light status based on command
            if message.lower() == 'on':
                self._light_status = 'on'
                self.light_status_changed.emit('on')
            elif message.lower() == 'off':
                self._light_status = 'off'
                self.light_status_changed.emit('off')
            elif message.lower() == 'toggle':
                # Toggle state - we'll get confirmation from device
                self._light_status = 'unknown'
                
            return True
        except Exception as e:
            logging.error(f"Light command send error: {e}")
            self._handle_connection_error()
            return False
            
    def turn_on(self) -> bool:
        """Bật đèn"""
        logging.info("💡 Requesting light ON")
        return self.send_message('on')
        
    def turn_off(self) -> bool:
        """Tắt đèn"""
        logging.info("💡 Requesting light OFF")
        return self.send_message('off')
        
    def toggle(self) -> bool:
        """Chuyển đổi trạng thái đèn"""
        logging.info("💡 Requesting light TOGGLE")
        return self.send_message('toggle')
        
    def set_brightness(self, level: int) -> bool:
        """
        Điều chỉnh độ sáng (0-100)
        
        Args:
            level: Mức độ sáng từ 0 (tắt) đến 100 (sáng tối đa)
        """
        if level < 0 or level > 100:
            logging.error(f"Invalid brightness level: {level}, must be 0-100")
            return False
        logging.info(f"💡 Requesting brightness level: {level}%")
        return self.send_message(f'brightness:{level}')
        
    def _monitor_socket(self):
        """Monitor socket for incoming data from light controller"""
        buffer = ""
        last_data_time = time.time()
        BUFFER_TIMEOUT = 0.1  # Fast response for light status
        FINAL_TIMEOUT = 1.0   # Final timeout before giving up
        
        logging.info("💡 Light controller monitor thread started")
        
        while not self._stop_monitor and self._socket:
            try:
                # Đọc dữ liệu từ thiết bị đèn
                data = self._socket.recv(4096)
                
                if not data:
                    # Connection closed by peer
                    logging.warning("💡 No data received - light controller closed connection")
                    self._handle_connection_error("Light controller disconnected")
                    break
                
                # Update last data time
                last_data_time = time.time()
                
                # Log raw data received
                logging.debug(f"💡 Raw data from light controller ({len(data)} bytes): {data!r}")
                
                # Decode data
                try:
                    decoded_data = data.decode('utf-8')
                    logging.debug(f"💡 Decoded light controller data: {decoded_data!r}")
                    buffer += decoded_data
                except UnicodeDecodeError as e:
                    logging.error(f"💡 Unicode decode error: {e}, raw data: {data!r}")
                    continue
                
                # ✅ OPTIMIZATION: Split lines immediately
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    self._handle_message(line)
                
                # Check for buffer timeout
                if buffer and (time.time() - last_data_time) > BUFFER_TIMEOUT:
                    logging.info(f"💡 Buffer timeout with data: {buffer!r}")
                    
                    # Split buffer by newline
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        self._handle_message(line)
                    
                    # Emit remaining data
                    if buffer:
                        self._handle_message(buffer)
                    
                    buffer = ""
                    last_data_time = time.time()
                    
            except socket.timeout:
                # Socket timeout - check if we have buffered data
                current_time = time.time()
                if buffer and (current_time - last_data_time) > FINAL_TIMEOUT:
                    logging.info(f"💡 Socket timeout with buffer: {buffer!r}")
                    
                    # Process buffered lines
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        self._handle_message(line)
                    
                    # Emit remaining data
                    if buffer:
                        self._handle_message(buffer)
                    
                    buffer = ""
                    last_data_time = current_time
                continue
                
            except Exception as e:
                logging.error(f"💡 Light controller monitor error: {e}", exc_info=True)
                self._handle_connection_error()
                break
        
        # Emit any remaining buffer data
        if buffer:
            logging.info(f"💡 Monitor stopping, remaining buffer: {buffer!r}")
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                self._handle_message(line)
            if buffer:
                self._handle_message(buffer)
                
        logging.info("💡 Light controller monitor thread stopped")
        
    def _handle_message(self, message: str):
        """
        Xử lý tin nhắn/trạng thái nhận được từ thiết bị đèn
        
        Args:
            message: Tin nhắn từ light controller (e.g., 'status:on', 'status:off', 'brightness:75')
        """
        # Strip whitespace
        message = message.strip()
        
        if not message:
            logging.debug("💡 Empty message received, skipping")
            return
        
        logging.info(f"💡 Light controller message: {message!r}")
        
        # Parse and update light status
        if message.lower().startswith('status:'):
            # Parse status: 'status:on' or 'status:off'
            status_part = message.split(':', 1)[1].lower()
            if status_part == 'on':
                self._light_status = 'on'
                self.light_status_changed.emit('on')
                logging.info(f"💡 Light status updated: ON")
            elif status_part == 'off':
                self._light_status = 'off'
                self.light_status_changed.emit('off')
                logging.info(f"💡 Light status updated: OFF")
        elif message.lower().startswith('brightness:'):
            # Parse brightness: 'brightness:75'
            try:
                brightness_str = message.split(':', 1)[1]
                brightness_level = int(brightness_str)
                logging.info(f"💡 Light brightness: {brightness_level}%")
                self.light_status_changed.emit(f'brightness:{brightness_level}')
            except (ValueError, IndexError) as e:
                logging.error(f"💡 Failed to parse brightness: {e}")
        
        # Emit all messages to UI
        self.message_received.emit(message)
        
    def _handle_connection_error(self, message: str = "Connection lost"):
        """Xử lý lỗi kết nối"""
        self._connected = False
        self._light_status = "error"
        self.connection_status_changed.emit(False, message)
        self.light_status_changed.emit('error')
        self._disconnect()
        
    def _disconnect(self):
        """Ngắt kết nối TCP với light controller"""
        try:
            self._stop_monitor = True
            if self._monitor_thread:
                self._monitor_thread.join(timeout=1.0)
                
            if self._socket:
                self._socket.close()
                self._socket = None
                
            self._connected = False
            self._current_ip = ""
            self._current_port = 0
            self._light_status = "unknown"
            
            logging.info("💡 Light controller disconnected")
        except Exception as e:
            logging.error(f"💡 Error during disconnect: {e}")
        finally:
            self.connection_status_changed.emit(False, "Disconnected")
            
    @property
    def is_connected(self) -> bool:
        """Kiểm tra trạng thái kết nối"""
        return self._connected and self._socket is not None
        
    @property
    def current_ip(self) -> str:
        """Lấy IP hiện tại"""
        return self._current_ip
        
    @property
    def current_port(self) -> int:
        """Lấy port hiện tại"""
        return self._current_port
        
    @property
    def light_status(self) -> str:
        """Lấy trạng thái đèn: 'on', 'off', 'error', 'unknown'"""
        return self._light_status
