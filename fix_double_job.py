#!/usr/bin/env python3
import re

# Read file
with open('e:/PROJECT/sed/gui/camera_manager.py', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Find and replace the trigger section
pattern = r"if current_mode == 'trigger' and button_is_enabled:.*?self\.activate_capture_request\(\)"

replacement = """if current_mode == 'trigger' and button_is_enabled:
            # STOP live stream to prevent double frame emit
            if self.camera_stream and hasattr(self.camera_stream, '_live_thread'):
                if self.camera_stream._live_thread and self.camera_stream._live_thread.isRunning():
                    print("DEBUG: [CameraManager] Stopping live thread temporarily...")
                    self.camera_stream._live_thread.quit()
                    self.camera_stream._live_thread.wait(timeout=500)
            
            # COOLDOWN FIX: Reset cooldown BEFORE sending TR1
            if self.camera_stream and hasattr(self.camera_stream, '_last_trigger_time'):
                self.camera_stream._last_trigger_time = 0.0
                print("DEBUG: [CameraManager] Cooldown reset")
            
            # TIMING FIX: Send TR1
            print("DEBUG: [CameraManager] Sending TR1 trigger signal to light...")
            if self.camera_stream:
                self.camera_stream.set_trigger_sent_time()
            self._send_trigger_to_light_controller()
            
            # CHECK DELAY TRIGGER
            delay_ms = self._get_delay_trigger_value()
            if delay_ms > 0:
                print(f"DEBUG: [CameraManager] Waiting {delay_ms:.1f}ms before capture...")
                time.sleep(delay_ms / 1000.0)
            
            # Capture frame
            print("DEBUG: [CameraManager] Now capturing frame...")
            self.activate_capture_request()
            
            # RESTART live stream after capture
            if self.camera_stream and hasattr(self.camera_stream, '_live_thread'):
                if not (self.camera_stream._live_thread and self.camera_stream._live_thread.isRunning()):
                    print("DEBUG: [CameraManager] Restarting live thread...")
                    try:
                        self.camera_stream.start_live_capture()
                    except Exception as e:
                        print(f"DEBUG: [CameraManager] Error restarting: {e}")"""

if re.search(pattern, content, re.DOTALL):
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    with open('e:/PROJECT/sed/gui/camera_manager.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('✅ Updated camera_manager.py')
else:
    print('❌ Pattern not found')
