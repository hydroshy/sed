from picamera2 import Picamera2
import cv2

picam2 = Picamera2()
picam2.start()
frame = picam2.capture_array()
cv2.imshow("Picamera2 Test", frame)
cv2.waitKey(0)
cv2.destroyAllWindows()
picam2.close()
