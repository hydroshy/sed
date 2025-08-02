# Detection Tools

Thư mục này chứa các công cụ phát hiện và xử lý hình ảnh cho dự án SED.

## Cấu trúc

- `detect_tool.py`: Công cụ phát hiện đối tượng sử dụng YOLO
- `model_manager.py`: Quản lý các mô hình YOLO ONNX
- `yolo_inference.py`: Engine suy luận YOLO ONNX
- `visualization.py`: Tiện ích hiển thị kết quả phát hiện
- `ocr_tool.py`: Công cụ OCR để nhận dạng văn bản
- `edge_detection.py`: Công cụ phát hiện biên cạnh

## Sử dụng

```python
from tools.detection import DetectTool, ModelManager, create_yolo_inference

# Khởi tạo công cụ phát hiện
detect_tool = DetectTool("My Detector")

# Xử lý hình ảnh
result_image, results = detect_tool.process(image)
```

## Các công cụ có sẵn

1. **DetectTool**: Phát hiện đối tượng bằng YOLO
2. **OcrTool**: Nhận dạng văn bản từ hình ảnh
3. **EdgeDetectionTool**: Phát hiện biên cạnh bằng Canny Edge Detection
