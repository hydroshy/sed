"""
ClassificationTool
------------------
Job-compatible image classification tool using ONNX models from
`model/classification`.

Features
- Direct ONNX inference for better performance and control
- Loads labels from adjacent `.json` files
- Classifies full-frame or optionally each ROI from previous DetectTool
- Returns top-k classes with confidences; can overlay predictions on image
- OK/NG evaluation based on expected class from UI
"""

from __future__ import annotations

import os
import json
import logging
from utils.debug_utils import conditional_print
from typing import Dict, Any, Tuple, Optional, List, Union

import numpy as np
import cv2

from tools.base_tool import BaseTool, ToolConfig
from utils.debug_utils import debug_log

# Direct ONNX imports
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logging.warning("ONNX Runtime not available - install with: pip install onnxruntime")

from pathlib import Path

logger = logging.getLogger(__name__)


class ClassificationTool(BaseTool):
    def __init__(
        self,
        name: str = "Classification Tool",
        config: Optional[Union[Dict[str, Any], ToolConfig]] = None,
        tool_id: Optional[int] = None,
    ):
        super().__init__(name, config, tool_id)
        
        # Direct ONNX model handling
        self.onnx_session = None
        self._model_loaded = False
        self._labels: List[str] = []
        self._model_path = ""
        
        # Model info
        project_root = Path(__file__).resolve().parents[2]
        self.models_dir = project_root / "model" / "classification"

    def setup_config(self) -> None:
        # Model + inference
        self.config.set_default("model_name", "")
        self.config.set_default("model_path", "")
        self.config.set_default("top_k", 1)
        self.config.set_default("input_width", 224)
        self.config.set_default("input_height", 224)
        self.config.set_default("use_rgb", True)
        self.config.set_default("normalize", False)
        # Standard ImageNet normalization
        self.config.set_default("mean", [0.485, 0.456, 0.406])
        self.config.set_default("std", [0.229, 0.224, 0.225])

        # Visualization
        self.config.set_default("draw_result", True)
        self.config.set_default("position", (8, 24))  # x,y for top-left text
        self.config.set_default("font_scale", 0.6)
        
        # OK/NG overlay option - KEY FEATURE
        self.config.set_default("result_display_enable", True)  # Enable OK/NG display
        self.config.set_default("expected_class_name", "")  # Set from classComboBox
        self.config.set_default("result_corner", "top-right")  # Position for OK/NG badge

        # ROI options from previous detection output
        self.config.set_default("use_detection_roi", False)
        self.config.set_default("classify_only_classes", [])
        self.config.set_default("roi_expand", 0.0)

        # NEW: Confidence-based rejection
        self.config.set_default("confidence_threshold", 0.75)
        self.config.set_default("enable_rejection", True)
        self.config.set_default("rejection_method", "both")  # "confidence", "entropy", "both"
        
        # NEW: Entropy-based uncertainty detection
        self.config.set_default("uncertainty_threshold", 0.8)
        
        # NEW: Per-class thresholds (optional)
        self.config.set_default("class_thresholds", {})

        # Validators
        self.config.set_validator("top_k", lambda x: int(x) >= 1)
        self.config.set_validator("roi_expand", lambda x: 0.0 <= float(x) <= 0.5)
        self.config.set_validator("confidence_threshold", lambda x: 0.0 <= float(x) <= 1.0)
        self.config.set_validator("uncertainty_threshold", lambda x: 0.0 <= float(x) <= 1.0)

    def _load_class_names(self, model_name: str) -> List[str]:
        """Load class names from JSON file - YOLO style"""
        try:
            json_path = self.models_dir / f"{model_name}.json"
            
            if json_path.exists():
                with open(json_path, 'r') as f:
                    class_mapping = json.load(f)
                
                # Convert to list (ordered by class index)
                names = []
                if isinstance(class_mapping, dict):
                    max_idx = max(int(k) for k in class_mapping.keys())
                    names = ["unknown"] * (max_idx + 1)
                    for k, v in class_mapping.items():
                        names[int(k)] = v
                
                logger.info(f"Loaded {len(names)} classes from {json_path}: {names}")
                return names
            else:
                logger.warning(f"Class mapping not found: {json_path}")
                return ["class_0", "class_1"]  # Default
                
        except Exception as e:
            logger.error(f"Error loading class names: {e}")
            return ["unknown"]

    def _ensure_model(self) -> bool:
        """Load ONNX model directly"""
        if not ONNX_AVAILABLE:
            logger.error("ONNX Runtime not available")
            return False
            
        if self._model_loaded and self.onnx_session is not None:
            return True

        model_name = self.config.get("model_name", "")
        model_path = self.config.get("model_path", "")
        
        logger.info(f"Loading ONNX model - model_name='{model_name}', model_path='{model_path}'")

        # Resolve model path from name if needed
        if (not model_path) and model_name:
            model_path = str(self.models_dir / f"{model_name}.onnx")
            self.config.set("model_path", model_path)
            
        if not model_path or not os.path.exists(model_path):
            logger.error(f"Model file not found: {model_path}")
            return False

        try:
            # Load ONNX model
            self.onnx_session = ort.InferenceSession(model_path)
            
            # Load class names
            if model_name:
                self._labels = self._load_class_names(model_name)
            else:
                # Extract model name from path
                model_basename = os.path.basename(model_path).replace('.onnx', '')
                self._labels = self._load_class_names(model_basename)
            
            self._model_path = model_path
            self._model_loaded = True
            
            # Log model info
            input_shape = self.onnx_session.get_inputs()[0].shape
            output_shape = self.onnx_session.get_outputs()[0].shape
            logger.info(f"ONNX model loaded successfully:")
            logger.info(f"  Path: {model_path}")
            logger.info(f"  Input shape: {input_shape}")
            logger.info(f"  Output shape: {output_shape}")
            logger.info(f"  Classes: {self._labels}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            self._model_loaded = False
            return False

    @staticmethod
    def _clip_roi(x1: int, y1: int, x2: int, y2: int, w: int, h: int) -> Tuple[int, int, int, int]:
        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(0, min(x2, w - 1))
        y2 = max(0, min(y2, h - 1))
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1
        return x1, y1, x2, y2

    def _calculate_entropy(self, probabilities: np.ndarray) -> float:
        """Calculate prediction entropy to detect uncertain predictions"""
        epsilon = 1e-8
        probs = np.clip(probabilities, epsilon, 1.0)
        entropy = -np.sum(probs * np.log(probs))
        return entropy

    def _apply_rejection_logic(self, predictions: List[Dict[str, Any]], probabilities: np.ndarray) -> List[Dict[str, Any]]:
        """Apply confidence and entropy-based rejection"""
        if not bool(self.config.get("enable_rejection", True)):
            return predictions
        
        confidence_threshold = float(self.config.get("confidence_threshold", 0.75))
        uncertainty_threshold = float(self.config.get("uncertainty_threshold", 0.8))
        rejection_method = self.config.get("rejection_method", "both")
        class_thresholds = self.config.get("class_thresholds", {})
        
        # Calculate uncertainty metrics
        entropy = self._calculate_entropy(probabilities)
        max_entropy = np.log(len(probabilities))
        uncertainty = entropy / max_entropy if max_entropy > 0 else 0.0
        
        debug_log(f"ClassificationTool: Entropy={entropy:.3f}, Uncertainty={uncertainty:.3f}", logging.INFO)
        
        # Check entropy-based rejection first
        if rejection_method in ["entropy", "both"] and uncertainty > uncertainty_threshold:
            debug_log(f"ClassificationTool: High uncertainty detected ({uncertainty:.3f} > {uncertainty_threshold}) - rejecting as 'uncertain'", logging.INFO)
            return [{
                "class_name": "uncertain",
                "confidence": 1.0 - uncertainty,
                "class_id": -2,
                "entropy": entropy,
                "uncertainty": uncertainty,
                "rejection_reason": "high_uncertainty"
            }]
        
        # Apply confidence-based rejection
        if rejection_method in ["confidence", "both"]:
            filtered_predictions = []
            
            for pred in predictions:
                class_name = pred["class_name"]
                confidence = pred["confidence"]
                
                # Check class-specific threshold first, then global threshold
                threshold = class_thresholds.get(class_name, confidence_threshold)
                
                if confidence >= threshold:
                    pred["threshold_met"] = True
                    filtered_predictions.append(pred)
                else:
                    debug_log(f"ClassificationTool: Rejecting {class_name} ({confidence:.3f} < {threshold:.3f})", logging.INFO)
            
            # If no predictions meet threshold, return "unknown"
            if not filtered_predictions:
                debug_log("ClassificationTool: No predictions meet confidence threshold - returning 'unknown'", logging.INFO)
                return [{
                    "class_name": "unknown",
                    "confidence": 0.0,
                    "class_id": -1,
                    "threshold_met": False,
                    "rejection_reason": "low_confidence"
                }]
            
            return filtered_predictions
        
        return predictions

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for ONNX inference"""
        # Get config parameters
        width = int(self.config.get("input_width", 448))
        height = int(self.config.get("input_height", 448))
        use_rgb = bool(self.config.get("use_rgb", True))
        normalize = bool(self.config.get("normalize", False))
        mean = self.config.get("mean", [0.485, 0.456, 0.406])
        std = self.config.get("std", [0.229, 0.224, 0.225])
        
        # Debug log (reduced for performance)
        # conditional_print(f"DEBUG: ClassificationTool preprocessing with dimensions {width}x{height}")
        
        # Resize image
        resized = cv2.resize(image, (width, height))
        
        # Convert BGR to RGB if needed
        if use_rgb:
            resized = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Convert to float32 and normalize to 0-1
        img_float = resized.astype(np.float32) / 255.0
        
        # Apply ImageNet normalization if enabled
        if normalize:
            mean = np.array(mean, dtype=np.float32)
            std = np.array(std, dtype=np.float32)
            img_float = (img_float - mean) / std
        
        # Convert to CHW format (channels first) and add batch dimension
        img_chw = np.transpose(img_float, (2, 0, 1))  # HWC -> CHW
        img_batch = np.expand_dims(img_chw, axis=0)   # Add batch dimension
        
        return img_batch

    def _classify_image(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Classify image using direct ONNX inference"""
        top_k = int(self.config.get("top_k", 1))
        
        # Add frame tracking (reduced logging for performance)
        import hashlib
        frame_hash = hashlib.md5(image.tobytes()).hexdigest()[:8]
        frame_mean = np.mean(image)
        frame_std = np.std(image)
        
        debug_log(f"ClassificationTool: _classify_image - input shape={image.shape}, top_k={top_k}", logging.INFO)
        debug_log(f"ClassificationTool: Frame hash={frame_hash}, mean={frame_mean:.2f}, std={frame_std:.2f}", logging.INFO)

        try:
            # Preprocess image
            input_tensor = self._preprocess_image(image)
            debug_log(f"ClassificationTool: Input tensor shape: {input_tensor.shape}", logging.INFO)
            
            # Run inference
            input_name = self.onnx_session.get_inputs()[0].name
            output_name = self.onnx_session.get_outputs()[0].name
            
            outputs = self.onnx_session.run([output_name], {input_name: input_tensor})
            predictions = outputs[0][0]  # Remove batch dimension
            
            # Detailed logging disabled for performance
            # logger.info(f"ClassificationTool: Raw predictions shape: {predictions.shape}")
            debug_log(f"ClassificationTool: Raw predictions/logits: {predictions}", logging.INFO)
            
            # Handle different output formats like YOLO
            if np.allclose(np.sum(predictions), 1.0, atol=1e-6) and np.all(predictions >= 0) and np.all(predictions <= 1):
                # Predictions are already probabilities
                probabilities = predictions
                debug_log("ClassificationTool: Using direct probabilities (no softmax needed)", logging.INFO)
            elif np.max(predictions) <= 1.0 and np.min(predictions) >= 0:
                # Looks like probabilities but don't sum to 1, normalize
                probabilities = predictions / np.sum(predictions)
                debug_log("ClassificationTool: Using normalized probabilities", logging.INFO)
            else:
                # Check if this is a YOLO-style output where one value is 1.0 and others are near 0
                if np.max(predictions) == 1.0 and np.sum(predictions < 1e-10) >= (len(predictions) - 1):
                    # This is already a one-hot style output from YOLO
                    probabilities = predictions.copy()
                    debug_log("ClassificationTool: Using YOLO-style one-hot output", logging.INFO)
                else:
                    # Apply softmax to get probabilities
                    max_pred = np.max(predictions)
                    exp_scores = np.exp(predictions - max_pred)  # Numerical stability
                    probabilities = exp_scores / np.sum(exp_scores)
                    debug_log("ClassificationTool: Using softmax probabilities", logging.INFO)
            
            debug_log(f"ClassificationTool: Final probabilities: {probabilities}", logging.INFO)
            
            # Create initial results (all classes sorted by confidence)
            num_classes = len(probabilities)
            all_indices = np.argsort(probabilities)[::-1]  # All classes sorted by confidence
            
            initial_results = []
            for i, idx in enumerate(all_indices):
                confidence = float(probabilities[idx])
                class_name = self._labels[idx] if idx < len(self._labels) else f"class_{idx}"
                
                result = {
                    "class_name": class_name,
                    "confidence": confidence,
                    "class_id": int(idx)
                }
                initial_results.append(result)
            
            # Apply rejection logic (confidence + entropy based)
            final_results = self._apply_rejection_logic(initial_results, probabilities)
            
            # Debug logging for final results
            if final_results:
                top_result = final_results[0]
                if top_result.get("rejection_reason"):
                    debug_log(f"ClassificationTool: Rejected - {top_result['class_name']} (reason: {top_result['rejection_reason']})", logging.INFO)
                else:
                    debug_log(f"ClassificationTool: Accepted - {top_result['class_name']} ({top_result['confidence']:.4f})", logging.INFO)
                
                # Log top-k for debugging (YOLO format)
                top_k_results = final_results[:top_k]
                results_str = [(r['class_name'], f"{r['confidence']:.4f}") for r in top_k_results]
                debug_log(f"ClassificationTool: Final Top-{top_k} results: {results_str}", logging.INFO)
            
            return final_results  # Return processed results with rejection logic
            
        except Exception as e:
            logger.error(f"ClassificationTool: _classify_image - inference error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _draw_label(self, img: np.ndarray, text: str, org: Tuple[int, int]) -> None:
        import cv2
        x, y = org
        cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                    float(self.config.get("font_scale", 0.6)), (0, 255, 0), 2, cv2.LINE_AA)

    def process(
        self,
        image: np.ndarray,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        debug_log(f"ClassificationTool: Starting classification process for image shape {image.shape}", logging.INFO)
        
        # Auto-detect and convert image format if needed
        # Most classification models expect RGB, but OpenCV uses BGR
        # Check context to see what format the image is in
        input_format = "unknown"
        if context and "pixel_format" in context:
            input_format = context["pixel_format"]
        elif context and "source" in context and "Camera Source" in context["source"]:
            # Camera Source typically provides BGR format (OpenCV standard)
            input_format = "BGR888"
        
        # Ensure image is in RGB format for classification
        work_image = image.copy()
        try:
            import cv2  # Ensure cv2 is available in local scope
            if input_format in ["BGR888", "unknown"] and len(image.shape) == 3 and image.shape[2] == 3:
                # Convert BGR to RGB for classification
                debug_log(f"ClassificationTool: About to convert BGR to RGB using cv2.cvtColor", logging.INFO)
                work_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                debug_log(f"ClassificationTool: Converted {input_format} to RGB for classification", logging.INFO)
            elif input_format == "RGB888":
                # Already RGB, no conversion needed
                logger.info(f"ClassificationTool: Image already in RGB format")
            else:
                logger.warning(f"ClassificationTool: Unknown format {input_format}, assuming RGB")
        except Exception as e:
            logger.error(f"ClassificationTool: Error in format conversion: {e}")
            # Fallback to original image
            work_image = image.copy()
        
        if not self._ensure_model():
            logger.error("ClassificationTool: Model not loaded")
            return image, {
                "tool_name": self.display_name,
                "status": "error",
                "error": "Model not loaded",
            }

        try:
            draw = bool(self.config.get("draw_result", True))
            result_display = bool(self.config.get("result_display_enable", False))
            # Removed threshold - always show OK/NG regardless of confidence
            
            debug_log(f"ClassificationTool: Config - draw_result={draw}, result_display={result_display}", logging.INFO)
            
            # Copy image if we are going to draw anything (class text or OK/NG)
            result_img = image.copy() if (draw or result_display) else image
            h, w = work_image.shape[:2]  # Use work_image (RGB) dimensions

            use_detection_roi = bool(self.config.get("use_detection_roi", False))
            roi_expand = float(self.config.get("roi_expand", 0.0))
            allowed_classes = set(self.config.get("classify_only_classes", []) or [])

            all_results: List[Dict[str, Any]] = []

            if use_detection_roi and context and isinstance(context.get("detections"), list):
                detections = context.get("detections")
                for det in detections:
                    # Optionally filter which detections to classify
                    if allowed_classes and det.get("class_name") not in allowed_classes:
                        continue
                    bbox = det.get("bbox")
                    if not bbox or len(bbox) != 4:
                        continue
                    x1, y1, x2, y2 = bbox

                    # Expand ROI by ratio
                    if roi_expand > 0.0:
                        bw = x2 - x1
                        bh = y2 - y1
                        dx = int(bw * roi_expand)
                        dy = int(bh * roi_expand)
                        x1 -= dx
                        y1 -= dy
                        x2 += dx
                        y2 += dy
                    x1, y1, x2, y2 = self._clip_roi(x1, y1, x2, y2, w, h)
                    crop = work_image[y1:y2, x1:x2]  # Use RGB work_image for classification
                    if crop.size == 0:
                        continue

                    preds = self._classify_image(crop)
                    all_results.append({
                        "bbox": [x1, y1, x2, y2],
                        "predictions": preds,
                    })

                    if draw and preds:
                        top1 = preds[0]
                        label = f"{top1['class_name']} {top1['confidence']:.2f}"
                        self._draw_label(result_img, label, (x1 + 4, max(y1 - 6, 12)))
            else:
                # Full-frame classification
                debug_log("ClassificationTool: Performing full-frame classification", logging.INFO)
                preds = self._classify_image(work_image)  # Use RGB work_image for classification
                debug_log(f"ClassificationTool: Got {len(preds)} predictions: {preds}", logging.INFO)
                
                all_results.append({
                    "bbox": None,
                    "predictions": preds,
                })
                if draw and preds:
                    top1 = preds[0]
                    debug_log(f"ClassificationTool: Top prediction - {top1['class_name']} with confidence {top1['confidence']:.3f}", logging.INFO)
                    label = f"{top1['class_name']} {top1['confidence']:.2f}"
                    pos = tuple(self.config.get("position", (8, 24)))
                    self._draw_label(result_img, label, pos)

            # Determine OK/NG status if enabled
            ok_flag: Optional[bool] = None
            if result_display:
                expected = (self.config.get("expected_class_name") or "").strip()
                confidence_threshold = self.config.get("confidence_threshold", 0.75)
                debug_log(f"ClassificationTool: OK/NG evaluation - expected_class='{expected}', threshold={confidence_threshold}", logging.INFO)
                
                # Collect top1 predictions from all results
                tops: List[Dict[str, Any]] = []
                for r in all_results:
                    preds = r.get("predictions") or []
                    if preds:
                        tops.append(preds[0])
                
                debug_log(f"ClassificationTool: Evaluating {len(tops)} predictions for OK/NG", logging.INFO)
                
                if tops:
                    # Filter by confidence threshold and reject cases
                    valid_preds = []
                    for t in tops:
                        class_name = t.get('class_name', '')
                        confidence = t.get('confidence', 0.0)
                        
                        # Reject "unknown" and "uncertain" predictions as NG
                        if class_name in ['unknown', 'uncertain']:
                            debug_log(f"ClassificationTool: Rejecting {class_name} prediction", logging.INFO)
                            continue
                            
                        # Apply confidence threshold
                        if confidence >= confidence_threshold:
                            valid_preds.append(t)
                        else:
                            debug_log(f"ClassificationTool: Low confidence {confidence:.3f} < {confidence_threshold}", logging.INFO)
                    
                    debug_log(f"ClassificationTool: {len(valid_preds)} valid predictions after filtering", logging.INFO)
                    
                    if valid_preds:
                        if expected:
                            # OK if any valid prediction matches expected class
                            matching_preds = [t for t in valid_preds if t.get('class_name') == expected]
                            ok_flag = len(matching_preds) > 0
                            debug_log(f"ClassificationTool: Expected class '{expected}' - found {len(matching_preds)} matching predictions", logging.INFO)
                        else:
                            # No expected class configured: OK if we have any valid prediction
                            ok_flag = True
                            logger.info(f"ClassificationTool: No expected class - OK because we have {len(valid_preds)} valid predictions")
                    else:
                        ok_flag = False
                        logger.info("ClassificationTool: NG - no valid predictions (rejected/low confidence)")
                else:
                    ok_flag = False
                    logger.info("ClassificationTool: NG - no predictions available")

                # Draw OK/NG badge at corner - always show result if we have predictions
                if ok_flag is not None:
                    should_show_result = len(tops) > 0  # Show if we have any predictions (including rejected ones)
                    debug_log(f"ClassificationTool: Should show OK/NG result: {should_show_result}", logging.INFO)
                    
                    if should_show_result:
                        try:
                            import cv2
                            label = "OK" if ok_flag else "NG"
                            color = (0, 200, 0) if ok_flag else (0, 0, 255)
                            debug_log(f"ClassificationTool: Drawing {label} badge in {color}", logging.INFO)
                            
                            # Badge size and position
                            pad = 8
                            rect_w, rect_h = 80, 36
                            corner = (self.config.get("result_corner") or "top-right").lower()
                            if corner == "top-left":
                                x, y = pad, pad
                            elif corner == "bottom-right":
                                x, y = w - rect_w - pad, h - rect_h - pad
                            elif corner == "bottom-left":
                                x, y = pad, h - rect_h - pad
                            else:  # top-right default
                                x, y = w - rect_w - pad, pad
                            # Draw filled rectangle
                            cv2.rectangle(result_img, (x, y), (x + rect_w, y + rect_h), color, thickness=-1)
                            # Draw text centered-ish
                            font = cv2.FONT_HERSHEY_SIMPLEX
                            scale = 0.9
                            thickness = 2
                            text_size, _ = cv2.getTextSize(label, font, scale, thickness)
                            tx = x + (rect_w - text_size[0]) // 2
                            ty = y + (rect_h + text_size[1]) // 2 - 4
                            cv2.putText(result_img, label, (tx, ty), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)
                        except Exception as e:
                            logger.error(f"ClassificationTool: Error drawing OK/NG badge: {e}")
                    else:
                        logger.info("ClassificationTool: Not showing OK/NG - confidence too low")

            output = {
                "tool_name": self.display_name,
                "status": "success",
                "results": all_results,
                "result_count": len(all_results),
            }
            
            debug_log(f"ClassificationTool: Process completed successfully - {len(all_results)} results", logging.INFO)
            if all_results and all_results[0].get("predictions"):
                top_pred = all_results[0]["predictions"][0]
                debug_log(f"ClassificationTool: Final result - {top_pred['class_name']} ({top_pred['confidence']:.3f})", logging.INFO)
            
            return result_img, output

        except Exception as e:
            logger.error(f"ClassificationTool error: {e}")
            return image, {
                "tool_name": self.display_name,
                "status": "error",
                "error": str(e),
            }

    def update_config(self, new_config: Dict[str, Any]) -> bool:
        ok = super().update_config(new_config)
        # Reset load flag to allow reloading on next process if model changed
        self._model_loaded = False
        return ok

    def get_info(self) -> Dict[str, Any]:
        info = super().get_info()
        info.update({
            "is_model_loaded": self._model_loaded,
            "top_k": self.config.get("top_k"),
            "threshold": self.config.get("threshold"),
            "use_detection_roi": self.config.get("use_detection_roi"),
        })
        return info


def create_classification_tool(config: Optional[Dict[str, Any]] = None) -> ClassificationTool:
    return ClassificationTool("Classification Tool", config)
