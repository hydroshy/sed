from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtWidgets import QApplication, QComboBox
from camera.camera_stream import CameraStream
from gui.camera_view import CameraView
import logging

class CameraManager(QObject):
    """
    Quản lý camera và xử lý tương tác với camera
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent  # Store reference to main window
        self.camera_stream = None
        self.camera_view = None
        self.exposure_edit = None  # Chỉ còn exposure edit, không có slider
        self.gain_edit = None
        self.ev_edit = None
        self.focus_bar = None
        self.fps_num = None
        self.width_spinbox = None
        self.height_spinbox = None
        
        # Settings synchronization
        self.settings_manager = None  # Will be set by main window
        
        # Camera mode state
        self.current_mode = 'live'  # Default to 'live' mode
        self.live_camera_btn = None
        self.trigger_camera_btn = None
        self.live_camera_mode = None  # Button for switching to live mode
        self.trigger_camera_mode = None  # Button for switching to trigger mode
        
        # Job control state
        self.job_enabled = False  # Mặc định DISABLE job execution để tránh camera bị đóng băng
        self.job_toggle_btn = None
        
        # Exposure settings state
        self._is_auto_exposure = False  # Bắt đầu với manual mode để user có thể chỉnh exposure
        self._pending_exposure_settings = {}  # Lưu settings chưa apply
        self._instant_apply = True  # Enable instant apply cho better UX
        self.auto_exposure_btn = None
        self.manual_exposure_btn = None
        self.apply_settings_btn = None
        self.cancel_settings_btn = None
        
        # UI state
        self.ui_enabled = False
        
        # AWB controls
        self.auto_awb_btn = None
        self.manual_awb_btn = None
        self.colour_gain_r_edit = None
        self.colour_gain_b_edit = None
        self._is_auto_awb = True
        
    def setup(self, camera_view_widget, exposure_edit,
             gain_edit, ev_edit, focus_bar, fps_num, source_output_combo=None):
        """Thiết lập các tham chiếu đến các widget UI và khởi tạo camera"""
        # Khởi tạo camera stream
        self.camera_stream = CameraStream()
        
        # Khởi tạo camera view với main_window reference
        self.camera_view = CameraView(camera_view_widget, self.main_window)
        self.camera_stream.frame_ready.connect(self.camera_view.display_frame)
        # Rebind frame_ready to route through our handler so we can run the job pipeline
        try:
            self.camera_stream.frame_ready.disconnect(self.camera_view.display_frame)
        except Exception:
            pass
        self.camera_stream.frame_ready.connect(self._on_frame_from_camera)
        
        # Setup source output combo box
        self.source_output_combo = source_output_combo
        if self.source_output_combo:
            print("DEBUG: sourceOutputComboBox found during setup")
            self.setup_source_output_combo()
        else:
            print("DEBUG: sourceOutputComboBox NOT found during setup")
        
        # Reload camera formats after camera stream is initialized
        if self.main_window and hasattr(self.main_window, 'reload_camera_formats'):
            self.main_window.reload_camera_formats()
        
        # Kết nối các widget - đã bỏ gain_slider và ev_slider
        self.exposure_edit = exposure_edit
        self.gain_edit = gain_edit
        self.ev_edit = ev_edit
        self.focus_bar = focus_bar
        self.fps_num = fps_num
        
        # Kết nối signals và slots
        self.camera_view.focus_calculated.connect(self.update_focus_value)
        self.camera_view.fps_updated.connect(self.update_fps_display)
        
        # Tắt hiển thị FPS trên góc hình ảnh preview
        self.camera_view.toggle_fps_display(False)
        
        # Set initial manual exposure mode
        self.set_manual_exposure_mode()
        self.update_exposure_mode_ui()
        
        # Sync initial camera parameters (chỉ khi camera sẵn sàng)
        # self.update_camera_params_from_camera()  # Hoãn lại đến khi camera start
        
        # Khởi tạo mặc định auto exposure
        self.set_auto_exposure_mode()
        
        # Kết nối signal cho các tham số camera
        self.setup_camera_param_signals()
        
        logging.info("CameraManager: Setup completed")
        
        # Disable UI initially
        self.set_ui_enabled(False)
        
    def _on_frame_from_camera(self, frame):
        """Handle frames from camera; run job pipeline when enabled, otherwise show raw.

        Drops incoming frames while processing to keep UI responsive.
        """
        try:
            # If job execution is disabled, just display raw frame
            if not getattr(self, 'job_enabled', False):
                if self.camera_view:
                    self.camera_view.display_frame(frame)
                return

            # Ensure we have a job to run
            job_manager = getattr(self.main_window, 'job_manager', None) if hasattr(self, 'main_window') else None
            current_job = job_manager.get_current_job() if job_manager else None
            if not job_manager or not current_job or not current_job.tools:
                if self.camera_view:
                    self.camera_view.display_frame(frame)
                return

            # Drop frame if a previous one is still being processed
            if getattr(self, '_processing_frame', False):
                return

            self._processing_frame = True
            try:
                processed_image, _ = job_manager.run_current_job(frame)
                if self.camera_view:
                    self.camera_view.display_frame(processed_image if processed_image is not None else frame)
            except Exception as e:
                logging.getLogger(__name__).error(f"Error processing frame in job pipeline: {e}")
                if self.camera_view:
                    self.camera_view.display_frame(frame)
            finally:
                self._processing_frame = False
        except Exception:
            # As a last resort, show the raw frame
            try:
                if self.camera_view:
                    self.camera_view.display_frame(frame)
            except Exception:
                pass

    def stop_camera_for_apply(self):
        """Stop camera before applying Camera Source tool to prevent conflicts"""
        print("DEBUG: CameraManager.stop_camera_for_apply called")
        logging.info("CameraManager: Stopping camera before applying Camera Source tool")
        
        if self.camera_stream and self.camera_stream.is_running():
            print("DEBUG: Stopping camera stream for apply")
            try:
                # Preferred safe stop: cancel pending and stop live
                try:
                    print("DEBUG: [CameraManager] Preferred stop - cancel_and_stop_live()")
                    self.camera_stream.cancel_and_stop_live()
                except AttributeError as e:
                    print(f"DEBUG: [CameraManager] AttributeError cancel_and_stop_live: {e}")
                    if hasattr(self.camera_stream, 'cancel_all_and_flush'):
                        self.camera_stream.cancel_all_and_flush()
                    if hasattr(self.camera_stream, 'stop_live'):
                        self.camera_stream.stop_live()
            except Exception as e:
                print(f"DEBUG: [CameraManager] Error stopping camera: {e}")
            
            # Reset camera mode buttons
            if self.live_camera_btn:
                self.live_camera_btn.setChecked(False)
            if self.trigger_camera_btn:
                self.trigger_camera_btn.setChecked(False)
                
            # Preserve selected mode; if CameraTool available, sync current_mode from it
            try:
                ct = self.find_camera_tool()
                if ct:
                    mode = ct.get_camera_mode()
                    if mode:
                        self.current_mode = mode
            except Exception:
                pass
            self.update_camera_mode_ui()
            
            # Clear camera view display areas
            if self.camera_view:
                self.camera_view.clear_all_areas()
                
            # Refresh source output combo to show updated pipeline
            self.refresh_source_output_combo()
                
            print("DEBUG: Camera stopped for apply - user can now choose source output")
            logging.info("CameraManager: Camera stopped for apply - source output combo refreshed")
            
            return True
        else:
            print("DEBUG: Camera was not running")
            # Still refresh the combo even if camera wasn't running
            self.refresh_source_output_combo()
            return False
        
    def setup_source_output_combo(self):
        """Setup source output combo box with available pipeline outputs"""
        print("DEBUG: setup_source_output_combo called")
        print(f"DEBUG: hasattr(self, 'source_output_combo'): {hasattr(self, 'source_output_combo')}")
        if hasattr(self, 'source_output_combo'):
            print(f"DEBUG: self.source_output_combo value: {self.source_output_combo}")
            print(f"DEBUG: self.source_output_combo type: {type(self.source_output_combo)}")
            print(f"DEBUG: self.source_output_combo is None: {self.source_output_combo is None}")
        
        # Try to find the combo if not already set
        if not hasattr(self, 'source_output_combo') or self.source_output_combo is None:
            print("DEBUG: Trying to find combo via main_window")
            if hasattr(self, 'main_window') and self.main_window:
                combo = self.main_window.findChild(QComboBox, 'sourceOutputComboBox')
                if combo:
                    print("DEBUG: Found sourceOutputComboBox via main_window.findChild")
                    self.source_output_combo = combo
                else:
                    print("DEBUG: sourceOutputComboBox not found via findChild")
                    return
            else:
                print("DEBUG: main_window not available")
                return
        
        if self.source_output_combo is None:
            print("DEBUG: Source output combo is None, skipping setup")
            return
        
        # Check if widget is valid and accessible
        try:
            self.source_output_combo.objectName()
            print("DEBUG: Source output combo is valid and accessible")
        except Exception as e:
            print(f"DEBUG: Source output combo is not accessible: {e}")
            return
            
        print("DEBUG: Source output combo is available, proceeding with setup")
        
        # Clear existing items
        self.source_output_combo.clear()
        
        # Always add Camera Source as the primary source
        self.source_output_combo.addItem("🎥 Camera Source", "camera")
        print("DEBUG: Added Camera Source to combo")
        
        # Add pipeline outputs from current job
        if hasattr(self.main_window, 'job_manager') and self.main_window.job_manager:
            print("DEBUG: Job manager found, checking for current job")
            current_job = self.main_window.job_manager.get_current_job()
            if current_job and current_job.tools:
                print(f"DEBUG: Current job found with {len(current_job.tools)} tools")
                for tool in current_job.tools:
                    tool_name = getattr(tool, 'name', getattr(tool, 'display_name', 'Unknown'))
                    tool_type = type(tool).__name__
                    print(f"DEBUG: Processing tool: {tool_name} (type: {tool_type})")
                    
                    # Add detection tool outputs
                    if tool_type == 'DetectTool' or 'detect' in tool_name.lower():
                        self.source_output_combo.addItem(f"🔍 {tool_name} Output", f"detection_{tool.tool_id}")
                        print(f"DEBUG: Added detection tool: {tool_name}")
                    # Add other tool outputs as needed
                    elif 'edge' in tool_name.lower():
                        self.source_output_combo.addItem(f"📐 {tool_name} Output", f"edge_{tool.tool_id}")
                        print(f"DEBUG: Added edge tool: {tool_name}")
                    elif 'ocr' in tool_name.lower():
                        self.source_output_combo.addItem(f"📝 {tool_name} Output", f"ocr_{tool.tool_id}")
                        print(f"DEBUG: Added OCR tool: {tool_name}")
            else:
                print("DEBUG: No current job or no tools in job")
        else:
            print("DEBUG: Job manager not found or not available")
        
        # Set default to Camera Source
        self.source_output_combo.setCurrentIndex(0)
        
        # Connect signal to handle selection changes
        if hasattr(self.source_output_combo, 'currentTextChanged'):
            try:
                self.source_output_combo.currentTextChanged.disconnect()
            except:
                pass
        self.source_output_combo.currentTextChanged.connect(self.on_source_output_changed)
        
        print(f"DEBUG: Source output combo populated with {self.source_output_combo.count()} items")
        
    def refresh_source_output_combo(self):
        """Refresh the source output combo when job tools change"""
        import traceback
        print("DEBUG: refresh_source_output_combo CALLED!")
        print("DEBUG: Call stack:")
        for line in traceback.format_stack()[-3:]:
            print(f"  {line.strip()}")
        print("DEBUG: Refreshing source output combo")
        print(f"DEBUG: hasattr(self, 'source_output_combo'): {hasattr(self, 'source_output_combo')}")
        if hasattr(self, 'source_output_combo'):
            print(f"DEBUG: self.source_output_combo value: {self.source_output_combo}")
            print(f"DEBUG: self.source_output_combo type: {type(self.source_output_combo)}")
        
        # Setup source output combo if it exists
        if hasattr(self, 'source_output_combo') and self.source_output_combo is not None:
            print("DEBUG: Calling setup_source_output_combo")
            self.setup_source_output_combo()
        else:
            print("DEBUG: Source output combo not available, skipping refresh")
        
    def on_source_output_changed(self, text):
        """Handle source output combo box selection change"""
        print(f"DEBUG: Source output changed to: {text}")
        
        if not self.source_output_combo:
            return
            
        # Get the data associated with the selection
        current_data = self.source_output_combo.currentData()
        print(f"DEBUG: Source output data: {current_data}")
        
        # Handle different pipeline outputs
        if current_data == "camera":
            # Show raw camera feed
            print("DEBUG: Switching to camera source display")
            if hasattr(self.camera_view, 'set_display_mode'):
                self.camera_view.set_display_mode("camera")
        elif current_data and current_data.startswith("detection_"):
            # Show detection results overlay
            print("DEBUG: Switching to detection output display")
            tool_id = current_data.split("_")[1]
            if hasattr(self.camera_view, 'set_display_mode'):
                self.camera_view.set_display_mode("detection", tool_id=tool_id)
        elif current_data and current_data.startswith("edge_"):
            # Show edge detection results
            print("DEBUG: Switching to edge detection display")
            tool_id = current_data.split("_")[1]
            if hasattr(self.camera_view, 'set_display_mode'):
                self.camera_view.set_display_mode("edge", tool_id=tool_id)
        elif current_data and current_data.startswith("ocr_"):
            # Show OCR results overlay
            print("DEBUG: Switching to OCR output display")
            tool_id = current_data.split("_")[1]
            if hasattr(self.camera_view, 'set_display_mode'):
                self.camera_view.set_display_mode("ocr", tool_id=tool_id)
        else:
            # Default to camera source
            print("DEBUG: Unknown source output, defaulting to camera")
            if hasattr(self.camera_view, 'set_display_mode'):
                self.camera_view.set_display_mode("camera")
        
    def setup_camera_buttons(self, live_camera_btn=None, trigger_camera_btn=None, 
                           auto_exposure_btn=None, manual_exposure_btn=None,
                           apply_settings_btn=None, cancel_settings_btn=None,
                           job_toggle_btn=None, live_camera_mode=None, trigger_camera_mode=None,
                           auto_awb_btn=None, manual_awb_btn=None,
                           colour_gain_r_edit=None, colour_gain_b_edit=None):
        """
        Thiết lập các button điều khiển camera và exposure
        
        Args:
            live_camera_btn: Button Live Camera
            trigger_camera_btn: Button Trigger Camera
            auto_exposure_btn: Button Auto Exposure
            manual_exposure_btn: Button Manual Exposure
            apply_settings_btn: Button Apply Settings
            cancel_settings_btn: Button Cancel Settings
            job_toggle_btn: Button Toggle Job Execution
            live_camera_mode: Button Live Camera Mode
            trigger_camera_mode: Button Trigger Camera Mode
        """
        self.live_camera_btn = live_camera_btn
        self.trigger_camera_btn = trigger_camera_btn
        self.auto_exposure_btn = auto_exposure_btn
        self.manual_exposure_btn = manual_exposure_btn
        self.apply_settings_btn = apply_settings_btn
        self.cancel_settings_btn = cancel_settings_btn
        self.job_toggle_btn = job_toggle_btn
        self.live_camera_mode = live_camera_mode
        self.trigger_camera_mode = trigger_camera_mode
        self.auto_awb_btn = auto_awb_btn
        self.manual_awb_btn = manual_awb_btn
        self.colour_gain_r_edit = colour_gain_r_edit
        self.colour_gain_b_edit = colour_gain_b_edit
        
        # Log missing widgets
        missing_widgets = []
        if not self.live_camera_btn:
            missing_widgets.append('liveCamera')
        if not self.trigger_camera_btn:
            missing_widgets.append('triggerCamera')
        if not self.auto_exposure_btn:
            missing_widgets.append('autoExposure')
        if not self.manual_exposure_btn:
            missing_widgets.append('manualExposure')
        if not self.apply_settings_btn:
            missing_widgets.append('applySetting')
        if not self.cancel_settings_btn:
            missing_widgets.append('cancelSetting')
        if not self.job_toggle_btn:
            missing_widgets.append('jobToggle')
        if not self.live_camera_mode:
            missing_widgets.append('liveCameraMode')
        if not self.trigger_camera_mode:
            missing_widgets.append('triggerCameraMode')
            
        if missing_widgets:
            logging.warning(f"Missing UI widgets: {', '.join(missing_widgets)}")
        
        # Kết nối signals
        if self.live_camera_btn:
            self.live_camera_btn.clicked.connect(self.on_live_camera_clicked)
            # Enable the button immediately without requiring Camera Source tool
            self.live_camera_btn.setEnabled(True)
            self.live_camera_btn.setToolTip("Start live camera preview")
            
        if self.trigger_camera_btn:
            self.trigger_camera_btn.clicked.connect(self.on_trigger_camera_clicked)
            # Enable the button immediately without requiring Camera Source tool
            self.trigger_camera_btn.setEnabled(True)
            self.trigger_camera_btn.setToolTip("Trigger single frame capture")
            
        # Connect new camera mode buttons
        if self.live_camera_mode:
            self.live_camera_mode.clicked.connect(self.on_live_camera_mode_clicked)
            # Enable the button immediately without requiring Camera Source tool
            self.live_camera_mode.setEnabled(True)
            self.live_camera_mode.setToolTip("Switch to live camera mode")
            # Ensure live mode is checked by default (following self.current_mode = 'live')
            self.live_camera_mode.setChecked(True)
            
        if self.trigger_camera_mode:
            self.trigger_camera_mode.clicked.connect(self.on_trigger_camera_mode_clicked)
            # Enable the button immediately without requiring Camera Source tool
            self.trigger_camera_mode.setEnabled(True)
            self.trigger_camera_mode.setToolTip("Switch to trigger camera mode")
            # Ensure trigger mode is unchecked by default
            self.trigger_camera_mode.setChecked(False)
            
        if self.auto_exposure_btn:
            self.auto_exposure_btn.clicked.connect(self.on_auto_exposure_clicked)
        if self.manual_exposure_btn:
            self.manual_exposure_btn.clicked.connect(self.on_manual_exposure_clicked)
        # AWB controls
        if self.auto_awb_btn:
            self.auto_awb_btn.clicked.connect(self.on_auto_awb_clicked)
            self.auto_awb_btn.setToolTip("Enable auto white balance")
        if self.manual_awb_btn:
            self.manual_awb_btn.clicked.connect(self.on_manual_awb_clicked)
            self.manual_awb_btn.setToolTip("Enable manual white balance")
        if self.colour_gain_r_edit and hasattr(self.colour_gain_r_edit, 'valueChanged'):
            self.colour_gain_r_edit.valueChanged.connect(self.on_colour_gain_r_changed)
        if self.colour_gain_b_edit and hasattr(self.colour_gain_b_edit, 'valueChanged'):
            self.colour_gain_b_edit.valueChanged.connect(self.on_colour_gain_b_changed)
        if self.apply_settings_btn:
            self.apply_settings_btn.clicked.connect(self.on_apply_settings_clicked)
        if self.cancel_settings_btn:
            self.cancel_settings_btn.clicked.connect(self.on_cancel_settings_clicked)
        if self.job_toggle_btn:
            self.job_toggle_btn.clicked.connect(self.on_job_toggle_clicked)
            
        # Khởi tạo UI state
        self.update_camera_mode_ui()
        self.update_exposure_mode_ui()
        self.update_awb_mode_ui()
        self.update_job_toggle_ui()
        
    def _apply_setting_if_manual(self, setting_type, value):
        """Helper method: Apply setting ngay lập tức nếu đang ở manual mode và instant_apply enabled"""
        if self._instant_apply and not self._is_auto_exposure and self.camera_stream:
            try:
                if setting_type == 'exposure':
                    self.camera_stream.set_exposure(value)
                elif setting_type == 'gain':
                    self.camera_stream.set_gain(value)
                elif setting_type == 'ev':
                    self.camera_stream.set_ev(value)
            except AttributeError:
                # Camera stream không có method này, skip
                pass
    
    def set_instant_apply(self, enabled):
        """Enable/disable instant apply cho exposure settings"""
        self._instant_apply = enabled
        logging.info(f"Instant apply {'enabled' if enabled else 'disabled'}")
        
    def set_ui_enabled(self, enabled):
        """Bật/tắt toàn bộ UI camera"""
        self.ui_enabled = enabled
        
        # Camera buttons
        if self.live_camera_btn:
            self.live_camera_btn.setEnabled(enabled)
        if self.trigger_camera_btn:
            self.trigger_camera_btn.setEnabled(enabled)
        if self.live_camera_mode:
            self.live_camera_mode.setEnabled(enabled)
        if self.trigger_camera_mode:
            self.trigger_camera_mode.setEnabled(enabled)
            
        # Settings controls
        self.set_settings_controls_enabled(enabled and not self._is_auto_exposure)
        # AWB controls
        if hasattr(self, 'set_awb_controls_enabled'):
            self.set_awb_controls_enabled(enabled and not getattr(self, '_is_auto_awb', True))
        
        # Apply/Cancel buttons
        if self.apply_settings_btn:
            self.apply_settings_btn.setEnabled(enabled)
        if self.cancel_settings_btn:
            self.cancel_settings_btn.setEnabled(enabled)
    
    def get_exposure_value(self):
        """Lấy giá trị exposure hiện tại"""
        try:
            if self.exposure_edit:
                return int(self.exposure_edit.text())
            elif self.camera_stream and hasattr(self.camera_stream, 'get_exposure'):
                return self.camera_stream.get_exposure()
            return 0
        except (ValueError, AttributeError):
            logging.error("Failed to get exposure value", exc_info=True)
            return 0
            
    def set_exposure_value(self, value):
        """Đặt giá trị exposure"""
        try:
            value = int(value)
            print(f"DEBUG: [CameraManager] Setting exposure value to {value}")
            # Update UI
            if self.exposure_edit:
                self.exposure_edit.setText(str(value))
            
            # Update camera
            if self.camera_stream and hasattr(self.camera_stream, 'set_exposure'):
                # Try to apply to camera if it's available
                try:
                    success = self.camera_stream.set_exposure(value)
                    if not success:
                        print(f"DEBUG: [CameraManager] Failed to set exposure on camera stream")
                except Exception as e:
                    print(f"DEBUG: [CameraManager] Error setting exposure: {e}")
            
            return True
        except (ValueError, AttributeError) as e:
            print(f"DEBUG: [CameraManager] Error setting exposure value: {e}")
            logging.error(f"Failed to set exposure value: {e}", exc_info=True)
            return False
            
    def get_gain_value(self):
        """Lấy giá trị gain hiện tại"""
        try:
            if self.gain_edit:
                return float(self.gain_edit.text())
            elif self.camera_stream and hasattr(self.camera_stream, 'get_gain'):
                return self.camera_stream.get_gain()
            return 1.0
        except (ValueError, AttributeError):
            logging.error("Failed to get gain value", exc_info=True)
            return 1.0
            
    def set_gain_value(self, value):
        """Đặt giá trị gain"""
        try:
            value = float(value)
            print(f"DEBUG: [CameraManager] Setting gain value to {value}")
            # Update UI
            if self.gain_edit:
                self.gain_edit.setText(str(value))
            
            # Update camera
            if self.camera_stream and hasattr(self.camera_stream, 'set_gain'):
                # Try to apply to camera if it's available
                try:
                    success = self.camera_stream.set_gain(value)
                    if not success:
                        print(f"DEBUG: [CameraManager] Failed to set gain on camera stream")
                except Exception as e:
                    print(f"DEBUG: [CameraManager] Error setting gain: {e}")
            
            return True
        except (ValueError, AttributeError) as e:
            print(f"DEBUG: [CameraManager] Error setting gain value: {e}")
            logging.error(f"Failed to set gain value: {e}", exc_info=True)
            return False
            
    def get_ev_value(self):
        """Lấy giá trị EV hiện tại"""
        try:
            if self.ev_edit:
                return float(self.ev_edit.text())
            elif self.camera_stream and hasattr(self.camera_stream, 'get_ev'):
                return self.camera_stream.get_ev()
            return 0.0
        except (ValueError, AttributeError):
            logging.error("Failed to get EV value", exc_info=True)
            return 0.0
            
    def set_ev_value(self, value):
        """Đặt giá trị EV"""
        try:
            # Handle tuple case (min, max, current)
            if isinstance(value, tuple) and len(value) >= 3:
                print(f"DEBUG: [CameraManager] Received EV tuple: {value}, using value[2]")
                value = value[2]  # Use the current value (third element)
                
            value = float(value)
            print(f"DEBUG: [CameraManager] Setting EV value to {value}")
            
            # Update UI
            if self.ev_edit:
                if hasattr(self.ev_edit, 'setValue'):
                    self.ev_edit.setValue(value)
                else:
                    self.ev_edit.setText(str(value))
            
            # Update camera
            if self.camera_stream and hasattr(self.camera_stream, 'set_ev'):
                # Try to apply to camera if it's available
                try:
                    success = self.camera_stream.set_ev(value)
                    if not success:
                        print(f"DEBUG: [CameraManager] Failed to set EV on camera stream")
                except Exception as e:
                    print(f"DEBUG: [CameraManager] Error setting EV: {e}")
            
            return True
        except (ValueError, AttributeError, TypeError) as e:
            print(f"DEBUG: [CameraManager] Error setting EV value: {e}")
            logging.error(f"Failed to set EV value: {e}", exc_info=True)
            return False
            return False
            
    def is_auto_exposure(self):
        """Kiểm tra xem có đang ở chế độ auto exposure không"""
        return self._is_auto_exposure
        
    def set_settings_controls_enabled(self, enabled):
        """Bật/tắt các control settings (exposure, gain, ev)"""
        if self.exposure_edit:
            self.exposure_edit.setEnabled(enabled)
        if self.gain_edit:
            self.gain_edit.setEnabled(enabled)
        if self.ev_edit:
            self.ev_edit.setEnabled(enabled)
        
    def setup_camera_param_signals(self):
        """Kết nối các signal và slot cho các tham số camera"""
        # Exposure - chỉ dùng edit box
        if self.exposure_edit:
            if hasattr(self.exposure_edit, 'valueChanged'):  # QDoubleSpinBox
                self.exposure_edit.valueChanged.connect(self.on_exposure_edit_changed)
            else:  # QLineEdit fallback
                self.exposure_edit.editingFinished.connect(self.on_exposure_edit_changed)
        # Gain
        if self.gain_edit:
            if hasattr(self.gain_edit, 'valueChanged'):  # QDoubleSpinBox
                self.gain_edit.valueChanged.connect(self.on_gain_edit_changed)
            else:  # QLineEdit fallback
                self.gain_edit.editingFinished.connect(self.on_gain_edit_changed)
        # EV
        if self.ev_edit:
            if hasattr(self.ev_edit, 'valueChanged'):  # QDoubleSpinBox
                self.ev_edit.valueChanged.connect(self.on_ev_edit_changed)
            else:  # QLineEdit fallback
                self.ev_edit.editingFinished.connect(self.on_ev_edit_changed)
            
    def setup_frame_size_spinboxes(self, width_spinbox=None, height_spinbox=None):
        """
        Thiết lập các spinbox để điều chỉnh kích thước frame camera
        
        Args:
            width_spinbox: QSpinBox cho chiều rộng
            height_spinbox: QSpinBox cho chiều cao
        """
        self.width_spinbox = width_spinbox
        self.height_spinbox = height_spinbox
        
        if self.width_spinbox:
            # Cấu hình spinbox chiều rộng
            self.width_spinbox.setMinimum(64)
            self.width_spinbox.setMaximum(1456)
            self.width_spinbox.setValue(1456)  # Giá trị mặc định
            self.width_spinbox.setSuffix(" px")
            self.width_spinbox.valueChanged.connect(self.on_frame_size_changed)
            
        if self.height_spinbox:
            # Cấu hình spinbox chiều cao
            self.height_spinbox.setMinimum(64)
            self.height_spinbox.setMaximum(1088)
            self.height_spinbox.setValue(1088)  # Giá trị mặc định
            self.height_spinbox.setSuffix(" px")
            self.height_spinbox.valueChanged.connect(self.on_frame_size_changed)
    
    def on_frame_size_changed(self):
        """Xử lý khi kích thước frame thay đổi"""
        if self.width_spinbox and self.height_spinbox and self.camera_stream:
            width = self.width_spinbox.value()
            height = self.height_spinbox.value()
            self.camera_stream.set_frame_size(width, height)
    
    def get_frame_size(self):
        """Lấy kích thước frame hiện tại"""
        if self.camera_stream:
            return self.camera_stream.get_frame_size()
        return (1456, 1088)  # Mặc định
    
    def set_frame_size(self, width, height):
        """Đặt kích thước frame và cập nhật UI"""
        # Cập nhật spinboxes
        if self.width_spinbox:
            self.width_spinbox.setValue(width)
        if self.height_spinbox:
            self.height_spinbox.setValue(height)
        
        # Cập nhật camera stream
        if self.camera_stream:
            self.camera_stream.set_frame_size(width, height)
            
    def set_exposure(self, value):
        """Đặt giá trị phơi sáng cho camera"""
        if self.exposure_edit:
            # Hiển thị trực tiếp giá trị microseconds
            if hasattr(self.exposure_edit, 'setValue'):  # QDoubleSpinBox
                self.exposure_edit.setValue(value)
            else:  # QLineEdit fallback
                self.exposure_edit.setText(str(value))
        if hasattr(self.camera_stream, 'set_exposure'):
            self.camera_stream.set_exposure(value)

    def set_gain(self, value):
        """Đặt giá trị gain cho camera"""
        if self.gain_edit:
            if hasattr(self.gain_edit, 'setValue'):  # QDoubleSpinBox
                self.gain_edit.setValue(float(value))
            else:  # QLineEdit fallback
                self.gain_edit.setText(str(value))
        if hasattr(self.camera_stream, 'set_gain'):
            self.camera_stream.set_gain(value)

    def set_ev(self, value):
        """Đặt giá trị EV cho camera"""
        try:
            # Check if value is a tuple and extract current value
            if isinstance(value, tuple) and len(value) >= 3:
                print(f"DEBUG: [CameraManager] Received EV tuple: {value}, using value[2]")
                value = value[2]  # Use the current value (third element)
                
            # Convert to float for UI
            ev_value = float(value)
            
            if self.ev_edit:
                if hasattr(self.ev_edit, 'setValue'):  # QDoubleSpinBox
                    self.ev_edit.setValue(ev_value)
                else:  # QLineEdit fallback
                    self.ev_edit.setText(str(ev_value))
                    
            if hasattr(self.camera_stream, 'set_ev'):
                self.camera_stream.set_ev(ev_value)
                
        except (ValueError, TypeError) as e:
            print(f"DEBUG: [CameraManager] Error in set_ev: {e}")
            # Default to 0.0 if conversion fails
            if self.ev_edit and hasattr(self.ev_edit, 'setValue'):
                self.ev_edit.setValue(0.0)

    def on_exposure_edit_changed(self):
        """Xử lý khi người dùng thay đổi giá trị exposure trong spinbox - chỉ lưu vào pending"""
        print(f"DEBUG: on_exposure_edit_changed called")
        try:
            if self.exposure_edit:
                # Get value from spinbox (microseconds) - không cần convert
                if hasattr(self.exposure_edit, 'value'):  # QDoubleSpinBox
                    value_us = self.exposure_edit.value()
                else:  # QLineEdit fallback
                    value_us = float(self.exposure_edit.text())
                
                print(f"DEBUG: New exposure value: {value_us} μs")
                print(f"DEBUG: Manual mode: {not self._is_auto_exposure}")
                
                # Lưu trực tiếp giá trị microseconds vào pending settings
                self._pending_exposure_settings['exposure'] = value_us
                print(f"DEBUG: Saved to pending settings")

                # Instant apply: áp dụng ngay khi ở manual mode để người dùng thấy hiệu ứng tức thời
                # Chỉ apply khi _instant_apply bật và không ở auto-exposure
                try:
                    self._apply_setting_if_manual('exposure', value_us)
                    print("DEBUG: Instant-applied exposure to camera (manual mode)")
                except Exception as e:
                    print(f"DEBUG: Failed instant apply exposure: {e}")
                
                # Notify settings manager about the change for synchronization
                if self.settings_manager:
                    self.settings_manager.mark_page_changed('camera')
                    # Optionally trigger immediate sync
                    # self.settings_manager.sync_settings_across_pages()
                
        except (ValueError, AttributeError) as e:
            print(f"DEBUG: Error in exposure edit changed: {e}")
    
    def set_settings_manager(self, settings_manager):
        """Set reference to settings manager for synchronization"""
        self.settings_manager = settings_manager
        print(f"DEBUG: CameraManager linked to SettingsManager")

    def on_gain_edit_changed(self, value=None):
        """Xử lý khi người dùng thay đổi giá trị gain"""
        try:
            if self.gain_edit:
                if value is None:
                    # Trường hợp editingFinished (QLineEdit)
                    value = float(self.gain_edit.text())
                # value đã được truyền trực tiếp nếu sự kiện là valueChanged (QDoubleSpinBox)
                
                if hasattr(self.camera_stream, 'set_gain'):
                    self.camera_stream.set_gain(value)
        except (ValueError, AttributeError):
            pass

    def on_ev_edit_changed(self, value=None):
        """Xử lý khi người dùng thay đổi giá trị EV"""
        try:
            if self.ev_edit:
                if value is None:
                    # Trường hợp editingFinished (QLineEdit)
                    value = float(self.ev_edit.text())
                # value đã được truyền trực tiếp nếu sự kiện là valueChanged (QDoubleSpinBox)
                
                if hasattr(self.camera_stream, 'set_ev'):
                    self.camera_stream.set_ev(value)
        except (ValueError, AttributeError):
            pass

    def update_camera_params_from_camera(self):
        """Cập nhật các tham số từ camera hiện tại"""
        if not self.camera_stream:
            return
            
        # Lấy giá trị thực tế từ camera nếu có API
        if hasattr(self.camera_stream, 'get_exposure'):
            exposure = self.camera_stream.get_exposure()
            print(f"DEBUG: Got exposure from camera: {exposure}")
            if exposure:  # Chỉ update nếu có giá trị hợp lệ
                if self.exposure_edit:
                    if hasattr(self.exposure_edit, 'setValue'):
                        self.exposure_edit.setValue(float(exposure))
                        print(f"DEBUG: Set exposure in UI: {exposure}")
                    else:
                        self.exposure_edit.setText(str(exposure))
                        
        if hasattr(self.camera_stream, 'get_gain'):
            try:
                gain = self.camera_stream.get_gain()
                print(f"DEBUG: Got gain from camera: {gain}")
                if gain is not None:
                    self.set_gain(gain)
            except Exception as e:
                print(f"DEBUG: [CameraManager] Error getting gain: {e}")
                
        if hasattr(self.camera_stream, 'get_ev'):
            try:
                ev = self.camera_stream.get_ev()
                print(f"DEBUG: Got EV from camera: {ev}")
                if ev is not None:
                    self.set_ev(ev)
            except Exception as e:
                print(f"DEBUG: [CameraManager] Error getting/setting EV: {e}")
            
    def _show_camera_error(self, message):
        """Show camera error message to user"""
        try:
            from PyQt5.QtWidgets import QMessageBox
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("Camera Error")
            msg_box.setText(f"Camera Error: {message}")
            msg_box.setInformativeText("Please check camera connection and try again.")
            msg_box.exec_()
        except Exception as e:
            print(f"DEBUG: [CameraManager] Error showing message box: {e}")
    
    def toggle_live_camera(self, checked):
        """Bật/tắt chế độ camera trực tiếp"""
        print(f"DEBUG: [CameraManager] toggle_live_camera called with checked={checked}")
        
        # Bỏ qua kiểm tra Camera Source để cho phép xem trực tiếp 
        # mà không cần thêm vào source trước
        # Người dùng có thể xem trước hình ảnh từ camera trước khi thêm vào pipeline
        
        if not self.camera_stream:
            print("DEBUG: [CameraManager] No camera stream available")
            return False
            
        try:
            if checked:
                print("DEBUG: [CameraManager] Starting live camera...")
                
                # Process pending events to keep UI responsive
                QApplication.processEvents()
                
                # Try with both method names for compatibility
                success = False
                try:
                    # First try direct method access - this helps with finding the true error
                    try:
                        print("DEBUG: [CameraManager] First attempt - direct start_live()")
                        success = self.camera_stream.start_live()
                    except AttributeError as e:
                        print(f"DEBUG: [CameraManager] AttributeError: {e}")
                        # Fall back to other method name
                        print("DEBUG: [CameraManager] Falling back to start_live_camera()")
                        try:
                            success = self.camera_stream.start_live_camera()
                        except AttributeError:
                            # Implement method directly if needed
                            print("DEBUG: [CameraManager] Both methods missing - implementing inline")
                            success = self._implement_start_live()
                except Exception as e:
                    print(f"DEBUG: [CameraManager] Error starting camera: {e}")
                    success = False
                
                # Process events again after camera start
                QApplication.processEvents()
                
                if success:
                    print("DEBUG: [CameraManager] Live camera started successfully")
                    # Sync camera params sau một chút delay để camera start hoàn toàn
                    from PyQt5.QtCore import QTimer
                    # Thử sync multiple times để đảm bảo camera đã sẵn sàng
                    QTimer.singleShot(1000, self.update_camera_params_from_camera)  # 1s delay
                    QTimer.singleShot(2000, self.update_camera_params_from_camera)  # retry sau 2s
                    return True
                else:
                    print("DEBUG: [CameraManager] Failed to start live camera")
                    # Show error to user
                    self._show_camera_error("Failed to start live preview")
                    # Update UI to reflect failure
                    self.current_mode = None
                    self.update_camera_mode_ui()
                    return False
            else:
                print("DEBUG: [CameraManager] Stopping live camera...")
                
                # Process events before stop
                QApplication.processEvents()
                
                try:
                    # Preferred safe stop
                    try:
                        print("DEBUG: [CameraManager] Preferred stop - cancel_and_stop_live()")
                        self.camera_stream.cancel_and_stop_live()
                    except AttributeError as e:
                        print(f"DEBUG: [CameraManager] AttributeError cancel_and_stop_live: {e}")
                        if hasattr(self.camera_stream, 'cancel_all_and_flush'):
                            self.camera_stream.cancel_all_and_flush()
                        if hasattr(self.camera_stream, 'stop_live'):
                            self.camera_stream.stop_live()
                except Exception as e:
                    print(f"DEBUG: [CameraManager] Error stopping camera: {e}")
                
                # Process events after stop to ensure UI updates
                QApplication.processEvents()
                
                print("DEBUG: [CameraManager] Live camera stopped")
                return True
                
        except Exception as e:
            print(f"DEBUG: [CameraManager] Error in toggle_live_camera: {e}")
            # Show error to user
            self._show_camera_error(f"Camera operation failed: {str(e)}")
            # Reset state on error
            self.current_mode = None
            self.update_camera_mode_ui()
            return False
            
    def set_auto_exposure_mode(self):
        """Đặt chế độ tự động phơi sáng"""
        self._is_auto_exposure = True
        if hasattr(self.camera_stream, 'set_auto_exposure'):
            self.camera_stream.set_auto_exposure(True)
        
        # Disable các widget điều chỉnh phơi sáng
        if self.exposure_edit:
            self.exposure_edit.setEnabled(False)
        if self.gain_edit:
            self.gain_edit.setEnabled(False)
        if self.ev_edit:
            self.ev_edit.setEnabled(False)
        if self.ev_edit:
            self.ev_edit.setEnabled(False)
            
    def set_manual_exposure_mode(self):
        """Đặt chế độ phơi sáng thủ công"""
        self._is_auto_exposure = False
        if hasattr(self.camera_stream, 'set_auto_exposure'):
            self.camera_stream.set_auto_exposure(False)
            print("DEBUG: Set camera auto exposure to False")
        
        # Enable các widget điều chỉnh phơi sáng
        if self.exposure_edit:
            self.exposure_edit.setEnabled(True)
            print("DEBUG: Enabled exposure_edit")
        if self.gain_edit:
            self.gain_edit.setEnabled(True)
        if self.ev_edit:
            self.ev_edit.setEnabled(True)
            
        print(f"DEBUG: Manual exposure mode set, _is_auto_exposure = {self._is_auto_exposure}")
            
    @pyqtSlot(int)
    def update_focus_value(self, value):
        """Cập nhật giá trị độ sắc nét trên thanh focusBar"""
        if self.focus_bar:
            self.focus_bar.setValue(value)
        
    @pyqtSlot(float)
    def update_fps_display(self, fps_value):
        """Cập nhật giá trị FPS lên LCD display"""
        if self.fps_num:
            self.fps_num.display(f"{fps_value:.1f}")
            
    def trigger_capture(self):
        """Kích hoạt chụp ảnh không đồng bộ"""
        # Bỏ qua kiểm tra Camera Source để cho phép chụp ảnh
        # mà không cần thêm vào source trước
        # Người dùng có thể chụp ảnh trước khi thêm Camera Source vào pipeline
            
        if self.camera_stream:
            print("DEBUG: [CameraManager] Triggering capture asynchronously...")
            
            # Visual feedback - temporarily change button text
            if self.trigger_camera_btn and self.current_mode == 'trigger':
                original_text = self.trigger_camera_btn.text()
                self.trigger_camera_btn.setText("Capturing...")
                
                # Button vẫn enabled để user có thể nhấn Cancel nếu muốn
                # Chỉ disable nếu đang xử lý capture đồng bộ
                # self.trigger_camera_btn.setEnabled(False)
                
                # Không còn chuyển sang trigger mode nữa
                # Giữ nguyên chế độ hiện tại (live hoặc trigger)
                print(f"DEBUG: [CameraManager] Capturing in current mode: {self.current_mode}")
                
                # Apply job setting to camera stream
                if hasattr(self.camera_stream, 'set_job_enabled'):
                    self.camera_stream.set_job_enabled(self.job_enabled)
                
                # Sync current exposure setting before trigger
                self.sync_exposure_to_camera()
                
                # Trigger actual capture asynchronously - không block UI
                if hasattr(self.camera_stream, 'trigger_capture_async'):
                    success = self.camera_stream.trigger_capture_async()
                    if not success:
                        print("DEBUG: [CameraManager] Failed to start async trigger")
                        # Fallback to synchronous capture if async failed
                        if hasattr(self.camera_stream, 'trigger_capture'):
                            try:
                                self.camera_stream.trigger_capture()
                            except Exception as e:
                                print(f"DEBUG: [CameraManager] Error in synchronous trigger_capture: {e}")
                                self._show_camera_error(f"Error capturing image: {str(e)}")
                        else:
                            print("DEBUG: [CameraManager] No trigger_capture method available")
                            self._show_camera_error("Camera trigger feature is not available. Please update the camera module.")
                else:
                    # Fallback to old synchronous method if async not available
                    print("DEBUG: [CameraManager] Async trigger not available, using sync")
                    if hasattr(self.camera_stream, 'trigger_capture'):
                        try:
                            self.camera_stream.trigger_capture()
                        except Exception as e:
                            print(f"DEBUG: [CameraManager] Error in synchronous trigger_capture: {e}")
                            self._show_camera_error(f"Error capturing image: {str(e)}")
                    else:
                        print("DEBUG: [CameraManager] No trigger_capture method available")
                        self._show_camera_error("Camera trigger feature is not available. Please update the camera module.")
                
                # Restore button after timeout nếu không có phản hồi
                from PyQt5.QtCore import QTimer
                def restore_button():
                    if self.trigger_camera_btn and self.trigger_camera_btn.text() == "Capturing...":
                        self.trigger_camera_btn.setText(original_text)
                        if self.current_mode == 'trigger':
                            self.trigger_camera_btn.setEnabled(True)
                
                # Set timeout dài hơn (10 giây) để cho phép có thời gian chờ trigger
                QTimer.singleShot(10000, restore_button)
            else:
                # Direct trigger without UI feedback
                if hasattr(self.camera_stream, 'trigger_capture_async'):
                    try:
                        self.camera_stream.trigger_capture_async()
                    except Exception as e:
                        print(f"DEBUG: [CameraManager] Error in async trigger: {e}")
                        self._show_camera_error(f"Error capturing image: {str(e)}")
                elif hasattr(self.camera_stream, 'trigger_capture'):
                    try:
                        self.camera_stream.trigger_capture()
                    except Exception as e:
                        print(f"DEBUG: [CameraManager] Error in direct trigger: {e}")
                        self._show_camera_error(f"Error capturing image: {str(e)}")
                else:
                    print("DEBUG: [CameraManager] No trigger methods available")
                    self._show_camera_error("Camera trigger feature is not available. Please update the camera module.")
        else:
            print("DEBUG: [CameraManager] No camera stream available")
            self._show_camera_error("Camera is not available. Please check camera connection.")

    def sync_exposure_to_camera(self):
        """Đồng bộ hóa các thông số exposure hiện tại từ UI vào camera"""
        print("DEBUG: [CameraManager] Syncing exposure settings to camera")
        try:
            # Lấy giá trị exposure từ UI
            if self.exposure_edit:
                try:
                    if hasattr(self.exposure_edit, 'value'):
                        exposure_value = self.exposure_edit.value()
                    else:
                        exposure_value = int(self.exposure_edit.text())
                    
                    print(f"DEBUG: [CameraManager] Syncing exposure value: {exposure_value}")
                    if hasattr(self.camera_stream, 'set_exposure'):
                        self.camera_stream.set_exposure(exposure_value)
                except (ValueError, AttributeError) as e:
                    print(f"DEBUG: [CameraManager] Error getting exposure value from UI: {e}")
            
            # Lấy giá trị gain từ UI
            if self.gain_edit:
                try:
                    if hasattr(self.gain_edit, 'value'):
                        gain_value = self.gain_edit.value()
                    else:
                        gain_value = float(self.gain_edit.text())
                    
                    print(f"DEBUG: [CameraManager] Syncing gain value: {gain_value}")
                    if hasattr(self.camera_stream, 'set_gain'):
                        self.camera_stream.set_gain(gain_value)
                except (ValueError, AttributeError) as e:
                    print(f"DEBUG: [CameraManager] Error getting gain value from UI: {e}")
            
            # Lấy giá trị EV từ UI
            if self.ev_edit:
                try:
                    if hasattr(self.ev_edit, 'value'):
                        ev_value = self.ev_edit.value()
                    else:
                        ev_value = float(self.ev_edit.text())
                    
                    print(f"DEBUG: [CameraManager] Syncing EV value: {ev_value}")
                    if hasattr(self.camera_stream, 'set_ev'):
                        self.camera_stream.set_ev(ev_value)
                except (ValueError, AttributeError) as e:
                    print(f"DEBUG: [CameraManager] Error getting EV value from UI: {e}")
            
            # Đồng bộ chế độ auto exposure
            if hasattr(self.camera_stream, 'set_auto_exposure'):
                print(f"DEBUG: [CameraManager] Syncing auto exposure: {self._is_auto_exposure}")
                self.camera_stream.set_auto_exposure(self._is_auto_exposure)
                
            return True
        except Exception as e:
            print(f"DEBUG: [CameraManager] Error syncing exposure settings: {e}")
            return False

    def set_trigger_mode(self, enabled):
        """
        Set trigger mode in camera
        
        Args:
            enabled: True to enable trigger mode, False to disable
        
        Returns:
            True if successful, False otherwise
        """
        print(f"DEBUG: [CameraManager] set_trigger_mode called with enabled={enabled}")
        try:
            # Sync current exposure setting to camera before changing trigger mode
            if self.camera_stream and self.exposure_edit:
                try:
                    exposure_value = self.get_exposure_value()
                    print(f"DEBUG: [CameraManager] Syncing exposure {exposure_value} before setting trigger mode")
                    self.camera_stream.set_exposure(exposure_value)
                except Exception as e:
                    print(f"DEBUG: [CameraManager] Error syncing exposure: {e}")
            
            # Update UI first
            if enabled:
                # Update mode tracking
                self.current_mode = 'trigger'
                
                # Update UI buttons
                if self.trigger_camera_btn:
                    self.trigger_camera_btn.setChecked(True)
                if self.live_camera_btn:
                    self.live_camera_btn.setChecked(False)
                    
                # Update mode buttons
                if self.trigger_camera_mode:
                    self.trigger_camera_mode.setChecked(True)
                if self.live_camera_mode:
                    self.live_camera_mode.setChecked(False)
            else:
                # Update mode tracking
                self.current_mode = 'live'
                
                # Update UI buttons
                if self.trigger_camera_btn:
                    self.trigger_camera_btn.setChecked(False)
                if self.live_camera_btn:
                    self.live_camera_btn.setChecked(True)
                    
                # Update mode buttons
                if self.trigger_camera_mode:
                    self.trigger_camera_mode.setChecked(False)
                if self.live_camera_mode:
                    self.live_camera_mode.setChecked(True)
            
            # Update camera hardware
            if self.camera_stream and hasattr(self.camera_stream, 'set_trigger_mode'):
                print(f"DEBUG: [CameraManager] Setting camera hardware trigger mode to {enabled}")
                success = self.camera_stream.set_trigger_mode(enabled)
                if not success:
                    print(f"DEBUG: [CameraManager] Failed to set trigger mode")
                    return False
            
            # Do not auto-start camera; only enforce hardware mode
            # (Startup should set mode without starting preview)
                
            self.update_camera_mode_ui()
            return True
        except Exception as e:
            print(f"DEBUG: [CameraManager] Error in set_trigger_mode: {e}")
            return False
            
    def rotate_left(self):
        """Xoay camera sang trái"""
        if self.camera_view:
            self.camera_view.rotate_left()
            
    def rotate_right(self):
        """Xoay camera sang phải"""
        if self.camera_view:
            self.camera_view.rotate_right()
            
    def zoom_in(self):
        """Phóng to"""
        if self.camera_view:
            self.camera_view.zoom_in()
            
    def zoom_out(self):
        """Thu nhỏ"""
        if self.camera_view:
            self.camera_view.zoom_out()
            
    def handle_resize_event(self):
        """Xử lý sự kiện khi cửa sổ thay đổi kích thước"""
        if self.camera_view:
            self.camera_view.handle_resize_event()
    
    # ============ CAMERA MODE HANDLERS ============
    
    def start_live_camera(self):
        """Start live camera mode (for programmatic access)"""
        print("DEBUG: [CameraManager] start_live_camera called")
        
        # Kiểm tra xem có đang ở chế độ trigger hay không
        trigger_mode = False
        if hasattr(self, 'current_mode') and self.current_mode == 'trigger':
            trigger_mode = True
        elif hasattr(self, 'trigger_camera_mode') and self.trigger_camera_mode and self.trigger_camera_mode.isChecked():
            trigger_mode = True
            
        if trigger_mode:
            print("DEBUG: [CameraManager] Using trigger mode based on current settings")
            # Sử dụng hàm on_live_camera_clicked để giữ nguyên chế độ trigger
            if hasattr(self, 'live_camera_btn') and self.live_camera_btn:
                # Đặt trạng thái checked để on_live_camera_clicked biết đang bật camera
                self.live_camera_btn.setChecked(True)
                self.on_live_camera_clicked()
                return True
        
        # Tiếp tục với chế độ live nếu không phải chế độ trigger
        if self.camera_stream and not self.camera_stream.is_running():
            try:
                success = self.camera_stream.start_live()
                if success:
                    # Đảm bảo chế độ hiện tại và UI được đồng bộ
                    self.current_mode = 'live'
                    
                    # Đảm bảo các nút chế độ camera được cập nhật đúng
                    if self.live_camera_mode:
                        self.live_camera_mode.blockSignals(True)
                        self.live_camera_mode.setChecked(True)
                        self.live_camera_mode.blockSignals(False)
                    if self.trigger_camera_mode:
                        self.trigger_camera_mode.blockSignals(True)
                        self.trigger_camera_mode.setChecked(False)
                        self.trigger_camera_mode.blockSignals(False)
                    
                    # Cập nhật UI
                    self.update_camera_mode_ui()
                    
                    # Refresh source output combo to show current pipeline
                    self.refresh_source_output_combo()
                    
                    # Apply current source output mode if set
                    current_data = self.source_output_combo.currentData() if self.source_output_combo else "camera"
                    if hasattr(self.camera_view, 'set_display_mode'):
                        tool_id = None
                        if current_data and "_" in str(current_data):
                            parts = str(current_data).split("_")
                            if len(parts) > 1:
                                tool_id = parts[1]
                        self.camera_view.set_display_mode(current_data, tool_id)
                        
                    print("DEBUG: [CameraManager] Live camera started successfully with display mode:", current_data)
                    return True
                else:
                    print("DEBUG: [CameraManager] Failed to start live camera")
                    return False
            except Exception as e:
                print(f"DEBUG: [CameraManager] Exception starting live camera: {e}")
                return False
        else:
            print("DEBUG: [CameraManager] Camera stream not available or already running")
            return False
    
    def on_live_camera_clicked(self):
        """Xử lý khi click Live Camera button (onlineCamera)"""
        current_checked = self.live_camera_btn.isChecked() if self.live_camera_btn else True
        print(f"DEBUG: [CameraManager] Live camera button clicked, checked: {current_checked}, current_mode: {self.current_mode}")
        
        if current_checked:
            # Button được click để bật camera
            print(f"DEBUG: [CameraManager] Starting camera in mode: {self.current_mode or 'default'}")
            
            # Hành vi khác nhau dựa vào chế độ hiện tại
            if self.current_mode == 'trigger' or (self.trigger_camera_mode and self.trigger_camera_mode.isChecked()):
                # Chế độ trigger - bật camera trong chế độ đợi external trigger
                print("DEBUG: [CameraManager] Starting camera in TRIGGER mode")
                
                # Đảm bảo hardware được thiết lập đúng ở chế độ trigger
                if self.camera_stream and hasattr(self.camera_stream, 'set_trigger_mode'):
                    print("DEBUG: [CameraManager] Setting hardware to trigger mode")
                    self.camera_stream.set_trigger_mode(True)
                    
                # Thiết lập chế độ trigger ngay cả khi không phải đang ở chế độ đó
                self.current_mode = 'trigger'
                
                # Bắt đầu camera trong chế độ STILL/TRIGGER
                success = self._implement_start_trigger()
                if not success:
                    print("DEBUG: [CameraManager] Failed to start camera in trigger mode")
                    self.current_mode = None
                    # Uncheck button if failed
                    if self.live_camera_btn:
                        self.live_camera_btn.setChecked(False)
            else:
                # Chế độ live mặc định hoặc đã được chọn
                print("DEBUG: [CameraManager] Starting camera in LIVE mode")
                
                # Set hardware to live mode
                if self.camera_stream and hasattr(self.camera_stream, 'set_trigger_mode'):
                    print("DEBUG: [CameraManager] Setting hardware to live mode")
                    self.camera_stream.set_trigger_mode(False)
                
                # Refresh source output combo before starting
                print("DEBUG: [CameraManager] Refreshing source output combo before live start")
                self.refresh_source_output_combo()
                    
                success = self.toggle_live_camera(True)
                if success:
                    self.current_mode = 'live'
                else:
                    print("DEBUG: [CameraManager] Failed to start live mode")
                    self.current_mode = None
                    # Uncheck button if failed
                    if self.live_camera_btn:
                        self.live_camera_btn.setChecked(False)
        else:
            # Button được click để tắt camera
            print("DEBUG: [CameraManager] Stopping camera")
            
            # Dừng camera bất kể chế độ nào
            if self.current_mode == 'trigger':
                # Nếu đang ở chế độ trigger, dừng camera theo cách phù hợp
                success = self._implement_stop_trigger()
            else:
                # Nếu ở chế độ live hoặc không xác định, dùng phương thức thông thường
                success = self.toggle_live_camera(False)
                
            if success:
                self.current_mode = None
            # Keep button unchecked regardless
        
        # Update UI to reflect current state
        self.update_camera_mode_ui()
    
    def on_trigger_camera_clicked(self):
        """Xử lý khi click Trigger Camera button - chỉ chụp ảnh một lần"""
        print("DEBUG: [CameraManager] Trigger camera button clicked - capturing single image")
        
        # Không chuyển đổi chế độ nữa, chỉ kích hoạt chụp ảnh
        if self.camera_stream:
            # Đảm bảo camera đã sẵn sàng
            if self.current_mode == 'live':
                print("DEBUG: [CameraManager] Live mode active, will capture while keeping live view")
                # Không tắt live, chỉ capture trong chế độ live
            elif self.current_mode == 'trigger':
                print("DEBUG: [CameraManager] Trigger mode active, capturing image")
            else:
                print("DEBUG: [CameraManager] No active mode, attempting to capture anyway")
            
            # Capture ảnh - không thiết lập trigger mode tạm thời nữa
            print("DEBUG: Triggering single capture...")
            # Kiểm tra xem trigger_capture có tồn tại không
            if hasattr(self.camera_stream, 'trigger_capture'):
                try:
                    self.camera_stream.trigger_capture()
                    print("DEBUG: [CameraManager] Capture triggered successfully")
                except Exception as e:
                    print(f"DEBUG: [CameraManager] Error triggering capture: {e}")
                    self._show_camera_error(f"Error triggering capture: {str(e)}")
            else:
                print("DEBUG: [CameraManager] trigger_capture method not available in camera_stream")
                self._show_camera_error("Camera trigger feature is not available. Please update the camera module.")
        else:
            print("DEBUG: [CameraManager] No camera stream available")
            self._show_camera_error("Camera is not available for capture. Please check connection.")
        
        # Không thay đổi giao diện người dùng, chỉ gọi update để làm mới UI nếu cần
        self.update_camera_mode_ui()
    
    def update_camera_mode_ui(self):
        """Cập nhật UI theo camera mode hiện tại - sync with CameraTool"""
        # Get current mode from CameraTool if available
        camera_tool = self.find_camera_tool()
        if camera_tool:
            current_mode = camera_tool.get_camera_mode()
            print(f"DEBUG: [CameraManager] Updating UI for mode from CameraTool: {current_mode}")
        else:
            # Fallback to local mode with default
            if self.current_mode is None:
                self.current_mode = 'live'
            current_mode = self.current_mode
            print(f"DEBUG: [CameraManager] Using local mode (no CameraTool): {current_mode}")
        
        is_camera_running = self.live_camera_btn and self.live_camera_btn.isChecked()
        print(f"DEBUG: [CameraManager] Camera is running: {is_camera_running}")
        
        if self.live_camera_btn and self.trigger_camera_btn:
            if current_mode == 'live':
                # Block signals to prevent recursive calls
                self.live_camera_btn.blockSignals(True)
                # Update live camera button state based on whether it's running
                if is_camera_running:
                    self.live_camera_btn.setChecked(True)
                    self.live_camera_btn.setText("Stop Camera")
                    self.live_camera_btn.setStyleSheet("background-color: #ff6b6b")  # Red
                else:
                    self.live_camera_btn.setChecked(False)
                    self.live_camera_btn.setText("Start Camera")
                    self.live_camera_btn.setStyleSheet("")
                self.live_camera_btn.setEnabled(True)  # Always enabled in live mode
                self.live_camera_btn.blockSignals(False)
                
                # Trigger camera button - always enabled in live mode for capturing photos
                self.trigger_camera_btn.setEnabled(True)
                self.trigger_camera_btn.setText("Capture Photo")
                self.trigger_camera_btn.setStyleSheet("")
                
                # Update mode buttons
                if self.live_camera_mode:
                    self.live_camera_mode.blockSignals(True)
                    self.live_camera_mode.setChecked(True)
                    self.live_camera_mode.setStyleSheet("background-color: #ffd43b")  # Yellow selected
                    self.live_camera_mode.blockSignals(False)
                if self.trigger_camera_mode:
                    self.trigger_camera_mode.blockSignals(True)
                    self.trigger_camera_mode.setChecked(False)
                    self.trigger_camera_mode.setStyleSheet("")
                    self.trigger_camera_mode.blockSignals(False)
                    
            elif current_mode == 'trigger':
                # Trigger mode UI
                self.trigger_camera_btn.setEnabled(True)  # Always enabled in trigger mode
                self.trigger_camera_btn.setText("Trigger Capture")
                self.trigger_camera_btn.setStyleSheet("background-color: #ffa62b")  # Orange
                
                # Live camera button state depends on if camera is running
                self.live_camera_btn.blockSignals(True)
                if is_camera_running:
                    self.live_camera_btn.setChecked(True)
                    self.live_camera_btn.setText("Stop Camera")
                    self.live_camera_btn.setStyleSheet("background-color: #ff6b6b")  # Red
                else:
                    self.live_camera_btn.setChecked(False)
                    self.live_camera_btn.setText("Wait For Trigger")
                    self.live_camera_btn.setStyleSheet("")
                self.live_camera_btn.setEnabled(True)  # Always enabled
                self.live_camera_btn.blockSignals(False)
                
                # Update mode buttons
                if self.live_camera_mode:
                    self.live_camera_mode.blockSignals(True)
                    self.live_camera_mode.setChecked(False)
                    self.live_camera_mode.setStyleSheet("")
                    self.live_camera_mode.blockSignals(False)
                if self.trigger_camera_mode:
                    self.trigger_camera_mode.blockSignals(True)
                    self.trigger_camera_mode.setChecked(True)
                    self.trigger_camera_mode.setStyleSheet("background-color: #ffd43b")  # Yellow selected
                    self.trigger_camera_mode.blockSignals(False)
            else:
                # No specific mode or camera stopped
                self.live_camera_btn.blockSignals(True)
                self.live_camera_btn.setChecked(False)
                self.live_camera_btn.setText("Start Camera")
                self.live_camera_btn.setStyleSheet("")
                self.live_camera_btn.setEnabled(True)
                self.live_camera_btn.blockSignals(False)
                
                self.trigger_camera_btn.setEnabled(False)  # Disabled when no camera running
                self.trigger_camera_btn.setText("Capture Photo")
                self.trigger_camera_btn.setStyleSheet("")
                
                # Default to live mode button checked
                if self.live_camera_mode:
                    self.live_camera_mode.blockSignals(True)
                    self.live_camera_mode.setChecked(True)
                    self.live_camera_mode.setStyleSheet("")
                    self.live_camera_mode.blockSignals(False)
                if self.trigger_camera_mode:
                    self.trigger_camera_mode.blockSignals(True)
                    self.trigger_camera_mode.setChecked(False)
                    self.trigger_camera_mode.setStyleSheet("")
                    self.trigger_camera_mode.blockSignals(False)

        # Always reflect mode selection color on mode buttons even if camera start/stop buttons are missing
        try:
            if current_mode == 'live':
                if self.live_camera_mode:
                    self.live_camera_mode.blockSignals(True)
                    self.live_camera_mode.setChecked(True)
                    self.live_camera_mode.setStyleSheet("background-color: #ffd43b")
                    self.live_camera_mode.blockSignals(False)
                if self.trigger_camera_mode:
                    self.trigger_camera_mode.blockSignals(True)
                    self.trigger_camera_mode.setChecked(False)
                    self.trigger_camera_mode.setStyleSheet("")
                    self.trigger_camera_mode.blockSignals(False)
            elif current_mode == 'trigger':
                if self.live_camera_mode:
                    self.live_camera_mode.blockSignals(True)
                    self.live_camera_mode.setChecked(False)
                    self.live_camera_mode.setStyleSheet("")
                    self.live_camera_mode.blockSignals(False)
                if self.trigger_camera_mode:
                    self.trigger_camera_mode.blockSignals(True)
                    self.trigger_camera_mode.setChecked(True)
                    self.trigger_camera_mode.setStyleSheet("background-color: #ffd43b")
                    self.trigger_camera_mode.blockSignals(False)
            else:
                # Default/no mode: highlight live as default
                if self.live_camera_mode:
                    self.live_camera_mode.blockSignals(True)
                    self.live_camera_mode.setChecked(True)
                    self.live_camera_mode.setStyleSheet("background-color: #ffd43b")
                    self.live_camera_mode.blockSignals(False)
                if self.trigger_camera_mode:
                    self.trigger_camera_mode.blockSignals(True)
                    self.trigger_camera_mode.setChecked(False)
                    self.trigger_camera_mode.setStyleSheet("")
                    self.trigger_camera_mode.blockSignals(False)
        except Exception:
            pass
    
    def on_live_camera_mode_clicked(self):
        """Xử lý khi click Live Camera Mode button - delegate to CameraTool"""
        print("DEBUG: [CameraManager] Live camera mode button clicked")
        
        # Find the Camera Source tool and delegate mode change to it
        camera_tool = self.find_camera_tool()
        if camera_tool:
            print("DEBUG: [CameraManager] Found Camera Source tool, delegating mode change")
            success = camera_tool.set_camera_mode("live")
            if success:
                print("DEBUG: [CameraManager] Live mode set successfully via CameraTool")
            else:
                print("DEBUG: [CameraManager] Failed to set live mode via CameraTool")
        else:
            # Fallback: handle mode change directly if no Camera Source tool found
            print("DEBUG: [CameraManager] No Camera Source tool found, handling mode change directly")
            self._handle_live_mode_directly()

        # Ensure mutual exclusivity like AE/Manual buttons
        if self.live_camera_mode:
            try:
                self.live_camera_mode.blockSignals(True)
                self.live_camera_mode.setChecked(True)
            finally:
                self.live_camera_mode.blockSignals(False)
        if self.trigger_camera_mode:
            try:
                self.trigger_camera_mode.blockSignals(True)
                self.trigger_camera_mode.setChecked(False)
            finally:
                self.trigger_camera_mode.blockSignals(False)

        # When switching back to live mode, revert 3A to Auto
        try:
            # AE back to auto
            self._is_auto_exposure = True
            self.set_auto_exposure_mode()
            self.update_exposure_mode_ui()
        except Exception as e:
            print(f"DEBUG: [CameraManager] Error forcing auto AE on live mode: {e}")

        try:
            # AWB back to auto
            self._is_auto_awb = True
            # Apply via CameraTool so CameraStream is updated
            ct = self.find_camera_tool()
            if ct and hasattr(ct, 'set_auto_awb'):
                ct.set_auto_awb(True)
            if hasattr(self, 'update_awb_mode_ui'):
                self.update_awb_mode_ui()
        except Exception as e:
            print(f"DEBUG: [CameraManager] Error forcing auto AWB on live mode: {e}")

    def on_trigger_camera_mode_clicked(self):
        """Xử lý khi click Trigger Camera Mode button - delegate to CameraTool"""
        print("DEBUG: [CameraManager] Trigger camera mode button clicked")

        # Find the Camera Source tool and delegate mode change to it
        camera_tool = self.find_camera_tool()
        if camera_tool:
            print("DEBUG: [CameraManager] Found Camera Source tool, delegating mode change")
            success = camera_tool.set_camera_mode("trigger")
            if success:
                print("DEBUG: [CameraManager] Trigger mode set successfully via CameraTool")
            else:
                print("DEBUG: [CameraManager] Failed to set trigger mode via CameraTool")
        else:
            # Fallback: handle mode change directly if no Camera Source tool found
            print("DEBUG: [CameraManager] No Camera Source tool found, handling mode change directly")
            self._handle_trigger_mode_directly()

        # Ensure mutual exclusivity like AE/Manual buttons
        if self.trigger_camera_mode:
            try:
                self.trigger_camera_mode.blockSignals(True)
                self.trigger_camera_mode.setChecked(True)
            finally:
                self.trigger_camera_mode.blockSignals(False)
        if self.live_camera_mode:
            try:
                self.live_camera_mode.blockSignals(True)
                self.live_camera_mode.setChecked(False)
            finally:
                self.live_camera_mode.blockSignals(False)

        # When entering trigger mode, force 3A to manual (lock) and apply current params
        # 1) Exposure/Gain -> Manual AE and push current values
        try:
            self._is_auto_exposure = False
            self.set_manual_exposure_mode()  # also flips AeEnable=False on camera
            self.update_exposure_mode_ui()
            # Push current spinbox values immediately
            if self.exposure_edit is not None:
                try:
                    exp_val = self.exposure_edit.value() if hasattr(self.exposure_edit, 'value') else float(self.exposure_edit.text())
                    self._apply_setting_if_manual('exposure', exp_val)
                except Exception:
                    pass
            if self.gain_edit is not None:
                try:
                    gain_val = self.gain_edit.value() if hasattr(self.gain_edit, 'value') else float(self.gain_edit.text())
                    self._apply_setting_if_manual('gain', gain_val)
                except Exception:
                    pass
        except Exception as e:
            print(f"DEBUG: [CameraManager] Error forcing manual AE on trigger mode: {e}")

        # 2) White Balance -> Manual AWB and push current R/B gains if available
        try:
            self._is_auto_awb = False
            # Update AWB UI and enable manual fields
            if hasattr(self, 'update_awb_mode_ui'):
                self.update_awb_mode_ui()
            # Apply via CameraTool so it immediately configures CameraStream
            ct = self.find_camera_tool()
            if ct and hasattr(ct, 'set_auto_awb'):
                ct.set_auto_awb(False)
            # Push current gains
            r = None; b = None
            if self.colour_gain_r_edit and hasattr(self.colour_gain_r_edit, 'value'):
                try:
                    r = float(self.colour_gain_r_edit.value())
                except Exception:
                    pass
            if self.colour_gain_b_edit and hasattr(self.colour_gain_b_edit, 'value'):
                try:
                    b = float(self.colour_gain_b_edit.value())
                except Exception:
                    pass
            if ct and hasattr(ct, 'set_colour_gains') and r is not None and b is not None:
                ct.set_colour_gains(r, b)
        except Exception as e:
            print(f"DEBUG: [CameraManager] Error forcing manual AWB on trigger mode: {e}")
    
    def _handle_live_mode_directly(self):
        """Fallback handler for live mode when no CameraTool is available"""
        print("DEBUG: [CameraManager] Handling live mode directly")
        
        # Update UI state
        if self.live_camera_mode:
            self.live_camera_mode.setChecked(True)
        if self.trigger_camera_mode:
            self.trigger_camera_mode.setChecked(False)
        
        # Set internal state
        self.current_mode = 'live'
        
        # Apply hardware changes - explicitly disable trigger mode for live
        print("DEBUG: [CameraManager] Setting trigger mode to FALSE for live mode")
        self.set_trigger_mode(False)
        self.update_camera_mode_ui()
    
    def _handle_trigger_mode_directly(self):
        """Fallback handler for trigger mode when no CameraTool is available"""
        print("DEBUG: [CameraManager] Handling trigger mode directly")
        
        # Update UI state
        if self.trigger_camera_mode:
            self.trigger_camera_mode.setChecked(True)
        if self.live_camera_mode:
            self.live_camera_mode.setChecked(False)
        
        # Set internal state
        self.current_mode = 'trigger'
        
        # Apply hardware changes - explicitly enable trigger mode
        print("DEBUG: [CameraManager] Setting trigger mode to TRUE for trigger mode")
        self.set_trigger_mode(True)
        self.update_camera_mode_ui()
    
    # ============ EXPOSURE MODE HANDLERS ============
    
    def on_auto_exposure_clicked(self):
        """Xử lý khi click Auto Exposure button"""
        self._is_auto_exposure = True
        # Áp dụng auto mode ngay lập tức
        self.set_auto_exposure_mode()
        self.update_exposure_mode_ui()
        # Lưu vào pending settings
        self._pending_exposure_settings['auto_exposure'] = True
    
    def on_manual_exposure_clicked(self):
        """Xử lý khi click Manual Exposure button"""
        self._is_auto_exposure = False
        # Áp dụng manual mode ngay lập tức
        self.set_manual_exposure_mode()
        self.update_exposure_mode_ui()
        # Lưu vào pending settings
        self._pending_exposure_settings['auto_exposure'] = False
    
    def update_exposure_mode_ui(self):
        """Cập nhật UI theo exposure mode hiện tại"""
        # Enable/disable manual controls
        self.set_settings_controls_enabled(not self._is_auto_exposure and self.ui_enabled)
        
        # Update button states
        if self.auto_exposure_btn and self.manual_exposure_btn:
            if self._is_auto_exposure:
                self.auto_exposure_btn.setStyleSheet("background-color: #51cf66")  # Green
                self.manual_exposure_btn.setStyleSheet("")
            else:
                self.auto_exposure_btn.setStyleSheet("")
                self.manual_exposure_btn.setStyleSheet("background-color: #ffd43b")  # Yellow
    
    def find_camera_tool(self):
        """Tìm camera tool trong danh sách công cụ"""
        if not hasattr(self, 'main_window') or not self.main_window:
            return None
            
        if not hasattr(self.main_window, 'tool_manager') or not self.main_window.tool_manager:
            return None
            
        # Access tools through job_manager instead of tool_manager
        job_manager = self.main_window.tool_manager.job_manager
        if not job_manager or not hasattr(job_manager, 'current_job') or not job_manager.current_job:
            return None
            
        # Search through tools in current job
        for tool in job_manager.current_job.tools:
            if hasattr(tool, '__class__') and tool.__class__.__name__ == 'CameraTool':
                return tool
            # Also check by name for backwards compatibility
            if hasattr(tool, 'name') and tool.name == 'Camera Source':
                return tool
                
        return None
    
    def on_apply_settings_clicked(self):
        """Áp dụng tất cả settings đã thay đổi"""
        try:
            # Kiểm tra xem có đang ở chế độ live camera không
            was_live_active = self.current_mode == 'live' and self.camera_stream and self.camera_stream.is_live
            
            # Nếu đang live, tạm dừng để apply settings
            if was_live_active:
                try:
                    # Preferred safe stop in apply settings
                    try:
                        print("DEBUG: [CameraManager] Preferred stop - cancel_and_stop_live() in apply settings")
                        self.camera_stream.cancel_and_stop_live()
                    except AttributeError as e:
                        print(f"DEBUG: [CameraManager] AttributeError cancel_and_stop_live in apply settings: {e}")
                        if hasattr(self.camera_stream, 'cancel_all_and_flush'):
                            self.camera_stream.cancel_all_and_flush()
                        if hasattr(self.camera_stream, 'stop_live'):
                            self.camera_stream.stop_live()
                except Exception as e:
                    print(f"DEBUG: [CameraManager] Error stopping camera in apply settings: {e}")
            
            # Apply exposure mode
            if 'auto_exposure' in self._pending_exposure_settings:
                auto_mode = self._pending_exposure_settings['auto_exposure']
                if self.camera_stream:
                    self.camera_stream.set_auto_exposure(auto_mode)
            
            # Apply exposure values
            if 'exposure' in self._pending_exposure_settings:
                exposure_value = self._pending_exposure_settings['exposure']
                print(f"DEBUG: Applying exposure: {exposure_value}μs")
                if self.camera_stream:
                    self.camera_stream.set_exposure(exposure_value)
                    print(f"DEBUG: Called set_exposure with {exposure_value}")
                else:
                    print("DEBUG: No camera_stream available")
            
            # Apply gain
            if 'gain' in self._pending_exposure_settings:
                if self.camera_stream:
                    self.camera_stream.set_gain(self._pending_exposure_settings['gain'])
            
            # Apply EV
            if 'ev' in self._pending_exposure_settings:
                if self.camera_stream:
                    self.camera_stream.set_ev(self._pending_exposure_settings['ev'])
            
            # Nếu trước đó đang live, restart live preview với settings mới
            if was_live_active:
                self.camera_stream.start_live()
            
            # Không sync lại UI từ camera để tránh reset về default
            # Giữ nguyên giá trị user đã set
            # self.update_camera_params_from_camera()
            
            # Clear pending settings
            self._pending_exposure_settings.clear()
        except Exception as e:
            logging.error(f"Error applying camera settings: {e}")
        
        # Hiển thị dialog thông báo thành công
        # KHÔNG hiển thị dialog thành công, chỉ ghi log
        logging.info("Camera settings applied successfully (no dialog)")
    
    def get_exposure_value(self):
        """Lấy giá trị exposure hiện tại của camera"""
        if self.exposure_edit:
            try:
                return int(self.exposure_edit.text())
            except (ValueError, TypeError):
                logging.warning("CameraManager: Failed to get exposure value from UI")
                
        # Fallback: get from camera stream if available
        if self.camera_stream:
            try:
                if hasattr(self.camera_stream, 'get_exposure'):
                    return self.camera_stream.get_exposure()
                elif hasattr(self.camera_stream, 'current_exposure'):
                    return self.camera_stream.current_exposure
                else:
                    logging.warning("CameraManager: Camera stream has no exposure getter methods")
            except Exception as e:
                logging.warning(f"CameraManager: Error getting exposure from camera: {e}")
        
        logging.warning("CameraManager: Using default exposure value")
        return 10000  # Default to 10ms
    
    def get_gain_value(self):
        """Lấy giá trị gain hiện tại của camera"""
        if self.gain_edit:
            try:
                return float(self.gain_edit.text())
            except (ValueError, TypeError):
                logging.warning("CameraManager: Failed to get gain value from UI")
                
        # Fallback: get from camera stream if available
        if self.camera_stream:
            try:
                if hasattr(self.camera_stream, 'get_gain'):
                    return self.camera_stream.get_gain()
                elif hasattr(self.camera_stream, 'current_gain'):
                    return self.camera_stream.current_gain
                else:
                    logging.warning("CameraManager: Camera stream has no gain getter methods")
            except Exception as e:
                logging.warning(f"CameraManager: Error getting gain from camera: {e}")
        
        logging.warning("CameraManager: Using default gain value")
        return 1.0  # Default gain
    
    def get_ev_value(self):
        """Lấy giá trị EV hiện tại của camera"""
        if self.ev_edit:
            try:
                return float(self.ev_edit.text())
            except (ValueError, TypeError):
                logging.warning("CameraManager: Failed to get EV value from UI")
                
        # Fallback: get from camera stream if available
        if self.camera_stream:
            try:
                if hasattr(self.camera_stream, 'get_ev'):
                    return self.camera_stream.get_ev()
                elif hasattr(self.camera_stream, 'current_ev'):
                    return self.camera_stream.current_ev
                else:
                    logging.warning("CameraManager: Camera stream has no EV getter methods")
            except Exception as e:
                logging.warning(f"CameraManager: Error getting EV from camera: {e}")
        
        logging.warning("CameraManager: Using default EV value")
        return 0.0  # Default EV
    
    def is_auto_exposure(self):
        """Kiểm tra chế độ auto exposure của camera"""
        return self._is_auto_exposure
        
    def enable_camera_buttons(self):
        """Kích hoạt các nút điều khiển camera sau khi đã thêm Camera Source tool"""
        if self.live_camera_btn:
            self.live_camera_btn.setEnabled(True)
            self.live_camera_btn.setToolTip("Start live camera preview")
            
        if self.trigger_camera_btn:
            self.trigger_camera_btn.setEnabled(True)
            self.trigger_camera_btn.setToolTip("Trigger single frame capture")
            
        if self.live_camera_mode:
            self.live_camera_mode.setEnabled(True)
            self.live_camera_mode.setToolTip("Switch to live camera mode")
            
        if self.trigger_camera_mode:
            self.trigger_camera_mode.setEnabled(True)
            self.trigger_camera_mode.setToolTip("Switch to trigger camera mode")
            
        logging.info("CameraManager: Camera control buttons enabled")
        
        # Tự động bắt đầu live camera sau khi thêm Camera Source
        self.start_camera_preview()
        
    def _implement_start_live(self):
        """
        Direct implementation of camera start live in CameraManager
        when CameraStream methods are unavailable
        """
        print("DEBUG: [CameraManager] _implement_start_live emergency fallback called")
        
        try:
            # Ensure we have access to the camera stream object
            if not hasattr(self, 'camera_stream') or self.camera_stream is None:
                print("DEBUG: [CameraManager] No camera_stream object available")
                return False
                
            # Check if camera is available
            if not hasattr(self.camera_stream, 'is_camera_available'):
                print("DEBUG: [CameraManager] is_camera_available not found")
                return False
                
            if not self.camera_stream.is_camera_available:
                print("DEBUG: [CameraManager] Camera not available")
                return False
                
            # Ensure picam2 exists
            if not hasattr(self.camera_stream, 'picam2') or self.camera_stream.picam2 is None:
                print("DEBUG: [CameraManager] picam2 not available")
                return False
                
            # Start the camera directly
            picam2 = self.camera_stream.picam2
            
            # Configure if needed
            if hasattr(self.camera_stream, 'preview_config'):
                try:
                    print("DEBUG: [CameraManager] Configuring camera with preview_config")
                    picam2.configure(self.camera_stream.preview_config)
                except Exception as e:
                    print(f"DEBUG: [CameraManager] Error configuring camera: {e}")
                    # Continue anyway
            
            # Start the camera
            try:
                print("DEBUG: [CameraManager] Starting camera directly")
                picam2.start()
            except Exception as e:
                print(f"DEBUG: [CameraManager] Error starting camera: {e}")
                return False
                
            # Start the timer
            if hasattr(self.camera_stream, 'timer'):
                try:
                    print("DEBUG: [CameraManager] Starting timer")
                    self.camera_stream.timer.start(100)  # 10 FPS
                except Exception as e:
                    print(f"DEBUG: [CameraManager] Error starting timer: {e}")
                    # Continue anyway
                    
            # Set live flag
            if hasattr(self.camera_stream, 'is_live'):
                self.camera_stream.is_live = True
                
            print("DEBUG: [CameraManager] Camera started successfully via direct implementation")
            return True
        except Exception as e:
            print(f"DEBUG: [CameraManager] Unhandled error in _implement_start_live: {e}")
            return False
            
    def _implement_stop_live(self):
        """
        Direct implementation of camera stop live in CameraManager
        when CameraStream methods are unavailable
        """
        print("DEBUG: [CameraManager] _implement_stop_live emergency fallback called")
        
        try:
            # Ensure we have access to the camera stream object
            if not hasattr(self, 'camera_stream') or self.camera_stream is None:
                print("DEBUG: [CameraManager] No camera_stream object available")
                return False
                
            # Stop the timer first
            if hasattr(self.camera_stream, 'timer'):
                try:
                    if hasattr(self.camera_stream.timer, 'isActive') and self.camera_stream.timer.isActive():
                        print("DEBUG: [CameraManager] Stopping timer directly")
                        self.camera_stream.timer.stop()
                except Exception as e:
                    print(f"DEBUG: [CameraManager] Error stopping timer: {e}")
                    # Continue anyway
            
            # Set is_live flag to False
            if hasattr(self.camera_stream, 'is_live'):
                self.camera_stream.is_live = False
                
            # Stop the camera if it exists
            if hasattr(self.camera_stream, 'picam2') and self.camera_stream.picam2 is not None:
                try:
                    picam2 = self.camera_stream.picam2
                    if hasattr(picam2, 'started') and picam2.started:
                        print("DEBUG: [CameraManager] Stopping camera directly")
                        picam2.stop()
                except Exception as e:
                    print(f"DEBUG: [CameraManager] Error stopping camera: {e}")
                    # Continue anyway
                    
            print("DEBUG: [CameraManager] Camera stopped successfully via direct implementation")
            return True
        except Exception as e:
            print(f"DEBUG: [CameraManager] Unhandled error in _implement_stop_live: {e}")
            return False
        
    def start_camera_preview(self):
        """Bắt đầu hiển thị camera preview sau khi thêm Camera Source"""
        print("DEBUG: CameraManager.start_camera_preview called")
        
        if not self.camera_stream:
            print("DEBUG: Camera stream is None, cannot start preview")
            logging.error("CameraManager: Cannot start preview - camera_stream is None")
            return False
            
        # Đảm bảo camera không đang chạy (trước khi thay đổi bất kỳ chế độ nào)
        if self.camera_stream.is_running():
            print("DEBUG: [CameraManager] Camera is already running, stopping it first")
            try:
                try:
                    self.camera_stream.cancel_and_stop_live()
                except AttributeError:
                    if hasattr(self.camera_stream, 'cancel_all_and_flush'):
                        self.camera_stream.cancel_all_and_flush()
                    self.camera_stream.stop_live()
            except Exception as e:
                print(f"DEBUG: [CameraManager] Error stopping camera: {e}")
        
        # Ensure job is enabled to see camera feed
        if not self.camera_stream.job_enabled:
            print("DEBUG: Enabling job execution for camera stream")
            self.camera_stream.job_enabled = True
            if self.job_toggle_btn:
                self.job_toggle_btn.setChecked(True)
                
        # Đảm bảo UI được cập nhật với chế độ camera hiện tại
        self.update_camera_mode_ui()
        
        # Lưu ý: Chúng ta không tự động khởi động camera nữa
        # Người dùng sẽ cần phải bấm nút Start Camera
        print("DEBUG: [CameraManager] Camera is ready but not auto-started - user must press Start Camera")
        
        return True
    def on_cancel_settings_clicked(self):
        """Hủy bỏ tất cả thay đổi và khôi phục giá trị mặc định"""
        try:
            # Reset to default values
            self._is_auto_exposure = True
            
            # Reset UI values
            if self.exposure_edit:
                self.exposure_edit.setValue(10000.0)  # 10000 microseconds (10ms)
            if self.gain_edit:
                self.gain_edit.setValue(1.0)
            if self.ev_edit:
                self.ev_edit.setValue(0.0)
            
            # Clear pending settings
            self._pending_exposure_settings.clear()
            
            # Update UI
            self.update_exposure_mode_ui()
            
            logging.info("Camera settings cancelled and reset to defaults")
            
        except Exception as e:
            logging.error(f"Error cancelling camera settings: {str(e)}")

    def on_job_toggle_clicked(self):
        """Xử lý sự kiện click nút toggle job"""
        print(f"DEBUG: [CameraManager] Job toggle clicked, current state: {self.job_enabled}")
        
        # Toggle job state
        self.job_enabled = not self.job_enabled
        
        # Update UI
        self.update_job_toggle_ui()
        
        # Always sync job setting to camera stream
        if self.camera_stream and hasattr(self.camera_stream, 'set_job_enabled'):
            self.camera_stream.set_job_enabled(self.job_enabled)
        
        # Nếu camera đang chạy live mode, cần restart để apply job setting
        if self.current_mode == 'live' and self.camera_stream:
            print(f"DEBUG: [CameraManager] Restarting live mode with job_enabled={self.job_enabled}")
            # Stop and restart live mode
            try:
                self.camera_stream.cancel_and_stop_live()
            except AttributeError:
                if hasattr(self.camera_stream, 'cancel_all_and_flush'):
                    self.camera_stream.cancel_all_and_flush()
                self.camera_stream.stop_live()
            self.camera_stream.start_live()
        
        print(f"DEBUG: [CameraManager] Job execution {'ENABLED' if self.job_enabled else 'DISABLED'}")

    def update_job_toggle_ui(self):
        """Cập nhật UI trạng thái job toggle"""
        if self.job_toggle_btn:
            if self.job_enabled:
                self.job_toggle_btn.setText("Disable Job")
                self.job_toggle_btn.setStyleSheet("background-color: #ff4444; color: white;")
                self.job_toggle_btn.setToolTip("Click to disable job execution (prevents camera hanging)")
            else:
                self.job_toggle_btn.setText("Enable Job")
                self.job_toggle_btn.setStyleSheet("background-color: #44ff44; color: black;")
                self.job_toggle_btn.setToolTip("Click to enable job execution")

    def is_job_enabled(self):
        """Kiểm tra job có được enable không"""
        return self.job_enabled
            
    def register_tool(self, tool):
        """
        Register a tool with the camera manager, used to connect tools with camera manager
        
        Args:
            tool: The tool to register
        """
        print(f"DEBUG: [CameraManager] Registering tool: {getattr(tool, 'display_name', 'Unknown')}")
        
        # Special handling for Camera Source tool
        if hasattr(tool, 'name') and tool.name == "Camera Source":
            print(f"DEBUG: [CameraManager] Detected Camera Source tool - establishing Single Source of Truth")
            
            # Set bidirectional reference (Single Source of Truth pattern)
            tool.camera_manager = self
            
            # Apply the camera tool config to camera manager
            if hasattr(tool, 'config'):
                print(f"DEBUG: [CameraManager] Applying Camera Source config to CameraManager")
                self._apply_camera_tool_config(tool.config)
            
            print(f"DEBUG: [CameraManager] Camera Source tool registered successfully")
        else:
            print(f"DEBUG: [CameraManager] Non-Camera Source tool registered: {getattr(tool, 'name', 'Unknown')}")
    
    def _apply_camera_tool_config(self, config):
        """Apply camera tool configuration to camera manager"""
        print(f"DEBUG: [CameraManager] Applying camera tool config: {config}")
        
        # Apply camera mode
        if 'camera_mode' in config:
            mode = config['camera_mode']
            print(f"DEBUG: [CameraManager] Setting mode from tool config: {mode}")
            self.current_mode = mode
            
            # Update UI to reflect the mode
            if mode == 'live' and self.live_camera_mode:
                self.live_camera_mode.setChecked(True)
            elif mode == 'trigger' and self.trigger_camera_mode:
                self.trigger_camera_mode.setChecked(True)

        # Apply other settings
        # Frame size
        if 'frame_size' in config and self.camera_stream and hasattr(self.camera_stream, 'set_frame_size'):
            try:
                w, h = config['frame_size']
                print(f"DEBUG: [CameraManager] Applying frame size from tool: {w}x{h}")
                self.camera_stream.set_frame_size(w, h)
            except Exception as e:
                print(f"DEBUG: [CameraManager] Could not apply frame size: {e}")
        # Pixel format
        if 'format' in config and self.camera_stream and hasattr(self.camera_stream, 'set_format'):
            try:
                pf = config['format']
                print(f"DEBUG: [CameraManager] Applying pixel format from tool: {pf}")
                self.camera_stream.set_format(pf)
            except Exception as e:
                print(f"DEBUG: [CameraManager] Could not apply pixel format: {e}")
        # Target FPS for live
        if 'target_fps' in config and self.camera_stream and hasattr(self.camera_stream, 'set_target_fps'):
            try:
                fps = config['target_fps']
                print(f"DEBUG: [CameraManager] Applying target FPS from tool: {fps}")
                self.camera_stream.set_target_fps(fps)
            except Exception as e:
                print(f"DEBUG: [CameraManager] Could not apply target FPS: {e}")
        if 'exposure' in config:
            self.set_exposure_value(config['exposure'])
        if 'gain' in config:
            self.set_gain_value(config['gain'])
        if 'ev' in config:
            self.set_ev_value(config['ev'])
        if 'is_auto_exposure' in config:
            if config['is_auto_exposure']:
                self.set_auto_exposure_mode()
            else:
                self.set_manual_exposure_mode()
        # External trigger preference (if any)
        if 'enable_external_trigger' in config and self.camera_stream and hasattr(self.camera_stream, 'set_trigger_mode'):
            try:
                trig = bool(config['enable_external_trigger'])
                print(f"DEBUG: [CameraManager] Applying external trigger preference: {trig}")
                self.camera_stream.set_trigger_mode(trig)
            except Exception as e:
                print(f"DEBUG: [CameraManager] Could not apply external trigger: {e}")
        
        print(f"DEBUG: [CameraManager] Camera tool config applied successfully")

    # ============ AWB MODE HANDLERS (inserted) ============
    def set_awb_controls_enabled(self, enabled):
        """Enable/disable manual AWB controls (colour gains)."""
        if hasattr(self, 'colour_gain_r_edit') and self.colour_gain_r_edit:
            self.colour_gain_r_edit.setEnabled(enabled)
        if hasattr(self, 'colour_gain_b_edit') and self.colour_gain_b_edit:
            self.colour_gain_b_edit.setEnabled(enabled)

    def on_auto_awb_clicked(self):
        """Handle click on Auto AWB button."""
        self._is_auto_awb = True
        self.update_awb_mode_ui()
        ct = self.find_camera_tool()
        try:
            if ct and hasattr(ct, 'set_auto_awb'):
                ct.set_auto_awb(True)
            # Reset displayed manual gains to defaults (visual reset)
            default_r = 1.0
            default_b = 1.0
            try:
                if ct and hasattr(ct, 'config'):
                    default_r = float(ct.config.get('colour_gain_r', default_r))
                    default_b = float(ct.config.get('colour_gain_b', default_b))
            except Exception:
                pass
            if hasattr(self, 'colour_gain_r_edit') and self.colour_gain_r_edit and hasattr(self.colour_gain_r_edit, 'setValue'):
                try:
                    self.colour_gain_r_edit.setValue(default_r)
                except Exception:
                    pass
            if hasattr(self, 'colour_gain_b_edit') and self.colour_gain_b_edit and hasattr(self.colour_gain_b_edit, 'setValue'):
                try:
                    self.colour_gain_b_edit.setValue(default_b)
                except Exception:
                    pass
        except Exception:
            pass

    def on_manual_awb_clicked(self):
        """Handle click on Manual AWB button."""
        self._is_auto_awb = False
        self.update_awb_mode_ui()
        ct = self.find_camera_tool()
        try:
            if ct and hasattr(ct, 'set_auto_awb'):
                ct.set_auto_awb(False)
            r = None
            b = None
            if hasattr(self, 'colour_gain_r_edit') and self.colour_gain_r_edit:
                try:
                    r = float(self.colour_gain_r_edit.value())
                except Exception:
                    pass
            if hasattr(self, 'colour_gain_b_edit') and self.colour_gain_b_edit:
                try:
                    b = float(self.colour_gain_b_edit.value())
                except Exception:
                    pass
            if ct and hasattr(ct, 'set_colour_gains') and r is not None and b is not None:
                ct.set_colour_gains(r, b)
        except Exception:
            pass

    def update_awb_mode_ui(self):
        """Update UI according to current AWB mode."""
        self.set_awb_controls_enabled(getattr(self, 'ui_enabled', False) and not getattr(self, '_is_auto_awb', True))
        if hasattr(self, 'auto_awb_btn') and hasattr(self, 'manual_awb_btn') and self.auto_awb_btn and self.manual_awb_btn:
            if getattr(self, '_is_auto_awb', True):
                self.auto_awb_btn.setStyleSheet("background-color: #51cf66")
                self.manual_awb_btn.setStyleSheet("")
            else:
                self.auto_awb_btn.setStyleSheet("")
                self.manual_awb_btn.setStyleSheet("background-color: #ffd43b")

    def on_colour_gain_r_changed(self, value=None):
        """Instant apply manual R gain when AWB is manual."""
        if getattr(self, '_is_auto_awb', True):
            return
        ct = self.find_camera_tool()
        if ct and hasattr(ct, 'set_colour_gains'):
            try:
                r = float(self.colour_gain_r_edit.value()) if self.colour_gain_r_edit else None
                b = float(self.colour_gain_b_edit.value()) if self.colour_gain_b_edit else None
                if r is not None and b is not None:
                    ct.set_colour_gains(r, b)
            except Exception:
                pass

    def on_colour_gain_b_changed(self, value=None):
        """Instant apply manual B gain when AWB is manual."""
        if getattr(self, '_is_auto_awb', True):
            return
        ct = self.find_camera_tool()
        if ct and hasattr(ct, 'set_colour_gains'):
            try:
                r = float(self.colour_gain_r_edit.value()) if self.colour_gain_r_edit else None
                b = float(self.colour_gain_b_edit.value()) if self.colour_gain_b_edit else None
                if r is not None and b is not None:
                    ct.set_colour_gains(r, b)
            except Exception:
                pass
            
    def cleanup(self):
        """Dọn dẹp tài nguyên camera khi thoát ứng dụng"""
        logger = logging.getLogger(__name__)
        try:
            # Dừng live preview nếu đang chạy
            if self.camera_stream:
                try:
                    logger.info("Stopping camera live preview...")
                    try:
                        self.camera_stream.cancel_and_stop_live()
                    except AttributeError as e:
                        logger.warning(f"AttributeError cancel_and_stop_live in cleanup: {e}")
                        try:
                            if hasattr(self.camera_stream, 'cancel_all_and_flush'):
                                self.camera_stream.cancel_all_and_flush()
                            if hasattr(self.camera_stream, 'stop_live'):
                                self.camera_stream.stop_live()
                        except Exception:
                            self._implement_stop_live()
                except Exception as e:
                    logger.error(f"Error stopping camera in cleanup: {e}")
            
            # Dọn dẹp camera stream
            if self.camera_stream and hasattr(self.camera_stream, 'cleanup'):
                logger.info("Cleaning up camera stream...")
                self.camera_stream.cleanup()
            
            # Dọn dẹp camera view
            if self.camera_view:
                logger.info("Cleaning up camera view...")
                self.camera_view = None
                
            logger.info("Camera manager cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during camera manager cleanup: {str(e)}", exc_info=True)

    # ============ TRIGGER MODE IMPLEMENTATION ============
    def _implement_start_live(self):
        """Triển khai việc bắt đầu chế độ live view"""
        print("DEBUG: [CameraManager] Implementing start live view")
        
        if not self.camera_stream:
            print("DEBUG: [CameraManager] No camera stream available")
            return False
        
        try:
            # Đảm bảo hardware không ở chế độ trigger
            if hasattr(self.camera_stream, 'set_trigger_mode'):
                print("DEBUG: [CameraManager] Setting hardware to live mode")
                self.camera_stream.set_trigger_mode(False)
                
            # Refresh source output combo before starting
            print("DEBUG: [CameraManager] Refreshing source output combo before live start")
            self.refresh_source_output_combo()
                
            # Bắt đầu camera live view
            success = self.toggle_live_camera(True)
            if not success:
                print("DEBUG: [CameraManager] Failed to start live camera")
                return False
                
            self.is_live = True
            print("DEBUG: [CameraManager] Live view started successfully")
            return True
            
        except Exception as e:
            print(f"DEBUG: [CameraManager] Error starting live view: {e}")
            return False
            
    def _implement_start_trigger(self):
        """
        Direct implementation of camera start in trigger mode
        when CameraStream methods are unavailable
        """
        print("DEBUG: [CameraManager] _implement_start_trigger called")
        
        try:
            # Ensure we have access to the camera stream object
            if not hasattr(self, 'camera_stream') or self.camera_stream is None:
                print("DEBUG: [CameraManager] No camera_stream object available")
                return False
                
            # Check if camera is available
            if not hasattr(self.camera_stream, 'is_camera_available'):
                print("DEBUG: [CameraManager] is_camera_available not found")
                return False
                
            if not self.camera_stream.is_camera_available:
                print("DEBUG: [CameraManager] Camera not available")
                return False
                
            # Ensure picam2 exists
            if not hasattr(self.camera_stream, 'picam2') or self.camera_stream.picam2 is None:
                print("DEBUG: [CameraManager] picam2 not available")
                return False
                
            # Set trigger mode on the camera
            if hasattr(self.camera_stream, 'set_trigger_mode'):
                print("DEBUG: [CameraManager] Setting camera to trigger mode")
                self.camera_stream.set_trigger_mode(True)
            else:
                print("DEBUG: [CameraManager] set_trigger_mode not available")
                return False
                
            # Start the camera directly
            picam2 = self.camera_stream.picam2
            
            # Configure if needed
            if hasattr(self.camera_stream, 'still_config'):
                try:
                    print("DEBUG: [CameraManager] Configuring camera with still_config")
                    picam2.configure(self.camera_stream.still_config)
                except Exception as e:
                    print(f"DEBUG: [CameraManager] Error configuring camera: {e}")
                    # Continue anyway
            
            # Start the camera
            try:
                print("DEBUG: [CameraManager] Starting camera in trigger mode")
                picam2.start()
            except Exception as e:
                print(f"DEBUG: [CameraManager] Error starting camera: {e}")
                return False
                
            # Set trigger flag
            if hasattr(self.camera_stream, 'external_trigger_enabled'):
                self.camera_stream.external_trigger_enabled = True
                
            print("DEBUG: [CameraManager] Camera started successfully in trigger mode")
            return True
        except Exception as e:
            print(f"DEBUG: [CameraManager] Unhandled error in _implement_start_trigger: {e}")
            return False
            
    def _implement_stop_trigger(self):
        """Triển khai việc dừng chế độ trigger"""
        print("DEBUG: [CameraManager] Implementing stop trigger mode")
        
        if not self.camera_stream:
            print("DEBUG: [CameraManager] No camera stream available for stopping trigger")
            return False
            
        try:
            # Dừng chế độ trigger
            if hasattr(self.camera_stream, 'stop_external_trigger'):
                print("DEBUG: [CameraManager] Stopping external trigger mode")
                self.camera_stream.stop_external_trigger()
                self.is_live = False
                return True
            else:
                # Dùng phương thức thông thường
                if hasattr(self.camera_stream, 'set_trigger_mode'):
                    print("DEBUG: [CameraManager] Setting trigger mode off")
                    self.camera_stream.set_trigger_mode(False)
                    
                if hasattr(self.camera_stream, 'picam2') and self.camera_stream.picam2:
                    try:
                        print("DEBUG: [CameraManager] Stopping camera in trigger mode")
                        self.camera_stream.picam2.stop()
                    except Exception as e:
                        print(f"DEBUG: [CameraManager] Error stopping camera: {e}")
                        return False
                
                if hasattr(self.camera_stream, 'external_trigger_enabled'):
                    self.camera_stream.external_trigger_enabled = False
                
                self.is_live = False
                return True
                
        except Exception as e:
            print(f"DEBUG: [CameraManager] Error stopping trigger mode: {e}")
            return False

