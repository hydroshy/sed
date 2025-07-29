from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtWidgets import QApplication
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
        self.gain_slider = None
        self.gain_edit = None
        self.ev_slider = None
        self.ev_edit = None
        self.focus_bar = None
        self.fps_num = None
        self.width_spinbox = None
        self.height_spinbox = None
        
        # Settings synchronization
        self.settings_manager = None  # Will be set by main window
        
        # Camera mode state
        self.current_mode = None  # 'live' hoặc 'trigger' hoặc None
        self.live_camera_btn = None
        self.trigger_camera_btn = None
        
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
        
    def setup(self, camera_view_widget, exposure_edit,
             gain_slider, gain_edit, ev_slider, ev_edit, focus_bar, fps_num):
        """Thiết lập các tham chiếu đến các widget UI và khởi tạo camera"""
        # Khởi tạo camera stream
        self.camera_stream = CameraStream()
        
        # Khởi tạo camera view với main_window reference
        self.camera_view = CameraView(camera_view_widget, self.main_window)
        self.camera_stream.frame_ready.connect(self.camera_view.display_frame)
        
        # Kết nối các widget - bỏ exposure_slider
        self.exposure_edit = exposure_edit
        self.gain_slider = gain_slider
        self.gain_edit = gain_edit
        self.ev_slider = ev_slider
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
        
    def setup_camera_buttons(self, live_camera_btn=None, trigger_camera_btn=None, 
                           auto_exposure_btn=None, manual_exposure_btn=None,
                           apply_settings_btn=None, cancel_settings_btn=None,
                           job_toggle_btn=None):
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
        """
        self.live_camera_btn = live_camera_btn
        self.trigger_camera_btn = trigger_camera_btn
        self.auto_exposure_btn = auto_exposure_btn
        self.manual_exposure_btn = manual_exposure_btn
        self.apply_settings_btn = apply_settings_btn
        self.cancel_settings_btn = cancel_settings_btn
        self.job_toggle_btn = job_toggle_btn
        
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
            
        if missing_widgets:
            logging.warning(f"Missing UI widgets: {', '.join(missing_widgets)}")
        
        # Kết nối signals
        if self.live_camera_btn:
            self.live_camera_btn.clicked.connect(self.on_live_camera_clicked)
        if self.trigger_camera_btn:
            self.trigger_camera_btn.clicked.connect(self.on_trigger_camera_clicked)
        if self.auto_exposure_btn:
            self.auto_exposure_btn.clicked.connect(self.on_auto_exposure_clicked)
        if self.manual_exposure_btn:
            self.manual_exposure_btn.clicked.connect(self.on_manual_exposure_clicked)
        if self.apply_settings_btn:
            self.apply_settings_btn.clicked.connect(self.on_apply_settings_clicked)
        if self.cancel_settings_btn:
            self.cancel_settings_btn.clicked.connect(self.on_cancel_settings_clicked)
        if self.job_toggle_btn:
            self.job_toggle_btn.clicked.connect(self.on_job_toggle_clicked)
            
        # Khởi tạo UI state
        self.update_camera_mode_ui()
        self.update_exposure_mode_ui()
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
            
        # Settings controls
        self.set_settings_controls_enabled(enabled and not self._is_auto_exposure)
        
        # Apply/Cancel buttons
        if self.apply_settings_btn:
            self.apply_settings_btn.setEnabled(enabled)
        if self.cancel_settings_btn:
            self.cancel_settings_btn.setEnabled(enabled)
    
    def set_settings_controls_enabled(self, enabled):
        """Bật/tắt các control settings (exposure, gain, ev)"""
        if self.exposure_edit:
            self.exposure_edit.setEnabled(enabled)
        if self.gain_slider:
            self.gain_slider.setEnabled(enabled)
        if self.gain_edit:
            self.gain_edit.setEnabled(enabled)
        if self.ev_slider:
            self.ev_slider.setEnabled(enabled)
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
        if self.gain_slider:
            self.gain_slider.valueChanged.connect(self.on_gain_slider_changed)
        if self.gain_edit:
            self.gain_edit.editingFinished.connect(self.on_gain_edit_changed)
        # EV
        if self.ev_slider:
            self.ev_slider.valueChanged.connect(self.on_ev_slider_changed)
        if self.ev_edit:
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
            self.gain_edit.setText(str(value))
        if self.gain_slider:
            self.gain_slider.setValue(int(value))
        if hasattr(self.camera_stream, 'set_gain'):
            self.camera_stream.set_gain(value)

    def set_ev(self, value):
        """Đặt giá trị EV cho camera"""
        if self.ev_edit:
            self.ev_edit.setText(str(value))
        if self.ev_slider:
            self.ev_slider.setValue(int(value))
        if hasattr(self.camera_stream, 'set_ev'):
            self.camera_stream.set_ev(value)

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

    def on_gain_slider_changed(self, value):
        """Xử lý khi người dùng thay đổi slider gain"""
        if self.gain_edit:
            self.gain_edit.setText(str(value))
        if hasattr(self.camera_stream, 'set_gain'):
            self.camera_stream.set_gain(value)

    def on_gain_edit_changed(self):
        """Xử lý khi người dùng thay đổi giá trị gain trong ô văn bản"""
        try:
            if self.gain_edit:
                value = int(self.gain_edit.text())
                if self.gain_slider:
                    self.gain_slider.setValue(value)
                if hasattr(self.camera_stream, 'set_gain'):
                    self.camera_stream.set_gain(value)
        except ValueError:
            pass

    def on_ev_slider_changed(self, value):
        """Xử lý khi người dùng thay đổi slider EV"""
        if self.ev_edit:
            self.ev_edit.setText(str(value))
        if hasattr(self.camera_stream, 'set_ev'):
            self.camera_stream.set_ev(value)

    def on_ev_edit_changed(self):
        """Xử lý khi người dùng thay đổi giá trị EV trong ô văn bản"""
        try:
            if self.ev_edit:
                value = int(self.ev_edit.text())
                if self.ev_slider:
                    self.ev_slider.setValue(value)
                if hasattr(self.camera_stream, 'set_ev'):
                    self.camera_stream.set_ev(value)
        except ValueError:
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
            gain = self.camera_stream.get_gain()
            print(f"DEBUG: Got gain from camera: {gain}")
            if gain:
                self.set_gain(gain)
                
        if hasattr(self.camera_stream, 'get_ev'):
            ev = self.camera_stream.get_ev()
            print(f"DEBUG: Got EV from camera: {ev}")
            if ev is not None:
                self.set_ev(ev)
            
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
        
        if not self.camera_stream:
            print("DEBUG: [CameraManager] No camera stream available")
            return False
            
        try:
            if checked:
                print("DEBUG: [CameraManager] Starting live camera...")
                
                # Process pending events to keep UI responsive
                QApplication.processEvents()
                
                success = self.camera_stream.start_live()
                
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
                
                self.camera_stream.stop_live()
                
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
        if self.gain_slider:
            self.gain_slider.setEnabled(False)
        if self.gain_edit:
            self.gain_edit.setEnabled(False)
        if self.ev_slider:
            self.ev_slider.setEnabled(False)
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
        if self.gain_slider:
            self.gain_slider.setEnabled(True)
        if self.gain_edit:
            self.gain_edit.setEnabled(True)
        if self.ev_slider:
            self.ev_slider.setEnabled(True)
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
        """Kích hoạt chụp ảnh"""
        if self.camera_stream:
            print("DEBUG: [CameraManager] Triggering capture...")
            
            # Visual feedback - temporarily change button text
            if self.trigger_camera_btn and self.current_mode == 'trigger':
                original_text = self.trigger_camera_btn.text()
                self.trigger_camera_btn.setText("Capturing...")
                self.trigger_camera_btn.setEnabled(False)
                
                # Ensure we're in trigger mode
                if self.current_mode != 'trigger':
                    print("DEBUG: [CameraManager] Switching to trigger mode")
                    self.set_trigger_mode()
                
                # Apply job setting to camera stream
                if hasattr(self.camera_stream, 'set_job_enabled'):
                    self.camera_stream.set_job_enabled(self.job_enabled)
                
                # Sync current exposure setting before trigger
                self.sync_exposure_to_camera()
                
                # Trigger actual capture
                self.camera_stream.trigger_capture()
                
                # Restore button after short delay
                from PyQt5.QtCore import QTimer
                def restore_button():
                    if self.trigger_camera_btn:
                        self.trigger_camera_btn.setText(original_text)
                        if self.current_mode == 'trigger':
                            self.trigger_camera_btn.setEnabled(True)
                
                QTimer.singleShot(1000, restore_button)  # 1 second delay
            else:
                # Direct trigger without UI feedback
                self.camera_stream.trigger_capture()
        else:
            print("DEBUG: [CameraManager] No camera stream available")

    def sync_exposure_to_camera(self):
        """Sync current exposure setting to camera before trigger capture"""
        if self.camera_stream and self.exposure_edit:
            try:
                # Get current exposure value from UI
                if hasattr(self.exposure_edit, 'value'):
                    current_exposure = self.exposure_edit.value()
                else:
                    current_exposure = float(self.exposure_edit.text())
                
                print(f"DEBUG: [CameraManager] Syncing exposure {current_exposure}μs to camera for trigger")
                
                # Set exposure on camera stream
                self.camera_stream.set_exposure(current_exposure)
                
            except Exception as e:
                print(f"DEBUG: [CameraManager] Error syncing exposure: {e}")
            
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
    
    def on_live_camera_clicked(self):
        """Xử lý khi click Live Camera button"""
        current_checked = self.live_camera_btn.isChecked() if self.live_camera_btn else False
        print(f"DEBUG: [CameraManager] Live camera button clicked, checked: {current_checked}, current_mode: {self.current_mode}")
        
        if current_checked:
            # Button được click để bật live mode
            print("DEBUG: [CameraManager] Starting live mode")
            if self.current_mode == 'trigger':
                # Reset trigger mode first
                self.current_mode = None
                
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
            # Button được click để tắt live mode
            print("DEBUG: [CameraManager] Stopping live mode")
            success = self.toggle_live_camera(False)
            if success:
                self.current_mode = None
            # Keep button unchecked regardless
        
        # Update UI to reflect current state
        self.update_camera_mode_ui()
    
    def on_trigger_camera_clicked(self):
        """Xử lý khi click Trigger Camera button"""
        if self.current_mode == 'trigger':
            # Đang ở trigger mode, tắt mode
            self.current_mode = None
        else:
            # Chuyển sang trigger mode
            if self.current_mode == 'live':
                # Tắt live trước
                self.toggle_live_camera(False)
            self.current_mode = 'trigger'
            
        # Trigger capture chỉ khi đang ở trigger mode
        if self.current_mode == 'trigger':
            print("DEBUG: Triggering capture...")
            self.trigger_capture()
        
        self.update_camera_mode_ui()
    
    def update_camera_mode_ui(self):
        """Cập nhật UI theo camera mode hiện tại"""
        if self.live_camera_btn and self.trigger_camera_btn:
            if self.current_mode == 'live':
                # Block signals to prevent recursive calls
                self.live_camera_btn.blockSignals(True)
                self.live_camera_btn.setChecked(True)
                self.live_camera_btn.setText("Stop Live")
                self.live_camera_btn.setStyleSheet("background-color: #ff6b6b")  # Red
                self.live_camera_btn.blockSignals(False)
                
                self.trigger_camera_btn.setEnabled(False)
                self.trigger_camera_btn.setText("Trigger Camera")
                self.trigger_camera_btn.setStyleSheet("")
            elif self.current_mode == 'trigger':
                self.trigger_camera_btn.setText("Trigger Ready")
                self.trigger_camera_btn.setStyleSheet("background-color: #4ecdc4")  # Teal
                
                self.live_camera_btn.setEnabled(False)
                self.live_camera_btn.blockSignals(True)
                self.live_camera_btn.setChecked(False)
                self.live_camera_btn.setText("Live Camera")
                self.live_camera_btn.setStyleSheet("")
                self.live_camera_btn.blockSignals(False)
            else:
                # No mode selected
                self.live_camera_btn.blockSignals(True)
                self.live_camera_btn.setChecked(False)
                self.live_camera_btn.setText("Live Camera")
                self.live_camera_btn.setStyleSheet("")
                self.live_camera_btn.setEnabled(True)
                self.live_camera_btn.blockSignals(False)
                
                self.trigger_camera_btn.setText("Trigger Camera")
                self.trigger_camera_btn.setStyleSheet("")
                self.trigger_camera_btn.setEnabled(True)
    
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
    
    # ============ SETTINGS HANDLERS ============
    
    def on_apply_settings_clicked(self):
        """Áp dụng tất cả settings đã thay đổi"""
        try:
            # Kiểm tra xem có đang ở chế độ live camera không
            was_live_active = self.current_mode == 'live' and self.camera_stream and self.camera_stream.is_live
            
            # Nếu đang live, tạm dừng để apply settings
            if was_live_active:
                self.camera_stream.stop_live()
            
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
            
            # Hiển thị dialog thông báo thành công
            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Thành công")
            msg.setText("Đã áp dụng cài đặt camera thành công!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            
            logging.info("Camera settings applied successfully")
            
        except Exception as e:
            logging.error(f"Error applying camera settings: {str(e)}")
    
    def on_cancel_settings_clicked(self):
        """Hủy bỏ tất cả thay đổi và khôi phục giá trị mặc định"""
        try:
            # Reset to default values
            self._is_auto_exposure = True
            
            # Reset UI values
            if self.exposure_edit:
                self.exposure_edit.setValue(10000.0)  # 10000 microseconds (10ms)
            if self.gain_slider:
                self.gain_slider.setValue(100)  # 1.0 gain
            if self.gain_edit:
                self.gain_edit.setValue(1.0)
            if self.ev_slider:
                self.ev_slider.setValue(0)
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
            
    def cleanup(self):
        """Dọn dẹp tài nguyên camera khi thoát ứng dụng"""
        logger = logging.getLogger(__name__)
        try:
            # Dừng live preview nếu đang chạy
            if self.camera_stream and hasattr(self.camera_stream, 'stop_live'):
                logger.info("Stopping camera live preview...")
                self.camera_stream.stop_live()
            
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
