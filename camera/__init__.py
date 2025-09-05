"""
Camera module initialization

This module automatically applies all necessary patches to ensure
the CameraStream class has all required methods.
"""

# Import the CameraStream class
from camera.camera_stream import CameraStream

# Apply all patches
try:
    from camera.camera_patches import apply_all_patches
    apply_all_patches()
    print("DEBUG: Camera module initialized with all patches applied")
except Exception as e:
    print(f"WARNING: Failed to apply camera patches: {e}")

# Import external trigger methods
try:
    import camera.external_trigger_methods
    print("DEBUG: External trigger methods loaded")
except Exception as e:
    print(f"WARNING: Failed to load external trigger methods: {e}")

__all__ = ['CameraStream']
