# ==========================================
# Raspberry Pi Pico + W5500 (MicroPython)
# ONE-SOCKET MODE:
# - Pico là TCP CLIENT kết nối 1 cổng duy nhất (Hercules TCP Server)
# - Nhận lệnh & phản hồi ngay trên chính socket này (PING/KICK/SETKICK/GOTO/HOME)
# - Gửi event START/END cũng trên chính socket này
# - START sensor RISING: trigger camera + send "start_rising|.."
# - END   sensor RISING: servo kick + send "end_rising|.."
# - Anti-jitter servo: release PWM at HOME + short refresh (non-blocking)
# ==========================================

from machine import Pin, PWM, SPI
import utime
import network
import usocket as socket

# ====== GIỮ NGUYÊN BIẾN CŨ ======
START_SENSOR_PIN = 26        # opto nhả OFF => mức 1 (changed from 27)
END_SENSOR_PIN   = 27        # opto nhả OFF => mức 1 (changed from 26)
CAM_PIN          = 18        # trigger camera (active-low) - fire_trigger xung (changed from 22)
RELAY_PIN        = 17        # trigger relay đèn (active-high)
LED_PIN_NAME     = "LED"

PULSE_US     = 3000          # độ rộng xung camera (us)
DEBOUNCE_MS  = 10            # chống dội (ms)
MIN_GAP_MS   = 10            # tối thiểu giữa 2 lần trigger camera (ms)

# ====== SERVO CONFIG (anti-jitter) ======
SERVO_PIN        = 16
SERVO_FREQ_HZ    = 50
SERVO_MIN_US     = 650
SERVO_MAX_US     = 2350
HOME_DEG         = 5
KICK_DEFAULT_DEG = 90        # mặc định gạt +90°
HOLD_MS          = 250

SERVO_RELEASE_AFTER_HOME = True
SERVO_REFRESH_MS         = 800
SERVO_REFRESH_PULSE_MS   = 40

SERVO_STEP_DEG   = 4
SERVO_STEP_MS    = 8
MIN_KICK_GAP_MS  = 200

# ====== TCP CONTROL (PC/Hercules) Pico sẽ KẾT NỐI vào (1 cổng duy nhất) ======
# CONTROL_HOST = "192.168.1.35"   # <-- ĐỔI THÀNH IP PC CỦA BẠN  # (disabled in HOST mode)
CONTROL_PORT = 4000

# ====== W5500 STATIC IP (SPI1) ======
# SCK=GP10, MOSI=GP11, MISO=GP12; CS=GP13; RST=GP15
STATIC_IP = ("192.168.1.190", "255.255.255.0", "192.168.1.1", "192.168.1.1")

spi  = SPI(1, baudrate=20_000_000, polarity=0, phase=0, sck=Pin(10), mosi=Pin(11), miso=Pin(12))
cs   = Pin(13, Pin.OUT, value=1)
rst  = Pin(15, Pin.OUT, value=1)

# Reset cứng W5500
rst.value(0); utime.sleep_ms(50); rst.value(1); utime.sleep_ms(200)

nic = network.WIZNET5K(spi, cs, rst)
nic.active(True)
nic.ifconfig(STATIC_IP)
print("ifconfig:", nic.ifconfig())


PICO_IP = nic.ifconfig()[0]
def wait_link(timeout_ms=15000):
    t0 = utime.ticks_ms()
    while not nic.isconnected():
        if utime.ticks_diff(utime.ticks_ms(), t0) > timeout_ms:
            return False
        utime.sleep_ms(100)
    return True

NET_READY = wait_link(15000)
print("LINK:", "UP" if NET_READY else "DOWN")

# ====== I/O PINS ======
start_sensor = Pin(START_SENSOR_PIN, Pin.IN, Pin.PULL_UP)
end_sensor   = Pin(END_SENSOR_PIN,   Pin.IN, Pin.PULL_UP)
cam_out      = Pin(CAM_PIN, Pin.OUT, value=1)  # active-low, nhả về 1
relay_out    = Pin(RELAY_PIN, Pin.OUT, value=0)  # active-high, nhả về 0
led          = Pin(LED_PIN_NAME, Pin.OUT, value=0)

# ====== SERVO PWM + HELPERS ======
_servo_pin_obj = Pin(SERVO_PIN, Pin.OUT)
servo_pwm = PWM(_servo_pin_obj)
servo_pwm.freq(SERVO_FREQ_HZ)
servo_enabled = True
PERIOD_US = 1_000_000 // SERVO_FREQ_HZ

def _servo_write_us(pulse_us: int):
    try:
        servo_pwm.duty_ns(pulse_us * 1000)
    except AttributeError:
        servo_pwm.duty_u16(int(pulse_us * 65535 // PERIOD_US))

def angle_to_us(deg: float) -> int:
    if deg < 0:   deg = 0
    if deg > 180: deg = 180
    return int(SERVO_MIN_US + (SERVO_MAX_US - SERVO_MIN_US) * (deg / 180.0))

def servo_goto(deg: float):
    _servo_write_us(angle_to_us(deg))

def servo_enable():
    global servo_pwm, servo_enabled
    if not servo_enabled:
        servo_pwm = PWM(_servo_pin_obj)
        servo_pwm.freq(SERVO_FREQ_HZ)
        servo_enabled = True

def servo_disable():
    global servo_pwm, servo_enabled
    if servo_enabled:
        try: servo_pwm.deinit()
        except: pass
        servo_enabled = False

# ====== LED BLINK (NON-BLOCKING) ======
_led_blink_left     = 0
_led_blink_interval = 100
_led_next_toggle    = 0
_led_active         = False

def led_blink_start(times=3, interval_ms=100):
    global _led_blink_left, _led_blink_interval, _led_next_toggle, _led_active
    _led_blink_left     = times * 2
    _led_blink_interval = interval_ms
    _led_next_toggle    = utime.ticks_add(utime.ticks_ms(), _led_blink_interval)
    _led_active         = True

def led_blink_update(now_ms):
    global _led_blink_left, _led_next_toggle, _led_active
    if not _led_active: return
    if utime.ticks_diff(now_ms, _led_next_toggle) >= 0:
        led.toggle()
        _led_blink_left -= 1
        if _led_blink_left <= 0:
            _led_active = False
            led.value(0)
        else:
            _led_next_toggle = utime.ticks_add(now_ms, _led_blink_interval)

# ====== FIRE TRIGGER (CAM + RELAY) ======
def fire_trigger():
    """Phát xung đồng bộ cho Camera (GPIO18) và bật Relay (GPIO17)
    Chạy chậm để relay có thời gian phản ứng
    """
    relay_out.value(1)  # Bật relay (GPIO17 = HIGH/3.3V)
    led.value(1)        # Bật LED

    # --- Camera: active-low pulse ---
    cam_out.value(0)    # bắt đầu phơi (GPIO18 xuống LOW)
    utime.sleep_us(PULSE_US)  # xung 1000us
    cam_out.value(1)    # GPIO18 nhả về HIGH

    # --- Giữ relay bật lâu hơn để nó có thời gian phản ứng ---
    utime.sleep_ms(100)  # Relay cần 10-100ms để hoạt động, giữ thêm để chắc
    
    relay_out.value(0)  # Tắt relay
    led.value(0)        # Tắt LED

# ====== SERVO STATE MACHINE (NON-BLOCKING) ======
# States: IDLE/MOVE_OUT/HOLDING/MOVE_HOME/AT_HOME/RELEASED
servo_state       = "IDLE"          
servo_cur_deg     = HOME_DEG
servo_target_deg  = min(HOME_DEG + KICK_DEFAULT_DEG, 180)
servo_next_step   = 0
servo_hold_until  = 0

refresh_state     = "OFF"           # OFF/ON
refresh_until_ms  = 0
next_refresh_ms   = 0

_restore_home_after_at_home = False
_home_backup = HOME_DEG

runtime_kick_delta_deg = KICK_DEFAULT_DEG
servo_waiting_for_release = False  # Flag: servo đang hold, chờ lệnh release từ TCP

def servo_release_from_hold(now_ms):
    """Release servo từ HOLDING state, quay về HOME"""
    global servo_state, servo_next_step, servo_waiting_for_release
    if servo_state == "HOLDING":
        servo_state = "MOVE_HOME"
        servo_next_step = utime.ticks_add(now_ms, SERVO_STEP_MS)
        servo_waiting_for_release = False
        print("[SERVO] Release from HOLDING, moving home")

def _set_servo_deg(deg):
    global servo_cur_deg
    servo_cur_deg = deg
    servo_goto(servo_cur_deg)

def servo_start_kick(now_ms):
    global servo_state, servo_target_deg, servo_next_step
    if servo_state in ("IDLE", "AT_HOME", "RELEASED"):
        servo_target_deg = min(HOME_DEG + runtime_kick_delta_deg, 180)
        servo_enable()
        _set_servo_deg(HOME_DEG)
        servo_state     = "MOVE_OUT"
        servo_next_step = utime.ticks_add(now_ms, SERVO_STEP_MS)

def _goto_abs(target_deg, now_ms):
    global servo_state, servo_target_deg, servo_next_step
    global _restore_home_after_at_home, _home_backup, HOME_DEG
    servo_enable()
    target_deg = max(0, min(180, target_deg))
    if target_deg >= servo_cur_deg:
        servo_target_deg = target_deg
        servo_state = "MOVE_OUT"
        servo_next_step = utime.ticks_add(now_ms, SERVO_STEP_MS)
    else:
        _home_backup = HOME_DEG
        HOME_DEG = target_deg
        servo_state = "MOVE_HOME"
        servo_next_step = utime.ticks_add(now_ms, SERVO_STEP_MS)
        _restore_home_after_at_home = True

def _servo_update(now_ms):
    global servo_state, servo_next_step, servo_hold_until
    global next_refresh_ms, refresh_state, refresh_until_ms
    global _restore_home_after_at_home, HOME_DEG, _home_backup
    global servo_waiting_for_release

    if servo_state == "MOVE_OUT":
        if utime.ticks_diff(now_ms, servo_next_step) >= 0:
            nxt = servo_cur_deg + SERVO_STEP_DEG
            if nxt >= servo_target_deg:
                _set_servo_deg(servo_target_deg)
                servo_state = "HOLDING"  # Chỉ hold, không auto-return
                servo_waiting_for_release = True
                print("[SERVO] Reached target {}, waiting for release command".format(servo_target_deg))
            else:
                _set_servo_deg(nxt)
                servo_next_step = utime.ticks_add(now_ms, SERVO_STEP_MS)

    elif servo_state == "HOLDING":
        # Chỉ chờ đợi, không tự động quay về
        # Lệnh release sẽ từ TCP (HOME hay RELEASE)
        pass

    elif servo_state == "MOVE_HOME":
        if utime.ticks_diff(now_ms, servo_next_step) >= 0:
            nxt = servo_cur_deg - SERVO_STEP_DEG
            if nxt <= HOME_DEG:
                _set_servo_deg(HOME_DEG)
                servo_state = "AT_HOME"
            else:
                _set_servo_deg(nxt)
                servo_next_step = utime.ticks_add(now_ms, SERVO_STEP_MS)

    elif servo_state == "AT_HOME":
        if _restore_home_after_at_home:
            HOME_DEG = _home_backup
            _restore_home_after_at_home = False

        led_blink_start(times=3, interval_ms=100)
        if SERVO_RELEASE_AFTER_HOME:
            servo_disable()
            servo_state   = "RELEASED"
            servo_waiting_for_release = False
            refresh_state = "OFF"
            next_refresh_ms = utime.ticks_add(now_ms, SERVO_REFRESH_MS)
        else:
            servo_state = "IDLE"
            servo_waiting_for_release = False

    elif servo_state == "RELEASED":
        if utime.ticks_diff(now_ms, next_refresh_ms) >= 0:
            servo_enable()
            _set_servo_deg(HOME_DEG)
            refresh_state   = "ON"
            refresh_until_ms= utime.ticks_add(now_ms, SERVO_REFRESH_PULSE_MS)
        if refresh_state == "ON" and utime.ticks_diff(now_ms, refresh_until_ms) >= 0:
            servo_disable()
            refresh_state = "OFF"
            next_refresh_ms = utime.ticks_add(now_ms, SERVO_REFRESH_MS)

# ====== KHỞI ĐỘNG: ĐƯA VỀ HOME & GIỮ PWM BẬT (KHÔNG RELEASE) ======
_set_servo_deg(HOME_DEG)
utime.sleep_ms(300)
# Giữ servo bật ở HOME thay vì release - để servo luôn sẵn sàng
servo_enabled = True
print("[SERVO] Initialized at HOME position, servo PWM enabled")

# ====== START SENSOR IRQ + DEBOUNCE ======
event_flag    = False
event_time_ms = 0
last_cam_ms   = utime.ticks_ms()

def on_edge_start(pin):
    global event_flag, event_time_ms
    event_time_ms = utime.ticks_ms()
    event_flag = True

start_sensor.irq(trigger=Pin.IRQ_RISING, handler=on_edge_start)

# ====== END SENSOR IRQ + DEBOUNCE (chỉ bắt 0->1) ======
end_event_flag    = False
end_event_time_ms = 0

def on_edge_end(pin):
    global end_event_flag, end_event_time_ms
    end_event_time_ms = utime.ticks_ms()
    end_event_flag = True

# Chỉ lắng nghe cạnh lên (0->1), gửi event ngay, không tự kick servo
end_sensor.irq(trigger=Pin.IRQ_RISING, handler=on_edge_end)

# ====== ONE-SOCKET CONTROL CLIENT ======
class OneSocketClient:
    def __init__(self, host, port, reconnect_ms=1500):
        self.addr = (host, port)
        self.reconnect_ms = reconnect_ms
        self.sock = None
        self.buf = b""
        self._next_try = 0
        self.connected = False
        self.last_rx_ms = 0
        self.LINE_IDLE_MS = 200
        self.ECHO_DEBUG = False  # để False để không echo "RCV ..."

    # Telnet negotiate filter (IAC/DO/DONT/WILL/WONT/SB)
    def _telnet_strip(self, data: bytes) -> bytes:
        IAC = 255; SE = 240; SB = 250
        DO = 253; DONT = 254; WILL = 251; WONT = 252
        out = bytearray(); i = 0; n = len(data)
        while i < n:
            b = data[i]
            if b == IAC:
                i += 1
                if i >= n: break
                cmd = data[i]; i += 1
                if cmd in (DO, DONT, WILL, WONT):
                    if i < n: i += 1
                elif cmd == SB:
                    while i < n:
                        if data[i] == IAC and i + 1 < n and data[i+1] == SE:
                            i += 2; break
                        i += 1
                elif cmd == IAC:
                    out.append(0xFF)
                else:
                    pass
            else:
                out.append(b); i += 1
        return bytes(out)

    def _connect(self, now_ms):
        if self.sock: return True
        if utime.ticks_diff(now_ms, self._next_try) < 0: return False
        s = None
        try:
            s = socket.socket()
            s.settimeout(2.0)
            s.connect(self.addr)
            s.settimeout(0.0)  # non-blocking recv
            self.sock = s
            self.connected = True
            print("Connected to", self.addr)
            self._safe_write(b"HELLO from Pico\n")
            return True
        except OSError:
            try:
                if s: s.close()
            except: pass
            self.sock = None; self.connected = False
            self._next_try = utime.ticks_add(now_ms, self.reconnect_ms)
            return False

    def _safe_write(self, bts):
        if not self.sock: return False
        try:
            self.sock.settimeout(0.5)
            self.sock.write(bts)
            self.sock.settimeout(0.0)
            return True
        except OSError:
            try: self.sock.settimeout(0.0)
            except: pass
            try: self.sock.close()
            except: pass
            self.sock = None; self.connected = False
            return False

    def send_line(self, text):
        self._safe_write((text + "\n").encode())

    def send_event(self, name, payload=""):
        now = utime.ticks_ms()
        self.send_line("{}|{}|{}".format(name, payload, now))

    def close(self):
        try:
            if self.sock: self.sock.close()
        except: pass
        self.sock = None; self.connected = False
        print("Disconnected")

    # FAST-PATH: xử lý ngay khi thấy chuỗi lệnh phổ biến trong gói vừa nhận
    def _fast_handle(self, data_bytes, now_ms):
        s  = data_bytes.decode("utf-8", "ignore")
        up = s.upper()

        if "PING" in up:
            self.send_line("PONG")

        try:
            if "HOME" in up:
                _goto_abs(HOME_DEG, now_ms)
                self.send_line("OK HOME")
        except: pass

        try:
            idx = up.find("KICK")
            if idx >= 0:
                tail = up[idx+4:].lstrip()
                if tail and tail[0].isdigit():
                    end = 1
                    while end < len(tail) and tail[end].isdigit():
                        end += 1
                    deg_str = s[idx+4:].lstrip()[:end]
                    deg = int(deg_str)
                    deg = max(0, min(180, deg))
                    global runtime_kick_delta_deg
                    runtime_kick_delta_deg = deg
                    servo_start_kick(now_ms)
                    self.send_line("OK KICK {}".format(deg))
        except: pass

        try:
            idx = up.find("SETKICK")
            if idx >= 0:
                tail = up[idx+7:].lstrip()
                if tail and tail[0].isdigit():
                    end = 1
                    while end < len(tail) and tail[end].isdigit():
                        end += 1
                    deg_str = s[idx+7:].lstrip()[:end]
                    deg = int(deg_str)
                    deg = max(0, min(180, deg))
                    global runtime_kick_delta_deg
                    runtime_kick_delta_deg = deg
                    self.send_line("OK SETKICK {}".format(deg))
        except: pass

        try:
            idx = up.find("GOTO")
            if idx >= 0:
                tail = up[idx+4:].lstrip()
                if tail and tail[0].isdigit():
                    end = 1
                    while end < len(tail) and tail[end].isdigit():
                        end += 1
                    deg_str = s[idx+4:].lstrip()[:end]
                    deg = int(deg_str)
                    deg = max(0, min(180, deg))
                    _goto_abs(deg, now_ms)
                    self.send_line("OK GOTO {}".format(deg))
        except: pass

    def _handle_line(self, line: str):
        s = line.strip()
        if not s: return
        parts = s.split()
        cmd = parts[0].upper()

        def parse_deg(idx=1, fallback=None):
            try: return int(parts[idx])
            except: return fallback

        now = utime.ticks_ms()
        try:
            if cmd == "PING":
                self.send_line("PONG")
            elif cmd == "KICK":
                global runtime_kick_delta_deg
                deg = parse_deg(1, runtime_kick_delta_deg)
                if deg is None: raise ValueError("KICK needs <deg>")
                runtime_kick_delta_deg = max(0, min(180, deg))
                servo_start_kick(now)
                self.send_line("OK KICK {}".format(runtime_kick_delta_deg))
            elif cmd == "SETKICK":
                deg = parse_deg(1, runtime_kick_delta_deg)
                if deg is None: raise ValueError("SETKICK needs <deg>")
                runtime_kick_delta_deg = max(0, min(180, deg))
                self.send_line("OK SETKICK {}".format(runtime_kick_delta_deg))
            elif cmd == "GOTO":
                deg = parse_deg(1, None)
                if deg is None: raise ValueError("GOTO needs <deg>")
                _goto_abs(max(0, min(180, deg)), now)
                self.send_line("OK GOTO {}".format(deg))
            elif cmd == "HOME":
                _goto_abs(HOME_DEG, now)
                self.send_line("OK HOME")
            elif cmd == "RELEASE":
                servo_release_from_hold(now)
                self.send_line("OK RELEASE")
            elif cmd == "TRIGGER":
                fire_trigger()
                self.send_line("OK TRIGGER")
            else:
                self.send_line("ERR unknown cmd")
        except Exception as e:
            self.send_line("ERR {}".format(e))

    def update(self, now_ms):
        if not self._connect(now_ms): return

        got_any = False
        try:
            data = self.sock.recv(512)
            if data is not None:
                if data == b"": self.close(); return
                got_any = True
                self.last_rx_ms = now_ms

                if self.ECHO_DEBUG:
                    try: self._safe_write(b"RCV " + data + b"\n")
                    except: pass

                data = self._telnet_strip(data)
                data = data.replace(b'\r\n', b'\n').replace(b'\r', b'\n').replace(b'\x00', b'')
                
                # Gom vào buffer để parser dòng/idle xử lý
                self.buf += data

                while b"\n" in self.buf:
                    line, self.buf = self.buf.split(b"\n", 1)
                    line = line.rstrip(b'\n')  # Xóa \n ở cuối
                    try:
                        self._handle_line(line.decode("utf-8", "ignore"))
                    except:
                        pass
        except OSError:
            pass

        # Không có LF nhưng im lặng đủ lâu -> coi như xong 1 lệnh
        if (not got_any) and self.buf and self.last_rx_ms:
            if utime.ticks_diff(now_ms, self.last_rx_ms) >= self.LINE_IDLE_MS:
                try:
                    self._handle_line(self.buf.decode("utf-8", "ignore").rstrip('\n'))
                except:
                    pass
                self.buf = b""


# ====== ONE-SOCKET CONTROL SERVER (HOST) ======
class OneSocketHost:
    def __init__(self, port, backlog=1):
        self.port = port
        self.backlog = backlog
        self.server = None   # socket listen
        self.sock = None     # socket đã accept (1 client)
        self.buf = b""
        self.connected = False
        self.last_rx_ms = 0
        self.LINE_IDLE_MS = 200
        self.ECHO_DEBUG = False

    # Telnet negotiate filter (IAC/DO/DONT/WILL/WONT/SB)
    def _telnet_strip(self, data: bytes) -> bytes:
        IAC = 255; SE = 240; SB = 250
        DO = 253; DONT = 254; WILL = 251; WONT = 252
        out = bytearray(); i = 0; n = len(data)
        while i < n:
            b = data[i]
            if b == IAC:
                i += 1
                if i >= n: break
                cmd = data[i]; i += 1
                if cmd in (DO, DONT, WILL, WONT):
                    if i < n: i += 1
                elif cmd == SB:
                    while i < n:
                        if data[i] == IAC and i + 1 < n and data[i+1] == SE:
                            i += 2; break
                        i += 1
                elif cmd == IAC:
                    out.append(0xFF)
                else:
                    pass
            else:
                out.append(b); i += 1
        return bytes(out)

    def _ensure_server(self):
        if self.server:
            return
        s = socket.socket()
        try:
            import usocket as _us
            try:
                s.setsockopt(_us.SOL_SOCKET, _us.SO_REUSEADDR, 1)
            except:
                pass
        except:
            pass
        s.bind(("0.0.0.0", self.port))
        s.listen(self.backlog)
        s.settimeout(0.0)  # non-blocking accept
        self.server = s
        print("Listening on 0.0.0.0:{} ...".format(self.port))

    def _accept_client(self):
        try:
            c, addr = self.server.accept()
        except OSError:
            return False
        c.settimeout(0.0)  # non-blocking recv
        self.sock = c
        self.connected = True
        self.buf = b""
        self.last_rx_ms = 0
        print("Client connected:", addr)
        self._safe_write(b"HELLO from Pico (server)\n")
        return True

    def _safe_write(self, bts):
        if not self.sock:
            return False
        try:
            self.sock.settimeout(0.5)
            self.sock.write(bts)
            self.sock.settimeout(0.0)
            return True
        except OSError:
            try: self.sock.settimeout(0.0)
            except: pass
            try: self.sock.close()
            except: pass
            self.sock = None
            self.connected = False
            print("Client disconnected (write fail)")
            return False

    def send_line(self, text):
        self._safe_write((text + "\n").encode())

    def send_event(self, name, payload=""):
        now = utime.ticks_ms()
        self.send_line("{}|{}|{}".format(name, payload, now))

    def close(self):
        try:
            if self.sock: self.sock.close()
        except: pass
        self.sock = None
        self.connected = False
        print("Client disconnected")

    # ========= Giữ nguyên logic parser/command như client =========
    def _fast_handle(self, data_bytes, now_ms):
        s  = data_bytes.decode("utf-8", "ignore")
        up = s.upper()

        if "PING" in up:
            self.send_line("PONG")

        try:
            if "HOME" in up:
                _goto_abs(HOME_DEG, now_ms)
                self.send_line("OK HOME")
        except: pass

        try:
            idx = up.find("KICK")
            if idx >= 0:
                tail = up[idx+4:].lstrip()
                if tail and tail[0].isdigit():
                    end = 1
                    while end < len(tail) and tail[end].isdigit():
                        end += 1
                    deg_str = s[idx+4:].lstrip()[:end]
                    deg = int(deg_str)
                    deg = max(0, min(180, deg))
                    global runtime_kick_delta_deg
                    runtime_kick_delta_deg = deg
                    servo_start_kick(now_ms)
                    self.send_line("OK KICK {}".format(deg))
        except: pass

        try:
            idx = up.find("SETKICK")
            if idx >= 0:
                tail = up[idx+7:].lstrip()
                if tail and tail[0].isdigit():
                    end = 1
                    while end < len(tail) and tail[end].isdigit():
                        end += 1
                    deg_str = s[idx+7:].lstrip()[:end]
                    deg = int(deg_str)
                    deg = max(0, min(180, deg))
                    global runtime_kick_delta_deg
                    runtime_kick_delta_deg = deg
                    self.send_line("OK SETKICK {}".format(deg))
        except: pass

        try:
            idx = up.find("GOTO")
            if idx >= 0:
                tail = up[idx+4:].lstrip()
                if tail and tail[0].isdigit():
                    end = 1
                    while end < len(tail) and tail[end].isdigit():
                        end += 1
                    deg_str = s[idx+4:].lstrip()[:end]
                    deg = int(deg_str)
                    deg = max(0, min(180, deg))
                    _goto_abs(deg, now_ms)
                    self.send_line("OK GOTO {}".format(deg))
        except: pass

    def _handle_line(self, line: str):
        s = line.strip()
        if not s: return
        parts = s.split()
        cmd = parts[0].upper()

        def parse_deg(idx=1, fallback=None):
            try: return int(parts[idx])
            except: return fallback

        now = utime.ticks_ms()
        try:
            if cmd == "PING":
                self.send_line("PONG")
            elif cmd == "KICK":
                global runtime_kick_delta_deg
                deg = parse_deg(1, runtime_kick_delta_deg)
                if deg is None: raise ValueError("KICK needs <deg>")
                runtime_kick_delta_deg = max(0, min(180, deg))
                servo_start_kick(now)
                self.send_line("OK KICK {}".format(runtime_kick_delta_deg))
            elif cmd == "SETKICK":
                deg = parse_deg(1, runtime_kick_delta_deg)
                if deg is None: raise ValueError("SETKICK needs <deg>")
                runtime_kick_delta_deg = max(0, min(180, deg))
                self.send_line("OK SETKICK {}".format(runtime_kick_delta_deg))
            elif cmd == "GOTO":
                deg = parse_deg(1, None)
                if deg is None: raise ValueError("GOTO needs <deg>")
                _goto_abs(max(0, min(180, deg)), now)
                self.send_line("OK GOTO {}".format(deg))
            elif cmd == "HOME":
                _goto_abs(HOME_DEG, now)
                self.send_line("OK HOME")
            elif cmd == "RELEASE":
                servo_release_from_hold(now)
                self.send_line("OK RELEASE")
            elif cmd == "TRIGGER":
                fire_trigger()
                self.send_line("OK TRIGGER")
            else:
                self.send_line("ERR unknown cmd")
        except Exception as e:
            self.send_line("ERR {}".format(e))

    def update(self, now_ms):
        # đảm bảo server
        self._ensure_server()

        # accept nếu chưa có client
        if not self.sock:
            self._accept_client()
            return

        got_any = False
        try:
            data = self.sock.recv(512)
            if data is not None:
                if data == b"":
                    self.close(); return
                got_any = True
                self.last_rx_ms = now_ms

                if self.ECHO_DEBUG:
                    try: self._safe_write(b"RCV " + data + b"\n")
                    except: pass

                data = self._telnet_strip(data)
                data = data.replace(b'\r\n', b'\n').replace(b'\r', b'\n').replace(b'\x00', b'')

                self.buf += data

                while b"\n" in self.buf:
                    line, self.buf = self.buf.split(b"\n", 1)
                    line = line.rstrip(b'\n')  # Xóa \n ở cuối
                    try:
                        self._handle_line(line.decode("utf-8", "ignore"))
                    except:
                        pass
        except OSError:
            pass

        if (not got_any) and self.buf and self.last_rx_ms:
            if utime.ticks_diff(now_ms, self.last_rx_ms) >= self.LINE_IDLE_MS:
                try:
                    self._handle_line(self.buf.decode("utf-8", "ignore").rstrip('\n'))
                except:
                    pass
                self.buf = b""

control = OneSocketHost(CONTROL_PORT) if NET_READY else None

print("System ready. HOST on 0.0.0.0:{} (IP: {})".format(CONTROL_PORT, PICO_IP))

# ====== MAIN LOOP ======
loop_count = 0
while True:
    now = utime.ticks_ms()
    loop_count += 1
    if loop_count % 5000 == 0:
        print("[LOOP] Running... ({}ms) NET_READY={} control={}".format(now, NET_READY, control is not None))

    # START -> Trigger camera + relay + send event
    if event_flag and utime.ticks_diff(now, event_time_ms) >= DEBOUNCE_MS:
        event_flag = False
        if start_sensor.value() == 1:
            if utime.ticks_diff(now, last_cam_ms) >= MIN_GAP_MS:
                print("[FIRE] camera + relay triggered at {}ms".format(now))
                fire_trigger()  # Phát xung camera + bật relay
                last_cam_ms = utime.ticks_ms()
                if control and control.connected:
                    control.send_event("start_rising")

    # END SENSOR -> Gửi event khi nhận cạnh lên (0->1), không tự kick
    if end_event_flag and utime.ticks_diff(now, end_event_time_ms) >= DEBOUNCE_MS:
        end_event_flag = False
        if end_sensor.value() == 1:  # Cạnh lên
            print("[END_SENSOR] Rising edge detected at {}ms".format(now))
            if control and control.connected:
                control.send_event("end_rising")
            else:
                print("[END_SENSOR] Waiting for TCP connection to send event")

    # cập nhật servo & LED
    _servo_update(now)
    led_blink_update(now)

    # cập nhật one-socket control (bọc try để tránh crash nếu có bất thường)
    if control and NET_READY:
        try:
            control.update(now)
        except Exception as e:
            # nếu có lỗi lẻ tẻ lúc parse/recv, không để treo hệ thống
            try:
                control.send_line("ERR {}".format(e))
            except: pass

    utime.sleep_ms(1)
