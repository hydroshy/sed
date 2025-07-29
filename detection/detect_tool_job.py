"""
Detect Tool Job Implementation
Integrates YOLO inference with job execution system for real-time object detection
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import cv2
from pathlib import Path
import time

from detection.yolo_inference import create_yolo_inference
from detection.model_manager import ModelManager

logger = logging.getLogger(__name__)

class DetectToolJob:
    """Detect Tool job for YOLO inference execution"""
    
    def __init__(self, tool_config: Dict[str, Any]):
        """
        Initialize Detect Tool Job
        
        Args:
            tool_config: Configuration from DetectToolManager
                - model_name: Name of ONNX model
                - model_path: Path to ONNX model file
                - selected_classes: List of classes to detect
                - confidence_threshold: Detection confidence threshold
                - nms_threshold: NMS threshold
        """
        self.tool_config = tool_config
        self.model_manager = ModelManager()
        self.yolo_inference = create_yolo_inference()
        self.is_initialized = False
        self.last_inference_time = 0
        
        # Extract configuration
        self.model_name = tool_config.get('model_name')
        self.model_path = tool_config.get('model_path')
        self.selected_classes = tool_config.get('selected_classes', [])
        self.confidence_threshold = tool_config.get('confidence_threshold', 0.5)
        self.nms_threshold = tool_config.get('nms_threshold', 0.4)
        
        logger.info(f"DetectToolJob created - Model: {self.model_name}, Classes: {self.selected_classes}")
    
    def initialize(self) -> bool:
        """Initialize the job with model loading"""
        try:
            if not self.model_path or not self.model_name:
                logger.error("No model specified for DetectToolJob")
                return False
            
            # Get model info
            model_info = self.model_manager.get_model_info(self.model_name)
            if not model_info:
                logger.error(f"Could not load model info for: {self.model_name}")
                return False
            
            # Load YOLO model
            success = self.yolo_inference.load_model(self.model_path, model_info['classes'])
            if not success:
                logger.error(f"Failed to load YOLO model: {self.model_path}")
                return False
            
            # Set thresholds
            self.yolo_inference.set_thresholds(self.confidence_threshold, self.nms_threshold)
            
            self.is_initialized = True
            logger.info(f"DetectToolJob initialized successfully - {self.model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing DetectToolJob: {e}")
            return False
    
    def execute(self, frame: np.ndarray, region_coords: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
        """
        Execute detection on frame
        
        Args:
            frame: Input image frame (BGR format)
            region_coords: Optional (x1, y1, x2, y2) region to detect in
            
        Returns:
            Dictionary with detection results
        """
        logger.info(f"===== DetectToolJob.execute CALLED =====")
        logger.info(f"Frame shape: {frame.shape}")
        logger.info(f"Region coords: {region_coords}")
        logger.info(f"Model name: {self.model_name}")
        logger.info(f"Is initialized: {self.is_initialized}")
        
        start_time = time.time()
        
        try:
            if not self.is_initialized:
                if not self.initialize():
                    return self._create_error_result("Job not initialized")
            
            # Extract region if specified
            detection_frame = frame
            region_offset = (0, 0)
            
            if region_coords:
                x1, y1, x2, y2 = region_coords
                # Ensure coordinates are within frame bounds
                height, width = frame.shape[:2]
                x1 = max(0, min(x1, width))
                y1 = max(0, min(y1, height))
                x2 = max(x1, min(x2, width))
                y2 = max(y1, min(y2, height))
                
                detection_frame = frame[y1:y2, x1:x2]
                region_offset = (x1, y1)
                
                logger.debug(f"Detecting in region: ({x1}, {y1}, {x2}, {y2})")
            
            # Run inference
            logger.info(f"Running YOLO inference on frame shape: {detection_frame.shape}")
            detections = self.yolo_inference.infer(detection_frame, self.selected_classes)
            logger.info(f"YOLO inference completed: {len(detections)} detections found")
            
            # Log detailed detection info
            for i, det in enumerate(detections):
                logger.info(f"Detection {i+1}: {det['class_name']} (conf: {det['confidence']:.3f}, bbox: {det['bbox']})")
            
            # Adjust detection coordinates back to full frame if region was used
            if region_coords and detections:
                for detection in detections:
                    bbox = detection['bbox']
                    detection['bbox'] = [
                        bbox[0] + region_offset[0],
                        bbox[1] + region_offset[1],
                        bbox[2] + region_offset[0],
                        bbox[3] + region_offset[1]
                    ]
            
            # Calculate execution time
            execution_time = time.time() - start_time
            self.last_inference_time = execution_time
            
            logger.debug(f"Detection completed in {execution_time:.3f}s - Found {len(detections)} objects")
            
            return {
                'success': True,
                'detections': detections,
                'execution_time': execution_time,
                'frame_shape': frame.shape,
                'region_coords': region_coords,
                'selected_classes': self.selected_classes,
                'model_name': self.model_name
            }
            
        except Exception as e:
            logger.error(f"Error in DetectToolJob execution: {e}")
            return self._create_error_result(str(e))
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result dictionary"""
        return {
            'success': False,
            'error': error_message,
            'detections': [],
            'execution_time': 0,
            'frame_shape': None,
            'region_coords': None,
            'selected_classes': self.selected_classes,
            'model_name': self.model_name
        }
    
    def get_info(self) -> Dict[str, Any]:
        """Get job information"""
        return {
            'job_type': 'DetectTool',
            'model_name': self.model_name,
            'model_path': self.model_path,
            'selected_classes': self.selected_classes,
            'confidence_threshold': self.confidence_threshold,
            'nms_threshold': self.nms_threshold,
            'is_initialized': self.is_initialized,
            'last_inference_time': self.last_inference_time
        }
    
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Update job configuration"""
        try:
            # Update thresholds if provided
            if 'confidence_threshold' in new_config:
                self.confidence_threshold = new_config['confidence_threshold']
                
            if 'nms_threshold' in new_config:
                self.nms_threshold = new_config['nms_threshold']
            
            # Update selected classes
            if 'selected_classes' in new_config:
                self.selected_classes = new_config['selected_classes']
                logger.info(f"Updated selected classes: {self.selected_classes}")
            
            # Apply threshold changes if inference is available
            if self.is_initialized and hasattr(self.yolo_inference, 'set_thresholds'):
                self.yolo_inference.set_thresholds(self.confidence_threshold, self.nms_threshold)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating DetectToolJob config: {e}")
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.is_initialized = False
            logger.info("DetectToolJob cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up DetectToolJob: {e}")

# Factory function for job manager integration
def create_detect_tool_job(tool_config: Dict[str, Any]) -> DetectToolJob:
    """Create DetectToolJob instance"""
    return DetectToolJob(tool_config)
