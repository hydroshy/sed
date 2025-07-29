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
    
    def draw_region_overlay(self, image: np.ndarray, region_coords: Tuple[int, int, int, int],
                           color: Tuple[int, int, int] = (0, 255, 0), 
                           thickness: int = 2, alpha: float = 0.3) -> np.ndarray:
        """
        Draw detection region overlay on image
        
        Args:
            image: Input image
            region_coords: (x1, y1, x2, y2) coordinates
            color: RGB color for overlay
            thickness: Border thickness
            alpha: Transparency for filled overlay
            
        Returns:
            Image with region overlay
        """
        result_image = image.copy()
        x1, y1, x2, y2 = region_coords
        
        # Draw border
        cv2.rectangle(result_image, (x1, y1), (x2, y2), color, thickness)
        
        # Draw semi-transparent fill
        if alpha > 0:
            overlay = result_image.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
            result_image = cv2.addWeighted(result_image, 1 - alpha, overlay, alpha, 0)
        
        return result_image
    
    def create_detection_summary(self, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create summary of detection results
        
        Args:
            detections: List of detection dictionaries
            
        Returns:
            Summary dictionary with counts and statistics
        """
        if not detections:
            return {
                'total_detections': 0,
                'class_counts': {},
                'avg_confidence': 0.0,
                'max_confidence': 0.0,
                'min_confidence': 0.0
            }
        
        # Count detections per class
        class_counts = {}
        confidences = []
        
        for detection in detections:
            class_name = detection['class_name']
            confidence = detection['confidence']
            
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
            confidences.append(confidence)
        
        return {
            'total_detections': len(detections),
            'class_counts': class_counts,
            'avg_confidence': np.mean(confidences),
            'max_confidence': np.max(confidences),
            'min_confidence': np.min(confidences)
        }
    
    def create_detection_info_image(self, detections: List[Dict[str, Any]], 
                                  image_size: Tuple[int, int] = (400, 300)) -> np.ndarray:
        """
        Create an info image showing detection statistics
        
        Args:
            detections: List of detection dictionaries
            image_size: (width, height) of info image
            
        Returns:
            Info image with detection summary
        """
        width, height = image_size
        info_image = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Get summary
        summary = self.create_detection_summary(detections)
        
        # Draw title
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(info_image, "Detection Results", (10, 30), 
                   font, 0.7, (255, 255, 255), 2)
        
        # Draw total count
        cv2.putText(info_image, f"Total: {summary['total_detections']}", 
                   (10, 60), font, 0.6, (0, 255, 0), 1)
        
        # Draw class counts
        y_pos = 90
        for class_name, count in summary['class_counts'].items():
            cv2.putText(info_image, f"{class_name}: {count}", 
                       (10, y_pos), font, 0.5, (255, 255, 0), 1)
            y_pos += 25
            if y_pos > height - 30:
                break
        
        # Draw confidence stats if there are detections
        if summary['total_detections'] > 0:
            cv2.putText(info_image, f"Avg Conf: {summary['avg_confidence']:.2f}", 
                       (10, height - 60), font, 0.5, (0, 255, 255), 1)
            cv2.putText(info_image, f"Max Conf: {summary['max_confidence']:.2f}", 
                       (10, height - 40), font, 0.5, (0, 255, 255), 1)
            cv2.putText(info_image, f"Min Conf: {summary['min_confidence']:.2f}", 
                       (10, height - 20), font, 0.5, (0, 255, 255), 1)
        
        return info_image

# Global visualizer instance
_visualizer = None

def get_visualizer() -> DetectionVisualizer:
    """Get global visualizer instance"""
    global _visualizer
    if _visualizer is None:
        _visualizer = DetectionVisualizer()
    return _visualizer

def draw_detections_on_image(image: np.ndarray, detections: List[Dict[str, Any]], 
                           **kwargs) -> np.ndarray:
    """Convenience function to draw detections"""
    return get_visualizer().draw_detections(image, detections, **kwargs)

def create_detection_display(image: np.ndarray, detections: List[Dict[str, Any]], 
                           region_coords: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
    """
    Create complete detection display with image, bounding boxes, and region overlay
    
    Args:
        image: Input image
        detections: Detection results
        region_coords: Optional detection region
        
    Returns:
        Complete visualization image
    """
    visualizer = get_visualizer()
    result_image = image.copy()
    
    # Draw region overlay if specified
    if region_coords:
        result_image = visualizer.draw_region_overlay(result_image, region_coords)
    
    # Draw detections
    result_image = visualizer.draw_detections(result_image, detections)
    
    return result_image
