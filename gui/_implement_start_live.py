"""
This file contains the implementation of _implement_start_live method
to be added to the CameraManager class
"""

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
