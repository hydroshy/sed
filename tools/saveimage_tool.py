# tools/saveimage_tool.py
import os
import cv2
import numpy as np
import logging
from typing import Dict, Any, Optional, Tuple, Union
from tools.base_tool import BaseTool, ToolConfig

logger = logging.getLogger(__name__)


class SaveImageTool(BaseTool):
    """
    Tool for saving images.
    Given a directory, a structure file prefix, and a chosen image format,
    this class provides functionality to save an image with a filename that includes a running number.
    """

    def __init__(self, name: str = "Save Image", config: Optional[Union[Dict[str, Any], ToolConfig]] = None, tool_id: Optional[int] = None):
        """
        Initialize SaveImage tool with proper BaseTool integration

        Args:
            name: Display name of the tool
            config: Tool configuration (dict or ToolConfig)
            tool_id: Tool ID in the job
        """
        logger.info(f"SaveImageTool.__init__ called with name='{name}', config={config}, tool_id={tool_id}")

        # Set name attributes FIRST to ensure they always exist
        self.name = name or "Save Image"
        self.display_name = name or "Save Image"

        try:
            super().__init__(name, config, tool_id)
            logger.info(f"SaveImageTool: super().__init__ completed")
        except Exception as e:
            logger.error(f"SaveImageTool: super().__init__ failed: {e}")
            # Even if super().__init__ fails, ensure we have basic attributes
            if not hasattr(self, 'config'):
                from tools.base_tool import ToolConfig
                self.config = ToolConfig(config if isinstance(config, dict) else {})
            if not hasattr(self, 'tool_id'):
                self.tool_id = tool_id
            logger.warning(f"SaveImageTool: Continuing with fallback initialization")

        # Ensure name and display_name are properly set (redundant but safe)
        if not hasattr(self, 'name') or not self.name:
            self.name = name or "Save Image"
        if not hasattr(self, 'display_name') or not self.display_name:
            self.display_name = name or "Save Image"

        logger.info(f"SaveImageTool: name='{self.name}', display_name='{self.display_name}'")

        # Set default configuration values
        self.config.set_default("directory", "")
        self.config.set_default("structure_file", "")
        self.config.set_default("image_format", "JPG")
        self.config.set_default("auto_save", False)

        # Initialize properties from config
        self.directory = self.config.get("directory", "")
        self.structure_file = self.config.get("structure_file", "").strip()
        self.image_format = self.config.get("image_format", "JPG").upper()
        self.auto_save = self.config.get("auto_save", False)

        # Debug: Verify all attributes are set
        logger.info(f"SaveImageTool initialization complete:")
        logger.info(f"  - name: {getattr(self, 'name', 'MISSING')}")
        logger.info(f"  - display_name: {getattr(self, 'display_name', 'MISSING')}")
        logger.info(f"  - tool_id: {getattr(self, 'tool_id', 'MISSING')}")
        logger.info(f"  - directory: {self.directory}")
        logger.info(f"  - structure_file: {self.structure_file}")
        logger.info(f"  - image_format: {self.image_format}")

    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Update tool configuration"""
        result = super().update_config(new_config)
        if result:
            self.directory = self.config.get("directory", "")
            self.structure_file = self.config.get("structure_file", "").strip()
            self.image_format = self.config.get("image_format", "JPG").upper()
            self.auto_save = self.config.get("auto_save", False)
        return result

    def get_next_filename(self):
        """Generate the next filename with incremental numbering"""
        if not self.directory:
            raise ValueError("Directory not set")
        if not os.path.isdir(self.directory):
            raise ValueError(f"Directory does not exist: {self.directory}")

        files = os.listdir(self.directory)
        prefix = self.structure_file
        nums = []

        for f in files:
            base, _ = os.path.splitext(f)
            if prefix:
                if base.startswith(prefix + "_"):
                    num_part = base[len(prefix)+1:]
                    if num_part.isdigit():
                        nums.append(int(num_part))
            else:
                if base.isdigit():
                    nums.append(int(base))

        next_num = max(nums) + 1 if nums else 1
        if prefix:
            filename = f"{prefix}_{next_num}.{self.image_format.lower()}"
        else:
            filename = f"{next_num}.{self.image_format.lower()}"
        return os.path.join(self.directory, filename)

    def process(self, image: np.ndarray, context: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Process method required by BaseTool - saves the image if auto_save is enabled

        Args:
            image: Input image (numpy array)
            context: Context from previous tools

        Returns:
            Tuple containing (processed image, results)
        """
        logger.info(f"SaveImageTool.process called with image shape: {image.shape}")
        logger.info(f"SaveImageTool config - directory: '{self.directory}', auto_save: {self.auto_save}")
        logger.info(f"SaveImageTool config - structure_file: '{self.structure_file}', format: '{self.image_format}'")
        
        try:
            result = {
                "tool_name": self.display_name,
                "saved": False,
                "filepath": None,
                "error": None
            }

            # Respect auto_save flag unless explicitly forced via context
            if not self.auto_save and not (context and context.get('force_save')):
                logger.info("SaveImageTool: auto_save is disabled; skipping save for this frame")
                return image, result

            # Check if we have a valid directory
            if not self.directory:
                error_msg = "No directory specified for saving images"
                logger.warning(f"SaveImageTool: {error_msg}")
                result["error"] = error_msg
                return image, result
                
            # Create directory if it doesn't exist
            if not os.path.exists(self.directory):
                try:
                    os.makedirs(self.directory, exist_ok=True)
                    logger.info(f"SaveImageTool: Created directory {self.directory}")
                except Exception as e:
                    error_msg = f"Failed to create directory {self.directory}: {str(e)}"
                    logger.error(f"SaveImageTool: {error_msg}")
                    result["error"] = error_msg
                    return image, result
            
            logger.info(f"SaveImageTool: Attempting to save image...")
            # Pass context so save routine can honor pixel format / color order
            filepath = self.save_image_array(image, context=context)
            if filepath:
                result["saved"] = True
                result["filepath"] = filepath
                logger.info(f"SaveImageTool: Image saved successfully to {filepath}")
            else:
                error_msg = "Failed to save image - save_image_array returned None"
                result["error"] = error_msg
                logger.error(f"SaveImageTool: {error_msg}")

            return image, result

        except Exception as e:
            error_msg = f"SaveImageTool error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return image, {
                "tool_name": self.display_name,
                "saved": False,
                "filepath": None,
                "error": error_msg
            }

    def save_image_array(self, image_array: np.ndarray, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Save numpy array image to file

        Args:
            image_array: Image as numpy array

        Returns:
            File path if saved successfully, None otherwise
        """
        try:
            logger.info(f"SaveImageTool.save_image_array: Input image shape: {image_array.shape}")
            logger.info(f"SaveImageTool.save_image_array: Image dtype: {image_array.dtype}")
            logger.info(f"SaveImageTool.save_image_array: Image min/max values: {image_array.min()}/{image_array.max()}")
            
            # Validate image array
            if image_array is None or image_array.size == 0:
                logger.error("SaveImageTool: Invalid image array (None or empty)")
                return None
            
            # Ensure image is in proper format for OpenCV
            if image_array.dtype != np.uint8:
                logger.info(f"SaveImageTool: Converting image from {image_array.dtype} to uint8")
                # Normalize to 0-255 range if needed
                if image_array.max() <= 1.0:
                    image_array = (image_array * 255).astype(np.uint8)
                else:
                    image_array = image_array.astype(np.uint8)
            
            filepath = self.get_next_filename()
            logger.info(f"SaveImageTool: Generated filepath: {filepath}")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Handle different image formats and color channels
            save_image = image_array.copy()

            # Decide channel order based on context if available
            input_format = None
            try:
                if context:
                    # Common keys that may carry format information
                    input_format = (
                        context.get('pixel_format')
                        or context.get('color_order')
                        or context.get('color_format')
                        or context.get('input_format')
                    )
                if isinstance(input_format, str):
                    input_format = input_format.upper()
            except Exception:
                input_format = None

            # Conversion rules:
            # - OpenCV's imwrite expects BGR order for 3-channel images.
            # - If input is RGB (e.g., 'RGB888'), convert RGB->BGR.
            # - If input is BGR (e.g., 'BGR888'), keep as-is.
            # - If unknown (no context), assume BGR to avoid double-swapping colors from OpenCV pipelines.
            if len(save_image.shape) == 3 and save_image.shape[2] == 3:
                if input_format and input_format.startswith('RGB'):
                    logger.info("SaveImageTool: Input format RGB detected, converting RGB->BGR for saving")
                    save_image = cv2.cvtColor(save_image, cv2.COLOR_RGB2BGR)
                else:
                    # Either explicitly BGR or unknown. Default to no conversion.
                    if input_format:
                        logger.info(f"SaveImageTool: Input format {input_format} treated as BGR/no-swap for saving")
                    else:
                        logger.info("SaveImageTool: No input format provided; assuming BGR (no color swap)")
            elif len(save_image.shape) == 3 and save_image.shape[2] == 4:
                # 4-channel images: try to respect context; otherwise assume BGRA
                if input_format and (input_format in ('RGBA', 'XRGB8888') or input_format.startswith('RGBA')):
                    logger.info("SaveImageTool: Input format RGBA detected, converting RGBA->BGRA for saving")
                    save_image = cv2.cvtColor(save_image, cv2.COLOR_RGBA2BGRA)
                else:
                    logger.info("SaveImageTool: Assuming BGRA or unknown 4-channel; no swap needed for saving")
            
            logger.info(f"SaveImageTool: Final image shape for saving: {save_image.shape}")
            logger.info(f"SaveImageTool: Final image dtype: {save_image.dtype}")
            
            # Set quality parameters for different formats
            save_params = []
            if self.image_format.upper() in ['JPG', 'JPEG']:
                save_params = [cv2.IMWRITE_JPEG_QUALITY, 95]
            elif self.image_format.upper() == 'PNG':
                save_params = [cv2.IMWRITE_PNG_COMPRESSION, 6]
            
            logger.info(f"SaveImageTool: Attempting to save with cv2.imwrite()...")
            success = cv2.imwrite(filepath, save_image, save_params)
            
            if success:
                # Verify the file was actually created
                if os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    logger.info(f"SaveImageTool: Image saved successfully to {filepath} (size: {file_size} bytes)")
                    return filepath
                else:
                    logger.error(f"SaveImageTool: cv2.imwrite returned True but file doesn't exist: {filepath}")
                    return None
            else:
                logger.error(f"SaveImageTool: cv2.imwrite returned False for {filepath}")
                return None

        except Exception as e:
            logger.error(f"SaveImageTool: Error saving image array: {e}", exc_info=True)
            return None

    def save_image(self, image_source):
        """
        Legacy method - saves using image_source.save() method
        Returns the file path if saved successfully, else None.
        The image_source is expected to have a .save(filepath, format) method.
        """
        try:
            filepath = self.get_next_filename()
            success = image_source.save(filepath, self.image_format)
            return filepath if success else None
        except Exception as e:
            logger.error(f"SaveImageTool: Error in legacy save_image: {e}")
            return None

# End of saveimage_tool.py
