"""
Optimized Detect Tool for Job System Integration
High-performance YOLO detection with direct ONNX inference
Based on testonnx.py approach for maximum performance
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
import time
import cv2
from pathlib import Path

from tools.base_tool import BaseTool, ToolConfig
from .model_manager import ModelManager

logger = logging.getLogger(__name__)

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("ONNX Runtime not available. Install with: pip install onnxruntime")

class DetectTool(BaseTool):
    """Optimized Detect Tool - Direct ONNX inference for maximum performance"""
    
    def __init__(self, name: str = "Detect Tool", config: Optional[Union[Dict[str, Any], ToolConfig]] = None, tool_id: Optional[int] = None):
        super().__init__(name, config)
        self.tool_id = tool_id
        self.name = name or "Detect Tool"
        
        # Core ONNX components
        self.session = None
        self.input_name = None
        self.model_path = None
        self.class_names = []
        
        # Processing parameters
        self.imgsz = 640
        self.confidence_threshold = 0.5
        self.nms_threshold = 0.45
        self.selected_classes = []
        
        # State tracking
        self.is_initialized = False
        self.last_detections = []
        self.execution_enabled = True
        
        # Performance optimization
        self._last_image_shape = None
        self._last_letterbox_cache = None
        self._session_input_details = None
        self._session_output_details = None
        
        # Legacy compatibility
        self.model_name = None
        self.detect_job = None
        
        logger.info(f"OptimizedDetectTool {self.display_name} created")
    
    def setup_config(self) -> None:
        """Setup default configuration"""
        # Core settings
        self.config.set_default('model_name', '')  # Legacy compatibility
        self.config.set_default('model_path', '')
        self.config.set_default('class_names', [])
        self.config.set_default('selected_classes', [])
        self.config.set_default('confidence_threshold', 0.5)
        self.config.set_default('nms_threshold', 0.45)
        self.config.set_default('imgsz', 640)
        
        # Detection area settings
        self.config.set_default('detection_region', None)
        self.config.set_default('detection_area', None)  # UI compatibility
        
        logger.info(f"DetectTool {self.display_name} configuration setup completed")
    
    def _letterbox_fast(self, bgr: np.ndarray, size: int = 640, color=(114, 114, 114), stride: int = 32) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """
        Fast letterbox resize + pad with caching
        
        Args:
            bgr: Input BGR image
            size: Target size
            color: Padding color
            stride: Stride for alignment
            
        Returns:
            Tuple containing:
            - padded_image: Resized and padded image
            - scale_ratio: Scale ratio used for resizing
            - (pad_left, pad_top): Padding offsets
        """
        current_shape = bgr.shape[:2]
        
        # Check cache
        if (self._last_image_shape == current_shape and 
            self._last_letterbox_cache is not None and 
            self._last_letterbox_cache[0].shape == (size, size, 3)):
            return self._last_letterbox_cache
            
        # Calculate scale ratio
        h, w = current_shape
        r = min(size / h, size / w)
        
        # Calculate new dimensions
        nh, nw = int(round(h * r)), int(round(w * r))
        
        # Ensure dimensions are divisible by stride
        nh = int(np.round(nh / stride) * stride)
        nw = int(np.round(nw / stride) * stride)
        
        # Fast resize
        if bgr.flags['C_CONTIGUOUS']:
            img = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
        else:
            img = cv2.resize(np.ascontiguousarray(bgr), (nw, nh), interpolation=cv2.INTER_LINEAR)
        
        # Calculate padding
        top = (size - nh) // 2
        left = (size - nw) // 2
        bottom = size - nh - top
        right = size - nw - left
        
        # Fast pad using preallocated array
        padded = np.full((size, size, 3), color, dtype=np.uint8)
        padded[top:top+nh, left:left+nw] = img
        
        # Update cache
        self._last_image_shape = current_shape
        self._last_letterbox_cache = (padded, r, (left, top))
        
        return self._last_letterbox_cache
    
    def _nms_numpy_fast(self, boxes: np.ndarray, scores: np.ndarray, iou_thres: float = 0.45) -> np.ndarray:
        """
        Optimized numpy-based NMS with vectorized operations
        
        Args:
            boxes: Nx4 array [x1, y1, x2, y2]
            scores: N array of confidence scores
            iou_thres: IoU threshold for NMS
            
        Returns:
            Array of indices to keep
        """
        if len(boxes) == 0:
            return np.array([], dtype=np.int64)
            
        # Ensure contiguous arrays for better performance
        if not boxes.flags['C_CONTIGUOUS']:
            boxes = np.ascontiguousarray(boxes)
        if not scores.flags['C_CONTIGUOUS']:
            scores = np.ascontiguousarray(scores)
            
        x1, y1, x2, y2 = boxes.T
        
        # Precompute areas using vectorized operations
        areas = np.multiply(
            np.maximum(0, x2 - x1),
            np.maximum(0, y2 - y1)
        )
        
        # Get indices sorted by score
        order = scores.argsort()[::-1]
        keep = []
        
        while order.size > 0:
            # Keep highest scoring box
            i = order[0]
            keep.append(i)
            
            if order.size == 1:
                break
                
            # Compute IoU using vectorized operations
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            # Compute areas of intersection
            inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
            
            # Compute IoU
            union = areas[i] + areas[order[1:]] - inter
            iou = np.divide(inter, union, out=np.zeros_like(inter), where=union > 0)
            
            # Get boxes with IoU below threshold
            mask = iou <= iou_thres
            order = order[1:][mask]
        
        return np.array(keep, dtype=np.int64)
    
    def _yolo_universal_decode(self, outputs: Any, iou_thres: float = 0.45) -> np.ndarray:
        """
        Universal YOLO output decoder (from testonnx.py)
        Supports multiple output formats:
        - 1 output: (N,6) or (N,7) or (1,N,6) 
        - 4 outputs: [num_dets, boxes, scores, classes]
        - Raw format: (N, 5+C) with NMS
        
        Returns: Nx6 array [x1, y1, x2, y2, score, class_id]
        """
        # Handle multiple outputs
        if isinstance(outputs, (list, tuple)):
            if len(outputs) == 4:
                # Format: [num_dets, boxes, scores, classes]
                num = int(np.array(outputs[0]).reshape(-1)[0])
                boxes = np.array(outputs[1])[0, :num]  # [num, 4]
                scores = np.array(outputs[2])[0, :num]  # [num]
                classes = np.array(outputs[3])[0, :num]  # [num]
                return np.concatenate([boxes, scores[:, None], classes[:, None]], axis=1).astype(np.float32)
            
            arr = np.array(outputs[0])
        else:
            arr = np.array(outputs)
        
        arr = np.squeeze(arr)
        if arr.ndim == 1:
            arr = arr[None, :]
        
        # Already NMS format: Nx6 or Nx7
        if arr.shape[-1] in (6, 7):
            if arr.shape[-1] == 7:  # [batch_id, x1, y1, x2, y2, score, class]
                arr = arr[:, 1:]
            return arr.astype(np.float32)
        
        # Raw format: [x, y, w, h, obj, p0..pC-1]
        if arr.shape[-1] > 6:
            xywh = arr[:, :4].astype(np.float32)
            obj = arr[:, 4].astype(np.float32)
            cls_probs = arr[:, 5:].astype(np.float32)
            
            cls_id = cls_probs.argmax(1).astype(np.float32)
            cls_conf = cls_probs.max(1)
            scores = obj * cls_conf
            
            # Convert center format to corner format
            x, y, w, h = xywh.T
            x1 = x - w/2
            y1 = y - h/2
            x2 = x + w/2
            y2 = y + h/2
            boxes = np.stack([x1, y1, x2, y2], axis=1)
            
            # Apply NMS
            keep = self._nms_numpy_fast(boxes, scores, iou_thres=iou_thres)
            return np.concatenate([
                boxes[keep],
                scores[keep, None],
                cls_id[keep, None]
            ], axis=1).astype(np.float32)
        
        raise ValueError(f"Unknown output format with shape: {arr.shape}")
    
    def initialize_detection(self) -> bool:
        """
        Initialize ONNX model and cache important parameters
        Returns:
            bool: True if initialization successful
        """
        if not ONNX_AVAILABLE:
            logger.error("ONNX Runtime not available")
            return False
            
        try:
            # Load and validate configuration
            if not self._load_config():
                return False
                
            # Initialize ONNX session with optimizations
            if not self._initialize_onnx_session():
                return False
                
            # Cache session parameters
            if not self._cache_session_parameters():
                return False
                
            self.is_initialized = True
            logger.info(f"DetectTool {self.display_name} initialized successfully")
            logger.info(f"Classes: {len(self.class_names)} - Selected: {len(self.selected_classes)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing DetectTool {self.display_name}: {e}")
            return False
            
    def _load_config(self) -> bool:
        """Load and validate configuration"""
        try:
            # Get configuration
            self.model_path = self.config.get('model_path') or self.config.get('model_name', '')
            self.class_names = self.config.get('class_names', [])
            self.selected_classes = self.config.get('selected_classes', [])
            self.confidence_threshold = self.config.get('confidence_threshold', 0.5)
            self.nms_threshold = self.config.get('nms_threshold', 0.45)
            self.imgsz = self.config.get('imgsz', 640)
            
            # Validate model path
            if not self.model_path or not Path(self.model_path).exists():
                logger.error(f"Model path not found: {self.model_path}")
                return False
                
            # Validate configuration values
            if not isinstance(self.imgsz, int) or self.imgsz <= 0:
                logger.error(f"Invalid input size: {self.imgsz}")
                return False
                
            if not 0 <= self.confidence_threshold <= 1:
                logger.error(f"Invalid confidence threshold: {self.confidence_threshold}")
                return False
                
            if not 0 <= self.nms_threshold <= 1:
                logger.error(f"Invalid NMS threshold: {self.nms_threshold}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return False
            
    def _initialize_onnx_session(self) -> bool:
        """Initialize ONNX session with optimizations"""
        try:
            # Select optimal providers
            providers = (["CUDAExecutionProvider", "CPUExecutionProvider"] 
                       if "CUDAExecutionProvider" in ort.get_available_providers() 
                       else ["CPUExecutionProvider"])
            
            # Set graph optimization level
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            # Enable parallel execution
            sess_options.enable_cpu_mem_arena = True
            sess_options.enable_mem_pattern = True
            
            # Initialize session
            self.session = ort.InferenceSession(
                self.model_path,
                providers=providers,
                sess_options=sess_options
            )
            
            self.input_name = self.session.get_inputs()[0].name
            self.model_name = Path(self.model_path).stem
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing ONNX session: {e}")
            return False
            
    def _cache_session_parameters(self) -> bool:
        """Cache important session parameters"""
        try:
            # Cache input details
            input_details = self.session.get_inputs()[0]
            self._session_input_details = {
                'name': input_details.name,
                'shape': input_details.shape,
                'type': input_details.type
            }
            
            # Cache output details
            self._session_output_details = []
            for output in self.session.get_outputs():
                self._session_output_details.append({
                    'name': output.name,
                    'shape': output.shape,
                    'type': output.type
                })
                
            return True
            
        except Exception as e:
            logger.error(f"Error caching session parameters: {e}")
            return False
    
    def process(self, image: np.ndarray, context: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Process image with optimized YOLO detection
        
        Args:
            image: Input image (BGR format)
            context: Processing context
            
        Returns:
            Tuple of (processed_image, results)
        """
        start_time = time.time()
        
        try:
            # Check execution state
            if not self.execution_enabled:
                return image, {
                    'tool_name': self.display_name,
                    'execution_time': 0,
                    'detections': [],
                    'status': 'disabled'
                }
            
            # Initialize if needed
            if not self.is_initialized:
                if not self.initialize_detection():
                    return image, {
                        'tool_name': self.display_name,
                        'execution_time': 0,
                        'detections': [],
                        'status': 'initialization_failed'
                    }
            
            # Get and prepare detection region
            detection_frame, region_offset, detection_region = self._prepare_detection_region(image, context)
            
            # Fast preprocessing
            preprocessed, scale, (pad_x, pad_y) = self._letterbox_fast(detection_frame, self.imgsz)
            
            # Prepare input tensor
            x = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            x = x.transpose(2, 0, 1)[None]  # [1, 3, H, W]
            
            # Run inference
            inference_start = time.time()
            outputs = self.session.run(None, {self.input_name: x})
            inference_time = time.time() - inference_start
            
            # Decode outputs
            dets = self._yolo_universal_decode(outputs, self.nms_threshold)
            
            # Post-process detections
            detections = []
            for x1, y1, x2, y2, score, cls_id in dets:
                if score < self.confidence_threshold:
                    continue
                
                # Map bbox from letterbox back to original frame
                x1, y1, x2, y2 = (np.array([x1, y1, x2, y2]) - [pad_x, pad_y, pad_x, pad_y]) / scale
                
                # Adjust for detection region
                if detection_region:
                    x1 += region_offset[0]
                    y1 += region_offset[1]
                    x2 += region_offset[0]
                    y2 += region_offset[1]
                
                # Get class name
                class_id = int(cls_id)
                class_name = self.class_names[class_id] if class_id < len(self.class_names) else f"class_{class_id}"
                
                # Filter by selected classes if any are specified
                if self.selected_classes and class_name not in self.selected_classes:
                    logger.debug(f"Skipping class {class_name} - not in selected_classes: {self.selected_classes}")
                    continue
                
                # If no selected_classes specified, detect all classes (legacy behavior)
                if not self.selected_classes:
                    logger.debug(f"No selected_classes specified, detecting all classes including: {class_name}")
                
                detections.append({
                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                    'confidence': float(score),
                    'class_id': class_id,
                    'class_name': class_name
                })
            
            self.last_detections = detections
            
            # Create visualization
            processed_image = image
            if self.config.get('visualize_results', True) and detections:
                processed_image = self._draw_detections(image.copy(), detections, detection_region)
            
            # Calculate execution time
            total_time = time.time() - start_time
            
            # Create result
            result = {
                'tool_name': self.display_name,
                'execution_time': total_time,
                'inference_time': inference_time,
                'detections': detections,
                'detection_count': len(detections),
                'model_name': self.model_name,
                'model_path': self.model_path,
                'selected_classes': self.selected_classes,
                'detection_region': detection_region,
                'status': 'success'
            }
            
            # Add statistics
            if detections:
                class_counts = {}
                for det in detections:
                    class_name = det['class_name']
                    class_counts[class_name] = class_counts.get(class_name, 0) + 1
                result['class_counts'] = class_counts
                result['avg_confidence'] = np.mean([det['confidence'] for det in detections])
                
                # Debug logging for successful detections
                logger.debug(f"DetectTool found {len(detections)} detections:")
                for i, det in enumerate(detections[:3]):  # Log first 3 detections
                    logger.debug(f"  Detection {i}: {det['class_name']} ({det['confidence']:.2f})")
            else:
                result['class_counts'] = {}
                result['avg_confidence'] = 0.0
            
            logger.debug(f"DetectTool {self.display_name} - {len(detections)} detections in {total_time:.3f}s")
            
            return processed_image, result
            
        except Exception as e:
            logger.error(f"Error in DetectTool {self.display_name}: {e}")
            return image, {
                'tool_name': self.display_name,
                'execution_time': time.time() - start_time,
                'detections': [],
                'status': 'error',
                'error': str(e)
            }
    
    def _prepare_detection_region(self, image: np.ndarray, context: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Tuple[int, int], Optional[Tuple[int, int, int, int]]]:
        """
        Prepare detection region for processing
        
        Args:
            image: Input image
            context: Optional context with detection region override
            
        Returns:
            Tuple containing:
            - detection_frame: Image cropped to detection region if specified
            - region_offset: (x, y) offset of detection region
            - detection_region: Validated detection region coordinates or None
        """
        # Get detection region from context or config
        detection_region = None
        if context and 'detection_region' in context:
            detection_region = context['detection_region']
        else:
            detection_region = self.config.get('detection_region') or self.config.get('detection_area')
            
        # Default values for full image
        detection_frame = image
        region_offset = (0, 0)
        
        if detection_region:
            try:
                x1, y1, x2, y2 = detection_region
                height, width = image.shape[:2]
                
                # Validate and clip coordinates
                x1 = max(0, min(int(x1), width))
                y1 = max(0, min(int(y1), height))
                x2 = max(x1, min(int(x2), width))
                y2 = max(y1, min(int(y2), height))
                
                # Only create detection region if it has valid size
                if x2 > x1 and y2 > y1:
                    detection_frame = image[y1:y2, x1:x2]
                    region_offset = (x1, y1)
                    detection_region = (x1, y1, x2, y2)
                else:
                    logger.warning(f"Invalid detection region size: {x2-x1}x{y2-y1}")
                    detection_region = None
                    
            except (ValueError, TypeError, IndexError) as e:
                logger.error(f"Error processing detection region: {e}")
                detection_region = None
                
        return detection_frame, region_offset, detection_region

    def _draw_detections(self, image: np.ndarray, detections: List[Dict[str, Any]], detection_region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """Draw detection results on image"""
        try:
            # Draw detection region if specified
            if detection_region:
                x1, y1, x2, y2 = detection_region
                cv2.rectangle(image, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(image, "Detection Region", (x1, max(y1 - 5, 10)),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            
            # Draw detections
            for det in detections:
                x1, y1, x2, y2 = det['bbox']
                confidence = det['confidence']
                class_name = det['class_name']
                
                # Draw bounding box
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw label
                if self.config.get('show_class_names', True) and self.config.get('show_confidence', True):
                    label = f"{class_name} {confidence:.2f}"
                elif self.config.get('show_class_names', True):
                    label = class_name
                elif self.config.get('show_confidence', True):
                    label = f"{confidence:.2f}"
                else:
                    label = ""
                
                if label:
                    cv2.putText(image, label, (x1, max(y1 - 5, 10)),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            return image
            
        except Exception as e:
            logger.error(f"Error drawing detections: {e}")
            return image
    
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Update tool configuration"""
        try:
            # Update configuration
            for key, value in new_config.items():
                if not self.config.set(key, value):
                    logger.warning(f"Invalid config value for {key}: {value}")
                    return False
            
            # Re-initialize if model changed
            if 'model_path' in new_config or 'model_name' in new_config:
                self.is_initialized = False
            
            logger.info(f"DetectTool {self.display_name} configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            return False
    
    def get_last_detections(self) -> List[Dict[str, Any]]:
        """Get detections from last execution"""
        return self.last_detections.copy()
    
    def set_execution_enabled(self, enabled: bool):
        """Enable or disable execution"""
        self.execution_enabled = enabled
        logger.info(f"DetectTool {self.display_name} execution {'enabled' if enabled else 'disabled'}")
    
    def get_info(self) -> Dict[str, Any]:
        """Get tool information"""
        return {
            'tool_type': 'DetectTool',
            'display_name': self.display_name,
            'tool_id': self.tool_id,
            'execution_enabled': self.execution_enabled,
            'is_initialized': self.is_initialized,
            'model_path': self.model_path,
            'model_name': self.model_name,
            'class_count': len(self.class_names),
            'selected_classes': len(self.selected_classes),
            'last_detection_count': len(self.last_detections),
            'config': self.config.to_dict()
        }
    
    def cleanup(self):
        """Cleanup resources"""
        if self.session:
            del self.session
            self.session = None
        
        self.last_detections = []
        self.is_initialized = False
        # Legacy compatibility
        self.detect_job = None
        logger.info(f"DetectTool {self.display_name} cleaned up")

# Factory function for creating DetectTool with default configuration
def create_detect_tool(config: Optional[Dict[str, Any]] = None) -> DetectTool:
    """
    Tạo một DetectTool mới với cấu hình cơ bản
    
    Args:
        config: Cấu hình cho công cụ phát hiện
        
    Returns:
        DetectTool instance
    """
    return DetectTool("Detect Tool", config)

# Factory function for creating DetectTool from DetectToolManager config
def create_detect_tool_from_manager_config(manager_config: Dict[str, Any], tool_id: Optional[int] = None) -> DetectTool:
    """
    Create DetectTool from DetectToolManager configuration
    
    Args:
        manager_config: Config from DetectToolManager.get_tool_config()
        tool_id: Optional tool ID
        
    Returns:
        DetectTool instance
    """
    # Convert manager config to tool config
    tool_config = {
        'model_name': manager_config.get('model_name', ''),
        'model_path': manager_config.get('model_path', ''),
        'class_names': manager_config.get('class_names', []),
        'selected_classes': manager_config.get('selected_classes', []),
        'class_thresholds': manager_config.get('class_thresholds', {}),
        'confidence_threshold': manager_config.get('confidence_threshold', 0.5),
        'nms_threshold': manager_config.get('nms_threshold', 0.45),
        'imgsz': manager_config.get('imgsz', 640),
        'detection_region': manager_config.get('detection_region', None),
        'detection_area': manager_config.get('detection_area', None),  # For UI compatibility
        'visualize_results': manager_config.get('visualize_results', True),
        'show_confidence': manager_config.get('show_confidence', True),
        'show_class_names': manager_config.get('show_class_names', True)
    }
    
    tool = DetectTool("Detect Tool", tool_config, tool_id)
    logger.info(f"Created DetectTool from manager config - Model: {tool_config.get('model_path', 'None')}")
    
    return tool
