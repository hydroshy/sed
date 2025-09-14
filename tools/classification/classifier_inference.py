"""
ONNX Classification Inference Engine
------------------------------------
Lightweight classifier wrapper for ONNX models. Handles:
- Session creation via onnxruntime
- Input size discovery (or default 224x224)
- BGR/RGB conversion, normalization
- Softmax + top-k selection
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

import numpy as np

logger = logging.getLogger(__name__)

try:
    import onnxruntime as ort
    ONNXRT_AVAILABLE = True
except Exception:
    ONNXRT_AVAILABLE = False
    logger.warning("onnxruntime not available; classification disabled")


@dataclass
class PreprocessConfig:
    input_size: Tuple[int, int] = (224, 224)  # (W, H)
    use_rgb: bool = True  # Convert BGR->RGB before feeding the model
    scale: float = 1.0 / 255.0
    mean: Optional[Tuple[float, float, float]] = None  # e.g., (0.485, 0.456, 0.406)
    std: Optional[Tuple[float, float, float]] = None   # e.g., (0.229, 0.224, 0.225)


class ClassifierInference:
    def __init__(self) -> None:
        self.session: Optional["ort.InferenceSession"] = None
        self.input_name: Optional[str] = None
        self.input_shape: Optional[Tuple[int, int, int, int]] = None  # NCHW
        self.labels: List[str] = []

    def load(self, model_path: str, labels: List[str]) -> bool:
        if not ONNXRT_AVAILABLE:
            logger.error("onnxruntime is not available; cannot load model")
            return False
        try:
            sess = ort.InferenceSession(model_path)
            self.session = sess
            inp = sess.get_inputs()[0]
            self.input_name = inp.name
            # Shape may contain None/-1; extract best-effort
            shape = inp.shape
            try:
                n = int(shape[0]) if shape[0] is not None else 1
                c = int(shape[1]) if shape[1] is not None else 3
                h = int(shape[2]) if shape[2] is not None else 224
                w = int(shape[3]) if shape[3] is not None else 224
            except Exception:
                n, c, h, w = 1, 3, 224, 224
            self.input_shape = (n, c, h, w)
            self.labels = labels or []
            logger.info(f"Loaded classifier: {model_path} input={self.input_shape} labels={len(self.labels)}")
            return True
        except Exception as e:
            logger.error(f"Failed to load classification model: {e}")
            return False

    def _preprocess(self, image_bgr: np.ndarray, cfg: PreprocessConfig) -> np.ndarray:
        import cv2
        h, w = image_bgr.shape[:2]

        target_w, target_h = cfg.input_size
        resized = cv2.resize(image_bgr, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
        if cfg.use_rgb:
            resized = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        x = resized.astype(np.float32) * cfg.scale
        if cfg.mean is not None and cfg.std is not None:
            mean = np.array(cfg.mean, dtype=np.float32).reshape(1, 1, 3)
            std = np.array(cfg.std, dtype=np.float32).reshape(1, 1, 3)
            x = (x - mean) / std

        # HWC -> CHW -> NCHW
        x = np.transpose(x, (2, 0, 1))
        x = np.expand_dims(x, axis=0)
        return x

    @staticmethod
    def _softmax(logits: np.ndarray) -> np.ndarray:
        logits = logits - np.max(logits)
        exp = np.exp(logits)
        return exp / np.sum(exp)

    def infer_topk(
        self,
        image_bgr: np.ndarray,
        top_k: int = 1,
        threshold: float = 0.0,
        preprocess: Optional[PreprocessConfig] = None,
    ) -> List[Dict[str, Any]]:
        if self.session is None or self.input_name is None:
            raise RuntimeError("Model not loaded")

        if preprocess is None:
            # Derive input size from model if available
            size = (224, 224)
            if self.input_shape is not None:
                _, _, h, w = self.input_shape
                if isinstance(h, int) and isinstance(w, int) and h > 0 and w > 0:
                    size = (w, h)
            preprocess = PreprocessConfig(input_size=size)

        inp = self._preprocess(image_bgr, preprocess)
        outputs = self.session.run(None, {self.input_name: inp})
        logits = outputs[0].squeeze()
        logits = np.array(logits, dtype=np.float32).reshape(-1)

        probs = self._softmax(logits)
        idx = np.argsort(probs)[::-1]

        results: List[Dict[str, Any]] = []
        for i in idx[: max(1, top_k)]:
            score = float(probs[i])
            if score < threshold:
                continue
            label = self.labels[i] if i < len(self.labels) and self.labels else f"class_{i}"
            results.append({
                "class_id": int(i),
                "class_name": label,
                "confidence": score,
            })
        return results


def create_classifier_inference() -> ClassifierInference:
    return ClassifierInference()

