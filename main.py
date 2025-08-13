import sys
import os
import argparse
import logging
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

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
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Smart Eye Detection")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("SED Project")
    
    # Set application style
    app.setStyle('Fusion')
    
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
