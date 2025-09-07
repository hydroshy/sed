from picamera2 import Picamera2
picam2 = Picamera2()
print("ColourGains:", picam2.camera_controls['ColourGains'])     # -> (min, max, default)
print("ExposureTime:", picam2.camera_controls['ExposureTime'])   # -> (min, max, default)
print("AnalogueGain:", picam2.camera_controls['AnalogueGain'])   # -> (min, max, default)
print("ExposureValue:", picam2.camera_controls['ExposureValue']) # -> (min, max, default)
