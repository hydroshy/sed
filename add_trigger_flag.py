with open('e:/PROJECT/sed/gui/camera_manager.py', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

# Find line with trigger capture and add the flag  
result = []
added = False
for i, line in enumerate(lines):
    if not added and 'print("DEBUG: [CameraManager] Now capturing frame...")' in line:
        # Insert lines BEFORE this line
        indent = ' ' * 12
        result.append(indent + '# Set flag to skip job execution during trigger\n')
        result.append(indent + 'self._trigger_capturing = True\n')
        result.append(indent + '\n')
        added = True
    result.append(line)

with open('e:/PROJECT/sed/gui/camera_manager.py', 'w', encoding='utf-8') as f:
    f.writelines(result)
print('✅ Added trigger flag')
