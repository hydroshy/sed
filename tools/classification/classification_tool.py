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
        self.config.set_default("threshold", 0.0)
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

        # ROI options from previous detection output
        self.config.set_default("use_detection_roi", False)  # If True, classify each detected bbox
        self.config.set_default("classify_only_classes", [])  # If set, only classify detections with these class names
        self.config.set_default("roi_expand", 0.0)  # Expand bbox by ratio (0..0.5)

        # Validators
        self.config.set_validator("threshold", lambda x: 0.0 <= float(x) <= 1.0)
        self.config.set_validator("top_k", lambda x: int(x) >= 1)
        self.config.set_validator("roi_expand", lambda x: 0.0 <= float(x) <= 0.5)

    def _ensure_model(self) -> bool:
        if self._model_loaded:
            return True

        model_name = self.config.get("model_name")
        model_path = self.config.get("model_path")

        # Allow users to only specify model_name; resolve to models_dir
        if (not model_path) and model_name:
            info = self.model_manager.get_model_info(model_name)
            if info:
                model_path = info.get("path", "")
                self.config.set("model_path", model_path)
                self._labels = info.get("classes", [])
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
            logger.info(f"ClassificationTool: Model loaded: {model_path}")
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
        threshold = float(self.config.get("threshold", 0.0))

        width = int(self.config.get("input_width", 224))
        height = int(self.config.get("input_height", 224))
        use_rgb = bool(self.config.get("use_rgb", True))

        normalize = bool(self.config.get("normalize", True))
        mean = self.config.get("mean") if normalize else None
        std = self.config.get("std") if normalize else None

        cfg = PreprocessConfig(
            input_size=(width, height),
            use_rgb=use_rgb,
            scale=(1.0 / 255.0),
            mean=tuple(mean) if mean else None,
            std=tuple(std) if std else None,
        )

        return self.classifier.infer_topk(
            image_bgr=image,
            top_k=top_k,
            threshold=threshold,
            preprocess=cfg,
        )

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
        if not self._ensure_model():
            return image, {
                "tool_name": self.display_name,
                "status": "error",
                "error": "Model not loaded",
            }

        try:
            draw = bool(self.config.get("draw_result", True))
            result_img = image.copy() if draw else image
            h, w = image.shape[:2]

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
                    crop = image[y1:y2, x1:x2]
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
                preds = self._classify_image(image)
                all_results.append({
                    "bbox": None,
                    "predictions": preds,
                })
                if draw and preds:
                    top1 = preds[0]
                    label = f"{top1['class_name']} {top1['confidence']:.2f}"
                    pos = tuple(self.config.get("position", (8, 24)))
                    self._draw_label(result_img, label, pos)

            output = {
                "tool_name": self.display_name,
                "status": "success",
                "results": all_results,
                "result_count": len(all_results),
            }
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

