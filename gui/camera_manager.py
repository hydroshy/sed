from PyQt5.QtCore import QObject, pyqtSlot
from camera.camera_stream import CameraStream
from gui.camera_view import CameraView
import logging

class CameraManager(QObject):
    """
    Quản lý camera và xử lý tương tác với camera
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.camera_stream = None
        self.camera_view = None
        self.exposure_slider = None
        self.exposure_edit = None
        self.gain_slider = None
        self.gain_edit = None
        self.ev_slider = None
        self.ev_edit = None
        self.focus_bar = None
        self.fps_num = None
        self._is_auto_exposure = True
        
    def setup(self, camera_view_widget, exposure_slider, exposure_edit,
             gain_slider, gain_edit, ev_slider, ev_edit, focus_bar, fps_num):
        """Thiết lập các tham chiếu đến các widget UI và khởi tạo camera"""
        # Khởi tạo camera stream
        self.camera_stream = CameraStream()
        
        # Khởi tạo camera view
        self.camera_view = CameraView(camera_view_widget)
        self.camera_stream.frame_ready.connect(self.camera_view.display_frame)
        
        # Kết nối các widget
        self.exposure_slider = exposure_slider
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
        
        # Bật hiển thị FPS
        self.camera_view.toggle_fps_display(True)
        
        # Khởi tạo mặc định auto exposure
        self.set_auto_exposure_mode()
        
        # Kết nối signal cho các tham số camera
        self.setup_camera_param_signals()
        
        logging.info("CameraManager: Setup completed")
        
    def setup_camera_param_signals(self):
        """Kết nối các signal và slot cho các tham số camera"""
        # Exposure
        if self.exposure_slider:
            self.exposure_slider.valueChanged.connect(self.on_exposure_slider_changed)
        if self.exposure_edit:
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
            
    def set_exposure(self, value):
        """Đặt giá trị phơi sáng cho camera"""
        if self.exposure_edit:
            self.exposure_edit.setText(str(value))
        if self.exposure_slider:
            self.exposure_slider.setValue(int(value))
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

    def on_exposure_slider_changed(self, value):
        """Xử lý khi người dùng thay đổi slider phơi sáng"""
        if self.exposure_edit:
            self.exposure_edit.setText(str(value))
        if hasattr(self.camera_stream, 'set_exposure'):
            self.camera_stream.set_exposure(value)

    def on_exposure_edit_changed(self):
        """Xử lý khi người dùng thay đổi giá trị phơi sáng trong ô văn bản"""
        try:
            if self.exposure_edit:
                value = int(self.exposure_edit.text())
                if self.exposure_slider:
                    self.exposure_slider.setValue(value)
                if hasattr(self.camera_stream, 'set_exposure'):
                    self.camera_stream.set_exposure(value)
        except ValueError:
            pass

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
        # Lấy giá trị thực tế từ camera nếu có API
        if hasattr(self.camera_stream, 'get_exposure'):
            exposure = self.camera_stream.get_exposure()
            self.set_exposure(exposure)
        if hasattr(self.camera_stream, 'get_gain'):
            gain = self.camera_stream.get_gain()
            self.set_gain(gain)
        if hasattr(self.camera_stream, 'get_ev'):
            ev = self.camera_stream.get_ev()
            self.set_ev(ev)
            
    def toggle_live_camera(self, checked):
        """Bật/tắt chế độ camera trực tiếp"""
        if not self.camera_stream:
            return
            
        if checked:
            self.camera_stream.start_live()
        else:
            self.camera_stream.stop_live()
            
    def set_auto_exposure_mode(self):
        """Đặt chế độ tự động phơi sáng"""
        self._is_auto_exposure = True
        if hasattr(self.camera_stream, 'set_auto_exposure'):
            self.camera_stream.set_auto_exposure(True)
        
        # Disable các widget điều chỉnh phơi sáng
        if self.exposure_slider:
            self.exposure_slider.setEnabled(False)
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
        
        # Enable các widget điều chỉnh phơi sáng
        if self.exposure_slider:
            self.exposure_slider.setEnabled(True)
        if self.exposure_edit:
            self.exposure_edit.setEnabled(True)
        if self.gain_slider:
            self.gain_slider.setEnabled(True)
        if self.gain_edit:
            self.gain_edit.setEnabled(True)
        if self.ev_slider:
            self.ev_slider.setEnabled(True)
        if self.ev_edit:
            self.ev_edit.setEnabled(True)
            
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
            self.camera_stream.trigger_capture()
            
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
