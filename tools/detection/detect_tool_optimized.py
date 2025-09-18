"""
Optimized Detect Tool - Based on testonnx.py approach
High-performance YOLO detection with direct ONNX inference
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
import time
import cv2
from pathlib import Path

from tools.base_tool import BaseTool, ToolConfig

logger = logging.getLogger(__name__)

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("ONNX Runtime not available. Install with: pip install onnxruntime")

class OptimizedDetectTool(BaseTool):
    """Optimized Detect Tool - Direct ONNX inference approach"""
    
    def __init__(self, name: str = "Optimized Detect Tool", config: Optional[Union[Dict[str, Any], ToolConfig]] = None, tool_id: Optional[int] = None):
        super().__init__(name, config)
        self.tool_id = tool_id
        self.name = name
        
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
        
        logger.info(f"OptimizedDetectTool {self.display_name} created")
    
    def setup_config(self) -> None:
        """Setup default configuration"""
        self.config.set_default('model_path', '')
        self.config.set_default('class_names', [])
        self.config.set_default('selected_classes', [])
        self.config.set_default('confidence_threshold', 0.5)
        self.config.set_default('nms_threshold', 0.45)
        self.config.set_default('imgsz', 640)
        self.config.set_default('detection_region', None)
        self.config.set_default('visualize_results', True)
        self.config.set_default('show_confidence', True)
        self.config.set_default('show_class_names', True)
        
        # Validators
        self.config.set_validator('confidence_threshold', lambda x: 0.0 <= x <= 1.0)
        self.config.set_validator('nms_threshold', lambda x: 0.0 <= x <= 1.0)
        self.config.set_validator('imgsz', lambda x: x > 0 and x % 32 == 0)
        
        logger.info(f"OptimizedDetectTool {self.display_name} configuration setup completed")
    
    def _letterbox_fast(self, bgr: np.ndarray, size: int = 640, color=(114, 114, 114), stride: int = 32) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """
        Fast letterbox resize + pad (from testonnx.py)
        Returns: (padded_image, scale_ratio, (pad_left, pad_top))
        """
        h, w = bgr.shape[:2]
        r = min(size / h, size / w)  # Scale ratio
        
        # Calculate new dimensions
        nh, nw = int(round(h * r)), int(round(w * r))
        
        # Resize image
        img = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
        
        # Calculate padding
        top = (size - nh) // 2
        left = (size - nw) // 2
        bottom = size - nh - top
        right = size - nw - left
        
        # Apply padding
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
        
        return img, r, (left, top)
    
    def _nms_numpy_fast(self, boxes: np.ndarray, scores: np.ndarray, iou_thres: float = 0.45) -> np.ndarray:
        """
        Fast numpy-based NMS (from testonnx.py)
        Args:
            boxes: Nx4 array [x1, y1, x2, y2]
            scores: N array of confidence scores
            iou_thres: IoU threshold for NMS
        Returns:
            Array of indices to keep
        """
        if len(boxes) == 0:
            return np.array([], dtype=np.int64)
            
        x1, y1, x2, y2 = boxes.T
        areas = (x2 - x1).clip(min=0) * (y2 - y1).clip(min=0)
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
            
            w = (xx2 - xx1).clip(min=0)
            h = (yy2 - yy1).clip(min=0)
            inter = w * h
            
            union = areas[i] + areas[order[1:]] - inter + 1e-6
            iou = inter / union
            
            # Keep boxes with IoU below threshold
            order = order[1:][iou <= iou_thres]
        
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
        """Initialize ONNX model for detection"""
        if not ONNX_AVAILABLE:
            logger.error("ONNX Runtime not available")
            return False
        
        try:
            # Get configuration
            self.model_path = self.config.get('model_path')
            self.class_names = self.config.get('class_names', [])
            self.selected_classes = self.config.get('selected_classes', [])
            self.confidence_threshold = self.config.get('confidence_threshold', 0.5)
            self.nms_threshold = self.config.get('nms_threshold', 0.45)
            self.imgsz = self.config.get('imgsz', 640)
            
            if not self.model_path or not Path(self.model_path).exists():
                logger.error(f"Model path not found: {self.model_path}")
                return False
            
            # Initialize ONNX session
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if "CUDAExecutionProvider" in ort.get_available_providers() else ["CPUExecutionProvider"]
            self.session = ort.InferenceSession(self.model_path, providers=providers)
            self.input_name = self.session.get_inputs()[0].name
            
            self.is_initialized = True
            logger.info(f"OptimizedDetectTool {self.display_name} initialized - Model: {Path(self.model_path).name}")
            logger.info(f"Classes: {len(self.class_names)} - Selected: {len(self.selected_classes)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing OptimizedDetectTool {self.display_name}: {e}")
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
            
            # Get detection region
            detection_region = self.config.get('detection_region')
            if context and 'detection_region' in context:
                detection_region = context['detection_region']
            
            # Prepare detection frame
            detection_frame = image
            region_offset = (0, 0)
            
            if detection_region:
                x1, y1, x2, y2 = detection_region
                height, width = image.shape[:2]
                x1 = max(0, min(x1, width))
                y1 = max(0, min(y1, height))
                x2 = max(x1, min(x2, width))
                y2 = max(y1, min(y2, height))
                detection_frame = image[y1:y2, x1:x2]
                region_offset = (x1, y1)
            
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
                
                # Filter by selected classes
                if self.selected_classes and class_name not in self.selected_classes:
                    continue
                
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
            else:
                result['class_counts'] = {}
                result['avg_confidence'] = 0.0
            
            logger.debug(f"OptimizedDetectTool {self.display_name} - {len(detections)} detections in {total_time:.3f}s")
            
            return processed_image, result
            
        except Exception as e:
            logger.error(f"Error in OptimizedDetectTool {self.display_name}: {e}")
            return image, {
                'tool_name': self.display_name,
                'execution_time': time.time() - start_time,
                'detections': [],
                'status': 'error',
                'error': str(e)
            }
    
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
            if 'model_path' in new_config:
                self.is_initialized = False
            
            logger.info(f"OptimizedDetectTool {self.display_name} configuration updated")
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
        logger.info(f"OptimizedDetectTool {self.display_name} execution {'enabled' if enabled else 'disabled'}")
    
    def get_info(self) -> Dict[str, Any]:
        """Get tool information"""
        return {
            'tool_type': 'OptimizedDetectTool',
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
        logger.info(f"OptimizedDetectTool {self.display_name} cleaned up")

# Factory function for backward compatibility
def create_optimized_detect_tool_from_config(config: Dict[str, Any], tool_id: Optional[int] = None) -> OptimizedDetectTool:
    """Create OptimizedDetectTool from configuration dict"""
    tool = OptimizedDetectTool("Optimized Detect Tool", config, tool_id)
    logger.info(f"Created OptimizedDetectTool from config - Model: {config.get('model_path', 'None')}")
    return tool