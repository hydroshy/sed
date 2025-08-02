"""
Detection Visualization Utilities
Handles drawing bounding boxes and displaying detection results
"""

import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import cv2

logger = logging.getLogger(__name__)

class DetectionVisualizer:
    """Handles visualization of YOLO detection results"""
    
    def __init__(self):
        # Default colors for different classes (BGR format)
        self.class_colors = [
            (0, 255, 255),    # Yellow
            (255, 0, 255),    # Magenta
            (0, 255, 0),      # Green
            (255, 0, 0),      # Blue
            (0, 0, 255),      # Red
            (255, 255, 0),    # Cyan
            (128, 0, 128),    # Purple
            (255, 165, 0),    # Orange
            (0, 128, 255),    # Light Blue
            (128, 255, 0),    # Lime
        ]
        
    def get_class_color(self, class_id: int) -> Tuple[int, int, int]:
        """Get color for specific class ID"""
        return self.class_colors[class_id % len(self.class_colors)]
    
    def draw_detections(self, image: np.ndarray, detections: List[Dict[str, Any]], 
                       show_confidence: bool = True, show_class_name: bool = True,
                       line_thickness: int = 2) -> np.ndarray:
        """
        Draw bounding boxes and labels on image
        
        Args:
            image: Input image (BGR format)
            detections: List of detection dictionaries
            show_confidence: Whether to show confidence scores
            show_class_name: Whether to show class names
            line_thickness: Thickness of bounding box lines
            
        Returns:
            Image with drawn detections
        """
        if not detections:
            return image.copy()
        
        result_image = image.copy()
        
        for detection in detections:
            try:
                bbox = detection['bbox']
                confidence = detection['confidence']
                class_id = detection['class_id']
                class_name = detection['class_name']
                
                # Get bounding box coordinates
                x1, y1, x2, y2 = bbox
                
                # Get color for this class
                color = self.get_class_color(class_id)
                
                # Draw bounding box
                cv2.rectangle(result_image, (x1, y1), (x2, y2), color, line_thickness)
                
                # Prepare label text
                label_parts = []
                if show_class_name:
                    label_parts.append(class_name)
                if show_confidence:
                    label_parts.append(f"{confidence:.2f}")
                
                if label_parts:
                    label = " ".join(label_parts)
                    
                    # Calculate text size and position
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 0.6
                    font_thickness = 1
                    
                    (text_width, text_height), baseline = cv2.getTextSize(
                        label, font, font_scale, font_thickness)
                    
                    # Draw label background
                    label_y = y1 - 10 if y1 - 10 > text_height else y1 + text_height + 10
                    cv2.rectangle(result_image, 
                                (x1, label_y - text_height - baseline),
                                (x1 + text_width, label_y + baseline),
                                color, -1)
                    
                    # Draw label text
                    cv2.putText(result_image, label, (x1, label_y - baseline),
                              font, font_scale, (255, 255, 255), font_thickness)
                
            except Exception as e:
                logger.error(f"Error drawing detection: {e}")
                continue
                
        return result_image
    
    def draw_detection_region(self, image: np.ndarray, region: Tuple[int, int, int, int], 
                             color: Tuple[int, int, int] = (0, 255, 0), 
                             line_thickness: int = 2) -> np.ndarray:
        """
        Draw detection region rectangle
        
        Args:
            image: Input image
            region: (x1, y1, x2, y2) detection region
            color: RGB color for rectangle
            line_thickness: Line thickness
            
        Returns:
            Image with drawn region
        """
        if region is None:
            return image.copy()
            
        result_image = image.copy()
        x1, y1, x2, y2 = region
        
        # Draw rectangle
        cv2.rectangle(result_image, (x1, y1), (x2, y2), color, line_thickness)
        
        # Draw "Detection Region" text
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(result_image, "Detection Region", (x1, y1 - 10),
                   font, 0.6, color, 2)
                   
        return result_image

# Factory function for creating detection visualization
def create_detection_display(image: np.ndarray, detections: List[Dict[str, Any]], 
                            detection_region: Optional[Tuple[int, int, int, int]] = None,
                            show_confidence: bool = True, show_class_name: bool = True) -> np.ndarray:
    """
    Create visualization for detections
    
    Args:
        image: Input image
        detections: List of detection dictionaries
        detection_region: Optional region to highlight
        show_confidence: Whether to show confidence values
        show_class_name: Whether to show class names
        
    Returns:
        Visualization image
    """
    visualizer = DetectionVisualizer()
    
    # Draw detections first
    result = visualizer.draw_detections(
        image, detections, show_confidence, show_class_name)
    
    # Then draw detection region if specified
    if detection_region:
        result = visualizer.draw_detection_region(result, detection_region)
    
    return result
