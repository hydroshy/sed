import os

def get_camera_sources():
    sources = []
    # Kiểm tra các cổng /dev/video* (USB camera)
    for i in range(10):
        dev = f"/dev/video{i}"
        if os.path.exists(dev):
            sources.append(f"USB Camera {i}")
    # CSI camera: thử khởi tạo Picamera2, nếu lỗi do đang bị chiếm dụng thì vẫn cho hiển thị
    try:
        from picamera2 import Picamera2
        try:
            picam = Picamera2()
            picam.close()
            sources.append("Raspberry Pi Camera (CSI)")
        except Exception as e:
            # Nếu lỗi do "Camera __init__ sequence did not complete" hoặc device busy, vẫn cho hiển thị
            if "Camera __init__ sequence did not complete" in str(e) or "Device or resource busy" in str(e):
                sources.append("Raspberry Pi Camera (CSI)")
    except ImportError:
        pass
    return sources
