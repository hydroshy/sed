"""
Stub module for pykms to prevent import errors on Raspberry Pi.
This module is loaded instead of the system pykms module when there are 
compatibility issues with the actual pykms library.
"""

import logging
logger = logging.getLogger("pykms_stub")
logger.warning("Using pykms stub module - pykms functionality is disabled")

# Create dummy enum for PixelFormat
class PixelFormat:
    """Stub implementation of pykms.PixelFormat enum"""
    RGB888 = 1
    BGR888 = 2
    XRGB8888 = 3
    XBGR8888 = 4
    ARGB8888 = 5
    ABGR8888 = 6
    UYVY = 7
    YUYV = 8
    YVYU = 9
    VYUY = 10
    YUV420 = 11
    YVU420 = 12
    YUV422 = 13
    NV12 = 14
    NV21 = 15

# Create dummy classes for DRM objects
class Card:
    def __init__(self, *args, **kwargs):
        logger.warning("Stub Card object created - no functionality available")
    
    def get_first_connected_connector(self):
        return Connector()
    
    def get_resources(self):
        return None

class Connector:
    def __init__(self, *args, **kwargs):
        self.encoder = None
        self.name = "STUB-CONNECTOR"
        self.modes = [Mode()]
    
    def get_default_mode(self):
        return Mode()
    
    def get_possible_encoders(self):
        return [Encoder()]

class Encoder:
    def __init__(self, *args, **kwargs):
        self.possible_clones = []
        self.possible_crtcs = [Crtc()]

class Crtc:
    def __init__(self, *args, **kwargs):
        self.mode = Mode()
        self.name = "STUB-CRTC"
    
    def set_mode(self, *args, **kwargs):
        return False

class Mode:
    def __init__(self, *args, **kwargs):
        self.name = "STUB-MODE"
        self.hdisplay = 1920
        self.vdisplay = 1080
        self.clock = 60000
        self.vrefresh = 60

class DrmObject:
    def __init__(self, *args, **kwargs):
        logger.warning("Stub DrmObject created - no functionality available")

class DrmFramebuffer:
    def __init__(self, *args, **kwargs):
        logger.warning("Stub DrmFramebuffer created - no functionality available")

class DumbFramebuffer:
    def __init__(self, card, width, height, format):
        logger.warning("Stub DumbFramebuffer created - no functionality available")
        self.width = width
        self.height = height
        self.format = format
        self.fd = -1
        self.planes = []

# Other functions picamera2 might need
def draw_test_pattern(*args, **kwargs):
    logger.warning("Stub draw_test_pattern called - no operation performed")
    return None
