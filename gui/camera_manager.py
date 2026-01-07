from PyQt5.QtCore import QObject, pyqtSlot, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication, QComboBox
from camera.camera_stream import CameraStream
from gui.camera_view import CameraView
from utils.debug_utils import conditional_print
import logging
import re
import inspect
import time

class CameraOperationThread(QThread):
    """Thread for non-blocking camera operations"""
    operation_completed = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, camera_stream, operation, *args):
        super().__init__()
        self.camera_stream = camera_stream
        self.operation = operation
        self.args = args
        
    def run(self):
        try:
            if self.operation == 'set_trigger_mode':
                success = self.camera_stream.set_trigger_mode(self.args[0])
                message = f"Trigger mode {'enabled' if self.args[0] else 'disabled'}"
                self.operation_completed.emit(success, message)
            elif self.operation == 'set_format':
                success = self.camera_stream.set_format(self.args[0])
                message = f"Format changed to {self.args[0]}"
                self.operation_completed.emit(success, message)
        except Exception as e:
            self.operation_completed.emit(False, f"Operation failed: {str(e)}")

class CameraManager(QObject):
    """
    Qu   n l   camera v   x    l   t    ng t  c v   i camera
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent  # Store reference to main window
        self.camera_stream = None
        self.camera_view = None
        self.exposure_edit = None  # Ch    c  n exposure edit, kh  ng c   slider
        self.gain_edit = None
        self.ev_edit = None
        self.focus_bar = None
        self.fps_num = None
        self.width_spinbox = None
        self.height_spinbox = None
        
        # Settings synchronization
        self.settings_manager = None  # Will be set by main window
        
        # Camera mode state
        self.current_mode = 'live'  # Default to 'live' mode
        self.live_camera_btn = None
        self.trigger_camera_btn = None
        self.live_camera_mode = None  # Button for switching to live mode
        self.trigger_camera_mode = None  # Button for switching to trigger mode
        
        # Job control state
        self.job_enabled = False  # Mặc định DISABLE job execution để tránh camera bị đơ cứng
        self.job_toggle_btn = None
        
        # Frame processing throttling for performance
        # self._frame_skip_counter = 0
        # self._frame_skip_interval = 3  # Process every 3rd frame for better performance  
        # self._last_processed_frame = None  # Store last processed frame to show during skipped frames
        
        # Exposure settings state
        self._is_auto_exposure = False  # B   t      u v   i manual mode       user c   th    ch   nh exposure
        self._pending_exposure_settings = {}  # L  u settings ch  a apply
        self._instant_apply = True  # Enable instant apply cho better UX
        self.auto_exposure_btn = None
        self.manual_exposure_btn = None
        self.apply_settings_btn = None
        self.cancel_settings_btn = None
        
        # Mode change flag: Skip redundant flush in helper methods when called from on_trigger_camera_mode_clicked
        self._mode_changing = False  # Flag để kiểm soát flush trong helper methods
        
        # UI state
        self.ui_enabled = False
        
        # Thread management for non-blocking operations
        self.operation_thread = None
        
        # Trigger capture flag to prevent double job execution
        self._trigger_capturing = False
    
    def cleanup(self):
        """Clean up camera manager resources including threads"""
        # Wait for any running operations to complete
        if self.operation_thread and self.operation_thread.isRunning():
            self.operation_thread.wait(5000)  # Wait up to 5 seconds
        
        # Clean up camera stream
        if self.camera_stream:
            try:
                self.camera_stream.cleanup()
            except Exception as e:
                logging.warning(f"Error cleaning up camera stream: {e}")
        
        # AWB controls
        self.auto_awb_btn = None
        self.manual_awb_btn = None
        self.colour_gain_r_edit = None
        self.colour_gain_b_edit = None
        self._is_auto_awb = True
        
        # Arm-and-wait behavior: mark waiting for first frame after (re)start
        self._waiting_first_frame = False
        # Preferred mode memory when no CameraTool is present
        self.preferred_mode = 'live'

        # Remember user's last selected mode even without CameraTool
        self.preferred_mode = 'live'
        
    def _warn_no_camera_source(self):
        """Show a warning dialog requesting user to add Camera Source tool."""
        try:
            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Thi   u Camera Source")
            msg.setText("Ch  a c   Camera Source trong workflow.")
            msg.setInformativeText("Vui l  ng th  m 'Camera Source' tr     c khi b   t camera.")
            msg.exec_()
        except Exception as e:
            logging.warning(f"Could not show warning dialog: {e}")
        # Reset related toggles/buttons if present
        try:
            if hasattr(self, 'live_camera_btn') and self.live_camera_btn:
                self.live_camera_btn.setChecked(False)
        except Exception:
            pass
        try:
            if hasattr(self, 'main_window') and self.main_window and hasattr(self.main_window, 'onlineCamera') and self.main_window.onlineCamera:
                self.main_window.onlineCamera.setChecked(False)
        except Exception:
            pass

    def _ensure_camera_source_present(self) -> bool:
        """Return True if Camera Source tool exists; otherwise warn and return False."""
        try:
            ct = self.find_camera_tool() if hasattr(self, 'find_camera_tool') else None
            if ct:
                return True
        except Exception:
            pass
        self._warn_no_camera_source()
        return False

    def setup(self, camera_view_widget, exposure_edit,
             gain_edit, ev_edit, focus_bar, fps_num, source_output_combo=None):
        """Thi   t l   p c  c tham chi   u      n c  c widget UI v   kh   i t   o camera"""
        # Kh   i t   o camera stream
        self.camera_stream = CameraStream()
        
        # Kh   i t   o camera view v   i main_window reference
        self.camera_view = CameraView(camera_view_widget, self.main_window)
        # Đảm bảo zoom level mặc định là 1.1
        if self.camera_view:
            self.camera_view.zoom_level = 1.1
            if hasattr(self.camera_view, '_zoom_changed'):
                self.camera_view._zoom_changed = True
            conditional_print(f"DEBUG: [CameraManager] Set zoom_level = 1.1 in setup")
        self.camera_stream.frame_ready.connect(self.camera_view.display_frame)
        # Rebind frame_ready to route through our handler so we can run the job pipeline
        try:
            self.camera_stream.frame_ready.disconnect(self.camera_view.display_frame)
        except Exception:
            pass
        self.camera_stream.frame_ready.connect(self._on_frame_from_camera)
        
        # Setup source output combo box
        self.source_output_combo = source_output_combo
        if self.source_output_combo:
            self.setup_source_output_combo()
        
        # Reload camera formats after camera stream is initialized
        if self.main_window and hasattr(self.main_window, 'reload_camera_formats'):
            self.main_window.reload_camera_formats()
        
        # K   t n   i c  c widget -      b    gain_slider v   ev_slider
        self.exposure_edit = exposure_edit
        self.gain_edit = gain_edit
        self.ev_edit = ev_edit
        self.focus_bar = focus_bar
        self.fps_num = fps_num
        
        # K   t n   i signals v   slots
        self.camera_view.focus_calculated.connect(self.update_focus_value)
        self.camera_view.fps_updated.connect(self.update_fps_display)
        
        # T   t hi   n th    FPS tr  n g  c h  nh    nh preview
        self.camera_view.toggle_fps_display(False)
        
        # Set initial manual exposure mode
        self.set_manual_exposure_mode()
        self.update_exposure_mode_ui()
        
        # Sync initial camera parameters (ch    khi camera s   n s  ng)
        # self.update_camera_params_from_camera()  # Ho  n l   i      n khi camera start
        
        # Kh   i t   o m   c      nh auto exposure
        self.set_auto_exposure_mode()
        
        # K   t n   i signal cho c  c tham s    camera
        self.setup_camera_param_signals()
        
        logging.info("CameraManager: Setup completed")
        
        # Disable UI initially
        self.set_ui_enabled(False)
        
        # Ensure camera mode UI is properly initialized (với trigger button disabled)
        self.update_camera_mode_ui()

    def register_tool(self, tool):
        """Register Camera Source tool (cache reference during pending/edit).

        Allows CameraManager to find the tool even before it's added to the job.
        """
        try:
            name = getattr(tool, 'name', '')
            if name == 'Camera Source' or getattr(tool, '__class__', type('X',(),{})).__name__ == 'CameraTool':
                tool.camera_manager = self
                self._camera_tool_ref = tool
                
                # Đảm bảo CameraView hiển thị với mức zoom mặc định là 1.1 khi thêm CameraTool
                if self.camera_view:
                    self.camera_view.zoom_level = 1.1
                    if hasattr(self.camera_view, '_zoom_changed'):
                        self.camera_view._zoom_changed = True
                    conditional_print(f"DEBUG: [CameraManager] Đã đặt zoom_level = 1.1 trong register_tool")
                
                return True
        except Exception as e:
            logging.warning(f"Error registering tool: {e}")
        return False
        
    def _is_editing_camera_tool(self) -> bool:
        """Return True if the user is currently editing the Camera Source tool.

        Checks multiple sources for robustness: ToolManager's current editing tool,
        MainWindow's _editing_tool, and SettingsManager's current_editing_tool name.
        """
        try:
            mw = getattr(self, 'main_window', None)
            if mw is None:
                return False
                
            # If we're on palette page, we're definitely not editing
            sm = getattr(mw, 'settings_manager', None)
            if sm and getattr(sm, 'palette_page', None):
                current_widget = None
                if hasattr(sm, 'setting_stacked_widget') and sm.setting_stacked_widget:
                    current_widget = sm.setting_stacked_widget.currentWidget()
                
                # If current widget is palette page, we're not editing
                if current_widget == sm.palette_page:
                    return False
                
            # Check if we're on the camera settings page AND actively editing a tool
            if sm:
                # Only consider it editing if we're on camera page AND there's a tool being edited
                if getattr(sm, 'current_page_type', None) == 'camera' and hasattr(mw, '_editing_tool'):
                    tm = getattr(mw, 'tool_manager', None)
                    if tm and hasattr(tm, '_pending_tool') and tm._pending_tool == "Camera Source":
                        return True
                
                if getattr(sm, 'current_editing_tool', None) == 'Camera Source':
                    return True
                    
            # Prefer ToolManager's state
            tm = getattr(mw, 'tool_manager', None)
            if tm and hasattr(tm, 'get_current_editing_tool'):
                t = tm.get_current_editing_tool()
                if t and getattr(t, 'name', '') == 'Camera Source':
                    return True
                    
            # Fallback to MainWindow's own editing reference
            et = getattr(mw, '_editing_tool', None)
            if et and getattr(et, 'name', '') == 'Camera Source':
                return True
                
        except Exception:
            pass
        return False

    def _on_frame_from_camera(self, frame):
        """Handle frames from camera; run job pipeline when enabled, otherwise show raw.

        Drops incoming frames while processing to keep UI responsive.
        """
        try:
            # Detect trigger capture mode - will run job but will skip subsequent live frames
            trigger_capturing = getattr(self, '_trigger_capturing', False)
            # Count calls for debugging
            self._frame_call_count = getattr(self, '_frame_call_count', 0) + 1
            if trigger_capturing:
                conditional_print(f"DEBUG: [CameraManager] _on_frame_from_camera called during TRIGGER CAPTURE (call #{self._frame_call_count}) - processing job for trigger frame")
            else:
                conditional_print(f"DEBUG: [CameraManager] _on_frame_from_camera called - _trigger_capturing=False (call #{self._frame_call_count}), processing live frame")
            
            # If we're waiting for the first frame after (re)start, clear the flag and sync UI
            if getattr(self, '_waiting_first_frame', False):
                self._waiting_first_frame = False
                try:
                    self.update_camera_mode_ui()
                except Exception:
                    pass
            # Enforce workflow disabled if configured
            if hasattr(self, 'workflow_enabled') and not self.workflow_enabled:
                self.job_enabled = False
            # If job execution is disabled OR we're editing Camera Source, just display raw frame
            if self._is_editing_camera_tool():
                if self.camera_view:
                    self.camera_view.display_frame(frame)
                return
            if not getattr(self, 'job_enabled', False):
                if self.camera_view:
                    self.camera_view.display_frame(frame)
                return

            # Ensure we have a job to run
            job_manager = getattr(self.main_window, 'job_manager', None) if hasattr(self, 'main_window') else None
            current_job = job_manager.get_current_job() if job_manager else None
            if not job_manager or not current_job or not current_job.tools:
                if self.camera_view:
                    self.camera_view.display_frame(frame)
                print(f"WARNING: No job available. job_manager={job_manager}, current_job={current_job}, tools={len(current_job.tools) if current_job else 0}")
                return

            # Debug: Show what tools are in the job
            tools_list = ", ".join([f"{t.name}" for t in current_job.tools])
            conditional_print(f"DEBUG: Job has {len(current_job.tools)} tools: [{tools_list}]")

            try:
                # Build context for pipeline: include pixel_format for correct color handling
                # Get current format from camera stream (default is RGB888)
                import cv2
                pixel_format = 'RGB888'  # Default - camera_stream outputs RGB888
                if hasattr(self.camera_stream, 'get_pixel_format'):
                    try:
                        current_format = self.camera_stream.get_pixel_format()
                        if current_format and current_format in ['BGR888', 'RGB888', 'XRGB8888', 'YUV420', 'NV12']:
                            pixel_format = current_format
                            conditional_print(f"DEBUG: [CameraManager] Using current camera format: {pixel_format}")
                    except Exception as e:
                        conditional_print(f"DEBUG: [CameraManager] Could not get camera format: {e}, using default RGB888")
                
                conditional_print(f"DEBUG: [CameraManager] Frame format: {pixel_format} for job processing")
                
                initial_context = {"force_save": True, "pixel_format": str(pixel_format)}
                conditional_print(f"DEBUG: [CameraManager] RUNNING JOB PIPELINE (trigger_capturing={getattr(self, '_trigger_capturing', False)})")
                
                # Tính toán thời gian thực thi
                import time as time_module
                start_time = time_module.time()
                processed_image, job_results = job_manager.run_current_job(frame, context=initial_context)
                total_execution_time = time_module.time() - start_time
                
                conditional_print(f"DEBUG: [CameraManager] JOB PIPELINE COMPLETED in {total_execution_time:.3f}s")
                
                # Cập nhật executionTime label với inference time từ ONNX model
                try:
                    if job_results and isinstance(job_results, dict):
                        inference_time = 0.0
                        
                        # Priority 1: Check nested results -> Detect Tool -> data -> inference_time
                        results_data = job_results.get('results', {})
                        if isinstance(results_data, dict):
                            detect_tool = results_data.get('Detect Tool', {})
                            if isinstance(detect_tool, dict):
                                detect_data = detect_tool.get('data', {})
                                if isinstance(detect_data, dict) and 'inference_time' in detect_data:
                                    inference_time = detect_data['inference_time']
                                    logging.info(f"Found inference_time from Detect Tool: {inference_time:.3f}s")
                        
                        # Priority 2: Check top-level inference_time
                        if inference_time == 0.0:
                            inference_time = job_results.get('inference_time', 0.0)
                            if inference_time > 0.0:
                                logging.info(f"Found inference_time from top-level: {inference_time:.3f}s")
                        
                        # Priority 3: Search tool_results
                        if inference_time == 0.0 and 'tool_results' in job_results:
                            tool_results = job_results['tool_results']
                            if isinstance(tool_results, dict):
                                for tool_name, tool_result in tool_results.items():
                                    if isinstance(tool_result, dict) and 'inference_time' in tool_result:
                                        inference_time = tool_result['inference_time']
                                        logging.info(f"Found inference_time from {tool_name}: {inference_time:.3f}s")
                                        break
                        
                        # Fallback: Use total execution time if no inference_time found
                        if inference_time == 0.0:
                            inference_time = total_execution_time
                            logging.info(f"No inference_time found, using total_execution_time: {inference_time:.3f}s")
                        
                        # Cập nhật executionTime label nếu có
                        if hasattr(self, 'main_window') and self.main_window:
                            if hasattr(self.main_window, 'executionTime') and self.main_window.executionTime:
                                self.main_window.executionTime.display(round(inference_time, 3))
                                conditional_print(f"DEBUG: Updated executionTime label: {inference_time:.3f}s")
                except Exception as update_err:
                    logging.debug(f"Could not update executionTime label: {update_err}")
                
                # Update execution label with OK/NG status
                self._update_execution_label(job_results)
                
                if self.camera_view:
                    self.camera_view.display_frame(processed_image if processed_image is not None else frame)
            except Exception as e:
                logging.getLogger(__name__).error(f"Error processing frame in job pipeline: {e}")
                if self.camera_view:
                    self.camera_view.display_frame(frame)
        except Exception:
            # As a last resort, show the raw frame
            try:
                if self.camera_view:
                    self.camera_view.display_frame(frame)
            except Exception:
                pass

    def stop_camera_for_apply(self):
        """Stop camera before applying Camera Source tool to prevent conflicts"""
        logging.info("CameraManager: Stopping camera before applying Camera Source tool")
        
        if self.camera_stream and self.camera_stream.is_running():
            try:
                # Preferred safe stop: cancel pending and stop live
                try:
                    self.camera_stream.cancel_and_stop_live()
                except AttributeError:
                    if hasattr(self.camera_stream, 'cancel_all_and_flush'):
                        self.camera_stream.cancel_all_and_flush()
                    if hasattr(self.camera_stream, 'stop_live'):
                        self.camera_stream.stop_live()
            except Exception as e:
                logging.warning(f"Error stopping camera: {e}")
            
            # Reset camera mode buttons
            if self.live_camera_btn:
                self.live_camera_btn.setChecked(False)
            if self.trigger_camera_btn:
                self.trigger_camera_btn.setChecked(False)
                
            # Preserve selected mode; if CameraTool available, sync current_mode from it
            try:
                ct = self.find_camera_tool()
                if ct:
                    mode = ct.get_camera_mode()
                    if mode:
                        self.current_mode = mode
            except Exception:
                pass
            self.update_camera_mode_ui()
            
            # Clear camera view display areas
            if self.camera_view:
                self.camera_view.clear_all_areas()
                # Đảm bảo zoom level vẫn được đặt về giá trị mặc định 1.1
                self.camera_view.zoom_level = 1.1
                if hasattr(self.camera_view, '_zoom_changed'):
                    self.camera_view._zoom_changed = True
                conditional_print(f"DEBUG: [CameraManager] Đã đặt zoom_level = 1.1 trong stop_camera_for_apply")
                
            # Refresh source output combo to show updated pipeline
            self.refresh_source_output_combo()
                
            logging.info("CameraManager: Camera stopped for apply - source output combo refreshed")
            return True
        else:
            # Still refresh the combo even if camera wasn't running
            self.refresh_source_output_combo()
            return False
        
    def setup_source_output_combo(self):
        """Source output selection is disabled; do nothing."""
        try:
            # If the widget exists, hide and disable it
            if hasattr(self, 'source_output_combo') and self.source_output_combo:
                try:
                    self.source_output_combo.setEnabled(False)
                    self.source_output_combo.setVisible(False)
                except Exception:
                    pass
        except Exception:
            pass
        return False
        
    def refresh_source_output_combo(self):
        """Source output selection is disabled; do nothing."""
        return False
        
    def on_source_output_changed(self, text):
        """Handle source output combo box selection change"""
        if not self.source_output_combo:
            return
            
        # Get the data associated with the selection
        current_data = self.source_output_combo.currentData()
        
        # Handle different pipeline outputs
        if current_data == "camera":
            # Show raw camera feed
            if hasattr(self.camera_view, 'set_display_mode'):
                self.camera_view.set_display_mode("camera")
        elif current_data and current_data.startswith("detection_"):
            # Show detection results overlay
            tool_id = current_data.split("_")[1]
            if hasattr(self.camera_view, 'set_display_mode'):
                self.camera_view.set_display_mode("detection", tool_id=tool_id)
        elif current_data and current_data.startswith("edge_"):
            # Show edge detection results
            tool_id = current_data.split("_")[1]
            if hasattr(self.camera_view, 'set_display_mode'):
                self.camera_view.set_display_mode("edge", tool_id=tool_id)
        elif current_data and current_data.startswith("ocr_"):
            # Show OCR results overlay
            tool_id = current_data.split("_")[1]
            if hasattr(self.camera_view, 'set_display_mode'):
                self.camera_view.set_display_mode("ocr", tool_id=tool_id)
        else:
            # Default to camera source
            if hasattr(self.camera_view, 'set_display_mode'):
                self.camera_view.set_display_mode("camera")
        
    def setup_camera_buttons(self, live_camera_btn=None, trigger_camera_btn=None, 
                           auto_exposure_btn=None, manual_exposure_btn=None,
                           apply_settings_btn=None, cancel_settings_btn=None,
                           job_toggle_btn=None, live_camera_mode=None, trigger_camera_mode=None,
                           auto_awb_btn=None, manual_awb_btn=None,
                           colour_gain_r_edit=None, colour_gain_b_edit=None):
        """
        Thi   t l   p c  c button   i   u khi   n camera v   exposure
        
        Args:
            live_camera_btn: Button Live Camera
            trigger_camera_btn: Button Trigger Camera
            auto_exposure_btn: Button Auto Exposure
            manual_exposure_btn: Button Manual Exposure
            apply_settings_btn: Button Apply Settings
            cancel_settings_btn: Button Cancel Settings
            job_toggle_btn: Button Toggle Job Execution
            live_camera_mode: Button Live Camera Mode
            trigger_camera_mode: Button Trigger Camera Mode
        """
        self.live_camera_btn = live_camera_btn
        self.trigger_camera_btn = trigger_camera_btn
        self.auto_exposure_btn = auto_exposure_btn
        self.manual_exposure_btn = manual_exposure_btn
        self.apply_settings_btn = apply_settings_btn
        self.cancel_settings_btn = cancel_settings_btn
        self.job_toggle_btn = job_toggle_btn
        self.live_camera_mode = live_camera_mode
        self.trigger_camera_mode = trigger_camera_mode
        self.auto_awb_btn = auto_awb_btn
        self.manual_awb_btn = manual_awb_btn
        self.colour_gain_r_edit = colour_gain_r_edit
        self.colour_gain_b_edit = colour_gain_b_edit
        
        # Log missing widgets
        missing_widgets = []
        if not self.live_camera_btn:
            missing_widgets.append('liveCamera')
        if not self.trigger_camera_btn:
            missing_widgets.append('triggerCamera')
        if not self.auto_exposure_btn:
            missing_widgets.append('autoExposure')
        if not self.manual_exposure_btn:
            missing_widgets.append('manualExposure')
        if not self.apply_settings_btn:
            missing_widgets.append('applySetting')
        if not self.cancel_settings_btn:
            missing_widgets.append('cancelSetting')
        if not self.job_toggle_btn:
            missing_widgets.append('jobToggle')
        if not self.live_camera_mode:
            missing_widgets.append('liveCameraMode')
        if not self.trigger_camera_mode:
            missing_widgets.append('triggerCameraMode')
            
        if missing_widgets:
            logging.warning(f"Missing UI widgets: {', '.join(missing_widgets)}")
        
        # K   t n   i signals
        if self.live_camera_btn:
            # Disconnect any existing connections to prevent duplicate triggers
            try:
                self.live_camera_btn.clicked.disconnect()
            except TypeError:
                pass  # No connections to disconnect
            self.live_camera_btn.clicked.connect(self.on_live_camera_clicked)
            # Enable the button immediately without requiring Camera Source tool
            self.live_camera_btn.setEnabled(True)
            self.live_camera_btn.setToolTip("Start live camera preview")
            
        if self.trigger_camera_btn:
            # Disconnect any existing connections to prevent duplicate triggers
            try:
                self.trigger_camera_btn.clicked.disconnect()
            except TypeError:
                pass  # No connections to disconnect
            self.trigger_camera_btn.clicked.connect(self.on_trigger_camera_clicked)
            # Vô hiệu hóa nút ngay khi khởi động và làm cho nó trông rõ ràng là bị vô hiệu hóa
            self.trigger_camera_btn.setEnabled(False)
            self.trigger_camera_btn.setText("Trigger Camera")
            self.trigger_camera_btn.setStyleSheet("background-color: #cccccc; color: #888888;")  # Gray when disabled
            self.trigger_camera_btn.setToolTip("Start camera first")
            
            # Đảm bảo các thay đổi được áp dụng ngay lập tức
            self.trigger_camera_btn.repaint()
            
        # Connect new camera mode buttons
        if self.live_camera_mode:
            # Disconnect any existing connections to prevent duplicate triggers
            try:
                self.live_camera_mode.clicked.disconnect()
            except TypeError:
                pass  # No connections to disconnect
            self.live_camera_mode.clicked.connect(self.on_live_camera_mode_clicked)
            # Enable the button immediately without requiring Camera Source tool
            self.live_camera_mode.setEnabled(True)
            self.live_camera_mode.setToolTip("Switch to live camera mode")
            # Ensure live mode is checked by default (following self.current_mode = 'live')
            self.live_camera_mode.setChecked(True)
            
        if self.trigger_camera_mode:
            # Disconnect any existing connections to prevent duplicate triggers
            try:
                self.trigger_camera_mode.clicked.disconnect()
            except TypeError:
                pass  # No connections to disconnect
            self.trigger_camera_mode.clicked.connect(self.on_trigger_camera_mode_clicked)
            # Enable the button immediately without requiring Camera Source tool
            self.trigger_camera_mode.setEnabled(True)
            self.trigger_camera_mode.setToolTip("Switch to trigger camera mode")
            # Ensure trigger mode is unchecked by default
            self.trigger_camera_mode.setChecked(False)
            
        if self.auto_exposure_btn:
            self.auto_exposure_btn.clicked.connect(self.on_auto_exposure_clicked)
        if self.manual_exposure_btn:
            self.manual_exposure_btn.clicked.connect(self.on_manual_exposure_clicked)
        # AWB controls
        if self.auto_awb_btn:
            self.auto_awb_btn.clicked.connect(self.on_auto_awb_clicked)
            self.auto_awb_btn.setToolTip("Enable auto white balance")
        if self.manual_awb_btn:
            self.manual_awb_btn.clicked.connect(self.on_manual_awb_clicked)
            self.manual_awb_btn.setToolTip("Enable manual white balance")
        if self.colour_gain_r_edit and hasattr(self.colour_gain_r_edit, 'valueChanged'):
            self.colour_gain_r_edit.valueChanged.connect(self.on_colour_gain_r_changed)
        if self.colour_gain_b_edit and hasattr(self.colour_gain_b_edit, 'valueChanged'):
            self.colour_gain_b_edit.valueChanged.connect(self.on_colour_gain_b_changed)
        if self.apply_settings_btn:
            self.apply_settings_btn.clicked.connect(self.on_apply_settings_clicked)
        if self.cancel_settings_btn:
            self.cancel_settings_btn.clicked.connect(self.on_cancel_settings_clicked)
        # Remove job toggle behavior: disable/hide if present
        if self.job_toggle_btn:
            try:
                self.job_toggle_btn.setEnabled(False)
                self.job_toggle_btn.setVisible(False)
            except Exception:
                pass
            
        # Kh   i t   o UI state
        self.update_camera_mode_ui()
        self.update_exposure_mode_ui()
        self.update_awb_mode_ui()
        # Job toggle UI removed
        try:
            self.update_job_toggle_ui()
        except Exception:
            pass

    # --- Optional stubs to avoid AttributeError when job toggle is not used ---
    def on_job_toggle_clicked(self):
        """No-op: workflow/job toggle removed."""
        return None

    def update_job_toggle_ui(self):
        """No-op: workflow/job toggle removed."""
        return None
        
    def _apply_setting_if_manual(self, setting_type, value):
        """Helper method: Apply setting ngay l   p t   c n   u   ang     manual mode v   instant_apply enabled
        
        IMPORTANT: Nếu có frame đang xử lý, flush ngay để áp dụng settings mới
        Điều này đảm bảo UI không bị đơ khi thay đổi tham số
        
        NHƯNG: Nếu đang trong on_trigger_camera_mode_clicked(), skip flush (đã flush ở đó rồi)
        """
        if self._instant_apply and not self._is_auto_exposure and self.camera_stream:
            try:
                # NẾU CÓ FRAME ĐANG PENDING VÀ KHÔNG PHẢI LÚC MODE CHANGING, FLUSH NGAY
                # Không đợi frame hoàn thành, áp dụng settings mới ngay lập tức
                if not self._mode_changing:  # Skip flush if mode is already changing (on_trigger_camera_mode_clicked)
                    if hasattr(self.camera_stream, 'fifo_queue') and self.camera_stream.fifo_queue:
                        queue_size = len(self.camera_stream.fifo_queue.queue) if hasattr(self.camera_stream.fifo_queue, 'queue') else 0
                        if queue_size > 0:
                            conditional_print(f"DEBUG: [CameraManager] Frame pending detected ({queue_size} frames), flushing to apply new {setting_type} setting")
                            if hasattr(self.camera_stream, 'cancel_all_and_flush'):
                                self.camera_stream.cancel_all_and_flush()
                else:
                    conditional_print(f"DEBUG: [CameraManager] Skipping flush during mode change (already flushed)")
                
                # APPLY NEW SETTING
                if setting_type == 'exposure':
                    self.camera_stream.set_exposure(value)
                    conditional_print(f"DEBUG: [CameraManager] Applied new exposure: {value}")
                elif setting_type == 'gain':
                    self.camera_stream.set_gain(value)
                    conditional_print(f"DEBUG: [CameraManager] Applied new gain: {value}")
                elif setting_type == 'ev':
                    self.camera_stream.set_ev(value)
                    conditional_print(f"DEBUG: [CameraManager] Applied new EV: {value}")
            except AttributeError:
                # Camera stream kh  ng c   method n  y, skip
                pass
    
    def set_instant_apply(self, enabled):
        """Enable/disable instant apply cho exposure settings"""
        self._instant_apply = enabled
        logging.info(f"Instant apply {'enabled' if enabled else 'disabled'}")
        
    def set_ui_enabled(self, enabled):
        """B   t/t   t to  n b    UI camera"""
        self.ui_enabled = enabled
        
        # Camera buttons - Chỉ kích hoạt các nút khác, KHÔNG kích hoạt trigger_camera_btn
        if self.live_camera_btn:
            self.live_camera_btn.setEnabled(enabled)
        # trigger_camera_btn được quản lý trong update_camera_mode_ui
        if self.live_camera_mode:
            self.live_camera_mode.setEnabled(enabled)
        if self.trigger_camera_mode:
            self.trigger_camera_mode.setEnabled(enabled)
            
        # Đảm bảo UI mode camera được cập nhật đúng
        self.update_camera_mode_ui()
            
        # Settings controls
        self.set_settings_controls_enabled(enabled and not self._is_auto_exposure)
        # AWB controls
        if hasattr(self, 'set_awb_controls_enabled'):
            self.set_awb_controls_enabled(enabled and not getattr(self, '_is_auto_awb', True))
        
        # Apply/Cancel buttons
        if self.apply_settings_btn:
            self.apply_settings_btn.setEnabled(enabled)
        if self.cancel_settings_btn:
            self.cancel_settings_btn.setEnabled(enabled)
    
    def get_exposure_value(self):
        """Return current exposure in microseconds (robustly parses UI text with units)."""
        try:
            # Prefer UI field if present; it may contain units like "10000.0 μs"
            if self.exposure_edit and hasattr(self.exposure_edit, 'text'):
                txt = str(self.exposure_edit.text())
                m = re.search(r"([0-9]+(?:\.[0-9]+)?)", txt)
                if m:
                    val = float(m.group(1))
                    return int(round(val))
            # Fallback to camera stream getter
            if self.camera_stream and hasattr(self.camera_stream, 'get_exposure'):
                return int(self.camera_stream.get_exposure())
            # As a last resort, try cached attribute
            if self.camera_stream and hasattr(self.camera_stream, 'current_exposure'):
                return int(self.camera_stream.current_exposure)
            return 0
        except Exception:
            logging.error("Failed to get exposure value", exc_info=True)
            return 0
            
    def set_exposure_value(self, value):
        """Set exposure value"""
        try:
            value = int(value)
            # Update UI
            if self.exposure_edit:
                self.exposure_edit.setText(str(value))
            
            # Update camera
            if self.camera_stream and hasattr(self.camera_stream, 'set_exposure'):
                try:
                    self.camera_stream.set_exposure(value)
                except Exception as e:
                    logging.warning(f"Error setting exposure: {e}")
            
            return True
        except (ValueError, AttributeError) as e:
            logging.error(f"Failed to set exposure value: {e}")
            return False
            
    def get_gain_value(self):
        """L   y gi   tr    gain hi   n t   i"""
        try:
            if self.gain_edit:
                return float(self.gain_edit.text())
            elif self.camera_stream and hasattr(self.camera_stream, 'get_gain'):
                return self.camera_stream.get_gain()
            return 1.0
        except (ValueError, AttributeError):
            logging.error("Failed to get gain value", exc_info=True)
            return 1.0
            
    def set_gain_value(self, value):
        """     t gi   tr    gain"""
        try:
            value = float(value)
            conditional_print(f"DEBUG: [CameraManager] Setting gain value to {value}")
            # Update UI
            if self.gain_edit:
                self.gain_edit.setText(str(value))
            
            # Update camera
            if self.camera_stream and hasattr(self.camera_stream, 'set_gain'):
                # Try to apply to camera if it's available
                try:
                    success = self.camera_stream.set_gain(value)
                    if not success:
                        conditional_print(f"DEBUG: [CameraManager] Failed to set gain on camera stream")
                except Exception as e:
                    conditional_print(f"DEBUG: [CameraManager] Error setting gain: {e}")
            
            return True
        except (ValueError, AttributeError) as e:
            conditional_print(f"DEBUG: [CameraManager] Error setting gain value: {e}")
            logging.error(f"Failed to set gain value: {e}", exc_info=True)
            return False
            
    def get_ev_value(self):
        """L   y gi   tr    EV hi   n t   i"""
        try:
            if self.ev_edit:
                return float(self.ev_edit.text())
            elif self.camera_stream and hasattr(self.camera_stream, 'get_ev'):
                return self.camera_stream.get_ev()
            return 0.0
        except (ValueError, AttributeError):
            logging.error("Failed to get EV value", exc_info=True)
            return 0.0
            
    def set_ev_value(self, value):
        """     t gi   tr    EV"""
        try:
            # Handle tuple case (min, max, current)
            if isinstance(value, tuple) and len(value) >= 3:
                conditional_print(f"DEBUG: [CameraManager] Received EV tuple: {value}, using value[2]")
                value = value[2]  # Use the current value (third element)
                
            value = float(value)
            conditional_print(f"DEBUG: [CameraManager] Setting EV value to {value}")
            
            # Update UI
            if self.ev_edit:
                if hasattr(self.ev_edit, 'setValue'):
                    self.ev_edit.setValue(value)
                else:
                    self.ev_edit.setText(str(value))
            
            # Update camera
            if self.camera_stream and hasattr(self.camera_stream, 'set_ev'):
                # Try to apply to camera if it's available
                try:
                    success = self.camera_stream.set_ev(value)
                    if not success:
                        conditional_print(f"DEBUG: [CameraManager] Failed to set EV on camera stream")
                except Exception as e:
                    conditional_print(f"DEBUG: [CameraManager] Error setting EV: {e}")
            
            return True
        except (ValueError, AttributeError, TypeError) as e:
            conditional_print(f"DEBUG: [CameraManager] Error setting EV value: {e}")
            logging.error(f"Failed to set EV value: {e}", exc_info=True)
            return False
            return False
            
    def is_auto_exposure(self):
        """Ki   m tra xem c     ang     ch          auto exposure kh  ng"""
        return self._is_auto_exposure
        
    def set_settings_controls_enabled(self, enabled):
        """B   t/t   t c  c control settings (exposure, gain, ev)"""
        if self.exposure_edit:
            self.exposure_edit.setEnabled(enabled)
        if self.gain_edit:
            self.gain_edit.setEnabled(enabled)
        if self.ev_edit:
            self.ev_edit.setEnabled(enabled)
        
    def setup_camera_param_signals(self):
        """K   t n   i c  c signal v   slot cho c  c tham s    camera"""
        # Exposure - ch    d  ng edit box
        if self.exposure_edit:
            if hasattr(self.exposure_edit, 'valueChanged'):  # QDoubleSpinBox
                self.exposure_edit.valueChanged.connect(self.on_exposure_edit_changed)
            else:  # QLineEdit fallback
                self.exposure_edit.editingFinished.connect(self.on_exposure_edit_changed)
        # Gain
        if self.gain_edit:
            if hasattr(self.gain_edit, 'valueChanged'):  # QDoubleSpinBox
                self.gain_edit.valueChanged.connect(self.on_gain_edit_changed)
            else:  # QLineEdit fallback
                self.gain_edit.editingFinished.connect(self.on_gain_edit_changed)
        # EV
        if self.ev_edit:
            if hasattr(self.ev_edit, 'valueChanged'):  # QDoubleSpinBox
                self.ev_edit.valueChanged.connect(self.on_ev_edit_changed)
            else:  # QLineEdit fallback
                self.ev_edit.editingFinished.connect(self.on_ev_edit_changed)
            
    def setup_frame_size_spinboxes(self, width_spinbox=None, height_spinbox=None):
        """
        Thi   t l   p c  c spinbox         i   u ch   nh k  ch th     c frame camera
        
        Args:
            width_spinbox: QSpinBox cho chi   u r   ng
            height_spinbox: QSpinBox cho chi   u cao
        """
        self.width_spinbox = width_spinbox
        self.height_spinbox = height_spinbox
        
        if self.width_spinbox:
            # C   u h  nh spinbox chi   u r   ng
            self.width_spinbox.setMinimum(64)
            self.width_spinbox.setMaximum(1456)
            self.width_spinbox.setValue(640)  # Gi   tr    m   c      nh
            self.width_spinbox.setSuffix(" px")
            self.width_spinbox.valueChanged.connect(self.on_frame_size_changed)
            
        if self.height_spinbox:
            # C   u h  nh spinbox chi   u cao
            self.height_spinbox.setMinimum(64)
            self.height_spinbox.setMaximum(1088)
            self.height_spinbox.setValue(480)  # Gi   tr    m   c      nh
            self.height_spinbox.setSuffix(" px")
            self.height_spinbox.valueChanged.connect(self.on_frame_size_changed)
    
    def on_frame_size_changed(self):
        """X    l   khi k  ch th     c frame thay      i"""
        if self.width_spinbox and self.height_spinbox and self.camera_stream:
            width = self.width_spinbox.value()
            height = self.height_spinbox.value()
            self.camera_stream.set_frame_size(width, height)
    
    def get_frame_size(self):
        """L   y k  ch th     c frame hi   n t   i"""
        if self.camera_stream:
            return self.camera_stream.get_frame_size()
        return (640, 480)  # M   c      nh
    
    def set_frame_size(self, width, height):
        """     t k  ch th     c frame v   c   p nh   t UI"""
        # C   p nh   t spinboxes
        if self.width_spinbox:
            self.width_spinbox.setValue(width)
        if self.height_spinbox:
            self.height_spinbox.setValue(height)
        
        # C   p nh   t camera stream
        if self.camera_stream:
            self.camera_stream.set_frame_size(width, height)
            
    def set_exposure(self, value):
        """     t gi   tr    ph  i s  ng cho camera"""
        if self.exposure_edit:
            # Hi   n th    tr   c ti   p gi   tr    microseconds
            if hasattr(self.exposure_edit, 'setValue'):  # QDoubleSpinBox
                self.exposure_edit.setValue(value)
            else:  # QLineEdit fallback
                self.exposure_edit.setText(str(value))
        if hasattr(self.camera_stream, 'set_exposure'):
            self.camera_stream.set_exposure(value)

    def set_gain(self, value):
        """     t gi   tr    gain cho camera"""
        if self.gain_edit:
            if hasattr(self.gain_edit, 'setValue'):  # QDoubleSpinBox
                self.gain_edit.setValue(float(value))
            else:  # QLineEdit fallback
                self.gain_edit.setText(str(value))
        if hasattr(self.camera_stream, 'set_gain'):
            self.camera_stream.set_gain(value)

    def set_ev(self, value):
        """     t gi   tr    EV cho camera"""
        try:
            # Check if value is a tuple and extract current value
            if isinstance(value, tuple) and len(value) >= 3:
                conditional_print(f"DEBUG: [CameraManager] Received EV tuple: {value}, using value[2]")
                value = value[2]  # Use the current value (third element)
                
            # Convert to float for UI
            ev_value = float(value)
            
            if self.ev_edit:
                if hasattr(self.ev_edit, 'setValue'):  # QDoubleSpinBox
                    self.ev_edit.setValue(ev_value)
                else:  # QLineEdit fallback
                    self.ev_edit.setText(str(ev_value))
                    
            if hasattr(self.camera_stream, 'set_ev'):
                self.camera_stream.set_ev(ev_value)
                
        except (ValueError, TypeError) as e:
            conditional_print(f"DEBUG: [CameraManager] Error in set_ev: {e}")
            # Default to 0.0 if conversion fails
            if self.ev_edit and hasattr(self.ev_edit, 'setValue'):
                self.ev_edit.setValue(0.0)

    def on_exposure_edit_changed(self):
        """X    l   khi ng     i d  ng thay      i gi   tr    exposure trong spinbox - ch    l  u v  o pending"""
        conditional_print(f"DEBUG: on_exposure_edit_changed called")
        try:
            if self.exposure_edit:
                # Get value from spinbox (microseconds) - kh  ng c   n convert
                if hasattr(self.exposure_edit, 'value'):  # QDoubleSpinBox
                    value_us = self.exposure_edit.value()
                else:  # QLineEdit fallback
                    value_us = float(self.exposure_edit.text())
                
                conditional_print(f"DEBUG: New exposure value: {value_us}   s")
                conditional_print(f"DEBUG: Manual mode: {not self._is_auto_exposure}")
                
                # L  u tr   c ti   p gi   tr    microseconds v  o pending settings
                self._pending_exposure_settings['exposure'] = value_us
                conditional_print(f"DEBUG: Saved to pending settings")

                # Instant apply:   p d   ng ngay khi     manual mode       ng     i d  ng th   y hi   u    ng t   c th   i
                # Ch    apply khi _instant_apply b   t v   kh  ng     auto-exposure
                try:
                    self._apply_setting_if_manual('exposure', value_us)
                    conditional_print(f"DEBUG: Instant-applied exposure to camera (manual mode)")
                except Exception as e:
                    conditional_print(f"DEBUG: Failed instant apply exposure: {e}")
                
                # Notify settings manager about the change for synchronization
                if self.settings_manager:
                    self.settings_manager.mark_page_changed('camera')
                    # Optionally trigger immediate sync
                    # self.settings_manager.sync_settings_across_pages()
                
        except (ValueError, AttributeError) as e:
            conditional_print(f"DEBUG: Error in exposure edit changed: {e}")
    
    def set_settings_manager(self, settings_manager):
        """Set reference to settings manager for synchronization"""
        self.settings_manager = settings_manager
        conditional_print(f"DEBUG: CameraManager linked to SettingsManager")

    def on_gain_edit_changed(self, value=None):
        """X    l   khi ng     i d  ng thay      i gi   tr    gain"""
        try:
            if self.gain_edit:
                if value is None:
                    # Tr     ng h   p editingFinished (QLineEdit)
                    value = float(self.gain_edit.text())
                # value             c truy   n tr   c ti   p n   u s    ki   n l   valueChanged (QDoubleSpinBox)
                
                if hasattr(self.camera_stream, 'set_gain'):
                    self.camera_stream.set_gain(value)
        except (ValueError, AttributeError):
            pass

    def on_ev_edit_changed(self, value=None):
        """X    l   khi ng     i d  ng thay      i gi   tr    EV"""
        try:
            if self.ev_edit:
                if value is None:
                    # Tr     ng h   p editingFinished (QLineEdit)
                    value = float(self.ev_edit.text())
                # value             c truy   n tr   c ti   p n   u s    ki   n l   valueChanged (QDoubleSpinBox)
                
                if hasattr(self.camera_stream, 'set_ev'):
                    self.camera_stream.set_ev(value)
        except (ValueError, AttributeError):
            pass

    def update_camera_params_from_camera(self):
        """C   p nh   t c  c tham s    t    camera hi   n t   i"""
        if not self.camera_stream:
            return
            
        # L   y gi   tr    th   c t    t    camera n   u c   API
        if hasattr(self.camera_stream, 'get_exposure'):
            exposure = self.camera_stream.get_exposure()
            conditional_print(f"DEBUG: Got exposure from camera: {exposure}")
            if exposure:  # Ch    update n   u c   gi   tr    h   p l   
                if self.exposure_edit:
                    if hasattr(self.exposure_edit, 'setValue'):
                        self.exposure_edit.setValue(float(exposure))
                        conditional_print(f"DEBUG: Set exposure in UI: {exposure}")
                    else:
                        self.exposure_edit.setText(str(exposure))
                        
        if hasattr(self.camera_stream, 'get_gain'):
            try:
                gain = self.camera_stream.get_gain()
                conditional_print(f"DEBUG: Got gain from camera: {gain}")
                if gain is not None:
                    self.set_gain(gain)
            except Exception as e:
                conditional_print(f"DEBUG: [CameraManager] Error getting gain: {e}")
                
        if hasattr(self.camera_stream, 'get_ev'):
            try:
                ev = self.camera_stream.get_ev()
                conditional_print(f"DEBUG: Got EV from camera: {ev}")
                if ev is not None:
                    self.set_ev(ev)
            except Exception as e:
                conditional_print(f"DEBUG: [CameraManager] Error getting/setting EV: {e}")
            
    def _show_camera_error(self, message):
        """Show camera error message to user"""
        try:
            from PyQt5.QtWidgets import QMessageBox
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("Camera Error")
            msg_box.setText(f"Camera Error: {message}")
            msg_box.setInformativeText("Please check camera connection and try again.")
            msg_box.exec_()
        except Exception as e:
            conditional_print(f"DEBUG: [CameraManager] Error showing message box: {e}")
    
    def toggle_live_camera(self, checked):
        """B   t/t   t ch          camera tr   c ti   p"""
        conditional_print(f"DEBUG: [CameraManager] toggle_live_camera called with checked={checked}")
        # Y  u c   u c   Camera Source trong workflow tr     c khi b   t camera        
        if not self.camera_stream:
            conditional_print(f"DEBUG: [CameraManager] No camera stream available")
            return False
            
        try:
            if checked:
                conditional_print(f"DEBUG: [CameraManager] Starting live camera...")
                
                # Process pending events to keep UI responsive
                QApplication.processEvents()
                
                # Try with both method names for compatibility
                success = False
                try:
                    # First try direct method access - this helps with finding the true error
                    try:
                        conditional_print(f"DEBUG: [CameraManager] First attempt - direct start_online_camera()")
                        success = self.camera_stream.start_online_camera()
                    except AttributeError as e:
                        conditional_print(f"DEBUG: [CameraManager] AttributeError: {e}")
                        # Fall back to other method name
                        conditional_print(f"DEBUG: [CameraManager] Falling back to start_live_camera()")
                        try:
                            success = self.camera_stream.start_live_camera()
                        except AttributeError:
                            # Implement method directly if needed
                            conditional_print(f"DEBUG: [CameraManager] Both methods missing - implementing inline")
                            success = self._implement_start_live()
                except Exception as e:
                    conditional_print(f"DEBUG: [CameraManager] Error starting camera: {e}")
                    success = False
                
                # Process events again after camera start
                QApplication.processEvents()
                
                if success:
                    conditional_print(f"DEBUG: [CameraManager] Live camera started successfully")
                    # Sync camera params sau m   t ch  t delay       camera start ho  n to  n
                    from PyQt5.QtCore import QTimer
                    # Th    sync multiple times            m b   o camera      s   n s  ng
                    QTimer.singleShot(1000, self.update_camera_params_from_camera)  # 1s delay
                    QTimer.singleShot(2000, self.update_camera_params_from_camera)  # retry sau 2s
                    return True
                else:
                    conditional_print(f"DEBUG: [CameraManager] Failed to start live camera")
                    # Show error to user
                    self._show_camera_error("Failed to start live preview")
                    # Update UI to reflect failure
                    self.current_mode = None
                    self.update_camera_mode_ui()
                    return False
            else:
                conditional_print(f"DEBUG: [CameraManager] Stopping live camera...")
                
                # Process events before stop
                QApplication.processEvents()
                
                try:
                    # Preferred safe stop
                    try:
                        conditional_print(f"DEBUG: [CameraManager] Preferred stop - cancel_and_stop_live()")
                        self.camera_stream.cancel_and_stop_live()
                    except AttributeError as e:
                        conditional_print(f"DEBUG: [CameraManager] AttributeError cancel_and_stop_live: {e}")
                        if hasattr(self.camera_stream, 'cancel_all_and_flush'):
                            self.camera_stream.cancel_all_and_flush()
                        if hasattr(self.camera_stream, 'stop_live'):
                            self.camera_stream.stop_live()
                except Exception as e:
                    conditional_print(f"DEBUG: [CameraManager] Error stopping camera: {e}")
                
                # Process events after stop to ensure UI updates
                QApplication.processEvents()
                
                conditional_print(f"DEBUG: [CameraManager] Live camera stopped")
                return True
                
        except Exception as e:
            conditional_print(f"DEBUG: [CameraManager] Error in toggle_live_camera: {e}")
            # Show error to user
            self._show_camera_error(f"Camera operation failed: {str(e)}")
            # Reset state on error
            self.current_mode = None
            self.update_camera_mode_ui()
            return False
            
    def set_auto_exposure_mode(self):
        """     t ch          t         ng ph  i s  ng"""
        self._is_auto_exposure = True
        if hasattr(self.camera_stream, 'set_auto_exposure'):
            self.camera_stream.set_auto_exposure(True)
        
        # Disable c  c widget   i   u ch   nh ph  i s  ng
        if self.exposure_edit:
            self.exposure_edit.setEnabled(False)
        if self.gain_edit:
            self.gain_edit.setEnabled(False)
        if self.ev_edit:
            self.ev_edit.setEnabled(False)
        if self.ev_edit:
            self.ev_edit.setEnabled(False)
            
    def set_manual_exposure_mode(self):
        """     t ch          ph  i s  ng th    c  ng
        
        IMPORTANT: Nếu có frame đang xử lý, flush ngay để chuyển sang manual mode
        Không đợi frame hoàn thành, đảm bảo UI responsive
        
        NHƯNG: Nếu đang trong on_trigger_camera_mode_clicked(), skip flush (đã flush ở đó rồi)
        """
        self._is_auto_exposure = False
        
        # FLUSH PENDING FRAME NẾU CÓ (và không phải lúc mode changing)
        # Không đợi frame hiện tại hoàn thành, áp dụng auto exposure = False ngay
        if not self._mode_changing:  # Skip flush if mode is already changing
            if self.camera_stream:
                if hasattr(self.camera_stream, 'fifo_queue') and self.camera_stream.fifo_queue:
                    queue_size = len(self.camera_stream.fifo_queue.queue) if hasattr(self.camera_stream.fifo_queue, 'queue') else 0
                    if queue_size > 0:
                        conditional_print(f"DEBUG: [CameraManager] Frame pending detected ({queue_size} frames), flushing to switch to manual exposure mode")
                        if hasattr(self.camera_stream, 'cancel_all_and_flush'):
                            self.camera_stream.cancel_all_and_flush()
        else:
            conditional_print(f"DEBUG: [CameraManager] Skipping flush during mode change (already flushed)")
        
        if hasattr(self.camera_stream, 'set_auto_exposure'):
            self.camera_stream.set_auto_exposure(False)
            conditional_print(f"DEBUG: Set camera auto exposure to False")
        
        # Enable c  c widget   i   u ch   nh ph  i s  ng
        if self.exposure_edit:
            self.exposure_edit.setEnabled(True)
            conditional_print(f"DEBUG: Enabled exposure_edit")
        if self.gain_edit:
            self.gain_edit.setEnabled(True)
        if self.ev_edit:
            self.ev_edit.setEnabled(True)
            
        conditional_print(f"DEBUG: Manual exposure mode set, _is_auto_exposure = {self._is_auto_exposure}")
            
    @pyqtSlot(int)
    def update_focus_value(self, value):
        """C   p nh   t gi   tr          s   c n  t tr  n thanh focusBar"""
        if self.focus_bar:
            self.focus_bar.setValue(value)
        
    @pyqtSlot(float)
    def update_fps_display(self, fps_value):
        """C   p nh   t gi   tr    FPS l  n LCD display"""
        if self.fps_num:
            self.fps_num.display(f"{fps_value:.1f}")
            
    def trigger_capture(self):
        """K  ch ho   t ch   p    nh kh  ng      ng b   """
        # B    qua ki   m tra Camera Source       cho ph  p ch   p    nh
        # m   kh  ng c   n th  m v  o source tr     c
        # Ng     i d  ng c   th    ch   p    nh tr     c khi th  m Camera Source v  o pipeline
            
        if self.camera_stream:
            conditional_print(f"DEBUG: [CameraManager] Triggering capture asynchronously...")
            
            # Visual feedback - temporarily change button text
            if self.trigger_camera_btn and self.current_mode == 'trigger':
                original_text = self.trigger_camera_btn.text()
                self.trigger_camera_btn.setText("Capturing...")
                
                # Button v   n enabled       user c   th    nh   n Cancel n   u mu   n
                # Ch    disable n   u   ang x    l   capture      ng b   
                # self.trigger_camera_btn.setEnabled(False)
                
                # Kh  ng c  n chuy   n sang trigger mode n   a
                # Gi    nguy  n ch          hi   n t   i (live ho   c trigger)
                conditional_print(f"DEBUG: [CameraManager] Capturing in current mode: {self.current_mode}")
                
                # Apply job setting to camera stream
                if hasattr(self.camera_stream, 'set_job_enabled'):
                    self.camera_stream.set_job_enabled(self.job_enabled)
                
                # Sync current exposure setting before trigger
                self.sync_exposure_to_camera()
                
                # Trigger actual capture asynchronously - kh  ng block UI
                if hasattr(self.camera_stream, 'trigger_capture_async'):
                    success = self.camera_stream.trigger_capture_async()
                    if not success:
                        conditional_print(f"DEBUG: [CameraManager] Failed to start async trigger")
                        # Fallback to synchronous capture if async failed
                        if hasattr(self.camera_stream, 'trigger_capture'):
                            try:
                                self.camera_stream.trigger_capture()
                            except Exception as e:
                                conditional_print(f"DEBUG: [CameraManager] Error in synchronous trigger_capture: {e}")
                                self._show_camera_error(f"Error capturing image: {str(e)}")
                        else:
                            conditional_print(f"DEBUG: [CameraManager] No trigger_capture method available")
                            self._show_camera_error("Camera trigger feature is not available. Please update the camera module.")
                else:
                    # Fallback to old synchronous method if async not available
                    conditional_print(f"DEBUG: [CameraManager] Async trigger not available, using sync")
                    if hasattr(self.camera_stream, 'trigger_capture'):
                        try:
                            self.camera_stream.trigger_capture()
                        except Exception as e:
                            conditional_print(f"DEBUG: [CameraManager] Error in synchronous trigger_capture: {e}")
                            self._show_camera_error(f"Error capturing image: {str(e)}")
                    else:
                        conditional_print(f"DEBUG: [CameraManager] No trigger_capture method available")
                        self._show_camera_error("Camera trigger feature is not available. Please update the camera module.")
                
                # Restore button after timeout n   u kh  ng c   ph   n h   i
                from PyQt5.QtCore import QTimer
                def restore_button():
                    if self.trigger_camera_btn and self.trigger_camera_btn.text() == "Capturing...":
                        self.trigger_camera_btn.setText(original_text)
                        # Update UI properly instead of just enabling
                        self.update_camera_mode_ui()
                
                # Set timeout d  i h  n (10 gi  y)       cho ph  p c   th   i gian ch    trigger
                QTimer.singleShot(10000, restore_button)
            else:
                # Direct trigger without UI feedback
                if hasattr(self.camera_stream, 'trigger_capture_async'):
                    try:
                        self.camera_stream.trigger_capture_async()
                    except Exception as e:
                        conditional_print(f"DEBUG: [CameraManager] Error in async trigger: {e}")
                        self._show_camera_error(f"Error capturing image: {str(e)}")
                elif hasattr(self.camera_stream, 'trigger_capture'):
                    try:
                        self.camera_stream.trigger_capture()
                    except Exception as e:
                        conditional_print(f"DEBUG: [CameraManager] Error in direct trigger: {e}")
                        self._show_camera_error(f"Error capturing image: {str(e)}")
                else:
                    conditional_print(f"DEBUG: [CameraManager] No trigger methods available")
                    self._show_camera_error("Camera trigger feature is not available. Please update the camera module.")
        else:
            conditional_print(f"DEBUG: [CameraManager] No camera stream available")
            self._show_camera_error("Camera is not available. Please check camera connection.")

    def sync_exposure_to_camera(self):
        """     ng b    h  a c  c th  ng s    exposure hi   n t   i t    UI v  o camera"""
        conditional_print(f"DEBUG: [CameraManager] Syncing exposure settings to camera")
        try:
            # L   y gi   tr    exposure t    UI
            if self.exposure_edit:
                try:
                    if hasattr(self.exposure_edit, 'value'):
                        exposure_value = self.exposure_edit.value()
                    else:
                        exposure_value = int(self.exposure_edit.text())
                    
                    conditional_print(f"DEBUG: [CameraManager] Syncing exposure value: {exposure_value}")
                    if hasattr(self.camera_stream, 'set_exposure'):
                        self.camera_stream.set_exposure(exposure_value)
                except (ValueError, AttributeError) as e:
                    conditional_print(f"DEBUG: [CameraManager] Error getting exposure value from UI: {e}")
            
            # L   y gi   tr    gain t    UI
            if self.gain_edit:
                try:
                    if hasattr(self.gain_edit, 'value'):
                        gain_value = self.gain_edit.value()
                    else:
                        gain_value = float(self.gain_edit.text())
                    
                    conditional_print(f"DEBUG: [CameraManager] Syncing gain value: {gain_value}")
                    if hasattr(self.camera_stream, 'set_gain'):
                        self.camera_stream.set_gain(gain_value)
                except (ValueError, AttributeError) as e:
                    conditional_print(f"DEBUG: [CameraManager] Error getting gain value from UI: {e}")
            
            # L   y gi   tr    EV t    UI
            if self.ev_edit:
                try:
                    if hasattr(self.ev_edit, 'value'):
                        ev_value = self.ev_edit.value()
                    else:
                        ev_value = float(self.ev_edit.text())
                    
                    conditional_print(f"DEBUG: [CameraManager] Syncing EV value: {ev_value}")
                    if hasattr(self.camera_stream, 'set_ev'):
                        self.camera_stream.set_ev(ev_value)
                except (ValueError, AttributeError) as e:
                    conditional_print(f"DEBUG: [CameraManager] Error getting EV value from UI: {e}")
            
            #      ng b    ch          auto exposure
            if hasattr(self.camera_stream, 'set_auto_exposure'):
                conditional_print(f"DEBUG: [CameraManager] Syncing auto exposure: {self._is_auto_exposure}")
                self.camera_stream.set_auto_exposure(self._is_auto_exposure)
                
            return True
        except Exception as e:
            conditional_print(f"DEBUG: [CameraManager] Error syncing exposure settings: {e}")
            return False

    def set_trigger_mode(self, enabled):
        """
        Set trigger mode in camera using async thread to prevent UI blocking
        
        IMPORTANT: Nếu có frame đang xử lý, flush ngay để chuyển mode
        Không đợi frame hoàn thành, đảm bảo UI responsive
        
        Args:
            enabled: True to enable trigger mode, False to disable
        
        Returns:
            True if operation started successfully, False otherwise
        """
        try:
            # FLUSH PENDING FRAME NẾU CÓ
            # Khi chuyển mode, không đợi frame hiện tại hoàn thành
            if self.camera_stream:
                if hasattr(self.camera_stream, 'fifo_queue') and self.camera_stream.fifo_queue:
                    queue_size = len(self.camera_stream.fifo_queue.queue) if hasattr(self.camera_stream.fifo_queue, 'queue') else 0
                    if queue_size > 0:
                        mode_name = "trigger" if enabled else "live"
                        conditional_print(f"DEBUG: [CameraManager] Frame pending detected ({queue_size} frames), flushing to switch to {mode_name} mode")
                        if hasattr(self.camera_stream, 'cancel_all_and_flush'):
                            self.camera_stream.cancel_all_and_flush()
            
            # Sync current exposure setting to camera before changing trigger mode
            if self.camera_stream and self.exposure_edit:
                try:
                    exposure_value = self.get_exposure_value()
                    self.camera_stream.set_exposure(exposure_value)
                except Exception:
                    pass  # Continue with mode change even if exposure sync fails
            
            # Update UI first for immediate feedback
            if enabled:
                self.current_mode = 'trigger'
                if self.trigger_camera_mode:
                    self.trigger_camera_mode.setChecked(True)
                if self.live_camera_mode:
                    self.live_camera_mode.setChecked(False)
            else:
                self.current_mode = 'live'
                if self.trigger_camera_mode:
                    self.trigger_camera_mode.setChecked(False)
                if self.live_camera_mode:
                    self.live_camera_mode.setChecked(True)
                    
            # CRITICAL: Đảm bảo nút trigger được vô hiệu hóa đúng cách khi chuyển sang live mode
            if not enabled and self.trigger_camera_btn:
                # Ngay lập tức vô hiệu hóa nút trigger khi chuyển sang chế độ live
                self.trigger_camera_btn.setEnabled(False)
                self.trigger_camera_btn.setProperty("forcedDisabled", True)
                self.trigger_camera_btn.setStyleSheet("background-color: #cccccc; color: #888888;")  # Gray when disabled
                self.trigger_camera_btn.repaint()  # Force immediate UI update
                conditional_print(f"DEBUG: [CameraManager] Immediately disabled trigger button when switching to live mode")
            
            # Update camera hardware in background thread to prevent UI blocking
            if self.camera_stream and hasattr(self.camera_stream, 'set_trigger_mode'):
                # Stop previous operation thread if running
                if self.operation_thread and self.operation_thread.isRunning():
                    self.operation_thread.wait()
                
                # Start new operation thread
                self.operation_thread = CameraOperationThread(
                    self.camera_stream, 'set_trigger_mode', enabled
                )
                self.operation_thread.operation_completed.connect(self._on_trigger_mode_completed)
                self.operation_thread.start()
            
            # Cập nhật toàn bộ UI CHÍNH THỨC sau khi đã thiết lập trạng thái
            self.update_camera_mode_ui()
            return True
        except Exception as e:
            logging.error(f"Error in set_trigger_mode: {e}")
            return False
    
    def _on_trigger_mode_completed(self, success, message):
        """Handle completion of trigger mode change operation"""
        if not success:
            logging.warning(f"Trigger mode operation failed: {message}")
            # Hiển thị thông báo lỗi cho người dùng nếu cần
            self._show_camera_error(f"Failed to change camera mode: {message}")
        
        # Luôn cập nhật lại UI để đảm bảo UI được hiển thị đúng trạng thái
        # Điều này đặc biệt quan trọng nếu hardware mode change thất bại
        try:
            current_mode = self.current_mode if self.current_mode else 'live'
            conditional_print(f"DEBUG: [CameraManager] Trigger mode operation completed, refreshing UI for mode: {current_mode}")
            
            # Đặc biệt đảm bảo nút trigger bị vô hiệu hóa trong chế độ live
            if current_mode == 'live' and self.trigger_camera_btn:
                self.trigger_camera_btn.setEnabled(False)
                self.trigger_camera_btn.setStyleSheet("background-color: #cccccc; color: #888888;")  # Gray when disabled
                self.trigger_camera_btn.repaint()  # Force immediate UI update
            
            # Cập nhật toàn bộ UI
            self.update_camera_mode_ui()
        except Exception as e:
            logging.error(f"Error updating UI after trigger mode completion: {e}")
    
    def set_format_async(self, pixel_format):
        """
        Set camera format using async thread to prevent UI blocking
        
        Args:
            pixel_format: Format string (e.g., 'RGB888', 'BGR888')
        
        Returns:
            True if operation started successfully, False otherwise
        """
        try:
            if self.camera_stream and hasattr(self.camera_stream, 'set_format'):
                # Stop previous operation thread if running
                if self.operation_thread and self.operation_thread.isRunning():
                    self.operation_thread.wait()
                
                # Start new operation thread
                self.operation_thread = CameraOperationThread(
                    self.camera_stream, 'set_format', pixel_format
                )
                self.operation_thread.operation_completed.connect(self._on_format_completed)
                self.operation_thread.start()
                return True
            return False
        except Exception as e:
            logging.error(f"Error in set_format_async: {e}")
            return False
    
    def _on_format_completed(self, success, message):
        """Handle completion of format change operation"""
        if not success:
            logging.warning(f"Format operation failed: {message}")
        
        # IMPORTANT: Flush any pending frames with old format
        # This ensures next frame will be with NEW format
        if self.camera_stream and hasattr(self.camera_stream, 'cancel_all_and_flush'):
            conditional_print(f"DEBUG: [CameraManager] Format change completed, flushing old frames to apply new format")
            self.camera_stream.cancel_all_and_flush()
        
        # Refresh display after format change
        if self.camera_view and hasattr(self.camera_view, 'refresh_display_with_new_format'):
            self.camera_view.refresh_display_with_new_format()
            
    def rotate_left(self):
        """Xoay camera sang tr  i"""
        if self.camera_view:
            self.camera_view.rotate_left()
            
    def rotate_right(self):
        """Xoay camera sang ph   i"""
        if self.camera_view:
            self.camera_view.rotate_right()
            
    # Zoom functionality is now fully implemented in CameraView
    # CameraManager just acts as a pass-through
    
    def zoom_in(self):
        """
        Simple pass-through to camera_view's zoom_in
        
        This method acts as a proxy to the actual zoom implementation in CameraView.
        
        Zoom Flow:
        1. MainWindow button click -> CameraManager.zoom_in
        2. CameraManager.zoom_in -> CameraView.zoom_in
        3. CameraView.zoom_in -> CameraView._apply_zoom (with throttling)
        """
        conditional_print(f"DEBUG: [CameraManager] zoom_in called")
        
        # Check if camera_view is available
        if not self.camera_view:
            conditional_print(f"DEBUG: [CameraManager] zoom_in failed - camera_view is None")
            return
            
        # Direct approach - call camera_view.zoom_in directly
        try:
            self.camera_view.zoom_in()
        except Exception as e:
            conditional_print(f"DEBUG: [CameraManager] Error calling camera_view.zoom_in(): {e}")
            
    def zoom_out(self):
        """
        Simple pass-through to camera_view's zoom_out
        
        This method acts as a proxy to the actual zoom implementation in CameraView.
        
        Zoom Flow:
        1. MainWindow button click -> CameraManager.zoom_out
        2. CameraManager.zoom_out -> CameraView.zoom_out
        3. CameraView.zoom_out -> CameraView._apply_zoom (with throttling)
        """
        conditional_print(f"DEBUG: [CameraManager] zoom_out called")
        
        # Check if camera_view is available
        if not self.camera_view:
            conditional_print(f"DEBUG: [CameraManager] zoom_out failed - camera_view is None")
            return
        
        # Direct approach - call camera_view.zoom_out directly
        try:
            self.camera_view.zoom_out()
        except Exception as e:
            conditional_print(f"DEBUG: [CameraManager] Error calling camera_view.zoom_out(): {e}")
            
    def reset_view(self):
        """
        Simple pass-through to camera_view's reset_view
        
        This method acts as a proxy to the actual reset implementation in CameraView.
        
        Reset Flow:
        1. MainWindow button click -> CameraManager.reset_view
        2. CameraManager.reset_view -> CameraView.reset_view
        """
        conditional_print(f"DEBUG: [CameraManager] reset_view called")
        
        # Check if camera_view is available
        if not self.camera_view:
            conditional_print(f"DEBUG: [CameraManager] reset_view failed - camera_view is None")
            return
        
        # Direct approach - call camera_view.reset_view directly
        try:
            self.camera_view.reset_view()
        except Exception as e:
            conditional_print(f"DEBUG: [CameraManager] Error calling camera_view.reset_view(): {e}")
            
    def handle_resize_event(self):
        """X    l   s    ki   n khi c   a s    thay      i k  ch th     c"""
        if self.camera_view:
            self.camera_view.handle_resize_event()
    
    # ============ CAMERA MODE HANDLERS ============
    
    def start_live_camera(self, force_mode_change=True):
        """Start live camera mode (for programmatic access)
        
        Args:
            force_mode_change: If False, preserve current camera mode and stream state
        """
        # Check if camera is already running and we shouldn't force mode change
        if self.camera_stream and self.camera_stream.is_running() and not force_mode_change:
            # Camera is already running, just update UI without changing stream
            logging.info("CameraManager: Camera already running, preserving current mode and stream")
            self.update_camera_mode_ui()
            # Refresh display mode
            if hasattr(self.camera_view, 'set_display_mode'):
                self.camera_view.set_display_mode("camera")
            return True
            
        # Arm and wait: mark waiting for first frame
        self._waiting_first_frame = True
        
        # Only force LIVE mode if explicitly requested
        if force_mode_change:
            # Force LIVE mode when starting via onlineCamera/start_live
            try:
                if self.trigger_camera_mode:
                    self.trigger_camera_mode.blockSignals(True)
                    self.trigger_camera_mode.setChecked(False)
                    self.trigger_camera_mode.blockSignals(False)
            except Exception:
                pass
            try:
                if self.live_camera_mode:
                    self.live_camera_mode.blockSignals(True)
                    self.live_camera_mode.setChecked(True)
                    self.live_camera_mode.blockSignals(False)
            except Exception:
                pass
            # Ensure hardware trigger is disabled for live
            if self.camera_stream and hasattr(self.camera_stream, 'set_trigger_mode'):
                try:
                    self.camera_stream.set_trigger_mode(False)
                except Exception:
                    pass

        # Start camera only if not running
        if self.camera_stream and not self.camera_stream.is_running():
            try:
                # start_online_camera() will preserve current trigger mode automatically
                conditional_print(f"DEBUG: [CameraManager] Starting camera")
                success = self.camera_stream.start_online_camera()
                
                if success:
                    # Only update mode if force_mode_change is True
                    if force_mode_change:
                        #      m b   o ch          hi   n t   i v   UI        c      ng b   
                        self.current_mode = 'live'
                        
                        #      m b   o c  c n  t ch          camera        c c   p nh   t     ng
                        if self.live_camera_mode:
                            self.live_camera_mode.blockSignals(True)
                            self.live_camera_mode.setChecked(True)
                            self.live_camera_mode.blockSignals(False)
                        if self.trigger_camera_mode:
                            self.trigger_camera_mode.blockSignals(True)
                            self.trigger_camera_mode.setChecked(False)
                            self.trigger_camera_mode.blockSignals(False)
                    
                    # C   p nh   t UI
                    self.update_camera_mode_ui()
                    
                    # Enable job execution when camera is started
                    logging.info("Enabling job execution in start_live_camera")
                    self.job_enabled = True
                    if hasattr(self.camera_stream, 'set_job_enabled'):
                        self.camera_stream.set_job_enabled(True)
                    
                    # Default to Camera Source display (no manual selection required)
                    # Still refresh combo for internal consistency, but ignore its value
                    self.refresh_source_output_combo()
                    current_data = "camera"
                    if hasattr(self.camera_view, 'set_display_mode'):
                        self.camera_view.set_display_mode("camera")
                    # Ensure user drawings/overlays are visible by default
                    try:
                        if hasattr(self.camera_view, 'show_detection_overlay'):
                            self.camera_view.show_detection_overlay = True
                        if hasattr(self.camera_view, 'update_detection_areas_visibility'):
                            self.camera_view.update_detection_areas_visibility()
                    except Exception:
                        pass
                        
                    conditional_print(f"DEBUG: [CameraManager] Live camera started successfully with display mode:", current_data)
                    return True
                else:
                    conditional_print(f"DEBUG: [CameraManager] Failed to start live camera")
                    return False
            except Exception as e:
                conditional_print(f"DEBUG: [CameraManager] Exception starting live camera: {e}")
                return False
        else:
            # Camera stream not available
            logging.warning("CameraManager: Camera stream not available")
            return False
    
    def on_live_camera_clicked(self):
        """Handle click Live Camera button (onlineCamera)
        
        Behavior depends on camera mode:
        - Live Mode: Start continuous camera streaming
        - Trigger Mode: Keep current mode (don't force continuous)
        """
        try:
            if self.live_camera_btn and self.live_camera_btn.isChecked():
                self._waiting_first_frame = True
        except Exception:
            pass
        
        current_checked = self.live_camera_btn.isChecked() if self.live_camera_btn else True
        conditional_print(f"DEBUG: [CameraManager] Live Camera button clicked, checked: {current_checked}")
        
        # Kiểm tra xem có đang edit Camera Source không
        editing_camera_tool = self._is_editing_camera_tool()
        conditional_print(f"DEBUG: [CameraManager] Editing Camera Source: {editing_camera_tool}")
        
        if not self.camera_stream:
            conditional_print(f"DEBUG: [CameraManager] No camera stream available")
            if self.live_camera_btn:
                self.live_camera_btn.setChecked(False)
            return
        
        # Lấy chế độ camera hiện tại
        current_mode = self.current_mode if self.current_mode else 'live'
        conditional_print(f"DEBUG: [CameraManager] Current camera mode: {current_mode}")
            
        if current_checked:
            # START camera based on mode
            conditional_print(f"DEBUG: [CameraManager] Starting camera stream...")
            try:
                if current_mode == 'live':
                    # LIVE MODE: Start continuous streaming
                    conditional_print(f"DEBUG: [CameraManager] LIVE MODE: Starting continuous camera stream")
                    success = self._start_camera_stream_continuous()
                else:
                    # TRIGGER MODE: Hoạt động chế độ hiện tại (giữ trigger mode, không ép continuous)
                    conditional_print(f"DEBUG: [CameraManager] TRIGGER MODE: Keeping current trigger mode")
                    success = self._start_camera_stream()
                
                if success:
                    conditional_print(f"DEBUG: [CameraManager] Camera stream started successfully")
                    if editing_camera_tool:
                        conditional_print(f"DEBUG: [CameraManager] Running in Camera Source edit mode - live preview")
                else:
                    conditional_print(f"DEBUG: [CameraManager] Failed to start camera stream")
                    if self.live_camera_btn:
                        self.live_camera_btn.setChecked(False)
            except Exception as e:
                conditional_print(f"DEBUG: [CameraManager] Error starting camera stream: {e}")
                if self.live_camera_btn:
                    self.live_camera_btn.setChecked(False)
        else:
            # STOP camera stream
            conditional_print(f"DEBUG: [CameraManager] Stopping camera stream...")
            try:
                success = self._stop_camera_stream()
                if success:
                    conditional_print(f"DEBUG: [CameraManager] Camera stream stopped successfully")
                else:
                    conditional_print(f"DEBUG: [CameraManager] Failed to stop camera stream")
            except Exception as e:
                conditional_print(f"DEBUG: [CameraManager] Error stopping camera stream: {e}")
        
        # Update UI to reflect current streaming state (not mode)
        self.update_camera_mode_ui()
    
    def _start_camera_stream_continuous(self):
        """Start continuous camera streaming in LIVE MODE
        
        This method ensures camera runs in continuous mode when "Live Camera" is clicked
        in live mode. It mimics testjob.py's simple streaming behavior.
        """
        if not self.camera_stream:
            return False
            
        try:
            # Check if camera is already streaming
            if hasattr(self.camera_stream, 'is_live') and self.camera_stream.is_live:
                conditional_print(f"DEBUG: [CameraManager] Camera stream already running")
                return True
            
            # Ensure we're NOT in trigger mode - explicitly use continuous/live mode
            conditional_print(f"DEBUG: [CameraManager] Ensuring continuous live mode...")
            
            # Disable external trigger if it's enabled
            if hasattr(self.camera_stream, 'external_trigger_enabled') and self.camera_stream.external_trigger_enabled:
                conditional_print(f"DEBUG: [CameraManager] Disabling external trigger for continuous mode")
                if hasattr(self.camera_stream, 'set_trigger_mode'):
                    self.camera_stream.set_trigger_mode(False)
            
            # Start live preview stream (continuous)
            conditional_print(f"DEBUG: [CameraManager] Starting continuous live stream...")
            if hasattr(self.camera_stream, 'start_online_camera'):
                success = self.camera_stream.start_online_camera()
            elif hasattr(self.camera_stream, 'start_live'):
                success = self.camera_stream.start_live()
            elif hasattr(self.camera_stream, 'start_preview'):
                success = self.camera_stream.start_preview()
            else:
                print("ERROR: No live streaming method available")
                return False
            
            if success:
                conditional_print(f"DEBUG: [CameraManager] Continuous camera stream started successfully")
                
                # Enable job execution for frame processing
                self.job_enabled = True
                if hasattr(self.camera_stream, 'set_job_enabled'):
                    self.camera_stream.set_job_enabled(True)
                
                conditional_print(f"DEBUG: [CameraManager] Continuous camera stream started with job processing enabled")
                return True
            else:
                conditional_print(f"DEBUG: [CameraManager] Failed to start continuous camera stream")
                return False
                
        except Exception as e:
            conditional_print(f"DEBUG: [CameraManager] Exception starting continuous camera stream: {e}")
            return False
    
    def _start_camera_stream(self):
        """Start camera stream - keeps current mode (used in TRIGGER MODE)
        
        In trigger mode: Start camera but keep trigger configuration (don't force continuous)
        """
        if not self.camera_stream:
            return False
            
        try:
            # Check if camera is already streaming
            if hasattr(self.camera_stream, 'is_live') and self.camera_stream.is_live:
                conditional_print(f"DEBUG: [CameraManager] Camera stream already running")
                return True
            
            # Kiểm tra xem có đang edit Camera Source không
            editing_camera_tool = self._is_editing_camera_tool()
            
            # Xác định chế độ camera hiện tại
            current_mode = self.current_mode
            if current_mode is None:
                current_mode = 'live'
            
            # Lưu và in ra thông tin về trạng thái camera mode và edit mode
            conditional_print(f"DEBUG: [CameraManager] Starting stream with current mode: {current_mode}, edit mode: {editing_camera_tool}")
            
            # Start simple preview stream (like testjob.py)
            if hasattr(self.camera_stream, 'start_preview'):
                success = self.camera_stream.start_preview()
            else:
                # Fallback to start_online_camera if start_preview not available
                success = self.camera_stream.start_online_camera()
            
            if success:
                conditional_print(f"DEBUG: [CameraManager] Camera stream started successfully, edit mode: {editing_camera_tool}")
                
                # Nếu đang edit Camera Source, không cần kích hoạt job processing
                if editing_camera_tool:
                    # Vẫn cho phép hiển thị khung hình nhưng không chạy job
                    self.job_enabled = False
                    if hasattr(self.camera_stream, 'set_job_enabled'):
                        self.camera_stream.set_job_enabled(False)
                else:
                    # Enable job execution for frame processing khi không trong edit mode
                    self.job_enabled = True
                    if hasattr(self.camera_stream, 'set_job_enabled'):
                        self.camera_stream.set_job_enabled(True)
                conditional_print(f"DEBUG: [CameraManager] Camera stream started with job processing enabled")
                return True
            else:
                conditional_print(f"DEBUG: [CameraManager] Failed to start camera stream")
                return False
                
        except Exception as e:
            conditional_print(f"DEBUG: [CameraManager] Exception starting camera stream: {e}")
            return False
    
    def _stop_camera_stream(self):
        """Stop camera stream like testjob.py - simple stop without mode change"""
        if not self.camera_stream:
            return False
            
        try:
            # Disable job execution first
            self.job_enabled = False
            if hasattr(self.camera_stream, 'set_job_enabled'):
                self.camera_stream.set_job_enabled(False)
            
            # Stop stream
            if hasattr(self.camera_stream, 'stop_preview'):
                success = self.camera_stream.stop_preview()
            elif hasattr(self.camera_stream, 'stop_live'):
                success = self.camera_stream.stop_live()
            else:
                # Fallback to cancel_all_and_flush
                self.camera_stream.cancel_all_and_flush()
                success = True
            
            conditional_print(f"DEBUG: [CameraManager] Camera stream stopped")
            return success
            
        except Exception as e:
            conditional_print(f"DEBUG: [CameraManager] Exception stopping camera stream: {e}")
            return False
    
    def activate_capture_request(self):
        """Capture a single frame using capture_request()"""
        # Kiểm tra xem camera có đang hoạt động không hoặc đang edit CameraTool
        camera_is_running = False
        editing_camera_tool = self._is_editing_camera_tool()
        
        # Kiểm tra chế độ camera hiện tại - ưu tiên lấy từ camera_tool trước
        camera_tool = self.find_camera_tool()
        if camera_tool:
            current_mode = camera_tool.get_camera_mode()
        else:
            # Fallback to local mode with default
            current_mode = self.current_mode
            if current_mode is None:
                current_mode = 'live'
                
        # Kiểm tra và ngăn chặn kích hoạt khi ở chế độ live (trừ khi đang edit)
        if current_mode == 'live' and not editing_camera_tool:
            conditional_print(f"DEBUG: [CameraManager] Cannot trigger in LIVE mode (editing={editing_camera_tool})")
            return False
        
        if self.camera_stream:
            try:
                camera_is_running = (hasattr(self.camera_stream, 'is_running') and 
                                    self.camera_stream.is_running())
            except Exception:
                pass
        
        # Luôn cho phép kích hoạt capture khi đang edit Camera Source, bất kể chế độ nào
        if editing_camera_tool:
            # Khi đang edit Camera Source, luôn cho phép trigger
            # Nếu camera chưa chạy, thử bắt đầu camera trước
            if not camera_is_running and hasattr(self, '_start_camera_stream'):
                try:
                    conditional_print(f"DEBUG: [CameraManager] Auto-starting camera stream for capture in edit mode")
                    self._start_camera_stream()
                except Exception as e:
                    conditional_print(f"DEBUG: [CameraManager] Error auto-starting camera for edit mode capture: {e}")
        # Nếu không đang edit, chỉ capture khi camera đang chạy hoặc có thể start được
        elif not camera_is_running:
            conditional_print(f"DEBUG: [CameraManager] Camera is not running, trying to start for capture_request")
            # Try to start camera for capture_request
            if hasattr(self, '_start_camera_stream'):
                try:
                    self._start_camera_stream()
                except Exception as e:
                    conditional_print(f"DEBUG: [CameraManager] Error starting camera for capture: {e}")
                    return False
            
        # Use trigger_capture for frame capture
        try:
            if not self.camera_stream:
                conditional_print(f"DEBUG: [CameraManager] No camera stream available")
                return False
            
            # TIMING FIX: Send light trigger EXACTLY when trigger_capture is called
            # This ensures light has maximum time to stabilize before frame is available
            conditional_print(f"DEBUG: [CameraManager] Calling trigger_capture()")
            conditional_print(f"DEBUG: [CameraManager] Camera running: {camera_is_running}, Editing Camera Source: {editing_camera_tool}, Mode: {current_mode}")
            
            # TR1 already sent in on_trigger_camera_clicked() before delay trigger
            # No need to send again here - just capture the frame
            self.camera_stream.trigger_capture()
            
            # trigger_capture() emits frame_ready signal, so return success
            conditional_print(f"DEBUG: [CameraManager] Frame capture triggered successfully")
            return True
                
        except Exception as e:
            conditional_print(f"DEBUG: [CameraManager] Error in trigger_capture: {e}")
            self._show_camera_error(f"Error capturing frame: {str(e)}")
            
        return False
    
    def is_camera_running(self):
        """Kiểm tra xem camera có đang chạy hay không"""
        camera_running = False
        if self.camera_stream:
            try:
                camera_running = (hasattr(self.camera_stream, 'is_running') and 
                                 self.camera_stream.is_running())
            except Exception:
                pass
        return camera_running
        
    def on_trigger_camera_clicked(self):
        """Xử lý khi click Trigger Camera button - gửi lệnh triggerCamera qua TCP"""
        current_time = time.time()
        conditional_print(f"DEBUG: [CameraManager] Trigger camera button clicked at", current_time)
        
        # GUARD: Block if trigger is currently processing
        if getattr(self, '_trigger_processing', False):
            conditional_print(f"DEBUG: [CameraManager] BLOCKED: Trigger already processing, ignoring click")
            return
        
        # GUARD: Prevent rapid double-clicks
        # Check if last trigger was less than 500ms ago (increased to 500ms to prevent double execution)
        last_trigger = getattr(self, '_last_ui_trigger_time', 0.0)
        time_since_last = (current_time - last_trigger) * 1000  # Convert to ms
        if time_since_last < 500:  # Less than 500ms since last trigger
            conditional_print(f"DEBUG: [CameraManager] BLOCKED: Trigger clicked too fast ({time_since_last:.1f}ms since last). Ignoring.")
            return
        self._last_ui_trigger_time = current_time
        
        # Set processing flag to block subsequent clicks
        self._trigger_processing = True
        conditional_print(f"DEBUG: [CameraManager] SET _trigger_processing = True")
        
        # Kiểm tra nút có thực sự được kích hoạt hay không
        button_is_enabled = True
        if self.trigger_camera_btn and hasattr(self.trigger_camera_btn, 'isEnabled'):
            button_is_enabled = self.trigger_camera_btn.isEnabled()
            conditional_print(f"DEBUG: [CameraManager] Trigger button enabled state: {button_is_enabled}")
            
            # Force update của button state để đảm bảo UI hiển thị đúng
            if not button_is_enabled:
                self.trigger_camera_btn.setEnabled(False)
                self.trigger_camera_btn.repaint()
                self._trigger_processing = False
                return
        
        # Kiểm tra chế độ hiện tại - chỉ kích hoạt GPIO khi ở chế độ trigger
        camera_tool = self.find_camera_tool()
        current_mode = 'live'  # Default to live
        
        if camera_tool:
            current_mode = camera_tool.get_camera_mode()
        else:
            # Fallback to local mode
            current_mode = self.current_mode if self.current_mode else 'live'
            
        conditional_print(f"DEBUG: [CameraManager] Camera running: {self.is_camera_running()}, Editing Camera Source: {self._is_editing_camera_tool()}, Mode: {current_mode}")
            
        # Chỉ kích hoạt trigger khi ở chế độ trigger và nút được kích hoạt
        if current_mode == 'trigger' and button_is_enabled:
            # Disable trigger button to prevent multiple clicks during processing
            if self.trigger_camera_btn:
                self.trigger_camera_btn.setEnabled(False)
                self.trigger_camera_btn.repaint()
                conditional_print(f"DEBUG: [CameraManager] Trigger button DISABLED to prevent multiple clicks")

            # 🔄 Send TRIGGER command via TCP to Pico
            conditional_print(f"DEBUG: [CameraManager] Sending 'TRIGGER' command via TCP to Pico...")
            try:
                # Get tcp_controller from main_window
                if not hasattr(self.main_window, 'tcp_controller'):
                    conditional_print(f"DEBUG: [CameraManager] TCP controller not found in main_window")
                    self._trigger_processing = False
                    if self.trigger_camera_btn:
                        self.trigger_camera_btn.setEnabled(True)
                        self.trigger_camera_btn.repaint()
                    return
                
                tcp_controller = self.main_window.tcp_controller
                
                # Check if TCP connection is active
                if not tcp_controller.tcp_controller.is_connected:
                    conditional_print(f"DEBUG: [CameraManager] TCP connection not active")
                    self._trigger_processing = False
                    if self.trigger_camera_btn:
                        self.trigger_camera_btn.setEnabled(True)
                        self.trigger_camera_btn.repaint()
                    return
                
                # Send TRIGGER command via TCP to Pico
                trigger_command = "TRIGGER"
                success = tcp_controller.tcp_controller.send_message(trigger_command)
                
                if success:
                    conditional_print(f"DEBUG: [CameraManager] Successfully sent TCP command: {trigger_command}")
                else:
                    conditional_print(f"DEBUG: [CameraManager] Failed to send TCP command: {trigger_command}")
                
                # Wait briefly for processing
                time.sleep(0.2)  # 200ms to allow processing
                
            except Exception as e:
                conditional_print(f"DEBUG: [CameraManager] Error sending TRIGGER command via TCP: {e}")
            finally:
                # Re-enable trigger button after processing complete
                if self.trigger_camera_btn:
                    self.trigger_camera_btn.setEnabled(True)
                    self.trigger_camera_btn.repaint()
                    conditional_print(f"DEBUG: [CameraManager] Trigger button RE-ENABLED after processing")
                
                # Clear processing flag to allow next trigger
                self._trigger_processing = False
                conditional_print(f"DEBUG: [CameraManager] CLEARED _trigger_processing = False")
        else:
            conditional_print(f"DEBUG: [CameraManager] Ignore trigger button click in live mode or button disabled")
            # Clear processing flag if we couldn't trigger
            self._trigger_processing = False
            self._trigger_processing = False
        
        # Không thay đổi giao diện người dùng, chỉ gọi update để làm mới UI nếu cần
        self.update_camera_mode_ui()
    
    def update_camera_mode_ui(self):
        """C   p nh   t UI theo camera mode hi   n t   i - sync with CameraTool"""
        # Luôn đảm bảo nút trigger có tên không đổi
        if self.trigger_camera_btn:
            self.trigger_camera_btn.setText("Trigger Camera")
        
        # Get current mode from CameraTool if available
        camera_tool = self.find_camera_tool()
        if camera_tool:
            current_mode = camera_tool.get_camera_mode()
            conditional_print(f"DEBUG: [CameraManager] Updating UI for mode from CameraTool: {current_mode}")
        else:
            # Fallback to local mode with default
            if self.current_mode is None:
                self.current_mode = 'live'
            current_mode = self.current_mode
            conditional_print(f"DEBUG: [CameraManager] Using local mode (no CameraTool): {current_mode}")
        
        # Kiểm tra camera có đang chạy không
        camera_is_running = self.is_camera_running()
        editing_camera_tool = self._is_editing_camera_tool()
        
        # Kiểm tra có camera tool hay không
        has_camera_tool = camera_tool is not None
        
        # Kiểm tra onlineCamera button có được nhấn hay không
        online_camera_checked = False
        if hasattr(self.main_window, 'onlineCamera') and self.main_window.onlineCamera:
            online_camera_checked = self.main_window.onlineCamera.isChecked()
        
        # ✅ NEW: Quy tắc mới để xác định khi nào nút trigger được kích hoạt:
        # TRIGGER MODE CONDITIONS (Any of these):
        # 1. In EDIT mode + trigger mode + has camera tool (allow user to test trigger settings)
        # 2. OR: Normal mode + trigger mode + camera is running + camera tool exists
        
        # Mặc định vô hiệu hóa nút trigger
        trigger_enabled = False
        
        # Chỉ kích hoạt nút trong những điều kiện cụ thể
        if current_mode == 'trigger' and has_camera_tool:
            # ✅ Allow trigger button in EDIT mode even if camera not running
            if editing_camera_tool:
                # In edit mode: enable trigger button to let user test settings
                trigger_enabled = True
            elif online_camera_checked:
                # In normal mode: require camera to be running
                trigger_enabled = True
        else:
            # Trong mọi trường hợp khác, vô hiệu hóa nút
            trigger_enabled = False
            
        conditional_print(f"DEBUG: [CameraManager] Trigger enabled: {trigger_enabled}, mode: {current_mode}, editing: {editing_camera_tool}, online_checked: {online_camera_checked}, has_tool: {has_camera_tool}")
        
        is_camera_btn_checked = self.live_camera_btn and self.live_camera_btn.isChecked()
        conditional_print(f"DEBUG: [CameraManager] Camera is running: {camera_is_running}, editing Camera Source: {editing_camera_tool}, button checked: {is_camera_btn_checked}")
        
        # Update trigger button state regardless of live button state
        if self.trigger_camera_btn:
            self.trigger_camera_btn.setText("Trigger Camera")  # Giữ nguyên tên
            self.trigger_camera_btn.setEnabled(trigger_enabled)
            
            if current_mode == 'live':
                # Always disabled in live mode
                self.trigger_camera_btn.setEnabled(False)
                self.trigger_camera_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #cccccc;
                        color: #888888;
                        border: 1px solid #999999;
                    }
                    QPushButton:hover {
                        background-color: #cccccc;
                    }
                    QPushButton:pressed {
                        background-color: #cccccc;
                    }
                """)
                self.trigger_camera_btn.setToolTip("Not available in Live Camera Mode")
                conditional_print(f"DEBUG: [CameraManager] Live mode - trigger button DISABLED")
                
            elif current_mode == 'trigger':
                # Trigger mode - enable/disable based on trigger_enabled flag
                if not trigger_enabled:
                    # Gray khi vô hiệu hóa + tooltip giải thích lý do
                    self.trigger_camera_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #cccccc;
                            color: #888888;
                            border: 1px solid #999999;
                        }
                        QPushButton:hover {
                            background-color: #cccccc;
                        }
                        QPushButton:pressed {
                            background-color: #cccccc;
                        }
                    """)
                    if not camera_tool:
                        self.trigger_camera_btn.setToolTip("Need to add Camera Tool first")
                    elif not online_camera_checked:
                        self.trigger_camera_btn.setToolTip("Click onlineCamera button first")
                    else:
                        self.trigger_camera_btn.setToolTip("Camera not ready")
                    conditional_print(f"DEBUG: [CameraManager] Trigger mode - trigger button DISABLED")
                else:
                    # ✅ Kích hoạt và hiển thị màu cam khi ở chế độ trigger (including edit mode)
                    self.trigger_camera_btn.setStyleSheet("background-color: #ffa62b")  # Orange
                    if editing_camera_tool:
                        self.trigger_camera_btn.setToolTip("Test trigger (Edit mode)")
                    else:
                        self.trigger_camera_btn.setToolTip("Trigger camera to capture")
                    conditional_print(f"DEBUG: [CameraManager] Trigger mode - trigger button ENABLED")
            else:
                # Default - disable
                self.trigger_camera_btn.setEnabled(False)
                self.trigger_camera_btn.setStyleSheet("background-color: #cccccc")
                conditional_print(f"DEBUG: [CameraManager] Default mode - trigger button DISABLED")
        
        # Update live button state
        if self.live_camera_btn:
            if current_mode == 'live':
                # Block signals to prevent recursive calls
                self.live_camera_btn.blockSignals(True)
                # Update live camera button state based on whether it's running
                if is_camera_btn_checked:
                    self.live_camera_btn.setChecked(True)
                    self.live_camera_btn.setText("Stop Camera")
                    self.live_camera_btn.setStyleSheet("background-color: #ff6b6b")  # Red
                else:
                    self.live_camera_btn.setChecked(False)
                    self.live_camera_btn.setText("Start Camera")
                    self.live_camera_btn.setStyleSheet("")
                self.live_camera_btn.setEnabled(True)  # Always enabled in live mode
                self.live_camera_btn.blockSignals(False)
                
            elif current_mode == 'trigger':
                # Live camera button state depends on if camera is running
                self.live_camera_btn.blockSignals(True)
                if camera_is_running or is_camera_btn_checked:
                    self.live_camera_btn.setChecked(True)
                    self.live_camera_btn.setText("Stop Camera")
                    self.live_camera_btn.setStyleSheet("background-color: #ff6b6b")  # Red
                else:
                    self.live_camera_btn.setChecked(False)
                    self.live_camera_btn.setText("Wait For Trigger")
                    self.live_camera_btn.setStyleSheet("")
                self.live_camera_btn.setEnabled(True)  # Always enabled
                self.live_camera_btn.blockSignals(False)
            else:
                # Default case
                self.live_camera_btn.blockSignals(True)
                self.live_camera_btn.setChecked(False)
                self.live_camera_btn.setText("Start Camera")
                self.live_camera_btn.setStyleSheet("")
                self.live_camera_btn.setEnabled(True)
                self.live_camera_btn.blockSignals(False)
        
        # Update mode buttons
        if self.live_camera_mode:
            self.live_camera_mode.blockSignals(True)
            if current_mode == 'live':
                self.live_camera_mode.setChecked(True)
                self.live_camera_mode.setStyleSheet("background-color: #ffd43b")  # Yellow selected
            else:
                self.live_camera_mode.setChecked(False)
                self.live_camera_mode.setStyleSheet("")
            self.live_camera_mode.blockSignals(False)
            
        if self.trigger_camera_mode:
            self.trigger_camera_mode.blockSignals(True)
            if current_mode == 'trigger':
                self.trigger_camera_mode.setChecked(True)
                self.trigger_camera_mode.setStyleSheet("background-color: #ffd43b")  # Yellow selected
            else:
                self.trigger_camera_mode.setChecked(False)
                self.trigger_camera_mode.setStyleSheet("")
            self.trigger_camera_mode.blockSignals(False)
        
        # Always reflect mode selection color on mode buttons even if camera start/stop buttons are missing
        try:
            if current_mode == 'live':
                if self.live_camera_mode:
                    self.live_camera_mode.blockSignals(True)
                    self.live_camera_mode.setChecked(True)
                    self.live_camera_mode.setStyleSheet("background-color: #ffd43b")
                    self.live_camera_mode.blockSignals(False)
                if self.trigger_camera_mode:
                    self.trigger_camera_mode.blockSignals(True)
                    self.trigger_camera_mode.setChecked(False)
                    self.trigger_camera_mode.setStyleSheet("")
                    self.trigger_camera_mode.blockSignals(False)
            elif current_mode == 'trigger':
                if self.live_camera_mode:
                    self.live_camera_mode.blockSignals(True)
                    self.live_camera_mode.setChecked(False)
                    self.live_camera_mode.setStyleSheet("")
                    self.live_camera_mode.blockSignals(False)
                if self.trigger_camera_mode:
                    self.trigger_camera_mode.blockSignals(True)
                    self.trigger_camera_mode.setChecked(True)
                    self.trigger_camera_mode.setStyleSheet("background-color: #ffd43b")
                    self.trigger_camera_mode.blockSignals(False)
            else:
                # Default/no mode: highlight live as default
                if self.live_camera_mode:
                    self.live_camera_mode.blockSignals(True)
                    self.live_camera_mode.setChecked(True)
                    self.live_camera_mode.setStyleSheet("background-color: #ffd43b")
                    self.live_camera_mode.blockSignals(False)
                if self.trigger_camera_mode:
                    self.trigger_camera_mode.blockSignals(True)
                    self.trigger_camera_mode.setChecked(False)
                    self.trigger_camera_mode.setStyleSheet("")
                    self.trigger_camera_mode.blockSignals(False)
        except Exception:
            pass
    
    def on_live_camera_mode_clicked(self, from_init=False):
        """X    l   khi click Live Camera Mode button - delegate to CameraTool"""
        conditional_print(f"DEBUG: [CameraManager] Live camera mode button clicked (from_init={from_init})")
        
        # Lưu lại mode trước đó để biết nếu đang chuyển từ trigger sang live
        previous_mode = self.current_mode
        was_in_trigger_mode = (previous_mode == 'trigger')
        
        # Lưu trạng thái để các hàm khác biết đang được gọi từ __init__ hay không
        self._from_init = from_init
        self.previous_mode = previous_mode
        
        # Find the Camera Source tool and delegate mode change to it
        camera_tool = self.find_camera_tool()
        if camera_tool:
            conditional_print(f"DEBUG: [CameraManager] Found Camera Source tool, delegating mode change")
            success = camera_tool.set_camera_mode("live")
            if success:
                conditional_print(f"DEBUG: [CameraManager] Live mode set successfully via CameraTool")
                # Nếu đang chuyển từ trigger sang live và camera chưa chạy, tự động bật camera
                if was_in_trigger_mode and self.camera_stream and hasattr(self.camera_stream, 'is_running'):
                    camera_running = self.camera_stream.is_running()
                    if not camera_running:
                        conditional_print(f"DEBUG: [CameraManager] Auto-starting camera when switching from trigger to live mode")
                        self._start_camera_stream()
                        if self.live_camera_btn:
                            self.live_camera_btn.setChecked(True)
            else:
                conditional_print(f"DEBUG: [CameraManager] Failed to set live mode via CameraTool")
        else:
            # Fallback: handle mode change directly if no Camera Source tool found
            conditional_print(f"DEBUG: [CameraManager] No Camera Source tool found, handling mode change directly")
            self._handle_live_mode_directly()

        # Persist preference
        self.preferred_mode = 'live'

        # Force update UI to ensure trigger button is disabled
        self.update_camera_mode_ui()

        # Ensure mutual exclusivity like AE/Manual buttons
        if self.live_camera_mode:
            try:
                self.live_camera_mode.blockSignals(True)
                self.live_camera_mode.setChecked(True)
            finally:
                self.live_camera_mode.blockSignals(False)
        if self.trigger_camera_mode:
            try:
                self.trigger_camera_mode.blockSignals(True)
                self.trigger_camera_mode.setChecked(False)
            finally:
                self.trigger_camera_mode.blockSignals(False)

        # When switching back to live mode, revert 3A to Auto
        try:
            # AE back to auto
            self._is_auto_exposure = True
            self.set_auto_exposure_mode()
            self.update_exposure_mode_ui()
        except Exception as e:
            conditional_print(f"DEBUG: [CameraManager] Error forcing auto AE on live mode: {e}")

        try:
            # AWB back to auto
            self._is_auto_awb = True
            # Apply via CameraTool so CameraStream is updated
            ct = self.find_camera_tool()
            if ct and hasattr(ct, 'set_auto_awb'):
                ct.set_auto_awb(True)
            if hasattr(self, 'update_awb_mode_ui'):
                self.update_awb_mode_ui()
        except Exception as e:
            conditional_print(f"DEBUG: [CameraManager] Error forcing auto AWB on live mode: {e}")
        
        # When switching to live mode, also set format to XRGB8888
        try:
            if self.camera_stream and hasattr(self.camera_stream, 'set_format'):
                self.camera_stream.set_format('RGB888')  # Will be converted to XRGB8888
                conditional_print(f"DEBUG: [CameraManager] Set camera format to XRGB8888 for live mode")
        except Exception as e:
            conditional_print(f"DEBUG: [CameraManager] Error setting format for live mode: {e}")

    def on_trigger_camera_mode_clicked(self):
        """X    l   khi click Trigger Camera Mode button - delegate to CameraTool"""
        conditional_print(f"DEBUG: [CameraManager] Trigger camera mode button clicked")

        # FLUSH PENDING FRAME ONCE AT THE START
        # Flush all pending frames so all subsequent settings apply immediately
        # Nếu có frame đang pending → flush ngay một lần, không lặp lại
        if self.camera_stream:
            if hasattr(self.camera_stream, 'fifo_queue') and self.camera_stream.fifo_queue:
                queue_size = len(self.camera_stream.fifo_queue.queue) if hasattr(self.camera_stream.fifo_queue, 'queue') else 0
                if queue_size > 0:
                    conditional_print(f"DEBUG: [CameraManager] Frame pending detected ({queue_size} frames), flushing ONCE for trigger mode change")
                    if hasattr(self.camera_stream, 'cancel_all_and_flush'):
                        self.camera_stream.cancel_all_and_flush()

        # Set flag: Tell helper methods NOT to flush again (we already flushed above)
        self._mode_changing = True
        
        try:
            # Find the Camera Source tool and delegate mode change to it
            camera_tool = self.find_camera_tool()
            if camera_tool:
                conditional_print(f"DEBUG: [CameraManager] Found Camera Source tool, delegating mode change")
                success = camera_tool.set_camera_mode("trigger")
                if success:
                    conditional_print(f"DEBUG: [CameraManager] Trigger mode set successfully via CameraTool")
                else:
                    conditional_print(f"DEBUG: [CameraManager] Failed to set trigger mode via CameraTool")
            else:
                # Fallback: handle mode change directly if no Camera Source tool found
                conditional_print(f"DEBUG: [CameraManager] No Camera Source tool found, handling mode change directly")
                self._handle_trigger_mode_directly()

            # Persist preference
            self.preferred_mode = 'trigger'

            # Force update UI to ensure trigger button is enabled if conditions are met
            self.update_camera_mode_ui()
            
            # Ensure mutual exclusivity like AE/Manual buttons
            if self.trigger_camera_mode:
                try:
                    self.trigger_camera_mode.blockSignals(True)
                    self.trigger_camera_mode.setChecked(True)
                finally:
                    self.trigger_camera_mode.blockSignals(False)
            if self.live_camera_mode:
                try:
                    self.live_camera_mode.blockSignals(True)
                    self.live_camera_mode.setChecked(False)
                finally:
                    self.live_camera_mode.blockSignals(False)

            # When entering trigger mode, force 3A to manual (lock) and apply current params
            # 1) Exposure/Gain -> Manual AE and push current values
            try:
                self._is_auto_exposure = False
                self.set_manual_exposure_mode()  # also flips AeEnable=False on camera
                self.update_exposure_mode_ui()
                # Push current spinbox values immediately
                if self.exposure_edit is not None:
                    try:
                        exp_val = self.exposure_edit.value() if hasattr(self.exposure_edit, 'value') else float(self.exposure_edit.text())
                        self._apply_setting_if_manual('exposure', exp_val)
                    except Exception:
                        pass
                if self.gain_edit is not None:
                    try:
                        gain_val = self.gain_edit.value() if hasattr(self.gain_edit, 'value') else float(self.gain_edit.text())
                        self._apply_setting_if_manual('gain', gain_val)
                    except Exception:
                        pass
            except Exception as e:
                conditional_print(f"DEBUG: [CameraManager] Error forcing manual AE on trigger mode: {e}")

            # 2) White Balance -> Manual AWB and push current R/B gains if available
            try:
                self._is_auto_awb = False
                # Update AWB UI and enable manual fields
                if hasattr(self, 'update_awb_mode_ui'):
                    self.update_awb_mode_ui()
                # Apply via CameraTool so it immediately configures CameraStream
                ct = self.find_camera_tool()
                if ct and hasattr(ct, 'set_auto_awb'):
                    ct.set_auto_awb(False)
                # Push current gains
                r = None; b = None
                if self.colour_gain_r_edit and hasattr(self.colour_gain_r_edit, 'value'):
                    try:
                        r = float(self.colour_gain_r_edit.value())
                    except Exception:
                        pass
                if self.colour_gain_b_edit and hasattr(self.colour_gain_b_edit, 'value'):
                    try:
                        b = float(self.colour_gain_b_edit.value())
                    except Exception:
                        pass
                if ct and hasattr(ct, 'set_colour_gains') and r is not None and b is not None:
                    ct.set_colour_gains(r, b)
            except Exception as e:
                conditional_print(f"DEBUG: [CameraManager] Error forcing manual AWB on trigger mode: {e}")
        finally:
            # Reset flag when done
            self._mode_changing = False
            conditional_print(f"DEBUG: [CameraManager] Mode change complete, _mode_changing flag reset")

        # Force update UI to ensure trigger button is enabled if conditions are met
        self.update_camera_mode_ui()
        
        # Ensure mutual exclusivity like AE/Manual buttons
        if self.trigger_camera_mode:
            try:
                self.trigger_camera_mode.blockSignals(True)
                self.trigger_camera_mode.setChecked(True)
            finally:
                self.trigger_camera_mode.blockSignals(False)
        if self.live_camera_mode:
            try:
                self.live_camera_mode.blockSignals(True)
                self.live_camera_mode.setChecked(False)
            finally:
                self.live_camera_mode.blockSignals(False)

        # When entering trigger mode, force 3A to manual (lock) and apply current params
        # 1) Exposure/Gain -> Manual AE and push current values
        try:
            self._is_auto_exposure = False
            self.set_manual_exposure_mode()  # also flips AeEnable=False on camera
            self.update_exposure_mode_ui()
            # Push current spinbox values immediately
            if self.exposure_edit is not None:
                try:
                    exp_val = self.exposure_edit.value() if hasattr(self.exposure_edit, 'value') else float(self.exposure_edit.text())
                    self._apply_setting_if_manual('exposure', exp_val)
                except Exception:
                    pass
            if self.gain_edit is not None:
                try:
                    gain_val = self.gain_edit.value() if hasattr(self.gain_edit, 'value') else float(self.gain_edit.text())
                    self._apply_setting_if_manual('gain', gain_val)
                except Exception:
                    pass
        except Exception as e:
            conditional_print(f"DEBUG: [CameraManager] Error forcing manual AE on trigger mode: {e}")

        # 2) White Balance -> Manual AWB and push current R/B gains if available
        try:
            self._is_auto_awb = False
            # Update AWB UI and enable manual fields
            if hasattr(self, 'update_awb_mode_ui'):
                self.update_awb_mode_ui()
            # Apply via CameraTool so it immediately configures CameraStream
            ct = self.find_camera_tool()
            if ct and hasattr(ct, 'set_auto_awb'):
                ct.set_auto_awb(False)
            # Push current gains
            r = None; b = None
            if self.colour_gain_r_edit and hasattr(self.colour_gain_r_edit, 'value'):
                try:
                    r = float(self.colour_gain_r_edit.value())
                except Exception:
                    pass
            if self.colour_gain_b_edit and hasattr(self.colour_gain_b_edit, 'value'):
                try:
                    b = float(self.colour_gain_b_edit.value())
                except Exception:
                    pass
            if ct and hasattr(ct, 'set_colour_gains') and r is not None and b is not None:
                ct.set_colour_gains(r, b)
        except Exception as e:
            conditional_print(f"DEBUG: [CameraManager] Error forcing manual AWB on trigger mode: {e}")
    
    def _handle_live_mode_directly(self):
        """Fallback handler for live mode when no CameraTool is available"""
        conditional_print(f"DEBUG: [CameraManager] Handling live mode directly")
        
        # Update UI state
        if self.live_camera_mode:
            self.live_camera_mode.setChecked(True)
        if self.trigger_camera_mode:
            self.trigger_camera_mode.setChecked(False)
        
        # Set internal state
        self.current_mode = 'live'
        
        # Kiểm tra xem có đang edit Camera Source không
        editing_camera_tool = self._is_editing_camera_tool()
        
        # Khi chuyển từ chế độ trigger sang live, tự động kích hoạt camera nếu cần
        # Nhưng không tự động kích hoạt khi được gọi từ MainWindow.__init__
        if self.camera_stream and hasattr(self.camera_stream, 'is_running') and not self.camera_stream.is_running():
            # Không tự động kích hoạt khi đang được gọi từ MainWindow.__init__
            from_init = getattr(self, '_from_init', False)
            if not from_init and getattr(self, 'previous_mode', None) == 'trigger':
                conditional_print(f"DEBUG: [CameraManager] Auto-starting camera when switching from trigger to live mode")
                self._start_camera_stream()
                if self.live_camera_btn:
                    self.live_camera_btn.setChecked(True)
        
        # Luôn kích hoạt chế độ live, bất kể có đang chỉnh sửa hay không
        logging.info("Enabling job execution in live mode")
        self.job_enabled = True
        if hasattr(self.camera_stream, 'set_job_enabled'):
            self.camera_stream.set_job_enabled(True)
        
        # Apply hardware changes - explicitly disable trigger mode for live
        conditional_print(f"DEBUG: [CameraManager] Setting trigger mode to FALSE for live mode")
        self.set_trigger_mode(False)
        
        # Log trạng thái edit để debug
        if editing_camera_tool:
            conditional_print(f"DEBUG: [CameraManager] Editing Camera Source in live mode")
            
        # Trong chế độ live, nút trigger LUÔN bị vô hiệu hóa, bất kể có đang edit hay không
        if self.trigger_camera_btn:
            self.trigger_camera_btn.setEnabled(False)
            self.trigger_camera_btn.setText("Trigger Camera")
            self.trigger_camera_btn.setStyleSheet("background-color: #cccccc; color: #888888;")  # Gray when disabled
            conditional_print(f"DEBUG: [CameraManager] Live mode - forcing trigger button disabled (no exceptions)")
        
        # Luôn cập nhật UI
        self.update_camera_mode_ui()
    
    def _handle_trigger_mode_directly(self):
        """Fallback handler for trigger mode when no CameraTool is available"""
        conditional_print(f"DEBUG: [CameraManager] Handling trigger mode directly")
        
        # Update UI state
        if self.trigger_camera_mode:
            self.trigger_camera_mode.setChecked(True)
        if self.live_camera_mode:
            self.live_camera_mode.setChecked(False)
        
        # Set internal state
        self.current_mode = 'trigger'
        
        # Kiểm tra xem có đang edit Camera Source không
        editing_camera_tool = self._is_editing_camera_tool()
        
        # Kích hoạt chế độ trigger ở mọi trường hợp
        # Bất kể có đang chỉnh sửa hay không, vẫn cấu hình trigger_mode
        logging.info("Enabling job execution in trigger mode")
        self.job_enabled = True
        if hasattr(self.camera_stream, 'set_job_enabled'):
            self.camera_stream.set_job_enabled(True)
        
        # Apply hardware changes - explicitly enable trigger mode
        conditional_print(f"DEBUG: [CameraManager] Setting trigger mode to TRUE for trigger mode")
        self.set_trigger_mode(True)
        
        # Nếu đang trong chế độ edit Camera Source, tùy chỉnh UI để biểu thị
        if editing_camera_tool:
            conditional_print(f"DEBUG: [CameraManager] Editing Camera Source in trigger mode")
            # Update UI properly using update_camera_mode_ui
            pass
        
        # Luôn cập nhật UI
        self.update_camera_mode_ui()
    
    # ============ EXPOSURE MODE HANDLERS ============
    
    def on_auto_exposure_clicked(self):
        """X    l   khi click Auto Exposure button"""
        self._is_auto_exposure = True
        #   p d   ng auto mode ngay l   p t   c
        self.set_auto_exposure_mode()
        self.update_exposure_mode_ui()
        # L  u v  o pending settings
        self._pending_exposure_settings['auto_exposure'] = True
    
    def on_manual_exposure_clicked(self):
        """X    l   khi click Manual Exposure button"""
        self._is_auto_exposure = False
        #   p d   ng manual mode ngay l   p t   c
        self.set_manual_exposure_mode()
        self.update_exposure_mode_ui()
        # L  u v  o pending settings
        self._pending_exposure_settings['auto_exposure'] = False
    
    def update_exposure_mode_ui(self):
        """C   p nh   t UI theo exposure mode hi   n t   i"""
        # Enable/disable manual controls
        self.set_settings_controls_enabled(not self._is_auto_exposure and self.ui_enabled)
        
        # Update button states
        if self.auto_exposure_btn and self.manual_exposure_btn:
            if self._is_auto_exposure:
                self.auto_exposure_btn.setStyleSheet("background-color: #51cf66")  # Green
                self.manual_exposure_btn.setStyleSheet("")
            else:
                self.auto_exposure_btn.setStyleSheet("")
                self.manual_exposure_btn.setStyleSheet("background-color: #ffd43b")  # Yellow

    # ====== AWB MODE HANDLERS ======
    def set_awb_controls_enabled(self, enabled):
        """Enable/disable manual AWB controls (colour gains)."""
        try:
            if self.colour_gain_r_edit:
                self.colour_gain_r_edit.setEnabled(bool(enabled))
            if self.colour_gain_b_edit:
                self.colour_gain_b_edit.setEnabled(bool(enabled))
        except Exception:
            pass

    def update_awb_mode_ui(self):
        """Update AWB UI state based on _is_auto_awb flag."""
        auto = getattr(self, '_is_auto_awb', True)
        try:
            if self.auto_awb_btn:
                self.auto_awb_btn.setStyleSheet("background-color: #51cf66" if auto else "")
            if self.manual_awb_btn:
                self.manual_awb_btn.setStyleSheet("" if auto else "background-color: #ffd43b")
        except Exception:
            pass
        # Enable manual gain fields only in manual mode
        self.set_awb_controls_enabled(self.ui_enabled and (not auto))

    def on_auto_awb_clicked(self):
        """Switch to Auto AWB and apply to active camera via CameraTool if available."""
        self._is_auto_awb = True
        # Update UI first
        self.update_awb_mode_ui()
        # Delegate to CameraTool for application
        try:
            ct = self.find_camera_tool()
            if ct and hasattr(ct, 'set_auto_awb'):
                ct.set_auto_awb(True)
        except Exception:
            pass

    def on_manual_awb_clicked(self):
        """Switch to Manual AWB and apply current gains via CameraTool if available."""
        self._is_auto_awb = False
        # Update UI first
        self.update_awb_mode_ui()
        # Read gains and apply via CameraTool
        r = None; b = None
        try:
            if self.colour_gain_r_edit:
                try:
                    r = float(self.colour_gain_r_edit.value()) if hasattr(self.colour_gain_r_edit, 'value') else float(self.colour_gain_r_edit.text())
                except Exception:
                    r = None
            if self.colour_gain_b_edit:
                try:
                    b = float(self.colour_gain_b_edit.value()) if hasattr(self.colour_gain_b_edit, 'value') else float(self.colour_gain_b_edit.text())
                except Exception:
                    b = None
            ct = self.find_camera_tool()
            if ct and hasattr(ct, 'set_auto_awb'):
                ct.set_auto_awb(False)
            if ct and r is not None and b is not None and hasattr(ct, 'set_colour_gains'):
                ct.set_colour_gains(r, b)
        except Exception:
            pass

    def on_colour_gain_r_changed(self, value):
        """Apply R gain immediately when in manual AWB."""
        try:
            if getattr(self, '_is_auto_awb', True):
                return
            r = float(value)
            b = None
            if self.colour_gain_b_edit:
                try:
                    b = float(self.colour_gain_b_edit.value()) if hasattr(self.colour_gain_b_edit, 'value') else float(self.colour_gain_b_edit.text())
                except Exception:
                    b = None
            ct = self.find_camera_tool()
            if ct and hasattr(ct, 'set_colour_gains') and b is not None:
                ct.set_colour_gains(r, b)
        except Exception:
            pass

    def on_colour_gain_b_changed(self, value):
        """Apply B gain immediately when in manual AWB."""
        try:
            if getattr(self, '_is_auto_awb', True):
                return
            b = float(value)
            r = None
            if self.colour_gain_r_edit:
                try:
                    r = float(self.colour_gain_r_edit.value()) if hasattr(self.colour_gain_r_edit, 'value') else float(self.colour_gain_r_edit.text())
                except Exception:
                    r = None
            ct = self.find_camera_tool()
            if ct and hasattr(ct, 'set_colour_gains') and r is not None:
                ct.set_colour_gains(r, b)
        except Exception:
            pass
    
    def find_camera_tool(self):
        """Find the Camera Source tool.

        Prefer a cached reference during pending/edit; else search current job.
        ✅ Also check _editing_tool for tools being edited
        """
        # Use cached reference if present (tool created/registered but not yet added to job)
        try:
            if getattr(self, '_camera_tool_ref', None) is not None:
                return self._camera_tool_ref
        except Exception:
            pass
        if not hasattr(self, 'main_window') or not self.main_window:
            return None
        
        # ✅ NEW: Check if we're editing a Camera Source tool
        # During edit, tool is in _editing_tool, not yet in job
        if hasattr(self.main_window, '_editing_tool') and self.main_window._editing_tool:
            editing_tool = self.main_window._editing_tool
            if hasattr(editing_tool, 'name') and editing_tool.name == 'Camera Source':
                return editing_tool
            if hasattr(editing_tool, 'display_name') and editing_tool.display_name == 'Camera Source':
                return editing_tool
        
        if not hasattr(self.main_window, 'tool_manager') or not self.main_window.tool_manager:
            return None
            
        # Access tools through job_manager instead of tool_manager
        job_manager = self.main_window.tool_manager.job_manager
        if not job_manager or not hasattr(job_manager, 'current_job') or not job_manager.current_job:
            return None
            
        # Search through tools in current job
        for tool in job_manager.current_job.tools:
            if hasattr(tool, '__class__') and tool.__class__.__name__ == 'CameraTool':
                return tool
            # Also check by name for backwards compatibility
            if hasattr(tool, 'name') and tool.name == 'Camera Source':
                return tool
                
        return None
    
    def _update_execution_label(self, job_results):
        """
        Update executionLabel with OK/NG status from ResultManager
        
        ResultManager evaluates detections/classifications independently
        from the job pipeline and provides OK/NG status.
        
        Args:
            job_results: Dict returned from job.run() (used to extract current detections)
        """
        try:
            # Get main window reference
            if not hasattr(self, 'main_window') or not self.main_window:
                return
            
            # Get ResultManager
            result_manager = getattr(self.main_window, 'result_manager', None)
            if not result_manager:
                conditional_print(f"DEBUG: [CameraManager] ResultManager not found in main_window")
                return
            
            # Get executionLabel
            execution_label = getattr(self.main_window, 'executionLabel', None)
            if not execution_label:
                conditional_print(f"DEBUG: [CameraManager] executionLabel not found")
                return
            
            # First, try to get result from ResultTool in job pipeline (new way)
            status = 'NG'
            reason = 'No result available'
            result_data = {}  # Initialize result_data for all paths
            inference_time = 0.0  # Initialize inference_time
            
            if isinstance(job_results, dict):
                # Debug: log the structure of job_results
                conditional_print(f"DEBUG: [CameraManager] job_results keys: {list(job_results.keys())}")
                conditional_print(f"DEBUG: [CameraManager] job_results content: {job_results}")
                
                # Get inference_time from top-level job_results (added by job_manager)
                inference_time = job_results.get('inference_time', 0.0)
                conditional_print(f"DEBUG: [CameraManager] Top-level inference_time: {inference_time:.3f}s")
                
                if inference_time == 0.0:
                    # Try getting from tool_results
                    tool_results = job_results.get('tool_results', {})
                    conditional_print(f"DEBUG: [CameraManager] tool_results keys: {list(tool_results.keys()) if tool_results else 'empty'}")
                    if isinstance(tool_results, dict):
                        for tool_name, tool_result in tool_results.items():
                            conditional_print(f"DEBUG: [CameraManager] Checking tool {tool_name}: {type(tool_result)}")
                            if isinstance(tool_result, dict) and 'inference_time' in tool_result:
                                inference_time = tool_result['inference_time']
                                conditional_print(f"DEBUG: [CameraManager] Got inference_time from {tool_name}: {inference_time:.3f}s")
                                break
                
                # Try alternative path: results -> Detect Tool -> data
                if inference_time == 0.0:
                    results_data = job_results.get('results', {})
                    conditional_print(f"DEBUG: [CameraManager] results keys: {list(results_data.keys()) if results_data else 'empty'}")
                    if isinstance(results_data, dict):
                        for tool_name in ['Detect Tool', 'detect_tool', 'DetectTool']:
                            if tool_name in results_data:
                                tool_data = results_data[tool_name]
                                if isinstance(tool_data, dict):
                                    data = tool_data.get('data', {})
                                    if isinstance(data, dict) and 'inference_time' in data:
                                        inference_time = data['inference_time']
                                        conditional_print(f"DEBUG: [CameraManager] Got inference_time from results.{tool_name}.data: {inference_time:.3f}s")
                                        break
                
                conditional_print(f"DEBUG: [CameraManager] Final inference_time: {inference_time:.3f}s")
                
                # Check for Result Tool output (new threshold-based evaluation)
                # Results are nested under 'results' key in job_results
                job_results_data = job_results.get('results', {})  # Look in nested results
                result_tool_result = job_results_data.get('Result Tool', {})
                
                if isinstance(result_tool_result, dict):
                    # Get the actual result data from the 'data' key
                    result_data = result_tool_result.get('data', {})
                    if 'ng_ok_result' in result_data:
                        status = result_data.get('ng_ok_result', 'NG')
                        reason = result_data.get('ng_ok_reason', 'Unknown')
                        conditional_print(f"DEBUG: [CameraManager] Using ResultTool evaluation: {status} - {reason}")
                    else:
                        # Fallback to old ResultManager method
                        conditional_print(f"DEBUG: [CameraManager] No ng_ok_result in ResultTool data, using legacy ResultManager")
                        result_data = {}  # Reset for legacy path
                else:
                    # Fallback to old ResultManager method for backward compatibility
                    conditional_print(f"DEBUG: [CameraManager] No ResultTool in job_results, using legacy ResultManager")
                    result_data = {}  # Reset for legacy path
                    
                    # Extract current detections from job_results nested structure
                    current_detections = []
                    detect_tool_result = job_results_data.get('Detect Tool', {})  # Look in nested results
                    if isinstance(detect_tool_result, dict):
                        result_data = detect_tool_result.get('data', {})
                        current_detections = result_data.get('detections', [])
                    
                    # Get NG/OK status from ResultManager
                    if current_detections:
                        # Evaluate current detections
                        result = result_manager.evaluate_detect_results(current_detections)
                        status = result.get('status', 'NG')
                        reason = result.get('reason', 'Unknown')
                    else:
                        # No detections - default to NG
                        status = 'NG'
                        reason = 'No detections'
            
            status_color = "#4caf50" if status == "OK" else "#f44336"  # Green for OK, Red for NG
            
            # Update label text and style
            execution_label.setText(status)
            execution_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {status_color};
                    color: white;
                    font-weight: bold;
                    font-size: 16px;
                    border-radius: 4px;
                }}
            """)
            
            conditional_print(f"DEBUG: [CameraManager] Execution status: {status} (from ResultManager)")
            conditional_print(f"DEBUG: [CameraManager] Reason: {reason}")
            
            # IMPORTANT: Record this result to ResultManager's frame history
            # This is needed for review labels to show OK/NG status for each frame
            try:
                result_manager = getattr(self.main_window, 'result_manager', None)
                if result_manager and hasattr(result_manager, '_add_frame_status_to_history'):
                    import time
                    import logging
                    current_time = time.time()
                    logging.info(f"[CameraManager] Recording result to history - status={status}, timestamp={current_time}")
                    
                    result_manager._add_frame_status_to_history(
                        timestamp=current_time,
                        status=status,
                        similarity=0.0  # Use 0.0 as placeholder
                    )
                    conditional_print(f"DEBUG: [CameraManager] Recorded result to ResultManager history: {status}")
            except Exception as e:
                conditional_print(f"DEBUG: [CameraManager] Could not record result to ResultManager: {e}")
            
            # NEW: Attach job result to waiting frame (frame created from TCP start_rising)
            # If no frame waiting, BUFFER the result to attach when frame arrives
            try:
                result_tab_manager = getattr(self.main_window, 'result_tab_manager', None)
                if result_tab_manager:
                    import logging
                    
                    # Prepare detection data if available
                    detection_data = None
                    if 'detections' in result_data:
                        detection_data = {
                            'detections': result_data.get('detections', []),
                            'detection_count': result_data.get('detection_count', 0),
                            'inference_time': inference_time,  # Use the extracted inference_time
                        }
                    else:
                        # Create detection_data with inference_time even if no detections
                        detection_data = {
                            'detections': [],
                            'detection_count': 0,
                            'inference_time': inference_time,
                        }
                    
                    conditional_print(f"DEBUG: [CameraManager] Detection data: inference_time={inference_time:.3f}s, detection_count={detection_data.get('detection_count', 0)}")
                    
                    # Try to attach result to waiting frame
                    success = result_tab_manager.attach_job_result_to_waiting_frame(
                        status=status,
                        detection_data=detection_data,
                        inference_time=inference_time,  # Use the extracted inference_time
                        reason=reason
                    )
                    
                    if success:
                        logging.info(f"[CameraManager] Attached job result to waiting frame: status={status}")
                        conditional_print(f"DEBUG: [CameraManager] Attached job result to frame: status={status}")
                    else:
                        # ✅ CRITICAL FIX: Buffer result if no waiting frame
                        # When TCP start_rising arrives, it will attach immediately
                        logging.info("[CameraManager] No waiting frame - buffering result for later")
                        conditional_print(f"DEBUG: [CameraManager] Buffering result (TCP signal not received yet)")
                        
                        # Save result to pending buffer
                        buffer_success = result_tab_manager.save_pending_job_result(
                            status=status,
                            similarity=0.0,
                            reason=reason,
                            detection_data=detection_data,
                            inference_time=inference_time  # Use the extracted inference_time
                        )
                        
                        if buffer_success:
                            logging.info(f"[CameraManager] ✅ Result buffered successfully: {status}, inference_time={inference_time:.3f}s")
                            conditional_print(f"DEBUG: [CameraManager] ✅ Result buffered: {status} (inference_time={inference_time:.3f}s)")
                        else:
                            logging.error("[CameraManager] Failed to buffer result")
                            conditional_print(f"DEBUG: [CameraManager] ❌ Failed to buffer result")
                else:
                    logging.warning("[CameraManager] Result Tab Manager not found in main_window")
                    conditional_print(f"DEBUG: [CameraManager] Result Tab Manager not available")
            except Exception as e:
                logging.error(f"[CameraManager] Error attaching/buffering job result: {e}", exc_info=True)
                conditional_print(f"DEBUG: [CameraManager] Error attaching/buffering job result: {e}")
            
            
        except Exception as e:
            logging.error(f"Error updating execution label: {e}")
            conditional_print(f"DEBUG: [CameraManager] Error updating execution label: {e}")
    
    
    def set_ng_ok_reference_from_current_detections(self):
        """
        Set NG/OK reference from DetectTool detections using ResultManager
        
        This calls ResultManager.set_reference_from_detect_tool()
        which is independent from the job pipeline.
        """
        try:
            # Get main window and result manager
            if not hasattr(self, 'main_window') or not self.main_window:
                conditional_print(f"DEBUG: [CameraManager] main_window not available")
                return False
            
            result_manager = getattr(self.main_window, 'result_manager', None)
            if not result_manager:
                conditional_print(f"DEBUG: [CameraManager] ResultManager not available")
                return False
            
            # Get current job and detect tool
            job_manager = self.main_window.job_manager
            current_job = job_manager.get_current_job()
            
            if not current_job:
                conditional_print(f"DEBUG: [CameraManager] No current job")
                return False
            
            # Find detect tool in job
            detect_tool = None
            for tool in current_job.tools:
                if hasattr(tool, 'name') and 'detect' in tool.name.lower():
                    detect_tool = tool
                    break
            
            if not detect_tool:
                conditional_print(f"DEBUG: [CameraManager] No DetectTool found in job")
                return False
            
            # Get last detections from detect tool
            last_detections = detect_tool.get_last_detections()
            
            if not last_detections:
                conditional_print(f"DEBUG: [CameraManager] No detections to set as reference")
                return False
            
            # Set reference in ResultManager (independent from job pipeline!)
            success = result_manager.set_reference_from_detect_tool(last_detections)
            
            if success:
                print(f"Reference set via ResultManager: {len(last_detections)} objects")
                # Show success message
                if hasattr(self.main_window, 'statusbar'):
                    self.main_window.statusbar().showMessage(f"Reference set: {len(last_detections)} objects", 3000)
            
            return success
            
        except Exception as e:
            logging.error(f"Error setting reference: {e}")
            conditional_print(f"DEBUG: [CameraManager] Error setting reference: {e}")
            return False
    
    
    def on_apply_settings_clicked(self):
        """Apply any pending camera settings and resync UI (safe stub)."""
        try:
            # Safely refresh UI state; real apply logic can be added here.
            self.update_camera_mode_ui()
        except Exception as e:
            conditional_print(f"DEBUG: [CameraManager] on_apply_settings_clicked error: {e}")
        return True
