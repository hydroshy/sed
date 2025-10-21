from machine import Pin, UART
import utime
import json

# ==== Cấu hình ====
START_SENSOR_PIN = 27        # vào từ opto (Autonics) - đầu băng tải
END_SENSOR_PIN   = 26        # sensor cuối băng tải
LED_PIN_NAME     = "LED"     # LED onboard để debug

# ==== Cấu hình UART ====
uart = UART(0,                    # UART0: GP0 (TX), GP1 (RX)
           baudrate=115200,       # Tốc độ baudrate
           tx=Pin(0),            # TX pin
           rx=Pin(1),            # RX pin
           timeout=100)          # timeout cho đọc UART (ms)

# ==== Khởi tạo chân ====
start_sensor = Pin(START_SENSOR_PIN, Pin.IN, Pin.PULL_UP)
end_sensor = Pin(END_SENSOR_PIN, Pin.IN, Pin.PULL_UP)
led = Pin(LED_PIN_NAME, Pin.OUT)

# ==== Protocol Constants ====
ACK = b'ACK\n'
NACK = b'NACK\n'
SYNC = b'SYNC\n'
CONNECTED = False  # Trạng thái kết nối

# ==== LED Patterns ====
LED_STARTUP_BLINKS = 5      # Số lần nhấp nháy khi khởi động
LED_HANDSHAKE_BLINKS = 2    # Số lần nhấp nháy khi bắt đầu handshake
LED_ERROR_BLINKS = 3        # Số lần nhấp nháy khi có lỗi
LED_SUCCESS_ON = True       # LED sáng liên tục khi thành công

# Trạng thái ban đầu và nhấp nháy khởi động
led.value(0)
for _ in range(LED_STARTUP_BLINKS):  # Nhấp nháy báo khởi động
    led.value(1)
    utime.sleep_ms(50)
    led.value(0)
    utime.sleep_ms(50)

# ==== Các tham số ====
DEBOUNCE_MS = 10       # Phần mềm debounce: thời gian ổn định (ms)
MIN_GAP_MS = 10        # Thời gian tối thiểu giữa 2 lần trigger
HANDSHAKE_TIMEOUT = 3000  # Timeout cho handshake (ms)
RETRY_INTERVAL = 1000     # Thời gian giữa các lần thử kết nối lại (ms)

# ==== Biến trạng thái ====
event_flag = False     # Set bởi IRQ, kiểm tra trong vòng lặp chính
event_time_ms = 0      # Thời điểm xảy ra event
last_trigger_ms = 0    # Thời điểm trigger cuối cùng
last_sync_ms = 0       # Thời điểm sync cuối cùng

def blink_led(times=3, delay_ms=100):
    """Nhấp nháy LED
    Args:
        times: Số lần nhấp nháy
        delay_ms: Thời gian delay giữa mỗi lần nhấp nháy (ms)
    """
    for _ in range(times):
        led.value(1)
        utime.sleep_ms(delay_ms)
        led.value(0)
        utime.sleep_ms(delay_ms)

def perform_handshake():
    """Thực hiện handshake với Pi 5
    Returns:
        bool: True nếu handshake thành công, False nếu thất bại
    """
    global CONNECTED, last_sync_ms
    
    print("Initiating handshake...")
    start_time = utime.ticks_ms()
    
    # LED nhấp nháy nhanh 2 lần để chỉ báo bắt đầu handshake
    blink_led(times=2, delay_ms=50)
    
    while utime.ticks_diff(utime.ticks_ms(), start_time) < HANDSHAKE_TIMEOUT:
        # Gửi SYNC
        uart.write(SYNC)
        led.value(1)  # LED sáng khi đang gửi SYNC
        utime.sleep_ms(50)
        led.value(0)
        
        # Đợi phản hồi
        if uart.any():
            response = uart.read()
            if response == ACK:
                print("Handshake successful!")
                CONNECTED = True
                last_sync_ms = utime.ticks_ms()
                # LED sáng liên tục khi kết nối thành công
                led.value(1)
                return True
    
    print("Handshake timeout!")
    CONNECTED = False
    # LED nhấp nháy chậm 3 lần để chỉ báo handshake thất bại
    blink_led(times=3, delay_ms=200)
    led.value(0)
    return False

def send_trigger_command():
    """Gửi lệnh trigger qua UART với xác nhận
    Returns:
        bool: True nếu lệnh được xác nhận, False nếu thất bại
    """
    if not CONNECTED:
        print("Not connected, attempting handshake...")
        if not perform_handshake():
            return False
    
    try:
        # Tạo gói tin JSON với timestamp
        message = {
            "cmd": "TRIGGER",
            "timestamp": utime.ticks_ms(),
            "sensor": "START"  # có thể mở rộng thêm thông tin
        }
        
        # Gửi và đợi ACK
        uart.write(json.dumps(message).encode() + b'\n')
        
        # Đợi ACK trong 100ms
        start_wait = utime.ticks_ms()
        while utime.ticks_diff(utime.ticks_ms(), start_wait) < 100:
            if uart.any():
                response = uart.read()
                if response == ACK:
                    led.value(1)  # Nhấp LED để debug
                    utime.sleep_ms(50)
                    led.value(0)
                    return True
                elif response == NACK:
                    print("Trigger NACK received")
                    return False
        
        print("Trigger timeout")
        CONNECTED = False  # Reset kết nối nếu timeout
        return False
        
    except Exception as e:
        print("Send error:", e)
        CONNECTED = False
        return False

def on_edge(pin):
    """IRQ handler: chỉ đánh dấu sự kiện và ghi thời điểm
    Để tránh nhiễu EMI từ động cơ, không thực hiện logic nặng trong IRQ.
    """
    global event_flag, event_time_ms
    event_time_ms = utime.ticks_ms()
    event_flag = True

# Nếu opto nhả ra (OFF) -> bắt RISING
start_sensor.irq(trigger=Pin.IRQ_RISING, handler=on_edge)

print("Ready: UART Trigger System with Handshake")
print("- Start sensor: GP%d" % START_SENSOR_PIN)
print("- End sensor: GP%d" % END_SENSOR_PIN)
print("- UART: TX=GP0, RX=GP1, baudrate=115200")

# Thử kết nối ban đầu
perform_handshake()

# ==== Vòng lặp chính ====
while True:
    now_ms = utime.ticks_ms()

    # Kiểm tra và duy trì kết nối
    if CONNECTED:
        # Gửi SYNC định kỳ mỗi 5 giây
        if utime.ticks_diff(now_ms, last_sync_ms) >= 5000:
            uart.write(SYNC)
            last_sync_ms = now_ms
    else:
        # Thử kết nối lại mỗi RETRY_INTERVAL
        if utime.ticks_diff(now_ms, last_sync_ms) >= RETRY_INTERVAL:
            perform_handshake()

    # Xử lý debounce khi có sự kiện từ start_sensor
    if event_flag and utime.ticks_diff(now_ms, event_time_ms) >= DEBOUNCE_MS:
        event_flag = False
        
        # Kiểm tra chân để đảm bảo thực sự là cạnh lên
        if start_sensor.value() == 1:
            # Kiểm tra khoảng cách tối thiểu giữa các lần trigger
            if utime.ticks_diff(now_ms, last_trigger_ms) >= MIN_GAP_MS:
                if send_trigger_command():
                    last_trigger_ms = now_ms
                    print("Trigger sent and acknowledged")
                else:
                    print("Trigger failed")
        else:
            print("Ignored unstable event on start_sensor")

    # Kiểm tra dữ liệu từ UART
    if uart.any():
        try:
            data = uart.read()
            if data == ACK:
                continue  # Bỏ qua ACK vì đã xử lý trong send_trigger_command
            elif data == NACK:
                CONNECTED = False  # Reset kết nối nếu nhận NACK
                print("Connection reset by peer")
            else:
                try:
                    # Thử parse JSON nếu là lệnh điều khiển
                    msg = json.loads(data.decode().strip())
                    print("Received command:", msg)
                except ValueError:
                    # Không phải JSON, in ra để debug
                    print("Received:", data)
        except Exception as e:
            print("UART read error:", e)

    utime.sleep_ms(1)  # Delay nhỏ để tránh quá tải CPU
