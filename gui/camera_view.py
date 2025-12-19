import logging
import cv2
import time
import threading
import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QRectF, QPoint, QThread, QTimer
from PyQt5.QtGui import QImage, QPixmap, QCursor, QPainter, QPen, QColor, QFont
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from gui.detection_area_overlay import DetectionAreaOverlay
from utils.debug_utils import debug_print

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class FrameHistoryWorker(QObject):
    """Worker thread for frame history processing to avoid UI blocking"""
    
    def __init__(self, camera_view):
        super().__init__()
        self.camera_view = camera_view
        self.running = True
    
    def process_frame_history(self):
        """Process frame history updates in background thread"""
        while self.running:
            try:
                # Check if there are frames to process
                with self.camera_view.frame_history_lock:
                    if len(self.camera_view.frame_history_queue) > 0:
                        # Get the latest frame
                        frame = self.camera_view.frame_history_queue[-1]
                        # Clear queue to only keep latest frame
                        self.camera_view.frame_history_queue.clear()
                        
                        # DEBUG: Log frame being added to history
                        logging.info(f"[FrameHistoryWorker] Adding frame to history - shape={frame.shape if frame is not None else 'None'}, history_count_before={len(self.camera_view.frame_history)}")
                        
                        # Add to history
                        self.camera_view.frame_history.append(frame.copy())
                        
                        # Keep only last N frames
                        if len(self.camera_view.frame_history) > self.camera_view.max_history_frames:
                            self.camera_view.frame_history.pop(0)
                        
                        # DEBUG: Log history state
                        logging.info(f"[FrameHistoryWorker] Frame added - history_count={len(self.camera_view.frame_history)}, max={self.camera_view.max_history_frames}")
                        
                        # Check if it's time to update review views
                        current_time = time.time()
                        if (current_time - self.camera_view._last_review_update) >= self.camera_view._review_update_interval:
                            # DEBUG: Log review update trigger
                            logging.info(f"[FrameHistoryWorker] Triggering review view update - history_count={len(self.camera_view.frame_history)}")
                            
                            # Schedule UI update on main thread
                            QTimer.singleShot(0, self.camera_view._update_review_views_threaded)
                            self.camera_view._last_review_update = current_time
                
                # Sleep briefly to avoid busy waiting
                time.sleep(0.033)  # ~30 FPS max processing rate
                
            except Exception as e:
                logging.error(f"Error in frame history worker: {e}")
                time.sleep(0.1)  # Sleep longer on error
    
    def stop(self):
        """Stop the worker"""
        self.running = False


class CameraDisplayWorker(QObject):
    """Worker thread for camera frame display processing to avoid UI blocking"""
    
    # Signal to update main thread UI
    frameProcessed = pyqtSignal(object, object)  # (qimage, frame_for_history)
    
    def __init__(self, camera_view):
        super().__init__()
        self.camera_view = camera_view
        self.running = True
        self.frame_queue = []
        self.frame_lock = threading.Lock()
    
    def add_frame(self, frame):
        """Add frame to processing queue (thread-safe)"""
        with self.frame_lock:
            # Keep only latest frame to avoid memory buildup
            self.frame_queue.clear()
            self.frame_queue.append(frame.copy())
            print(f"DEBUG: [CameraDisplayWorker.add_frame] Frame added to queue, size={len(self.frame_queue)}")
    
    def process_frames(self):
        """Process frames in background thread"""
        print(f"DEBUG: [CameraDisplayWorker.process_frames] Worker thread started, running={self.running}")
        while self.running:
            try:
                frame = None
                with self.frame_lock:
                    if len(self.frame_queue) > 0:
                        frame = self.frame_queue.pop(0)
                
                if frame is not None:
                    # Process frame in background thread
                    print(f"DEBUG: [CameraDisplayWorker.process_frames] Processing frame, shape={frame.shape}")
                    processed_qimage, frame_for_history = self._process_frame_to_qimage(frame)
                    
                    if processed_qimage is not None:
                        print(f"DEBUG: [CameraDisplayWorker.process_frames] Emitting frameProcessed signal")
                        # Emit signal to update UI on main thread
                        self.frameProcessed.emit(processed_qimage, frame_for_history)
                    else:
                        print(f"DEBUG: [CameraDisplayWorker.process_frames] processed_qimage is None!")
                
                # Sleep briefly to avoid busy waiting
                time.sleep(0.016)  # ~60 FPS max processing rate
                
            except Exception as e:
                logging.error(f"Error in camera display worker: {e}")
                time.sleep(0.1)  # Sleep longer on error
    
    def _process_frame_to_qimage(self, frame):
        """Process frame to QImage in background thread"""
        try:
            if frame is None or frame.size == 0:
                print(f"DEBUG: [_process_frame_to_qimage] Invalid frame")
                return None, None
            
            # Choose frame to display based on current display mode
            display_frame = self.camera_view._get_display_frame_from_raw(frame)
            frame_to_process = display_frame if display_frame is not None else frame
            
            # Get pixel format from camera stream (use actual format, not requested)
            pixel_format = 'XBGR8888'  # Default - assume BGR by default
            try:
                mw = getattr(self.camera_view, 'main_window', None)
                cm = getattr(mw, 'camera_manager', None) if mw else None
                cs = getattr(cm, 'camera_stream', None) if cm else None
                if cs is not None:
                    # Try to get actual camera format first (what it's REALLY using)
                    if hasattr(cs, 'get_actual_camera_format'):
                        pixel_format = cs.get_actual_camera_format()
                    elif hasattr(cs, 'get_pixel_format'):
                        # Fallback to requested format if actual not available
                        pixel_format = cs.get_pixel_format()
            except Exception:
                pass
            
            print(f"DEBUG: [_process_frame_to_qimage] Processing with format: {pixel_format}, shape={frame_to_process.shape}")
            
            # Handle different frame formats safely with proper color conversion
            if len(frame_to_process.shape) == 3 and frame_to_process.shape[2] >= 3:  # Color image with channels
                if frame_to_process.shape[2] == 4:  # 4-channel format (XRGB or XBGR)
                    actual_format_str = str(pixel_format)
                    
                    # NOTE: For 4-channel formats from picamera2, use OpenCV's color conversion
                    # This is more reliable than manual channel reordering
                    # Picamera2 returns BGRA byte order regardless of format name
                    
                    if actual_format_str in ('XBGR8888', 'XRGB8888', 'BGR888', 'RGB888'):
                        # All 4-channel picamera2 formats have BGRA byte order
                        # Use OpenCV to convert BGRA to RGB
                        frame_to_process = cv2.cvtColor(frame_to_process, cv2.COLOR_BGRA2RGB)
                        debug_print(f"{actual_format_str} (4-ch): Converting BGRA->RGB with cvtColor", "[CameraDisplayWorker]")
                    else:
                        # Unknown format - try BGRA conversion as fallback
                        frame_to_process = cv2.cvtColor(frame_to_process, cv2.COLOR_BGRA2RGB)
                        debug_print(f"Unknown 4-channel format {actual_format_str}: Converting BGRA->RGB", "[CameraDisplayWorker]")
                        
                elif frame_to_process.shape[2] == 3:  # 3-channel format
                    # NOTE: Picamera2 always returns data in BGR order for 3-channel
                    # regardless of whether we request RGB888 or BGR888
                    # So for 3-channel data, we always need to convert BGR->RGB
                    actual_format_str = str(pixel_format)
                    if actual_format_str in ('RGB888', 'XRGB8888', 'BGR888', 'XBGR8888'):
                        # Picamera2 returns BGR byte order for all formats
                        frame_to_process = cv2.cvtColor(frame_to_process, cv2.COLOR_BGR2RGB)
                        debug_print(f"{actual_format_str}: Converting BGR->RGB (3-channel)", "[CameraDisplayWorker]")
                    else:
                        # Unknown format, assume BGR and convert
                        frame_to_process = cv2.cvtColor(frame_to_process, cv2.COLOR_BGR2RGB)
                        debug_print(f"Unknown 3-channel format {actual_format_str}, assuming BGR", "[CameraDisplayWorker]")
            elif len(frame_to_process.shape) == 2:  # 2D frame
                frame_to_process = cv2.cvtColor(frame_to_process, cv2.COLOR_GRAY2RGB)
            else:
                # Handle other formats
                if len(frame_to_process.shape) == 3 and frame_to_process.shape[2] == 1:
                    frame_to_process = frame_to_process.squeeze()
                    frame_to_process = cv2.cvtColor(frame_to_process, cv2.COLOR_GRAY2RGB)
                else:
                    print(f"DEBUG: [_process_frame_to_qimage] Unsupported format: {frame_to_process.shape}")
                    logging.warning("Unsupported frame format with shape: %s", frame_to_process.shape)
                    return None, None
            
            # Convert to QImage
            h, w, ch = frame_to_process.shape
            bytes_per_line = ch * w
            
            # Ensure the frame is a contiguous C-order array (required for QImage)
            # This is especially important after channel reordering with advanced indexing
            frame_to_process = np.ascontiguousarray(frame_to_process)
            
            # Create QImage from processed frame
            print(f"DEBUG: [_process_frame_to_qimage] Creating QImage: {w}x{h}, channels={ch}")
            qimage = QImage(frame_to_process.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # Return QImage and frame for history (make copies to be thread-safe)
            print(f"DEBUG: [_process_frame_to_qimage] QImage created successfully, isNull={qimage.isNull()}")
            return qimage.copy(), frame_to_process.copy()
            
        except Exception as e:
            print(f"DEBUG: [_process_frame_to_qimage] ERROR: {e}")
            logging.error(f"Error processing frame to QImage: {e}")
            return None, None
    
    def stop(self):
        """Stop the worker"""
        self.running = False


class CameraView(QObject):
    """
    Lớp quản lý và hiển thị hình ảnh từ camera
    """
    
    # Tín hiệu để thông báo khi các thông số focus được tính toán
    focus_calculated = pyqtSignal(int)
    
    # Lock cho các hoạt động zoom để tránh zoom quá nhanh
    _zoom_lock = False
    _last_zoom_time = 0
    _zoom_mutex = threading.Lock()  # Thread-safe mutex for zoom operations
    
    # Tín hiệu để thông báo cập nhật FPS
    fps_updated = pyqtSignal(float)
    
    # Tín hiệu để thông báo khi area được vẽ
    area_drawn = pyqtSignal(int, int, int, int)  # x1, y1, x2, y2
    
    # Tín hiệu để thông báo khi area thay đổi (move/resize)
    area_changed = pyqtSignal(int, int, int, int)  # x1, y1, x2, y2

    def __init__(self, graphics_view, main_window=None):
        """
        Khởi tạo camera view
        
        Args:
            graphics_view: QGraphicsView widget từ UI để hiển thị hình ảnh
            main_window: Reference to MainWindow for job manager access
        """
        super().__init__()
        self.graphics_view = graphics_view
        self.main_window = main_window  # Store reference to main window
        
        # Khởi tạo các biến thành viên
        self.current_frame = None
        self.last_valid_qimage = None  # Store last valid QImage for trigger mode
        self.in_trigger_mode = False   # Track if camera is in trigger mode
        self.zoom_level = 1.1  # Default zoom level tăng 1 mức zoom_in
        self.zoom_step = 0.1
        self.rotation_angle = 0
        self.fit_on_next_frame = False
        self._zoom_changed = False     # Flag to track if zoom level was manually changed
        
        # Method to get rotation angle
        def get_rotation_angle(self):
            return self.rotation_angle
            
        # Add the method to the instance
        self.get_rotation_angle = get_rotation_angle.__get__(self, CameraView)
        
        # Method to get current frame
        def get_current_frame(self):
            return self.current_frame.copy() if self.current_frame is not None else None
            
        # Add the method to the instance
        self.get_current_frame = get_current_frame.__get__(self, CameraView)
        
        # Biến tính toán FPS
        self.prev_frame_time = 0
        self.fps = 0
        self.fps_alpha = 0.9  # Hệ số trung bình động cho FPS
        self.show_fps = True
        
        # Frame history for review views
        self.frame_history = []  # Store last 5 frames for review views
        self.max_history_frames = 5
        self.review_views = None  # Will be set by main window
        self.review_labels = None  # Will be set by main window for NG/OK status display
        self._last_review_update = 0  # Timestamp of last review update
        self._review_update_interval = 0.3  # Update review views every 300ms max (increased for better performance)
        self.enable_frame_history = True  # Re-enabled with threading support
        
        # Threading for frame history processing
        self.frame_history_thread = None
        self.frame_history_worker = None
        self.frame_history_queue = []
        self.frame_history_lock = threading.Lock()
        self._shutdown_frame_history = False
        
        # Threading for camera display processing
        self.camera_display_thread = None
        self.camera_display_worker = None
        self._shutdown_camera_display = False
        
        # Start worker threads
        self._start_frame_history_worker()
        self._start_camera_display_worker()
        
        # Drawing mode variables
        self.draw_mode = False
        self.drawing = False
        self.start_point = None
        self.end_point = None
        self.current_overlay = None  # Overlay hiện tại đang edit
        self.overlays = {}  # Dict mapping tool_id -> DetectionAreaOverlay
        self.overlay_edit_mode = False  # Trạng thái có thể chỉnh sửa overlay
        self.saved_areas = []  # List of saved detection areas
        self.current_area = None  # Current area being worked with
        self.detection_results = []  # Store detection results for visualization
        
        # Display mode variables for pipeline output selection
        self.display_mode = "camera"  # Default to camera source
        self.display_tool_id = None   # Tool ID for specific tool outputs
        self.show_detection_overlay = False  # Whether to show detection results
        self.processed_frames = {}  # Store processed frames from tools: {tool_id: frame}
        self.current_raw_frame = None  # Store current raw camera frame
        self.current_editing_tool_id = None  # Tool ID currently being edited
        # Track first draw to control auto-centering
        self._has_drawn_once = False
        
        # Khởi tạo scene và cấu hình graphics view
        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)
        self.pixmap_item = None
        
        # Configure view properties
        self.graphics_view.setRenderHints(QPainter.SmoothPixmapTransform)
        self.graphics_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.graphics_view.setDragMode(QGraphicsView.NoDrag)
        
        # Register additional zoom and pan handlers
        self.register_zoom_events()
        
        # Setup mouse event handling for drawing
        # Store original event handlers
        self._original_mouse_press = self.graphics_view.mousePressEvent
        self._original_mouse_move = self.graphics_view.mouseMoveEvent
        self._original_mouse_release = self.graphics_view.mouseReleaseEvent
        
        # Set custom event handlers
        self.graphics_view.mousePressEvent = self._mouse_press_event
        self.graphics_view.mouseMoveEvent = self._mouse_move_event
        self.graphics_view.mouseReleaseEvent = self._mouse_release_event
        
        # Khởi tạo offset cho scene
        self.scene_offset = [0, 0]
        self.scene_offset_max = [0, 0]

    def set_display_mode(self, mode, tool_id=None):
        """
        Set the display mode for camera view
        
        Args:
            mode: Display mode ('camera', 'detection', 'edge', 'ocr')
            tool_id: Tool ID for specific tool outputs (optional)
        """
        print(f"DEBUG: [CameraView] Setting display mode to: {mode}, tool_id: {tool_id}")
        self.display_mode = mode
        self.display_tool_id = tool_id
        
        # Đảm bảo giữ mức zoom là 1.1 khi thay đổi display mode
        self.zoom_level = 1.1
        self._zoom_changed = True
        print(f"DEBUG: [CameraView] Đã đặt zoom_level = 1.1 trong set_display_mode")
        
        # Configure display based on mode
        if mode == "camera":
            self.show_detection_overlay = False
            print("DEBUG: [CameraView] Display mode: Camera source (raw)")
        elif mode == "detection":
            self.show_detection_overlay = True
            print(f"DEBUG: [CameraView] Display mode: Detection output (tool_id: {tool_id})")
        elif mode == "edge":
            self.show_detection_overlay = False
            print(f"DEBUG: [CameraView] Display mode: Edge detection (tool_id: {tool_id})")
        elif mode == "ocr":
            self.show_detection_overlay = False
            print(f"DEBUG: [CameraView] Display mode: OCR output (tool_id: {tool_id})")
        else:
            print(f"DEBUG: [CameraView] Unknown display mode: {mode}, defaulting to camera")
            self.display_mode = "camera"
            self.show_detection_overlay = False
            
        # Update visibility of detection areas based on display mode
        self.update_detection_areas_visibility()
    
    def _get_display_frame(self):
        """Get the frame to display based on current display mode"""
        if self.display_mode == "camera":
            # Show raw camera frame
            return self.current_raw_frame
        elif self.display_mode == "detection" and self.display_tool_id:
            # Show processed frame from detection tool if available
            tool_key = f"detection_{self.display_tool_id}"
            if tool_key in self.processed_frames:
                print(f"DEBUG: [CameraView] Using processed frame from {tool_key}")
                return self.processed_frames[tool_key]
            else:
                print(f"DEBUG: [CameraView] No processed frame available for {tool_key}, using raw")
                return self.current_raw_frame
        elif self.display_mode in ["edge", "ocr"] and self.display_tool_id:
            # Show processed frame from other tools if available  
            tool_key = f"{self.display_mode}_{self.display_tool_id}"
            if tool_key in self.processed_frames:
                print(f"DEBUG: [CameraView] Using processed frame from {tool_key}")
                return self.processed_frames[tool_key]
            else:
                print(f"DEBUG: [CameraView] No processed frame available for {tool_key}, using raw")
                return self.current_raw_frame
        else:
            # Default to raw camera frame
            return self.current_raw_frame

    def refresh_display_with_new_format(self):
        """Force refresh the current display with new pixel format settings"""
        if hasattr(self, 'current_raw_frame') and self.current_raw_frame is not None:
            print("DEBUG: [CameraView] Refreshing display with new format using raw frame")
            # Re-process the raw frame with new format settings
            self.display_frame(self.current_raw_frame)
            return True
        elif hasattr(self, 'current_frame') and self.current_frame is not None:
            print("DEBUG: [CameraView] Refreshing display using current_frame")
            # Force re-render of current processed frame
            self._show_frame_with_zoom()
            return True
        else:
            print("DEBUG: [CameraView] No frame available for format refresh")
            return False

    def display_frame(self, frame):
        """
        Hiển thị frame từ camera (sử dụng background thread cho xử lý)
        
        Args:
            frame: Numpy array chứa hình ảnh từ camera (có thể là BGR, RGB, YUV420, etc.)
        """
        if frame is None or frame.size == 0:
            logging.error("Invalid frame received")
            return

        logging.debug("Frame received with shape: %s", frame.shape)
        print(f"DEBUG: [display_frame] Frame received: shape={frame.shape}, worker={self.camera_display_worker is not None}")
        
        # Store raw frame for display mode switching
        self.current_raw_frame = frame.copy()
        
        # Send frame to worker thread for processing
        if self.camera_display_worker:
            print(f"DEBUG: [display_frame] Adding frame to worker queue")
            self.camera_display_worker.add_frame(frame)
        else:
            # Fallback to synchronous processing if worker not available
            print(f"DEBUG: [display_frame] Worker is None! Thread: {self.camera_display_thread}, Running: {self.camera_display_thread.isRunning() if self.camera_display_thread else 'None'}")
            logging.warning("Camera display worker not available, using synchronous processing")
            self._display_frame_sync(frame)
    
    def _get_display_frame_from_raw(self, raw_frame):
        """Get display frame from raw frame based on current display mode (thread-safe)"""
        try:
            # Store current raw frame temporarily
            temp_raw_frame = self.current_raw_frame
            self.current_raw_frame = raw_frame
            
            # Get display frame
            display_frame = self._get_display_frame()
            
            # Restore previous raw frame
            self.current_raw_frame = temp_raw_frame
            
            return display_frame
            
        except Exception as e:
            logging.error(f"Error getting display frame from raw: {e}")
            return None
    
    def _display_frame_sync(self, frame):
        """Fallback synchronous frame display method"""
        try:
            # Use existing synchronous processing logic
            display_frame = self._get_display_frame()
            frame_to_process = display_frame if display_frame is not None else frame
            
            # Handle frame format conversion (simplified version)
            if len(frame_to_process.shape) == 3 and frame_to_process.shape[2] >= 3:
                if frame_to_process.shape[2] == 4:
                    frame_to_process = cv2.cvtColor(frame_to_process, cv2.COLOR_RGBA2RGB)
            elif len(frame_to_process.shape) == 2:
                frame_to_process = cv2.cvtColor(frame_to_process, cv2.COLOR_GRAY2RGB)
            
            self.current_frame = frame_to_process
            
            # Display the frame without changing zoom level
            self._show_frame_with_zoom()
            self._calculate_fps()
            
        except Exception as e:
            logging.error(f"Error in synchronous frame display: {e}")
        
    def _run_job_processing(self, frame):
        """
        Run job manager processing on current frame - DISABLED to avoid duplicate execution
        CameraManager now handles job processing directly.
        
        Args:
            frame: Current frame to process
        """
        # DISABLED: CameraManager now handles job processing to avoid duplicate execution
        logging.debug("CameraView: _run_job_processing disabled - CameraManager handles jobs")
        return
    
    def _store_processed_frames(self, tool_results):
        """Store processed frames from job results for display mode switching"""
        try:
            for tool_name, tool_result in tool_results.items():
                # tool_result format from job_manager: (result_image, result_data)
                if isinstance(tool_result, tuple) and len(tool_result) == 2:
                    result_image, result_data = tool_result
                    if result_image is not None:
                        # Determine tool type and store accordingly
                        if 'detect' in tool_name.lower():
                            tool_key = f"detection_detect_tool"
                            self.processed_frames[tool_key] = result_image
                            print(f"DEBUG: [CameraView] Stored processed frame for {tool_key}")
                        elif 'classification' in tool_name.lower():
                            tool_key = f"classification_classification_tool"
                            self.processed_frames[tool_key] = result_image
                            print(f"DEBUG: [CameraView] Stored processed frame for {tool_key}")
                        elif 'edge' in tool_name.lower():
                            tool_key = f"edge_edge_tool"
                            self.processed_frames[tool_key] = result_image
                            print(f"DEBUG: [CameraView] Stored processed frame for {tool_key}")
                        elif 'ocr' in tool_name.lower():
                            tool_key = f"ocr_ocr_tool"
                            self.processed_frames[tool_key] = result_image
                            print(f"DEBUG: [CameraView] Stored processed frame for {tool_key}")
                # Also handle dict format with 'data' field (fallback)
                elif isinstance(tool_result, dict) and 'processed_frame' in tool_result:
                    processed_frame = tool_result['processed_frame']
                    if processed_frame is not None:
                        if 'detect' in tool_name.lower():
                            tool_key = f"detection_detect_tool"
                            self.processed_frames[tool_key] = processed_frame
                            print(f"DEBUG: [CameraView] Stored processed frame for {tool_key} (dict format)")
        except Exception as e:
            logging.error(f"Error storing processed frames: {e}")
    
    def _draw_detection_boxes_on_pixmap(self, pixmap):
        """
        Draw detection bounding boxes on pixmap
        
        Args:
            pixmap: QPixmap to draw on
        """
        try:
            painter = QPainter(pixmap)
            
            # Set pen for bounding boxes
            pen = QPen(QColor(255, 0, 0), 2)  # Red color, 2px width
            painter.setPen(pen)
            
            # Set font for labels
            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            
            for detection in self.detection_results:
                bbox = detection.get('bbox', [])
                if len(bbox) >= 4:
                    x1, y1, x2, y2 = bbox
                    
                    # Draw bounding box
                    painter.drawRect(x1, y1, x2 - x1, y2 - y1)
                    
                    # Prepare label text
                    class_name = detection.get('class_name', 'Unknown')
                    confidence = detection.get('confidence', 0)
                    label = f"{class_name}: {confidence:.2f}"
                    
                    # Draw label background
                    label_rect = painter.fontMetrics().boundingRect(label)
                    label_rect.moveTopLeft(QPoint(x1, y1 - label_rect.height() - 2))
                    painter.fillRect(label_rect, QColor(255, 0, 0, 180))  # Semi-transparent red
                    
                    # Draw label text
                    painter.setPen(QColor(255, 255, 255))  # White text
                    painter.drawText(label_rect, Qt.AlignCenter, label)
                    
                    # Reset pen for next box
                    painter.setPen(pen)
            
            painter.end()
            logging.debug(f"Drew {len(self.detection_results)} detection boxes")
            
        except Exception as e:
            logging.error(f"Error drawing detection boxes: {e}")
    
    def _handle_detection_results(self, results, processed_frame):
        """
        Handle detection results and display bounding boxes
        
        Args:
            results: Results from job execution
            processed_frame: Processed frame from detection
        """
        try:
            logging.info(f"=== HANDLING DETECTION RESULTS ===")
            logging.info(f"Results keys: {list(results.keys())}")
            
            # Find detection results
            detection_results = None
            for tool_name, tool_result in results.items():
                logging.info(f"Tool: {tool_name}, Result type: {type(tool_result)}")
                if isinstance(tool_result, dict):
                    logging.info(f"Tool {tool_name} result keys: {list(tool_result.keys())}")
                    if 'detect' in tool_name.lower() and 'data' in tool_result:
                        detection_results = tool_result['data']
                        logging.info(f"Found detection data in {tool_name}")
                        break
                    elif 'detect' in tool_name.lower() and 'detections' in tool_result:
                        detection_results = tool_result
                        logging.info(f"Found direct detections in {tool_name}")
                        break
            
            if detection_results and 'detections' in detection_results:
                detections = detection_results['detections']
                logging.info(f"=== FOUND {len(detections)} DETECTIONS ===")
                
                for i, det in enumerate(detections):
                    logging.info(f"Detection {i+1}: {det}")
                
                # Store detection results for visualization
                self.detection_results = detections
                logging.info(f"Stored {len(detections)} detections for visualization")
                
                # Force refresh display to show detection boxes
                self._show_frame_with_zoom()
                logging.info("Refreshed frame display to show detections")
            else:
                logging.warning("No detection results found in job output")
                logging.info(f"Available data: {results}")
                
        except Exception as e:
            logging.error(f"Error handling detection results: {e}")
            import traceback
            traceback.print_exc()

    def _calculate_fps(self):
        """
        Tính toán và cập nhật FPS
        """
        try:
            # Tính toán độ sắc nét sử dụng Laplacian
            if self.current_frame is not None:
                gray = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2GRAY)
                sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
                sharpness_norm = min(int(sharpness / 10), 100)  # Chuẩn hóa về 0-100
                self.focus_calculated.emit(sharpness_norm)
                logging.debug("Sharpness calculated: %d", sharpness_norm)
        except Exception as e:
            logging.error("Error calculating sharpness: %s", e)
            
    def _calculate_fps(self):
        """
        Tính toán và cập nhật FPS
        """
        current_time = time.time()
        if self.prev_frame_time > 0:
            # Tính FPS tức thời
            instant_fps = 1 / (current_time - self.prev_frame_time)
            
            # Áp dụng trung bình động để làm mượt giá trị FPS
            if self.fps > 0:
                self.fps = self.fps_alpha * self.fps + (1 - self.fps_alpha) * instant_fps
            else:
                self.fps = instant_fps
                
            # Phát tín hiệu cập nhật FPS
            self.fps_updated.emit(self.fps)
            
        self.prev_frame_time = current_time

    def _show_frame_with_zoom(self):
        """
        Hiển thị frame hiện tại với mức zoom và xoay đã cài đặt
        """
        print(f"DEBUG: [CameraView] _show_frame_with_zoom called, zoom_level={self.zoom_level}")
        
        # Check if we're in trigger mode
        in_trigger_mode = self._is_in_trigger_mode()
        
        # If no current frame and not in trigger mode, we can't continue
        if self.current_frame is None and not in_trigger_mode:
            logging.warning("No current frame to display and not in trigger mode")
            return
            
        # Handle different display scenarios
        # Case 1: We're in trigger mode and need to use existing or create blank pixmap
        if self.current_frame is None and in_trigger_mode:
            print("DEBUG: [CameraView] In trigger mode with no frame")
            
            try:
                # Use the last valid pixmap if available
                if hasattr(self, 'pixmap_item') and self.pixmap_item is not None and self.pixmap_item.pixmap() and not self.pixmap_item.pixmap().isNull():
                    print("DEBUG: [CameraView] Using existing pixmap in trigger mode")
                    pixmap = self.pixmap_item.pixmap()
                    
                    # Update the scene
                    self.scene.setSceneRect(self.pixmap_item.boundingRect())
                    
                # Or use the last valid QImage if available
                elif hasattr(self, 'last_valid_qimage') and self.last_valid_qimage is not None and not self.last_valid_qimage.isNull():
                    print("DEBUG: [CameraView] Using last_valid_qimage in trigger mode")
                    pixmap = QPixmap.fromImage(self.last_valid_qimage)
                    
                    # Create or update pixmap item
                    if self.pixmap_item is not None:
                        self.scene.removeItem(self.pixmap_item)
                    self.pixmap_item = QGraphicsPixmapItem(pixmap)
                    self.scene.addItem(self.pixmap_item)
                    
                # Last resort: create a blank pixmap
                else:
                    print("DEBUG: [CameraView] Creating blank pixmap for trigger mode")
                    pixmap = QPixmap(1440, 1080)
                    pixmap.fill(Qt.black)
                    
                    # Create or update pixmap item
                    if self.pixmap_item is not None:
                        self.scene.removeItem(self.pixmap_item)
                    self.pixmap_item = QGraphicsPixmapItem(pixmap)
                    self.scene.addItem(self.pixmap_item)
                
                # Make sure pixmap is in scene
                self.scene.setSceneRect(self.pixmap_item.boundingRect())
                
                # Apply zoom transform but don't reset zoom level
                self.graphics_view.resetTransform()
                self.graphics_view.scale(self.zoom_level, self.zoom_level)
                return
            except Exception as e:
                print(f"DEBUG: [CameraView] Error in trigger mode display: {e}")
                # Continue to normal frame display

        # Case 2: Normal display with actual frame
        try:
            # Process current frame if available
            if self.current_frame is not None:
                print("DEBUG: [CameraView] Processing actual frame")
                h, w, ch = self.current_frame.shape
                bytes_per_line = ch * w
                
                # Determine pixel format from camera stream
                pixel_format = 'BGR888'  # Default fallback
                try:
                    mw = getattr(self, 'main_window', None)
                    cm = getattr(mw, 'camera_manager', None) if mw else None
                    cs = getattr(cm, 'camera_stream', None) if cm else None
                    if cs is not None and hasattr(cs, 'get_pixel_format'):
                        pixel_format = cs.get_pixel_format()
                except Exception as e:
                    print(f"DEBUG: [CameraView] Error getting pixel format: {e}")
                
                # Convert frame based on channel count and format
                if ch == 3:  # 3-channel image (BGR or RGB)
                    # Debug info
                    debug_print(f"Current pixel_format: '{pixel_format}'", "[CameraView]")
                    
                    # Convert frame to RGB for display
                    if str(pixel_format) == 'RGB888':
                        # PiCamera2 quirk: returns BGR even when set to RGB
                        debug_print("PiCamera2 RGB888 config: Converting BGR->RGB", "[CameraView]")
                        rgb_image = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
                    else:
                        # Standard BGR conversion
                        debug_print("Frame BGR888, converting to RGB", "[CameraView]")
                        rgb_image = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
                    
                elif ch == 4:  # 4-channel image (BGRA or RGBA)
                    # Debug info
                    debug_print(f"4-channel pixel_format: '{pixel_format}'", "[CameraView]")
                    
                    # Handle 4-channel formats
                    if str(pixel_format) in ('XRGB8888', 'XBGR8888'):
                        # PiCamera2 XBGR8888 returns BGRX data (or XBGR format)
                        debug_print(f"PiCamera2 {pixel_format} config: Converting BGRA->RGB", "[CameraView]")
                        rgb_image = cv2.cvtColor(self.current_frame, cv2.COLOR_BGRA2RGB)
                    else:
                        # Unknown 4-channel format, assume BGRA
                        debug_print(f"4-channel frame, converting BGRA->RGB", "[CameraView]")
                        rgb_image = cv2.cvtColor(self.current_frame, cv2.COLOR_BGRA2RGB)
                else:
                    # Fallback for other channel counts
                    try:
                        rgb_image = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
                    except Exception:
                        rgb_image = self.current_frame  # Use as-is if conversion fails
                
                # Create Qt image and pixmap from RGB data
                if 'rgb_image' in locals() and rgb_image is not None:
                    qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    
                    # Store last valid QImage for trigger mode
                    self.last_valid_qimage = qt_image.copy()
                    
                    # Create pixmap from QImage
                    pixmap = QPixmap.fromImage(qt_image)
                    
                    # Draw FPS if enabled
                    if self.show_fps and self.fps > 0:
                        painter = QPainter(pixmap)
                        font = QFont()
                        font.setPointSize(14)
                        painter.setFont(font)
                        painter.setPen(QColor(0, 255, 0))  # Green color
                        painter.drawText(10, 30, f"FPS: {self.fps:.1f}")
                        painter.end()
                else:
                    # No valid RGB image - fallback to last valid image or blank
                    if hasattr(self, 'last_valid_qimage') and self.last_valid_qimage is not None and not self.last_valid_qimage.isNull():
                        pixmap = QPixmap.fromImage(self.last_valid_qimage)
                        print("DEBUG: [CameraView] Using last valid QImage as fallback")
                    elif hasattr(self, 'pixmap_item') and self.pixmap_item is not None and not self.pixmap_item.pixmap().isNull():
                        pixmap = self.pixmap_item.pixmap()
                        print("DEBUG: [CameraView] Using existing pixmap as fallback")
                    else:
                        # Create a minimal blank pixmap
                        pixmap = QPixmap(1440, 1080)
                        pixmap.fill(Qt.black)
                        print("DEBUG: [CameraView] Created blank pixmap as fallback")
            else:
                # No current frame - should not happen as we already handled trigger mode case
                print("DEBUG: [CameraView] Unexpected: No frame available in normal display path")
                return
            
            # Draw detection overlays if enabled
            if 'pixmap' in locals() and self.show_detection_overlay and self.detection_results:
                print("DEBUG: [CameraView] Drawing detection boxes on pixmap")
                self._draw_detection_boxes_on_pixmap(pixmap)

            # Update the pixmap in the scene
            try:
                # Remove existing pixmap item if it exists
                if self.pixmap_item is not None:
                    if self.pixmap_item.scene() is not None:
                        self.scene.removeItem(self.pixmap_item)
                    self.pixmap_item = None
                
                # Create new pixmap item
                if 'pixmap' in locals() and pixmap is not None:
                    self.pixmap_item = QGraphicsPixmapItem(pixmap)
                    self.pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
                    
                    # Set pixmap_item at lowest z-level so detection areas appear above
                    self.pixmap_item.setZValue(-1)
                    self.scene.addItem(self.pixmap_item)

                    # Set rotation origin point to center of pixmap
                    self.pixmap_item.setTransformOriginPoint(
                        self.pixmap_item.boundingRect().width() / 2,
                        self.pixmap_item.boundingRect().height() / 2
                    )

                    # Apply rotation angle
                    self.pixmap_item.setRotation(self.rotation_angle)

                    # Calculate scene rectangle to include pixmap and any detection areas
                    scene_rect = self.pixmap_item.boundingRect()
                    
                    # Expand scene rect to include detection areas
                    if hasattr(self, 'saved_areas') and self.saved_areas:
                        for area in self.saved_areas:
                            if area.scene() == self.scene:
                                scene_rect = scene_rect.united(area.boundingRect())
                    
                    if hasattr(self, 'current_area') and self.current_area and self.current_area.scene() == self.scene:
                        scene_rect = scene_rect.united(self.current_area.boundingRect())
                    
                    # Update scene rect
                    self.scene.setSceneRect(scene_rect)

                    # Center view on pixmap for initial display or when zoomed out
                    pixmap_center = self.pixmap_item.boundingRect().center()
                    if (not self._has_drawn_once) or self.fit_on_next_frame or (self.zoom_level <= 1.0):
                        self.graphics_view.centerOn(pixmap_center)
                    
                    # Set proper alignment
                    self.graphics_view.setAlignment(Qt.AlignmentFlag.AlignCenter)

                    # Set appropriate drag mode based on zoom level
                    if not hasattr(self, 'draw_mode') or not self.draw_mode:
                        if self.zoom_level > 1.0:
                            self.graphics_view.setDragMode(QGraphicsView.ScrollHandDrag)
                            self.graphics_view.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
                        else:
                            self.graphics_view.setDragMode(QGraphicsView.NoDrag)
                            self.graphics_view.viewport().setCursor(Qt.CursorShape.ArrowCursor)

                    # Only apply zoom transform if the zoom has been changed or it's the first frame
                    if not hasattr(self, '_has_drawn_once') or not self._has_drawn_once or hasattr(self, '_zoom_changed') and self._zoom_changed:
                        print("DEBUG: [CameraView] Applying zoom transform due to manual change or first frame")
                        
                        # Apply zoom transform
                        self.graphics_view.resetTransform()
                        self.graphics_view.scale(self.zoom_level, self.zoom_level)
                        
                        # Clear the zoom changed flag after applying zoom
                        self._zoom_changed = False
                    
                    # Handle fit to view if needed
                    if hasattr(self, 'fit_on_next_frame') and self.fit_on_next_frame:
                        self.graphics_view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
                        self.zoom_level = 1.1  # Đặt mức zoom mặc định cao hơn 1 mức
                        self.fit_on_next_frame = False
                    
                    # Mark that we've drawn at least once
                    self._has_drawn_once = True
                    
                    # Log frame display
                    print(f"DEBUG: [CameraView] Frame displayed with zoom={self.zoom_level}, rotation={self.rotation_angle}")
                else:
                    print("ERROR: [CameraView] No valid pixmap to display")
            except Exception as e:
                logging.error(f"Error updating pixmap in scene: {e}")
        except Exception as e:
            logging.error(f"Error in frame display: {e}")
            print(f"DEBUG: [CameraView] Exception in _show_frame_with_zoom: {e}")

    def _is_in_trigger_mode(self):
        """Check if camera is in trigger mode"""
        try:
            if hasattr(self, 'in_trigger_mode'):
                return self.in_trigger_mode
                
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'camera_manager'):
                cs = self.main_window.camera_manager.camera_stream
                if cs and hasattr(cs, 'external_trigger_enabled'):
                    return cs.external_trigger_enabled
        except Exception:
            pass
        return False
    
    def _apply_zoom(self, new_zoom_level):
        """
        Apply a specific zoom level to the view (internal method)
        
        This is the core implementation of zoom functionality that directly
        manipulates the QGraphicsView transform.
        
        Args:
            new_zoom_level: The absolute zoom level to apply (not incremental)
            
        Returns:
            True if successful, False if an error occurred
            
        Note:
            - Uses absolute transforms (resetTransform + scale) to prevent accumulated errors
            - Updates drag mode based on zoom level to enable panning when zoomed in
            - Ensures zoom level stays within reasonable bounds (0.25 to 5.0)
        """
        try:
            print(f"DEBUG: [CameraView] Applying zoom level: {new_zoom_level}")
            
            # Validate zoom level within bounds
            if new_zoom_level < 0.25:
                print(f"DEBUG: [CameraView] Zoom level too small ({new_zoom_level}), using 0.25")
                new_zoom_level = 0.25
            elif new_zoom_level > 5.0:
                print(f"DEBUG: [CameraView] Zoom level too large ({new_zoom_level}), using 5.0")
                new_zoom_level = 5.0
            
            # Store the old zoom level for debugging
            old_zoom = self.zoom_level
            
            # Update the zoom level
            self.zoom_level = new_zoom_level
            
            # Direct approach: reset transform and apply absolute scale
            # This prevents accumulated transform errors
            self.graphics_view.resetTransform()
            self.graphics_view.scale(self.zoom_level, self.zoom_level)
            
            # Clear the zoom changed flag after applying zoom
            self._zoom_changed = False
            
            # Center on the image if we have a pixmap
            if hasattr(self, 'pixmap_item') and self.pixmap_item is not None:
                # Only recenter if significantly zooming in from 1.0 or zooming out to 1.0
                if (old_zoom <= 1.0 and new_zoom_level > 1.0) or (old_zoom > 1.0 and new_zoom_level <= 1.0):
                    self.graphics_view.centerOn(self.pixmap_item)
                
            print(f"DEBUG: [CameraView] Zoom applied: {old_zoom} -> {self.zoom_level}")
            
            # Update drag mode based on zoom level
            if self.zoom_level > 1.0:
                # Enable drag mode when zoomed in to allow panning
                self.graphics_view.setDragMode(QGraphicsView.ScrollHandDrag)
                self.graphics_view.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                # Disable drag mode when at normal zoom
                self.graphics_view.setDragMode(QGraphicsView.NoDrag)
                self.graphics_view.viewport().setCursor(Qt.CursorShape.ArrowCursor)
                
            return True
        except Exception as e:
            print(f"DEBUG: [CameraView] Error applying zoom: {e}")
            return False
    
    def zoom_in(self):
        """
        Increase zoom level and apply to the view
        
        This is the primary implementation of zoom-in functionality.
        1. Called either directly or via CameraManager.zoom_in
        2. Applies throttling to prevent rapid zoom operations
        3. Schedules the actual zoom application via QTimer to ensure UI thread execution
        4. Uses _apply_zoom to perform the actual transformation
        """
        print("DEBUG: [CameraView] zoom_in called, current level:", self.zoom_level)
        
        # Use PyQt's QTimer to schedule zoom operation in the main thread's event loop
        from PyQt5.QtCore import QTimer
        
        # Simple throttling to prevent rapid zoom operations
        current_time = time.time()
        if hasattr(self, '_last_zoom_time') and (current_time - self._last_zoom_time) < 0.2:
            print("DEBUG: [CameraView] Zoom operation too frequent, ignoring")
            return
            
        self._last_zoom_time = current_time
        
        # Calculate new zoom level with upper limit
        new_zoom = min(5.0, self.zoom_level + self.zoom_step)
        
        # Set flag to indicate zoom was manually changed
        self._zoom_changed = True
        
        # Use single-shot timer to ensure operation runs on the main UI thread
        QTimer.singleShot(10, lambda: self._apply_zoom(new_zoom))

    def zoom_out(self):
        """
        Decrease zoom level and apply to the view
        
        This is the primary implementation of zoom-out functionality.
        1. Called either directly or via CameraManager.zoom_out
        2. Applies throttling to prevent rapid zoom operations
        3. Schedules the actual zoom application via QTimer to ensure UI thread execution
        4. Uses _apply_zoom to perform the actual transformation
        """
        print("DEBUG: [CameraView] zoom_out called, current level:", self.zoom_level)
        
        # Use PyQt's QTimer to schedule zoom operation in the main thread's event loop
        from PyQt5.QtCore import QTimer
        
        # Simple throttling to prevent rapid zoom operations
        current_time = time.time()
        if hasattr(self, '_last_zoom_time') and (current_time - self._last_zoom_time) < 0.2:
            print("DEBUG: [CameraView] Zoom operation too frequent, ignoring")
            return
            
        self._last_zoom_time = current_time
        
        # Calculate new zoom level with lower limit
        new_zoom = max(0.1, self.zoom_level - self.zoom_step)
        
        # Set flag to indicate zoom was manually changed
        self._zoom_changed = True
        
        # Use single-shot timer to ensure operation runs on the main UI thread
        QTimer.singleShot(10, lambda: self._apply_zoom(new_zoom))
        
    def register_zoom_events(self):
        """Register zoom and pan event handlers"""
        try:
            # Make sure graphics_view is initialized
            if not hasattr(self, 'graphics_view') or self.graphics_view is None:
                print("DEBUG: [CameraView] Cannot register zoom events - graphics_view not initialized")
                return False
            
            # Set up wheel event handling for zoom
            if not hasattr(self, '_original_wheel_event'):
                self._original_wheel_event = self.graphics_view.wheelEvent
                
                def _wheel_zoom_event(event):
                    """Handle wheel events for zoom"""
                    if event.modifiers() & Qt.ControlModifier:
                        # Calculate zoom factor based on wheel delta
                        angle_delta = event.angleDelta().y()
                        if angle_delta > 0:
                            # Zoom in
                            new_zoom = min(5.0, self.zoom_level * 1.1)
                            self._apply_zoom(new_zoom)
                        else:
                            # Zoom out
                            new_zoom = max(0.1, self.zoom_level / 1.1)
                            self._apply_zoom(new_zoom)
                        event.accept()
                    else:
                        # Use original wheel behavior for scrolling
                        self._original_wheel_event(event)
                
                # Install custom wheel handler
                self.graphics_view.wheelEvent = _wheel_zoom_event
                print("DEBUG: [CameraView] Registered wheel zoom event handler")
            
            return True
        except Exception as e:
            print(f"DEBUG: [CameraView] Error registering zoom events: {e}")
            return False

    def rotate_left(self):
        """
        Xoay ngược chiều kim đồng hồ 90 độ
        """
        self.rotation_angle = (self.rotation_angle - 90) % 360
        
        # Apply the transform directly
        self.graphics_view.resetTransform()
        self.graphics_view.scale(self.zoom_level, self.zoom_level)
        self.graphics_view.rotate(self.rotation_angle)

    def rotate_right(self):
        """
        Xoay theo chiều kim đồng hồ 90 độ
        """
        self.rotation_angle = (self.rotation_angle + 90) % 360
        
        # Apply the transform directly
        self.graphics_view.resetTransform()
        self.graphics_view.scale(self.zoom_level, self.zoom_level)
        self.graphics_view.rotate(self.rotation_angle)

    def reset_view(self):
        """
        Đặt lại mức zoom và xoay về mặc định
        
        Phương thức này reset hoàn toàn view về trạng thái mặc định:
        - Đặt zoom_level về 1.1
        - Đặt góc xoay về 0
        - Reset transform
        - Căn giữa hình ảnh
        """
        print("DEBUG: [CameraView] reset_view called")
        
        # Đặt lại các thông số
        self.zoom_level = 1.1  # Reset về mức zoom mặc định đã được tăng 1 mức
        self.rotation_angle = 0
        self._zoom_changed = True  # Đảm bảo transform được áp dụng
        
        # Reset transform trực tiếp
        self.graphics_view.resetTransform()
        
        # Đặt lại chế độ drag khi zoom về mặc định
        self.graphics_view.setDragMode(QGraphicsView.NoDrag)
        self.graphics_view.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        
        # Căn giữa hình ảnh
        if hasattr(self, 'scene') and self.scene is not None and self.scene.sceneRect().isValid():
            self.graphics_view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self.fit_on_next_frame = False
        else:
            self.fit_on_next_frame = True
            
        print(f"DEBUG: [CameraView] View reset to zoom={self.zoom_level}, rotation={self.rotation_angle}")

    def fit_to_view(self):
        """
        Phóng to/thu nhỏ để vừa khung nhìn
        """
        self.fit_on_next_frame = True
        self.zoom_level = 1.1  # Đảm bảo mức zoom đúng ngay cả khi fit to view
        self._show_frame_with_zoom()

    def get_current_frame(self):
        """
        Lấy frame hiện tại
        
        Returns:
            Numpy array chứa frame hiện tại hoặc None nếu không có
        """
        return self.current_frame

    def handle_resize_event(self):
        """
        Xử lý sự kiện khi view được resize
        """
        # Nếu đang ở chế độ fit, fit lại khi resize
        if self.fit_on_next_frame:
            self.graphics_view.fitInView(self.graphics_view.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self.zoom_level = 1.1  # Đảm bảo mức zoom mặc định được duy trì
            self.fit_on_next_frame = False
            
    def toggle_fps_display(self, show_fps):
        """
        Bật/tắt hiển thị FPS
        
        Args:
            show_fps: Boolean cho biết có hiển thị FPS hay không
        """
        self.show_fps = show_fps
        # Cập nhật lại hiển thị nếu có frame
        if self.current_frame is not None:
            self._show_frame_with_zoom()
            
    def display_frame_with_ocr_boxes(self, frame, boxes):
        """
        Hiển thị frame với các box OCR được vẽ lên
        
        Args:
            frame: Numpy array chứa hình ảnh BGR từ camera
            boxes: Danh sách các box OCR, mỗi box là một mảng các điểm
        """
        if frame is None or frame.size == 0:
            logging.error("Invalid frame received for OCR boxes")
            return

        try:
            # Chuyển đổi frame thành QPixmap
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            
            # Vẽ các box OCR lên pixmap
            painter = QPainter(pixmap)
            pen = QPen(QColor(0, 255, 0), 2)  # Màu xanh lá, độ dày 2px
            painter.setPen(pen)
            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            
            for idx, box in enumerate(boxes):
                pts = [tuple(map(int, pt)) for pt in box]
                # Vẽ đa giác nối các điểm
                for i in range(4):
                    painter.drawLine(pts[i][0], pts[i][1], pts[(i+1)%4][0], pts[(i+1)%4][1])
                # Vẽ chỉ số box
                painter.drawText(pts[0][0], pts[0][1]-5, f"Box {idx+1}")
            
            # Vẽ FPS nếu được bật
            if self.show_fps and self.fps > 0:
                painter.setPen(QColor(0, 255, 0))  # Màu xanh lá
                font = QFont()
                font.setPointSize(14)
                painter.setFont(font)
                painter.drawText(10, 30, f"FPS: {self.fps:.1f}")
                
            painter.end()

            # Cập nhật scene với pixmap mới
            if self.pixmap_item is not None:
                if self.pixmap_item.scene() is not None:
                    self.scene.removeItem(self.pixmap_item)
                self.pixmap_item = None

            self.pixmap_item = QGraphicsPixmapItem(pixmap)
            self.pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            self.scene.addItem(self.pixmap_item)

            # Đặt điểm xoay ở giữa pixmap
            self.pixmap_item.setTransformOriginPoint(w/2, h/2)
            
            # Áp dụng góc xoay
            self.pixmap_item.setRotation(self.rotation_angle)
            
            # Cập nhật kích thước scene
            self.scene.setSceneRect(0, 0, w, h)
            self.graphics_view.setSceneRect(0, 0, w, h)
            
            # Reset transform trước khi áp dụng zoom
            self.graphics_view.resetTransform()
            self.graphics_view.scale(self.zoom_level, self.zoom_level)
            
            # Căn giữa nếu pixmap đã được thêm vào scene
            if self.pixmap_item and self.pixmap_item.scene() == self.scene:
                self.graphics_view.centerOn(self.pixmap_item)
                
            self._calculate_fps()  # Cập nhật FPS
            
        except Exception as e:
            logging.error(f"Error displaying frame with OCR boxes: {e}")
    
    # ===== DRAWING MODE METHODS =====
    
    def set_draw_mode(self, enabled):
        """Enable/disable drawing mode"""
        self.draw_mode = enabled
        print(f"DEBUG: Drawing mode set to {enabled}")
        if enabled:
            # Khi vào draw mode, tắt selection và set cursor
            self.graphics_view.setDragMode(QGraphicsView.NoDrag)
            self.graphics_view.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        else:
            # Khi thoát draw mode, cho phép selection và interaction
            if self.zoom_level > 1.0:
                self.graphics_view.setDragMode(QGraphicsView.ScrollHandDrag)
            else:
                self.graphics_view.setDragMode(QGraphicsView.RubberBandDrag)
            self.graphics_view.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            self.drawing = False
            self.start_point = None
            self.end_point = None
    
    def _mouse_press_event(self, event):
        """Handle mouse press events for drawing"""
        if self.draw_mode and event.button() == Qt.MouseButton.LeftButton:
            # Convert screen coordinates to scene coordinates
            scene_pos = self.graphics_view.mapToScene(event.pos())
            self.start_point = (scene_pos.x(), scene_pos.y())
            self.drawing = True
            print(f"DEBUG: Started drawing at {self.start_point}")
        else:
            # Call original handler for normal interaction
            self._original_mouse_press(event)
    
    def _mouse_move_event(self, event):
        """Handle mouse move events for drawing"""
        if self.draw_mode and self.drawing:
            scene_pos = self.graphics_view.mapToScene(event.pos())
            self.end_point = (scene_pos.x(), scene_pos.y())
            self._update_current_area()
        else:
            # Call original handler for normal interaction
            self._original_mouse_move(event)
    
    def _mouse_release_event(self, event):
        """Handle mouse release events for drawing"""
        if self.draw_mode and self.drawing and event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.graphics_view.mapToScene(event.pos())
            self.end_point = (scene_pos.x(), scene_pos.y())
            self.drawing = False
            
            if self.start_point and self.end_point:
                # Calculate final area coordinates
                x1, y1 = self.start_point
                x2, y2 = self.end_point
                
                # Ensure x1 < x2 and y1 < y2
                x1, x2 = min(x1, x2), max(x1, x2)
                y1, y2 = min(y1, y2), max(y1, y2)
                
                # Create new overlay for drawing
                rect = QRectF(x1, y1, x2-x1, y2-y1)
                overlay = DetectionAreaOverlay(rect, camera_view=self)
                self.scene.addItem(overlay)
                
                # Set as current for editing
                self.current_overlay = overlay
                self.overlays[overlay.tool_id] = overlay
                
                # Set edit mode for immediate editing
                overlay.set_edit_mode(True)
                self.overlay_edit_mode = True
                
                print(f"DEBUG: Created detection area overlay #{overlay.tool_id}: ({x1}, {y1}) to ({x2}, {y2})")
                
                # Emit the area_drawn signal with tool_id
                self.area_drawn.emit(int(x1), int(y1), int(x2), int(y2))
        else:
            # Call original handler for normal interaction
            self._original_mouse_release(event)
    
    def _update_current_area(self):
        """Update the current drawing area visualization"""
        # This could be used to show real-time rectangle while drawing
        # For now, we'll implement it later if needed
        pass
    
    def add_detection_area(self, x1, y1, x2, y2, label="Detection Area"):
        """Add a detection area to be displayed on camera view"""
        # Use current editing tool ID if available
        tool_id = self.current_editing_tool_id
        print(f"DEBUG: add_detection_area called with tool_id: {tool_id}")
        
        if self.current_overlay:
            # Update existing overlay
            self.current_overlay.update_from_coords(x1, y1, x2, y2)
        else:
            # Create new overlay with correct tool ID
            rect = QRectF(x1, y1, x2-x1, y2-y1)
            self.current_overlay = DetectionAreaOverlay(rect, tool_id=tool_id, camera_view=self)
            self.scene.addItem(self.current_overlay)
            
            # Store in overlays dict if tool_id is available
            if tool_id is not None:
                self.overlays[self.current_overlay.tool_id] = self.current_overlay
                print(f"DEBUG: Added overlay with tool_id {self.current_overlay.tool_id} to overlays dict")
            
        print(f"DEBUG: Added detection area overlay: ({x1}, {y1}) to ({x2}, {y2})")
        return self.current_overlay
    
    def clear_detection_areas(self):
        """Clear all detection areas"""
        # Clear all overlays
        for overlay in self.overlays.values():
            if overlay.scene():
                self.scene.removeItem(overlay)
        self.overlays.clear()
        self.current_overlay = None
        self.overlay_edit_mode = False
        print("DEBUG: Cleared all detection area overlays")
        
    def clear_all_areas(self):
        """Alias for clear_detection_areas"""
        self.clear_detection_areas()
        
    def update_detection_areas_visibility(self):
        """Update visibility of detection areas based on current display mode"""
        print(f"DEBUG: [CameraView] Updating detection areas visibility, show_overlay: {self.show_detection_overlay}")
        
        # Update visibility for all overlays
        for tool_id, overlay in self.overlays.items():
            if overlay and hasattr(overlay, 'setVisible'):
                overlay.setVisible(self.show_detection_overlay)
                print(f"DEBUG: [CameraView] Set overlay {tool_id} visible: {self.show_detection_overlay}")
        
        # Update visibility for current overlay being drawn
        if self.current_overlay and hasattr(self.current_overlay, 'setVisible'):
            self.current_overlay.setVisible(self.show_detection_overlay)
            print(f"DEBUG: [CameraView] Set current overlay visible: {self.show_detection_overlay}")
        
    def add_tool_overlay(self, x1, y1, x2, y2, tool_id=None):
        """Add overlay for a specific tool"""
        rect = QRectF(x1, y1, x2-x1, y2-y1)
        overlay = DetectionAreaOverlay(rect, tool_id, camera_view=self)
        self.scene.addItem(overlay)
        self.overlays[overlay.tool_id] = overlay
        print(f"DEBUG: Added tool overlay #{overlay.tool_id}: ({x1}, {y1}) to ({x2}, {y2})")
        return overlay
        
    def remove_tool_overlay(self, tool_id):
        """Remove overlay for a specific tool"""
        if tool_id in self.overlays:
            overlay = self.overlays[tool_id]
            if overlay.scene():
                self.scene.removeItem(overlay)
            del self.overlays[tool_id]
            if self.current_overlay and self.current_overlay.tool_id == tool_id:
                self.current_overlay = None
            print(f"DEBUG: Removed tool overlay #{tool_id}")
            return True
        return False
        
    def edit_tool_overlay(self, tool_id):
        """Set a tool overlay to edit mode"""
        if tool_id in self.overlays:
            # Disable edit mode for all overlays
            for overlay in self.overlays.values():
                overlay.set_edit_mode(False)
            
            # Enable edit mode for selected overlay
            overlay = self.overlays[tool_id]
            overlay.set_edit_mode(True)
            self.current_overlay = overlay
            self.overlay_edit_mode = True
            print(f"DEBUG: Editing tool overlay #{tool_id}")
            return overlay
        return None
    
    def get_current_area_coords(self):
        """Get current area coordinates"""
        if self.current_overlay:
            return self.current_overlay.get_area_coords()
        return None
    
    def get_all_area_coords(self):
        """Get all detection area coordinates"""
        return [overlay.get_area_coords() for overlay in self.overlays.values()]
        
    def add_detection_area(self, x1, y1, x2, y2, label="Detection Area"):
        """Add a detection area to be displayed on camera view"""
        # Use current editing tool ID if available
        tool_id = getattr(self, 'current_editing_tool_id', None)
        print(f"DEBUG: [CameraView] add_detection_area using tool_id: {tool_id}")
        return self.add_tool_overlay(x1, y1, x2, y2, tool_id=tool_id)
        
    def get_tool_overlay_coords(self, tool_id):
        """Get coordinates for specific tool overlay"""
        if tool_id in self.overlays:
            return self.overlays[tool_id].get_area_coords()
        return None
        
    def set_overlay_edit_mode(self, enabled):
        """Bật/tắt edit mode cho overlay"""
        self.overlay_edit_mode = enabled
        if self.current_overlay:
            self.current_overlay.set_edit_mode(enabled)
            print(f"DEBUG: Overlay edit mode set to: {enabled}")
            
    def show_detection_area(self, x1, y1, x2, y2, editable=False):
        """Hiển thị detection area trên camera view"""
        if self.current_overlay:
            self.current_overlay.update_from_coords(x1, y1, x2, y2)
        else:
            rect = QRectF(x1, y1, x2-x1, y2-y1)
            self.current_overlay = DetectionAreaOverlay(rect, camera_view=self)
    
    def set_review_views(self, review_views):
        """Set reference to review views for frame history display"""
        self.review_views = review_views
        
        # Configure each review view for read-only display
        for i, review_view in enumerate(review_views):
            if review_view:
                # Disable user interactions
                review_view.setDragMode(review_view.NoDrag)
                review_view.setInteractive(False)
                review_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                review_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                
                # Disable zoom with mouse wheel
                review_view.wheelEvent = lambda event: None
                
                # Set background color
                review_view.setStyleSheet("background-color: #2b2b2b; border: 1px solid #555;")
                
        logging.info(f"Frame history: Connected to {len(review_views)} review views (read-only mode)")
    
    def set_review_labels(self, review_labels):
        """Set reference to review labels for displaying NG/OK status
        
        Args:
            review_labels: List of QLabel widgets [reviewLabel_1, reviewLabel_2, ..., reviewLabel_5]
        """
        self.review_labels = review_labels
        
        # Configure each review label for status display
        for i, label in enumerate(review_labels):
            if label:
                label.setAlignment(Qt.AlignCenter)
                label.setStyleSheet("font-weight: bold; font-size: 12px; color: white;")
        
        logging.info(f"Frame history: Connected to {len(review_labels)} review labels for NG/OK display")
    
    
    def update_frame_history(self, frame):
        """Add frame to history queue for background processing (thread-safe)"""
        try:
            # Skip frame history if disabled for performance
            if not self.enable_frame_history or frame is None:
                return
            
            # DEBUG: Log frame arrival
            logging.info(f"[FrameHistory] New frame received: shape={frame.shape if frame is not None else 'None'}, queue_size_before={len(self.frame_history_queue)}")
            
            # Resize frame for history to improve memory and performance
            import cv2
            history_frame = frame
            h, w = frame.shape[:2]
            
            # Resize frames larger than 1440x1080 for history storage
            if h > 1080 or w > 1440:
                aspect_ratio = w / h
                if aspect_ratio > 1:  # Landscape
                    new_w, new_h = 1440, int(1440 / aspect_ratio)
                else:  # Portrait
                    new_w, new_h = int(1080 * aspect_ratio), 1080
                history_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            
            # Add frame to queue for background processing
            with self.frame_history_lock:
                # Add frame to queue (keep only latest few frames in queue)
                self.frame_history_queue.append(history_frame.copy())
                # Limit queue size to prevent memory buildup
                if len(self.frame_history_queue) > 3:
                    self.frame_history_queue.pop(0)
            
            # DEBUG: Log queue state after add
            logging.debug(f"[FrameHistory] Queue updated: size={len(self.frame_history_queue)}")
            
        except Exception as e:
            logging.error(f"Error updating frame history: {e}")
    
    def _start_frame_history_worker(self):
        """Start the frame history worker thread"""
        try:
            if self.frame_history_thread is not None:
                return  # Already started
            
            # Create worker and thread
            self.frame_history_worker = FrameHistoryWorker(self)
            self.frame_history_thread = QThread()
            
            # Move worker to thread
            self.frame_history_worker.moveToThread(self.frame_history_thread)
            
            # Connect signals
            self.frame_history_thread.started.connect(self.frame_history_worker.process_frame_history)
            
            # Start thread
            self.frame_history_thread.start()
            logging.info("Frame history worker thread started")
            
        except Exception as e:
            logging.error(f"Error starting frame history worker: {e}")
    
    def _stop_frame_history_worker(self):
        """Stop the frame history worker thread"""
        try:
            if self.frame_history_worker:
                self.frame_history_worker.stop()
            
            if self.frame_history_thread and self.frame_history_thread.isRunning():
                self.frame_history_thread.quit()
                self.frame_history_thread.wait(5000)  # Wait up to 5 seconds
                
            self.frame_history_worker = None
            self.frame_history_thread = None
            logging.info("Frame history worker thread stopped")
            
        except Exception as e:
            logging.error(f"Error stopping frame history worker: {e}")
    
    def _start_camera_display_worker(self):
        """Start the camera display worker thread"""
        try:
            print(f"DEBUG: [_start_camera_display_worker] Starting worker, thread={self.camera_display_thread}")
            if self.camera_display_thread is not None:
                print(f"DEBUG: [_start_camera_display_worker] Worker already started, returning")
                return  # Already started
            
            # Create worker and thread
            print(f"DEBUG: [_start_camera_display_worker] Creating CameraDisplayWorker")
            self.camera_display_worker = CameraDisplayWorker(self)
            self.camera_display_thread = QThread()
            
            # Move worker to thread
            print(f"DEBUG: [_start_camera_display_worker] Moving worker to thread")
            self.camera_display_worker.moveToThread(self.camera_display_thread)
            
            # Connect signals
            print(f"DEBUG: [_start_camera_display_worker] Connecting signals")
            self.camera_display_thread.started.connect(self.camera_display_worker.process_frames)
            self.camera_display_worker.frameProcessed.connect(self._handle_processed_frame)
            
            # Start thread
            print(f"DEBUG: [_start_camera_display_worker] Starting thread")
            self.camera_display_thread.start()
            logging.info("Camera display worker thread started")
            print(f"DEBUG: [_start_camera_display_worker] Worker started successfully")
            
        except Exception as e:
            print(f"DEBUG: [_start_camera_display_worker] ERROR: {e}")
            logging.error(f"Error starting camera display worker: {e}")
    
    def _stop_camera_display_worker(self):
        """Stop the camera display worker thread"""
        try:
            if self.camera_display_worker:
                self.camera_display_worker.stop()
            
            if self.camera_display_thread and self.camera_display_thread.isRunning():
                self.camera_display_thread.quit()
                self.camera_display_thread.wait(5000)  # Wait up to 5 seconds
                
            self.camera_display_worker = None
            self.camera_display_thread = None
            logging.info("Camera display worker thread stopped")
            
        except Exception as e:
            logging.error(f"Error stopping camera display worker: {e}")
    
    def _handle_processed_frame(self, qimage, frame_for_history):
        """Handle processed frame from worker thread (runs on main thread)"""
        try:
            print(f"DEBUG: [_handle_processed_frame] Received processed frame, qimage is None: {qimage is None}")
            if qimage is None:
                return
            
            # Update current frame for internal use
            self.current_frame = frame_for_history
            
            # Store last valid QImage for use in trigger mode
            if not hasattr(self, 'last_valid_qimage') or qimage is not None:
                self.last_valid_qimage = qimage
            
            # Check if we're in trigger mode
            in_trigger_mode = False
            try:
                if hasattr(self, 'main_window') and hasattr(self.main_window, 'camera_manager'):
                    cs = self.main_window.camera_manager.camera_stream
                    if cs and hasattr(cs, 'external_trigger_enabled'):
                        in_trigger_mode = cs.external_trigger_enabled
            except Exception:
                pass
            
            # Keep track of trigger mode state
            if hasattr(self, 'in_trigger_mode') and self.in_trigger_mode != in_trigger_mode:
                print(f"DEBUG: [CameraView] Trigger mode changed: {in_trigger_mode}")
            self.in_trigger_mode = in_trigger_mode
            
            # Display the processed QImage
            print(f"DEBUG: [_handle_processed_frame] Calling _display_qimage")
            self._display_qimage(qimage)
            
            # Calculate FPS
            self._calculate_fps()
            
            # NOTE: Frame history is now updated in _display_qimage() only to avoid duplicates
            
        except Exception as e:
            print(f"DEBUG: [_handle_processed_frame] ERROR: {e}")
            logging.error(f"Error handling processed frame: {e}")
    
    def _display_qimage(self, qimage):
        """Display QImage in graphics view (main thread only)"""
        try:
            print(f"DEBUG: [_display_qimage] Displaying QImage")
            # Convert QImage to QPixmap
            pixmap = QPixmap.fromImage(qimage)
            print(f"DEBUG: [_display_qimage] Pixmap created, isNull={pixmap.isNull()}, size={pixmap.size()}")
            if pixmap.isNull():
                print(f"DEBUG: [_display_qimage] Pixmap is null, returning")
                return
            
            # Get or create graphics scene
            scene = self.graphics_view.scene()
            if scene is None:
                print(f"DEBUG: [_display_qimage] Creating new graphics scene")
                scene = QGraphicsScene()
                self.graphics_view.setScene(scene)
            else:
                scene.clear()
            
            # Add pixmap to scene
            print(f"DEBUG: [_display_qimage] Adding pixmap to scene")
            scene.addPixmap(pixmap)
            
            # Apply zoom and rotation if needed
            if self.fit_on_next_frame:
                self.graphics_view.fitInView(scene.itemsBoundingRect(), Qt.KeepAspectRatio)
                self.fit_on_next_frame = False
            
            # The zoom level should already be applied by the zoom_in/zoom_out methods
            # Don't reapply zoom with each new frame as that causes cumulative zoom effect
            # We only need to reset the transform and apply the current zoom if explicitly requested
            if hasattr(self, '_zoom_changed') and self._zoom_changed:
                self.graphics_view.resetTransform()
                self.graphics_view.scale(self.zoom_level, self.zoom_level)
                self._zoom_changed = False
            
            # Don't apply rotation on every frame - only when rotation has changed
            # This will be handled in rotate_left and rotate_right methods directly
            
            # Update frame history with current frame (only here to avoid duplicates)
            # Note: self.current_frame is already in RGB format from _process_frame_to_qimage
            if self.current_frame is not None and len(self.current_frame.shape) == 3:
                if len(self.current_frame.shape) == 3 and self.current_frame.shape[2] == 3:
                    # current_frame is already RGB (converted in CameraDisplayWorker._process_frame_to_qimage)
                    # Use it directly without conversion
                    logging.info(f"[CameraView] Adding frame to history in _display_qimage - shape={self.current_frame.shape}")
                    self.update_frame_history(self.current_frame)
            
        except Exception as e:
            logging.error(f"Error displaying QImage: {e}")
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        self._stop_frame_history_worker()
        self._stop_camera_display_worker()
    
    def _update_review_views_threaded(self):
        """Update review views from main thread (called by worker thread)"""
        try:
            # Make a thread-safe copy of frame history
            with self.frame_history_lock:
                frame_history_copy = self.frame_history.copy()
            
            # DEBUG: Log review update being triggered
            logging.info(f"[ReviewViewUpdate] Main thread update triggered - frame_history_count={len(frame_history_copy)}")
            
            # Update review views with the copy
            self._update_review_views_with_frames(frame_history_copy)
            
        except Exception as e:
            logging.error(f"Error in threaded review views update: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_review_views_with_frames(self, frame_history):
        """Update review views with given frame history and update labels with NG/OK status"""
        try:
            if not self.review_views or not frame_history:
                # DEBUG: Log early return
                if not frame_history:
                    logging.debug(f"[ReviewViewUpdate] Early return - frame_history empty")
                return
            
            # Get frame status history from result manager (if available)
            frame_status_history = []
            if hasattr(self, 'main_window') and self.main_window:
                result_manager = getattr(self.main_window, 'result_manager', None)
                if result_manager:
                    frame_status_history = result_manager.get_frame_status_history()
            
            # DEBUG: Log initial state
            logging.info(f"[ReviewLabel] UPDATE START - frame_history count: {len(frame_history)}, status_history count: {len(frame_status_history)}")
            
            # Update each review view with corresponding frame from history
            # reviewView_1 = most recent, reviewView_5 = oldest
            for i, review_view in enumerate(self.review_views):
                if not review_view:
                    continue
                    
                # Calculate frame index (newest to oldest)
                frame_index = len(frame_history) - 1 - i
                
                # DEBUG: Log position mapping
                logging.debug(f"[ReviewLabel] Position {i+1}: frame_index={frame_index}, review_view exists={review_view is not None}")
                
                if frame_index >= 0 and frame_index < len(frame_history):
                    frame = frame_history[frame_index]
                    self._display_frame_in_review_view(review_view, frame, i + 1)
                    
                    # DEBUG: Log frame info
                    logging.info(f"[ReviewLabel] reviewLabel_{i+1} - Displaying frame #{frame_index}, shape={frame.shape if frame is not None else 'None'}")
                    
                    # Update corresponding label with NG/OK status
                    if self.review_labels and i < len(self.review_labels):
                        label = self.review_labels[i]
                        
                        # Get status from frame status history
                        # Status history: newest is at END (last index)
                        # So we need to map: i=0 (newest frame) → last status in history
                        status = 'NG'  # Default to NG
                        similarity = 0.0
                        
                        # Map frame index to status history index (reversed!)
                        # Newest frame (i=0) should get newest status (last in list)
                        status_history_index = len(frame_status_history) - 1 - i  # Reversed mapping
                        
                        if status_history_index >= 0 and status_history_index < len(frame_status_history):
                            status_data = frame_status_history[status_history_index]
                            status = status_data.get('status', 'NG')
                            similarity = status_data.get('similarity', 0.0)
                            # Update label with status and color
                            self._update_review_label(label, status, similarity, i + 1)
                            
                            # DEBUG: Log status assignment
                            logging.info(f"[ReviewLabel] reviewLabel_{i+1} - status_history_index={status_history_index}, status={status}, similarity={similarity:.2%}")
                        else:
                            # No corresponding status data - clear label
                            if label:
                                label.setText("")
                                label.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555;")
                            
                            # DEBUG: Log clear action
                            logging.info(f"[ReviewLabel] reviewLabel_{i+1} - CLEARED (no status at index {status_history_index})")
                else:
                    # Clear review view if no frame available
                    self._clear_review_view(review_view)
                    
                    # Clear corresponding label
                    if self.review_labels and i < len(self.review_labels):
                        label = self.review_labels[i]
                        if label:
                            label.setText("")
                            label.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555;")
                    
                    # DEBUG: Log clear for out-of-range
                    logging.debug(f"[ReviewLabel] reviewLabel_{i+1} - CLEARED (frame_index {frame_index} out of range)")
                    
        except Exception as e:
            logging.error(f"Error updating review views with frames: {e}")
            import traceback
            traceback.print_exc()
    
    def _display_frame_in_review_view(self, review_view, frame, view_number):
        """Display a frame in specific review view (auto-fit, read-only)"""
        try:
            if frame is None or review_view is None:
                return
            
            # Skip if frame is too large (performance optimization)
            if frame.size > 1440 * 1080 * 3:  # Skip very large frames for review views
                return
            
            # Configure review view for read-only display
            review_view.setDragMode(review_view.NoDrag)
            review_view.setInteractive(False)
            review_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            review_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            # Get or create scene for review view
            scene = review_view.scene()
            if scene is None:
                scene = QGraphicsScene()
                review_view.setScene(scene)
            else:
                scene.clear()
            
            # Resize frame for review views to improve performance
            import cv2
            display_frame = frame
            h, w = frame.shape[:2]
            if h > 240 or w > 320:  # Resize large frames for review views
                display_frame = cv2.resize(frame, (320, 240), interpolation=cv2.INTER_LINEAR)
                h, w = display_frame.shape[:2]
            
            # Convert frame to QPixmap with proper color format handling
            if len(display_frame.shape) == 3:
                ch = display_frame.shape[2]
                if ch == 3:
                    # Frame from history should already be in RGB format
                    # Use faster image creation without copy
                    qimg = QImage(display_frame.data, w, h, w * ch, QImage.Format_RGB888)
                elif ch == 4:
                    # RGBA format
                    qimg = QImage(display_frame.data, w, h, w * ch, QImage.Format_RGBA8888)
                else:
                    logging.warning(f"Unsupported channel count for review view {view_number}: {ch}")
                    return
            elif len(display_frame.shape) == 2:
                # Grayscale
                qimg = QImage(display_frame.data, w, h, w, QImage.Format_Grayscale8)
            else:
                logging.warning(f"Unsupported frame shape for review view {view_number}: {display_frame.shape}")
                return
            
            # Create pixmap and add to scene
            pixmap = QPixmap.fromImage(qimg)
            if pixmap.isNull():
                return
                
            scene.addPixmap(pixmap)
            
            # Always fit image in view and maintain aspect ratio
            review_view.fitInView(scene.itemsBoundingRect(), Qt.KeepAspectRatio)
            
            # Reset any zoom transformations
            review_view.resetTransform()
            review_view.fitInView(scene.itemsBoundingRect(), Qt.KeepAspectRatio)
            
        except Exception as e:
            logging.error(f"Error displaying frame in review view {view_number}: {e}")
    
    def _clear_review_view(self, review_view):
        """Clear a review view"""
        try:
            if review_view and review_view.scene():
                review_view.scene().clear()
        except Exception as e:
            logging.error(f"Error clearing review view: {e}")
    
    def _update_review_label(self, label, status: str, similarity: float, label_number: int):
        """
        Update review label with NG/OK status and color
        
        Args:
            label: QLabel widget to update
            status: 'OK' or 'NG'
            similarity: Similarity score (0.0 to 1.0)
            label_number: Label number (1-5) for reference
        """
        try:
            if not label:
                return
            
            # Format text with status only (no percentage)
            if status == 'OK':
                text = "OK"
                bg_color = "#00AA00"  # Green
                text_color = "white"
            else:
                text = "NG"
                bg_color = "#AA0000"  # Red
                text_color = "white"
            
            # Update label
            label.setText(text)
            label.setStyleSheet(f"background-color: {bg_color}; color: {text_color}; "
                              f"border: 1px solid #555; font-weight: bold; font-size: 12px;")
            
            # DEBUG: Log label update
            logging.info(f"[ReviewLabel] reviewLabel_{label_number} - Updated: text='{text}', color={bg_color}, similarity={similarity:.2%}")
            
        except Exception as e:
            logging.error(f"Error updating review label {label_number}: {e}")

