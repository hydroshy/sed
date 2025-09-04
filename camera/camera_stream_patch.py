"""
This module defines a monkey patching function to add the start_live
method directly to CameraStream class if it doesn't already exist.
"""

def add_start_live_method(CameraStream):
    """Add start_live method to CameraStream class if it doesn't exist"""
    
    def start_live(self):
        """Start live camera preview - dynamically added method"""
        print("DEBUG: [CameraStream] Dynamically added start_live called")
        try:
            if not self.is_camera_available:
                print("DEBUG: [CameraStream] Camera not available for live mode")
                return False
                
            if hasattr(self, 'is_live') and self.is_live:
                print("DEBUG: [CameraStream] Already in live mode")
                return True
            
            # Ensure camera is initialized
            if self.picam2 is None:
                print("DEBUG: [CameraStream] Reinitializing camera...")
                if not self._safe_init_picamera():
                    print("DEBUG: [CameraStream] Camera reinitialization failed")
                    return False
                print("DEBUG: [CameraStream] Camera reinitialized successfully")
                
            print("DEBUG: [CameraStream] Starting live preview...")
            
            # Update config with current settings
            if hasattr(self, '_update_preview_config'):
                self._update_preview_config()
            
            # Stop camera if running
            if self.picam2 and hasattr(self.picam2, 'started') and self.picam2.started:
                print("DEBUG: [CameraStream] Stopping camera before reconfigure")
                self.picam2.stop()
            
            # Configure and start
            if hasattr(self, 'preview_config'):
                print("DEBUG: [CameraStream] Configuring camera for preview")
                self.picam2.configure(self.preview_config)
            
            print("DEBUG: [CameraStream] Starting camera")
            # Start camera based on job enabled state
            if hasattr(self, 'job_enabled') and self.job_enabled:
                print("DEBUG: [CameraStream] Job enabled - starting camera normally")
                self.picam2.start()
            else:
                print("DEBUG: [CameraStream] Job disabled - starting camera in safe mode")
                try:
                    self.picam2.start(show_preview=False)  # Start without preview to avoid job execution
                except TypeError:
                    # If show_preview is not supported, just start normally
                    self.picam2.start()
            
            print("DEBUG: [CameraStream] Starting timer for frame capture")
            if hasattr(self, 'timer'):
                self.timer.start(100)  # 10 FPS
            
            self.is_live = True
            print("DEBUG: [CameraStream] Live mode started successfully")
            return True
            
        except Exception as e:
            print(f"DEBUG: [CameraStream] Error starting live mode: {e}")
            self.is_live = False
            # Try to stop timer and camera to avoid hanging state
            try:
                if hasattr(self, 'timer') and self.timer.isActive():
                    self.timer.stop()
                if self.picam2 and hasattr(self.picam2, 'started') and self.picam2.started:
                    self.picam2.stop()
            except:
                pass
            return False
    
    # Only add the method if it doesn't exist
    if not hasattr(CameraStream, 'start_live'):
        print("DEBUG: Monkey patching CameraStream.start_live method")
        CameraStream.start_live = start_live
        
    # Also add start_live_camera as an alias
    if not hasattr(CameraStream, 'start_live_camera'):
        print("DEBUG: Monkey patching CameraStream.start_live_camera method")
        CameraStream.start_live_camera = start_live
