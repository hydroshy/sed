#!/usr/bin/env python3
"""
Fix double trigger click issue by disabling button during processing
"""

with open('gui/camera_manager.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and modify the trigger button click handler
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    new_lines.append(line)
    
    # Look for the line with "if current_mode == 'trigger' and button_is_enabled:"
    if "if current_mode == 'trigger' and button_is_enabled:" in line:
        i += 1
        # Skip the next lines until we find the first statement after the if
        new_lines.append(lines[i])  # This is the opening of the if block
        i += 1
        
        # Insert the button disable code
        indent = "            "
        new_lines.append(f"{indent}# Disable trigger button to prevent multiple clicks during processing\n")
        new_lines.append(f"{indent}if self.trigger_camera_btn:\n")
        new_lines.append(f"{indent}    self.trigger_camera_btn.setEnabled(False)\n")
        new_lines.append(f"{indent}    self.trigger_camera_btn.repaint()\n")
        new_lines.append(f'{indent}    print("DEBUG: [CameraManager] Trigger button DISABLED to prevent multiple clicks")\n')
        new_lines.append(f"\n")
        continue
    
    # Look for "_trigger_capturing = False" and add re-enable after it
    if "_trigger_capturing = False" in line and i > 1900:
        new_lines.append(line)
        i += 1
        
        # Add re-enable code
        indent = "            "
        new_lines.append(f"\n")
        new_lines.append(f"{indent}# Re-enable trigger button after processing complete\n")
        new_lines.append(f"{indent}if self.trigger_camera_btn:\n")
        new_lines.append(f"{indent}    self.trigger_camera_btn.setEnabled(True)\n")
        new_lines.append(f"{indent}    self.trigger_camera_btn.repaint()\n")
        new_lines.append(f'{indent}    print("DEBUG: [CameraManager] Trigger button RE-ENABLED after processing")\n')
        continue
    
    i += 1

with open('gui/camera_manager.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✓ Fixed trigger double-click issue")
print("✓ Added button disable/enable logic")
