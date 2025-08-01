from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QStackedWidget, QWidget, QPushButton, QSlider, QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox, QCheckBox
import logging
from typing import Dict, Any, Optional

class SettingsManager(QObject):
    """
    Quản lý giao diện cài đặt và xử lý chuyển đổi giữa các trang cài đặt
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent  # Store reference to main window
        self.setting_stacked_widget = None
        self.camera_setting_page = None
        self.detect_setting_page = None
        self.apply_setting_button = None
        self.cancel_setting_button = None
        
        # Settings synchronization storage
        self.shared_settings = {
            'camera': {},      # Settings shared across all pages
            'detection': {},   # Detection-specific settings
            'global': {}       # Global application settings
        }
        
        # Track which page has pending changes
        self.pending_changes = {
            'camera': False,
            'detection': False
        }
        
        # Mapping tool types to setting pages
        self.tool_to_page_mapping = {
            "EdgeDetectionTool": "detect",
            "OcrTool": "detect", 
            "Detect Tool": "detect",
            "OCR": "detect"
        }
        
    def setup(self, stacked_widget, camera_page, detect_page, apply_button, cancel_button):
        """Thiết lập các tham chiếu đến các widget UI"""
        self.setting_stacked_widget = stacked_widget
        self.camera_setting_page = camera_page
        self.detect_setting_page = detect_page
        self.apply_setting_button = apply_button
        self.cancel_setting_button = cancel_button
        
        # Log thông tin về các widget đã tìm thấy
        logging.info(f"SettingsManager: settingStackedWidget found: {self.setting_stacked_widget is not None}")
        logging.info(f"SettingsManager: cameraSettingPage found: {self.camera_setting_page is not None}")
        logging.info(f"SettingsManager: detectSettingPage found: {self.detect_setting_page is not None}")
        logging.info(f"SettingsManager: applySetting button found: {self.apply_setting_button is not None}")
        logging.info(f"SettingsManager: cancleSetting button found: {self.cancel_setting_button is not None}")
        
        # Log current state of settingStackedWidget
        if self.setting_stacked_widget:
            current_index = self.setting_stacked_widget.currentIndex()
            count = self.setting_stacked_widget.count()
            logging.info(f"SettingsManager: settingStackedWidget state: index={current_index}, count={count}")
            
            # Log pages in the stacked widget
            for i in range(count):
                widget = self.setting_stacked_widget.widget(i)
                widget_name = widget.objectName() if widget else "None"
                logging.info(f"SettingsManager: Page {i}: {widget_name}")
                
    def switch_to_tool_setting_page(self, tool_name):
        """Chuyển đến trang cài đặt tương ứng với tool được chọn"""
        logging.info(f"SettingsManager: switch_to_tool_setting_page called with tool: {tool_name}")
        
        if not tool_name:
            logging.error("SettingsManager: tool_name is empty")
            return False
            
        if not self.setting_stacked_widget:
            logging.error("SettingsManager: settingStackedWidget not found")
            return False
            
        # Log current state of the stacked widget
        current_index = self.setting_stacked_widget.currentIndex()
        count = self.setting_stacked_widget.count()
        logging.info(f"SettingsManager: Current settingStackedWidget state: index={current_index}, count={count}")
            
        # Xác định trang cài đặt dựa trên tool mapping
        page_type = self.tool_to_page_mapping.get(tool_name)
        target_page = None
        
        if page_type == "detect" and self.detect_setting_page:
            target_page = self.detect_setting_page
            logging.info("SettingsManager: Target page is detectSettingPage")
        else:
            # Fallback to detect page for unknown tools
            if self.detect_setting_page:
                target_page = self.detect_setting_page
                logging.info(f"SettingsManager: Using detectSettingPage as fallback for {tool_name}")
            else:
                logging.error(f"SettingsManager: No setting page available for tool: {tool_name}")
                return False
            
        # Chuyển đến trang cài đặt nếu tìm thấy
        if target_page:
            index = self.setting_stacked_widget.indexOf(target_page)
            logging.info(f"SettingsManager: Found target page at index: {index}")
            if index != -1:
                logging.info(f"SettingsManager: Switching to {tool_name} setting page with index {index}.")
                self.setting_stacked_widget.setCurrentIndex(index)
                
                # Refresh DetectToolManager if switching to detect page
                if page_type == "detect" or tool_name == "Detect Tool":
                    if hasattr(self.main_window, 'refresh_detect_tool_manager'):
                        self.main_window.refresh_detect_tool_manager()
                
                # Verify the switch
                new_index = self.setting_stacked_widget.currentIndex()
                logging.info(f"SettingsManager: After switch, current index is: {new_index}")
                return True
            else:
                logging.error(f"SettingsManager: Setting page for {tool_name} not found in settingStackedWidget.")
        
        return False
        
    def return_to_camera_setting_page(self):
        """Quay lại trang cài đặt camera"""
        if not self.setting_stacked_widget or not self.camera_setting_page:
            logging.error("SettingsManager: settingStackedWidget or cameraSettingPage not available.")
            return False
            
        index = self.setting_stacked_widget.indexOf(self.camera_setting_page)
        if index != -1:
            logging.info(f"SettingsManager: Returning to camera setting page with index {index}.")
            self.setting_stacked_widget.setCurrentIndex(index)
            return True
        else:
            logging.error("SettingsManager: Camera setting page not found in settingStackedWidget.")
            return False
            
    def collect_tool_config(self, tool_name: str, ui_widgets: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Thu thập cấu hình từ UI widgets cho tool
        
        Args:
            tool_name: Tên tool
            ui_widgets: Dictionary chứa các UI widgets
            
        Returns:
            Dictionary chứa cấu hình tool hoặc None nếu có lỗi
        """
        try:
            config = {}
            
            # Edge Detection Tool settings
            if tool_name in ["EdgeDetectionTool", "Detect Tool"]:
                config = self._collect_edge_detection_config(ui_widgets)
            # OCR Tool settings  
            elif tool_name in ["OcrTool", "OCR"]:
                config = self._collect_ocr_config(ui_widgets)
            else:
                logging.warning(f"SettingsManager: Unknown tool type for config collection: {tool_name}")
                
            logging.info(f"SettingsManager: Collected config for {tool_name}: {config}")
            return config
            
        except Exception as e:
            logging.error(f"SettingsManager: Error collecting config for {tool_name}: {str(e)}")
            return None
            
    def _collect_edge_detection_config(self, ui_widgets: Dict[str, Any]) -> Dict[str, Any]:
        """Thu thập cấu hình cho EdgeDetectionTool"""
        config = {}
        
        # Threshold settings
        if 'threshold_slider' in ui_widgets and ui_widgets['threshold_slider']:
            threshold_widget = ui_widgets['threshold_slider']
            if isinstance(threshold_widget, QSlider):
                config['low_threshold'] = threshold_widget.value()
                # High threshold thường gấp 2-3 lần low threshold
                config['high_threshold'] = threshold_widget.value() * 2
            elif isinstance(threshold_widget, QSpinBox):
                config['low_threshold'] = threshold_widget.value()
                config['high_threshold'] = threshold_widget.value() * 2
                
        # Additional settings nếu có UI widgets
        if 'aperture_size_combo' in ui_widgets and ui_widgets['aperture_size_combo']:
            combo = ui_widgets['aperture_size_combo']
            if isinstance(combo, QComboBox):
                config['aperture_size'] = int(combo.currentText())
                
        if 'blur_enable_check' in ui_widgets and ui_widgets['blur_enable_check']:
            check = ui_widgets['blur_enable_check']
            if isinstance(check, QCheckBox):
                config['enable_blur'] = check.isChecked()
                
        if 'blur_kernel_spinner' in ui_widgets and ui_widgets['blur_kernel_spinner']:
            spinner = ui_widgets['blur_kernel_spinner']
            if isinstance(spinner, QSpinBox):
                kernel_size = spinner.value()
                # Đảm bảo kernel size là số lẻ
                if kernel_size % 2 == 0:
                    kernel_size += 1
                config['blur_kernel_size'] = kernel_size
                
        # Set default values nếu không có UI
        if 'low_threshold' not in config:
            config['low_threshold'] = 50
        if 'high_threshold' not in config:
            config['high_threshold'] = 150
        if 'aperture_size' not in config:
            config['aperture_size'] = 3
        if 'enable_blur' not in config:
            config['enable_blur'] = True
        if 'blur_kernel_size' not in config:
            config['blur_kernel_size'] = 5
            
        return config
        
    def _collect_ocr_config(self, ui_widgets: Dict[str, Any]) -> Dict[str, Any]:
        """Thu thập cấu hình cho OcrTool"""
        config = {}
        
        # Confidence threshold
        if 'min_confidence_edit' in ui_widgets and ui_widgets['min_confidence_edit']:
            confidence_widget = ui_widgets['min_confidence_edit']
            if isinstance(confidence_widget, QDoubleSpinBox):
                config['min_confidence'] = confidence_widget.value()
            elif isinstance(confidence_widget, QLineEdit):
                try:
                    config['min_confidence'] = float(confidence_widget.text())
                except ValueError:
                    config['min_confidence'] = 0.5
                    
        # Language settings
        if 'language_combo' in ui_widgets and ui_widgets['language_combo']:
            combo = ui_widgets['language_combo']
            if isinstance(combo, QComboBox):
                config['language'] = combo.currentText()
                
        # Output format
        if 'output_format_combo' in ui_widgets and ui_widgets['output_format_combo']:
            combo = ui_widgets['output_format_combo']
            if isinstance(combo, QComboBox):
                config['output_format'] = combo.currentText()
                
        # Preprocessing
        if 'preprocessing_check' in ui_widgets and ui_widgets['preprocessing_check']:
            check = ui_widgets['preprocessing_check']
            if isinstance(check, QCheckBox):
                config['preprocessing'] = check.isChecked()
                
        # Scale factor
        if 'scale_factor_spinner' in ui_widgets and ui_widgets['scale_factor_spinner']:
            spinner = ui_widgets['scale_factor_spinner']
            if isinstance(spinner, QDoubleSpinBox):
                config['scale_factor'] = spinner.value()
                
        # Set default values nếu không có UI
        if 'min_confidence' not in config:
            config['min_confidence'] = 0.5
        if 'language' not in config:
            config['language'] = 'en'
        if 'output_format' not in config:
            config['output_format'] = 'both'
        if 'preprocessing' not in config:
            config['preprocessing'] = True
        if 'scale_factor' not in config:
            config['scale_factor'] = 2.0
            
        return config
        
    def populate_tool_settings(self, tool_name: str, config: Dict[str, Any], ui_widgets: Dict[str, Any]):
        """
        Điền cấu hình tool vào UI widgets
        
        Args:
            tool_name: Tên tool
            config: Cấu hình tool
            ui_widgets: Dictionary chứa các UI widgets
        """
        try:
            if tool_name in ["EdgeDetectionTool", "Detect Tool"]:
                self._populate_edge_detection_settings(config, ui_widgets)
            elif tool_name in ["OcrTool", "OCR"]:
                self._populate_ocr_settings(config, ui_widgets)
                
            logging.info(f"SettingsManager: Populated settings for {tool_name}")
            
        except Exception as e:
            logging.error(f"SettingsManager: Error populating settings for {tool_name}: {str(e)}")
            
    def _populate_edge_detection_settings(self, config: Dict[str, Any], ui_widgets: Dict[str, Any]):
        """Điền cấu hình EdgeDetectionTool vào UI"""
        if 'threshold_slider' in ui_widgets and ui_widgets['threshold_slider']:
            widget = ui_widgets['threshold_slider']
            if isinstance(widget, QSlider):
                widget.setValue(config.get('low_threshold', 50))
            elif isinstance(widget, QSpinBox):
                widget.setValue(config.get('low_threshold', 50))
                
        # Populate other widgets similarly...
        
    def _populate_ocr_settings(self, config: Dict[str, Any], ui_widgets: Dict[str, Any]):
        """Điền cấu hình OcrTool vào UI"""
        if 'min_confidence_edit' in ui_widgets and ui_widgets['min_confidence_edit']:
            widget = ui_widgets['min_confidence_edit']
            if isinstance(widget, QDoubleSpinBox):
                widget.setValue(config.get('min_confidence', 0.5))
            elif isinstance(widget, QLineEdit):
                widget.setText(str(config.get('min_confidence', 0.5)))
                
        # Populate other widgets similarly...
        else:
            logging.error("SettingsManager: cameraSettingPage not found in settingStackedWidget.")
            return False
            
    def collect_tool_config(self, tool_name, ui_widgets):
        """Thu thập cấu hình từ UI tương ứng với từng loại tool"""
        config = {}
        
        # Thu thập cấu hình dựa trên loại tool
        if tool_name == "Detect Tool":
            # Ví dụ: Thu thập cấu hình từ UI cho Detect Tool
            threshold_slider = ui_widgets.get('threshold_slider')
            if threshold_slider:
                config['threshold'] = threshold_slider.value()
                
            min_confidence_edit = ui_widgets.get('min_confidence_edit')
            if min_confidence_edit:
                try:
                    config['min_confidence'] = float(min_confidence_edit.text())
                except (ValueError, AttributeError):
                    config['min_confidence'] = 0.5  # Giá trị mặc định
        
        # Thêm xử lý cho các loại tool khác tại đây
        
        logging.info(f"SettingsManager: Collected config for {tool_name}: {config}")
        return config
    
    # ===== SETTINGS SYNCHRONIZATION METHODS =====
    
    def sync_settings_across_pages(self):
        """Đồng bộ settings giữa tất cả các pages"""
        try:
            # Collect current settings from all pages
            self._collect_camera_settings()
            self._collect_detection_settings()
            
            # Apply synchronized settings to all pages
            self._apply_synchronized_settings()
            
            logging.info("SettingsManager: Settings synchronized across all pages")
            
        except Exception as e:
            logging.error(f"SettingsManager: Error synchronizing settings: {str(e)}")
    
    def _collect_camera_settings(self):
        """Thu thập settings từ camera page"""
        try:
            if not self.camera_setting_page:
                return
            
            # Collect exposure settings
            exposure_edit = self.camera_setting_page.findChild(QDoubleSpinBox, "exposureEdit")
            if exposure_edit:
                self.shared_settings['camera']['exposure'] = exposure_edit.value()
            
            # Collect frame size settings
            frame_width_edit = self.camera_setting_page.findChild(QSpinBox, "frameWidthEdit")
            frame_height_edit = self.camera_setting_page.findChild(QSpinBox, "frameHeightEdit")
            if frame_width_edit and frame_height_edit:
                self.shared_settings['camera']['frame_size'] = {
                    'width': frame_width_edit.value(),
                    'height': frame_height_edit.value()
                }
            
            # Collect other camera settings as needed
            logging.info(f"SettingsManager: Collected camera settings: {self.shared_settings['camera']}")
            
        except Exception as e:
            logging.error(f"SettingsManager: Error collecting camera settings: {str(e)}")
    
    def _collect_detection_settings(self):
        """Thu thập settings từ detection page"""
        try:
            if not self.detect_setting_page:
                return
            
            # Collect threshold settings
            threshold_slider = self.detect_setting_page.findChild(QSlider, "threshold_slider")
            if threshold_slider:
                self.shared_settings['detection']['threshold'] = threshold_slider.value()
            
            # Collect confidence settings
            min_confidence_edit = self.detect_setting_page.findChild(QDoubleSpinBox, "min_confidence_edit")
            if min_confidence_edit:
                self.shared_settings['detection']['min_confidence'] = min_confidence_edit.value()
            
            # Collect other detection settings as needed
            logging.info(f"SettingsManager: Collected detection settings: {self.shared_settings['detection']}")
            
        except Exception as e:
            logging.error(f"SettingsManager: Error collecting detection settings: {str(e)}")
    
    def _apply_synchronized_settings(self):
        """Áp dụng synchronized settings cho tất cả pages"""
        try:
            # Apply to camera page
            if self.camera_setting_page and self.shared_settings['camera']:
                self._apply_camera_settings()
            
            # Apply to detection page
            if self.detect_setting_page and self.shared_settings['detection']:
                self._apply_detection_settings()
            
            logging.info("SettingsManager: Applied synchronized settings to all pages")
            
        except Exception as e:
            logging.error(f"SettingsManager: Error applying synchronized settings: {str(e)}")
    
    def _apply_camera_settings(self):
        """Áp dụng camera settings"""
        try:
            settings = self.shared_settings['camera']
            
            # Apply exposure
            if 'exposure' in settings:
                exposure_edit = self.camera_setting_page.findChild(QDoubleSpinBox, "exposureEdit")
                if exposure_edit:
                    exposure_edit.setValue(settings['exposure'])
            
            # Apply frame size
            if 'frame_size' in settings:
                frame_width_edit = self.camera_setting_page.findChild(QSpinBox, "frameWidthEdit")
                frame_height_edit = self.camera_setting_page.findChild(QSpinBox, "frameHeightEdit")
                if frame_width_edit and frame_height_edit:
                    frame_width_edit.setValue(settings['frame_size']['width'])
                    frame_height_edit.setValue(settings['frame_size']['height'])
            
            logging.info("SettingsManager: Applied camera settings")
            
        except Exception as e:
            logging.error(f"SettingsManager: Error applying camera settings: {str(e)}")
    
    def _apply_detection_settings(self):
        """Áp dụng detection settings"""
        try:
            settings = self.shared_settings['detection']
            
            # Apply threshold
            if 'threshold' in settings:
                threshold_slider = self.detect_setting_page.findChild(QSlider, "threshold_slider")
                if threshold_slider:
                    threshold_slider.setValue(settings['threshold'])
            
            # Apply confidence
            if 'min_confidence' in settings:
                min_confidence_edit = self.detect_setting_page.findChild(QDoubleSpinBox, "min_confidence_edit")
                if min_confidence_edit:
                    min_confidence_edit.setValue(settings['min_confidence'])
            
            logging.info("SettingsManager: Applied detection settings")
            
        except Exception as e:
            logging.error(f"SettingsManager: Error applying detection settings: {str(e)}")
    
    def mark_page_changed(self, page_type: str):
        """Đánh dấu page có thay đổi settings"""
        if page_type in self.pending_changes:
            self.pending_changes[page_type] = True
            logging.info(f"SettingsManager: Marked {page_type} page as changed")
    
    def get_current_page_type(self) -> str:
        """Lấy loại page hiện tại"""
        if not self.setting_stacked_widget:
            return "unknown"
        
        current_widget = self.setting_stacked_widget.currentWidget()
        if current_widget == self.camera_setting_page:
            return "camera"
        elif current_widget == self.detect_setting_page:
            return "detection"
        else:
            return "unknown"
    
    def has_pending_changes(self) -> bool:
        """Kiểm tra có pending changes không"""
        return any(self.pending_changes.values())
    
    def clear_pending_changes(self):
        """Clear tất cả pending changes"""
        for key in self.pending_changes:
            self.pending_changes[key] = False
        logging.info("SettingsManager: Cleared all pending changes")
