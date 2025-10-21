import logging
import socket
import json
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from typing import Optional, Dict, Any

class TCPController(QObject):
    # Signals for UI updates
    connection_status_changed = pyqtSignal(bool, str)  # connected, status message
    message_received = pyqtSignal(str)  # message from device
    
    def __init__(self):
        super().__init__()
        self._socket: Optional[socket.socket] = None
        self._connected = False
        self._current_ip = ""
        self._current_port = 0
        self._stop_monitor = False
        self._monitor_thread = None
        
    @pyqtSlot(str, str)
    def connect(self, ip: str, port: str) -> bool:
        """
        Kết nối đến thiết bị qua TCP
        
        Args:
            ip: Địa chỉ IP của thiết bị
            port: Port number
            
        Returns:
            bool: True nếu kết nối thành công, False nếu thất bại
        """
        # Validate input
        if not ip or not port:
            self.connection_status_changed.emit(False, "Error: IP and port must be specified")
            return False
            
        try:
            port_num = int(port)
            if port_num < 0 or port_num > 65535:
                self.connection_status_changed.emit(False, "Error: Invalid port number")
                return False
        except ValueError:
            self.connection_status_changed.emit(False, "Error: Port must be a number")
            return False
            
        try:
            # Close existing connection if any
            if self._socket:
                self._disconnect()
                
            # Create new socket
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Set timeout to 30 seconds for receiving data
            self._socket.settimeout(30)  # 30 seconds timeout for recv/connect
            
            # Try to connect
            logging.info(f"Attempting to connect to {ip}:{port_num}")
            self._socket.connect((ip, port_num))
            logging.info(f"Successfully connected to {ip}:{port_num}")
            
            self._connected = True
            self._current_ip = ip
            self._current_port = port_num
            
            # Start monitor thread
            self._stop_monitor = False
            self._monitor_thread = threading.Thread(target=self._monitor_socket)
            self._monitor_thread.daemon = False  # Not daemon - keep running
            self._monitor_thread.start()
            logging.info("Monitor thread started")
            
            self.connection_status_changed.emit(True, "Connected")
            return True
            
        except socket.timeout:
            self.connection_status_changed.emit(False, "Error: Connection timeout")
            return False
        except ConnectionRefusedError:
            self.connection_status_changed.emit(False, "Error: Connection refused")
            return False
        except Exception as e:
            logging.error(f"Connection error: {e}")
            self.connection_status_changed.emit(False, f"Error: {str(e)}")
            return False
            
    def send_message(self, message: str) -> bool:
        """
        Gửi tin nhắn đến thiết bị
        
        Args:
            message: Tin nhắn cần gửi
            
        Returns:
            bool: True nếu gửi thành công, False nếu thất bại
        """
        if not self._connected or not self._socket:
            logging.error("Cannot send: not connected or socket is None")
            return False
            
        try:
            # Thêm newline để device biết kết thúc message
            data = (message + '\n').encode('utf-8')
            logging.info(f"★ Sending message: {message!r}")
            self._socket.sendall(data)
            logging.info(f"✓ Message sent successfully")
            return True
        except Exception as e:
            logging.error(f"Send error: {e}")
            self._handle_connection_error()
            return False
            
    def _monitor_socket(self):
        """Monitor socket cho dữ liệu đến"""
        buffer = ""
        last_data_time = time.time()
        logging.info("Monitor thread started")
        
        while not self._stop_monitor and self._socket:
            try:
                # Đọc dữ liệu
                data = self._socket.recv(1024)
                
                if not data:
                    # Connection closed by peer
                    logging.warning("No data received - connection closed by device")
                    self._handle_connection_error("Connection closed by device")
                    break
                
                # Update last data time
                last_data_time = time.time()
                
                # Log raw data received
                logging.debug(f"Raw data received ({len(data)} bytes): {data!r}")
                
                # Decode và xử lý dữ liệu
                try:
                    decoded_data = data.decode('utf-8')
                    logging.debug(f"Decoded data: {decoded_data!r}")
                    buffer += decoded_data
                    logging.debug(f"Current buffer: {buffer!r}")
                except UnicodeDecodeError as e:
                    logging.error(f"Unicode decode error: {e}, raw data: {data!r}")
                    continue
                
                # Xử lý từng dòng trong buffer (nếu có newline)
                has_newline = '\n' in buffer
                logging.debug(f"★ Checking buffer split: has_newline={has_newline}, buffer={buffer!r}")
                has_newline_count = buffer.count('\n')
                logging.debug(f"  Newline count: {has_newline_count}")
                
                line_count = 0
                while '\n' in buffer:
                    line_count += 1
                    logging.info(f"★ SPLITTING BUFFER! Iteration {line_count}")
                    line, buffer = buffer.split('\n', 1)
                    logging.info(f"Processing line from buffer: {line!r}, remaining: {buffer!r}")
                    self._handle_message(line)
                
                # Nếu buffer có dữ liệu nhưng không có newline, 
                # kiểm tra xem có timeout không và emit
                if buffer and (time.time() - last_data_time) > 0.5:
                    logging.info(f"Buffer timeout with data: {buffer!r}")
                    
                    # Split buffer by newline
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        logging.info(f"Emitting line from buffer timeout: {line!r}")
                        self._handle_message(line)
                    
                    # Emit remaining non-newline data
                    if buffer:
                        logging.info(f"Emitting remaining non-newline data: {buffer!r}")
                        self._handle_message(buffer)
                    
                    buffer = ""
                    last_data_time = time.time()
                    
            except socket.timeout:
                # Timeout là bình thường, nhưng kiểm tra buffer
                current_time = time.time()
                if buffer and (current_time - last_data_time) > 1.0:
                    logging.info(f"Socket timeout with buffered data: {buffer!r}")
                    
                    # IMPORTANT: Split buffer by newline before emitting!
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        logging.info(f"Emitting line from timeout buffer: {line!r}")
                        self._handle_message(line)
                    
                    # Emit remaining data if any
                    if buffer:
                        logging.info(f"Emitting remaining data after timeout: {buffer!r}")
                        self._handle_message(buffer)
                    
                    buffer = ""
                    last_data_time = current_time
                continue
            except Exception as e:
                logging.error(f"Monitor error: {e}", exc_info=True)
                self._handle_connection_error()
                break
        
        # Emit any remaining buffer data
        if buffer:
            logging.info(f"Monitor stopping, remaining buffer: {buffer!r}")
            # Split buffer before emitting
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                logging.info(f"Emitting remaining line: {line!r}")
                self._handle_message(line)
            # Emit any non-newline data
            if buffer:
                logging.info(f"Emitting final data: {buffer!r}")
                self._handle_message(buffer)
                
        logging.info("Monitor thread stopped")
        
    def _handle_message(self, message: str):
        """
        Xử lý tin nhắn nhận được từ device
        
        Args:
            message: Tin nhắn đã decode
        """
        # Strip whitespace
        message = message.strip()
        
        # Log message
        logging.info(f"_handle_message called with: {message!r}")
        
        # Emit tin nhắn để hiển thị trong UI nếu không rỗng
        if message:
            logging.info(f"Emitting signal - message_received.emit({message!r})")
            self.message_received.emit(message)
            logging.info(f"Signal emitted successfully")
        else:
            logging.debug("Message is empty after strip, not emitting")
        
    def _handle_connection_error(self, message: str = "Connection lost"):
        """Xử lý lỗi kết nối"""
        self._connected = False
        self.connection_status_changed.emit(False, message)
        self._disconnect()
        
    def _disconnect(self):
        """Ngắt kết nối TCP"""
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
            
        except Exception as e:
            logging.error(f"Error during disconnect: {e}")
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