"""
ResultManager - Manages NG/OK result evaluation independently
Separates result comparison logic from camera manager and job pipeline

Purpose:
  - Read detection/classification results from tools
  - Compare with reference data
  - Determine OK/NG status
  - Provide result to UI independently
  - No dependency on CameraManager
"""

import logging
from utils.debug_utils import conditional_print
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class ResultManager:
    """
    Independent manager for NG/OK result evaluation
    
    Responsibilities:
    - Store and manage reference data
    - Evaluate detection/classification results
    - Calculate similarity scores
    - Provide OK/NG status to UI
    - Work independently from job pipeline
    """
    
    def __init__(self, main_window=None):
        """
        Initialize ResultManager
        
        Args:
            main_window: Reference to main window for accessing tools/data
        """
        self.main_window = main_window
        
        # Reference data storage
        self.reference_data = {
            'detections': [],
            'source_tool': None,  # 'DetectTool' or 'ClassificationTool'
            'timestamp': None,
            'is_set': False
        }
        
        # NG/OK configuration
        self.ng_ok_enabled = False
        self.similarity_threshold = 0.8
        
        # Last evaluation result
        self.last_result = {
            'status': 'NG',  # Default to NG
            'similarity': 0.0,
            'reason': 'No reference set',
            'source_tool': None,
            'detection_count': 0
        }
        
        # Frame status history - track last 5 frame evaluations
        self.frame_status_history = []  # [(timestamp, status, similarity), ...]
        self.max_frame_history = 5
        
        logger.info("ResultManager initialized")
    
    def set_reference_from_detect_tool(self, detections: List[Dict[str, Any]]) -> bool:
        """
        Set reference from DetectTool detections
        
        Args:
            detections: List of detection dicts from DetectTool
            
        Returns:
            bool: True if reference set successfully
        """
        try:
            if not detections:
                logger.warning("ResultManager: Cannot set reference with empty detections")
                return False
            
            self.reference_data = {
                'detections': detections.copy(),
                'source_tool': 'DetectTool',
                'timestamp': None,
                'is_set': True
            }
            
            self.ng_ok_enabled = True
            
            logger.info(f"ResultManager: Reference set from DetectTool with {len(detections)} objects")
            conditional_print(f"DEBUG: [ResultManager] Reference set from DetectTool: {len(detections)} objects")
            
            return True
            
        except Exception as e:
            logger.error(f"ResultManager: Error setting reference: {e}")
            conditional_print(f"DEBUG: [ResultManager] Error setting reference: {e}")
            return False
    
    def evaluate_detect_results(self, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate current detection results against reference
        
        Args:
            detections: Current frame detections from DetectTool
            
        Returns:
            Dict with status, similarity, reason, source_tool, detection_count
        """
        try:
            # If NG/OK not enabled, default to NG
            if not self.ng_ok_enabled or not self.reference_data['is_set']:
                self.last_result = {
                    'status': 'NG',
                    'similarity': 0.0,
                    'reason': 'No reference set',
                    'source_tool': 'DetectTool',
                    'detection_count': len(detections)
                }
                return self.last_result
            
            # If no detections, it's NG
            if not detections:
                self.last_result = {
                    'status': 'NG',
                    'similarity': 0.0,
                    'reason': 'No detections found',
                    'source_tool': 'DetectTool',
                    'detection_count': 0
                }
                return self.last_result
            
            # Compare with reference
            similarity, reason = self._compare_detections(
                detections,
                self.reference_data['detections']
            )
            
            # Determine status
            status = 'OK' if similarity >= self.similarity_threshold else 'NG'
            
            self.last_result = {
                'status': status,
                'similarity': similarity,
                'reason': reason,
                'source_tool': 'DetectTool',
                'detection_count': len(detections)
            }
            
            # Add to frame status history (for review display)
            import time
            self._add_frame_status_to_history(time.time(), status, similarity)
            
            logger.debug(f"ResultManager: DetectTool evaluation - {status} (similarity: {similarity:.2f})")
            
            return self.last_result
            
        except Exception as e:
            logger.error(f"ResultManager: Error evaluating detections: {e}")
            self.last_result = {
                'status': 'NG',
                'similarity': 0.0,
                'reason': f'Error: {str(e)}',
                'source_tool': 'DetectTool',
                'detection_count': 0
            }
            return self.last_result
    
    def evaluate_classification_results(self, classifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate current classification results against reference
        
        Args:
            classifications: Current frame classifications from ClassificationTool
            
        Returns:
            Dict with status, similarity, reason, source_tool
        """
        try:
            # If NG/OK not enabled, default to NG
            if not self.ng_ok_enabled or not self.reference_data['is_set']:
                self.last_result = {
                    'status': 'NG',
                    'similarity': 0.0,
                    'reason': 'No reference set',
                    'source_tool': 'ClassificationTool',
                    'detection_count': len(classifications)
                }
                return self.last_result
            
            # If no classifications, it's NG
            if not classifications:
                self.last_result = {
                    'status': 'NG',
                    'similarity': 0.0,
                    'reason': 'No classifications found',
                    'source_tool': 'ClassificationTool',
                    'detection_count': 0
                }
                return self.last_result
            
            # For classification, compare class names and confidence
            similarity, reason = self._compare_classifications(
                classifications,
                self.reference_data['detections']
            )
            
            # Determine status
            status = 'OK' if similarity >= self.similarity_threshold else 'NG'
            
            self.last_result = {
                'status': status,
                'similarity': similarity,
                'reason': reason,
                'source_tool': 'ClassificationTool',
                'detection_count': len(classifications)
            }
            
            logger.debug(f"ResultManager: ClassificationTool evaluation - {status}")
            
            return self.last_result
            
        except Exception as e:
            logger.error(f"ResultManager: Error evaluating classifications: {e}")
            self.last_result = {
                'status': 'NG',
                'similarity': 0.0,
                'reason': f'Error: {str(e)}',
                'source_tool': 'ClassificationTool',
                'detection_count': 0
            }
            return self.last_result
    
    def _compare_detections(self, current: List[Dict], reference: List[Dict]) -> Tuple[float, str]:
        """
        Compare current detections with reference detections
        
        Args:
            current: Current frame detections
            reference: Reference detections
            
        Returns:
            Tuple[similarity_score (0-1), reason_string]
        """
        try:
            # Check count match
            if len(current) != len(reference):
                similarity = max(0, 1 - abs(len(current) - len(reference)) / max(len(reference), 1))
                return similarity, f"Count mismatch: {len(current)} vs {len(reference)}"
            
            # If both empty, perfect match
            if len(current) == 0 and len(reference) == 0:
                return 1.0, "Both frames have no objects"
            
            # Compare class names
            current_classes = sorted([det.get('class_name', '') for det in current])
            reference_classes = sorted([det.get('class_name', '') for det in reference])
            
            if current_classes != reference_classes:
                class_match = sum(1 for c, r in zip(current_classes, reference_classes) if c == r) / len(reference_classes)
                return class_match, f"Class mismatch: {current_classes} vs {reference_classes}"
            
            # Compare bounding boxes (IoU-based)
            iou_scores = []
            for curr_det, ref_det in zip(current, reference):
                curr_box = curr_det.get('bbox', [0, 0, 0, 0])
                ref_box = ref_det.get('bbox', [0, 0, 0, 0])
                
                # Handle bbox format [x1, y1, x2, y2]
                if len(curr_box) >= 4 and len(ref_box) >= 4:
                    iou = self._calculate_iou(curr_box[:4], ref_box[:4])
                    iou_scores.append(iou)
            
            if iou_scores:
                avg_iou = sum(iou_scores) / len(iou_scores)
                return avg_iou, f"Bbox match: IoU = {avg_iou:.2f}"
            
            # Fallback
            return 0.5, "Partial match"
            
        except Exception as e:
            logger.error(f"ResultManager: Error comparing detections: {e}")
            return 0.0, f"Comparison error: {str(e)}"
    
    def _compare_classifications(self, current: List[Dict], reference: List[Dict]) -> Tuple[float, str]:
        """
        Compare current classifications with reference detections
        
        Args:
            current: Current frame classifications
            reference: Reference detections
            
        Returns:
            Tuple[similarity_score (0-1), reason_string]
        """
        try:
            # Extract classes from both
            current_classes = sorted([c.get('class_name', '') for c in current])
            reference_classes = sorted([det.get('class_name', '') for det in reference])
            
            if not current_classes or not reference_classes:
                return 0.0, "Empty classification data"
            
            # Check if top class matches
            if current_classes[0] == reference_classes[0]:
                return 0.9, f"Top class matches: {current_classes[0]}"
            else:
                return 0.3, f"Top class mismatch: {current_classes[0]} vs {reference_classes[0]}"
                
        except Exception as e:
            logger.error(f"ResultManager: Error comparing classifications: {e}")
            return 0.0, f"Comparison error: {str(e)}"
    
    def _calculate_iou(self, box1: List[float], box2: List[float]) -> float:
        """
        Calculate Intersection over Union for two bounding boxes
        
        Args:
            box1: [x1, y1, x2, y2]
            box2: [x1, y1, x2, y2]
            
        Returns:
            IoU score (0-1)
        """
        try:
            x1_inter = max(box1[0], box2[0])
            y1_inter = max(box1[1], box2[1])
            x2_inter = min(box1[2], box2[2])
            y2_inter = min(box1[3], box2[3])
            
            if x2_inter < x1_inter or y2_inter < y1_inter:
                return 0.0
            
            inter_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
            
            box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
            box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
            
            union_area = box1_area + box2_area - inter_area
            
            if union_area == 0:
                return 0.0
            
            return inter_area / union_area
            
        except Exception as e:
            logger.error(f"ResultManager: Error calculating IoU: {e}")
            return 0.0
    
    def get_last_result(self) -> Dict[str, Any]:
        """Get the last evaluation result"""
        return self.last_result.copy()
    
    def set_reference_enabled(self, enabled: bool):
        """Enable/disable NG/OK evaluation"""
        self.ng_ok_enabled = enabled
        logger.info(f"ResultManager: NG/OK evaluation {'enabled' if enabled else 'disabled'}")
    
    def clear_reference(self):
        """Clear reference data and disable evaluation"""
        self.reference_data = {
            'detections': [],
            'source_tool': None,
            'timestamp': None,
            'is_set': False
        }
        self.ng_ok_enabled = False
        logger.info("ResultManager: Reference cleared")
        conditional_print(f"DEBUG: [ResultManager] Reference cleared")
    
    def get_info(self) -> Dict[str, Any]:
        """Get ResultManager information"""
        return {
            'ng_ok_enabled': self.ng_ok_enabled,
            'similarity_threshold': self.similarity_threshold,
            'reference_set': self.reference_data['is_set'],
            'reference_source': self.reference_data['source_tool'],
            'reference_count': len(self.reference_data['detections']),
            'last_status': self.last_result['status'],
            'last_similarity': self.last_result['similarity']
        }
    
    def _add_frame_status_to_history(self, timestamp: float, status: str, similarity: float):
        """
        Add frame evaluation status to history
        
        Args:
            timestamp: Frame timestamp
            status: 'OK' or 'NG'
            similarity: Similarity score (0.0 to 1.0)
        """
        try:
            self.frame_status_history.append({
                'timestamp': timestamp,
                'status': status,
                'similarity': similarity
            })
            
            # DEBUG: Log status being added
            import logging
            logging.info(f"[ResultManager] Status recorded - status={status}, similarity={similarity:.2%}, history_count={len(self.frame_status_history)}")
            
            # Keep only last N frames
            if len(self.frame_status_history) > self.max_frame_history:
                removed = self.frame_status_history.pop(0)
                logging.info(f"[ResultManager] Removed oldest status - history_count={len(self.frame_status_history)}")
                
        except Exception as e:
            logger.error(f"ResultManager: Error adding frame status to history: {e}")
    
    def get_frame_status_history(self) -> List[Dict[str, Any]]:
        """
        Get frame status history (last 5 frames)
        
        Returns:
            List of frame status dicts [(status, similarity), ...]
            Most recent is last in list (index 4 is most recent, index 0 is oldest)
        """
        try:
            return self.frame_status_history.copy()
        except Exception as e:
            logger.error(f"ResultManager: Error getting frame status history: {e}")
            return []
