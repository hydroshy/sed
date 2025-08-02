"""
Module chứa tất cả các import cần thiết cho ứng dụng SED.
File này được tạo để tập trung các import, tránh trùng lặp và dễ quản lý.
"""

# PyQt5 imports
from PyQt5.QtGui import QCloseEvent, QImage, QPixmap, QIntValidator, QDoubleValidator, QPen, QColor, QPainter, QFont
from PyQt5.QtCore import Qt, QStringListModel
from PyQt5.QtWidgets import (
    # Main window components
    QMainWindow, QWidget, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    
    # Layout and containers
    QStackedWidget, QTabWidget, QScrollArea,
    
    # Input widgets
    QComboBox, QPushButton, QSlider, QLineEdit, 
    QSpinBox, QDoubleSpinBox,
    
    # Display widgets
    QProgressBar, QLCDNumber, QListView, QTreeView, QTableView, QLabel,
    
    # Dialog widgets
    QFileDialog, QInputDialog, QMessageBox,
    
    # Layout managers
    QVBoxLayout, QHBoxLayout
)
from PyQt5 import uic

# Standard library imports
import os
import sys
import logging
import json
import time
import traceback
from typing import Dict, List, Optional, Any, Tuple, Union, Callable

# Numpy and CV2 for image processing
import numpy as np
import cv2

# Application specific imports
from job.job_manager import JobManager, Tool, Job
from gui.tool_manager import ToolManager
from gui.settings_manager import SettingsManager
from gui.camera_manager import CameraManager
from gui.detect_tool_manager import DetectToolManager
from gui.camera_view import CameraView
from camera.camera_stream import CameraStream
from tools.detection.ocr_tool import OcrTool
