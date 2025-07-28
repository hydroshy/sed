# Picamera2 Pipeline Configuration
# File cấu hình cho camera pipeline

# Camera Settings
CAMERA_SETTINGS = {
    # Preview settings (for real-time display)
    "preview": {
        "size": (640, 480),
        "format": "RGB888",
        "fps": 30,
        "controls": {
            "FrameRate": 30,
            "AeEnable": True,      # Auto exposure
            "AwbEnable": True,     # Auto white balance
            "Brightness": 0.0,
            "Contrast": 1.0,
            "Saturation": 1.0,
            "Sharpness": 1.0
        }
    },
    
    # Still capture settings (high quality)
    "still": {
        "size": (1456, 1088),  # Native IMX296 resolution
        "format": "RGB888",
        "controls": {
            "AeEnable": False,     # Manual exposure for consistent results
            "AwbEnable": True,
            "NoiseReductionMode": "HighQuality"
        }
    },
    
    # RAW capture settings (for advanced processing)
    "raw": {
        "main_size": (1456, 1088),
        "main_format": "RGB888",
        "raw_format": "SBGGR10_1X10",  # Sensor native format
        "controls": {
            "AeEnable": False,
            "AwbEnable": False,    # Manual WB for RAW
        }
    }
}

# Default camera parameters
DEFAULT_PARAMS = {
    "exposure_time": 10000,    # 10ms in microseconds
    "analogue_gain": 1.0,
    "exposure_value": 0.0,
    "colour_temperature": 5500,  # Daylight
    "auto_exposure": True,
    "auto_white_balance": True
}

# White balance presets
WHITE_BALANCE_PRESETS = {
    "auto": {"AwbEnable": True},
    "daylight": {"AwbEnable": False, "ColourTemperature": 5500},
    "cloudy": {"AwbEnable": False, "ColourTemperature": 6500},
    "tungsten": {"AwbEnable": False, "ColourTemperature": 3200},
    "fluorescent": {"AwbEnable": False, "ColourTemperature": 4000},
    "flash": {"AwbEnable": False, "ColourTemperature": 5500}
}

# Performance settings
PERFORMANCE_SETTINGS = {
    "preview_fps": 30,
    "capture_timeout": 5.0,    # seconds
    "metadata_enabled": True,
    "threading_enabled": True,
    "buffer_count": 3
}

# Image processing settings
PROCESSING_SETTINGS = {
    "enable_denoise": True,
    "enable_sharpening": True,
    "enable_contrast_enhancement": False,
    "jpeg_quality": 95,
    "png_compression": 6
}

# Advanced pipeline settings
PIPELINE_SETTINGS = {
    # ISP (Image Signal Processor) settings
    "isp": {
        "enable_lens_shading_correction": True,
        "enable_defective_pixel_correction": True,
        "enable_noise_reduction": True,
        "enable_edge_enhancement": True
    },
    
    # Sensor settings
    "sensor": {
        "enable_fast_startup": True,
        "pixel_rate": 74250000,  # IMX296 pixel rate
        "line_length": 1560,
        "frame_length": 1122
    }
}

# Debug and logging settings
DEBUG_SETTINGS = {
    "log_level": "INFO",
    "enable_frame_logging": False,
    "enable_metadata_logging": True,
    "save_debug_images": False,
    "debug_image_path": "/tmp/sed_debug/"
}
