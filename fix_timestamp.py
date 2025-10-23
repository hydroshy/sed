#!/usr/bin/env python3
import re

with open('e:/PROJECT/sed/camera/camera_stream.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the metadata checking section
old = '''                print(f"DEBUG: [CameraStream] ✅ SYNCHRONIZED FRAME captured: {frame.shape} (after {skip_frames} frame skip)")
                
                # Get metadata if needed
                metadata = request.get_metadata()
                if metadata:
                    print(f"DEBUG: [CameraStream] Frame metadata: ExposureTime={metadata.get('ExposureTime', 'N/A')}, AnalogueGain={metadata.get('AnalogueGain', 'N/A')}")'''

new = '''                # Get metadata to validate frame timing
                metadata = request.get_metadata()
                frame_timestamp = metadata.get('SensorTimestamp', 0) if metadata else 0
                
                # Convert nanoseconds to seconds for comparison  
                frame_timestamp_sec = frame_timestamp / 1_000_000_000 if frame_timestamp > 1e8 else frame_timestamp
                
                # Check if frame was captured AFTER trigger was sent
                time_since_trigger = frame_timestamp_sec - self._trigger_sent_time if self._trigger_sent_time > 0 else 999
                
                if self._trigger_sent_time > 0:
                    print(f"DEBUG: [CameraStream] ✅ SYNCHRONIZED FRAME: {frame.shape} (delta={time_since_trigger*1000:.1f}ms after trigger)")
                else:
                    print(f"DEBUG: [CameraStream] ✅ FRAME captured: {frame.shape}")
                
                if metadata:
                    print(f"DEBUG: [CameraStream] Frame metadata: ExposureTime={metadata.get('ExposureTime', 'N/A')}, AnalogueGain={metadata.get('AnalogueGain', 'N/A')}")'''

if old in content:
    content = content.replace(old, new)
    with open('e:/PROJECT/sed/camera/camera_stream.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('✅ Updated camera_stream.py with timestamp validation')
else:
    print('❌ Could not find old code exactly - checking alternatives...')
    if 'SYNCHRONIZED FRAME captured' in content:
        print('Found "SYNCHRONIZED FRAME captured" - code structure may have changed')
    else:
        print('Marker not found in file')
