"""
Example Integration: How to use ResultTabManager in your application

This file shows practical examples of integrating the Result Tab FIFO queue
with TCP sensor events and detection pipeline.
"""

# ============================================================================
# EXAMPLE 1: TCP Sensor Events Integration
# ============================================================================

def handle_tcp_sensor_event(main_window, sensor_type, sensor_id):
    """
    Handle sensor events from PicoPython via TCP
    
    Args:
        main_window: Reference to MainWindow
        sensor_type: 'START' or 'END'
        sensor_id: Sensor ID from PicoPython
    """
    
    if sensor_type == 'START':
        # Object entering - create new frame entry
        frame_id = main_window.result_tab_manager.add_sensor_in_event(sensor_id)
        print(f"New object detected: frame_id={frame_id}, sensor_in={sensor_id}")
        
        # Trigger camera capture (if auto-mode)
        if main_window.camera_manager:
            # Camera should capture and associate with frame_id
            main_window.camera_manager.capture_frame_with_id(frame_id)
    
    elif sensor_type == 'END':
        # Object exiting - match to pending frame
        success = main_window.result_tab_manager.add_sensor_out_event(sensor_id)
        if success:
            print(f"Object exited: sensor_out={sensor_id}")
        else:
            print(f"WARNING: No pending frame for sensor_out={sensor_id}")


# ============================================================================
# EXAMPLE 2: Detection Pipeline Integration
# ============================================================================

def run_detection_pipeline(main_window, frame_id, frame_image):
    """
    Run detection on captured frame and update result tab
    
    Args:
        main_window: Reference to MainWindow
        frame_id: Frame ID assigned when sensor triggered
        frame_image: Captured frame image
    """
    
    # Run detection tool
    detection_results = main_window.detect_tool_manager.run_detection(frame_image)
    
    if detection_results:
        # Store detection data in queue
        success = main_window.result_tab_manager.set_frame_detection_data(
            frame_id=frame_id,
            detection_data=detection_results
        )
        
        if success:
            # Evaluate OK/NG using result_manager
            status = main_window.result_manager.evaluate_NG_OK(detection_results)
            
            # Update status in result tab
            main_window.result_tab_manager.set_frame_status(
                frame_id=frame_id,
                status=status
            )
            
            print(f"Detection complete: frame_id={frame_id}, status={status}")
        else:
            print(f"ERROR: Could not find frame_id={frame_id} in queue")
    else:
        print(f"ERROR: Detection failed for frame_id={frame_id}")


# ============================================================================
# EXAMPLE 3: Classification Pipeline Integration
# ============================================================================

def run_classification_pipeline(main_window, frame_id, frame_image):
    """
    Run classification on captured frame and update result tab
    
    Args:
        main_window: Reference to MainWindow
        frame_id: Frame ID assigned when sensor triggered
        frame_image: Captured frame image
    """
    
    # Run classification tool
    classification_results = main_window.classification_tool_manager.run_classification(frame_image)
    
    if classification_results:
        # Store classification data in queue
        success = main_window.result_tab_manager.set_frame_detection_data(
            frame_id=frame_id,
            detection_data=classification_results
        )
        
        if success:
            # Classify as OK/NG based on results
            if 'defect' in classification_results:
                status = 'NG'
            else:
                status = 'OK'
            
            # Update status in result tab
            main_window.result_tab_manager.set_frame_status(
                frame_id=frame_id,
                status=status
            )
            
            print(f"Classification complete: frame_id={frame_id}, status={status}")
        else:
            print(f"ERROR: Could not find frame_id={frame_id} in queue")


# ============================================================================
# EXAMPLE 4: Combined Sensor + Detection Workflow
# ============================================================================

class SensorDetectionWorkflow:
    """
    Manages complete workflow: Sensor → Capture → Detect → Result
    """
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.pending_frames = {}  # frame_id -> capture_time mapping
    
    def on_sensor_start(self, sensor_id_in):
        """Handle start sensor event"""
        
        # Create new frame entry
        frame_id = self.main_window.result_tab_manager.add_sensor_in_event(sensor_id_in)
        
        # Trigger camera capture
        frame = self.main_window.camera_manager.capture_frame_with_id(frame_id)
        
        # Store pending frame
        self.pending_frames[frame_id] = {
            'sensor_id_in': sensor_id_in,
            'frame': frame,
            'timestamp': datetime.now()
        }
        
        # Run detection in background (optional)
        self._run_detection_async(frame_id, frame)
        
        print(f"Sensor START: frame_id={frame_id}, sensor_id_in={sensor_id_in}")
    
    def on_sensor_end(self, sensor_id_out):
        """Handle end sensor event"""
        
        # Match to pending frame
        success = self.main_window.result_tab_manager.add_sensor_out_event(sensor_id_out)
        
        if success:
            print(f"Sensor END: sensor_id_out={sensor_id_out}")
        
        return success
    
    def _run_detection_async(self, frame_id, frame):
        """Run detection in background thread"""
        from threading import Thread
        
        def detect():
            detection_results = self.main_window.detect_tool_manager.run_detection(frame)
            if detection_results:
                self.main_window.result_tab_manager.set_frame_detection_data(
                    frame_id, detection_results
                )
                
                # Evaluate status
                status = self.main_window.result_manager.evaluate_NG_OK(detection_results)
                self.main_window.result_tab_manager.set_frame_status(frame_id, status)
        
        thread = Thread(target=detect, daemon=True)
        thread.start()


# ============================================================================
# EXAMPLE 5: Data Export
# ============================================================================

def export_results_to_csv(main_window, filename):
    """Export result queue to CSV file"""
    import pandas as pd
    
    # Get queue data
    queue_data = main_window.result_tab_manager.fifo_queue.get_queue_as_table_data()
    
    # Convert to DataFrame
    df = pd.DataFrame(queue_data)
    
    # Export to CSV
    df.to_csv(filename, index=False)
    
    print(f"Results exported to: {filename}")


def get_results_summary(main_window):
    """Get summary statistics of results"""
    
    queue_size = main_window.result_tab_manager.get_queue_size()
    pending = main_window.result_tab_manager.get_pending_frames()
    completed = main_window.result_tab_manager.get_completed_frames()
    
    # Count OK/NG
    ok_count = sum(1 for item in completed if item.status == 'OK')
    ng_count = sum(1 for item in completed if item.status == 'NG')
    
    return {
        'total': queue_size,
        'pending': len(pending),
        'completed': len(completed),
        'ok_count': ok_count,
        'ng_count': ng_count,
        'ng_ratio': ng_count / len(completed) if completed else 0
    }


# ============================================================================
# EXAMPLE 6: TCP Controller Integration Hook
# ============================================================================

class TCPSensorHook:
    """
    Hook into TCP controller to automatically handle sensor events
    
    In your tcp_controller_manager.py, add this code to message handler:
    """
    
    @staticmethod
    def on_tcp_message_received(main_window, message):
        """
        Parse TCP message and trigger sensor event handling
        
        Message format examples:
        - "SENSOR:START:5" → Start sensor ID 5
        - "SENSOR:END:10"  → End sensor ID 10
        """
        
        try:
            parts = message.split(':')
            
            if parts[0] == 'SENSOR':
                sensor_type = parts[1]  # START or END
                sensor_id = int(parts[2])  # Sensor ID
                
                handle_tcp_sensor_event(main_window, sensor_type, sensor_id)
        
        except Exception as e:
            print(f"ERROR: Failed to parse TCP message: {e}")


# ============================================================================
# EXAMPLE 7: Quick Reference - Common Operations
# ============================================================================

"""
Quick Reference for ResultTabManager

# Add sensor IN event (creates new row)
frame_id = result_tab_manager.add_sensor_in_event(sensor_id_in=5)

# Store detection/classification data
result_tab_manager.set_frame_detection_data(frame_id, detection_data)

# Set OK/NG status
result_tab_manager.set_frame_status(frame_id, 'OK')
# or 'NG', or 'PENDING'

# Add sensor OUT event (matches to pending frame)
result_tab_manager.add_sensor_out_event(sensor_id_out=10)

# Get statistics
pending_frames = result_tab_manager.get_pending_frames()
completed_frames = result_tab_manager.get_completed_frames()
queue_size = result_tab_manager.get_queue_size()

# User actions (automatic via buttons)
# Delete selected row: on_delete_clicked()
# Clear all rows: on_clear_queue_clicked()

# Enable/disable auto-refresh
result_tab_manager.enable_auto_refresh(interval_ms=1000)
result_tab_manager.disable_auto_refresh()
"""


# ============================================================================
# TESTING EXAMPLE
# ============================================================================

if __name__ == '__main__':
    """
    Standalone test of FIFO queue logic (no GUI)
    """
    
    from fifo_result_queue import FIFOResultQueue
    
    # Create queue
    queue = FIFOResultQueue()
    
    # Test: Simulate 3 objects
    print("=== Test: 3 Objects Passing Through ===\n")
    
    # Object 1
    frame_id_1 = queue.add_sensor_in_event(sensor_id_in=1)
    print(f"Object 1 enters: frame_id={frame_id_1}")
    
    # Object 2
    frame_id_2 = queue.add_sensor_in_event(sensor_id_in=2)
    print(f"Object 2 enters: frame_id={frame_id_2}")
    
    # Object 3
    frame_id_3 = queue.add_sensor_in_event(sensor_id_in=3)
    print(f"Object 3 enters: frame_id={frame_id_3}")
    
    # Object 1 exits
    queue.add_sensor_out_event(sensor_id_out=10)
    print(f"Object 1 exits: sensor_out=10")
    
    # Set status for Object 1
    queue.set_frame_status(frame_id_1, 'OK')
    print(f"Object 1 status: OK\n")
    
    # Object 2 exits
    queue.add_sensor_out_event(sensor_id_out=11)
    print(f"Object 2 exits: sensor_out=11")
    
    # Set status for Object 2
    queue.set_frame_status(frame_id_2, 'NG')
    print(f"Object 2 status: NG\n")
    
    # Display queue
    print("=== Queue Contents ===")
    for item in queue.get_queue_items():
        print(f"Frame {item.frame_id}: SenIN={item.sensor_id_in}, "
              f"SenOUT={item.sensor_id_out}, Status={item.status}")
    
    print(f"\nQueue size: {queue.get_queue_size()}")
    print(f"Pending: {len(queue.get_pending_items())}")
    print(f"Completed: {len(queue.get_completed_items())}")
