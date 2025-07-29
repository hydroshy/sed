import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Try to import ONNX libraries, handle gracefully if not available
try:
    import onnx
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logging.warning("ONNX or ONNXRuntime not available. Model validation will be limited.")

class ModelManager:
    """Manager for YOLO ONNX models and their classes"""
    
    def __init__(self, models_dir: str = None):
        """
        Initialize ModelManager
        
        Args:
            models_dir: Path to directory containing ONNX models
        """
        if models_dir is None:
            # Default to model/detect directory relative to project root
            project_root = Path(__file__).parent.parent
            self.models_dir = project_root / "model" / "detect"
        else:
            self.models_dir = Path(models_dir)
            
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache for model info
        self._model_cache = {}
        
        # Common YOLO class names for different models
        self._default_class_names = {
            'coco': [
                'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light',
                'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
                'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
                'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
                'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
                'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
                'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
                'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear',
                'hair drier', 'toothbrush'
            ]
        }
        
        logging.info(f"ModelManager initialized with models directory: {self.models_dir}")
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available ONNX model files
        
        Returns:
            List of model filenames (without extension)
        """
        try:
            models = []
            if self.models_dir.exists():
                for file_path in self.models_dir.glob("*.onnx"):
                    models.append(file_path.stem)
            logging.info(f"Found {len(models)} ONNX models: {models}")
            return sorted(models)
        except Exception as e:
            logging.error(f"Error getting available models: {e}")
            return []
    
    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """
        Get information about a specific model
        
        Args:
            model_name: Name of the model (without .onnx extension)
            
        Returns:
            Dictionary with model info or None if not found
        """
        try:
            model_path = self.models_dir / f"{model_name}.onnx"
            if not model_path.exists():
                logging.warning(f"Model not found: {model_path}")
                return None
            
            # Check cache first
            if model_name in self._model_cache:
                return self._model_cache[model_name]
            
            # Load model info
            info = {
                'name': model_name,
                'path': str(model_path),
                'classes': self._load_model_classes(model_path),
                'input_shape': None,
                'output_shape': None
            }
            
            # Try to get input/output shapes
            if ONNX_AVAILABLE:
                try:
                    session = ort.InferenceSession(str(model_path))
                    if session.get_inputs():
                        info['input_shape'] = session.get_inputs()[0].shape
                    if session.get_outputs():
                        info['output_shape'] = session.get_outputs()[0].shape
                except Exception as e:
                    logging.warning(f"Could not load model session for {model_name}: {e}")
            else:
                logging.warning("ONNX not available, skipping model shape detection")
            
            # Cache the info
            self._model_cache[model_name] = info
            
            return info
            
        except Exception as e:
            logging.error(f"Error getting model info for {model_name}: {e}")
            return None
    
    def _load_model_classes(self, model_path: Path) -> List[str]:
        """
        Load class names for a model
        
        Args:
            model_path: Path to the ONNX model file
            
        Returns:
            List of class names
        """
        try:
            # First try to find a .names or .txt file with the same name
            names_files = [
                model_path.with_suffix('.names'),
                model_path.with_suffix('.txt'),
                model_path.parent / f"{model_path.stem}_classes.txt",
                model_path.parent / "classes.txt"
            ]
            
            for names_file in names_files:
                if names_file.exists():
                    with open(names_file, 'r', encoding='utf-8') as f:
                        classes = [line.strip() for line in f.readlines() if line.strip()]
                    logging.info(f"Loaded {len(classes)} classes from {names_file}")
                    return classes
            
            # Try to find a JSON metadata file
            json_files = [
                model_path.with_suffix('.json'),
                model_path.parent / f"{model_path.stem}_metadata.json",
                model_path.parent / f"{model_path.stem}_config.json",
                model_path.parent / "config.json"
            ]
            
            for json_file in json_files:
                if json_file.exists():
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            
                        # Handle different JSON formats
                        classes = None
                        
                        # Format 1: Direct list in 'classes' key
                        class_keys = ['classes', 'class_names', 'names', 'labels']
                        for key in class_keys:
                            if key in metadata:
                                if isinstance(metadata[key], list) and len(metadata[key]) > 0:
                                    classes = metadata[key]
                                    logging.info(f"Loaded {len(classes)} classes from JSON file {json_file} (key: {key}, format: list)")
                                    break
                                elif isinstance(metadata[key], dict):
                                    # Format 2: Dictionary mapping index to class name {"0": "class1", "1": "class2"}
                                    class_dict = metadata[key]
                                    # Sort by numeric keys to maintain order
                                    sorted_keys = sorted(class_dict.keys(), key=lambda x: int(x) if x.isdigit() else float('inf'))
                                    classes = [class_dict[k] for k in sorted_keys]
                                    logging.info(f"Loaded {len(classes)} classes from JSON file {json_file} (key: {key}, format: dict)")
                                    break
                        
                        # Format 3: Root level dictionary with numeric string keys
                        if not classes and isinstance(metadata, dict):
                            # Check if all keys are numeric strings
                            if all(k.isdigit() for k in metadata.keys()):
                                sorted_keys = sorted(metadata.keys(), key=int)
                                classes = [metadata[k] for k in sorted_keys]
                                logging.info(f"Loaded {len(classes)} classes from JSON file {json_file} (format: root dict)")
                        
                        if classes:
                            return classes
                                    
                        # If no classes found, log available keys for debugging
                        logging.debug(f"JSON file {json_file} found but no classes. Available keys: {list(metadata.keys())}")
                        
                    except json.JSONDecodeError as e:
                        logging.warning(f"Invalid JSON format in {json_file}: {e}")
                    except Exception as e:
                        logging.warning(f"Error reading JSON file {json_file}: {e}")
            
            # Try to extract from ONNX model metadata
            if ONNX_AVAILABLE:
                try:
                    model = onnx.load(str(model_path))
                    for prop in model.metadata_props:
                        if prop.key in ['names', 'classes', 'class_names']:
                            try:
                                # Try to parse as JSON first
                                classes = json.loads(prop.value)
                                if isinstance(classes, list):
                                    logging.info(f"Loaded {len(classes)} classes from ONNX metadata (JSON)")
                                    return classes
                            except:
                                try:
                                    # Try to evaluate as Python list
                                    classes = eval(prop.value)
                                    if isinstance(classes, list):
                                        logging.info(f"Loaded {len(classes)} classes from ONNX metadata (eval)")
                                        return classes
                                except:
                                    # Try to split as comma-separated string
                                    classes = [cls.strip() for cls in prop.value.split(',')]
                                    if len(classes) > 1:
                                        logging.info(f"Loaded {len(classes)} classes from ONNX metadata (split)")
                                        return classes
                except Exception as e:
                    logging.debug(f"Could not extract classes from ONNX metadata: {e}")
            
            # For YOLOv11 and similar models, try to infer from filename
            model_name_lower = model_path.stem.lower()
            if 'yolo' in model_name_lower or 'coco' in model_name_lower:
                logging.info(f"Using COCO classes for YOLO model: {model_path.stem}")
                return self._default_class_names['coco']
            
            # Default to COCO classes if nothing found
            logging.info(f"Using default COCO classes for model: {model_path.stem}")
            return self._default_class_names['coco']
            
        except Exception as e:
            logging.error(f"Error loading model classes: {e}")
            return self._default_class_names['coco']
    
    def create_model_metadata(self, model_name: str, classes: List[str], overwrite: bool = False, additional_info: Dict = None):
        """
        Create a metadata file for a model with class names
        
        Args:
            model_name: Name of the model
            classes: List of class names
            overwrite: Whether to overwrite existing metadata
            additional_info: Additional metadata to include
        """
        try:
            metadata_file = self.models_dir / f"{model_name}.json"
            
            if metadata_file.exists() and not overwrite:
                logging.warning(f"Metadata file already exists: {metadata_file}")
                return
            
            metadata = {
                'model_name': model_name,
                'classes': classes,
                'num_classes': len(classes),
                'model_type': 'YOLO',
                'framework': 'ONNX',
                'created_at': str(Path(__file__).stat().st_mtime)
            }
            
            # Add additional info if provided
            if additional_info:
                metadata.update(additional_info)
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Clear cache for this model
            if model_name in self._model_cache:
                del self._model_cache[model_name]
            
            logging.info(f"Created metadata file for {model_name} with {len(classes)} classes")
            
        except Exception as e:
            logging.error(f"Error creating model metadata: {e}")
    
    def auto_generate_metadata(self, model_name: str, overwrite: bool = False):
        """
        Auto-generate metadata for a model based on filename and available information
        
        Args:
            model_name: Name of the model
            overwrite: Whether to overwrite existing metadata
        """
        try:
            model_path = self.models_dir / f"{model_name}.onnx"
            if not model_path.exists():
                logging.error(f"Model file not found: {model_path}")
                return
            
            # Try to determine model type and version from filename
            model_name_lower = model_name.lower()
            additional_info = {}
            
            if 'yolo' in model_name_lower:
                additional_info['model_type'] = 'YOLO'
                
                # Try to extract version
                if 'v11' in model_name_lower or 'yolo11' in model_name_lower:
                    additional_info['version'] = '11'
                elif 'v8' in model_name_lower or 'yolo8' in model_name_lower:
                    additional_info['version'] = '8'
                elif 'v5' in model_name_lower or 'yolo5' in model_name_lower:
                    additional_info['version'] = '5'
                
                # Try to extract model size
                if 'nano' in model_name_lower or 'n' in model_name_lower.split('v')[-1]:
                    additional_info['size'] = 'nano'
                elif 'small' in model_name_lower or 's' in model_name_lower.split('v')[-1]:
                    additional_info['size'] = 'small'
                elif 'medium' in model_name_lower or 'm' in model_name_lower.split('v')[-1]:
                    additional_info['size'] = 'medium'
                elif 'large' in model_name_lower or 'l' in model_name_lower.split('v')[-1]:
                    additional_info['size'] = 'large'
                elif 'xlarge' in model_name_lower or 'x' in model_name_lower.split('v')[-1]:
                    additional_info['size'] = 'xlarge'
            
            # Use COCO classes as default for YOLO models
            classes = self._default_class_names['coco']
            additional_info['description'] = f"Auto-generated metadata for {model_name}"
            
            # Try to get model shapes if ONNX is available
            if ONNX_AVAILABLE:
                try:
                    session = ort.InferenceSession(str(model_path))
                    if session.get_inputs():
                        additional_info['input_shape'] = session.get_inputs()[0].shape
                    if session.get_outputs():
                        additional_info['output_shape'] = session.get_outputs()[0].shape
                except Exception as e:
                    logging.debug(f"Could not get model shapes: {e}")
            
            self.create_model_metadata(model_name, classes, overwrite, additional_info)
            
        except Exception as e:
            logging.error(f"Error auto-generating metadata for {model_name}: {e}")
    
    def validate_model(self, model_name: str) -> Tuple[bool, str]:
        """
        Validate that a model can be loaded and used
        
        Args:
            model_name: Name of the model to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            model_path = self.models_dir / f"{model_name}.onnx"
            
            if not model_path.exists():
                return False, f"Model file not found: {model_path}"
            
            if not ONNX_AVAILABLE:
                # Basic validation without ONNX libraries
                if model_path.stat().st_size == 0:
                    return False, "Model file is empty"
                return True, "Model file exists (ONNX libraries not available for full validation)"
            
            # Try to create inference session
            session = ort.InferenceSession(str(model_path))
            
            # Check that model has expected inputs/outputs
            if not session.get_inputs():
                return False, "Model has no inputs"
            
            if not session.get_outputs():
                return False, "Model has no outputs"
            
            return True, "Model is valid"
            
        except Exception as e:
            return False, f"Model validation failed: {e}"
