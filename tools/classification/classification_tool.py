"""
ClassificationTool
------------------
Job-compatible image classification tool using ONNX models from
`model/classification`.

Features
- Loads labels from adjacent `.txt` or `.json` (same as detection ModelManager)
- Classifies full-frame or optionally each ROI from previous DetectTool
- Returns top-k classes with confidences; can overlay predictions on image
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Tuple, Optional, List, Union

import numpy as np
import cv2

from tools.base_tool import BaseTool, ToolConfig
from tools.classification.classifier_inference import (
    create_classifier_inference,
    PreprocessConfig,
)

# Reuse detection ModelManager but point to classification directory
from tools.detection.model_manager import ModelManager
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
        # Model manager pointing to model/classification
        project_root = Path(__file__).resolve().parents[2]
        models_dir = project_root / "model" / "classification"
        self.model_manager = ModelManager(str(models_dir))

        self.classifier = create_classifier_inference()
        self._model_loaded = False
        self._labels: List[str] = []

    def setup_config(self) -> None:
        # Model + inference
        self.config.set_default("model_name", "")
        self.config.set_default("model_path", "")
        self.config.set_default("top_k", 1)
        # Removed threshold - always show OK/NG regardless of confidence
        self.config.set_default("input_width", 224)
        self.config.set_default("input_height", 224)
        self.config.set_default("use_rgb", True)
        self.config.set_default("normalize", True)
        # Optional mean/std if normalize=True
        self.config.set_default("mean", (0.485, 0.456, 0.406))
        self.config.set_default("std", (0.229, 0.224, 0.225))

        # Visualization
        self.config.set_default("draw_result", True)
        self.config.set_default("position", (8, 24))  # x,y for top-left text
        self.config.set_default("font_scale", 0.6)
        # OK/NG overlay option
        self.config.set_default("result_display_enable", True)  # Enable OK/NG display by default
        self.config.set_default("expected_class_name", "")
        self.config.set_default("result_corner", "top-right")  # top-right, top-left, bottom-right, bottom-left

        # ROI options from previous detection output
        self.config.set_default("use_detection_roi", False)  # If True, classify each detected bbox
        self.config.set_default("classify_only_classes", [])  # If set, only classify detections with these class names
        self.config.set_default("roi_expand", 0.0)  # Expand bbox by ratio (0..0.5)

        # Validators
        # Removed threshold validator since threshold is removed
        self.config.set_validator("top_k", lambda x: int(x) >= 1)
        self.config.set_validator("roi_expand", lambda x: 0.0 <= float(x) <= 0.5)

    def _ensure_model(self) -> bool:
        if self._model_loaded:
            logger.info(f"ClassificationTool: Model already loaded")
            return True

        model_name = self.config.get("model_name")
        model_path = self.config.get("model_path")
        
        logger.info(f"ClassificationTool: Loading model - model_name='{model_name}', model_path='{model_path}'")

        # Allow users to only specify model_name; resolve to models_dir
        if (not model_path) and model_name:
            info = self.model_manager.get_model_info(model_name)
            if info:
                model_path = info.get("path", "")
                self.config.set("model_path", model_path)
                self._labels = info.get("classes", [])
                logger.info(f"ClassificationTool: Resolved model_path='{model_path}', labels={self._labels}")
        # If still no labels, try reading sidecar files via model_manager
        if not self._labels and model_name:
            info = self.model_manager.get_model_info(model_name)
            if info:
                self._labels = info.get("classes", [])

        if not model_path:
            logger.warning("ClassificationTool: No model specified")
            return False

        ok = self.classifier.load(model_path, self._labels)
        self._model_loaded = ok
        if not ok:
            logger.error(f"ClassificationTool: Failed to load model: {model_path}")
        else:
            logger.info(f"ClassificationTool: Model loaded successfully: {model_path}")
            logger.info(f"ClassificationTool: Available labels: {self._labels}")
        return ok

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

    def _classify_image(self, image: np.ndarray) -> List[Dict[str, Any]]:
        top_k = int(self.config.get("top_k", 1))
        # Removed threshold - return all predictions

        width = int(self.config.get("input_width", 224))
        height = int(self.config.get("input_height", 224))
        use_rgb = bool(self.config.get("use_rgb", True))

        normalize = bool(self.config.get("normalize", True))
        mean = self.config.get("mean") if normalize else None
        std = self.config.get("std") if normalize else None

        logger.info(f"ClassificationTool: _classify_image - input shape={image.shape}, top_k={top_k}")
        logger.info(f"ClassificationTool: _classify_image - input_size=({width}, {height}), use_rgb={use_rgb}, normalize={normalize}")

        cfg = PreprocessConfig(
            input_size=(width, height),
            use_rgb=use_rgb,
            scale=(1.0 / 255.0),
            mean=tuple(mean) if mean else None,
            std=tuple(std) if std else None,
        )

        try:
            logger.info("ClassificationTool: _classify_image - starting inference...")
            results = self.classifier.infer_topk(
                image_bgr=image,
                top_k=top_k,
                threshold=0.0,  # Set to 0.0 to get all predictions
                preprocess=cfg,
            )
            logger.info(f"ClassificationTool: _classify_image - inference completed successfully")
            logger.info(f"ClassificationTool: _classify_image - got {len(results)} results: {results}")
            return results
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
        logger.info(f"ClassificationTool: Starting classification process for image shape {image.shape}")
        
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
            if input_format in ["BGR888", "unknown"] and len(image.shape) == 3 and image.shape[2] == 3:
                # Convert BGR to RGB for classification
                logger.info(f"ClassificationTool: About to convert BGR to RGB using cv2.cvtColor")
                work_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                logger.info(f"ClassificationTool: Converted {input_format} to RGB for classification")
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
            
            logger.info(f"ClassificationTool: Config - draw_result={draw}, result_display={result_display}")
            
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
                logger.info("ClassificationTool: Performing full-frame classification")
                preds = self._classify_image(work_image)  # Use RGB work_image for classification
                logger.info(f"ClassificationTool: Got {len(preds)} predictions: {preds}")
                
                all_results.append({
                    "bbox": None,
                    "predictions": preds,
                })
                if draw and preds:
                    top1 = preds[0]
                    logger.info(f"ClassificationTool: Top prediction - {top1['class_name']} with confidence {top1['confidence']:.3f}")
                    label = f"{top1['class_name']} {top1['confidence']:.2f}"
                    pos = tuple(self.config.get("position", (8, 24)))
                    self._draw_label(result_img, label, pos)

            # Determine OK/NG status if enabled
            ok_flag: Optional[bool] = None
            if result_display:
                expected = (self.config.get("expected_class_name") or "").strip()
                # Removed threshold - evaluate all predictions regardless of confidence
                logger.info(f"ClassificationTool: OK/NG evaluation - expected_class='{expected}' (no threshold)")
                
                # Collect top1 predictions from all results
                tops: List[Dict[str, Any]] = []
                for r in all_results:
                    preds = r.get("predictions") or []
                    if preds:
                        tops.append(preds[0])
                
                logger.info(f"ClassificationTool: Evaluating {len(tops)} predictions for OK/NG")
                
                if tops:
                    # No threshold check - evaluate all predictions
                    if expected:
                        # OK if any prediction matches expected class
                        matching_preds = [t for t in tops if t.get('class_name') == expected]
                        ok_flag = len(matching_preds) > 0
                        logger.info(f"ClassificationTool: Expected class '{expected}' - found {len(matching_preds)} matching predictions")
                    else:
                        # No expected class configured: OK if we have any prediction
                        ok_flag = True
                        logger.info(f"ClassificationTool: No expected class - OK because we have {len(tops)} predictions")
                else:
                    ok_flag = False
                    logger.info("ClassificationTool: NG - no predictions available")

                # Draw OK/NG badge at corner - always show result if we have predictions
                if ok_flag is not None:
                    should_show_result = len(tops) > 0  # Show if we have any predictions
                    logger.info(f"ClassificationTool: Should show OK/NG result: {should_show_result}")
                    
                    if should_show_result:
                        try:
                            import cv2
                            label = "OK" if ok_flag else "NG"
                            color = (0, 200, 0) if ok_flag else (0, 0, 255)
                            logger.info(f"ClassificationTool: Drawing {label} badge in {color}")
                            
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
            
            logger.info(f"ClassificationTool: Process completed successfully - {len(all_results)} results")
            if all_results and all_results[0].get("predictions"):
                top_pred = all_results[0]["predictions"][0]
                logger.info(f"ClassificationTool: Final result - {top_pred['class_name']} ({top_pred['confidence']:.3f})")
            
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
