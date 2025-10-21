#!/usr/bin/env python3
"""
Test script để kiểm tra TCP Controller widgets và setup
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5 import uic
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('TCPControllerTest')

def test_widget_hierarchy():
    """Test xem các widget TCP có được khai báo trong UI file không"""
    logger.info("=" * 80)
    logger.info("TEST 1: Kiểm tra Widget Hierarchy trong UI file")
    logger.info("=" * 80)
    
    app = QApplication(sys.argv)
    
    # Load UI
    ui_path = os.path.join(os.path.dirname(__file__), 'mainUI.ui')
    main_window = QMainWindow()
    uic.loadUi(ui_path, main_window)
    
    # Kiểm tra palettePage
    palettePage = main_window.findChild(QMainWindow.__bases__[0], 'palettePage')
    if not palettePage:
        from PyQt5.QtWidgets import QWidget
        palettePage = main_window.findChild(QWidget, 'palettePage')
    
    logger.info(f"palettePage found: {palettePage is not None}")
    
    if palettePage:
        from PyQt5.QtWidgets import QTabWidget
        paletteTab = palettePage.findChild(QTabWidget, 'paletteTab')
        logger.info(f"paletteTab found: {paletteTab is not None}")
        
        if paletteTab:
            from PyQt5.QtWidgets import QWidget
            # List tất cả tabs
            for i in range(paletteTab.count()):
                tab_widget = paletteTab.widget(i)
                logger.info(f"  Tab {i}: {tab_widget.objectName()} - {paletteTab.tabText(i)}")
            
            controllerTab = paletteTab.findChild(QWidget, 'controllerTab')
            logger.info(f"controllerTab found: {controllerTab is not None}")
            
            if controllerTab:
                from PyQt5.QtWidgets import (QLineEdit, QPushButton, QLabel, 
                                            QListWidget)
                
                # Tìm tất cả TCP widgets
                tcp_widgets = {
                    'ipLineEdit': (QLineEdit, 'ipLineEdit'),
                    'portLineEdit': (QLineEdit, 'portLineEdit'),
                    'connectButton': (QPushButton, 'connectButton'),
                    'statusLabel': (QLabel, 'statusLabel'),
                    'messageListWidget': (QListWidget, 'messageListWidget'),
                    'messageLineEdit': (QLineEdit, 'messageLineEdit'),
                    'sendButton': (QPushButton, 'sendButton'),
                }
                
                logger.info("\nTCP Controller Widgets:")
                for name, (widget_type, obj_name) in tcp_widgets.items():
                    widget = controllerTab.findChild(widget_type, obj_name)
                    status = "✓ FOUND" if widget else "✗ NOT FOUND"
                    logger.info(f"  {name}: {status}")
                    if widget:
                        logger.info(f"    - Enabled: {widget.isEnabled()}")
                        logger.info(f"    - Visible: {widget.isVisible()}")

def test_main_window_initialization():
    """Test xem MainWindow có khởi tạo TCP Controller đúng không"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Kiểm tra MainWindow Initialization")
    logger.info("=" * 80)
    
    try:
        from gui.main_window import MainWindow
        
        app = QApplication.instance() or QApplication(sys.argv)
        
        logger.info("Creating MainWindow...")
        main_window = MainWindow()
        
        # Kiểm tra TCP widgets
        logger.info("\nTCP Controller Widgets in MainWindow:")
        tcp_widget_names = [
            ('ipEdit', 'ipLineEdit'),
            ('portEdit', 'portLineEdit'),
            ('connectButton', 'connectButton'),
            ('statusLabel', 'statusLabel'),
            ('messageList', 'messageListWidget'),
            ('messageEdit', 'messageLineEdit'),
            ('sendButton', 'sendButton'),
        ]
        
        for attr_name, obj_name in tcp_widget_names:
            widget = getattr(main_window, attr_name, None)
            status = "✓ FOUND" if widget else "✗ NOT FOUND"
            logger.info(f"  main_window.{attr_name}: {status}")
            if widget:
                logger.info(f"    - ObjectName: {widget.objectName()}")
                logger.info(f"    - Enabled: {widget.isEnabled()}")
                logger.info(f"    - Visible: {widget.isVisible()}")
        
        # Kiểm tra TCP Controller Manager
        logger.info("\nTCP Controller Manager:")
        tcp_mgr = main_window.tcp_controller
        logger.info(f"  tcp_controller: {tcp_mgr is not None}")
        if tcp_mgr:
            logger.info(f"  tcp_controller.tcp_controller: {tcp_mgr.tcp_controller is not None}")
            logger.info(f"  TCP signals connected: {tcp_mgr.connect_button is not None}")
        
        logger.info("\n✓ MainWindow initialized successfully!")
        
    except Exception as e:
        logger.error(f"✗ Error initializing MainWindow: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    test_widget_hierarchy()
    # test_main_window_initialization()  # Uncomment để test MainWindow
    
    logger.info("\n" + "=" * 80)
    logger.info("Tests completed!")
    logger.info("=" * 80)
