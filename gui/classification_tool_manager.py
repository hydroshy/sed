import logging
from pathlib import Path
from typing import List, Optional

from PyQt5.QtWidgets import QComboBox

from tools.detection.model_manager import ModelManager


class ClassificationToolManager:
    """Lightweight manager for Classification Tool UI (model/classes combos)."""

    def __init__(self, main_window):
        self.main_window = main_window
        self.model_combo: Optional[QComboBox] = None
        self.class_combo: Optional[QComboBox] = None
        self.model_manager: Optional[ModelManager] = None

        # Resolve classification models dir relative to project root
        project_root = Path(__file__).parent.parent
        models_dir = project_root / "model" / "classification"
        self.model_manager = ModelManager(str(models_dir))
        logging.info(f"ClassificationToolManager initialized with models dir: {models_dir}")

    def setup_ui_components(self, model_combo: QComboBox, class_combo: QComboBox):
        self.model_combo = model_combo
        self.class_combo = class_combo

        # Use 'is None' instead of truthiness check to avoid PyQt5 boolean evaluation bug
        if self.model_combo is None or self.class_combo is None:
            logging.warning("ClassificationToolManager: model or class combo is missing")
            logging.warning(f"model_combo: {self.model_combo is not None}, class_combo: {self.class_combo is not None}")
            return

        logging.info("ClassificationToolManager: both combo boxes confirmed, setting up connections")
        self._force_refresh_connections()
        self.load_available_models()

    def _force_refresh_connections(self):
        # Use 'is None' instead of truthiness check to avoid PyQt5 boolean evaluation bug
        if self.model_combo is None:
            return
        try:
            self.model_combo.currentTextChanged.disconnect()
            self.model_combo.activated.disconnect()
        except Exception:
            pass
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        self.model_combo.activated.connect(self._on_model_index_activated)
        logging.info("ClassificationToolManager: connected model combo signals")

    def load_available_models(self):
        # Use 'is None' instead of truthiness check to avoid PyQt5 boolean evaluation bug
        if self.model_combo is None:
            logging.warning("ClassificationToolManager: model_combo is None in load_available_models")
            return
            
        # Verify combo box is accessible
        try:
            test_count = self.model_combo.count()
            logging.info(f"ClassificationToolManager: model_combo accessible, current count={test_count}")
        except Exception as e:
            logging.error(f"ClassificationToolManager: model_combo not accessible: {e}")
            return
            
        # Check combo box state
        logging.info(f"ClassificationToolManager: model_combo enabled={self.model_combo.isEnabled()}, visible={self.model_combo.isVisible()}")
        
        try:
            logging.info("ClassificationToolManager: Starting model loading process...")
            self.model_combo.blockSignals(True)
            self.model_combo.clear()
            logging.info("ClassificationToolManager: Cleared existing items")

            models: List[str] = []
            try:
                models = self.model_manager.get_available_models() if self.model_manager else []
                logging.info(f"ClassificationToolManager: ModelManager returned {len(models)} models: {models}")
            except Exception as e:
                logging.error(f"ClassificationToolManager: error getting models: {e}")
                models = []

            if not models:
                # Fallback to direct glob
                try:
                    models_dir = Path(self.model_manager.models_dir) if self.model_manager else None
                    if models_dir and models_dir.exists():
                        models = sorted({p.stem for p in list(models_dir.glob('*.onnx')) + list(models_dir.glob('*.ONNX'))})
                        logging.info(f"ClassificationToolManager: Fallback glob found {len(models)} models: {models}")
                except Exception as e:
                    logging.warning(f"ClassificationToolManager: fallback glob failed: {e}")

            if not models:
                self.model_combo.addItem("No models found")
                logging.warning("ClassificationToolManager: no models found, added placeholder")
            else:
                self.model_combo.addItem("Select Model...")
                logging.info("ClassificationToolManager: Added 'Select Model...' item")
                for m in models:
                    self.model_combo.addItem(m)
                    logging.info(f"ClassificationToolManager: Added model '{m}'")
                logging.info(f"ClassificationToolManager: loaded {len(models)} models: {models}")
                
                # Keep default selection on "Select Model..." (index 0)
                # Do not auto-select any model - let user choose manually
                logging.info("ClassificationToolManager: Keeping default 'Select Model...' selection")
                
                # Initialize class combo with default state
                if self.class_combo is not None:
                    self._clear_classes()
                    
            # Force enable the combo box
            self.model_combo.setEnabled(True)
            logging.info(f"ClassificationToolManager: forced model_combo enabled={self.model_combo.isEnabled()}")
            
            # Also enable class combo
            if self.class_combo:
                self.class_combo.setEnabled(True)
                logging.info(f"ClassificationToolManager: forced class_combo enabled={self.class_combo.isEnabled()}")
                
            self.model_combo.blockSignals(False)
            logging.info("ClassificationToolManager: Unblocked signals")

            # Log final items
            try:
                items = [self.model_combo.itemText(i) for i in range(self.model_combo.count())]
                logging.info(f"ClassificationToolManager: Final modelComboBox items: {items}")
            except Exception as e:
                logging.error(f"ClassificationToolManager: Error reading final items: {e}")
                
        except Exception as e:
            logging.error(f"ClassificationToolManager: load_available_models error: {e}")
            import traceback
            traceback.print_exc()

    def _on_model_index_activated(self, index: int):
        # Use 'is None' instead of truthiness check to avoid PyQt5 boolean evaluation bug
        if self.model_combo is None or index < 0:
            return
        name = self.model_combo.itemText(index)
        logging.info(f"ClassificationToolManager: model activated index={index} '{name}'")
        self._on_model_changed(name)

    def _on_model_changed(self, model_name: str):
        logging.info(f"ClassificationToolManager: model changed to '{model_name}'")
        if not model_name or model_name in ("Select Model...", "No models found", "Error loading models"):
            self._clear_classes()
            return
        try:
            info = self.model_manager.get_model_info(model_name) if self.model_manager else None
            classes = info.get('classes', []) if info else []
            if not classes:
                # Sidecar fallback
                try:
                    models_dir = Path(self.model_manager.models_dir) if self.model_manager else None
                    if models_dir:
                        mp = models_dir / f"{model_name}.onnx"
                        txt = mp.with_suffix('.txt')
                        js = mp.with_suffix('.json')
                        if txt.exists():
                            classes = [line.strip() for line in txt.read_text(encoding='utf-8', errors='ignore').splitlines() if line.strip()]
                        elif js.exists():
                            import json
                            data = json.loads(js.read_text(encoding='utf-8', errors='ignore'))
                            if isinstance(data, list):
                                classes = [str(x) for x in data]
                            elif isinstance(data, dict):
                                try:
                                    items = sorted(data.items(), key=lambda kv: int(kv[0]))
                                    classes = [str(v) for _, v in items]
                                except Exception:
                                    classes = [str(v) for v in data.values()]
                except Exception as e:
                    logging.warning(f"ClassificationToolManager: sidecar class load failed: {e}")

            self._load_classes(classes)
        except Exception as e:
            logging.error(f"ClassificationToolManager: _on_model_changed error: {e}")

    def _load_classes(self, classes: List[str]):
        # Use 'is None' instead of truthiness check to avoid PyQt5 boolean evaluation bug
        if self.class_combo is None:
            return
        try:
            self.class_combo.blockSignals(True)
            self.class_combo.clear()
            if not classes:
                self.class_combo.addItem("No classes")
                logging.info("ClassificationToolManager: no classes found for model")
            else:
                self.class_combo.addItem("Select Class...")
                for c in classes:
                    self.class_combo.addItem(c)
                logging.info(f"ClassificationToolManager: loaded {len(classes)} classes")
            self.class_combo.blockSignals(False)
        except Exception as e:
            logging.error(f"ClassificationToolManager: _load_classes error: {e}")

    def _clear_classes(self):
        # Use 'is None' instead of truthiness check to avoid PyQt5 boolean evaluation bug
        if self.class_combo is None:
            return
        self.class_combo.blockSignals(True)
        self.class_combo.clear()
        self.class_combo.addItem("Select Class...")
        self.class_combo.blockSignals(False)

