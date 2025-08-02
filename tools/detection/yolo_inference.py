"""
YOLO ONNX Inference Engine for Detect Tool
Handles ONNX model loading and inference with bounding box detection
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
import cv2
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
    logger.info("ONNX Runtime available for inference")
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("ONNX Runtime not available. Install with: pip install onnxruntime")

class YOLOInference:
    """YOLO ONNX inference engine"""
    
    def __init__(self):
        self.session = None
        self.model_path = None
        self.class_names = []
        self.input_shape = None
        self.confidence_threshold = 0.5
        self.nms_threshold = 0.4
        
    def load_model(self, model_path: str, class_names: List[str]):
        """Load ONNX model for inference"""
        if not ONNX_AVAILABLE:
            raise RuntimeError("ONNX Runtime not available")
            
        try:
            # Create inference session
            self.session = ort.InferenceSession(model_path)
            self.model_path = model_path
            self.class_names = class_names
            
            # Get input shape
            input_meta = self.session.get_inputs()[0]
            self.input_shape = input_meta.shape
            
            logger.info(f"YOLO model loaded: {Path(model_path).name}")
            logger.info(f"Input shape: {self.input_shape}")
            logger.info(f"Classes: {len(class_names)} - {class_names}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            return False
    
    def preprocess_image(self, image: np.ndarray, target_size: Tuple[int, int] = (640, 640)) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """Preprocess image for YOLO inference"""
        original_height, original_width = image.shape[:2]
        
        # Resize while maintaining aspect ratio
        scale = min(target_size[0] / original_width, target_size[1] / original_height)
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        
        resized_image = cv2.resize(image, (new_width, new_height))
        
        # Pad to target size
        pad_x = (target_size[0] - new_width) // 2
        pad_y = (target_size[1] - new_height) // 2
        
        padded_image = np.full((target_size[1], target_size[0], 3), 114, dtype=np.uint8)
        padded_image[pad_y:pad_y + new_height, pad_x:pad_x + new_width] = resized_image
        
        # Normalize and transpose for model input
        input_image = padded_image.astype(np.float32) / 255.0
        input_image = np.transpose(input_image, (2, 0, 1))  # HWC to CHW
        input_image = np.expand_dims(input_image, axis=0)   # Add batch dimension
        
        return input_image, scale, (pad_x, pad_y)
    
    def set_thresholds(self, confidence_threshold: float, nms_threshold: float) -> None:
        """Set detection thresholds"""
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        logger.debug(f"Set thresholds: confidence={confidence_threshold}, NMS={nms_threshold}")
    
    def infer(self, image: np.ndarray, selected_classes: List[str] = None) -> List[Dict[str, Any]]:
        """Run inference on an image"""
        if self.session is None:
            raise RuntimeError("Model not loaded")
        
        try:
            original_shape = image.shape[:2]
            
            # Preprocess image
            input_tensor, scale, pads = self.preprocess_image(image)
            
            # Run inference
            outputs = self.session.run(None, {self.session.get_inputs()[0].name: input_tensor})
            
            # Postprocess detections
            detections = self.postprocess_detections(outputs, scale, pads, original_shape)
            
            # Filter by selected classes if provided
            if selected_classes:
                detections = [d for d in detections if d['class_name'] in selected_classes]
            
            return detections
            
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return []

# Factory function for creating YOLOInference
def create_yolo_inference() -> YOLOInference:
    """Create a new YOLOInference instance"""
    return YOLOInference()
