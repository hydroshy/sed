import sys
import os
import argparse
import logging
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

# Xử lý PyKMS trên Raspberry Pi 
try:
    # Kiểm tra nếu đang chạy trên Raspberry Pi
    is_raspberry_pi = os.path.exists('/proc/device-tree/model') and 'Raspberry Pi' in open('/proc/device-tree/model', 'r').read()
    
    if is_raspberry_pi:
        logger = logging.getLogger("pykms_handler")
        # Set up logging handler for console output
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        logger.info("Detected Raspberry Pi environment")
        
        # Configure PyKMS handling
        try:
            # Set XCB platform by default on Raspberry Pi
            os.environ['QT_QPA_PLATFORM'] = 'xcb'
            
            # Add our stubs directory to the beginning of sys.path
            stubs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stubs')
            if os.path.exists(stubs_dir) and stubs_dir not in sys.path:
                sys.path.insert(0, stubs_dir)
                logger.info(f"Added stubs directory to path: {stubs_dir}")
            
            # Force import our stub pykms before picamera2 tries to load the real one
            import pykms
            logger.info("PyKMS stub loaded successfully")
            
            # Ensure picamera2 doesn't try to use DrmPreview
            os.environ['PICAMERA2_PREVIEW_PREFER'] = 'qt'
            logger.info("Set PICAMERA2_PREVIEW_PREFER=qt to avoid DrmPreview")
            
        except Exception as e:
            logger.warning(f"Error setting up Raspberry Pi display: {e}")
except Exception as e:
    # Không làm gì nếu không phải Raspberry Pi hoặc không thể kiểm tra
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sed_app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def show_error_dialog(title, message):
    """Hiển thị dialog lỗi"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.exec_()

def main():
    """Entry point chính của ứng dụng"""
    parser = argparse.ArgumentParser(description='Smart Eye Detection (SED) Application')
    parser.add_argument('--debug', '-d', 
                       action='store_true',
                       help='Enable debug logging')
    parser.add_argument('--no-camera', 
                       action='store_true',
                       help='Run without camera (for testing)')
    parser.add_argument('--new', 
                       action='store_true',
                       help='Use new main window architecture')
    parser.add_argument('--platform',
                       choices=['xcb', 'wayland', 'eglfs', 'linuxfb'],
                       help='Force specific Qt platform plugin')
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Force Qt platform if specified
    if args.platform:
        os.environ['QT_QPA_PLATFORM'] = args.platform
        logger.info(f"Forcing Qt platform: {args.platform}")
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Smart Eye Detection")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("SED Project")
    
    # Set application style
    app.setStyle('Fusion')
    
    # Ensure camera patches are applied
    try:
        from camera.camera_patches import apply_all_patches
        apply_all_patches()
        logger.info("Camera patches applied successfully")
    except Exception as e:
        logger.warning(f"Failed to apply camera patches: {e}")
    
    try:
        # Import main window (chọn phiên bản theo tham số --new)
        logger.info("Loading SED application...")
        if getattr(args, 'new', False):
            from gui.main_window_new import MainWindowNew
            window = MainWindowNew()
        else:
            from gui.main_window import MainWindow
            window = MainWindow()
        
        # Handle no-camera mode for testing
        if args.no_camera:
            logger.warning("Running in no-camera mode for testing")
            if hasattr(window, 'camera_manager'):
                window.camera_manager.is_camera_available = False
        
        # Show window and run application
        window.show()
        logger.info("SED Application started successfully")
        
        # Run the application
        exit_code = app.exec_()
        
        # Cleanup
        logger.info("Application shutting down...")
        try:
            if hasattr(window, 'camera_manager') and window.camera_manager:
                window.camera_manager.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
        
        sys.exit(exit_code)
        
    except ImportError as e:
        error_msg = f"Failed to import required modules: {str(e)}"
        logger.error(error_msg)
        show_error_dialog("Import Error", 
                         f"{error_msg}\n\nPlease check your dependencies.")
        sys.exit(1)
        
    except Exception as e:
        error_msg = f"Failed to start application: {str(e)}"
        logger.error(error_msg, exc_info=True)
        show_error_dialog("Startup Error", 
                         f"{error_msg}\n\nCheck the log file for more details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
