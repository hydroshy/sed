"""testcamera.py

Kiểm tra các định dạng (pixel formats) mà Picamera2 có thể cấu hình.

Script cố gắng theo trình tự: lấy thông tin control nếu có, rồi thử cấu hình
với một danh sách định dạng phổ biến. Script rất phòng ngừa: nếu Picamera2
không cài đặt hoặc phần cứng không cho phép, script sẽ báo và thoát nhẹ.

Sử dụng:
  python testcamera.py

Kết quả: in ra danh sách định dạng 'supported' và 'unsupported' theo thử nghiệm.
"""

import sys
import time
import logging

try:
	from picamera2 import Picamera2
	PICAMERA2_AVAILABLE = True
except Exception:
	PICAMERA2_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("testcamera")


def probe_camera_formats():
	if not PICAMERA2_AVAILABLE:
		logger.error("Picamera2 không khả dụng trong môi trường này. Cài đặt PyPI package 'picamera2' hoặc chạy trên Raspberry Pi OS mới có sẵn.")
		return 1

	picam2 = None
	try:
		picam2 = Picamera2()
	except Exception as e:
		logger.error(f"Không thể khởi tạo Picamera2(): {e}")
		return 2

	logger.info("Picamera2 khởi tạo thành công. Kiểm tra camera_controls (nếu có)...")
	try:
		controls = getattr(picam2, 'camera_controls', None)
		if controls:
			logger.info("camera_controls keys: %s", sorted(list(controls.keys())))
		else:
			logger.info("Không tìm thấy attribute 'camera_controls' trên đối tượng Picamera2.")
	except Exception as e:
		logger.info(f"Đọc camera_controls lỗi: {e}")

	# Danh sách các pixel formats thường gặp — sửa/sắp thêm khi cần
	candidate_formats = [
		"RGB888",
		"BGR888",
		"XRGB8888",
		"YUV420",
		"NV12",
		"YUV420_8",
		"YUV422",
		"GRAY8",
		"GRAY16_LE",
	]

	supported = []
	unsupported = []

	logger.info("Thử cấu hình camera với các định dạng mẫu (mỗi lần sẽ configure/khởi động nhanh)...")

	for fmt in candidate_formats:
		logger.info(f"Kiểm tra format: {fmt} ...")
		ok = False
		try:
			# Một số API Picamera2 cung cấp helper create_preview_configuration/create_video_configuration
			cfg = None
			try:
				# Tùy phiên bản, helper có thể nhận kwargs hoặc dict; thử cả hai
				cfg = picam2.create_preview_configuration(main={"format": fmt, "size": (640, 480)})
			except Exception:
				try:
					cfg = picam2.create_preview_configuration(format=fmt, size=(640, 480))
				except Exception:
					cfg = None

			if cfg is not None:
				# Thử configure/start/stop nhanh để kiểm tra
				try:
					picam2.configure(cfg)
					picam2.start()
					# nhẹ nhàng chờ vài frame
					time.sleep(0.2)
					picam2.stop()
					ok = True
				except Exception as e:
					logger.info(f"configure/start failed for {fmt}: {e}")
					ok = False
			else:
				# Fallback: thử trực tiếp gọi configure với dict (phiên bản cũ/mới khác nhau)
				try:
					fake_cfg = {"main": {"format": fmt, "size": (640, 480)}}
					picam2.configure(fake_cfg)
					picam2.start()
					time.sleep(0.2)
					picam2.stop()
					ok = True
				except Exception as e:
					logger.info(f"Fallback configure failed for {fmt}: {e}")
					ok = False
		except Exception as e:
			logger.info(f"Lỗi kiểm tra {fmt}: {e}")
			ok = False

		if ok:
			supported.append(fmt)
			logger.info(f"=> SUPPORTED: {fmt}")
		else:
			unsupported.append(fmt)
			logger.info(f"=> unsupported: {fmt}")

	logger.info("\nKết quả kiểm tra formats:")
	logger.info("Supported: %s", supported)
	logger.info("Unsupported: %s", unsupported)

	try:
		if picam2 is not None:
			# đảm bảo dọn dẹp
			try:
				picam2.close()
			except Exception:
				pass
	except Exception:
		pass

	return 0


if __name__ == '__main__':
	sys.exit(probe_camera_formats())
