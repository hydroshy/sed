"""
This file adds the trigger_capture method to the CameraStream class.

To install this fix:
1. Copy this file to your Raspberry Pi at /home/pi/Desktop/project/sed/camera/
2. Run the following command on the Raspberry Pi to apply the fix:

python3 /home/pi/Desktop/project/sed/camera/apply_trigger_capture_fix.py

This script will backup the original camera_stream.py file and add the trigger_capture method.
"""

import os
import sys
import shutil
import datetime

# Define the target path
CAMERA_STREAM_PATH = "/home/pi/Desktop/project/sed/camera/camera_stream.py"

def apply_fix():
    """Apply the trigger_capture fix to camera_stream.py"""
    print(f"Applying trigger_capture fix to {CAMERA_STREAM_PATH}")
    
    # Check if the file exists
    if not os.path.exists(CAMERA_STREAM_PATH):
        print(f"Error: File not found: {CAMERA_STREAM_PATH}")
        return False
    
    # Create a backup with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{CAMERA_STREAM_PATH}.bak_{timestamp}"
    try:
        shutil.copy2(CAMERA_STREAM_PATH, backup_path)
        print(f"Created backup at {backup_path}")
    except Exception as e:
        print(f"Error creating backup: {e}")
        return False
    
    # Read the file content
    try:
        with open(CAMERA_STREAM_PATH, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return False
    
    # Check if trigger_capture already exists
    if "def trigger_capture(self)" in content:
        print("trigger_capture method already exists. No changes needed.")
        return True
    
    # Find a good place to add the trigger_capture method
    try:
        # Try to find the end of the file or before specific patterns
        if "# Add the method to the class" in content:
            # Find the last occurrence
            parts = content.split("# Add the method to the class")
            insert_index = len("# Add the method to the class".join(parts[:-1])) + len("# Add the method to the class")
            
            # Move to the end of that line
            insert_index = content.find('\n', insert_index)
            if insert_index == -1:
                insert_index = len(content)
        else:
            # Add to the end of the file
            insert_index = len(content)
        
        # Prepare the trigger_capture method to add
        trigger_capture_code = """

# Add trigger_capture method if it doesn't exist
if not hasattr(CameraStream, 'trigger_capture'):
    print("DEBUG: [CameraStream] Adding trigger_capture method to class")
    def _trigger_capture(self):
        \"\"\"
        Trigger single photo capture
        
        NOTE: Trigger capture ALWAYS works regardless of job_enabled setting.
        - Job enabled: Full processing with potential longer capture time
        - Job disabled: Simple capture, faster but no advanced processing
        \"\"\"
        try:
            print("DEBUG: [CameraStream] trigger_capture called")
            
            if not self.is_camera_available:
                print("DEBUG: [CameraStream] Camera not available")
                # Emit a test frame for testing without camera
                import numpy as np
                test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                self.frame_ready.emit(test_frame)
                return
                
            # Ensure camera is initialized
            if not hasattr(self, 'picam2') or self.picam2 is None:
                print("DEBUG: [CameraStream] Camera not initialized, reinitializing...")
                if not self._safe_init_picamera():
                    print("DEBUG: [CameraStream] Camera reinitialization failed")
                    return
                print("DEBUG: [CameraStream] Camera reinitialized for trigger capture")
                
            # Remember current state
            was_live = self.is_live
            print(f"DEBUG: [CameraStream] was_live: {was_live}")
            
            # Stop current capture if running
            if was_live or (self.picam2 and self.picam2.started):
                print("DEBUG: [CameraStream] Stopping current capture")
                if self.picam2:
                    self.picam2.stop()
            
            # Configure for still capture
            print("DEBUG: [CameraStream] Configuring for still capture")
            if not hasattr(self, 'still_config') or not self.still_config:
                # Create still config if not exists
                self.still_config = self.picam2.create_still_configuration()
                print("DEBUG: [CameraStream] Created still config")
            
            # Update still config with current exposure settings
            if "controls" not in self.still_config:
                self.still_config["controls"] = {}
                
            # Apply current exposure settings to still capture
            self.still_config["controls"]["ExposureTime"] = self.current_exposure
            self.still_config["controls"]["AeEnable"] = False  # Manual exposure
            
            # Set frame duration limits to accommodate exposure time
            min_frame_duration = max(100, self.current_exposure + 1000)  # At least exposure + 1ms
            self.still_config["controls"]["FrameDurationLimits"] = (min_frame_duration, 1000000000)
            
            # Handle noise reduction properly to avoid TDN error
            if not self.job_enabled:
                # Use minimal noise reduction instead of completely off
                self.still_config["controls"]["NoiseReductionMode"] = 3  # Minimal
            else:
                # Use high quality for full processing
                self.still_config["controls"]["NoiseReductionMode"] = 2  # HighQuality
            
            print(f"DEBUG: [CameraStream] Still config exposure: {self.current_exposure}μs")
            
            # Configure camera with error handling
            try:
                self.picam2.configure(self.still_config)
                print("DEBUG: [CameraStream] Still configuration successful")
            except Exception as config_error:
                print(f"DEBUG: [CameraStream] Still config failed: {config_error}")
                # Fallback to simpler configuration
                simple_config = self.picam2.create_still_configuration()
                simple_config["controls"] = {
                    "ExposureTime": self.current_exposure,
                    "AeEnable": False,
                    "NoiseReductionMode": 3  # Minimal to avoid TDN error
                }
                self.picam2.configure(simple_config)
                print("DEBUG: [CameraStream] Fallback configuration applied")
            
            # Start and capture
            print(f"DEBUG: [CameraStream] Starting still capture (Job: {'ON' if self.job_enabled else 'OFF'})")
            # Always start camera for trigger capture, but control preview based on job setting
            try:
                self.picam2.start(show_preview=False)  # Always use safe mode for trigger
                print("DEBUG: [CameraStream] Camera started successfully for still capture")
            except Exception as start_error:
                print(f"DEBUG: [CameraStream] Camera start failed: {start_error}")
                # Try to recover
                if "TDN" in str(start_error):
                    print("DEBUG: [CameraStream] TDN error detected, trying simpler config")
                    self.picam2.stop()
                    # Ultra-simple config to avoid TDN issues
                    ultra_simple = self.picam2.create_still_configuration()
                    ultra_simple["controls"] = {"ExposureTime": self.current_exposure, "AeEnable": False}
                    self.picam2.configure(ultra_simple)
                    self.picam2.start(show_preview=False)
                else:
                    raise start_error
            
            print("DEBUG: [CameraStream] Capturing frame")
            # Trigger capture ALWAYS works, but with different handling based on job setting
            try:
                frame = self.picam2.capture_array()
                if frame is None:
                    print("DEBUG: [CameraStream] No frame captured, retrying...")
                    # Retry once
                    frame = self.picam2.capture_array()
            except Exception as capture_error:
                print(f"DEBUG: [CameraStream] Capture error: {capture_error}")
                frame = None
            
            if frame is not None:
                print(f"DEBUG: [CameraStream] Frame captured: {frame.shape}")
                self.frame_ready.emit(frame)
            else:
                print("DEBUG: [CameraStream] No frame captured")
            
            # Stop still capture
            print("DEBUG: [CameraStream] Stopping still capture")
            if not self.job_enabled:
                # Force close to avoid job execution on stop
                self.picam2.close()
                # Reinitialize for next operation
                if not self._safe_init_picamera():
                    print("DEBUG: [CameraStream] Camera reinitialization failed after still capture")
                else:
                    print("DEBUG: [CameraStream] Camera reinitialized after still capture")
            else:
                self.picam2.stop()
            
            # Restore preview if was live
            if was_live:
                print("DEBUG: [CameraStream] Restoring live preview")
                if self.picam2:
                    self.picam2.configure(self.preview_config)
                    if self.job_enabled:
                        self.picam2.start()
                    else:
                        self.picam2.start(show_preview=False)
            else:
                print("DEBUG: [CameraStream] Not restoring live (was not live)")
                
            print("DEBUG: [CameraStream] trigger_capture completed successfully")
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error in trigger_capture: {e}")
            # Try to recover by reconfiguring preview
            try:
                if self.is_camera_available and hasattr(self, 'picam2') and self.picam2:
                    self.picam2.stop()
                    self.picam2.configure(self.preview_config)
                    if was_live:
                        self.picam2.start()
            except Exception as recovery_error:
                print(f"DEBUG: [CameraStream] Recovery failed: {recovery_error}")
    
    # Add the method to the class
    CameraStream.trigger_capture = _trigger_capture
"""
        
        # Insert the trigger_capture method at the determined position
        new_content = content[:insert_index] + trigger_capture_code + content[insert_index:]
        
        # Write the modified content back to the file
        with open(CAMERA_STREAM_PATH, 'w') as f:
            f.write(new_content)
        
        print(f"Successfully added trigger_capture method to {CAMERA_STREAM_PATH}")
        return True
        
    except Exception as e:
        print(f"Error applying fix: {e}")
        
        # Try to restore from backup
        try:
            print(f"Attempting to restore from backup {backup_path}")
            shutil.copy2(backup_path, CAMERA_STREAM_PATH)
            print("Restore successful")
        except Exception as restore_error:
            print(f"Error restoring from backup: {restore_error}")
        
        return False

if __name__ == "__main__":
    # Run the fix
    success = apply_fix()
    if success:
        print("Fix applied successfully. Please restart the application.")
    else:
        print("Failed to apply fix. Check the error messages above.")
        sys.exit(1)
