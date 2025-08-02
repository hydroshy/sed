import cv2
import numpy as np
from typing import Dict, Any, Tuple, Optional, List
from tools.base_tool import BaseTool, ToolConfig
import logging

logger = logging.getLogger(__name__)

class OcrTool(BaseTool):
    """Công cụ OCR để nhận dạng văn bản từ ảnh"""
    
    def __init__(self, name: str = "OCR", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)
        self._ocr_engine = None
        self._initialize_ocr()
        
    def _initialize_ocr(self):
        """Khởi tạo OCR engine"""
        try:
            # Thử import easyocr trước
            import easyocr
            self._ocr_engine = easyocr.Reader(['en', 'vi'])  # Hỗ trợ tiếng Anh và tiếng Việt
            logger.info("EasyOCR engine initialized successfully")
        except ImportError:
            try:
                # Fallback sang pytesseract
                import pytesseract
                self._ocr_engine = "tesseract"
                logger.info("Tesseract OCR engine initialized successfully")
            except ImportError:
                logger.warning("No OCR engine available. OCR functionality will be limited.")
                self._ocr_engine = None
        
    def setup_config(self) -> None:
        """Thiết lập cấu hình mặc định cho OCR"""
        self.config.set_default("min_confidence", 0.5)
        self.config.set_default("preprocessing", True)
        self.config.set_default("language", "en")
        self.config.set_default("output_format", "text")  # "text", "boxes", "both"
        self.config.set_default("scale_factor", 2.0)
        
        # Validators
        self.config.set_validator("min_confidence", lambda x: 0.0 <= x <= 1.0)
        self.config.set_validator("scale_factor", lambda x: 0.5 <= x <= 5.0)
        self.config.set_validator("output_format", lambda x: x in ["text", "boxes", "both"])
        
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Tiền xử lý ảnh để cải thiện độ chính xác OCR"""
        if not self.config.get("preprocessing"):
            return image
            
        # Chuyển sang grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
            
        # Scale up ảnh để cải thiện OCR
        scale_factor = self.config.get("scale_factor")
        if scale_factor != 1.0:
            height, width = gray.shape
            new_height = int(height * scale_factor)
            new_width = int(width * scale_factor)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Áp dụng threshold để làm rõ text
        # Sử dụng Otsu's thresholding để tự động tìm threshold tối ưu
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Noise reduction
        kernel = np.ones((1, 1), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return binary
        
    def _detect_with_easyocr(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Sử dụng EasyOCR để nhận dạng text"""
        try:
            results = self._ocr_engine.readtext(image)
            detections = []
            
            min_confidence = self.config.get("min_confidence")
            
            for bbox, text, confidence in results:
                if confidence >= min_confidence:
                    # Chuyển đổi bbox về format chuẩn
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                    
                    detection = {
                        "text": text,
                        "confidence": confidence,
                        "bbox": {
                            "x1": int(min(x_coords)),
                            "y1": int(min(y_coords)),
                            "x2": int(max(x_coords)),
                            "y2": int(max(y_coords))
                        },
                        "raw_bbox": bbox
                    }
                    detections.append(detection)
                    
            return detections
            
        except Exception as e:
            logger.error(f"Error in EasyOCR detection: {e}")
            return []
    
    def _detect_with_tesseract(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Sử dụng Tesseract OCR để nhận dạng text"""
        try:
            import pytesseract
            
            # Thiết lập config cho Tesseract
            config = f'--psm 6 --oem 3'
            if self.config.get("language") == "vi":
                config += " -l vie"
                
            # Detect text từ ảnh
            data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
            
            # Chuyển đổi kết quả về định dạng tiêu chuẩn
            detections = []
            min_confidence = self.config.get("min_confidence") * 100  # Tesseract uses 0-100
            
            for i in range(len(data['text'])):
                # Skip empty text
                if not data['text'][i].strip():
                    continue
                    
                # Get confidence and check threshold
                confidence = int(data['conf'][i]) / 100.0  # Convert to 0-1 range
                if confidence < self.config.get("min_confidence"):
                    continue
                
                # Get bounding box
                x = data['left'][i]
                y = data['top'][i]
                w = data['width'][i]
                h = data['height'][i]
                
                detection = {
                    "text": data['text'][i],
                    "confidence": confidence,
                    "bbox": {
                        "x1": x,
                        "y1": y,
                        "x2": x + w,
                        "y2": y + h
                    }
                }
                detections.append(detection)
                
            return detections
            
        except Exception as e:
            logger.error(f"Error in Tesseract detection: {e}")
            return []
        
    def process(self, image: np.ndarray, context: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Thực hiện OCR trên ảnh
        
        Args:
            image: Ảnh đầu vào
            context: Ngữ cảnh từ các tool trước
            
        Returns:
            Tuple chứa ảnh đã xử lý và kết quả OCR
        """
        try:
            if self._ocr_engine is None:
                return image, {"error": "No OCR engine available"}
                
            # Tiền xử lý ảnh
            processed_image = self._preprocess_image(image)
            
            # Detect text
            if isinstance(self._ocr_engine, str) and self._ocr_engine == "tesseract":
                detections = self._detect_with_tesseract(processed_image)
            else:
                detections = self._detect_with_easyocr(processed_image)
                
            # Visualize results
            result_image = image.copy()
            for detection in detections:
                bbox = detection["bbox"]
                text = detection["text"]
                conf = detection["confidence"]
                
                # Draw bounding box
                cv2.rectangle(result_image, 
                            (bbox["x1"], bbox["y1"]), 
                            (bbox["x2"], bbox["y2"]),
                            (0, 255, 0), 2)
                
                # Draw text and confidence
                label = f"{text} ({conf:.2f})"
                cv2.putText(result_image, label, 
                          (bbox["x1"], bbox["y1"] - 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
            # Extract text
            extracted_text = " ".join([d["text"] for d in detections])
            
            result = {
                "text": extracted_text,
                "detections": detections,
                "detection_count": len(detections)
            }
            
            return result_image, result
            
        except Exception as e:
            logger.error(f"Error in OCR Tool: {e}")
            return image, {"error": str(e)}
