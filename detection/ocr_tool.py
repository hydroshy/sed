
# Dummy OcrTool để tránh lỗi import khi tạm thời ẩn chức năng OCR
class OcrTool:
    def __init__(self, *args, **kwargs):
        pass
    def detect(self, image):
        return []
