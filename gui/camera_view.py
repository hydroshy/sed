import logging
import cv2
import time
import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QRectF, QPoint
from PyQt5.QtGui import QImage, QPixmap, QCursor, QPainter, QPen, QColor, QFont
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from gui.detection_area_overlay import DetectionAreaOverlay

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class CameraView(QObject):
    """
    Lớp quản lý và hiển thị hình ảnh từ camera
    """
    
    # Tín hiệu để thông báo khi các thông số focus được tính toán
    focus_calculated = pyqtSignal(int)
    
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
        self.zoom_level = 1.0
        self.zoom_step = 0.1
        self.rotation_angle = 0
        self.fit_on_next_frame = False
        
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
        
        # Cấu hình thuộc tính khác
        self.graphics_view.setRenderHints(QPainter.SmoothPixmapTransform)
        self.graphics_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.graphics_view.setDragMode(QGraphicsView.RubberBandDrag)
        
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
        Hiển thị frame từ camera
        
        Args:
            frame: Numpy array chứa hình ảnh từ camera (có thể là BGR, RGB, YUV420, etc.)
        """
        if frame is None or frame.size == 0:
            logging.error("Invalid frame received")
            return

        logging.debug("Frame received with shape: %s", frame.shape)
        
        # Store raw frame for display mode switching
        self.current_raw_frame = frame.copy()
        
        # Choose frame to display based on current display mode
        display_frame = self._get_display_frame()

        try:
            # Handle different frame formats safely
            if len(frame.shape) == 3 and frame.shape[2] >= 3:  # Color image with channels
                if frame.shape[2] == 4:  # RGBA format
                    logging.debug("Converting RGBA to RGB")
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
                elif frame.shape[2] == 3:  # Already 3-channel (BGR/RGB)
                    logging.debug("Using 3-channel frame as-is")
            elif len(frame.shape) == 2:  # 2D frame
                logging.debug("Converting 2D frame to RGB for display")
                # For simplicity, treat all 2D frames as grayscale
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            else:
                # For other formats, try to display as-is or convert to displayable format
                logging.debug("Frame format: %s, attempting to display directly", frame.shape)
                if len(frame.shape) == 3 and frame.shape[2] == 1:
                    # Single channel, convert to grayscale then RGB
                    frame = frame.squeeze()  # Remove single dimension
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
                elif len(frame.shape) == 1:
                    # 1D array - reshape to 2D if possible
                    height = int(np.sqrt(frame.size))
                    if height * height == frame.size:
                        frame = frame.reshape(height, height)
                        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
                    else:
                        logging.warning("Cannot display 1D frame of size %s", frame.size)
                        return
                else:
                    logging.warning("Unsupported frame format with shape: %s", frame.shape)
                    return
        except Exception as e:
            logging.error("Error processing frame format: %s", e)
            # Fallback: try to display as grayscale if possible
            try:
                if len(frame.shape) >= 2:
                    # Take first 2 dimensions and treat as grayscale
                    gray_frame = frame[:, :, 0] if len(frame.shape) == 3 else frame
                    frame = cv2.cvtColor(gray_frame.astype(np.uint8), cv2.COLOR_GRAY2RGB)
                else:
                    logging.error("Cannot recover from frame format error")
                    return
            except Exception as fallback_error:
                logging.error("Fallback frame processing failed: %s", fallback_error)
                return

        self.current_frame = frame  # Lưu frame hiện tại sau khi xử lý format
        # current_raw_frame đã được lưu ở đầu hàm
        
        self._show_frame_with_zoom()
        self._calculate_fps()
        
    def _run_job_processing(self, frame):
        """
        Run job manager processing on current frame
        
        Args:
            frame: Current frame to process
        """
        try:
            # Get job manager from main window
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'job_manager'):
                job_manager = self.main_window.job_manager
                current_job = job_manager.get_current_job()
                
                if current_job and current_job.tools:
                    logging.debug(f"Running job: {current_job.name} with {len(current_job.tools)} tools")
                    
                    # Process frame through job pipeline
                    processed_frame, results = current_job.run(frame)
                    
                    logging.info(f"=== JOB RESULTS DEBUG ===")
                    logging.info(f"Results type: {type(results)}")
                    logging.info(f"Results keys: {list(results.keys()) if isinstance(results, dict) else 'Not a dict'}")
                    
                    # Get actual tool results - they might be nested under 'results' key
                    tool_results = results
                    if 'results' in results and isinstance(results['results'], dict):
                        tool_results = results['results']
                        logging.info(f"Found nested results, tool result keys: {list(tool_results.keys())}")
                    
                    # Handle detection results if available - check all tool results
                    has_detections = False
                    for tool_name, tool_result in tool_results.items():
                        if isinstance(tool_result, dict):
                            logging.info(f"Checking tool {tool_name}, result keys: {list(tool_result.keys())}")
                            # Check if this tool has detection data
                            if 'data' in tool_result:
                                tool_data = tool_result['data']
                                if isinstance(tool_data, dict) and 'detections' in tool_data:
                                    logging.info(f"Found detections in tool {tool_name} data")
                                    has_detections = True
                                    break
                            # Also check direct detections field
                            elif 'detections' in tool_result:
                                logging.info(f"Found direct detections in tool {tool_name}")
                                has_detections = True
                                break
                    
                    if has_detections:
                        logging.info("Processing detection results...")
                        self._handle_detection_results(tool_results, processed_frame)
                    else:
                        logging.warning("No detection results found in any tool")
                        # Debug: show what's actually in the results
                        for tool_name, tool_result in tool_results.items():
                            if isinstance(tool_result, dict):
                                logging.info(f"Tool {tool_name} available keys: {list(tool_result.keys())}")
                    
                    # Store processed frames from tools for display mode switching
                    self._store_processed_frames(tool_results)
                        
                    logging.debug(f"Job processing completed: {len(tool_results)} tool results")
                else:
                    logging.debug("No active job with tools to run")
            else:
                logging.debug("Job manager not available")
                
        except Exception as e:
            logging.error(f"Error in job processing: {e}")
    
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
        if self.current_frame is None:
            logging.warning("No current frame to display")
            return

        try:
            # Chuyển đổi frame thành QPixmap
            h, w, ch = self.current_frame.shape
            bytes_per_line = ch * w
            pixel_format = 'BGR888'  # Default fallback (matches PiCamera2's natural output)
            try:
                mw = getattr(self, 'main_window', None)
                cm = getattr(mw, 'camera_manager', None) if mw else None
                cs = getattr(cm, 'camera_stream', None) if cm else None
                if cs is not None and hasattr(cs, 'get_pixel_format'):
                    pixel_format = cs.get_pixel_format()
                    print(f"DEBUG: [CameraView] Got pixel format from stream: {pixel_format}")
                else:
                    print(f"DEBUG: [CameraView] Could not get pixel format from stream, using default: {pixel_format}")
            except Exception as e:
                print(f"DEBUG: [CameraView] Exception getting pixel format: {e}")
                pixel_format = 'BGR888'
            # Convert frame to RGB - PiCamera2 ALWAYS returns BGR regardless of config
            # Only trust format for test frames (when camera not available)
            is_test_frame = False
            try:
                mw = getattr(self, 'main_window', None)
                cm = getattr(mw, 'camera_manager', None) if mw else None
                cs = getattr(cm, 'camera_stream', None) if cm else None
                if cs is not None:
                    is_test_frame = not getattr(cs, 'is_camera_available', False)
            except Exception:
                pass
                
            if ch == 3:
                if is_test_frame:
                    # For test frames, trust the pixel format
                    if str(pixel_format) == 'RGB888':
                        # Test frame is already RGB, use directly
                        print(f"DEBUG: [CameraView] Test frame RGB888, using directly")
                        rgb_image = self.current_frame
                    elif str(pixel_format) == 'BGR888':
                        # Test frame is BGR, convert to RGB
                        print(f"DEBUG: [CameraView] Test frame BGR888, converting to RGB")
                        rgb_image = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
                    else:
                        # Unknown test frame format, assume BGR
                        print(f"DEBUG: [CameraView] Test frame {pixel_format}, assuming BGR and converting")
                        rgb_image = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
                else:
                    # For real camera frames: PiCamera2 ALWAYS returns BGR data regardless of format setting
                    # This is PiCamera2's internal behavior - it converts all formats to BGR internally
                    print(f"DEBUG: [CameraView] Real camera processing: format={pixel_format}")
                    print(f"DEBUG: [CameraView] Original frame shape: {self.current_frame.shape}")
                    print(f"DEBUG: [CameraView] PiCamera2 always returns BGR data, converting to RGB for PyQt")
                    
                    # Always convert BGR->RGB for 3-channel real camera frames
                    # PiCamera2 internally provides BGR regardless of format setting
                    rgb_image = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
                    
                    print(f"DEBUG: [CameraView] Converted frame shape: {rgb_image.shape}")
                    
                    # Debug: Check pixel values 
                    if h > 100 and w > 100:
                        sample_pixel = self.current_frame[50, 50]  # Sample a pixel from original
                        display_sample = rgb_image[50, 50]  # Sample from display data
                        print(f"DEBUG: [CameraView] Original pixel at (50,50): {sample_pixel} (BGR from PiCamera2)")
                        print(f"DEBUG: [CameraView] Display pixel at (50,50): {display_sample} (RGB for PyQt)")
                        print(f"DEBUG: [CameraView] Color analysis - R:{display_sample[0]}, G:{display_sample[1]}, B:{display_sample[2]}")
            elif ch == 4:
                if is_test_frame and str(pixel_format) == 'XRGB8888':
                    # Test frame RGBA format, convert to RGB
                    print(f"DEBUG: [CameraView] Test frame XRGB8888, converting RGBA->RGB")
                    rgb_image = cv2.cvtColor(self.current_frame, cv2.COLOR_RGBA2RGB)
                else:
                    # Real camera or unknown 4-channel format, assume BGRA and convert
                    print(f"DEBUG: [CameraView] 4-channel frame (format={pixel_format}), converting BGRA->RGB")
                    rgb_image = cv2.cvtColor(self.current_frame, cv2.COLOR_BGRA2RGB)
            else:
                # Fallback for other channel counts
                try:
                    if str(pixel_format) == 'RGB888':
                        rgb_image = self.current_frame
                    else:
                        rgb_image = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
                except Exception:
                    rgb_image = self.current_frame
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            
            # Vẽ FPS lên pixmap nếu được bật
            if self.show_fps and self.fps > 0:
                painter = QPainter(pixmap)
                font = QFont()
                font.setPointSize(14)
                painter.setFont(font)
                painter.setPen(QColor(0, 255, 0))  # Màu xanh lá
                painter.drawText(10, 30, f"FPS: {self.fps:.1f}")
                painter.end()
            
            # Vẽ detection boxes nếu có (hiện overlay cả ở chế độ camera)
            if self.show_detection_overlay and self.detection_results:
                self._draw_detection_boxes_on_pixmap(pixmap)

            # Quản lý pixmap_item
            if self.pixmap_item is not None:
                if self.pixmap_item.scene() is not None:
                    self.scene.removeItem(self.pixmap_item)
                self.pixmap_item = None

            self.pixmap_item = QGraphicsPixmapItem(pixmap)
            self.pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            
            # Đặt pixmap_item ở z-level thấp nhất để detection areas nằm trên
            self.pixmap_item.setZValue(-1)
            self.scene.addItem(self.pixmap_item)

            # Đặt điểm xoay ở giữa pixmap
            self.pixmap_item.setTransformOriginPoint(self.pixmap_item.boundingRect().width() / 2, 
                                                  self.pixmap_item.boundingRect().height() / 2)

            # Áp dụng góc xoay
            self.pixmap_item.setRotation(self.rotation_angle)

            # Điều chỉnh scene rectangle để bao gồm cả pixmap và các detection areas
            scene_rect = self.pixmap_item.boundingRect()
            # Mở rộng scene rect để chứa các detection areas
            if self.saved_areas:
                for area in self.saved_areas:
                    if area.scene() == self.scene:
                        scene_rect = scene_rect.united(area.boundingRect())
            if self.current_area and self.current_area.scene() == self.scene:
                scene_rect = scene_rect.united(self.current_area.boundingRect())
            
            self.scene.setSceneRect(scene_rect)

            pixmap_center = self.pixmap_item.boundingRect().center()
            if (not self._has_drawn_once) or self.fit_on_next_frame or (self.zoom_level <= 1.0):
                self.graphics_view.centerOn(pixmap_center)
            self.graphics_view.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            self.graphics_view.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

            if not self.draw_mode:
                if self.zoom_level > 1.0:
                    self.graphics_view.setDragMode(QGraphicsView.ScrollHandDrag)
                    self.graphics_view.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
                else:
                    self.graphics_view.setDragMode(QGraphicsView.RubberBandDrag)
                    self.graphics_view.viewport().setCursor(Qt.CursorShape.ArrowCursor)

            if self.fit_on_next_frame:
                self.graphics_view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
                self.zoom_level = 1.0
                self.fit_on_next_frame = False
            else:
                # Preserve current transform to keep user panning when zoomed
                pass

            logging.debug("Frame displayed with zoom level: %f and rotation angle: %d", 
                        self.zoom_level, self.rotation_angle)
            self._has_drawn_once = True
        except Exception as e:
            logging.error("Error displaying frame: %s", e)

    def zoom_in(self):
        """
        Tăng mức zoom và áp dụng
        """
        self.zoom_level += self.zoom_step
        self.graphics_view.scale(1 + self.zoom_step, 1 + self.zoom_step)

    def zoom_out(self):
        """
        Giảm mức zoom và áp dụng
        """
        # Giảm mức zoom và đảm bảo không thấp hơn giá trị tối thiểu
        new_zoom = self.zoom_level - self.zoom_step
        if new_zoom < 0.1:
            new_zoom = 0.1
        
        # Calculate scale factor
        scale_factor = new_zoom / self.zoom_level
        self.zoom_level = new_zoom
        
        # Apply zoom
        self.graphics_view.scale(scale_factor, scale_factor)

    def rotate_left(self):
        """
        Xoay ngược chiều kim đồng hồ 90 độ
        """
        self.rotation_angle = (self.rotation_angle - 90) % 360
        self._show_frame_with_zoom()

    def rotate_right(self):
        """
        Xoay theo chiều kim đồng hồ 90 độ
        """
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self._show_frame_with_zoom()

    def reset_view(self):
        """
        Đặt lại mức zoom và xoay về mặc định
        """
        self.zoom_level = 1.0
        self.rotation_angle = 0
        self.fit_on_next_frame = True
        self._show_frame_with_zoom()

    def fit_to_view(self):
        """
        Phóng to/thu nhỏ để vừa khung nhìn
        """
        self.fit_on_next_frame = True
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
            self.scene.addItem(self.current_overlay)
            
        self.set_overlay_edit_mode(editable)
        return self.current_overlay
