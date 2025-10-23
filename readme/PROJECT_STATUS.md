# Tình Trạng Dự Án (Housekeeping)

Cập nhật nhanh về tình hình modules camera, dọn dẹp file thừa, và các bước tiếp theo. Tài liệu này giúp kiểm soát phạm vi kỹ thuật, rủi ro và việc cần làm.

Ngày cập nhật: 2025-09-05

## Tóm tắt
- ĐÃ LOẠI BỎ cơ chế monkey‑patch (external trigger và camera patches).
- ĐÃ dọn các file patch/placeholder không còn dùng.

## Thành phần đang được sử dụng
- `camera/camera_stream.py`:
  - Lớp CameraStream chính, được dùng ở:
    - `camera/__init__.py:9`
    - `gui/camera_manager.py:3`
    - `gui/camera_manager.py:54`
    - `gui/imports.py:51`
- External trigger: dùng trực tiếp `CameraStream.set_trigger_mode(...)` khi cần (không còn nạp monkey‑patch).

## Thành phần đã xóa hoặc không còn dùng
- ĐÃ XÓA:
  - `camera/apply_trigger_capture_fix.py`
  - `camera/add_trigger_capture.py`
  - `camera/camera_stream_patch.py`
  - `camera_stream_fixed.py` (ở repo root)
  - `camera/camera_stream_fixed.py`
  - `camera/external_trigger_methods.py`
  - `camera/camera_patches.py`

## Việc cần làm (Next actions)
1) Housekeeping
   - Cập nhật hướng dẫn contributor: external trigger dùng trực tiếp `set_trigger_mode(...)`; không còn cơ chế patch động.

2) Hợp nhất patching
   - Đã loại bỏ hoàn toàn patch động. Nếu cần API thân thiện, cân nhắc thêm wrapper `start_external_trigger/stop_external_trigger` (gọi `set_trigger_mode`).

3) Kiểm thử
   - Khởi tạo `CameraStream`, gọi `start_live()` (khi có/stub camera).
   - Bật/tắt external trigger bằng `set_trigger_mode(True/False)` và xác nhận hành vi.
   - Chạy: `python run_tests.py` (hoặc `python -m pytest -q` nếu có pytest).

4) Quan sát vận hành
   - Trên Raspberry Pi: xác nhận biến môi trường và stub PyKMS theo `main.py`.
   - Kiểm tra log `sed_app.log` để theo dõi patch được áp dụng và hành vi camera.

## Lệnh khuyến nghị để tự kiểm tra
- `rg -n --no-ignore-vcs -S CameraStream`
- `python main.py`
- `python run_tests.py`

## Nhật ký quyết định (Decision log)
- 2025-09-05: Loại bỏ monkey‑patch external trigger và toàn bộ `camera/camera_patches.py`.
- 2025-09-05: Dọn dẹp – xóa các file không dùng: `camera/apply_trigger_capture_fix.py`, `camera/add_trigger_capture.py`, `camera/camera_stream_patch.py`, `camera_stream_fixed.py` (root), `camera/camera_stream_fixed.py`, `camera/external_trigger_methods.py`, `camera/camera_patches.py`.

