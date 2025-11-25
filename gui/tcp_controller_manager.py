from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QLineEdit, QListWidget, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from controller.tcp_controller import TCPController
from controller.tcp_light_controller import TCPLightController
from gui.tcp_optimized_trigger import OptimizedTCPControllerManager
import logging
import time

class TCPControllerManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.tcp_controller = TCPController()
        self.light_controller = TCPLightController()  # ✨ NEW: Light controller
        
        # OPTIMIZATION: Initialize optimized trigger handler
        self.optimized_manager = None
        
        # UI components - Camera Controller
        self.ip_edit: QLineEdit = None
        self.port_edit: QLineEdit = None
        self.connect_button: QPushButton = None
        self.status_label: QLabel = None
        self.message_list: QListWidget = None
        self.message_edit: QLineEdit = None
        self.send_button: QPushButton = None
        
        # ✨ NEW: UI components - Light Controller
        self.light_ip_edit: QLineEdit = None
        self.light_port_edit: QLineEdit = None
        self.light_connect_button: QPushButton = None
        self.light_status_label: QLabel = None
        self.light_message_list: QListWidget = None
        self.light_message_edit: QLineEdit = None
        self.light_send_button: QPushButton = None
        
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
                # OPTIMIZATION: Initialize optimized trigger handler
                if hasattr(self.main_window, 'camera_manager'):
                    self.optimized_manager = OptimizedTCPControllerManager(
                        self.tcp_controller,
                        self.main_window.camera_manager
                    )
                    logging.info("Optimized TCP trigger handler initialized")
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
    
    def setup_light_controller(self, ip_edit: QLineEdit, port_edit: QLineEdit,
                              connect_button: QPushButton, status_label: QLabel,
                              message_list: QListWidget, message_edit: QLineEdit,
                              send_button: QPushButton):
        """Setup light controller UI components"""
        try:
            # Store UI components
            self.light_ip_edit = ip_edit
            self.light_port_edit = port_edit
            self.light_connect_button = connect_button
            self.light_status_label = status_label
            self.light_message_list = message_list
            self.light_message_edit = message_edit
            self.light_send_button = send_button
            
            # Set initial states
            self.light_status_label.setText("Disconnected")
            self.light_status_label.setStyleSheet("color: red")
            self._update_light_button_states(False)
            
            # Connect light controller signals
            self.light_controller.connection_status_changed.connect(
                self._on_light_connection_status
            )
            self.light_controller.message_received.connect(
                self._on_light_message_received
            )
            self.light_controller.light_status_changed.connect(
                self._on_light_status_changed
            )
            
            # Connect button signals
            self.light_connect_button.clicked.connect(
                self._on_light_connect_click
            )
            self.light_send_button.clicked.connect(
                self._on_light_send_click
            )
            
            # Allow pressing Enter in message edit to send
            self.light_message_edit.returnPressed.connect(
                self._on_light_send_click
            )
            
            logging.info("Light controller UI setup completed successfully")
            
        except Exception as e:
            logging.error(f"Error during light controller setup: {str(e)}")
            
    def _update_light_button_states(self, connected: bool):
        """Update light controller UI states based on connection status"""
        # Connection controls
        self.light_ip_edit.setEnabled(not connected)
        self.light_port_edit.setEnabled(not connected)
        self.light_connect_button.setText("Disconnect" if connected else "Connect")
        
        # Message controls
        self.light_message_edit.setEnabled(connected)
        self.light_send_button.setEnabled(connected)
    
    def _on_light_connection_status(self, connected: bool, message: str):
        """Handle light controller connection status changes"""
        self._update_light_button_states(connected)
        
        # Update status label
        self.light_status_label.setText(message)
        self.light_status_label.setStyleSheet(
            "color: green" if connected else "color: red"
        )
        
        # Add status message to list
        self.light_message_list.addItem(f"Status: {message}")
        self.light_message_list.scrollToBottom()
        
        logging.info(f"Light controller connection status: {message}")
    
    def _on_light_message_received(self, message: str):
        """Handle messages received from light controller"""
        logging.info(f"Message from light controller: {message!r}")
        
        # Add message to UI
        if self.light_message_list:
            self.light_message_list.addItem(f"← {message}")
            self.light_message_list.scrollToBottom()
    
    def _on_light_status_changed(self, status: str):
        """Handle light status changes"""
        logging.info(f"Light status changed: {status}")
    
    def _on_light_connect_click(self):
        """Handle light controller connect/disconnect button clicks"""
        logging.info("Light controller connect button clicked")
        
        if not self.light_controller.is_connected:
            # Get IP and port
            ip = self.light_ip_edit.text().strip()
            port = self.light_port_edit.text().strip()
            
            logging.info(f"Attempting to connect to light controller at {ip}:{port}")
            
            if not ip or not port:
                error_msg = "Error: IP and port required"
                logging.error(f"{error_msg}")
                self.light_status_label.setText(error_msg)
                self.light_status_label.setStyleSheet("color: red")
                return
            
            try:
                result = self.light_controller.connect(ip, port)
                logging.info(f"Connection attempt result: {result}")
            except Exception as e:
                logging.error(f"Error during connection: {str(e)}")
                self.light_status_label.setText(f"Error: {str(e)}")
                self.light_status_label.setStyleSheet("color: red")
        else:
            # Disconnect
            logging.info("Disconnecting light controller")
            try:
                self.light_controller._disconnect()
                logging.info("Disconnected successfully")
            except Exception as e:
                logging.error(f"Error during disconnect: {str(e)}")
    
    def _on_light_send_click(self):
        """Handle light controller send button clicks"""
        if not self.light_controller.is_connected:
            logging.warning("Not connected to light controller")
            return
        
        message = self.light_message_edit.text().strip()
        if message:
            if self.light_controller.send_message(message):
                # Add sent message to list
                self.light_message_list.addItem(f"→ {message}")
                self.light_message_list.scrollToBottom()
                # Clear input field
                self.light_message_edit.clear()
                logging.info(f"Message sent: {message}")
            else:
                self.light_message_list.addItem("Error: Failed to send message")
                self.light_message_list.scrollToBottom()
                logging.error("Failed to send message")
                
            
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
            logging.info(f"Message added to list")
        else:
            logging.error("message_list is None!")
        
        # NEW: Check if message is sensor event from pico
        # Expected format: "start_sensor,<sensor_id>" or "end_sensor,<sensor_id>"
        self._process_sensor_event(message)
        
        # Check if in trigger mode and trigger camera if needed
        self._check_and_trigger_camera_if_needed(message)
    
    def _process_sensor_event(self, message: str):
        """
        NEW: Xử lý sensor event từ TCP message
        
        Expected formats:
        - "start_sensor,<sensor_id>"  → Sensor IN (nhận từ pico)
        - "end_sensor,<sensor_id>"    → Sensor OUT
        
        Args:
            message: TCP message string
        """
        try:
            # Parse message
            if not message:
                return
            
            # Check if it's a sensor event
            if message.startswith("start_sensor"):
                # Parse sensor ID
                parts = message.split(",")
                if len(parts) >= 2:
                    try:
                        sensor_id = int(parts[1].strip())
                        self._handle_sensor_in_event(sensor_id)
                    except ValueError:
                        logging.warning(f"[TCPController] Invalid sensor ID in start_sensor: {parts[1]}")
                        
            elif message.startswith("end_sensor"):
                # Parse sensor ID
                parts = message.split(",")
                if len(parts) >= 2:
                    try:
                        sensor_id = int(parts[1].strip())
                        self._handle_sensor_out_event(sensor_id)
                    except ValueError:
                        logging.warning(f"[TCPController] Invalid sensor ID in end_sensor: {parts[1]}")
                        
        except Exception as e:
            logging.error(f"[TCPController] Error processing sensor event: {e}", exc_info=True)
    
    def _handle_sensor_in_event(self, sensor_id: int):
        """
        NEW: Xử lý sensor IN event (start_sensor)
        
        Ghép pending job result với frame mới từ TCP sensor_id
        
        Args:
            sensor_id: Sensor ID từ pico
        """
        try:
            logging.info(f"[TCPController] Sensor IN received: sensor_id={sensor_id}")
            print(f"DEBUG: [TCPController] Sensor IN received: {sensor_id}")
            
            # Get result tab manager
            result_tab_manager = getattr(self.main_window, 'result_tab_manager', None)
            if not result_tab_manager:
                logging.warning("[TCPController] Result Tab Manager not found!")
                print("DEBUG: [TCPController] Result Tab Manager not found!")
                return
            
            # Gọi method tạo frame và ghép result
            frame_id = result_tab_manager.on_sensor_in_received(sensor_id)
            
            if frame_id > 0:
                logging.info(f"[TCPController] Frame created: frame_id={frame_id}, sensor_id={sensor_id}")
                print(f"DEBUG: [TCPController] Frame created: {frame_id}")
                
                # Optional: hiển thị message trên UI
                if self.message_list:
                    self.message_list.addItem(f"[FRAME] Frame #{frame_id} created with sensor_id={sensor_id}")
                    self.message_list.scrollToBottom()
            else:
                logging.error(f"[TCPController] Failed to create frame for sensor_id={sensor_id}")
                print(f"DEBUG: [TCPController] Failed to create frame")
                
        except Exception as e:
            logging.error(f"[TCPController] Error handling sensor IN: {e}", exc_info=True)
            print(f"DEBUG: [TCPController] Error handling sensor IN: {e}")
    
    def _handle_sensor_out_event(self, sensor_id: int):
        """
        NEW: Xử lý sensor OUT event (end_sensor)
        When sensor OUT arrives:
        1. Frame marked as DONE
        2. Get frame status (OK/NG)
        3. Execute servo command: OK → GOTO 41, NG → HOME
        
        Args:
            sensor_id: Sensor ID từ pico
        """
        try:
            logging.info(f"[TCPController] 🔚 Sensor OUT received: sensor_id={sensor_id}")
            print(f"DEBUG: [TCPController] 🔚 Sensor OUT received: {sensor_id}")
            
            # Get result tab manager
            result_tab_manager = getattr(self.main_window, 'result_tab_manager', None)
            if not result_tab_manager:
                logging.warning("[TCPController] Result Tab Manager not found!")
                return
            
            # Thêm sensor OUT event (frame marked as DONE)
            success = result_tab_manager.add_sensor_out_event(sensor_id)
            
            if success:
                logging.info(f"[TCPController] Sensor OUT matched successfully")
                print(f"DEBUG: [TCPController] Sensor OUT matched")
                
                # ✅ NEW: Execute servo command based on frame status
                self._execute_servo_command_for_done_frame()
                
                # Optional: hiển thị message trên UI
                if self.message_list:
                    self.message_list.addItem(f"[SENSOR_OUT] Sensor OUT={sensor_id} matched")
                    self.message_list.scrollToBottom()
            else:
                logging.warning(f"[TCPController] Sensor OUT not matched (no pending frame)")
                print(f"DEBUG: [TCPController] Sensor OUT not matched")
                
        except Exception as e:
            logging.error(f"[TCPController] Error handling sensor OUT: {e}", exc_info=True)
            print(f"DEBUG: [TCPController] Error handling sensor OUT: {e}")
    
    def _execute_servo_command_for_done_frame(self):
        """
        ✅ NEW: Execute servo command based on the frame that just became DONE
        
        FIFO: Get most recently DONE frame
        - If frame_status == "OK" → Send "GOTO 41" (move to position 41)
        - If frame_status == "NG" → Send "HOME" (move to home position)
        """
        try:
            # Get result tab manager to access queue
            result_tab_manager = getattr(self.main_window, 'result_tab_manager', None)
            if not result_tab_manager:
                logging.warning("[TCPController] Cannot execute servo: Result Tab Manager not found")
                return
            
            # Get FIFO queue
            fifo_queue = getattr(result_tab_manager, 'fifo_queue', None)
            if not fifo_queue:
                logging.warning("[TCPController] Cannot execute servo: FIFO queue not found")
                return
            
            # Get the most recently DONE frame
            done_frame = fifo_queue.get_last_done_frame()
            if not done_frame:
                logging.warning("[TCPController] Cannot execute servo: No DONE frame found")
                return
            
            # Determine servo command based on frame status
            frame_status = done_frame.frame_status
            servo_command = None
            
            if frame_status == "OK":
                servo_command = "GOTO 41"
                logging.info(f"[TCPController] ✅ Frame {done_frame.frame_id} is OK → Servo command: GOTO 41")
                print(f"DEBUG: [TCPController] ✅ OK status → GOTO 41")
            elif frame_status == "NG":
                servo_command = "HOME"
                logging.info(f"[TCPController] ❌ Frame {done_frame.frame_id} is NG → Servo command: HOME")
                print(f"DEBUG: [TCPController] ❌ NG status → HOME")
            else:
                logging.warning(f"[TCPController] Frame status is '{frame_status}' (not OK/NG), skipping servo command")
                print(f"DEBUG: [TCPController] Skipping: status={frame_status}")
                return
            
            # Send servo command via TCP
            if servo_command and self.tcp_controller and self.tcp_controller.is_connected:
                success = self.tcp_controller.send_message(servo_command)
                
                if success:
                    logging.info(f"[TCPController] ✅ Servo command sent: {servo_command}")
                    print(f"DEBUG: [TCPController] ✅ TX: {servo_command}")
                    
                    # Add to message list for UI display
                    if self.message_list:
                        self.message_list.addItem(f"[SERVO] TX: {servo_command}")
                        self.message_list.scrollToBottom()
                else:
                    logging.error(f"[TCPController] Failed to send servo command: {servo_command}")
                    print(f"DEBUG: [TCPController] ❌ Failed to send: {servo_command}")
            else:
                logging.warning("[TCPController] Cannot send servo command: TCP not connected")
                print(f"DEBUG: [TCPController] TCP not connected")
            
        except Exception as e:
            logging.error(f"[TCPController] Error executing servo command: {e}", exc_info=True)
            print(f"DEBUG: [TCPController] Error executing servo: {e}")
    
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
    
    def _get_delay_trigger_settings(self):
        """
        Get delay trigger settings from UI
        
        Returns:
            tuple: (is_enabled: bool, delay_ms: float)
                   delay_ms is the delay in milliseconds (0.0 if disabled)
        """
        try:
            delay_checkbox = getattr(self.main_window, 'delayTriggerCheckBox', None)
            delay_spinbox = getattr(self.main_window, 'delayTriggerTime', None)
            
            if not delay_checkbox or not delay_spinbox:
                return False, 0.0
            
            is_enabled = delay_checkbox.isChecked()
            delay_ms = delay_spinbox.value() if is_enabled else 0.0
            
            return is_enabled, delay_ms
            
        except Exception as e:
            logging.error(f"Error getting delay trigger settings: {e}")
            return False, 0.0
    
    def _apply_delay_trigger(self, delay_ms: float):
        """
        Apply delay before triggering camera
        
        Handles both delay application and cooldown management:
        - If delay < cooldown: applies delay, then trigger (may hit cooldown)
        - If delay >= cooldown: resets trigger timer to allow trigger
        
        Args:
            delay_ms: Delay time in milliseconds (0.0 = no delay)
        """
        if delay_ms > 0:
            # Convert milliseconds to seconds
            delay_sec = delay_ms / 1000.0
            logging.info(f"Applying delay: {delay_ms:.1f}ms ({delay_sec:.4f}s)")
            
            # IMPORTANT: Reset the last_trigger_time so the delay duration
            # acts as the effective cooldown period instead of blocking trigger
            try:
                if hasattr(self.main_window, 'camera_manager') and self.main_window.camera_manager:
                    camera_manager = self.main_window.camera_manager
                    if hasattr(camera_manager, 'camera_stream') and camera_manager.camera_stream:
                        camera_stream = camera_manager.camera_stream
                        
                        # Get current cooldown
                        import time as time_module
                        current_cooldown_s = camera_stream._cooldown_s
                        current_cooldown_ms = current_cooldown_s * 1000.0
                        
                        # If delay >= cooldown, reset the trigger timer
                        # This ensures trigger after delay won't be blocked
                        if delay_ms >= current_cooldown_ms:
                            logging.info(f"📊 Delay ({delay_ms:.1f}ms) >= Cooldown ({current_cooldown_ms:.1f}ms)")
                            logging.info(f"📊 Resetting trigger timer to bypass cooldown block")
                            # Set last_trigger_time to BEFORE delay duration
                            camera_stream._last_trigger_time = time_module.time() - delay_sec
                        else:
                            logging.info(f"📊 Delay ({delay_ms:.1f}ms) < Cooldown ({current_cooldown_ms:.1f}ms)")
                            logging.info(f"📊 Adjusting cooldown temporarily to prevent blocking")
                            # For smaller delays, temporarily reduce cooldown
                            new_cooldown_sec = delay_sec * 0.9
                            camera_stream.set_trigger_cooldown(new_cooldown_sec)
            except Exception as e:
                logging.debug(f"Note: Could not manage cooldown: {e}")
            
            time.sleep(delay_sec)
            logging.info(f"Delay completed, triggering camera now...")

    def _check_and_trigger_camera_if_needed(self, message: str):
        """
        Handle start_rising and end_rising sensor signals and update result tab
        
        Message formats from sensor:
        - "start_rising||<sensor_id>" → Create new frame entry (sensor IN)
        - "end_rising||<sensor_id>"   → Match to pending frame (sensor OUT, FIFO)
        
        NOTE: Neither message triggers camera automatically. Camera trigger is user-controlled.
        """
        try:
            # Check for start_rising signal
            if "start_rising" in message.lower():
                self._handle_start_rising(message)
            # Check for end_rising signal
            elif "end_rising" in message.lower():
                self._handle_end_rising(message)
            else:
                logging.debug(f"Message '{message}' is not start_rising or end_rising, ignoring")
                
        except Exception as e:
            logging.error(f"Error in _check_and_trigger_camera_if_needed: {e}", exc_info=True)
    
    def _handle_start_rising(self, message: str):
        """
        Handle start_rising signal - create new frame entry in result tab
        
        Message format: "start_rising||<sensor_id>"
        """
        try:
            logging.info(f"★ Detected start_rising signal: {message}")
            
            # Extract sensor_id from message format: "start_rising||<sensor_id>"
            try:
                parts = message.split('||')
                if len(parts) >= 2:
                    sensor_id = int(parts[1].strip())
                    logging.info(f"★ Extracted sensor_id: {sensor_id}")
                else:
                    logging.warning(f"Could not parse sensor_id from message: {message}")
                    return
            except (ValueError, IndexError) as e:
                logging.warning(f"Error parsing sensor_id from message '{message}': {e}")
                return
            
            # Call sensor IN handler to create frame and merge result
            logging.info(f"★ Calling _handle_sensor_in_event with sensor_id={sensor_id}")
            self._handle_sensor_in_event(sensor_id)
                
        except Exception as e:
            logging.error(f"Error in _handle_start_rising: {e}", exc_info=True)
    
    def _handle_end_rising(self, message: str):
        """
        Handle end_rising signal - match to first PENDING frame in queue (FIFO)
        
        Message format: "end_rising||<sensor_id>"
        When matched, frame's completion_status becomes DONE
        """
        try:
            logging.info(f"★ Detected end_rising signal: {message}")
            
            # Extract sensor_id from message format: "end_rising||<sensor_id>"
            try:
                parts = message.split('||')
                if len(parts) >= 2:
                    sensor_id = int(parts[1].strip())
                    logging.info(f"★ Extracted sensor_id for end_rising: {sensor_id}")
                else:
                    logging.warning(f"Could not parse sensor_id from message: {message}")
                    return
            except (ValueError, IndexError) as e:
                logging.warning(f"Error parsing sensor_id from message '{message}': {e}")
                return
            
            # Call sensor OUT handler to match to PENDING frame
            logging.info(f"★ Calling _handle_sensor_out_event with sensor_id={sensor_id}")
            self._handle_sensor_out_event(sensor_id)
                
        except Exception as e:
            logging.error(f"Error in _handle_end_rising: {e}", exc_info=True)
    
    def _restore_default_cooldown(self):
        """
        Restore camera cooldown to default value (250ms)
        This is called after trigger completes to ensure normal cooldown timing
        """
        try:
            if hasattr(self.main_window, 'camera_manager') and self.main_window.camera_manager:
                camera_manager = self.main_window.camera_manager
                if hasattr(camera_manager, 'camera_stream') and camera_manager.camera_stream:
                    camera_stream = camera_manager.camera_stream
                    # Restore to default 250ms (0.25s)
                    camera_stream.set_trigger_cooldown(0.25)
                    logging.debug(f"Cooldown restored to default: 250ms")
        except Exception as e:
            logging.debug(f"Note: Could not restore cooldown: {e}")
    
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
            
            # ✨ Cleanup light controller
            if self.light_controller:
                try:
                    if hasattr(self.light_controller, '_disconnect'):
                        self.light_controller._disconnect()
                except Exception as e:
                    logging.debug(f"Error disconnecting light controller: {e}")
            
            logging.info("TCPControllerManager cleanup completed")
        
        except Exception as e:
            logging.error(f"Error during TCPControllerManager cleanup: {e}")