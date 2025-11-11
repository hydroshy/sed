"""
Detect Tool for Job System Integration
High-performance YOLO detection with direct ONNX inference
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
    """Detect Tool - Direct ONNX inference for maximum performance"""
    
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
        self.class_thresholds = {}  # Per-class thresholds
        
        # State tracking
        self.is_initialized = False
        self.last_detections = []
        self.execution_enabled = True
        self._config_changed = False  # ✅ Track if config has changed
        
        # Performance optimization
        self._last_image_shape = None
        self._last_letterbox_cache = None
        
        # Legacy compatibility
        self.model_name = None
        self.detect_job = None
        
        logger.info(f"DetectTool {self.display_name} created")
    
    def setup_config(self) -> None:
        """Setup default configuration"""
        # Core settings
        self.config.set_default('model_name', '')
        self.config.set_default('model_path', '')
        self.config.set_default('class_names', [])
        self.config.set_default('selected_classes', [])
        self.config.set_default('class_thresholds', {})
        self.config.set_default('confidence_threshold', 0.5)
        self.config.set_default('nms_threshold', 0.45)
        self.config.set_default('imgsz', 640)
        
        logger.info(f"DetectTool {self.display_name} configuration setup completed")
    
    def _letterbox_fast(self, bgr: np.ndarray, size: int = 640, color=(114, 114, 114), stride: int = 32) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """
        Fast letterbox resize + pad
        
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
        
        # Calculate scale ratio
        h, w = current_shape
        r = min(size / h, size / w)
        
        # Calculate new dimensions
        nh, nw = int(np.round(h * r)), int(np.round(w * r))
        
        # Ensure dimensions are divisible by stride
        nh = int(np.round(nh / stride) * stride)
        nw = int(np.round(nw / stride) * stride)
        
        # Fast resize
        if bgr.flags['C_CONTIGUOUS']:
            img = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
        else:
            img = cv2.resize(bgr.copy(), (nw, nh), interpolation=cv2.INTER_LINEAR)
        
        # Calculate padding
        top = (size - nh) // 2
        left = (size - nw) // 2
        bottom = size - nh - top
        right = size - nw - left
        
        # Fast pad using preallocated array
        padded = np.full((size, size, 3), color, dtype=np.uint8)
        padded[top:top+nh, left:left+nw] = img
        
        return padded, r, (left, top)
    
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
            i = order[0]
            keep.append(i)
            
            if order.size == 1:
                break
                
            # Calculate IoU with remaining boxes
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            w = np.maximum(0, xx2 - xx1)
            h = np.maximum(0, yy2 - yy1)
            inter = w * h
            
            union = areas[i] + areas[order[1:]] - inter + 1e-6
            iou = inter / union
            
            # Keep boxes with IoU below threshold
            order = order[1:][iou <= iou_thres]
        
        return np.array(keep, dtype=np.int64)
    
    def _yolo_universal_decode(self, outputs: Any, iou_thres: float = 0.45) -> np.ndarray:
        """
        Universal YOLO output decoder
        Supports multiple output formats:
        - 1 output: (N,6) or (N,7) or (1,N,6) 
        - 4 outputs: [num_dets, boxes, scores, classes]
        - Raw format: (N, 5+C) with NMS
        
        Returns: Nx6 array [x1, y1, x2, y2, score, class_id]
        """
        # Handle multiple outputs
        if isinstance(outputs, (list, tuple)):
            if len(outputs) == 4:
                num_dets, boxes, scores, class_ids = outputs
                # num_dets might be shape (1,) with count
                return np.concatenate([
                    np.array(boxes).squeeze(),
                    np.array(scores).squeeze()[:, None],
                    np.array(class_ids).squeeze()[:, None]
                ], axis=1).astype(np.float32)
            
            arr = np.array(outputs[0])
        else:
            arr = np.array(outputs)
        
        arr = np.squeeze(arr)
        if arr.ndim == 1:
            arr = arr[None, :]
        
        # Already NMS format: Nx6 or Nx7
        if arr.shape[-1] in (6, 7):
            if arr.shape[-1] == 7:
                arr = arr[:, [0, 1, 2, 3, 4, 6]]  # Remove confidence, keep class
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
    
    def mark_config_changed(self) -> None:
        """
        Mark that configuration has changed and needs re-initialization.
        Call this method when the tool's config is updated externally.
        """
        logger.info(f"🔄 DetectTool {self.display_name}: Config marked as changed, will re-initialize on next process()")
        self._config_changed = True
    
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
            # Load configuration
            self.model_path = self.config.get('model_path')
            self.class_names = self.config.get('class_names', [])
            self.selected_classes = self.config.get('selected_classes', [])
            self.class_thresholds = self.config.get('class_thresholds', {})
            self.confidence_threshold = self.config.get('confidence_threshold', 0.5)
            self.nms_threshold = self.config.get('nms_threshold', 0.45)
            self.imgsz = self.config.get('imgsz', 640)
            
            # Validate model path
            if not self.model_path or not Path(self.model_path).exists():
                logger.error(f"Model not found: {self.model_path}")
                return False
            
            # Initialize ONNX session
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] \
                if "CUDAExecutionProvider" in ort.get_available_providers() \
                else ["CPUExecutionProvider"]
            
            self.session = ort.InferenceSession(self.model_path, providers=providers)
            self.input_name = self.session.get_inputs()[0].name
            
            self.is_initialized = True
            logger.info(f"DetectTool {self.display_name} initialized")
            logger.info(f"  Model: {Path(self.model_path).name}")
            logger.info(f"  Classes: {len(self.class_names)} total, {len(self.selected_classes)} selected")
            logger.info(f"  Thresholds: {self.class_thresholds}")  # ✅ Log thresholds
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing DetectTool: {e}")
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
        logger.info(f"🔍 DetectTool.process() called - Image shape: {image.shape if image is not None else 'None'}")
        
        try:
            # Check execution state
            if not self.execution_enabled:
                logger.info("⏹️  DetectTool execution is DISABLED")
                return image, {'detections': [], 'error': 'Execution disabled'}
            
            # Initialize if needed OR if config changed
            if not self.is_initialized or self._config_changed:
                if self._config_changed:
                    logger.info("🔄 DetectTool config changed, re-initializing...")
                    self.is_initialized = False  # Reset to force re-initialization
                    self._config_changed = False
                else:
                    logger.info("DetectTool not initialized, initializing now...")
                
                if not self.initialize_detection():
                    logger.error("❌ DetectTool initialization FAILED")
                    return image, {'detections': [], 'error': 'Initialization failed'}
            
            logger.info("✅ DetectTool initialized, starting detection...")
            
            # Preprocessing
            preprocessed, scale, (pad_x, pad_y) = self._letterbox_fast(image, self.imgsz)
            
            # Prepare input tensor
            x = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            x = x.transpose(2, 0, 1)[None]  # [1, 3, H, W]
            
            # Run inference
            inference_start = time.time()
            outputs = self.session.run(None, {self.input_name: x})
            inference_time = time.time() - inference_start
            
            # Decode outputs
            detections_raw = self._yolo_universal_decode(outputs, iou_thres=self.nms_threshold)
            
            # Filter detections
            detections = []
            for detection in detections_raw:
                x1, y1, x2, y2, score, class_id = detection
                class_id = int(class_id)
                
                # Skip if class not selected
                if self.selected_classes:
                    if class_id >= len(self.class_names):
                        continue
                    class_name = self.class_names[class_id]
                    if class_name not in self.selected_classes:
                        continue
                
                # Check class-specific threshold
                threshold = self.class_thresholds.get(self.class_names[class_id], self.confidence_threshold) \
                    if class_id < len(self.class_names) else self.confidence_threshold
                
                if score >= threshold:
                    # Denormalize coordinates
                    x1_orig = (x1 - pad_x) / scale
                    y1_orig = (y1 - pad_y) / scale
                    x2_orig = (x2 - pad_x) / scale
                    y2_orig = (y2 - pad_y) / scale
                    
                    detection_dict = {
                        'class_id': class_id,
                        'class_name': self.class_names[class_id] if class_id < len(self.class_names) else f'unknown_{class_id}',
                        'confidence': float(score),
                        'x1': float(x1_orig),
                        'y1': float(y1_orig),
                        'x2': float(x2_orig),
                        'y2': float(y2_orig),
                        'width': float(x2_orig - x1_orig),
                        'height': float(y2_orig - y1_orig)
                    }
                    detections.append(detection_dict)
            
            # Store last detections
            self.last_detections = detections
            
            # Draw detections on output image
            output_image = image.copy()
            if self.config.get('visualize_results', True):
                output_image = self._draw_detections(output_image, detections)
            
            # Calculate execution time
            total_time = time.time() - start_time
            
            # Log results
            if detections:
                logger.info(f"✅ DetectTool found {len(detections)} detections:")
                for i, det in enumerate(detections[:3]):  # Log first 3
                    logger.info(f"   Detection {i}: {det['class_name']} ({det['confidence']:.2f})")
            else:
                logger.info(f"❌ DetectTool found NO detections")
            
            logger.info(f"DetectTool - {len(detections)} detections in {total_time:.3f}s (inference: {inference_time:.3f}s)")
            
            result = {
                'detections': detections,
                'detection_count': len(detections),
                'inference_time': float(inference_time),
                'total_time': float(total_time),
                'model': Path(self.model_path).name if self.model_path else 'None',
                'classes_total': len(self.class_names),
                'classes_selected': len(self.selected_classes),
                'class_thresholds': self.class_thresholds,  # ✅ Add thresholds for ResultTool
                'selected_classes': self.selected_classes    # ✅ Add selected classes for ResultTool
            }
            
            return output_image, result
            
        except Exception as e:
            logger.error(f"❌ Error in DetectTool process: {e}")
            import traceback
            traceback.print_exc()
            return image, {'detections': [], 'error': str(e)}
    
    def _draw_detections(self, image: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        """Draw detection results on image"""
        try:
            output = image.copy()
            
            for detection in detections:
                x1 = int(detection['x1'])
                y1 = int(detection['y1'])
                x2 = int(detection['x2'])
                y2 = int(detection['y2'])
                confidence = detection['confidence']
                class_name = detection['class_name']
                
                # Draw bounding box
                cv2.rectangle(output, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw label
                if self.config.get('show_class_names', True):
                    label_text = class_name
                    if self.config.get('show_confidence', True):
                        label_text += f" {confidence:.2f}"
                    
                    (text_width, text_height), baseline = cv2.getTextSize(
                        label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
                    )
                    
                    cv2.rectangle(output, (x1, y1 - text_height - baseline),
                                (x1 + text_width, y1), (0, 255, 0), -1)
                    cv2.putText(output, label_text, (x1, y1 - baseline),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
            return output
            
        except Exception as e:
            logger.error(f"Error drawing detections: {e}")
            return image
    
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Update tool configuration"""
        try:
            for key, value in new_config.items():
                self.config.set(key, value)
            
            # Reset initialization flag
            self.is_initialized = False
            
            logger.info(f"DetectTool {self.display_name} configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating DetectTool config: {e}")
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
        logger.info(f"DetectTool {self.display_name} cleaned up")


# Factory functions
def create_detect_tool(config: Optional[Dict[str, Any]] = None) -> DetectTool:
    """Create a new DetectTool with optional configuration"""
    return DetectTool("Detect Tool", config)


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
        'visualize_results': manager_config.get('visualize_results', True),
        'show_confidence': manager_config.get('show_confidence', True),
        'show_class_names': manager_config.get('show_class_names', True)
    }
    
    tool = DetectTool("Detect Tool", tool_config, tool_id)
    logger.info(f"Created DetectTool from manager config")
    logger.info(f"  Model: {tool_config.get('model_path', 'None')}")
    logger.info(f"  Selected classes: {tool_config.get('selected_classes', [])}")
    logger.info(f"  Class thresholds: {tool_config.get('class_thresholds', {})}")  # ✅ Log thresholds
    
    return tool
