#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Button Trigger Camera

Module để kích hoạt camera thông qua GPIO pin 17 trên Raspberry Pi
sử dụng thư viện gpiozero.

NOTE: Trigger mode hiện tại đã được thay đổi để sử dụng capture_request() 
thay vì GPIO trigger. Module này được giữ lại để tham khảo hoặc để quay lại 
GPIO trigger nếu cần.

Hiện tại:
- CameraManager.activate_capture_request() sử dụng CameraStream.capture_single_frame_request()
- capture_single_frame_request() sử dụng picamera2.capture_request() 
- Không cần GPIO trigger hay sysfs parameters nữa

Version: 1.2 (Legacy)
- Tối ưu hóa API: xóa hàm initialize_trigger() không cần thiết
- Cải thiện quản lý tài nguyên GPIO
- Tự động dọn dẹp sau mỗi lần trigger
- Hỗ trợ gpiozero và fallback sang RPi.GPIO
"""

import sys
import time
import logging
import threading

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


class CameraTrigger:
    """Class quản lý việc kích hoạt camera qua GPIO sử dụng gpiozero"""
    
    def __init__(self, gpio_pin=17, pulse_us=10000, inverted=False):
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
                # Sẽ sử dụng chế độ giả lập khi không thể khởi tạo GPIO
    
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


# Biến toàn cục để lưu trữ đối tượng trigger
_camera_trigger = None

def trigger_camera(gpio_pin=17, pulse_us=10000, inverted=False, blocking=False):
    """Kích hoạt camera thông qua GPIO
    
    Args:
        gpio_pin: Số GPIO pin sử dụng (mặc định là 17)
        pulse_us: Độ rộng xung tính bằng µs (microseconds)
        inverted: Chế độ hoạt động (True = ngược, False = thường)
        blocking: Nếu True, hàm sẽ chờ cho đến khi trigger hoàn tất
                 Nếu False, trigger sẽ được thực hiện trong thread riêng
    
    Returns:
        bool: True nếu trigger thành công hoặc đã được gửi đi, False nếu lỗi
    """
    global _camera_trigger
    
    # Dọn dẹp trigger cũ nếu có
    if _camera_trigger is not None:
        _camera_trigger.cleanup()
        _camera_trigger = None
    
    # Tạo trigger mới với cấu hình được yêu cầu
    _camera_trigger = CameraTrigger(gpio_pin, pulse_us, inverted)
    
    # Thực hiện trigger
    if blocking:
        # Chế độ chặn - chờ cho đến khi hoàn tất
        result = _camera_trigger.fire_trigger()
        # Dọn dẹp sau khi hoàn tất
        _camera_trigger.cleanup()
        _camera_trigger = None
        return result
    else:
        # Chế độ không chặn - thực hiện trong thread riêng
        def trigger_and_cleanup():
            try:
                result = _camera_trigger.fire_trigger()
                return result
            finally:
                # Dọn dẹp sau khi trigger xong
                if _camera_trigger:
                    _camera_trigger.cleanup()
        
        thread = threading.Thread(target=trigger_and_cleanup)
        thread.daemon = True  # Thread sẽ tự kết thúc khi ứng dụng đóng
        thread.start()
        return True

def cleanup_trigger():
    """Dọn dẹp tài nguyên GPIO"""
    global _camera_trigger
    
    if _camera_trigger is not None:
        _camera_trigger.cleanup()
        _camera_trigger = None