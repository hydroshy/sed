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
        logger.info(f"🔵 SaveImageTool.process ENTRY")
        logger.info(f"SaveImageTool.process called with image shape: {image.shape}")
        logger.info(f"SaveImageTool config - directory: '{self.directory}', auto_save: {self.auto_save}")
        logger.info(f"SaveImageTool config - structure_file: '{self.structure_file}', format: '{self.image_format}'")
        logger.info(f"SaveImageTool.process - context provided: {context is not None}")
        if context:
            logger.info(f"SaveImageTool.process - context keys: {list(context.keys())}")
            logger.info(f"SaveImageTool.process - force_save: {context.get('force_save')}")
            logger.info(f"SaveImageTool.process - pixel_format: {context.get('pixel_format')}")
        
        try:
            result = {
                "tool_name": self.display_name,
                "saved": False,
                "filepath": None,
                "error": None
            }

            # Respect auto_save flag unless explicitly forced via context
            if not self.auto_save and not (context and context.get('force_save')):
                logger.info(f"⏭️  SaveImageTool: auto_save={self.auto_save}, force_save={context.get('force_save') if context else 'N/A'} - SKIPPING SAVE")
                return image, result
            
            logger.info(f"✅ SaveImageTool: Proceeding with save (auto_save={self.auto_save} OR force_save={context.get('force_save') if context else False})")

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
                logger.info(f"✅ SaveImageTool: Image saved successfully to {filepath}")
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
            logger.info(f"SaveImageTool.save_image_array: ENTRY - Input image shape: {image_array.shape}")
            logger.info(f"SaveImageTool.save_image_array: Image dtype: {image_array.dtype}")
            logger.info(f"SaveImageTool.save_image_array: Image min/max values: {image_array.min()}/{image_array.max()}")
            logger.info(f"SaveImageTool.save_image_array: Context provided: {context is not None}")
            if context:
                logger.info(f"SaveImageTool.save_image_array: Context keys: {list(context.keys())}")
                logger.info(f"SaveImageTool.save_image_array: context['pixel_format'] = {context.get('pixel_format')}")
            
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
                    logger.info(f"SaveImageTool: Full context: {context}")
                    # Common keys that may carry format information
                    input_format = (
                        context.get('pixel_format')
                        or context.get('color_order')
                        or context.get('color_format')
                        or context.get('input_format')
                    )
                    logger.info(f"SaveImageTool: pixel_format={context.get('pixel_format')}, color_order={context.get('color_order')}, color_format={context.get('color_format')}, input_format={context.get('input_format')}")
                    logger.info(f"SaveImageTool: Extracted input_format before type check: {input_format} (type: {type(input_format)})")
                if isinstance(input_format, str):
                    input_format = input_format.upper()
            except Exception as e:
                logger.error(f"SaveImageTool: Error extracting format from context: {e}", exc_info=True)
                input_format = None
            
            logger.info(f"SaveImageTool: Final input_format: {input_format} (type: {type(input_format)})")

            # Conversion rules:
            # - Camera stream sends RGB format by default
            # - cv2.imwrite() saves image bytes AS-IS (no automatic color conversion)
            # - For RGB image to save with correct colors in file: Keep as RGB, don't convert!
            # - For BGR image: Keep as-is
            # NOTE: Some image viewers assume BGR when opening JPG/PNG, but that's viewer behavior
            # The file format doesn't carry color space info, so we need to ensure bytes are in correct order
            if len(save_image.shape) == 3 and save_image.shape[2] == 3:
                logger.info(f"SaveImageTool: Processing 3-channel image (shape={save_image.shape}), input_format={input_format} (type: {type(input_format).__name__})")
                
                # Default to RGB if format not specified (camera streams default to RGB)
                if input_format is None:
                    input_format = "RGB"
                    logger.info("SaveImageTool: ℹ️  No input_format specified, defaulting to RGB")
                
                logger.info(f"SaveImageTool: Checking if 'RGB' in {repr(input_format)}")
                if input_format and 'RGB' in str(input_format).upper():
                    logger.info(f"✅ SaveImageTool: Input format RGB detected! Saving as RGB (NO conversion for imwrite)")
                    logger.info(f"   Image is RGB format - will be saved with RGB channel order")
                    logger.info(f"   Image before save - min={save_image.min()}, max={save_image.max()}, dtype={save_image.dtype}")
                    # IMPORTANT: Keep image in RGB format! imwrite will save these exact bytes
                    # Note: Some viewers assume BGR, but the file contains actual RGB data
                    # When opened in OpenCV it will be correct
                else:
                    logger.warning(f"⚠️  SaveImageTool: Input format NOT RGB (got {repr(input_format)}), saving as-is")
            elif len(save_image.shape) == 3 and save_image.shape[2] == 4:
                # 4-channel images: try to respect context; otherwise assume RGBA (from RGB pipeline)
                if input_format and (input_format in ('RGBA', 'XRGB8888') or input_format.startswith('RGBA')):
                    logger.info("SaveImageTool: Input format RGBA detected, converting RGBA->BGR (dropping alpha)")
                    save_image = cv2.cvtColor(save_image, cv2.COLOR_RGBA2BGR)
                else:
                    logger.info("SaveImageTool: Assuming BGRA (from BGR pipeline); no conversion needed")
            else:
                logger.info(f"SaveImageTool: Processing image with shape={save_image.shape}")

            
            logger.info(f"SaveImageTool: Final image shape for saving: {save_image.shape}")
            logger.info(f"SaveImageTool: Final image dtype: {save_image.dtype}")
            logger.info(f"SaveImageTool: Final image - First pixel value: {save_image[0, 0]}")  # DEBUG: check actual RGB/BGR order
            
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
