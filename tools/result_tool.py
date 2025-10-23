"""
Result Tool - Evaluates and compares detections to determine OK/NG status

Purpose:
  - Takes detection results from detection tools
  - Compares with reference detections
  - Outputs OK/NG decision based on similarity threshold
  - Decoupled from detection tool for modularity
"""

import logging
from typing import Dict, Any, Tuple, Optional, List
import numpy as np
from .base_tool import BaseTool, ToolConfig

logger = logging.getLogger(__name__)


class ResultTool(BaseTool):
    """
    Tool for comparing detection results and determining OK/NG status.
    
    Input:
      - detections: List of detection results from detection tool
      
    Output:
      - ng_ok_result: 'OK', 'NG', or None
      - ng_ok_similarity: Similarity score (0-1)
      - ng_ok_reason: Explanation string
    """
    
    def __init__(self, name: str = "Result Tool", config: Optional[Dict[str, Any]] = None, tool_id: Optional[int] = None):
        """Initialize Result Tool
        
        Args:
            name: Display name
            config: Configuration dictionary
            tool_id: Tool ID in job pipeline
        """
        super().__init__(name=name, config=config, tool_id=tool_id)
        
        # NG/OK Parameters
        self.ng_ok_enabled = False                      # Enable NG/OK judgment
        self.ng_ok_reference_detections = []            # Reference detections from OK frame
        self.ng_ok_similarity_threshold = 0.8           # 80% similarity = OK
        self.ng_ok_result = None                        # 'OK', 'NG', or None
        self.ng_ok_similarity = None                    # Similarity score
        self.ng_ok_reason = None                        # Reason string
        
    def setup_config(self) -> None:
        """Setup default configuration"""
        self.config.set_default('ng_ok_enabled', False)
        self.config.set_default('ng_ok_similarity_threshold', 0.8)
        self.config.set_default('enable_debug', False)
        
    def set_reference_detections(self, detections: List[Dict[str, Any]]) -> None:
        """
        Set reference detections from an OK frame for future comparisons
        
        Args:
            detections: List of detection dictionaries with keys:
                       ['x1', 'y1', 'x2', 'y2', 'class_name', 'confidence']
        """
        self.ng_ok_reference_detections = detections
        self.ng_ok_enabled = True
        logger.info(f"ResultTool: Reference detections set - {len(detections)} objects")
        
    def _compare_detections_similarity(self, 
                                       current_detections: List[Dict[str, Any]], 
                                       reference_detections: List[Dict[str, Any]]) -> Tuple[float, str]:
        """
        Compare current detections with reference detections and calculate similarity.
        
        Factors considered:
        1. Object count match
        2. Class names match
        3. Bounding box overlap (IoU)
        
        Args:
            current_detections: Current frame detections
            reference_detections: Reference (OK) frame detections
            
        Returns:
            (similarity_score, reason_string) where score is 0-1
        """
        if not reference_detections:
            return 0.0, "No reference detections"
            
        if not current_detections:
            return 0.0, f"No detections found (expected {len(reference_detections)})"
        
        # Check 1: Object count
        current_count = len(current_detections)
        ref_count = len(reference_detections)
        
        if current_count != ref_count:
            count_ratio = current_count / ref_count if ref_count > 0 else 0
            reason = f"Object count mismatch: {current_count} vs {ref_count}"
            return count_ratio, reason
        
        # Check 2: Class names match
        current_classes = sorted([d.get('class_name', '') for d in current_detections])
        ref_classes = sorted([d.get('class_name', '') for d in reference_detections])
        
        if current_classes != ref_classes:
            matched = sum(1 for c, r in zip(current_classes, ref_classes) if c == r)
            match_ratio = matched / len(ref_classes) if ref_classes else 0
            reason = f"Class mismatch: {current_classes} vs {ref_classes}"
            return match_ratio, reason
        
        # Check 3: Bounding box overlap (IoU)
        iou_scores = []
        
        for curr_det, ref_det in zip(current_detections, reference_detections):
            # Calculate IoU for each detection pair
            curr_box = [curr_det['x1'], curr_det['y1'], curr_det['x2'], curr_det['y2']]
            ref_box = [ref_det['x1'], ref_det['y1'], ref_det['x2'], ref_det['y2']]
            
            iou = self._calculate_iou(curr_box, ref_box)
            iou_scores.append(iou)
        
        if iou_scores:
            avg_iou = sum(iou_scores) / len(iou_scores)
            reason = f"All objects match: avg IoU = {avg_iou:.2f}"
            return avg_iou, reason
        
        return 0.0, "No IoU calculation possible"
    
    def _calculate_iou(self, box1: List[float], box2: List[float]) -> float:
        """
        Calculate Intersection over Union (IoU) for two bounding boxes
        
        Args:
            box1: [x1, y1, x2, y2]
            box2: [x1, y1, x2, y2]
            
        Returns:
            IoU score (0-1)
        """
        x1_inter = max(box1[0], box2[0])
        y1_inter = max(box1[1], box2[1])
        x2_inter = min(box1[2], box2[2])
        y2_inter = min(box1[3], box2[3])
        
        # Check if boxes intersect
        if x2_inter < x1_inter or y2_inter < y1_inter:
            return 0.0
        
        inter_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
        
        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        union_area = box1_area + box2_area - inter_area
        
        if union_area == 0:
            return 0.0
        
        iou = inter_area / union_area
        return iou
    
    def evaluate_ng_ok(self, detections: List[Dict[str, Any]]) -> Tuple[str, float, str]:
        """
        Main NG/OK evaluation function
        
        Args:
            detections: Current frame detections
            
        Returns:
            (result, similarity, reason) where:
            - result: 'OK', 'NG', or None
            - similarity: float 0-1
            - reason: string explanation
        """
        if not self.ng_ok_enabled:
            return None, None, "NG/OK evaluation disabled"
        
        if not self.ng_ok_reference_detections:
            return None, None, "No reference detections set"
        
        # Compare detections
        similarity, reason = self._compare_detections_similarity(
            detections, 
            self.ng_ok_reference_detections
        )
        
        # Determine OK/NG
        threshold = self.config.get('ng_ok_similarity_threshold', 0.8)
        
        if similarity >= threshold:
            result = 'OK'
            full_reason = f"OK: {reason} (similarity={similarity:.2f} >= {threshold})"
        else:
            result = 'NG'
            full_reason = f"NG: {reason} (similarity={similarity:.2f} < {threshold})"
        
        return result, similarity, full_reason
    
    def process(self, image: np.ndarray, context: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Process frame and evaluate NG/OK status based on detection results
        
        Args:
            image: Input image (not used, but required by BaseTool interface)
            context: Context dict containing detection results from previous tool
                    Expected keys: 'detections', 'detection_tool_id'
                    
        Returns:
            (image, result_dict) where result_dict contains:
            - 'ng_ok_result': 'OK', 'NG', or None
            - 'ng_ok_similarity': Similarity score 0-1
            - 'ng_ok_reason': Explanation string
        """
        result = {
            'ng_ok_result': None,
            'ng_ok_similarity': None,
            'ng_ok_reason': "Result Tool not executed"
        }
        
        # Check if NG/OK is enabled
        if not self.ng_ok_enabled:
            result['ng_ok_reason'] = "NG/OK evaluation disabled"
            return image, result
        
        # Get detections from context (from previous detection tool)
        context = context or {}
        detections = context.get('detections', [])
        
        if 'detection_tool_id' not in context:
            logger.warning("ResultTool: No detection_tool_id in context")
        
        # Evaluate NG/OK
        ng_ok_status, similarity, reason = self.evaluate_ng_ok(detections)
        
        # Store results
        self.ng_ok_result = ng_ok_status
        self.ng_ok_similarity = similarity
        self.ng_ok_reason = reason
        
        result['ng_ok_result'] = ng_ok_status
        result['ng_ok_similarity'] = similarity
        result['ng_ok_reason'] = reason
        
        # Debug output
        if self.config.get('enable_debug', False):
            logger.debug(f"ResultTool: {ng_ok_status} - {reason}")
        
        return image, result
    
    def get_info(self) -> Dict[str, Any]:
        """Get tool information"""
        info = super().get_info()
        info.update({
            'ng_ok_enabled': self.ng_ok_enabled,
            'ng_ok_similarity_threshold': self.config.get('ng_ok_similarity_threshold', 0.8),
            'reference_detections_count': len(self.ng_ok_reference_detections),
            'last_result': self.ng_ok_result,
            'last_similarity': self.ng_ok_similarity,
        })
        return info
