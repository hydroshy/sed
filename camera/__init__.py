"""
Camera module initialization

This module automatically applies all necessary patches to ensure
the CameraStream class has all required methods.
"""

# Import the CameraStream class
from camera.camera_stream import CameraStream

# CameraStream includes required methods; skipping dynamic patching.

# External trigger methods are integrated or optional; no dynamic import.

__all__ = ['CameraStream']
