#!/usr/bin/env python3
"""
Manual test script for Result Tab functionality
Run this to test Result Tab FIFO queue without needing camera triggers

Usage:
    python test_result_tab_manual.py
"""

import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow

def test_result_tab():
    """Test Result Tab functionality manually"""
    
    print("\n" + "="*80)
    print("RESULT TAB MANUAL TEST")
    print("="*80 + "\n")
    
    # Create application
    app = QApplication(sys.argv)
    
    # Create main window
    print("[1] Initializing MainWindow...")
    window = MainWindow()
    
    # Show window
    print("[2] Showing window...")
    window.show()
    
    # Access Result Tab Manager
    result_tab_manager = getattr(window, 'result_tab_manager', None)
    if not result_tab_manager:
        print("❌ ERROR: result_tab_manager not found in main_window!")
        return
    
    print("✅ result_tab_manager found\n")
    
    # Test 1: Add sensor IN events
    print("[3] Testing add_sensor_in_event()...")
    print("-" * 40)
    
    frame_ids = []
    for i in range(3):
        sensor_id = 5 + i
        frame_id = result_tab_manager.add_sensor_in_event(sensor_id_in=sensor_id)
        frame_ids.append(frame_id)
        print(f"  ✓ Added sensor IN {sensor_id} → frame_id {frame_id}")
        time.sleep(0.1)
    
    print(f"\n✅ Added {len(frame_ids)} frames\n")
    
    # Test 2: Set frame status to OK
    print("[4] Testing set_frame_status() - OK...")
    print("-" * 40)
    
    result_tab_manager.set_frame_status(frame_ids[0], 'OK')
    print(f"  ✓ Frame {frame_ids[0]} set to OK (green)")
    time.sleep(0.2)
    
    # Test 3: Set frame status to NG
    print("\n[5] Testing set_frame_status() - NG...")
    print("-" * 40)
    
    result_tab_manager.set_frame_status(frame_ids[1], 'NG')
    print(f"  ✓ Frame {frame_ids[1]} set to NG (red)")
    time.sleep(0.2)
    
    # Test 4: Set frame status to PENDING
    print("\n[6] Testing set_frame_status() - PENDING...")
    print("-" * 40)
    
    result_tab_manager.set_frame_status(frame_ids[2], 'PENDING')
    print(f"  ✓ Frame {frame_ids[2]} set to PENDING (yellow)")
    time.sleep(0.2)
    
    # Test 5: Set detection data
    print("\n[7] Testing set_frame_detection_data()...")
    print("-" * 40)
    
    detection_data = {
        'detections': [
            {'class': 'pilsner333', 'confidence': 0.92, 'bbox': [10, 20, 100, 150]},
            {'class': 'heineken', 'confidence': 0.85, 'bbox': [120, 50, 180, 120]},
        ],
        'detection_count': 2,
        'inference_time': 0.210,
    }
    result_tab_manager.set_frame_detection_data(frame_ids[0], detection_data)
    print(f"  ✓ Stored {detection_data['detection_count']} detections for frame {frame_ids[0]}")
    print(f"    - Inference time: {detection_data['inference_time']}s")
    
    # Test 6: Add sensor OUT event
    print("\n[8] Testing add_sensor_out_event()...")
    print("-" * 40)
    
    success = result_tab_manager.add_sensor_out_event(sensor_id_out=105)
    print(f"  ✓ Added sensor OUT 105 → matched to frame {frame_ids[0]}" if success else 
          f"  ✗ Failed to match sensor OUT")
    
    # Test 7: Get queue status
    print("\n[9] Testing get_queue_status()...")
    print("-" * 40)
    
    queue_data = result_tab_manager.fifo_queue.get_queue_as_table_data()
    print(f"  Queue has {len(queue_data)} items")
    for item in queue_data:
        print(f"    - Frame {item['frame_id']}: Sensor IN={item['sensor_id_in']}, "
              f"OUT={item['sensor_id_out']}, Status={item['status']}")
    
    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETE")
    print("="*80)
    print("\nThe window is still open. You can interact with:")
    print("  - Delete button: Select a row and click to remove it")
    print("  - Clear button: Click to clear all rows")
    print("\nClose the window to exit the test.\n")
    
    # Run application event loop
    sys.exit(app.exec_())

if __name__ == '__main__':
    test_result_tab()
