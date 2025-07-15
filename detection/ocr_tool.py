from paddleocr import PaddleOCR
import numpy as np

class OcrTool:
    def __init__(self, det_model_dir=None, use_gpu=False):
        # Sử dụng mô hình PP-OCRv5_mobile_det
        self.ocr = PaddleOCR(
            det_model_dir=det_model_dir or None,  # Nếu None sẽ tự động tải về PP-OCRv5_mobile_det
            use_angle_cls=False,
            lang='en',
            use_gpu=use_gpu,
            det=True,
            rec=False,
            type='ocr',
            det_model='PP-OCRv5',
            det_limit_side_len=960
        )

    def detect(self, image: np.ndarray):
        # image: numpy array (BGR hoặc RGB)
        # Trả về danh sách box [(x1, y1, x2, y2, x3, y3, x4, y4), ...]
        result = self.ocr.ocr(image, cls=False)
        boxes = []
        for line in result:
            for box, _ in line:
                boxes.append(box)
        return boxes
