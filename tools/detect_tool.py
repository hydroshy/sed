from .base_tool import BaseTool
from .detection.detect_tool import DetectTool as AdvancedDetectTool
from .detection.model_manager import ModelManager

class DetectTool(BaseTool):
    def __init__(self, name="DetectTool", config=None):
        super().__init__(name, config)
        self.advanced_tool = AdvancedDetectTool(name, config)
        
    def run(self, frame):
        # Sử dụng advanced detect tool
        result_image, results = self.advanced_tool.process(frame)
        return {"detections": results.get('detections', [])}
