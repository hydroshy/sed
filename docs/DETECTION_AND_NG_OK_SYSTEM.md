# Detection Tool & NG/OK Execution System

## Tổng Quan Hệ Thống

Hệ thống hiện có 2 phần chính:

### 1. **Detection System** (DetectTool)
- **Vị trí**: `tools/detection/detect_tool.py`
- **Mục đích**: Phát hiện objects trong frame sử dụng YOLO + ONNX inference
- **Đầu vào**: Frame từ camera
- **Đầu ra**: Danh sách detections (bounding boxes, confidence, class_name)

### 2. **Execution Control** (Để cơ chế NG/OK)
- **Vị trí**: `tools/detection/detect_tool.py` - property `execution_enabled`
- **Mục đích**: Bật/tắt việc thực thi detection
- **Hiện tại**: Chỉ bật/tắt detection, không có logic NG/OK

---

## Cách Hoạt Động Detection

### Quy Trình Xử Lý:

```
Frame Input
    ↓
[Chuẩn Bị Detection Region] - Nếu có draw area
    ↓
[Letterbox Resize] - Đưa image về kích thước 640x640
    ↓
[Convert BGR→RGB & Normalize] - Chuẩn bị input cho ONNX
    ↓
[ONNX Inference] - Chạy YOLO model
    ↓
[Decode Outputs] - Parse kết quả từ model
    ↓
[NMS (Non-Maximum Suppression)] - Loại bỏ duplicate detections
    ↓
[Filter by Selected Classes] - Chỉ giữ classes cần detect
    ↓
[Map Back to Original Image] - Chuyển bbox từ 640x640 → original size
    ↓
Detections Output (List of {bbox, confidence, class_id, class_name})
```

### Key Parameters:

```python
class DetectTool:
    imgsz = 640                          # Input size cho YOLO (640x640)
    confidence_threshold = 0.5           # Min confidence để keep detection
    nms_threshold = 0.45                 # IoU threshold cho NMS
    selected_classes = []                # Classes để detect ([] = detect all)
    execution_enabled = True             # Bật/tắt detection
    last_detections = []                 # Kết quả detection mới nhất
```

### Detection Output Format:

```python
detections = [
    {
        'bbox': [x1, y1, x2, y2],        # Pixel coordinates
        'confidence': 0.95,               # 0-1 confidence score
        'class_id': 0,                    # Class index
        'class_name': 'bottle'            # Class name
    },
    ...
]
```

---

## Cách Thêm NG/OK Execution System

### Bước 1: Thêm NG/OK Logic vào DetectTool

Cần thêm các property mới:

```python
class DetectTool(BaseTool):
    def __init__(self, ...):
        self.execution_enabled = True           # Hiện tại
        
        # NEW: NG/OK Parameters
        self.ng_ok_enabled = False              # Enable NG/OK judgment
        self.ng_ok_mode = 'similarity'          # 'similarity' hoặc 'threshold'
        self.ng_ok_reference_detections = []    # Reference detections (từ OK frame)
        self.ng_ok_similarity_threshold = 0.8   # 80% similarity = OK
        self.ng_ok_result = None                # 'OK', 'NG', hoặc None
        self.ng_ok_reason = ''                  # Lý do NG
```

### Bước 2: Thêm Similarity Comparison Function

```python
def _compare_detections(self, current, reference):
    """
    So sánh detection giữa current frame và reference frame
    
    Args:
        current: List of current detections
        reference: List of reference detections
        
    Returns:
        Tuple[bool, float, str]: (is_ok, similarity_score, reason)
    """
    # Logic:
    # 1. Kiểm tra số lượng objects
    # 2. Kiểm tra class giống nhau
    # 3. Kiểm tra bbox overlap (IoU)
    # 4. Tính similarity score
```

### Bước 3: Thêm NG/OK Decision Logic

```python
def process(self, image, context=None):
    # ... Detection logic (existing) ...
    
    # NEW: NG/OK Check
    if self.ng_ok_enabled and self.ng_ok_reference_detections:
        is_ok, similarity, reason = self._compare_detections(
            detections, 
            self.ng_ok_reference_detections
        )
        
        if similarity < self.ng_ok_similarity_threshold:
            self.ng_ok_result = 'NG'
            self.ng_ok_reason = reason
        else:
            self.ng_ok_result = 'OK'
            self.ng_ok_reason = 'Matches reference'
```

---

## Cách Người Dùng Sử Dụng NG/OK

### Workflow:

1. **Chuẩn Bị Reference (OK Frame)**
   ```
   Bấn trigger camera khi frame là OK
   → Lưu detections này làm reference
   → Hiển thị: "Reference Set - Ready for NG/OK Check"
   ```

2. **Kiểm Tra Frames (NG/OK Check)**
   ```
   Trigger frame tiếp theo
   → So sánh với reference
   → Hiển thị kết quả: "OK ✓" hoặc "NG ✗"
   ```

3. **Tùy Chỉnh Độ Nhạy**
   ```
   UI: Slider "NG/OK Similarity Threshold" (0-100%)
   - 100% = Phải giống hệt (Strict)
   - 50% = Chỉ cần ~50% giống (Loose)
   ```

---

## Current Detection Flow in Job

### Trong `job/job_manager.py`:

```python
def run(self, image, context=None):
    # Mỗi tool được chạy tuần tự
    for tool in self.tools:
        image, results = tool.process(image, context)
        
        # results = {
        #     'tool_name': 'Detect Tool',
        #     'detections': [...],
        #     'execution_time': 0.045,
        #     'status': 'success'
        # }
```

### Trong `gui/camera_manager.py`:

```python
def _run_job_processing(self, frame):
    # Chạy job
    processed_frame, results = self.job_manager.run_current_job(frame)
    
    # Trích xuất detection results
    detection_results = results.get('Detect Tool', {})
    detections = detection_results.get('detections', [])
    
    # Store để display
    self.camera_view.display_frame(processed_frame)
```

---

## Đề Xuất Implementation NG/OK

### Phase 1: Core NG/OK Logic (trong DetectTool)
- ✅ Thêm `ng_ok_enabled`, `ng_ok_mode`
- ✅ Thêm `_compare_detections()` method
- ✅ Thêm `set_reference_detections()` method
- ✅ Thêm NG/OK result output

### Phase 2: UI Control (trong MainWindow)
- ❌ Thêm "Set Reference" button (khi trigger)
- ❌ Thêm "NG/OK Status" display
- ❌ Thêm "Similarity Threshold" slider
- ❌ Thêm "NG/OK Enabled" checkbox

### Phase 3: Result Visualization
- ❌ Hiển thị "OK ✓" hoặc "NG ✗" trên frame
- ❌ Log history NG/OK results
- ❌ Export NG/OK report

---

## Key Parameters Cần Biết

### Similarity Metrics:

```python
# Option 1: IoU (Intersection over Union)
# IoU = intersection_area / union_area
# Range: 0-1, higher = more similar

# Option 2: Class Match Score
# Score = (classes_matched / total_classes) * 100%

# Option 3: Combined Score
# score = 0.5 * iou_score + 0.5 * class_match
```

### Threshold Interpretation:

```
similarity_threshold = 0.8 (80%)

- If similarity >= 0.8 → OK ✓
- If similarity < 0.8 → NG ✗
```

---

## Files Cần Modify:

1. **tools/detection/detect_tool.py**
   - Add NG/OK properties
   - Add comparison methods
   - Modify process() to include NG/OK logic

2. **gui/camera_manager.py**
   - Add reference setting logic
   - Display NG/OK result
   - Handle trigger for reference capture

3. **gui/main_window.py**
   - Add UI controls for NG/OK
   - Add visualization of results

4. **job/job_manager.py**
   - Export NG/OK results in job output

---

## Next Steps:

1. **Tôi sẽ implement core NG/OK logic trong DetectTool**
2. **Tôi sẽ thêm UI controls vào MainWindow**
3. **Tôi sẽ integrate result display vào camera_manager**

Bạn có muốn tôi bắt đầu implement không?
