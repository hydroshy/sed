#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple GPIO Trigger

Ứng dụng đơn giản để kích hoạt (trigger) GPIO pin 4 trên Raspberry Pi 
mà không cần kích hoạt camera hay bất kỳ thiết bị nào khác.
"""

import sys
import time
import logging
import argparse
import threading
from PyQt5 import QtWidgets, QtCore, QtGui

# Cấu hình logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Thử import gpiozero (thư viện GPIO cao cấp cho Raspberry Pi)
try:
    from gpiozero import OutputDevice
    HAS_GPIO = True
    logger.info("gpiozero imported successfully")
    
    # Kiểm tra quyền truy cập GPIO
    try:
        # Thử tạo một OutputDevice để kiểm tra quyền
        test_device = OutputDevice(17, active_high=True)
        test_device.close()  # Đóng ngay sau khi kiểm tra
        logger.info("GPIO access permission OK (gpiozero)")
    except PermissionError:
        logger.warning("Permission denied accessing GPIO with gpiozero. You may need to run:")
        logger.warning("sudo usermod -a -G gpio $USER")
        logger.warning("Then log out and log back in, or run the script with sudo")
    except Exception as e:
        logger.warning(f"GPIO access check error: {e}")
        
except ImportError:
    # Thử dùng RPi.GPIO nếu không có gpiozero
    try:
        import RPi.GPIO as GPIO
        HAS_GPIO = True
        logger.info("RPi.GPIO imported successfully (fallback)")
        # Cấu hình GPIO
        GPIO.setmode(GPIO.BCM)
        
        # Kiểm tra quyền truy cập
        try:
            # Thử truy cập /dev/gpiomem để kiểm tra quyền
            with open('/dev/gpiomem', 'rb') as f:
                logger.info("GPIO access permission OK")
        except PermissionError:
            logger.warning("Permission denied accessing /dev/gpiomem. You may need to run:")
            logger.warning("sudo usermod -a -G gpio $USER")
            logger.warning("Then log out and log back in, or run the script with sudo")
        except FileNotFoundError:
            logger.warning("GPIO device not found. Are you running on a Raspberry Pi?")
    except ImportError:
        HAS_GPIO = False
        logger.warning("Failed to import both gpiozero and RPi.GPIO, using dummy GPIO")


class GPIOTrigger:
    """Class quản lý việc kích hoạt GPIO sử dụng gpiozero"""
    
    def __init__(self, gpio_pin=17, pulse_us=1000, inverted=True):
        """Khởi tạo GPIO trigger
        
        Args:
            gpio_pin: Số GPIO pin sử dụng (mặc định là 17 cho camera trigger)
            pulse_us: Độ rộng xung tính bằng µs (microseconds)
            inverted: Nếu True, XTR camera rảnh ở mức CAO (HIGH), kích hoạt ở mức THẤP (LOW)
                     Nếu False, ngược lại
        """
        self.gpio_pin = gpio_pin
        self.pulse_us = pulse_us
        self.trigger_count = 0
        self.last_trigger_time = 0
        self.initialized = False
        self.inverted = inverted  # Chế độ ngược (XTR rảnh ở mức CAO)
        
        # Biến lưu trữ tài nguyên GPIO
        self.gpio_device = None
        self.using_gpiozero = False
        self.using_rpi_gpio = False
        
        # Khởi tạo GPIO nếu có
        if HAS_GPIO:
            try:
                # Thử sử dụng gpiozero (thư viện cao cấp)
                if 'gpiozero' in sys.modules:
                    # active_high quyết định liệu giá trị 1 có nghĩa là HIGH hay LOW
                    # Nếu inverted=True: XTR rảnh ở mức CAO, active ở mức THẤP
                    # Trong trường hợp này, active_high=False để khi value=1, điện áp thực sự là LOW
                    active_high = not inverted
                    
                    # Khởi tạo OutputDevice với trạng thái ban đầu
                    # initial_value=False để giá trị ban đầu ở trạng thái không active
                    # Với active_high=False, điều này có nghĩa là đặt thành HIGH (cho XTR)
                    self.gpio_device = OutputDevice(
                        pin=gpio_pin,
                        active_high=active_high,
                        initial_value=False  # Bắt đầu ở trạng thái không active
                    )
                    
                    self.using_gpiozero = True
                    self.initialized = True
                    logger.info(f"GPIO {self.gpio_pin} configured as output using gpiozero")
                    logger.info(f"Inverted mode: {inverted}, active_high: {active_high}")
                    
                # Fallback to RPi.GPIO nếu không có gpiozero
                elif 'RPi.GPIO' in sys.modules:
                    GPIO.setup(self.gpio_pin, GPIO.OUT, 
                              initial=GPIO.HIGH if inverted else GPIO.LOW)
                    self.using_rpi_gpio = True
                    self.initialized = True
                    logger.info(f"GPIO {self.gpio_pin} configured as output using RPi.GPIO")
            except Exception as e:
                logger.error(f"Error configuring GPIO: {e}")
    
    def fire_trigger(self):
        """Phát xung theo cấu hình
        
        Returns:
            bool: True nếu kích hoạt thành công, False nếu không
        """
        if not self.initialized:
            logger.warning("GPIO not initialized, trigger ignored")
            return False
            
        self.trigger_count += 1
        self.last_trigger_time = time.time()
        
        try:
            # Phương pháp sử dụng gpiozero
            if self.using_gpiozero and self.gpio_device:
                # Phát xung kích hoạt sử dụng gpiozero
                logger.info(f"Triggering GPIO {self.gpio_pin} with {self.pulse_us}µs pulse using gpiozero (#{self.trigger_count})")
                
                # Bật
                self.gpio_device.on()  # Đặt output thành active
                
                # Đợi theo độ rộng xung
                time.sleep(self.pulse_us / 1_000_000)
                
                # Tắt
                self.gpio_device.off()  # Trở về trạng thái rảnh
                
                return True
                
            # Phương pháp sử dụng RPi.GPIO
            elif self.using_rpi_gpio:
                # Phát xung kích hoạt sử dụng RPi.GPIO
                logger.info(f"Triggering GPIO {self.gpio_pin} with {self.pulse_us}µs pulse using RPi.GPIO (#{self.trigger_count})")
                
                # Xác định mức logic dựa vào chế độ inverted
                active_level = GPIO.LOW if self.inverted else GPIO.HIGH
                idle_level = GPIO.HIGH if self.inverted else GPIO.LOW
                
                GPIO.output(self.gpio_pin, active_level)  # Kích hoạt
                time.sleep(self.pulse_us / 1_000_000)  # Chờ theo độ rộng xung
                GPIO.output(self.gpio_pin, idle_level)  # Trở về trạng thái rảnh
                
                return True
            else:
                # Giả lập xung (khi không có GPIO thực)
                logger.info(f"[SIMULATION] Triggering GPIO {self.gpio_pin} with {self.pulse_us}µs pulse (#{self.trigger_count})")
                time.sleep(self.pulse_us / 1_000_000)
                
                return True
        except Exception as e:
            logger.error(f"Error triggering GPIO: {e}")
            return False
    
    def set_pulse_width(self, pulse_us):
        """Thiết lập độ rộng xung trigger
        
        Args:
            pulse_us: Độ rộng xung tính bằng µs (microseconds)
        """
        self.pulse_us = pulse_us
        logger.info(f"Pulse width set to {pulse_us}µs")
    
    def cleanup(self):
        """Dọn dẹp GPIO khi kết thúc"""
        try:
            # Dọn dẹp tài nguyên gpiozero
            if self.using_gpiozero and self.gpio_device:
                try:
                    # Đặt về trạng thái không active trước khi đóng
                    self.gpio_device.off()
                    # Đóng thiết bị và giải phóng pin
                    self.gpio_device.close()
                    logger.info(f"GPIO {self.gpio_pin} cleaned up (gpiozero)")
                except Exception as e:
                    logger.error(f"Error cleaning up GPIO via gpiozero: {e}")
                
                # Thiết lập gpio_device thành None
                self.gpio_device = None
            
            # Xử lý RPi.GPIO
            elif self.using_rpi_gpio:
                try:
                    GPIO.cleanup(self.gpio_pin)
                    logger.info(f"GPIO {self.gpio_pin} cleaned up (RPi.GPIO)")
                except Exception as e:
                    logger.error(f"Error cleaning up GPIO via RPi.GPIO: {e}")
                
            # Thông báo kết thúc
            self.initialized = False
        except Exception as e:
            logger.error(f"Error cleaning up GPIO: {e}")


class TriggerApp(QtWidgets.QMainWindow):
    """Ứng dụng đơn giản để kích hoạt GPIO"""
    
    def __init__(self):
        super().__init__()
        self.gpio_trigger = None
        self.trigger_count = 0
        self.last_trigger_time = 0
        self.auto_trigger_active = False
        
        self.init_ui()
        self.init_gpio()
    
    def init_ui(self):
        """Khởi tạo giao diện người dùng"""
        # Thiết lập cửa sổ chính
        self.setWindowTitle("Simple GPIO Trigger")
        self.setGeometry(100, 100, 400, 250)
        
        # Widget chính
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout chính
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        
        # Nhóm thiết lập GPIO
        gpio_group = QtWidgets.QGroupBox("GPIO Settings")
        gpio_layout = QtWidgets.QFormLayout()
        
        # Chọn GPIO pin
        self.pin_selector = QtWidgets.QSpinBox()
        self.pin_selector.setRange(1, 27)  # GPIO pins on Raspberry Pi
        self.pin_selector.setValue(17)  # Default to GPIO 17 for camera external trigger
        self.pin_selector.valueChanged.connect(self.on_pin_changed)
        gpio_layout.addRow("GPIO Pin:", self.pin_selector)
        
        # Thiết lập độ rộng xung
        self.pulse_width = QtWidgets.QSpinBox()
        self.pulse_width.setRange(100, 10000)  # 100µs to 10ms
        self.pulse_width.setValue(1000)
        self.pulse_width.setSingleStep(100)
        self.pulse_width.setSuffix(" µs")
        self.pulse_width.valueChanged.connect(self.on_pulse_width_changed)
        gpio_layout.addRow("Pulse Width:", self.pulse_width)
        
        # Checkbox cho chế độ kích hoạt ngược (XTR rảnh ở mức CAO)
        self.inverted_mode = QtWidgets.QCheckBox("Inverted Mode (XTR idle HIGH, active LOW)")
        self.inverted_mode.setChecked(True)  # Mặc định là chế độ ngược cho camera XTR
        self.inverted_mode.setToolTip("Check for Raspberry Pi Camera (XTR idle at HIGH, active at LOW)")
        self.inverted_mode.toggled.connect(self.on_inverted_mode_changed)
        gpio_layout.addRow("Trigger Mode:", self.inverted_mode)
        
        # Thêm nhãn giải thích
        info_label = QtWidgets.QLabel(
            "Camera XTR: rảnh ở mức CAO (1.8V), kéo THẤP để phơi sáng"
        )
        info_label.setStyleSheet("font-style: italic; color: #666;")
        gpio_layout.addRow("", info_label)
        
        gpio_group.setLayout(gpio_layout)
        
        # Nhóm kích hoạt
        trigger_group = QtWidgets.QGroupBox("Trigger Control")
        trigger_layout = QtWidgets.QVBoxLayout()
        
        # Nút kích hoạt
        self.trigger_button = QtWidgets.QPushButton("Trigger Now")
        self.trigger_button.setMinimumHeight(50)
        self.trigger_button.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.trigger_button.clicked.connect(self.on_trigger_button_clicked)
        trigger_layout.addWidget(self.trigger_button)
        
        # Thiết lập tự động kích hoạt
        auto_layout = QtWidgets.QHBoxLayout()
        auto_layout.addWidget(QtWidgets.QLabel("Auto Trigger (Hz):"))
        
        self.auto_trigger_spinner = QtWidgets.QDoubleSpinBox()
        self.auto_trigger_spinner.setRange(0, 30)
        self.auto_trigger_spinner.setSingleStep(1)
        self.auto_trigger_spinner.setValue(0)  # Mặc định là 0 (tắt)
        self.auto_trigger_spinner.setDecimals(1)
        self.auto_trigger_spinner.valueChanged.connect(self.on_auto_trigger_changed)
        auto_layout.addWidget(self.auto_trigger_spinner)
        
        trigger_layout.addLayout(auto_layout)
        
        # Trạng thái trigger
        status_layout = QtWidgets.QHBoxLayout()
        status_layout.addWidget(QtWidgets.QLabel("Trigger Count:"))
        self.trigger_count_label = QtWidgets.QLabel("0")
        self.trigger_count_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.trigger_count_label)
        
        status_layout.addWidget(QtWidgets.QLabel("Last Trigger:"))
        self.last_trigger_label = QtWidgets.QLabel("None")
        status_layout.addWidget(self.last_trigger_label)
        
        trigger_layout.addLayout(status_layout)
        
        # Trạng thái GPIO
        self.gpio_status = QtWidgets.QLabel("GPIO Ready")
        self.gpio_status.setStyleSheet("font-style: italic;")
        trigger_layout.addWidget(self.gpio_status)
        
        trigger_group.setLayout(trigger_layout)
        
        # Thêm các nhóm vào layout chính
        main_layout.addWidget(gpio_group)
        main_layout.addWidget(trigger_group)
        
        # Timer cho auto trigger
        self.auto_trigger_timer = QtCore.QTimer()
        self.auto_trigger_timer.timeout.connect(self.auto_fire_trigger)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def init_gpio(self):
        """Khởi tạo GPIO trigger"""
        pin = self.pin_selector.value()
        pulse_us = self.pulse_width.value()
        inverted = self.inverted_mode.isChecked()
        
        self.gpio_trigger = GPIOTrigger(gpio_pin=pin, pulse_us=pulse_us, inverted=inverted)
        
        if self.gpio_trigger.initialized:
            if HAS_GPIO:
                if pin == 17:
                    status = "Camera Trigger Ready (GPIO 17)"
                    self.gpio_status.setStyleSheet("font-weight: bold; color: green;")
                    self.statusBar().showMessage("GPIO 17 initialized for camera external trigger")
                else:
                    status = f"GPIO {pin} Ready"
                    self.gpio_status.setStyleSheet("font-weight: bold; color: blue;")
            else:
                status = "Simulation Mode"
                self.gpio_status.setStyleSheet("font-weight: bold; color: orange;")
            
            self.gpio_status.setText(status)
        else:
            self.gpio_status.setText("GPIO Error - Permission Issue?")
            self.gpio_status.setStyleSheet("font-weight: bold; color: red;")
            self.statusBar().showMessage("GPIO initialization failed. Check permissions or run with sudo")
    
    def on_pin_changed(self, value):
        """Xử lý khi thay đổi GPIO pin"""
        # Dọn dẹp GPIO cũ
        if self.gpio_trigger:
            self.gpio_trigger.cleanup()
        
        # Khởi tạo GPIO mới
        self.gpio_trigger = GPIOTrigger(
            gpio_pin=value,
            pulse_us=self.pulse_width.value(),
            inverted=self.inverted_mode.isChecked()
        )
        
        if self.gpio_trigger.initialized:
            self.statusBar().showMessage(f"GPIO pin changed to {value}")
        else:
            self.statusBar().showMessage(f"Failed to initialize GPIO pin {value}")
    
    def on_pulse_width_changed(self, value):
        """Xử lý khi thay đổi độ rộng xung"""
        if self.gpio_trigger:
            self.gpio_trigger.set_pulse_width(value)
            self.statusBar().showMessage(f"Pulse width set to {value}µs")
    
    def on_inverted_mode_changed(self, checked):
        """Xử lý khi thay đổi chế độ đảo ngược"""
        # Dọn dẹp GPIO cũ
        if self.gpio_trigger:
            self.gpio_trigger.cleanup()
        
        # Khởi tạo GPIO mới với chế độ đảo ngược mới
        self.gpio_trigger = GPIOTrigger(
            gpio_pin=self.pin_selector.value(),
            pulse_us=self.pulse_width.value(),
            inverted=checked
        )
        
        mode_str = "inverted (XTR idle HIGH, active LOW)" if checked else "normal (idle LOW, active HIGH)"
        self.statusBar().showMessage(f"Trigger mode changed to {mode_str}")
    
    def on_auto_trigger_changed(self, value):
        """Xử lý khi thay đổi tần số tự động kích hoạt"""
        if value > 0:
            # Bật auto trigger
            interval_ms = int(1000 / value)
            self.auto_trigger_timer.start(interval_ms)
            self.auto_trigger_active = True
            self.statusBar().showMessage(f"Auto trigger enabled at {value}Hz (every {interval_ms}ms)")
            self.trigger_button.setEnabled(False)
        else:
            # Tắt auto trigger
            self.auto_trigger_timer.stop()
            self.auto_trigger_active = False
            self.statusBar().showMessage("Auto trigger disabled")
            self.trigger_button.setEnabled(True)
    
    def on_trigger_button_clicked(self):
        """Xử lý khi nút trigger được nhấn"""
        # Disable button ngay lập tức để tránh nhấn nhiều lần
        self.trigger_button.setEnabled(False)
        self.statusBar().showMessage("Triggering GPIO...")
        
        # Thực hiện trigger trong thread riêng để không block UI
        threading.Thread(target=self._trigger_and_update_ui).start()
    
    def auto_fire_trigger(self):
        """Thực hiện tự động kích hoạt khi timer kích hoạt"""
        if not self.auto_trigger_active:
            return
            
        threading.Thread(target=self._trigger_and_update_ui).start()
    
    def _trigger_and_update_ui(self):
        """Hàm thực hiện trigger và cập nhật UI sau khi xong"""
        # Thực hiện trigger
        success = self.gpio_trigger.fire_trigger()
        
        # Cập nhật UI trên thread chính
        QtCore.QMetaObject.invokeMethod(
            self, "_update_ui_after_trigger", 
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(bool, success)
        )
    
    @QtCore.pyqtSlot(bool)
    def _update_ui_after_trigger(self, success):
        """Cập nhật UI sau khi trigger xong"""
        if not self.auto_trigger_active:
            self.trigger_button.setEnabled(True)
        
        if success:
            # Cập nhật thông tin trigger
            self.trigger_count = self.gpio_trigger.trigger_count
            self.last_trigger_time = self.gpio_trigger.last_trigger_time
            
            # Cập nhật UI
            self.trigger_count_label.setText(str(self.trigger_count))
            
            timestamp = time.strftime("%H:%M:%S", time.localtime(self.last_trigger_time))
            self.last_trigger_label.setText(timestamp)
            
            # Cập nhật status bar
            pin = self.gpio_trigger.gpio_pin
            pulse = self.gpio_trigger.pulse_us
            self.statusBar().showMessage(f"Triggered GPIO{pin} with {pulse}µs pulse")
        else:
            self.statusBar().showMessage("Trigger failed!")
    
    def closeEvent(self, event):
        """Xử lý khi đóng ứng dụng"""
        # Dừng timer nếu đang chạy
        if self.auto_trigger_timer.isActive():
            self.auto_trigger_timer.stop()
        
        # Dọn dẹp GPIO
        if self.gpio_trigger:
            self.gpio_trigger.cleanup()
        
        # Chấp nhận sự kiện đóng
        event.accept()


def parse_arguments():
    """Phân tích đối số dòng lệnh"""
    parser = argparse.ArgumentParser(description="Simple GPIO Trigger Application")
    parser.add_argument('-p', '--pin', type=int, default=17,
                        help='GPIO pin number (BCM mode, default: 17 for camera trigger)')
    parser.add_argument('-w', '--pulse-width', type=int, default=1000,
                        help='Pulse width in microseconds (default: 1000)')
    parser.add_argument('-a', '--auto', type=float, default=0,
                        help='Auto trigger frequency in Hz (default: 0, disabled)')
    parser.add_argument('--force-root', action='store_true',
                        help='Try to force GPIO access even if not in gpio group')
    return parser.parse_args()


def main():
    """Hàm chính của ứng dụng"""
    # Phân tích đối số
    args = parse_arguments()
    
    # Kiểm tra quyền truy cập GPIO nếu yêu cầu
    if args.force_root and HAS_GPIO:
        try:
            # Thử thiết lập quyền truy cập GPIO
            import os
            if os.geteuid() != 0:  # Không chạy với quyền root
                logger.warning("--force-root flag set but not running as root")
                logger.warning("Some GPIO operations may fail due to permission issues")
            else:
                # Thiết lập quyền cho GPIO
                try:
                    os.system("chmod -R ug+rwx /dev/gpiomem")
                    os.system("chown -R root:gpio /dev/gpiomem")
                    logger.info("GPIO permissions updated")
                except Exception as e:
                    logger.error(f"Error setting GPIO permissions: {e}")
        except Exception as e:
            logger.error(f"Error checking permissions: {e}")
    
    # Khởi tạo ứng dụng
    app = QtWidgets.QApplication(sys.argv)
    trigger_app = TriggerApp()
    
    # Thiết lập ban đầu từ đối số dòng lệnh
    trigger_app.pin_selector.setValue(args.pin)
    trigger_app.pulse_width.setValue(args.pulse_width)
    if args.auto > 0:
        trigger_app.auto_trigger_spinner.setValue(args.auto)
    
    # Hiển thị ứng dụng
    trigger_app.show()
    
    # Chạy vòng lặp sự kiện
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()