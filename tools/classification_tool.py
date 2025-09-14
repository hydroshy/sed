"""
Wrapper for ClassificationTool
------------------------------
This module mirrors the structure of tools/detect_tool.py, providing
an import-stable wrapper that delegates to the advanced implementation
in tools.classification.classification_tool.
"""

import logging
from typing import Dict, Any, Optional, Tuple, Union
import numpy as np

from .base_tool import BaseTool, ToolConfig

try:
    from tools.classification.classification_tool import ClassificationTool as _Impl
    ADV_AVAILABLE = True
except Exception:
    ADV_AVAILABLE = False
    logging.warning("Classification advanced tool not available; wrapper will be inert")


class ClassificationTool(BaseTool):
    def __init__(
        self,
        name: str = "Classification Tool",
        config: Optional[Union[Dict[str, Any], ToolConfig]] = None,
        tool_id: Optional[int] = None,
    ):
        super().__init__(name, config, tool_id)
        self._impl = _Impl(name, config, tool_id) if ADV_AVAILABLE else None

    def setup_config(self) -> None:
        if ADV_AVAILABLE:
            # Impl will set defaults; ensure we keep a few expected keys here too
            self.config.set_default("model_name", "")
            self.config.set_default("model_path", "")
        else:
            self.config.set_default("model_name", "")
            self.config.set_default("model_path", "")

    def process(self, image: np.ndarray, context: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        if not ADV_AVAILABLE or self._impl is None:
            logging.warning("ClassificationTool impl unavailable")
            return image, {"tool_name": self.display_name, "status": "error", "error": "impl_unavailable"}
        return self._impl.process(image, context)

    def update_config(self, new_config: Dict[str, Any]) -> bool:
        ok = super().update_config(new_config)
        if ADV_AVAILABLE and self._impl is not None:
            self._impl.update_config(new_config)
        return ok

    def get_info(self) -> Dict[str, Any]:
        info = super().get_info()
        if ADV_AVAILABLE and self._impl is not None:
            info.update(self._impl.get_info())
        return info


def create_classification_tool(config: Optional[Dict[str, Any]] = None) -> ClassificationTool:
    return ClassificationTool("Classification Tool", config)

