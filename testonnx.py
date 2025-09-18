import cv2, numpy as np, onnxruntime as ort
import matplotlib.pyplot as plt
from pathlib import Path

ONNX = ".\yolov11\sed.onnx"
IMGSZ = 640           # phải khớp với imgsz khi export nếu dynamic=False (thường 320/480/512/640)
NAMES = ["pilsner333","saxizero","warriorgrape"]       # sửa theo lớp của bạn, hoặc load từ file JSON mapping

IMG = r".\image\saxizero\saxizero_1.jpg"

def letterbox(bgr, size=640, color=(114,114,114), stride=32):
    """Resize + pad theo YOLO, trả về ảnh đã pad, tỉ lệ r, offset (left,top)."""
    h, w = bgr.shape[:2]
    r = min(size / h, size / w)
    nh, nw = int(round(h * r)), int(round(w * r))
    img = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
    top  = (size - nh) // 2
    left = (size - nw) // 2
    bottom = size - nh - top
    right  = size - nw - left
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return img, r, (left, top)

def nms_numpy(boxes, scores, iou_thres=0.45):
    x1, y1, x2, y2 = [boxes[:, i] for i in range(4)]
    areas = (x2 - x1).clip(min=0) * (y2 - y1).clip(min=0)
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]; keep.append(i)
        if order.size == 1: break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = (xx2 - xx1).clip(min=0); h = (yy2 - yy1).clip(min=0)
        inter = w * h
        union = areas[i] + areas[order[1:]] - inter + 1e-6
        iou = inter / union
        order = order[1:][iou <= iou_thres]
    return np.array(keep, dtype=np.int64)

def yolo_onnx_to_dets(out, iou_thres=0.45):
    """
    Chuẩn hóa output về Nx6 = [x1,y1,x2,y2,score,cls].
    Hỗ trợ:
      - 1 output: (N,6) hoặc (N,7=batch_id+6) hoặc (1,N,6)
      - 4 output: [num_dets, boxes, scores, classes]
      - RAW (chưa NMS): (N, 5+C) -> decode + NMS tối giản
    """
    # Gói ra numpy
    if isinstance(out, (list, tuple)):
        # kiểu 4 output: num, boxes, scores, classes
        if len(out) == 4:
            num = int(np.array(out[0]).reshape(-1)[0])
            boxes   = np.array(out[1])[0, :num]  # [num,4] (x1,y1,x2,y2)
            scores  = np.array(out[2])[0, :num]  # [num]
            classes = np.array(out[3])[0, :num]  # [num]
            return np.concatenate([boxes, scores[:,None], classes[:,None]], axis=1).astype(np.float32)
        arr = np.array(out[0])
    else:
        arr = np.array(out)

    arr = np.squeeze(arr)                  # (N,*) hoặc (*,)
    if arr.ndim == 1: arr = arr[None, :]

    # đã NMS: Nx6 hoặc Nx7 (batch_id + 6)
    if arr.shape[-1] in (6, 7):
        if arr.shape[-1] == 7:             # [batch,x1,y1,x2,y2,score,cls]
            arr = arr[:, 1:]
        return arr.astype(np.float32)

    # RAW: [x,y,w,h,obj, p0..pC-1]  (xywh-center theo pixel của ảnh đã letterbox)
    if arr.shape[-1] > 6:
        xywh = arr[:, :4].astype(np.float32)
        obj  = arr[:, 4].astype(np.float32)
        cls_probs = arr[:, 5:].astype(np.float32)
        cls_id = cls_probs.argmax(1).astype(np.float32)
        cls_conf = cls_probs.max(1)
        scores = obj * cls_conf

        x, y, w, h = xywh.T
        x1 = x - w/2; y1 = y - h/2
        x2 = x + w/2; y2 = y + h/2
        boxes = np.stack([x1,y1,x2,y2], axis=1)

        keep = nms_numpy(boxes, scores, iou_thres=iou_thres)
        return np.concatenate([boxes[keep],
                               scores[keep, None],
                               cls_id[keep, None]], axis=1).astype(np.float32)

    raise ValueError(f"Không nhận dạng được output shape: {arr.shape}. Hãy export ONNX với nms=True cho đơn giản.")

providers = ["CPUExecutionProvider"]  # có GPU NVIDIA: ["CUDAExecutionProvider","CPUExecutionProvider"]
sess = ort.InferenceSession(ONNX, providers=providers)
inp_name = sess.get_inputs()[0].name

img_bgr = cv2.imread(IMG)
if img_bgr is None:
    raise FileNotFoundError(f"Không đọc được ảnh: {Path(IMG).resolve()}")

im, r, (lx, ly) = letterbox(img_bgr, IMGSZ)
x = cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
x = x.transpose(2,0,1)[None]  # [1,3,H,W]

out = sess.run(None, {inp_name: x})
print("Output shapes:", [np.array(o).shape for o in (out if isinstance(out,(list,tuple)) else [out])])

dets = yolo_onnx_to_dets(out)  # -> Nx6

conf_thres = 0.25
vis = img_bgr.copy()
for x1,y1,x2,y2,score,cls_id in dets:
    if score < conf_thres: 
        continue
    # map bbox từ khung letterbox về ảnh gốc
    x1,y1,x2,y2 = (np.array([x1,y1,x2,y2]) - [lx,ly,lx,ly]) / r
    p1, p2 = (int(x1), int(y1)), (int(x2), int(y2))
    cv2.rectangle(vis, p1, p2, (0,255,0), 2)
    name = NAMES[int(cls_id)] if int(cls_id) < len(NAMES) else str(int(cls_id))
    cv2.putText(vis, f"{name} {score:.2f}", (p1[0], max(p1[1]-5, 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
    

# Access the results
for result in results:
    xywh = result.boxes.xywh  # center-x, center-y, width, height
    xywhn = result.boxes.xywhn  # normalized
    xyxy = result.boxes.xyxy  # top-left-x, top-left-y, bottom-right-x, bottom-right-y
    xyxyn = result.boxes.xyxyn  # normalized
    names = [result.names[cls.item()] for cls in result.boxes.cls.int()]  # class name of each box
    confs = result.boxes.conf  # confidence score of each box

out_path = "out_detect.jpg"
cv2.imwrite(out_path, vis)
print("Saved:", Path(out_path).resolve())

plt.figure(figsize=(8,8))
plt.imshow(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
plt.title("Detections")
plt.axis("off")
plt.show()