from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QStackedWidget, QWidget, QPushButton, QSlider, QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox, QCheckBox
import logging
from utils.debug_utils import conditional_print
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
        self.save_image_page = None  # Add saveImagePage reference
        self.classification_setting_page = None  # Classification settings page
        self.palette_page = None  # Trang palette mới (mặc định)
        self.apply_setting_button = None
        self.cancel_setting_button = None
        
        # Lưu trang trước khi chỉnh sửa tool để trở về
        self.previous_page_index = 0
        self.current_editing_tool = None
        
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
            "OCR": "detect",
            "Camera Source": "camera",  # Add Camera Source tool mapping to camera settings page
            "Save Image": "save_image",  # Add Save Image tool mapping to saveImagePage
            "Classification Tool": "classification",  # Add Classification Tool mapping
            "Result Tool": "detect"  # Add Result Tool mapping (use detect page as fallback)
        }
        
    def setup(self, stacked_widget, camera_page, detect_page, apply_button, cancel_button, save_image_page=None):
        """Thiết lập các tham chiếu đến các widget UI"""
        self.setting_stacked_widget = stacked_widget
        self.camera_setting_page = camera_page
        self.detect_setting_page = detect_page
        self.apply_setting_button = apply_button
        self.cancel_setting_button = cancel_button

        # Find saveImagePage if not provided
        if save_image_page:
            self.save_image_page = save_image_page
        elif stacked_widget:
            # Try to find saveImagePage by name
            self.save_image_page = stacked_widget.findChild(QWidget, 'saveImagePage')
            if self.save_image_page:
                logging.info("SettingsManager: Found saveImagePage automatically")
            else:
                logging.warning("SettingsManager: saveImagePage not found")

        # Find classificationSettingPage automatically
        if stacked_widget and not self.classification_setting_page:
            self.classification_setting_page = stacked_widget.findChild(QWidget, 'classificationSettingPage')
            if self.classification_setting_page:
                logging.info("SettingsManager: Found classificationSettingPage automatically")
            else:
                logging.warning("SettingsManager: classificationSettingPage not found")
        
        # Vô hiệu hóa nút ngay từ đầu
        if self.apply_setting_button:
            self.apply_setting_button.setEnabled(False)
            logging.info("SettingsManager: Disabled Apply button during setup")
        if self.cancel_setting_button:
            self.cancel_setting_button.setEnabled(False)
            logging.info("SettingsManager: Disabled Cancel button during setup")
        
        # Tìm palette page (mặc định là index 0)
        if self.setting_stacked_widget and self.setting_stacked_widget.count() > 0:
            self.palette_page = self.setting_stacked_widget.widget(0)
            if self.palette_page:
                logging.info(f"SettingsManager: palettePage found: {self.palette_page.objectName()}")
        
        # Đặt trang mặc định là palettePage
        if self.setting_stacked_widget and self.palette_page:
            self.setting_stacked_widget.setCurrentWidget(self.palette_page)
            
        # Kết nối signal cho stacked widget để theo dõi thay đổi trang
        if self.setting_stacked_widget:
            self.setting_stacked_widget.currentChanged.connect(self._on_stacked_widget_page_changed)
        
        # Vô hiệu hóa các nút Apply/Cancel khi ở trang palette (mặc định)
        self._update_buttons_state(is_palette_page=True)
        
        # Log thông tin về các widget đã tìm thấy
        logging.info(f"SettingsManager: settingStackedWidget found: {self.setting_stacked_widget is not None}")
        logging.info(f"SettingsManager: cameraSettingPage found: {self.camera_setting_page is not None}")
        logging.info(f"SettingsManager: detectSettingPage found: {self.detect_setting_page is not None}")
        logging.info(f"SettingsManager: saveImagePage found: {self.save_image_page is not None}")
        logging.info(f"SettingsManager: palettePage found: {self.palette_page is not None}")
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
        
        # CHECK: If adding Camera Source (not editing), verify only 1 exists
        if tool_name == "Camera Source":
            # ✅ Check if we're in EDIT MODE (main_window._editing_tool is set)
            is_editing = (hasattr(self.main_window, '_editing_tool') and 
                         self.main_window._editing_tool is not None)
            
            # Only check for duplicates if we're ADDING (not EDITING)
            if not is_editing:
                has_camera_source = False
                if hasattr(self.main_window, 'job_manager') and self.main_window.job_manager:
                    current_job = self.main_window.job_manager.get_current_job()
                    if current_job:
                        for tool in current_job.tools:
                            if hasattr(tool, 'name') and tool.name.lower() == "camera source":
                                has_camera_source = True
                                break
                
                # If already has Camera Source and we're ADDING, show warning and return
                if has_camera_source:
                    from PyQt5.QtWidgets import QMessageBox
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Warning)
                    msg.setWindowTitle("Camera Source Already Exists")
                    msg.setText("Job already contains a Camera Source tool.\n\nOnly 1 camera can be connected at a time.")
                    msg.setStandardButtons(QMessageBox.Ok)
                    msg.exec_()
                    conditional_print(f"DEBUG: User tried to add multiple Camera Source tools - blocked at switch_to_tool_setting_page")
                    logging.warning("SettingsManager: Attempted to add multiple Camera Source tools - blocked at switch_to_tool_setting_page")
                    return False
            else:
                conditional_print(f"DEBUG: In EDIT MODE - allowing Camera Source edit despite existing instance")
                logging.info("SettingsManager: In EDIT MODE - skipping duplicate check")
            
        if not self.setting_stacked_widget:
            logging.error("SettingsManager: settingStackedWidget not found")
            return False
            
        # Lưu trang hiện tại trước khi chuyển
        self.previous_page_index = self.setting_stacked_widget.currentIndex()
        logging.info(f"SettingsManager: Saving previous page index: {self.previous_page_index}")
        
        # Lưu tool đang được chỉnh sửa
        self.current_editing_tool = tool_name
            
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
        elif page_type == "camera" and self.camera_setting_page:
            target_page = self.camera_setting_page
            logging.info("SettingsManager: Target page is cameraSettingPage")
        elif page_type == "save_image" and self.save_image_page:
            target_page = self.save_image_page
            logging.info("SettingsManager: Target page is saveImagePage")
        elif page_type == "classification" and self.classification_setting_page:
            target_page = self.classification_setting_page
            logging.info("SettingsManager: Target page is classificationSettingPage")
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
                
                # Kích hoạt các nút Apply/Cancel khi chuyển đến trang tool
                self._update_buttons_state(is_palette_page=False)
                
                # Refresh DetectToolManager if switching to detect page
                if page_type == "detect" or tool_name == "Detect Tool":
                    if hasattr(self.main_window, 'refresh_detect_tool_manager'):
                        self.main_window.refresh_detect_tool_manager()
                    
                    # Auto-switch sourceOutputComboBox to detection mode
                    if hasattr(self.main_window, 'camera_manager') and self.main_window.camera_manager:
                        logging.info("SettingsManager: Auto-switching to detection display mode for Detect Tool editing")
                        try:
                            # Switch camera view to detection mode to show detection areas
                            if hasattr(self.main_window.camera_manager, 'camera_view'):
                                self.main_window.camera_manager.camera_view.set_display_mode("detection", tool_id="detect_tool")
                            
                            # Update sourceOutputComboBox to show detection output
                            if hasattr(self.main_window.camera_manager, 'source_output_combo') and self.main_window.camera_manager.source_output_combo:
                                combo = self.main_window.camera_manager.source_output_combo
                                for i in range(combo.count()):
                                    if "detect" in combo.itemText(i).lower():
                                        combo.setCurrentIndex(i)
                                        logging.info(f"SettingsManager: Switched sourceOutputComboBox to detection output: {combo.itemText(i)}")
                                        break
                        except Exception as e:
                            logging.warning(f"SettingsManager: Failed to auto-switch to detection mode: {e}")
                
                # Initialize/Refresh Classification page widgets and lists
                if page_type == "classification" or tool_name == "Classification Tool":
                    try:
                        if hasattr(self.main_window, 'refresh_classification_tool_manager'):
                            self.main_window.refresh_classification_tool_manager()
                    except Exception as e:
                        logging.warning(f"SettingsManager: Failed to refresh classification manager: {e}")
                
                # When switching to camera settings page: reflect current mode in UI and (optionally) start preview
                if page_type == "camera":
                    # Load camera formats into formatCameraComboBox first
                    try:
                        if hasattr(self.main_window, '_load_camera_formats'):
                            self.main_window._load_camera_formats()
                            logging.info("SettingsManager: Loaded camera formats into comboBox")
                    except Exception as e:
                        logging.warning(f"SettingsManager: Failed to load camera formats: {e}")
                    
                    if hasattr(self.main_window, 'camera_manager') and self.main_window.camera_manager:
                        # Sync mode buttons to current live/trigger state
                        try:
                            self.main_window.camera_manager.update_camera_mode_ui()
                        except Exception:
                            pass
                        # Auto-start preview (existing behavior)
                        # Don't force mode change - preserve current camera mode and stream
                        try:
                            self.main_window.camera_manager.start_live_camera(force_mode_change=False)
                            logging.info("SettingsManager: Camera started for settings preview")
                        except Exception as e:
                            logging.warning(f"SettingsManager: Failed to auto-start camera: {e}")
                
                # Verify the switch
                new_index = self.setting_stacked_widget.currentIndex()
                logging.info(f"SettingsManager: After switch, current index is: {new_index}")
                return True
            else:
                logging.error(f"SettingsManager: Setting page for {tool_name} not found in settingStackedWidget.")
        
        return False
        
    def return_to_camera_setting_page(self):
        """Quay lại trang cài đặt camera (DEPRECATED - sử dụng return_to_palette_page)"""
        logging.warning("SettingsManager: return_to_camera_setting_page is deprecated, use return_to_palette_page instead")
        return self.return_to_palette_page()
        
    def return_to_palette_page(self):
        """Quay lại trang palette (trang mặc định)"""
        if not self.setting_stacked_widget or not self.palette_page:
            logging.error("SettingsManager: settingStackedWidget or palettePage not available.")
            return False
            
        # Stop camera if currently running before returning to palette
        if hasattr(self.main_window, 'camera_manager') and self.main_window.camera_manager:
            logging.info("SettingsManager: Stopping camera before returning to palette")
            # Disable job processing and flush camera pipeline
            try:
                if hasattr(self.main_window.camera_manager, 'job_enabled'):
                    self.main_window.camera_manager.job_enabled = False
                cs = getattr(self.main_window.camera_manager, 'camera_stream', None)
                if cs and hasattr(cs, 'set_job_enabled'):
                    cs.set_job_enabled(False)
                if cs and hasattr(cs, 'cancel_all_and_flush'):
                    cs.cancel_all_and_flush()
            except Exception:
                pass
            # Then stop camera safely
            self.main_window.camera_manager.stop_camera_for_apply()
            
        index = self.setting_stacked_widget.indexOf(self.palette_page)
        if index != -1:
            logging.info(f"SettingsManager: Returning to palette page with index {index}.")
            self.setting_stacked_widget.setCurrentIndex(index)
            
            # Vô hiệu hóa các nút khi trở về trang palette
            self._update_buttons_state(is_palette_page=True)
            
            # Reset current editing tool
            self.current_editing_tool = None
            
            # Update camera button state after returning to palette page
            if hasattr(self.main_window, '_update_camera_button_state'):
                logging.info("SettingsManager: Updating camera button state after returning to palette")
                self.main_window._update_camera_button_state()
                
            return True
        else:
            logging.error("SettingsManager: Palette page not found in settingStackedWidget.")
            return False
            
    def return_to_previous_page(self):
        """Quay lại trang trước đó"""
        if not self.setting_stacked_widget:
            logging.error("SettingsManager: settingStackedWidget not available.")
            return False
            
        if self.previous_page_index < 0 or self.previous_page_index >= self.setting_stacked_widget.count():
            logging.warning(f"SettingsManager: Invalid previous page index: {self.previous_page_index}. Returning to palette page.")
            return self.return_to_palette_page()
            
        logging.info(f"SettingsManager: Returning to previous page with index {self.previous_page_index}.")
        self.setting_stacked_widget.setCurrentIndex(self.previous_page_index)
        return True
            
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
            
            # Collect exposure settings (new-only)
            exposure_edit = self.camera_setting_page.findChild(QDoubleSpinBox, "exposureTimeEdit")
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
            
            # Apply exposure (new-only)
            if 'exposure' in settings:
                exposure_edit = self.camera_setting_page.findChild(QDoubleSpinBox, "exposureTimeEdit")
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
        if current_widget == self.palette_page:
            return "palette"
        elif current_widget == self.camera_setting_page:
            return "camera"
        elif current_widget == self.detect_setting_page:
            return "detect"  # Changed from "detection" to "detect" to match the logic in main_window.py
        elif current_widget == self.save_image_page:
            return "save_image"
        elif hasattr(self, 'classification_setting_page') and self.classification_setting_page and current_widget == self.classification_setting_page:
            return "classification"
        else:
            return "unknown"
    
    def post_init(self):
        """Được gọi sau khi tất cả các thành phần đã được thiết lập để đảm bảo trạng thái UI chính xác"""
        logging.info("SettingsManager: Running post-initialization tasks")
        
        # Đảm bảo các nút Apply/Cancel bị vô hiệu hóa khi ở trang palette
        if self.setting_stacked_widget and self.palette_page:
            # Kiểm tra xem trang hiện tại có phải là palette không
            current_widget = self.setting_stacked_widget.currentWidget()
            is_palette = (current_widget == self.palette_page)
            
            # Vô hiệu hóa các nút nếu đang ở trang palette
            self._update_buttons_state(is_palette_page=is_palette)
            
            # Đảm bảo rằng các nút luôn bị vô hiệu hóa khi khởi động
            if self.apply_setting_button:
                self.apply_setting_button.setEnabled(False)
                logging.info("SettingsManager: Explicitly disabled Apply button in post_init")
            if self.cancel_setting_button:
                self.cancel_setting_button.setEnabled(False)
                logging.info("SettingsManager: Explicitly disabled Cancel button in post_init")
    
    def _on_stacked_widget_page_changed(self, index):
        """Xử lý khi người dùng thay đổi trang trong StackedWidget"""
        # Kiểm tra xem trang hiện tại có phải là palettePage không
        current_widget = self.setting_stacked_widget.widget(index)
        is_palette = (current_widget == self.palette_page)
        
        # Cập nhật trạng thái nút Apply/Cancel
        self._update_buttons_state(is_palette_page=is_palette)
        
    def _update_buttons_state(self, is_palette_page=False):
        """Cập nhật trạng thái kích hoạt/vô hiệu hóa của các nút Apply/Cancel"""
        if self.apply_setting_button:
            self.apply_setting_button.setEnabled(not is_palette_page)
            logging.info(f"SettingsManager: Apply button {'disabled' if is_palette_page else 'enabled'}")
            
        if self.cancel_setting_button:
            self.cancel_setting_button.setEnabled(not is_palette_page)
            logging.info(f"SettingsManager: Cancel button {'disabled' if is_palette_page else 'enabled'}")
    def has_pending_changes(self) -> bool:
        """Kiểm tra có pending changes không"""
        return any(self.pending_changes.values())
    
    def clear_pending_changes(self):
        """Clear tất cả pending changes"""
        for key in self.pending_changes:
            self.pending_changes[key] = False
        logging.info("SettingsManager: Cleared all pending changes")
