"""
Detect Tool for Job System Integration
Integrates YOLO detection with the existing job processing pipeline
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
import time

try:
    from job.job_manager import Tool, ToolConfig
    from detection.detect_tool_job import create_detect_tool_job
    from detection.visualization import create_detection_display
    JOB_SYSTEM_AVAILABLE = True
except ImportError:
    JOB_SYSTEM_AVAILABLE = False

logger = logging.getLogger(__name__)

class DetectTool(Tool):
    """Detect Tool implementation for job system"""
    
    def __init__(self, name: str = "Detect Tool", config: Optional[Union[Dict[str, Any], ToolConfig]] = None, tool_id: Optional[int] = None):
        super().__init__(name, config, tool_id)
        self.detect_job = None
        self.last_detections = []
        self.execution_enabled = True
        
    def setup_config(self) -> None:
        """Setup default configuration for Detect Tool"""
        # Set default values
        self.config.set_default('model_name', '')
        self.config.set_default('model_path', '')
        self.config.set_default('selected_classes', [])
        self.config.set_default('confidence_threshold', 0.5)
        self.config.set_default('nms_threshold', 0.4)
        self.config.set_default('detection_region', None)  # (x1, y1, x2, y2) or None for full image
        self.config.set_default('visualize_results', True)
        self.config.set_default('show_confidence', True)
        self.config.set_default('show_class_names', True)
        
        # Set validators
        self.config.set_validator('confidence_threshold', lambda x: 0.0 <= x <= 1.0)
        self.config.set_validator('nms_threshold', lambda x: 0.0 <= x <= 1.0)
        self.config.set_validator('selected_classes', lambda x: isinstance(x, list))
        
        logger.info(f"DetectTool {self.display_name} configuration setup completed")
    
    def initialize_detection(self) -> bool:
        """Initialize detection job with current config"""
        try:
            # Get configuration
            tool_config = {
                'model_name': self.config.get('model_name'),
                'model_path': self.config.get('model_path'),
                'selected_classes': self.config.get('selected_classes'),
                'confidence_threshold': self.config.get('confidence_threshold'),
                'nms_threshold': self.config.get('nms_threshold')
            }
            
            # Validate configuration
            if not tool_config['model_name'] or not tool_config['model_path']:
                logger.error(f"DetectTool {self.display_name}: No model specified")
                return False
            
            if not tool_config['selected_classes']:
                logger.warning(f"DetectTool {self.display_name}: No classes selected, will detect all classes")
            
            # Create detection job
            self.detect_job = create_detect_tool_job(tool_config)
            
            # Initialize the job
            success = self.detect_job.initialize()
            if success:
                logger.info(f"DetectTool {self.display_name} initialized successfully")
            else:
                logger.error(f"DetectTool {self.display_name} initialization failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error initializing DetectTool {self.display_name}: {e}")
            return False
    
    def process(self, image: np.ndarray, context: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Process image with YOLO detection
        
        Args:
            image: Input image (BGR format)
            context: Processing context from previous tools
            
        Returns:
            Tuple of (processed_image, results)
        """
        logger.info(f"===== DetectTool.process CALLED =====")
        logger.info(f"Image shape: {image.shape}")
        logger.info(f"Tool name: {self.display_name}")
        logger.info(f"Execution enabled: {self.execution_enabled}")
        logger.info(f"Detect job initialized: {self.detect_job is not None}")
        
        start_time = time.time()
        
        try:
            # Check if execution is enabled
            if not self.execution_enabled:
                logger.debug(f"DetectTool {self.display_name} execution disabled")
                return image, {
                    'tool_name': self.display_name,
                    'execution_time': 0,
                    'detections': [],
                    'status': 'disabled'
                }
            
            # Initialize detection if not done
            if not self.detect_job:
                if not self.initialize_detection():
                    return image, {
                        'tool_name': self.display_name,
                        'execution_time': 0,
                        'detections': [],
                        'status': 'initialization_failed',
                        'error': 'Failed to initialize detection job'
                    }
            
            # Get detection region from config or context
            detection_region = self.config.get('detection_region')
            if context and 'detection_region' in context:
                detection_region = context['detection_region']
            
            # Run detection
            detection_result = self.detect_job.execute(image, detection_region)
            
            if not detection_result['success']:
                logger.error(f"DetectTool {self.display_name} execution failed: {detection_result.get('error', 'Unknown error')}")
                return image, {
                    'tool_name': self.display_name,
                    'execution_time': time.time() - start_time,
                    'detections': [],
                    'status': 'execution_failed',
                    'error': detection_result.get('error', 'Unknown error')
                }
            
            # Extract detections
            detections = detection_result['detections']
            self.last_detections = detections
            
            # Create visualization if enabled
            processed_image = image
            if self.config.get('visualize_results', True):
                try:
                    processed_image = create_detection_display(
                        image, 
                        detections, 
                        detection_region
                    )
                except Exception as e:
                    logger.error(f"Visualization error in DetectTool {self.display_name}: {e}")
                    processed_image = image
            
            # Calculate total execution time
            total_time = time.time() - start_time
            
            # Create result context
            result = {
                'tool_name': self.display_name,
                'execution_time': total_time,
                'inference_time': detection_result['execution_time'],
                'detections': detections,
                'detection_count': len(detections),
                'model_name': detection_result['model_name'],
                'selected_classes': detection_result['selected_classes'],
                'detection_region': detection_region,
                'status': 'success'
            }
            
            # Add detection summary
            if detections:
                class_counts = {}
                for det in detections:
                    class_name = det['class_name']
                    class_counts[class_name] = class_counts.get(class_name, 0) + 1
                result['class_counts'] = class_counts
                result['avg_confidence'] = np.mean([det['confidence'] for det in detections])
            else:
                result['class_counts'] = {}
                result['avg_confidence'] = 0.0
            
            logger.debug(f"DetectTool {self.display_name} completed - Found {len(detections)} detections in {total_time:.3f}s")
            
            return processed_image, result
            
        except Exception as e:
            logger.error(f"Error in DetectTool {self.display_name} process: {e}")
            return image, {
                'tool_name': self.display_name,
                'execution_time': time.time() - start_time,
                'detections': [],
                'status': 'error',
                'error': str(e)
            }
    
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Update tool configuration"""
        try:
            # Update tool config
            for key, value in new_config.items():
                if not self.config.set(key, value):
                    logger.warning(f"Invalid config value for {key}: {value}")
                    return False
            
            # Update detection job if it exists
            if self.detect_job:
                detection_config = {
                    'selected_classes': self.config.get('selected_classes'),
                    'confidence_threshold': self.config.get('confidence_threshold'),
                    'nms_threshold': self.config.get('nms_threshold')
                }
                self.detect_job.update_config(detection_config)
            
            logger.info(f"DetectTool {self.display_name} configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating DetectTool {self.display_name} config: {e}")
            return False
    
    def get_last_detections(self) -> List[Dict[str, Any]]:
        """Get detections from last execution"""
        return self.last_detections.copy()
    
    def set_execution_enabled(self, enabled: bool):
        """Enable or disable execution"""
        self.execution_enabled = enabled
        logger.info(f"DetectTool {self.display_name} execution {'enabled' if enabled else 'disabled'}")
    
    def get_info(self) -> Dict[str, Any]:
        """Get tool information"""
        info = {
            'tool_type': 'DetectTool',
            'display_name': self.display_name,
            'tool_id': self.tool_id,
            'execution_enabled': self.execution_enabled,
            'config': self.config.to_dict(),
            'last_detection_count': len(self.last_detections),
            'is_initialized': self.detect_job is not None and self.detect_job.is_initialized
        }
        
        if self.detect_job:
            info.update(self.detect_job.get_info())
        
        return info
    
    def cleanup(self):
        """Cleanup resources"""
        if self.detect_job:
            self.detect_job.cleanup()
            self.detect_job = None
        self.last_detections = []
        logger.info(f"DetectTool {self.display_name} cleaned up")

# Factory function for creating DetectTool from DetectToolManager config
def create_detect_tool_from_manager_config(manager_config: Dict[str, Any], tool_id: Optional[int] = None) -> DetectTool:
    """
    Create DetectTool from DetectToolManager configuration
    
    Args:
        manager_config: Config from DetectToolManager.get_tool_config()
        tool_id: Optional tool ID
        
    Returns:
        DetectTool instance
    """
    # Convert manager config to tool config
    tool_config = {
        'model_name': manager_config.get('model_name', ''),
        'model_path': manager_config.get('model_path', ''),
        'selected_classes': manager_config.get('selected_classes', []),
        'confidence_threshold': manager_config.get('confidence_threshold', 0.5),  # Use value from config or default
        'nms_threshold': manager_config.get('nms_threshold', 0.4),  # Use value from config or default
        'detection_region': manager_config.get('detection_region', None),
        'visualize_results': manager_config.get('visualize_results', True),
        'show_confidence': manager_config.get('show_confidence', True),
        'show_class_names': manager_config.get('show_class_names', True)
    }
    
    tool = DetectTool("Detect Tool", tool_config, tool_id)
    logger.info(f"Created DetectTool from manager config - Model: {tool_config['model_name']}, Classes: {len(tool_config['selected_classes'])}")
    
    return tool
