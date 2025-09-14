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
            project_root = Path(__file__).parent.parent.parent
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
            models: List[str] = []
            if self.models_dir.exists():
                # Include both .onnx and .ONNX to be robust on case-sensitive filesystems
                patterns = ["*.onnx", "*.ONNX"]
                seen = set()
                for pat in patterns:
                    for file_path in self.models_dir.glob(pat):
                        stem = file_path.stem
                        if stem not in seen:
                            seen.add(stem)
                            models.append(stem)
            models_sorted = sorted(models)
            logging.info(f"Found {len(models_sorted)} ONNX models in {self.models_dir}: {models_sorted}")
            return models_sorted
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
            
            # Try to get input/output shapes if ONNX is available
            if ONNX_AVAILABLE:
                try:
                    # Load model and analyze
                    model = onnx.load(str(model_path))
                    inputs = model.graph.input
                    outputs = model.graph.output
                    
                    # Get input shape
                    if inputs and inputs[0].type.tensor_type.shape.dim:
                        dims = inputs[0].type.tensor_type.shape.dim
                        if len(dims) == 4:  # NCHW format
                            # Get dynamic or static shape
                            n = dims[0].dim_value or -1
                            c = dims[1].dim_value or -1
                            h = dims[2].dim_value or -1
                            w = dims[3].dim_value or -1
                            info['input_shape'] = [n, c, h, w]
                    
                    # Get output shapes (multiple outputs possible)
                    output_shapes = []
                    for output in outputs:
                        if output.type.tensor_type.shape.dim:
                            dims = output.type.tensor_type.shape.dim
                            shape = [dim.dim_value or -1 for dim in dims]
                            output_shapes.append(shape)
                    if output_shapes:
                        info['output_shape'] = output_shapes
                        
                    logging.info(f"Model {model_name} input shape: {info['input_shape']}, output shape: {info['output_shape']}")
                except Exception as e:
                    logging.warning(f"Error analyzing ONNX model {model_name}: {e}")
            
            # Add to cache
            self._model_cache[model_name] = info
            return info
            
        except Exception as e:
            logging.error(f"Error getting model info for {model_name}: {e}")
            return None
    
    def _load_model_classes(self, model_path: Path) -> List[str]:
        """
        Load class names for a model
        
        Args:
            model_path: Path to ONNX model file
            
        Returns:
            List of class names
        """
        try:
            # Try to load class list from adjacent text file
            classes_file = model_path.with_suffix('.txt')
            if classes_file.exists():
                with open(classes_file, 'r') as f:
                    classes = [line.strip() for line in f.readlines()]
                logging.info(f"Loaded {len(classes)} classes from {classes_file}")
                return classes
                
            # Try to load from JSON file
            json_file = model_path.with_suffix('.json')
            if json_file.exists():
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        classes = data
                    elif isinstance(data, dict) and 'classes' in data:
                        classes = data['classes']
                    elif isinstance(data, dict):
                        # Handle index-to-class-name mapping (e.g., {"0": "barcode", "1": "hangtag"})
                        try:
                            # Sort by index to maintain order
                            sorted_items = sorted(data.items(), key=lambda x: int(x[0]))
                            classes = [item[1] for item in sorted_items]
                            logging.info(f"Loaded {len(classes)} classes from index-to-name mapping in {json_file}")
                        except (ValueError, TypeError):
                            # If keys can't be converted to integers, just use values
                            classes = list(data.values())
                            logging.info(f"Loaded {len(classes)} classes from dict values in {json_file}")
                    else:
                        classes = []
                logging.info(f"Loaded {len(classes)} classes from {json_file}")
                return classes
                
            # Look for 'coco' in the model name to use default COCO classes
            if 'coco' in model_path.stem.lower():
                logging.info(f"Using default COCO classes for {model_path.stem}")
                return self._default_class_names['coco']
                
            # Default to empty class list with unknown-0, unknown-1, etc.
            logging.warning(f"No class list found for {model_path.stem}, using numbered placeholders")
            return [f"unknown-{i}" for i in range(80)]  # Default to 80 classes for COCO models
            
        except Exception as e:
            logging.error(f"Error loading classes for {model_path.stem}: {e}")
            return [f"unknown-{i}" for i in range(80)]
    
    def add_model(self, model_path: str, class_names: List[str] = None) -> bool:
        """
        Add a new model to the models directory
        
        Args:
            model_path: Path to ONNX model file
            class_names: Optional list of class names
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if model path exists
            src_path = Path(model_path)
            if not src_path.exists():
                logging.error(f"Model file not found: {model_path}")
                return False
                
            # Check if file is ONNX
            if src_path.suffix.lower() != '.onnx':
                logging.error(f"File is not ONNX model: {model_path}")
                return False
                
            # Copy model to models directory
            dst_path = self.models_dir / src_path.name
            import shutil
            shutil.copy2(src_path, dst_path)
            
            # Write class names if provided
            if class_names:
                classes_file = dst_path.with_suffix('.txt')
                with open(classes_file, 'w') as f:
                    for class_name in class_names:
                        f.write(f"{class_name}\n")
                        
            # Clear cache for this model
            if dst_path.stem in self._model_cache:
                del self._model_cache[dst_path.stem]
                
            logging.info(f"Added model {src_path.name} to models directory")
            return True
            
        except Exception as e:
            logging.error(f"Error adding model {model_path}: {e}")
            return False
    
    def validate_model(self, model_name: str) -> Tuple[bool, str]:
        """
        Validate an ONNX model for inference
        
        Args:
            model_name: Name of the model to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        if not ONNX_AVAILABLE:
            return False, "ONNX or ONNXRuntime not available"
            
        try:
            # Get model info
            info = self.get_model_info(model_name)
            if not info:
                return False, f"Model {model_name} not found"
                
            model_path = info['path']
            
            # Check model exists
            if not os.path.exists(model_path):
                return False, f"Model file does not exist: {model_path}"
                
            # Try to load and check model with ONNX
            try:
                model = onnx.load(model_path)
                onnx.checker.check_model(model)
            except Exception as e:
                return False, f"ONNX model check failed: {e}"
                
            # Try to create inference session
            try:
                session = ort.InferenceSession(model_path)
                
                # Check input and output shapes
                inputs = session.get_inputs()
                outputs = session.get_outputs()
                
                if not inputs:
                    return False, "Model has no inputs"
                if not outputs:
                    return False, "Model has no outputs"
                    
                # Check if model has expected input shape
                input_shape = inputs[0].shape
                if len(input_shape) != 4:  # NCHW format
                    return False, f"Unexpected input shape: {input_shape}, expected NCHW format"
                    
                # Check if model has expected output shape for YOLO
                # YOLO output formats vary, but they generally have shape [batch, boxes, 5+classes]
                # or similar formats with detection information
                
                logging.info(f"Model {model_name} validated successfully")
                return True, "Model validated successfully"
                
            except Exception as e:
                return False, f"ONNX runtime initialization failed: {e}"
                
        except Exception as e:
            logging.error(f"Error validating model {model_name}: {e}")
            return False, f"Validation error: {e}"
    
    def remove_model(self, model_name: str) -> bool:
        """
        Remove a model from the models directory
        
        Args:
            model_name: Name of the model to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if model exists
            model_path = self.models_dir / f"{model_name}.onnx"
            if not model_path.exists():
                logging.warning(f"Model not found: {model_path}")
                return False
                
            # Remove model file
            model_path.unlink()
            
            # Remove class file if it exists
            classes_file = model_path.with_suffix('.txt')
            if classes_file.exists():
                classes_file.unlink()
                
            # Remove JSON file if it exists
            json_file = model_path.with_suffix('.json')
            if json_file.exists():
                json_file.unlink()
                
            # Remove from cache
            if model_name in self._model_cache:
                del self._model_cache[model_name]
                
            logging.info(f"Removed model {model_name}")
            return True
            
        except Exception as e:
            logging.error(f"Error removing model {model_name}: {e}")
            return False
