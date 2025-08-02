
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
            logger.error(f"EasyOCR detection failed: {str(e)}")
            return []
            
    def _detect_with_tesseract(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Sử dụng Tesseract để nhận dạng text"""
        try:
            import pytesseract
            
            # Lấy thông tin chi tiết từ tesseract
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            detections = []
            min_confidence = self.config.get("min_confidence") * 100  # Tesseract sử dụng 0-100
            
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                confidence = data['conf'][i]
                
                if text and confidence >= min_confidence:
                    detection = {
                        "text": text,
                        "confidence": confidence / 100.0,  # Chuyển về 0-1
                        "bbox": {
                            "x1": data['left'][i],
                            "y1": data['top'][i],
                            "x2": data['left'][i] + data['width'][i],
                            "y2": data['top'][i] + data['height'][i]
                        }
                    }
                    detections.append(detection)
                    
            return detections
            
        except Exception as e:
            logger.error(f"Tesseract detection failed: {str(e)}")
            return []
    
    def detect(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Phương thức detect để tương thích với code cũ"""
        try:
            processed_image = self._preprocess_image(image)
            
            if self._ocr_engine is None:
                return []
                
            if hasattr(self._ocr_engine, 'readtext'):  # EasyOCR
                return self._detect_with_easyocr(processed_image)
            else:  # Tesseract
                return self._detect_with_tesseract(processed_image)
                
        except Exception as e:
            logger.error(f"OCR detection failed: {str(e)}")
            return []
        
    def process(self, image: np.ndarray, context: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Xử lý OCR trên ảnh
        
        Args:
            image: Ảnh đầu vào
            context: Ngữ cảnh từ các tool trước
            
        Returns:
            Tuple chứa ảnh đã xử lý và kết quả
        """
        try:
            # Thực hiện OCR
            detections = self.detect(image)
            
            # Tạo ảnh output với bounding boxes
            output_image = image.copy()
            output_format = self.config.get("output_format")
            
            if output_format in ["boxes", "both"] and detections:
                for detection in detections:
                    bbox = detection["bbox"]
                    text = detection["text"]
                    confidence = detection["confidence"]
                    
                    # Vẽ bounding box
                    cv2.rectangle(output_image, 
                                (bbox["x1"], bbox["y1"]), 
                                (bbox["x2"], bbox["y2"]), 
                                (0, 255, 0), 2)
                    
                    # Vẽ text và confidence
                    label = f"{text} ({confidence:.2f})"
                    cv2.putText(output_image, label, 
                              (bbox["x1"], bbox["y1"] - 10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, 
                              (0, 255, 0), 1)
            
            # Tổng hợp kết quả
            all_text = " ".join([d["text"] for d in detections])
            
            result = {
                "detections": detections,
                "text_count": len(detections),
                "all_text": all_text,
                "average_confidence": np.mean([d["confidence"] for d in detections]) if detections else 0.0,
                "config_used": self.config.to_dict()
            }
            
            return output_image, result
            
        except Exception as e:
            error_msg = f"Lỗi trong OcrTool: {str(e)}"
            return image, {"error": error_msg}
