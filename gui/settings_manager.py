from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QStackedWidget, QWidget, QPushButton
import logging

class SettingsManager(QObject):
    """
    Quản lý giao diện cài đặt và xử lý chuyển đổi giữa các trang cài đặt
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setting_stacked_widget = None
        self.camera_setting_page = None
        self.detect_setting_page = None
        self.apply_setting_button = None
        self.cancel_setting_button = None
        
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
            return
            
        if not self.setting_stacked_widget:
            logging.error("SettingsManager: settingStackedWidget not found")
            return
            
        # Log current state of the stacked widget
        current_index = self.setting_stacked_widget.currentIndex()
        count = self.setting_stacked_widget.count()
        logging.info(f"SettingsManager: Current settingStackedWidget state: index={current_index}, count={count}")
            
        # Xác định trang cài đặt dựa trên tên tool
        target_page = None
        if tool_name == "Detect Tool" and self.detect_setting_page:
            target_page = self.detect_setting_page
            logging.info("SettingsManager: Target page is detectSettingPage")
        elif tool_name == "Other Tool" and hasattr(self, 'other_tool_setting_page'):
            target_page = self.other_tool_setting_page
            logging.info("SettingsManager: Target page is otherToolSettingPage")
        else:
            logging.error(f"SettingsManager: No matching page found for tool: {tool_name}")
            
        # Chuyển đến trang cài đặt nếu tìm thấy
        if target_page:
            index = self.setting_stacked_widget.indexOf(target_page)
            logging.info(f"SettingsManager: Found target page at index: {index}")
            if index != -1:
                logging.info(f"SettingsManager: Switching to {tool_name} setting page with index {index}.")
                self.setting_stacked_widget.setCurrentIndex(index)
                # Verify the switch
                new_index = self.setting_stacked_widget.currentIndex()
                logging.info(f"SettingsManager: After switch, current index is: {new_index}")
                return True
            else:
                logging.error(f"SettingsManager: Setting page for {tool_name} not found in settingStackedWidget.")
        else:
            logging.error(f"SettingsManager: No setting page defined for {tool_name}")
            
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
