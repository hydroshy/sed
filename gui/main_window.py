from PyQt5.QtGui import QCloseEvent
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QGraphicsView, QWidget, QStackedWidget, QComboBox, QPushButton, 
                            QSlider, QLineEdit, QProgressBar, QLCDNumber, QTabWidget, QListView, 
                            QTreeView, QMainWindow, QSpinBox, QDoubleSpinBox, QTableView, QVBoxLayout)
from PyQt5 import uic
import os
import logging
from job.job_manager import JobManager
from gui.tool_manager import ToolManager
from gui.settings_manager import SettingsManager
from gui.camera_manager import CameraManager
from gui.detect_tool_manager import DetectToolManager
from gui.classification_tool_manager import ClassificationToolManager
from gui.workflow_view import WorkflowWidget

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MainWindow(QMainWindow):
    def _clear_tool_config_ui(self):
        """Reset UI cấu hình tool về mặc định khi tạo mới"""
        # Xóa detection area (4 trường)
        if self.x1PositionLineEdit:
            self.x1PositionLineEdit.setText("")
        if self.y1PositionLineEdit:
            self.y1PositionLineEdit.setText("")
        if self.x2PositionLineEdit:
            self.x2PositionLineEdit.setText("")
        if self.y2PositionLineEdit:
            self.y2PositionLineEdit.setText("")
        # Xóa bảng class đã chọn
        if self.classificationTableView and hasattr(self.classificationTableView, 'model'):
            model = self.classificationTableView.model()
            if model:
                model.removeRows(0, model.rowCount())
        # Đặt combobox model về mặc định
        if self.algorithmComboBox:
            if self.algorithmComboBox.count() > 0:
                self.algorithmComboBox.setCurrentIndex(0)
        # Nếu có detect_tool_manager, xóa class đã chọn (nếu có hàm)
        if hasattr(self, 'detect_tool_manager') and hasattr(self.detect_tool_manager, 'selected_classes'):
            self.detect_tool_manager.selected_classes = []
    def _disable_all_overlay_edit_mode(self):
        """Tắt edit mode cho tất cả overlays và current_overlay nếu có camera_view"""
        if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
            camera_view = self.camera_manager.camera_view
            if hasattr(camera_view, 'overlays'):
                for overlay in camera_view.overlays.values():
                    overlay.set_edit_mode(False)
            if hasattr(camera_view, 'current_overlay') and camera_view.current_overlay:
                camera_view.current_overlay.set_edit_mode(False)
                camera_view.current_overlay = None
            camera_view.set_overlay_edit_mode(False)
    def __init__(self):
        super().__init__()
        self._editing_tool = None  # Tool đang được chỉnh sửa
        
        # Khởi tạo các biến thành viên
        self.tool_manager = ToolManager(self)
        self.settings_manager = SettingsManager(self)
        self.camera_manager = CameraManager(self)
        self.job_manager = JobManager()
        self.detect_tool_manager = DetectToolManager(self)
        self.classification_tool_manager = ClassificationToolManager(self)
        
        # Load UI từ file .ui
        ui_path = os.path.join(os.path.dirname(__file__), '..', 'mainUI.ui')
        uic.loadUi(ui_path, self)
        
        # Tìm và kết nối các widget chính
        self._find_widgets()
        
        # Thay thế jobView bằng JobTreeView với drag-drop
        self._upgrade_job_view()
        
        # Debug: Log all QComboBox objectNames after UI load
        for w in self.findChildren(QComboBox):
            logging.info(f"QComboBox found: {w.objectName()}")
        
        # Thiết lập các manager và kết nối signals/slots
        self._setup_managers()
        
        # Kết nối các widget với các hàm xử lý sự kiện
        self._connect_signals()
        
        logging.info("MainWindow initialized successfully")
        
    def _upgrade_job_view(self):
        """Thay thế jobView thông thường bằng JobTreeView với drag-drop"""
        try:
            from gui.job_tree_view import JobTreeView
            from PyQt5.QtWidgets import QTreeView, QWidget
            
            if self.jobView and isinstance(self.jobView, QTreeView):
                parent = self.jobView.parent()
                
                # Kiểm tra parent có phải là QWidget không
                if isinstance(parent, QWidget):
                    layout = parent.layout()
                    
                    if layout is not None:
                        # Lưu thông tin của widget cũ
                        geometry = self.jobView.geometry()
                        style_sheet = self.jobView.styleSheet()
                        object_name = self.jobView.objectName()
                        
                        # Tìm index trong layout
                        index = -1
                        for i in range(layout.count()):
                            item = layout.itemAt(i)
                            if item and item.widget() == self.jobView:
                                index = i
                                break
                        
                        if index >= 0:
                            # Xóa widget cũ khỏi layout
                            old_item = layout.takeAt(index)
                            old_widget = old_item.widget() if old_item else None
                            
                            # Tạo JobTreeView mới
                            new_job_view = JobTreeView(parent)
                            new_job_view.setObjectName(object_name)
                            new_job_view.setGeometry(geometry)
                            if style_sheet:
                                new_job_view.setStyleSheet(style_sheet)
                            
                            # Thêm vào layout tại vị trí cũ
                            layout.insertWidget(index, new_job_view)
                            
                            # Cập nhật reference
                            self.jobView = new_job_view
                            
                            # Xóa widget cũ
                            if old_widget:
                                old_widget.setParent(None)
                                old_widget.deleteLater()
                            
                            logging.info("✅ JobView upgraded to JobTreeView with drag-drop support!")
                            print(f"DEBUG: JobView type after upgrade: {type(self.jobView)}")
                            print(f"DEBUG: JobView drag enabled: {self.jobView.dragEnabled()}")
                            print(f"DEBUG: JobView accepts drops: {self.jobView.acceptDrops()}")
                            return True
                        else:
                            logging.warning("Could not find jobView in parent layout")
                    else:
                        # Trường hợp parent không có layout, thử thay thế trực tiếp
                        logging.info("Parent has no layout, trying direct replacement...")
                        
                        # Lưu thông tin widget cũ
                        geometry = self.jobView.geometry()
                        style_sheet = self.jobView.styleSheet()
                        object_name = self.jobView.objectName()
                        
                        # Tạo JobTreeView mới
                        new_job_view = JobTreeView(parent)
                        new_job_view.setObjectName(object_name)
                        new_job_view.setGeometry(geometry)
                        if style_sheet:
                            new_job_view.setStyleSheet(style_sheet)
                        
                        # Ẩn widget cũ và hiển thị widget mới
                        self.jobView.hide()
                        new_job_view.show()
                        
                        # Cập nhật reference
                        old_job_view = self.jobView
                        self.jobView = new_job_view
                        
                        # Xóa widget cũ sau một chút
                        old_job_view.deleteLater()
                        
                        logging.info("✅ JobView replaced directly with JobTreeView!")
                        return True
                else:
                    logging.warning("JobView parent is not a QWidget")
            elif tool_name == "Classification Tool":
                if self.settings_manager.switch_to_tool_setting_page("Classification Tool"):
                    self.refresh_classification_tool_manager()
            else:
                logging.warning("JobView not found or not a QTreeView")
                
        except ImportError as e:
            logging.error(f"Failed to import JobTreeView: {e}")
        except Exception as e:
            logging.error(f"Failed to upgrade jobView: {e}")
            import traceback
            traceback.print_exc()
            
        return False
        
    def _find_widgets(self):
        """Tìm tất cả các widget cần thiết từ UI file"""
        # Camera view widgets
        self.cameraView = self.findChild(QGraphicsView, 'cameraView')
        self.focusBar = self.findChild(QProgressBar, 'focusBar')
        self.fpsNum = self.findChild(QLCDNumber, 'fpsNum')
        self.executionTime = self.findChild(QLCDNumber, 'executionTime')
        
        # Camera control buttons
        self.liveCamera = self.findChild(QPushButton, 'liveCamera')
        self.triggerCamera = self.findChild(QPushButton, 'triggerCamera')
        self.onlineCamera = self.findChild(QPushButton, 'onlineCamera')  # Thêm onlineCamera button
        self.zoomIn = self.findChild(QPushButton, 'zoomIn')
        self.zoomOut = self.findChild(QPushButton, 'zoomOut')
        self.rotateLeft = self.findChild(QPushButton, 'rotateLeft')
        self.rotateRight = self.findChild(QPushButton, 'rotateRight')
        self.x1PositionLineEdit = self.findChild(QLineEdit, 'x1PositionLineEdit')
        self.y1PositionLineEdit = self.findChild(QLineEdit, 'y1PositionLineEdit')
        self.x2PositionLineEdit = self.findChild(QLineEdit, 'x2PositionLineEdit')
        self.y2PositionLineEdit = self.findChild(QLineEdit, 'y2PositionLineEdit')
        # Reset detection area fields
        if self.x1PositionLineEdit:
            self.x1PositionLineEdit.setText("")
        if self.y1PositionLineEdit:
            self.y1PositionLineEdit.setText("")
        if self.x2PositionLineEdit:
            self.x2PositionLineEdit.setText("")
        if self.y2PositionLineEdit:
            self.y2PositionLineEdit.setText("")
        self.triggerCameraMode = self.findChild(QPushButton, 'triggerCameraMode')
        self.liveCameraMode = self.findChild(QPushButton, 'liveCameraMode')
        
        # Camera settings widgets (use only new names)
        # EV may be absent
        self.evEdit = self.findChild(QDoubleSpinBox, 'evEdit')
        # New-only: exposure and gain controls
        self.exposureEdit = self.findChild(QDoubleSpinBox, 'exposureTimeEdit')
        self.gainEdit = self.findChild(QDoubleSpinBox, 'analogueGainEdit')
        # AE buttons (new-only)
        self.manualExposure = self.findChild(QPushButton, 'manualAE')
        self.autoExposure = self.findChild(QPushButton, 'autoAE')
        # AWB buttons & spinboxes (new-only)
        self.autoAWB = self.findChild(QPushButton, 'autoAWB')
        self.manualAWB = self.findChild(QPushButton, 'manualAWB')
        self.colourGainREdit = self.findChild(QDoubleSpinBox, 'colourGainREdit')
        self.colourGainBEdit = self.findChild(QDoubleSpinBox, 'colourGainBEdit')
        
        # Try to find formatCameraComboBox using different methods
        self.formatCameraComboBox = self.findChild(QComboBox, 'formatCameraComboBox')
        if not self.formatCameraComboBox:
            # Alternative method: search through all combo boxes
            all_combos = self.findChildren(QComboBox)
            for combo in all_combos:
                if combo.objectName() == 'formatCameraComboBox':
                    self.formatCameraComboBox = combo
                    break
        
        print(f"DEBUG: formatCameraComboBox found: {self.formatCameraComboBox is not None}")
        if self.formatCameraComboBox:
            print(f"DEBUG: formatCameraComboBox type: {type(self.formatCameraComboBox)}")
        else:
            print("DEBUG: formatCameraComboBox is None - searching for all ComboBoxes")
            all_combos = self.findChildren(QComboBox)
            for combo in all_combos:
                print(f"DEBUG: Found combo: {combo.objectName()}")
        
        # Settings control buttons
        self.applySetting = self.findChild(QPushButton, 'applySetting')
        self.cancelSetting = self.findChild(QPushButton, 'cancelSetting')
        
        # Frame size control widgets
        self.widthCameraFrameSpinBox = self.findChild(QSpinBox, 'widthCameraFrameSpinBox')
        self.heightCameraFrameSpinBox = self.findChild(QSpinBox, 'heightCameraFrameSpinBox')
        
        # Job management widgets
        self.paletteTab = self.findChild(QTabWidget, 'paletteTab')
        self.jobTab = self.findChild(QTreeView, 'jobTab')
        self.jobView = self.findChild(QTreeView, 'jobView')
        self.removeJob = self.findChild(QPushButton, 'removeJob')
        self.editJob = self.findChild(QPushButton, 'editJob')
        
        # Tạo tab Workflow để hiển thị workflow - TEMPORARILY DISABLED
        # self.workflowTab = QWidget()
        # if self.paletteTab:
        #     self.paletteTab.addTab(self.workflowTab, "Workflow")
        #     # Tạo WorkflowWidget và thêm vào tab
        #     self.workflow_widget = WorkflowWidget(self.workflowTab)
        #     layout = QVBoxLayout(self.workflowTab)
        #     layout.addWidget(self.workflow_widget)
        #     self.workflowTab.setLayout(layout)
        self.addJob = self.findChild(QPushButton, 'addJob')
        self.loadJob = self.findChild(QPushButton, 'loadJob')
        self.toolView = self.findChild(QListView, 'toolView')
        self.addTool = self.findChild(QPushButton, 'addTool')
        self.editTool = self.findChild(QPushButton, 'editTool')
        self.removeTool = self.findChild(QPushButton, 'removeTool')
        self.cancleTool = self.findChild(QPushButton, 'cancleTool')
        self.toolComboBox = self.findChild(QComboBox, 'toolComboBox')
        
        # Source output combo box to control camera view pipeline
        self.sourceOutputComboBox = self.findChild(QComboBox, 'sourceOutputComboBox')
        print(f"DEBUG: main_window sourceOutputComboBox found: {self.sourceOutputComboBox is not None}")
        if self.sourceOutputComboBox:
            print(f"DEBUG: sourceOutputComboBox type: {type(self.sourceOutputComboBox)}")
        else:
            print("DEBUG: sourceOutputComboBox is None!")
            # Try to find it with different methods
            all_combos = self.findChildren(QComboBox)
            for combo in all_combos:
                print(f"DEBUG: Found combo: {combo.objectName()}")
            # Try to find it specifically
            source_combo = None
            for combo in all_combos:
                if 'sourceOutput' in combo.objectName():
                    source_combo = combo
                    break
            if source_combo:
                print(f"DEBUG: Found sourceOutput combo via manual search: {source_combo.objectName()}")
                self.sourceOutputComboBox = source_combo
        
        # Settings widgets
        self.settingStackedWidget = self.findChild(QStackedWidget, 'settingStackedWidget')
        self.cameraSettingPage = self.findChild(QWidget, 'cameraSettingPage')
        self.detectSettingPage = self.findChild(QWidget, 'detectSettingPage')
        self.cameraSettingFrame = self.findChild(QWidget, 'cameraSettingFrame')
        self.detectSettingFrame = self.findChild(QWidget, 'detectSettingFrame')
        
        # Detect tool widgets
        self.drawAreaButton = self.findChild(QPushButton, 'drawAreaButton')
        self.xPositionLineEdit = self.findChild(QLineEdit, 'xPositionLineEdit')
        self.yPositionLineEdit = self.findChild(QLineEdit, 'yPositionLineEdit')
        
        # Thiết lập cấu hình cho DoubleSpinBox thay vì validators
        if self.exposureEdit:
            self.exposureEdit.setMinimum(1.0)  # 1μs minimum
            self.exposureEdit.setMaximum(10000000.0)  # 10s maximum  
            self.exposureEdit.setValue(10000.0)  # 10ms default (10000μs)
            self.exposureEdit.setDecimals(1)  # 1 decimal place
            self.exposureEdit.setSuffix(" μs")  # Microseconds unit suffix
            
            
        if self.evEdit:
            self.evEdit.setMinimum(-2.0)  # -2.0 minimum EV
            self.evEdit.setMaximum(2.0)  # 2.0 maximum EV
            self.evEdit.setValue(0.0)  # 0.0 default EV
            self.evEdit.setDecimals(1)  # 1 decimal place
            
        if self.gainEdit:
            self.gainEdit.setMinimum(0.0)  # Minimum gain
            self.gainEdit.setMaximum(10.0)  # Maximum gain
            self.gainEdit.setValue(1.0)  # Default gain
            self.gainEdit.setDecimals(2)  # 2 decimal places
            self.gainEdit.setSingleStep(0.1)  # Step by 0.1
            
        # Tìm các widget Detect Tool settings (không phụ thuộc vào detectSettingFrame)
        self.thresholdSlider = self.findChild(QSlider, 'thresholdSlider')
        self.thresholdSpinBox = self.findChild(QSlider, 'thresholdSpinBox')  # Note: This might need to be changed to QSpinBox
        self.minConfidenceEdit = self.findChild(QLineEdit, 'minConfidenceEdit')  # Note: This might need to be changed to QDoubleSpinBox
        
        # Model and classification widgets
        self.algorithmComboBox = self.findChild(QComboBox, 'algorithmComboBox')
        self.classificationComboBox = self.findChild(QComboBox, 'classificationComboBox')
        self.addClassificationButton = self.findChild(QPushButton, 'addClassificationButton')
        self.removeClassificationButton = self.findChild(QPushButton, 'removeClassificationButton')
        self.classificationScrollArea = self.findChild(QWidget, 'classificationScrollArea')  # QScrollArea or QListWidget
        self.classificationTableView = self.findChild(QTableView, 'classificationTableView')
        
        # Debug logging for widget finding
        logging.info(f"detectSettingFrame found: {self.detectSettingFrame is not None}")
        logging.info(f"Found algorithmComboBox: {self.algorithmComboBox is not None}")
        logging.info(f"Found classificationComboBox: {self.classificationComboBox is not None}")
        logging.info(f"Found addClassificationButton: {self.addClassificationButton is not None}")
        logging.info(f"Found removeClassificationButton: {self.removeClassificationButton is not None}")
        logging.info(f"Found classificationScrollArea: {self.classificationScrollArea is not None}")
        
        # Log actual widget addresses if found
        if self.algorithmComboBox:
            logging.info(f"algorithmComboBox address: {hex(id(self.algorithmComboBox))}")
        if self.classificationComboBox:
            logging.info(f"classificationComboBox address: {hex(id(self.classificationComboBox))}")
        
    def _setup_managers(self):
        """Thiết lập và kết nối các manager"""
        # Setup ToolManager
        self.tool_manager.setup(
            self.job_manager,
            self.toolView,
            self.jobView,
            self.toolComboBox,
            self  # Pass main_window reference
        )
        
        # Setup SettingsManager
        self.settings_manager.setup(
            self.settingStackedWidget,
            self.cameraSettingPage,
            self.detectSettingPage,
            self.applySetting,
            self.cancleSetting,
            save_image_page=getattr(self, 'saveImagePage', None)
        )
        
        # Setup CameraManager
        self.camera_manager.setup(
            self.cameraView,
            self.exposureEdit,
            self.gainEdit,
            self.evEdit,
            self.focusBar,
            self.fpsNum,
            self.sourceOutputComboBox
        )
        
        # Setup frame size spinboxes if they exist
        if hasattr(self, 'widthCameraFrameSpinBox') and hasattr(self, 'heightCameraFrameSpinBox'):
            self.camera_manager.setup_frame_size_spinboxes(
                self.widthCameraFrameSpinBox,
                self.heightCameraFrameSpinBox
            )
        
        # Setup camera control buttons (handle missing widgets gracefully)
        self.camera_manager.setup_camera_buttons(
            live_camera_btn=getattr(self, 'liveCamera', None),
            trigger_camera_btn=getattr(self, 'triggerCamera', None),
            auto_exposure_btn=self.autoExposure,
            manual_exposure_btn=self.manualExposure,
            apply_settings_btn=getattr(self, 'applySetting', None),
            cancel_settings_btn=getattr(self, 'cancelSetting', None),
            job_toggle_btn=getattr(self, 'runJob', None),  # Use runJob as toggle button
            live_camera_mode=getattr(self, 'liveCameraMode', None),
            trigger_camera_mode=getattr(self, 'triggerCameraMode', None),
            auto_awb_btn=self.autoAWB,
            manual_awb_btn=self.manualAWB,
            colour_gain_r_edit=self.colourGainREdit,
            colour_gain_b_edit=self.colourGainBEdit
        )
        
        # Link CameraManager with SettingsManager for synchronization
        self.camera_manager.set_settings_manager(self.settings_manager)
        
        # Setup area change connections
        if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
            if hasattr(self.camera_manager.camera_view, 'area_changed'):
                self.camera_manager.camera_view.area_changed.connect(self._on_area_changed)
        
        # Setup DetectToolManager
        if hasattr(self, 'detect_tool_manager'):
            logging.info("Setting up DetectToolManager...")
            logging.info(f"algorithmComboBox before setup: {self.algorithmComboBox}")
            logging.info(f"classificationComboBox before setup: {self.classificationComboBox}")
            
            self.detect_tool_manager.setup_ui_components(
                algorithm_combo=self.algorithmComboBox,
                classification_combo=self.classificationComboBox,
                add_btn=self.addClassificationButton,
                remove_btn=self.removeClassificationButton,
                scroll_area=self.classificationScrollArea,
                table_view=self.classificationTableView
            )
        else:
            logging.error("DetectToolManager not initialized!")

        # Setup ClassificationToolManager (bind to classificationSettingPage widgets)
        try:
            from PyQt5.QtWidgets import QWidget, QComboBox, QFrame
            
            logging.info("Setting up ClassificationToolManager...")
            
            # First, try to find the classification page
            classification_page = None
            if hasattr(self, 'settingStackedWidget') and self.settingStackedWidget:
                classification_page = self.settingStackedWidget.findChild(QWidget, 'classificationSettingPage')
                logging.info(f"Classification page from stackedWidget: {classification_page is not None}")
            
            if not classification_page:
                classification_page = self.findChild(QWidget, 'classificationSettingPage')
                logging.info(f"Classification page from main window: {classification_page is not None}")
            
            # Debug: List all pages in stacked widget
            if hasattr(self, 'settingStackedWidget') and self.settingStackedWidget:
                page_count = self.settingStackedWidget.count()
                logging.info(f"StackedWidget has {page_count} pages:")
                for i in range(page_count):
                    page = self.settingStackedWidget.widget(i)
                    logging.info(f"  Page {i}: {page.__class__.__name__} '{page.objectName()}'")
            
            # Try to find combo boxes in various ways
            model_combo = None
            class_combo = None
            
            # Method 1: Look in frame within page
            if classification_page:
                frame = classification_page.findChild(QFrame, 'classificationSettingFrame')
                logging.info(f"Classification frame found: {frame is not None}")
                if frame:
                    model_combo = frame.findChild(QComboBox, 'modelComboBox')
                    class_combo = frame.findChild(QComboBox, 'classComboBox')
                    logging.info(f"Classification setup: frame method -> model_combo: {model_combo is not None}, class_combo: {class_combo is not None}")
                
                # Method 2: Look directly in page
                if not model_combo or not class_combo:
                    if not model_combo:
                        model_combo = classification_page.findChild(QComboBox, 'modelComboBox')
                    if not class_combo:
                        class_combo = classification_page.findChild(QComboBox, 'classComboBox')
                    logging.info(f"Classification setup: page method -> model_combo: {model_combo is not None}, class_combo: {class_combo is not None}")
            
            # Method 3: Global search as fallback
            if not model_combo or not class_combo:
                if not model_combo:
                    model_combo = self.findChild(QComboBox, 'modelComboBox')
                if not class_combo:
                    class_combo = self.findChild(QComboBox, 'classComboBox')
                logging.info(f"Classification setup: global method -> model_combo: {model_combo is not None}, class_combo: {class_combo is not None}")
                
                # Debug: List all combo boxes
                all_combos = self.findChildren(QComboBox)
                logging.info(f"All combo boxes in main window ({len(all_combos)}):")
                for combo in all_combos:
                    logging.info(f"  ComboBox: '{combo.objectName()}'")
            
            # Log what we found
            if model_combo:
                logging.info(f"Found modelComboBox: {model_combo.objectName()} at {hex(id(model_combo))}")
            if class_combo:
                logging.info(f"Found classComboBox: {class_combo.objectName()} at {hex(id(class_combo))}")
            
            # Setup if we have both combo boxes
            if model_combo is not None and class_combo is not None and hasattr(self, 'classification_tool_manager'):
                logging.info("Setting up ClassificationToolManager with found combo boxes")
                self.classification_tool_manager.setup_ui_components(model_combo, class_combo)
                logging.info("ClassificationToolManager UI components setup completed")
                
                # Store references for later access
                self.class_modelComboBox = model_combo
                self.class_classComboBox = class_combo
            else:
                missing_items = []
                if model_combo is None:
                    missing_items.append("modelComboBox")
                if class_combo is None:
                    missing_items.append("classComboBox")
                if not hasattr(self, 'classification_tool_manager'):
                    missing_items.append("classification_tool_manager")
                logging.warning(f"ClassificationToolManager setup failed - missing: {missing_items}")
        except Exception as e:
            logging.error(f"Failed to setup ClassificationToolManager: {e}")
            import traceback
            traceback.print_exc()
        
        # Enable UI after setup is complete
        self.camera_manager.set_ui_enabled(True)
        
        # Force mode to Live on startup (do not start camera)
        try:
            if hasattr(self.camera_manager, 'on_live_camera_mode_clicked'):
                self.camera_manager.on_live_camera_mode_clicked()
        except Exception as e:
            logging.error(f"Failed to set default live mode: {e}")
        
        # Load available camera formats
        self._load_camera_formats()
        
        # Đảm bảo rằng nút Apply/Cancel bị vô hiệu hóa khi khởi động
        if hasattr(self, 'settings_manager'):
            self.settings_manager.post_init()
            
        # Cập nhật workflow view ban đầu - TEMPORARILY DISABLED
        # self._update_workflow_view()
        
    def _update_workflow_view(self):
        """Cập nhật workflow view khi job thay đổi - TEMPORARILY DISABLED"""
        # if hasattr(self, 'workflow_widget'):
        #     current_job = self.job_manager.get_current_job()
        #     self.workflow_widget.build_workflow_from_job(current_job)
        #     logging.info("Đã cập nhật workflow view")
        pass

    def refresh_classification_tool_manager(self):
        """Refresh ClassificationToolManager connections and reload models/classes"""
        try:
            if hasattr(self, 'classification_tool_manager') and self.classification_tool_manager:
                logging.info("Refreshing ClassificationToolManager connections...")
                
                ctm = self.classification_tool_manager
                
                # Always search for combo boxes fresh (don't trust cached references)
                logging.info("Searching for combo boxes...")
                
                # Use the same robust search logic as in _setup_managers
                from PyQt5.QtWidgets import QWidget, QComboBox, QFrame
                
                # Find classification page
                classification_page = None
                if hasattr(self, 'settingStackedWidget') and self.settingStackedWidget:
                    classification_page = self.settingStackedWidget.findChild(QWidget, 'classificationSettingPage')
                    logging.info(f"Classification page from stackedWidget: {classification_page is not None}")
                if not classification_page:
                    classification_page = self.findChild(QWidget, 'classificationSettingPage')
                    logging.info(f"Classification page from main window: {classification_page is not None}")
                
                # Find combo boxes with simpler, clearer logic
                model_combo = None
                class_combo = None
                
                # Step 1: Try frame search
                if classification_page:
                    frame = classification_page.findChild(QFrame, 'classificationSettingFrame')
                    logging.info(f"Classification frame found: {frame is not None}")
                    if frame:
                        model_combo = frame.findChild(QComboBox, 'modelComboBox')
                        class_combo = frame.findChild(QComboBox, 'classComboBox')
                        logging.info(f"Frame search -> model_combo: {model_combo is not None}, class_combo: {class_combo is not None}")
                        
                        if model_combo is not None and class_combo is not None:
                            logging.info("✅ Found both combo boxes in frame - stopping search")
                        else:
                            logging.warning("❌ Frame search incomplete - continuing...")
                    else:
                        logging.warning("❌ Frame not found - continuing to page search...")
                
                # Step 2: Try page search (only if needed)
                if (model_combo is None or class_combo is None) and classification_page:
                    logging.info("Trying direct page search...")
                    if model_combo is None:
                        model_combo = classification_page.findChild(QComboBox, 'modelComboBox')
                        logging.info(f"Page search for modelComboBox: {model_combo is not None}")
                    if class_combo is None:
                        class_combo = classification_page.findChild(QComboBox, 'classComboBox')
                        logging.info(f"Page search for classComboBox: {class_combo is not None}")
                    
                    if model_combo is not None and class_combo is not None:
                        logging.info("✅ Found both combo boxes in page - stopping search")
                
                # Step 3: Global search (only if still needed)
                if model_combo is None or class_combo is None:
                    logging.info("Trying global search...")
                    if model_combo is None:
                        model_combo = self.findChild(QComboBox, 'modelComboBox')
                        logging.info(f"Global search for modelComboBox: {model_combo is not None}")
                    if class_combo is None:
                        class_combo = self.findChild(QComboBox, 'classComboBox')
                        logging.info(f"Global search for classComboBox: {class_combo is not None}")
                
                # Final status
                logging.info(f"🔍 Search complete: model_combo={model_combo is not None}, class_combo={class_combo is not None}")
                
                # Setup if found
                logging.info(f"Final check before setup: model_combo={model_combo is not None}, class_combo={class_combo is not None}")
                if model_combo:
                    logging.info(f"model_combo details: {type(model_combo)} '{model_combo.objectName()}'")
                if class_combo:
                    logging.info(f"class_combo details: {type(class_combo)} '{class_combo.objectName()}'")
                
                if model_combo is not None and class_combo is not None:
                    try:
                        logging.info("Both combo boxes found, setting up ClassificationToolManager...")
                        ctm.setup_ui_components(model_combo, class_combo)
                        logging.info("ClassificationToolManager: UI components bound on refresh")
                        # Store references
                        self.class_modelComboBox = model_combo
                        self.class_classComboBox = class_combo
                    except Exception as setup_error:
                        logging.error(f"Error in setup_ui_components: {setup_error}")
                        import traceback
                        traceback.print_exc()
                        return
                else:
                    # This should never happen based on our logs, but let's check why
                    logging.warning(f"ClassificationToolManager: Logic error - model_combo: {model_combo is not None}, class_combo: {class_combo is not None}")
                    if model_combo is not None:
                        logging.warning(f"model_combo bool value: {bool(model_combo)}")
                        logging.warning(f"model_combo type: {type(model_combo)}")
                        logging.warning(f"model_combo objectName: {model_combo.objectName()}")
                    if class_combo is not None:
                        logging.warning(f"class_combo bool value: {bool(class_combo)}")
                        logging.warning(f"class_combo type: {type(class_combo)}")
                        logging.warning(f"class_combo objectName: {class_combo.objectName()}")
                    return
                
                # Force refresh connections and reload models
                if hasattr(ctm, '_force_refresh_connections'):
                    ctm._force_refresh_connections()
                
                # Reload models immediately instead of using QTimer
                try:
                    logging.info("ClassificationToolManager: loading models immediately")
                    ctm.load_available_models()
                    logging.info("ClassificationToolManager: models loaded immediately")
                except Exception as load_error:
                    logging.error(f"ClassificationToolManager: immediate load error: {load_error}")
                    import traceback
                    traceback.print_exc()
                    # Fallback to QTimer
                    try:
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(100, ctm.load_available_models)
                        logging.info("ClassificationToolManager: scheduled model loading as fallback")
                    except Exception:
                        logging.error("ClassificationToolManager: even QTimer fallback failed")
                    
        except Exception as e:
            logging.error(f"Failed to refresh ClassificationToolManager: {e}")
            import traceback
            traceback.print_exc()
        
    def _toggle_camera(self, checked):
        """Đơn giản: bật/tắt camera stream để hiển thị frame lên cameraView
        
        Args:
            checked: Boolean, True = bật camera, False = tắt camera
        """
        try:
            logging.info(f"Simple camera toggle: {checked}")
            
            if not hasattr(self, 'camera_manager') or not self.camera_manager:
                logging.error("Camera manager not available")
                return
            
            # Check if Camera Source exists in job before allowing camera operation
            if checked and not self._has_camera_source_in_job():
                logging.warning("Cannot start camera: No Camera Source tool in job")
                self.onlineCamera.setChecked(False)
                return
                
            if checked:
                # Bật camera stream đơn giản
                logging.info("Starting camera stream...")
                success = False
                
                if hasattr(self.camera_manager, 'camera_stream') and self.camera_manager.camera_stream:
                    try:
                        # Gọi start_live() để bắt đầu stream frame
                        success = self.camera_manager.camera_stream.start_live()
                        if success:
                            logging.info("Camera stream started successfully")
                            # Enable job execution để có thể chạy classification
                            if hasattr(self.camera_manager.camera_stream, 'set_job_enabled'):
                                self.camera_manager.camera_stream.set_job_enabled(True)
                                logging.info("Job execution enabled on camera stream")
                            # Also enable job execution in camera manager
                            if hasattr(self.camera_manager, 'job_enabled'):
                                self.camera_manager.job_enabled = True
                                logging.info("Job execution enabled in camera manager")
                            # Set button style to green when active
                            self.onlineCamera.setStyleSheet("""
                                QPushButton {
                                    background-color: #4CAF50;  /* Green */
                                    color: white;
                                    border: 2px solid #45a049;
                                    border-radius: 4px;
                                    font-weight: bold;
                                }
                                QPushButton:hover {
                                    background-color: #45a049;
                                }
                            """)
                        else:
                            logging.error("Camera stream failed to start")
                    except Exception as e:
                        logging.error(f"Error starting camera stream: {e}")
                        success = False
                else:
                    logging.error("Camera stream not initialized")
                
                if not success:
                    # Nếu thất bại, bỏ check nút và set màu đỏ
                    self.onlineCamera.setChecked(False)
                    self._set_camera_button_off_style()
                    
            else:
                # Tắt camera stream đơn giản
                logging.info("Stopping camera stream...")
                
                if hasattr(self.camera_manager, 'camera_stream') and self.camera_manager.camera_stream:
                    try:
                        # Disable job execution when stopping camera
                        if hasattr(self.camera_manager.camera_stream, 'set_job_enabled'):
                            self.camera_manager.camera_stream.set_job_enabled(False)
                            logging.info("Job execution disabled on camera stream")
                        if hasattr(self.camera_manager, 'job_enabled'):
                            self.camera_manager.job_enabled = False
                            logging.info("Job execution disabled in camera manager")
                        
                        self.camera_manager.camera_stream.stop_live()
                        logging.info("Camera stream stopped")
                    except Exception as e:
                        logging.error(f"Error stopping camera stream: {e}")
                else:
                    logging.warning("Camera stream not available")
                
                # Set button style to red when inactive
                self._set_camera_button_off_style()
                    
        except Exception as e:
            logging.error(f"Error in simple camera toggle: {e}")
            import traceback
            traceback.print_exc()
            # Reset button state and style on error
            self.onlineCamera.setChecked(False)
            self._set_camera_button_off_style()
            
    def _set_camera_button_off_style(self):
        """Set camera button style to red (off state)"""
        self.onlineCamera.setStyleSheet("""
            QPushButton {
                background-color: #f44336;  /* Red */
                color: white;
                border: 2px solid #da190b;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
                border: 2px solid #999999;
            }
        """)
        
    def _update_camera_button_state(self):
        """Update camera button state based on whether Camera Source exists in job"""
        try:
            has_camera_source = self._has_camera_source_in_job()
            
            logging.info(f"_update_camera_button_state called: has_camera_source={has_camera_source}")
            
            if has_camera_source:
                # Enable button and set red style (off state)
                self.onlineCamera.setEnabled(True)
                self._set_camera_button_off_style()
                logging.info("Camera button enabled (has Camera Source in job)")
            else:
                # Disable button and set gray style
                self.onlineCamera.setEnabled(False)
                self.onlineCamera.setChecked(False)
                self.onlineCamera.setStyleSheet("""
                    QPushButton {
                        background-color: #cccccc;  /* Gray */
                        color: #666666;
                        border: 2px solid #999999;
                        border-radius: 4px;
                        font-weight: bold;
                    }
                """)
                logging.info("Camera button disabled (no Camera Source in job)")
                
        except Exception as e:
            logging.error(f"Error updating camera button state: {e}")
            
    def _has_camera_source_in_job(self):
        """Check if current job has a Camera Source tool"""
        try:
            if not hasattr(self, 'job_manager') or not self.job_manager:
                logging.info("_has_camera_source_in_job: No job_manager")
                return False
                
            current_job = self.job_manager.get_current_job()
            if not current_job:
                logging.info("_has_camera_source_in_job: No current job")
                return False
                
            logging.info(f"_has_camera_source_in_job: Checking {len(current_job.tools)} tools")
            
            # Check if job has any tools with Camera Source type
            for i, tool in enumerate(current_job.tools):
                tool_type = getattr(tool, 'tool_type', 'Unknown')
                display_name = getattr(tool, 'display_name', 'Unknown')
                logging.info(f"  Tool {i}: tool_type='{tool_type}', display_name='{display_name}'")
                
                if hasattr(tool, 'tool_type') and tool.tool_type == "Camera Source":
                    logging.info("_has_camera_source_in_job: Found Camera Source by tool_type")
                    return True
                elif hasattr(tool, 'display_name') and tool.display_name == "Camera Source":
                    logging.info("_has_camera_source_in_job: Found Camera Source by display_name")
                    return True
                    
            logging.info("_has_camera_source_in_job: No Camera Source found")
            return False
            
        except Exception as e:
            logging.error(f"Error checking for Camera Source in job: {e}")
            return False
        
    def refresh_detect_tool_manager(self):
        """Refresh DetectToolManager connections when switching to detect page"""
        if hasattr(self, 'detect_tool_manager'):
            logging.info("Refreshing DetectToolManager connections...")
            self.detect_tool_manager._force_refresh_connections()
            
            # Test signal by logging current state
            if self.algorithmComboBox:
                logging.info(f"Current algorithm combo selection: {self.algorithmComboBox.currentText()}")
                logging.info(f"Algorithm combo item count: {self.algorithmComboBox.count()}")
            
            if self.classificationComboBox:
                logging.info(f"Current classification combo count: {self.classificationComboBox.count()}")
                for i in range(self.classificationComboBox.count()):
                    logging.info(f"  Class {i}: {self.classificationComboBox.itemText(i)}")
        else:
            logging.warning("DetectToolManager not available for refresh")
        
    def _connect_signals(self):
        # Job run button
        if hasattr(self, 'runJob') and self.runJob:
            self.runJob.clicked.connect(self.run_current_job)
            logging.info("runJob button connected to run_current_job.")
        """Kết nối các signal với các slot tương ứng"""
        # Tool management connections
        if self.addTool:
            self.addTool.clicked.connect(self._on_add_tool)
            logging.info("addTool button connected to _on_add_tool.")
        
        if self.editTool:
            self.editTool.clicked.connect(self._on_edit_tool)
            logging.info("editTool button connected to _on_edit_tool.")
            
        if self.removeTool:
            self.removeTool.clicked.connect(self._on_remove_tool)
            logging.info("removeTool button connected to _on_remove_tool.")
        
        if self.cancleTool:
            self.cancleTool.clicked.connect(self.tool_manager.on_remove_tool_from_job)
            
        if self.editJob:
            self.editJob.clicked.connect(self._on_edit_job)
            
        if self.removeJob:
            self.removeJob.clicked.connect(self.tool_manager.on_remove_tool_from_job)
            
        # Settings connections
        if self.applySetting:
            self.applySetting.clicked.connect(self._on_apply_setting)
            
        if self.cancleSetting:
            self.cancleSetting.clicked.connect(self._on_cancel_setting)
            
        # Detect tool connections
        if self.drawAreaButton:
            self.drawAreaButton.clicked.connect(self._on_draw_area_clicked)
            
        # Camera connections
        if self.liveCamera:
            self.liveCamera.setCheckable(True)
            self.liveCamera.clicked.connect(self.camera_manager.on_live_camera_clicked)
            
        if self.onlineCamera:  # Thêm kết nối cho nút onlineCamera dạng toggle
            self.onlineCamera.setCheckable(True)  # Làm cho nút có thể chọn
            self.onlineCamera.clicked.connect(self._toggle_camera)
            # Set initial state based on job (gray if no Camera Source, red if has Camera Source but off)
            self._update_camera_button_state()
            logging.info("onlineCamera button connected to _toggle_camera.")
            
        if self.triggerCamera:
            self.triggerCamera.clicked.connect(self.camera_manager.on_trigger_camera_clicked)
            
        if self.zoomIn:
            self.zoomIn.clicked.connect(self.camera_manager.zoom_in)
            
        if self.zoomOut:
            self.zoomOut.clicked.connect(self.camera_manager.zoom_out)
            
        if self.rotateLeft:
            self.rotateLeft.clicked.connect(self.camera_manager.rotate_left)
            
        if self.rotateRight:
            self.rotateRight.clicked.connect(self.camera_manager.rotate_right)

        # Camera pixel format combo box: apply immediately when selection changes
        try:
            if getattr(self, 'formatCameraComboBox', None):
                # Prefer text-changed signal for immediate update
                try:
                    self.formatCameraComboBox.currentTextChanged.connect(self._on_format_changed)
                    logging.info("formatCameraComboBox connected to _on_format_changed (currentTextChanged)")
                except Exception:
                    pass
                # Fallbacks for environments where currentTextChanged may not emit
                try:
                    # activated[str] passes the selected text directly
                    self.formatCameraComboBox.activated[str].connect(self._on_format_changed)
                    logging.info("formatCameraComboBox connected to _on_format_changed (activated[str])")
                except Exception:
                    pass
                try:
                    # As a last resort, map index change to current text
                    self.formatCameraComboBox.currentIndexChanged.connect(
                        lambda idx: self._on_format_changed(self.formatCameraComboBox.itemText(idx))
                    )
                    logging.info("formatCameraComboBox connected to _on_format_changed (currentIndexChanged)")
                except Exception:
                    pass
        except Exception as e:
            logging.error(f"Failed to connect formatCameraComboBox signals: {e}")
            
        if self.manualExposure:
            self.manualExposure.clicked.connect(self.camera_manager.set_manual_exposure_mode)
            
        if self.autoExposure:
            self.autoExposure.clicked.connect(self.camera_manager.set_auto_exposure_mode)
            
        # runJob button is now handled by camera_manager as job_toggle_btn
        # if self.runJob:
        #     self.runJob.clicked.connect(self.run_current_job)
            
        # Job save/load connections
        if self.saveJob:
            self.saveJob.clicked.connect(self.save_current_job)
            
        if self.loadJob:
            self.loadJob.clicked.connect(self.load_job_file)
            
        if self.addJob:
            self.addJob.clicked.connect(self.add_new_job)
            
        if self.removeJob:
            self.removeJob.clicked.connect(self.remove_current_job)
            
        # Kết nối sự kiện thay đổi tab để cập nhật workflow khi chuyển tab
        if hasattr(self, 'paletteTab') and self.paletteTab:
            self.paletteTab.currentChanged.connect(self._on_tab_changed)
            
        # Kết nối workflow view với tool manager - TEMPORARILY DISABLED
        # if hasattr(self, 'workflow_widget'):
        #     self.workflow_widget.node_selected.connect(self._on_workflow_node_selected)
            
        # Add Camera Source to tool combo box if not already present
        self._add_camera_source_to_combo_box()
    
    def _add_camera_source_to_combo_box(self):
        """Ensure common tools exist in the tool combo box"""
        if self.toolComboBox:
            items = [self.toolComboBox.itemText(i) for i in range(self.toolComboBox.count())]
            for text in ["Camera Source", "Classification Tool"]:
                if text and text not in items:
                    self.toolComboBox.addItem(text)
                    logging.info(f"MainWindow: Added {text} to tool combo box")
    
    def _on_tab_changed(self, index):
        """Xử lý khi người dùng chuyển tab"""
        tab_widget = self.sender()
        if tab_widget and index < tab_widget.count():
            tab_name = tab_widget.tabText(index)
            if tab_name == "Workflow":
                # Cập nhật workflow view khi chuyển đến tab Workflow
                self._update_workflow_view()
                
    def _on_workflow_node_selected(self, tool_id):
        """Xử lý khi người dùng chọn một node trong workflow view"""
        # Tìm tool bằng ID
        current_job = self.job_manager.get_current_job()
        if current_job:
            tool = current_job.get_tool_by_id(tool_id)
            if tool:
                # Hiển thị thông tin về tool
                logging.info(f"Selected tool: {tool.display_name} (ID: {tool.tool_id})")
                # Có thể thêm code để chọn tool trong jobView
    
    def _on_add_tool(self):
        """Xử lý khi người dùng nhấn nút Add Tool"""
        # Lấy công cụ được chọn
        tool_name = self.tool_manager.on_add_tool()
        # Khi add tool mới, không truyền detection_area từ tool trước đó
        # pending_detection_area chỉ dùng cho preview/crop khi cần
        self.tool_manager._pending_detection_area = None
        if tool_name:
            # Handle Save Image tool specifically
            if tool_name == "Save Image":
                if self.settings_manager.switch_to_tool_setting_page("Save Image"):
                    self.setup_save_image_tool_logic()
            elif tool_name == "Classification Tool":
                if self.settings_manager.switch_to_tool_setting_page("Classification Tool"):
                    self.refresh_classification_tool_manager()
            else:
                self.settings_manager.switch_to_tool_setting_page(tool_name)
                self._clear_tool_config_ui()
                # Cập nhật workflow view
                self._update_workflow_view()
            
            # Update camera button state when tool is added
            self._update_camera_button_state()
    
    def setup_save_image_tool_logic(self):
        """Thiết lập logic cho Save Image Tool từ giao diện saveImagePage"""
        logging.info("Setting up Save Image Tool Logic")

        # Get saveImagePage from settings_manager
        save_image_page = self.settings_manager.save_image_page

        if save_image_page:
            logging.info("Save Image Page found, setting up widget connections")

            # Find widgets in the saveImagePage
            self.directoryPlace = save_image_page.findChild(QLineEdit, 'directoryPlace')
            self.browseButton = save_image_page.findChild(QPushButton, 'browseButton')
            self.formatComboBox = save_image_page.findChild(QComboBox, 'formatComboBox')
            self.structureFile = save_image_page.findChild(QLineEdit, 'structureFile')

            # Log found widgets
            logging.info(f"Found directoryPlace: {self.directoryPlace is not None}")
            logging.info(f"Found browseButton: {self.browseButton is not None}")
            logging.info(f"Found formatComboBox: {self.formatComboBox is not None}")
            logging.info(f"Found structureFile: {self.structureFile is not None}")

            # Connect browse button if found
            if self.browseButton:
                # Disconnect any existing connections to avoid duplicates
                try:
                    self.browseButton.clicked.disconnect()
                except:
                    pass
                self.browseButton.clicked.connect(self.handle_browse_directory)
                logging.info("Connected browse button")

            # Set default values
            if self.formatComboBox:
                self.formatComboBox.setCurrentText("JPG")

            # Clear any previous values
            if self.directoryPlace:
                self.directoryPlace.clear()
            if self.structureFile:
                self.structureFile.clear()

        else:
            logging.error("Save Image Page not found in settings manager")

    def handle_browse_directory(self):
        """Xử lý sự kiện khi người dùng nhấn nút duyệt thư mục trong trang Save Image"""
        from PyQt5.QtWidgets import QFileDialog

        logging.info("Browse directory button clicked for Save Image Tool")

        # Open directory selection dialog
        directory = QFileDialog.getExistingDirectory(
            self,
            'Select Directory to Save Images',
            '',  # Start from current directory
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if directory and self.directoryPlace:
            self.directoryPlace.setText(directory)
            logging.info(f"Selected directory: {directory}")
        else:
            logging.info("No directory selected or directoryPlace widget not found")

    def setup_classification_tool_logic(self):
        """Thiết lập logic cho Classification Tool trên trang classificationSettingPage"""
        logging.info("Setting up Classification Tool Logic")

        # Find widgets on classificationSettingPage
        from PyQt5.QtWidgets import QWidget, QComboBox, QCheckBox
        page = None
        if hasattr(self.settings_manager, 'classification_setting_page'):
            page = self.settings_manager.classification_setting_page
        if not page and hasattr(self, 'settingStackedWidget'):
            page = self.settingStackedWidget.findChild(QWidget, 'classificationSettingPage')

        if not page:
            page = self.findChild(QWidget, 'classificationSettingPage')

        if not page:
            logging.error("Classification Setting Page not found")
            return

        # Resolve widgets
        self.class_modelComboBox = page.findChild(QComboBox, 'modelComboBox')
        self.class_classComboBox = page.findChild(QComboBox, 'classComboBox')
        self.class_resultDisplayCheckBox = page.findChild(QCheckBox, 'resultDisplayCheckBox')

        logging.info(f"Found modelComboBox: {self.class_modelComboBox is not None}")
        logging.info(f"Found classComboBox: {self.class_classComboBox is not None}")
        logging.info(f"Found resultDisplayCheckBox: {self.class_resultDisplayCheckBox is not None}")

        # Note: Model loading is now handled by ClassificationToolManager
        # The ClassificationToolManager will populate modelComboBox and classComboBox
        logging.info("Classification UI setup - models will be loaded by ClassificationToolManager")
        
        # Ensure ClassificationToolManager is properly connected and refreshed
        if hasattr(self, 'classification_tool_manager') and self.classification_tool_manager:
            logging.info("Refreshing ClassificationToolManager after UI setup")
            self.refresh_classification_tool_manager()

    def _apply_save_image_settings(self):
        """Apply SaveImage tool settings and add tool to job"""
        logging.info("Applying SaveImage tool settings")

        try:
            # Collect configuration from UI
            config = {}

            if self.directoryPlace:
                config["directory"] = self.directoryPlace.text().strip()

            if self.structureFile:
                config["structure_file"] = self.structureFile.text().strip()

            if self.formatComboBox:
                config["image_format"] = self.formatComboBox.currentText()

            # Validate required fields
            if not config.get("directory"):
                logging.error("Directory is required for SaveImage tool")
                return

            # Check if we're editing an existing tool or adding a new one
            if self._editing_tool is not None:
                logging.info(f"Updating existing SaveImage tool: {self._editing_tool.display_name}")
                self._editing_tool.update_config(config)
                self._editing_tool = None
            else:
                # Adding new SaveImage tool
                if hasattr(self.tool_manager, '_pending_tool') and self.tool_manager._pending_tool == "Save Image":
                    logging.info("Adding new SaveImage tool")

                    # Set the config in tool manager
                    self.tool_manager.set_tool_config(config)

                    # Apply using tool_manager
                    added_tool = self.tool_manager.on_apply_setting()
                    if added_tool:
                        logging.info(f"SaveImage tool added successfully: {added_tool.display_name}")
                    else:
                        logging.error("Failed to add SaveImage tool")

            # Update job view
            if hasattr(self.tool_manager, '_update_job_view'):
                self.tool_manager._update_job_view()

            # Return to palette page
            self.settings_manager.return_to_palette_page()

            # Update workflow view
            self._update_workflow_view()

        except Exception as e:
            logging.error(f"Error applying SaveImage settings: {e}")

    def _on_edit_tool(self):
        """Xử lý khi người dùng nhấn nút Edit Tool"""
        # Get selected tool from tool view
        selected_tool = self.tool_manager.get_selected_tool()
        if selected_tool:
            self._editing_tool = selected_tool
            self.tool_manager._pending_tool = None
            
            # Auto-stop camera if editing Camera Source
            if selected_tool.display_name == "Camera Source" or selected_tool.name == "Camera Source":
                self._auto_stop_camera_for_edit()
            
            # DO NOT disable camera button during edit - let it depend only on Camera Source presence
            # The camera button state should only depend on whether Camera Source exists in job
            
            # Set current editing tool ID BEFORE any overlay operations
            if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                self.camera_manager.camera_view.current_editing_tool_id = selected_tool.tool_id
                print(f"DEBUG: Set current_editing_tool_id to: {selected_tool.tool_id}")
            
            detection_area = None
            if hasattr(selected_tool, 'config') and hasattr(selected_tool.config, 'get'):
                detection_area = selected_tool.config.get('detection_area')
            self.tool_manager._pending_detection_area = detection_area
            
            if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                overlay = self.camera_manager.camera_view.edit_tool_overlay(selected_tool.tool_id)
                if overlay:
                    print(f"DEBUG: Editing tool #{selected_tool.tool_id}")
                else:
                    print(f"DEBUG: Tool #{selected_tool.tool_id} overlay not found")
            self.settings_manager.switch_to_tool_setting_page(selected_tool.name)
            self._load_tool_config_to_ui(selected_tool)
        else:
            print("DEBUG: No tool selected for editing")
            
    def _auto_stop_camera_for_edit(self):
        """Automatically stop camera when editing Camera Source"""
        if self.onlineCamera and self.onlineCamera.isChecked():
            logging.info("Auto-stopping camera for Camera Source edit")
            self.onlineCamera.setChecked(False)
            self._toggle_camera(False)  # Force stop camera
    
    def _on_remove_tool(self):
        """Xử lý khi người dùng nhấn nút Remove Tool"""
        # Get selected tool from tool view
        selected_tool = self.tool_manager.get_selected_tool()
        if selected_tool:
            # Remove tool overlay from camera view
            if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                self.camera_manager.camera_view.remove_tool_overlay(selected_tool.tool_id)
            
            # Remove tool from job
            self.tool_manager.remove_tool_from_job(selected_tool)
            print(f"DEBUG: Removed tool #{selected_tool.tool_id}")
            
            # Update camera button state when tool is removed
            self._update_camera_button_state()
            
            # Cập nhật workflow view
            self._update_workflow_view()
        else:
            print("DEBUG: No tool selected for removal")
    
    def _on_apply_setting(self):
        """Xử lý khi người dùng nhấn nút Apply trong trang cài đặt"""
        print("DEBUG: _on_apply_setting called in MainWindow")
        # Flush camera pipeline before applying to avoid pending requests
        try:
            if hasattr(self, 'camera_manager') and self.camera_manager and \
               hasattr(self.camera_manager, 'camera_stream') and self.camera_manager.camera_stream and \
               hasattr(self.camera_manager.camera_stream, 'cancel_all_and_flush'):
                self.camera_manager.camera_stream.cancel_all_and_flush()
                print("DEBUG: [MainWindow] cancel_all_and_flush called before apply settings")
        except Exception:
            pass

        # Synchronize settings across all pages before applying
        print("DEBUG: Synchronizing settings across pages...")
        self.settings_manager.sync_settings_across_pages()
        
        # Get current page type to handle page-specific logic
        current_page = self.settings_manager.get_current_page_type()
        print(f"DEBUG: Applying settings for page type: {current_page}")
        
        # Handle camera settings page
        if current_page == "camera":
            self._apply_camera_settings()
            
            # Check if Camera Source tool is pending and add it
            if hasattr(self.tool_manager, '_pending_tool') and self.tool_manager._pending_tool == "Camera Source":
                print("DEBUG: Applying Camera Source tool settings")
                
                # Stop camera before applying to prevent conflicts
                if hasattr(self.camera_manager, 'stop_camera_for_apply'):
                    self.camera_manager.stop_camera_for_apply()
                
                # Call the tool manager to create and add the Camera Source tool
                added_tool = self.tool_manager.on_apply_setting()
                if added_tool:
                    print(f"DEBUG: Camera Source tool added successfully with ID: {added_tool.tool_id}")
                    # Update job view to show the new tool
                    self.tool_manager._update_job_view()
                    # Update camera button state when Camera Source is added
                    self._update_camera_button_state()
                    
                    # Don't automatically start camera - user must choose manually
                    print("DEBUG: Camera Source tool added - user must manually start camera using Live/Trigger buttons")
                else:
                    print("DEBUG: Failed to add Camera Source tool")
            
            # Chuyển về trang palette sau khi áp dụng cài đặt camera
            self.settings_manager.return_to_palette_page()
            return

        # Handle save image settings page
        if current_page == "save_image":
            self._apply_save_image_settings()
            return

        # Handle detection settings page
        if current_page == "detect":
            # Nếu đang ở chế độ chỉnh sửa tool (edit), chỉ cập nhật config tool đó
            if self._editing_tool is not None:
                print(f"DEBUG: Updating config for editing tool: {self._editing_tool.display_name}")
                detection_area = self._collect_detection_area()
                if self._editing_tool.name == "Detect Tool" and hasattr(self, 'detect_tool_manager'):
                    new_config = self.detect_tool_manager.get_tool_config()
                    # Luôn lưu detection_area từ UI nếu có
                    if detection_area:
                        new_config['detection_area'] = detection_area
                    self._editing_tool.config = new_config
                    print(f"DEBUG: Updated DetectTool config: {self._editing_tool.config}")
                else:
                    # For other tools, update config with detection_area if present
                    if hasattr(self._editing_tool, 'config') and detection_area:
                        self._editing_tool.config['detection_area'] = detection_area
                self._editing_tool = None
                if hasattr(self.tool_manager, '_update_job_view'):
                    self.tool_manager._update_job_view()
                
                # Chuyển về trang palette sau khi áp dụng cài đặt
                self.settings_manager.return_to_palette_page()
                
                # --- Always robustly disable edit mode for all overlays and current_overlay ---
                if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                    camera_view = self.camera_manager.camera_view
                    # Tắt edit mode cho tất cả overlays
                    if hasattr(camera_view, 'overlays'):
                        for overlay in camera_view.overlays.values():
                            overlay.set_edit_mode(False)
                            print(f"DEBUG: Overlay #{overlay.tool_id} edit_mode after apply: {overlay.edit_mode}")
                    # Tắt edit mode cho current_overlay nếu còn tồn tại
                    if hasattr(camera_view, 'current_overlay'):
                        if camera_view.current_overlay:
                            camera_view.current_overlay.set_edit_mode(False)
                            print(f"DEBUG: Current overlay edit_mode after apply: {camera_view.current_overlay.edit_mode}")
                        camera_view.current_overlay = None
                    camera_view.set_overlay_edit_mode(False)
                print("DEBUG: All overlays and current_overlay are now not editable after apply.")
                
                # Cập nhật workflow view
                self._update_workflow_view()
                return
        # Handle classification settings page (simple apply -> add tool)
        if current_page == "classification":
            try:
                added_tool = self.tool_manager.on_apply_setting()
                if hasattr(self.tool_manager, '_update_job_view'):
                    self.tool_manager._update_job_view()
                self.settings_manager.return_to_palette_page()
                # Disable overlays edit mode (consistency)
                if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                    camera_view = self.camera_manager.camera_view
                    if hasattr(camera_view, 'overlays'):
                        for overlay in camera_view.overlays.values():
                            overlay.set_edit_mode(False)
                    camera_view.set_overlay_edit_mode(False)
                return
            except Exception as e:
                logging.error(f"Error applying Classification Tool settings: {e}")
            # Nếu không phải chế độ edit, xử lý như cũ (thêm mới tool)
            print(f"DEBUG: Detection page - _pending_tool: {getattr(self.tool_manager, '_pending_tool', 'None')}")
            print(f"DEBUG: Detection page - _editing_tool: {self._editing_tool}")
            
            logging.debug(f"Detection page - tool_manager has _pending_tool: {hasattr(self.tool_manager, '_pending_tool')}")
            if hasattr(self.tool_manager, '_pending_tool'):
                logging.debug(f"_pending_tool value: {getattr(self.tool_manager, '_pending_tool', 'None')}")
            if hasattr(self.tool_manager, '_pending_tool') and self.tool_manager._pending_tool == "Detect Tool":
                print("DEBUG: Processing Detect Tool via detect_tool_manager path")
                logging.info("Applying Detect Tool configuration...")
                # --- Always save detection_area from UI to config before applying ---
                detection_area = self._collect_detection_area()
                config = self.detect_tool_manager.get_tool_config() if hasattr(self, 'detect_tool_manager') else {}
                if detection_area:
                    config['detection_area'] = detection_area
                self.tool_manager.set_tool_config(config)
                success = self.detect_tool_manager.apply_detect_tool_to_job()
                if hasattr(self.tool_manager, '_update_job_view'):
                    self.tool_manager._update_job_view()
                self.settings_manager.return_to_palette_page()  # Changed from return_to_camera_setting_page
                # --- Tắt edit mode cho overlays như cancelSetting ---
                if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                    camera_view = self.camera_manager.camera_view
                    if hasattr(camera_view, 'overlays'):
                        for overlay in camera_view.overlays.values():
                            overlay.set_edit_mode(False)
                    if hasattr(camera_view, 'current_overlay'):
                        camera_view.current_overlay = None
                    camera_view.set_overlay_edit_mode(False)
                    print("DEBUG: Disabled overlay edit mode on apply (after add tool)")
                if success:
                    logging.info("Detect Tool applied to job successfully")
                else:
                    logging.error("Failed to apply Detect Tool to job")
                return
            else:
                print("DEBUG: Detect Tool not in _pending_tool or _pending_tool not set correctly")
                print("DEBUG: Falling back to generic tool creation path")
                logging.debug("Detect Tool not selected or _pending_tool not set correctly")
            
            # Fallback: use generic tool manager path for Detect Tool
            if hasattr(self.tool_manager, '_pending_tool') and self.tool_manager._pending_tool:
                print(f"DEBUG: Using generic tool creation path for: {self.tool_manager._pending_tool}")
                
                # Collect detection area
                detection_area = self._collect_detection_area()
                
                # Get configuration from detect_tool_manager if available
                if self.tool_manager._pending_tool == "Detect Tool" and hasattr(self, 'detect_tool_manager'):
                    config = self.detect_tool_manager.get_tool_config()
                    if detection_area:
                        config['detection_area'] = detection_area
                    self.tool_manager.set_tool_config(config)
                    print(f"DEBUG: Set Detect Tool config: {config}")
                    
                # Apply using tool_manager.on_apply_setting()
                added_tool = self.tool_manager.on_apply_setting()
                if added_tool:
                    print(f"DEBUG: Generic path - Tool added successfully: {added_tool.name} with ID: {added_tool.tool_id}")
                    # Update job view to show the new tool
                    self.tool_manager._update_job_view()
                else:
                    print("DEBUG: Generic path - Failed to add tool")
                
                # Return to palette page
                self.settings_manager.return_to_palette_page()
                
                # Disable overlay edit mode
                if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                    camera_view = self.camera_manager.camera_view
                    if hasattr(camera_view, 'overlays'):
                        for overlay in camera_view.overlays.values():
                            overlay.set_edit_mode(False)
                    if hasattr(camera_view, 'current_overlay'):
                        camera_view.current_overlay = None
                    camera_view.set_overlay_edit_mode(False)
                    print("DEBUG: Disabled overlay edit mode on apply (generic path)")
                
                return
            
            # Đoạn này đã xử lý cập nhật tool ở trên với self._editing_tool, không cần lặp lại với editing_tool
            # Nếu không phải chế độ edit, xử lý như cũ (thêm mới tool)
            # Adding new tool (old path - should not reach here for Detect Tool)
            print("DEBUG: Adding new tool (old path)")
            # Lưu cấu hình vào tool_manager
            if hasattr(self.tool_manager, '_pending_tool') and self.tool_manager._pending_tool:
                # Get UI widgets from appropriate setting page
                ui_widgets = {}
                current_widget = self.settingStackedWidget.currentWidget()
                
                # Collect all relevant UI widgets from the current setting page
                if current_widget:
                    # Find all relevant UI controls
                    all_controls = current_widget.findChildren(QWidget)
                    for control in all_controls:
                        if control.objectName():
                            ui_widgets[control.objectName()] = control
                
                config = self.settings_manager.collect_tool_config(
                    self.tool_manager._pending_tool,
                    ui_widgets
                )
                self.tool_manager.set_tool_config(config)

                # Áp dụng cài đặt detection và get added tool
                added_tool = self.tool_manager.on_apply_setting()
                
                # Debug log để kiểm tra tool đã được thêm chưa
                print(f"DEBUG: Added tool result: {added_tool}")
                if added_tool:
                    print(f"DEBUG: Added tool details - name: {added_tool.name}, display_name: {getattr(added_tool, 'display_name', 'N/A')}, ID: {getattr(added_tool, 'tool_id', 'N/A')}")
                    # Kiểm tra xem tool đã được thêm vào job chưa
                    current_job = self.job_manager.get_current_job()
                    if current_job:
                        print(f"DEBUG: Current job has {len(current_job.tools)} tools")
                        for i, t in enumerate(current_job.tools):
                            print(f"DEBUG: Job tool {i}: {getattr(t, 'name', 'Unknown')}, ID: {getattr(t, 'tool_id', 'N/A')}")
                
                # Update overlay with tool_id if tool was added
                if added_tool and hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                    if self.camera_manager.camera_view.current_overlay:
                        overlay = self.camera_manager.camera_view.current_overlay
                        # Update overlay with tool ID and add to overlays dict
                        old_id = overlay.tool_id
                        overlay.tool_id = added_tool.tool_id
                        overlay.update()  # Trigger repaint to show new ID

                        # Move to overlays dict with new tool_id
                        if old_id in self.camera_manager.camera_view.overlays:
                            del self.camera_manager.camera_view.overlays[old_id]
                        self.camera_manager.camera_view.overlays[added_tool.tool_id] = overlay

                        # Disable edit mode
                        overlay.set_edit_mode(False)
                        self.camera_manager.camera_view.current_overlay = None
                        print(f"DEBUG: Updated overlay with tool ID #{added_tool.tool_id}")

            # Quay lại trang palette (không phải trang camera)
            self.settings_manager.return_to_palette_page()
        
        # Re-enable camera button when leaving edit mode
        self._enable_camera_button_after_edit()
        
        # Clear pending changes after successful apply
        self.settings_manager.clear_pending_changes()
        # --- Tắt edit mode cho overlays như cancelSetting ---
        if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
            camera_view = self.camera_manager.camera_view
            # Tắt edit mode cho tất cả overlays
            if hasattr(camera_view, 'overlays'):
                for overlay in camera_view.overlays.values():
                    overlay.set_edit_mode(False)
            # Đặt current_overlay = None
            if hasattr(camera_view, 'current_overlay'):
                camera_view.current_overlay = None
            camera_view.set_overlay_edit_mode(False)
            print("DEBUG: Disabled overlay edit mode on apply")
        
        # Update camera button state based on Camera Source presence (not just enable)
        self._update_camera_button_state()
        self._editing_tool = None  # Clear editing state
        
        print("DEBUG: Settings applied and synchronized successfully")
    
    def _on_cancel_setting(self):
        """Xử lý khi người dùng nhấn nút Cancel trong trang cài đặt"""
        # Update camera button state based on Camera Source presence (not just enable)
        self._update_camera_button_state()
        self._editing_tool = None  # Clear editing state
        
        # Disable overlay edit mode when canceling
        if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
            camera_view = self.camera_manager.camera_view
            # Tắt edit mode cho tất cả overlays
            if hasattr(camera_view, 'overlays'):
                for overlay in camera_view.overlays.values():
                    overlay.set_edit_mode(False)
            # Đặt current_overlay = None
            if hasattr(camera_view, 'current_overlay'):
                camera_view.current_overlay = None
            camera_view.set_overlay_edit_mode(False)
            print("DEBUG: Disabled overlay edit mode on cancel")
        
        # Hủy bỏ thao tác thêm tool
        self.tool_manager.on_cancel_setting()
        
        # Quay lại trang palette (không phải camera setting)
        self.settings_manager.return_to_palette_page()
        
    def _enable_camera_button_after_edit(self):
        """Update camera button state when leaving edit mode based on Camera Source presence"""
        self._update_camera_button_state()
    
    def _on_edit_job(self):
        """Xử lý khi người dùng nhấn nút Edit Job"""
        print("DEBUG: Edit Job button clicked")
        
        # Get selected tool for editing
        editing_tool = self.tool_manager.on_edit_tool_in_job()
        if not editing_tool:
            print("DEBUG: No tool selected for editing")
            return
        
        print(f"DEBUG: Editing tool: {editing_tool.display_name}")
        
        # Switch to detect settings page
        tool_name = editing_tool.name
        if self.settings_manager.switch_to_tool_setting_page(tool_name):
            # Load tool configuration into UI
            self._load_tool_config_to_ui(editing_tool)
            print(f"DEBUG: Switched to settings page for {tool_name}")
        else:
            print(f"DEBUG: Failed to switch to settings page for {tool_name}")
    
    def _load_tool_config_to_ui(self, tool):
        """Load tool configuration into UI for editing"""
        try:
            # Always reset UI before loading tool config
            self._clear_tool_config_ui()
            # Get config as dict
            if hasattr(tool.config, 'to_dict'):
                config = tool.config.to_dict()
            else:
                config = tool.config
            print(f"DEBUG: Loading tool config: {config}")

            # Handle tool-specific configuration loading
            if tool.name == "Detect Tool" and hasattr(self, 'detect_tool_manager'):
                print(f"DEBUG: Loading DetectTool configuration via DetectToolManager")
                self.detect_tool_manager.load_tool_config(config)

            # --- Load detection area (x1, y1, x2, y2) robustly ---
            area = None
            print(f"DEBUG: Looking for detection area in config...")
            print(f"DEBUG: detection_area in config: {'detection_area' in config}")
            print(f"DEBUG: detection_region in config: {'detection_region' in config}")
            if 'detection_area' in config:
                print(f"DEBUG: detection_area value: {config['detection_area']}")
            if 'detection_region' in config:
                print(f"DEBUG: detection_region value: {config['detection_region']}")
                
            if 'detection_area' in config and config['detection_area'] is not None:
                area = config['detection_area']
                print(f"DEBUG: Using detection_area: {area}")
            elif 'detection_region' in config and config['detection_region'] is not None:
                area = config['detection_region']
                print(f"DEBUG: Using detection_region: {area}")

            # If area is still None, try to get from overlay (if exists)
            if (not area or not (isinstance(area, (list, tuple)) and len(area) == 4)) and hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                print(f"DEBUG: Trying to get area from existing overlay...")
                camera_view = self.camera_manager.camera_view
                if hasattr(camera_view, 'overlays'):
                    print(f"DEBUG: Available overlays: {list(camera_view.overlays.keys())}")
                    overlay = camera_view.overlays.get(tool.tool_id)
                    if overlay and hasattr(overlay, 'get_area_coords'):
                        area = overlay.get_area_coords()
                        # Update config so next time it is available
                        tool.config['detection_area'] = area
                        print(f"DEBUG: Loaded detection_area from overlay: {area}")
                    else:
                        print(f"DEBUG: No overlay found for tool #{tool.tool_id}")
                else:
                    print(f"DEBUG: No overlays attribute in camera_view")

            if area and isinstance(area, (list, tuple)) and len(area) == 4:
                x1, y1, x2, y2 = area
                if self.x1PositionLineEdit:
                    self.x1PositionLineEdit.setText(str(x1))
                if self.y1PositionLineEdit:
                    self.y1PositionLineEdit.setText(str(y1))
                if self.x2PositionLineEdit:
                    self.x2PositionLineEdit.setText(str(x2))
                if self.y2PositionLineEdit:
                    self.y2PositionLineEdit.setText(str(y2))
                # Add or update detection area overlay for editing (preserve other overlays)
                if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                    camera_view = self.camera_manager.camera_view
                    
                    # Set current editing tool ID
                    camera_view.current_editing_tool_id = tool.tool_id
                    print(f"DEBUG: Set current editing tool ID to: {tool.tool_id}")
                    
                    if tool.tool_id in camera_view.overlays:
                        overlay = camera_view.overlays[tool.tool_id]
                        overlay.update_from_coords(x1, y1, x2, y2)
                        overlay.set_edit_mode(True)
                        camera_view.current_overlay = overlay
                        print(f"DEBUG: Updated existing overlay for tool #{tool.tool_id}")
                    else:
                        overlay = camera_view.add_tool_overlay(x1, y1, x2, y2, tool.tool_id)
                        overlay.set_edit_mode(True)
                        camera_view.current_overlay = overlay
                        print(f"DEBUG: Added new overlay for tool #{tool.tool_id}")
                    print(f"DEBUG: Loaded detection area for editing: ({x1}, {y1}) to ({x2}, {y2})")
                    print("DEBUG: Enabled overlay edit mode for tool editing")
            else:
                # If no area, clear all fields
                if self.x1PositionLineEdit:
                    self.x1PositionLineEdit.setText("")
                if self.y1PositionLineEdit:
                    self.y1PositionLineEdit.setText("")
                if self.x2PositionLineEdit:
                    self.x2PositionLineEdit.setText("")
                if self.y2PositionLineEdit:
                    self.y2PositionLineEdit.setText("")

            # Load other settings (threshold, confidence, etc.)
            if 'threshold' in config and hasattr(self, 'thresholdSlider'):
                self.thresholdSlider.setValue(config['threshold'])

            if 'min_confidence' in config and hasattr(self, 'minConfidenceEdit'):
                self.minConfidenceEdit.setValue(config['min_confidence'])

        except Exception as e:
            print(f"DEBUG: Error loading tool config: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_draw_area_clicked(self):
        """Xử lý khi người dùng nhấn nút Draw Area"""
        print("DEBUG: Draw Area button clicked")
        
        # Chỉ xóa overlay tạm thời (pending), giữ lại overlay của các tool đã add vào job
        if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
            # Nếu đang có overlay tạm thời (current_overlay) thì xóa, không xóa overlays của tool đã add
            if self.camera_manager.camera_view.current_overlay:
                overlay = self.camera_manager.camera_view.current_overlay
                if overlay.tool_id is None or overlay.tool_id not in self.camera_manager.camera_view.overlays:
                    # Chỉ xóa overlay tạm thời chưa gán tool_id
                    self.camera_manager.camera_view.scene.removeItem(overlay)
                    self.camera_manager.camera_view.current_overlay = None
            # Enable drawing mode in camera view
            self.camera_manager.camera_view.set_draw_mode(True)
            # Connect area drawing signals
            if hasattr(self.camera_manager.camera_view, 'area_drawn'):
                self.camera_manager.camera_view.area_drawn.connect(self._on_area_drawn)
            # Update button state
            if self.drawAreaButton:
                self.drawAreaButton.setText("Drawing...")
                self.drawAreaButton.setEnabled(False)
            print("DEBUG: Enabled drawing mode in camera view")
        else:
            print("DEBUG: Camera view not available")
    
    def _on_area_drawn(self, x1, y1, x2, y2):
        """Xử lý khi user đã vẽ xong area"""
        print(f"DEBUG: Area drawn: ({x1}, {y1}) to ({x2}, {y2})")

        # Update x1, y1, x2, y2 LineEdits with drawn area coordinates
        if self.x1PositionLineEdit:
            self.x1PositionLineEdit.setText(str(int(x1)))
        if self.y1PositionLineEdit:
            self.y1PositionLineEdit.setText(str(int(y1)))
        if self.x2PositionLineEdit:
            self.x2PositionLineEdit.setText(str(int(x2)))
        if self.y2PositionLineEdit:
            self.y2PositionLineEdit.setText(str(int(y2)))

        # Reset button state
        if self.drawAreaButton:
            self.drawAreaButton.setText("Draw area")
            self.drawAreaButton.setEnabled(True)

        # Disable drawing mode but keep overlay editable in pending state
        if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
            self.camera_manager.camera_view.set_draw_mode(False)
            # Keep overlay editable until applied/canceled
            self.camera_manager.camera_view.set_overlay_edit_mode(True)

        print(f"DEBUG: Updated detection area fields: x1={int(x1)}, y1={int(y1)}, x2={int(x2)}, y2={int(y2)}")
    
    def _on_area_changed(self, x1, y1, x2, y2):
        """Xử lý khi area thay đổi (move/resize)"""
        print(f"DEBUG: Area changed: ({x1}, {y1}) to ({x2}, {y2})")

        # Update x1, y1, x2, y2 LineEdits with changed area coordinates
        if self.x1PositionLineEdit:
            self.x1PositionLineEdit.setText(str(int(x1)))
        if self.y1PositionLineEdit:
            self.y1PositionLineEdit.setText(str(int(y1)))
        if self.x2PositionLineEdit:
            self.x2PositionLineEdit.setText(str(int(x2)))
        if self.y2PositionLineEdit:
            self.y2PositionLineEdit.setText(str(int(y2)))

        print(f"DEBUG: Updated detection area fields from area change: x1={int(x1)}, y1={int(y1)}, x2={int(x2)}, y2={int(y2)}")
    
    def _collect_detection_area(self):
        """Collect detection area coordinates from UI or current drawn area"""
        print("DEBUG: _collect_detection_area called")
        
        # First try to get from current drawn area
        if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
            camera_view = self.camera_manager.camera_view
            print(f"DEBUG: Camera view available, current_overlay: {camera_view.current_overlay}")
            print(f"DEBUG: Camera view overlays count: {len(camera_view.overlays) if hasattr(camera_view, 'overlays') else 0}")
            if hasattr(camera_view, 'overlays'):
                for tool_id, overlay in camera_view.overlays.items():
                    coords = overlay.get_area_coords() if overlay else None
                    print(f"DEBUG: Overlay {tool_id} coords: {coords}")
            
            current_coords = camera_view.get_current_area_coords()
            if current_coords:
                print(f"DEBUG: Got coordinates from drawn area: {current_coords}")
                return current_coords
            else:
                print("DEBUG: No current overlay coordinates available")
        
        # Fallback to text input
        print("DEBUG: Trying text input fallback")
        try:
            if self.x1PositionLineEdit and self.y1PositionLineEdit and self.x2PositionLineEdit and self.y2PositionLineEdit:
                x1_text = self.x1PositionLineEdit.text().strip()
                y1_text = self.y1PositionLineEdit.text().strip()
                x2_text = self.x2PositionLineEdit.text().strip()
                y2_text = self.y2PositionLineEdit.text().strip()
                if x1_text and y1_text and x2_text and y2_text:
                    x1 = int(x1_text)
                    y1 = int(y1_text)
                    x2 = int(x2_text)
                    y2 = int(y2_text)
                    return (x1, y1, x2, y2)
        except ValueError as e:
            print(f"DEBUG: Error parsing coordinates: {e}")
        return None
    
    def save_current_job(self):
        self._disable_all_overlay_edit_mode()
        """Lưu job hiện tại vào file"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Save Job", 
                "job.json", 
                "JSON files (*.json)"
            )
            
            if file_path:
                if self.job_manager.save_current_job(file_path):
                    logging.info(f"Job saved successfully to {file_path}")
                else:
                    logging.error("Failed to save job")
                    
        except Exception as e:
            logging.error(f"Error saving job: {str(e)}")
            
    def load_job_file(self):
        self._disable_all_overlay_edit_mode()
        """Tải job từ file"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "Load Job", 
                "", 
                "JSON files (*.json)"
            )
            
            if file_path:
                job = self.job_manager.load_job(file_path)
                if job:
                    # Cập nhật UI
                    self.tool_manager._update_job_view()
                    # Update camera button state when job is loaded
                    self._update_camera_button_state()
                    # Cập nhật workflow view
                    self._update_workflow_view()
                    logging.info(f"Job loaded successfully from {file_path}")
                else:
                    logging.error("Failed to load job")
                    
        except Exception as e:
            logging.error(f"Error loading job: {str(e)}")
            
    def add_new_job(self):
        self._disable_all_overlay_edit_mode()
        """Tạo job mới"""
        try:
            from PyQt5.QtWidgets import QInputDialog
            
            job_name, ok = QInputDialog.getText(
                self, 
                "New Job", 
                "Enter job name:",
                text="New Job"
            )
            
            if ok and job_name:
                new_job = self.job_manager.create_default_job(job_name)
                self.tool_manager._update_job_view()
                # Update camera button state when new job is created
                self._update_camera_button_state()
                # Cập nhật workflow view
                self._update_workflow_view()
                logging.info(f"New job '{job_name}' created")
                
        except Exception as e:
            logging.error(f"Error creating new job: {str(e)}")
            
    def remove_current_job(self):
        self._disable_all_overlay_edit_mode()
        """Xóa job hiện tại"""
        try:
            from PyQt5.QtWidgets import QMessageBox
            
            current_job = self.job_manager.get_current_job()
            if not current_job:
                logging.warning("No current job to remove")
                return
                
            reply = QMessageBox.question(
                self, 
                "Remove Job", 
                f"Are you sure you want to remove job '{current_job.name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                current_index = self.job_manager.current_job_index
                if self.job_manager.remove_job(current_index):
                    self.tool_manager._update_job_view()
                    # Cập nhật workflow view
                    self._update_workflow_view()
                    logging.info(f"Job '{current_job.name}' removed")
                else:
                    logging.error("Failed to remove job")
                    
        except Exception as e:
            logging.error(f"Error removing job: {str(e)}")
        
    def run_current_job(self):
        """Chạy job hiện tại"""
        try:
            current_job = self.job_manager.get_current_job()
            if not current_job:
                logging.warning("No current job to run")
                return
                
            if not current_job.tools:
                logging.warning("Current job has no tools")
                return
                
            # Import numpy for creating test images if needed
            import numpy as np
                
            # Lấy frame hiện tại từ camera
            if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                frame = None
                # Check if the job has a CameraTool as the first tool
                first_tool = current_job.tools[0] if current_job.tools else None
                if first_tool and first_tool.name == "Camera Source":
                    logging.info("Using Camera Source tool to get frame")
                    # We'll let the job processing handle the camera source tool
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)  # Placeholder - will be replaced by CameraTool
                else:
                    # Get current frame from camera_view if no CameraTool is present
                    if hasattr(self.camera_manager.camera_view, 'get_current_frame'):
                        frame = self.camera_manager.camera_view.get_current_frame()
                    
                    # Fallback to test image if no frame is available
                    if frame is None:
                        logging.warning("No frame available, using test image")
                        frame = np.zeros((480, 640, 3), dtype=np.uint8)
                
                # Chạy job with force_save enabled
                initial_context = {"force_save": True}
                processed_image, results = current_job.run(frame, initial_context)
                
                # Hiển thị kết quả
                if 'error' not in results:
                    logging.info(f"Job '{current_job.name}' completed successfully")
                    logging.info(f"Execution time: {results.get('execution_time', 0):.2f}s")
                    
                    # Cập nhật execution time display
                    if self.executionTime:
                        self.executionTime.display(results.get('execution_time', 0))
                else:
                    logging.error(f"Job failed: {results['error']}")
                    
        except Exception as e:
            logging.error(f"Error running job: {str(e)}")
        
    def _apply_camera_settings(self):
        """Apply camera settings including format"""
        print("DEBUG: Applying camera settings...")
        
        # Apply camera format if formatCameraComboBox exists and has selection
        if self.formatCameraComboBox and self.formatCameraComboBox.currentText():
            selected_format = self.formatCameraComboBox.currentText()
            print(f"DEBUG: Applying camera format: {selected_format}")
            
            # Get camera stream instance
            if hasattr(self.camera_manager, 'camera_stream') and self.camera_manager.camera_stream:
                camera_stream = self.camera_manager.camera_stream
                # Ensure camera is not running to avoid restart pulses during apply
                try:
                    if hasattr(camera_stream, 'is_running') and camera_stream.is_running():
                        if hasattr(camera_stream, 'cancel_and_stop_live'):
                            camera_stream.cancel_and_stop_live()
                        else:
                            if hasattr(camera_stream, 'cancel_all_and_flush'):
                                camera_stream.cancel_all_and_flush()
                            if hasattr(camera_stream, 'stop_live'):
                                camera_stream.stop_live()
                except Exception as e:
                    print(f"DEBUG: Error pre-stopping camera before format apply: {e}")
                
                # Xác thực định dạng trước khi áp dụng
                safe_formats = ["RGB888", "BGR888", "XRGB8888"]
                if selected_format not in safe_formats:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(
                        self, 
                        "Định dạng không được hỗ trợ",
                        f"Định dạng {selected_format} có thể không được hỗ trợ trên thiết bị này.\n"
                        f"S? d?ng RGB888."
                    )
                    selected_format = "RGB888"
                    # Cập nhật lại combo box để hiển thị định dạng thực tế
                    index = self.formatCameraComboBox.findText(selected_format)
                    if index >= 0:
                        self.formatCameraComboBox.setCurrentIndex(index)
                
                # Apply the new format
                try:
                    camera_stream.set_format(selected_format)
                    print(f"DEBUG: Successfully applied camera format: {selected_format}")
                except Exception as e:
                    print(f"DEBUG: Failed to apply camera format {selected_format}: {e}")
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.critical(
                        self, 
                        "Lỗi định dạng camera",
                        f"Không thể áp dụng định dạng {selected_format}.\n"
                        f"Lỗi: {str(e)}"
                    )
            else:
                print("DEBUG: Camera stream not available for format change")
        
        # Update camera button state after applying camera settings
        self._update_camera_button_state()
        
        print("DEBUG: Camera settings applied successfully")
    
    def _load_camera_formats(self):
        """Load available camera formats into formatCameraComboBox"""
        print("DEBUG: _load_camera_formats called")
        
        # Always try to find formatCameraComboBox fresh
        combo_widget = None
        
        # First try findChild
        combo_widget = self.findChild(QComboBox, 'formatCameraComboBox')
        if combo_widget:
            print(f"DEBUG: Found formatCameraComboBox via findChild: {combo_widget}")
        else:
            print("DEBUG: findChild failed, trying findChildren...")
            # Alternative method: search through all combo boxes
            all_combos = self.findChildren(QComboBox)
            for combo in all_combos:
                if combo.objectName() == 'formatCameraComboBox':
                    combo_widget = combo
                    print(f"DEBUG: Found formatCameraComboBox via findChildren: {combo_widget}")
                    print(f"DEBUG: Widget valid: {combo_widget is not None}")
                    print(f"DEBUG: Widget type: {type(combo_widget)}")
                    print(f"DEBUG: Widget objectName: {combo_widget.objectName()}")
                    break
        
        print(f"DEBUG: Final combo_widget value: {combo_widget}")
        print(f"DEBUG: combo_widget is None: {combo_widget is None}")
        
        if combo_widget is None:
            print("DEBUG: formatCameraComboBox not found anywhere")
            return
            
        # Assign to self for future use
        self.formatCameraComboBox = combo_widget
        print("DEBUG: formatCameraComboBox assigned, proceeding with format loading")
        
        # Clear existing items
        combo_widget.clear()
        
        # Get camera stream instance
        if hasattr(self.camera_manager, 'camera_stream') and self.camera_manager.camera_stream:
            camera_stream = self.camera_manager.camera_stream
            print("DEBUG: Got camera stream instance")
            # Always show supported formats in the combo box (BGR888 first as PyQt expects BGR data)
            supported = ["BGR888", "RGB888", "XRGB8888"]
            for fmt in supported:
                combo_widget.addItem(fmt)
                print(f"DEBUG: Added supported format: {fmt}")
                    
            # Set default/current selection to BGR888 (PyQt Format_RGB888 expects BGR data)
            preferred_format = 'BGR888'
            idx = combo_widget.findText(preferred_format)
            if idx >= 0:
                combo_widget.setCurrentIndex(idx)
                print(f"DEBUG: Set current format to: {preferred_format}")
            else:
                # Fallback to first available format if BGR888 not found
                if combo_widget.count() > 0:
                    combo_widget.setCurrentIndex(0)
                    print(f"DEBUG: BGR888 not found, using first format: {combo_widget.itemText(0)}")
            
            print(f"DEBUG: ComboBox now has {combo_widget.count()} items")
        else:
            print("DEBUG: Camera stream not available, adding fallback formats")
            # Add fallback formats when camera not available (BGR888 first as default)
            safe_formats = ["BGR888", "RGB888", "XRGB8888"]
            for fmt in safe_formats:
                combo_widget.addItem(fmt)
                print(f"DEBUG: Added fallback format: {fmt}")
            print(f"DEBUG: ComboBox now has {combo_widget.count()} fallback items")
    
    def reload_camera_formats(self):
        """Public method to reload camera formats - can be called by camera_manager"""
        self._load_camera_formats()
    
    def resizeEvent(self, a0):
        """Xử lý sự kiện khi cửa sổ thay đổi kích thước"""
        super().resizeEvent(a0)
        if hasattr(self, 'camera_manager') and self.camera_manager:
            self.camera_manager.handle_resize_event()
    
    def closeEvent(self, event):
        """Xử lý sự kiện đóng cửa sổ - dọn dẹp tài nguyên"""
        logger = logging.getLogger(__name__)
        try:
            logger.info("Main window closing - cleaning up resources...")
            
            # Dọn dẹp camera manager
            if hasattr(self, 'camera_manager') and self.camera_manager:
                self.camera_manager.cleanup()
                
            # Chấp nhận sự kiện đóng cửa sổ
            event.accept()
            logger.info("Main window cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during window close cleanup: {str(e)}")
            # Vẫn chấp nhận sự kiện để thoát ứng dụng
            event.accept()





    def _on_format_changed(self, text):
        """Apply camera pixel format immediately when user selects a new one."""
        try:
            # Only support RGB variants now (removed YUV420/NV12 as they cause issues)
            supported = ["BGR888", "RGB888", "XRGB8888"]
            fmt = str(text)
            
            print(f"DEBUG: [MainWindow] Format changed to: {fmt}")
            
            if fmt not in supported:
                print(f"DEBUG: [MainWindow] Ignoring unsupported format selection: {fmt}")
                return
            
            # Use QTimer to defer processing and avoid blocking UI
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._process_format_change(fmt))
                
        except Exception as e:
            print(f"DEBUG: [MainWindow] _on_format_changed error: {e}")
    
    def _process_format_change(self, fmt):
        """Process format change in a non-blocking way"""
        try:
            if not hasattr(self, 'camera_manager') or not self.camera_manager:
                print(f"DEBUG: [MainWindow] No camera_manager available")
                return
            
            if not hasattr(self.camera_manager, 'camera_stream') or not self.camera_manager.camera_stream:
                print(f"DEBUG: [MainWindow] No camera_stream available")
                return
                
            cs = self.camera_manager.camera_stream
            
            # Get current format for comparison
            old_format = cs.get_pixel_format() if hasattr(cs, 'get_pixel_format') else 'Unknown'
            print(f"DEBUG: [MainWindow] Processing format change from {old_format} to {fmt}")
            
            if old_format == fmt:
                print(f"DEBUG: [MainWindow] Format already set to {fmt}, just refreshing display")
                # Still refresh display in case UI is out of sync
                if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                    cv = self.camera_manager.camera_view
                    if hasattr(cv, 'refresh_display_with_new_format'):
                        cv.refresh_display_with_new_format()
                return
            
            # Update format (should be fast)
            try:
                ok = cs.set_format(fmt)
                print(f"DEBUG: [MainWindow] set_format({fmt}) returned {ok}")
            except Exception as e:
                print(f"DEBUG: [MainWindow] Error setting format: {e}")
                return
            
            # For stub backend, generate test frame
            if not getattr(cs, 'is_camera_available', False) and hasattr(cs, '_generate_test_frame'):
                print(f"DEBUG: [MainWindow] Generating new test frame with format {fmt}")
                cs._generate_test_frame()
            
            # Simple re-render attempt
            if hasattr(self.camera_manager, 'camera_view') and self.camera_manager.camera_view:
                cv = self.camera_manager.camera_view
                if hasattr(cv, 'refresh_display_with_new_format'):
                    success = cv.refresh_display_with_new_format()
                    print(f"DEBUG: [MainWindow] Refresh display result: {success}")
            
            # Update CameraTool config
            try:
                ct = self.camera_manager.find_camera_tool() if hasattr(self.camera_manager, 'find_camera_tool') else None
                if ct and hasattr(ct, 'update_config'):
                    ct.update_config({'format': fmt})
                    print(f"DEBUG: [MainWindow] Updated CameraTool config with format {fmt}")
            except Exception as e:
                print(f"DEBUG: [MainWindow] Could not update CameraTool config: {e}")
                
        except Exception as e:
            print(f"DEBUG: [MainWindow] Error in _process_format_change: {e}")

    def showEvent(self, event):
        """Override showEvent để đảm bảo ClassificationToolManager được setup đúng"""
        super().showEvent(event)
        
        # Đảm bảo ClassificationToolManager được refresh sau khi window hiển thị
        try:
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self._delayed_classification_setup)
        except Exception as e:
            logging.error(f"Error in showEvent: {e}")
    
    def _delayed_classification_setup(self):
        """Setup ClassificationToolManager sau khi UI hoàn toàn sẵn sàng"""
        try:
            logging.info("Performing delayed ClassificationToolManager setup...")
            if hasattr(self, 'classification_tool_manager'):
                self.refresh_classification_tool_manager()
                logging.info("Delayed ClassificationToolManager setup completed")
        except Exception as e:
            logging.error(f"Error in delayed classification setup: {e}")


