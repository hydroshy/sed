"""
ResultTabManager - Manages Result Tab UI and integration with FIFO queue

Purpose:
  - Display FIFO queue items in QTableView
  - Handle button clicks (Delete, Clear Queue)
  - Update table when new frames/sensors added
  - Provide interface to result_manager for OK/NG evaluation
"""

import logging
from typing import Optional, Dict, Any, List
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QMessageBox, QPushButton
from PyQt5.QtCore import Qt, QTimer

from .fifo_result_queue import FIFOResultQueue, ResultQueueItem
from .pending_result import PendingJobResult

logger = logging.getLogger(__name__)


class ResultTabManager:
    """
    Manages Result Tab UI and FIFO queue display
    
    Responsibilities:
    - Maintain FIFO result queue
    - Update table view with queue items
    - Handle delete/clear button actions
    - Sync with sensor events
    - Provide data for result evaluation
    """
    
    def __init__(self, main_window=None):
        """
        Initialize ResultTabManager
        
        Args:
            main_window: Reference to MainWindow for UI access
        """
        self.main_window = main_window
        self.fifo_queue = FIFOResultQueue()
        
        # UI components (initialized in setup_ui)
        self.result_table_view: Optional[QTableWidget] = None
        self.delete_button: Optional[QPushButton] = None
        self.clear_button: Optional[QPushButton] = None
        
        # NEW: Lưu tạm kết quả job chờ nhận sensor IN từ TCP
        self.pending_result: Optional[PendingJobResult] = None
        
        # NEW: Track which frame is waiting for job result
        # When TCP start_rising arrives → Create frame entry
        # When job completes → Update that frame with result
        self.frame_id_waiting_for_result: Optional[int] = None
        
        # Table column mapping
        self.COLUMNS = {
            'frame_id': 0,
            'frame_status': 1,      # OK/NG status of the frame
            'sensor_id_in': 2,
            'sensor_id_out': 3,
            'completion_status': 4  # PENDING or DONE
        }
        
        # Update timer for periodic refresh
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_table)
        
        logger.info("ResultTabManager initialized")
    
    def setup_ui(self):
        """
        Setup UI components from main window
        Should be called after main window UI is loaded
        """
        try:
            print("DEBUG: ResultTabManager.setup_ui() called")
            
            if not self.main_window:
                logger.error("ResultTabManager: main_window not set")
                print("DEBUG: ResultTabManager.setup_ui() - main_window is None!")
                return False
            
            # Get table view from main_window attributes (set by _find_widgets)
            self.result_table_view = getattr(self.main_window, 'resultTableView', None)
            self.delete_button = getattr(self.main_window, 'deleteObjectButton', None)
            self.clear_button = getattr(self.main_window, 'clearQueueButton', None)
            
            logger.info(f"ResultTabManager: Found widgets - "
                       f"resultTableView={self.result_table_view is not None}, "
                       f"deleteObjectButton={self.delete_button is not None}, "
                       f"clearQueueButton={self.clear_button is not None}")
            print(f"DEBUG: ResultTabManager.setup_ui() - resultTableView={self.result_table_view is not None}, "
                  f"deleteObjectButton={self.delete_button is not None}, "
                  f"clearQueueButton={self.clear_button is not None}")
            
            if not self.result_table_view:
                logger.error("ResultTabManager: resultTableView not found on main_window")
                print("DEBUG: ResultTabManager.setup_ui() - resultTableView NOT FOUND!")
                return False
            
            # Setup table
            self.setup_table()
            print("DEBUG: ResultTabManager.setup_ui() - table setup complete")
            
            # Connect signals
            if self.delete_button:
                self.delete_button.clicked.connect(self.on_delete_clicked)
                logger.info("ResultTabManager: Connected deleteObjectButton")
                print("DEBUG: ResultTabManager.setup_ui() - deleteObjectButton connected")
            else:
                logger.warning("ResultTabManager: deleteObjectButton not found")
                print("DEBUG: ResultTabManager.setup_ui() - deleteObjectButton NOT FOUND")
            
            if self.clear_button:
                self.clear_button.clicked.connect(self.on_clear_queue_clicked)
                logger.info("ResultTabManager: Connected clearQueueButton")
                print("DEBUG: ResultTabManager.setup_ui() - clearQueueButton connected")
            else:
                logger.warning("ResultTabManager: clearQueueButton not found")
                print("DEBUG: ResultTabManager.setup_ui() - clearQueueButton NOT FOUND")
            
            logger.info("ResultTabManager: UI setup complete")
            print("DEBUG: ResultTabManager.setup_ui() - COMPLETE SUCCESS")
            return True
            
        except Exception as e:
            logger.error(f"ResultTabManager: Error in setup_ui: {e}", exc_info=True)
            print(f"DEBUG: ResultTabManager.setup_ui() - ERROR: {e}")
            return False
    
    def setup_table(self):
        """Setup table columns and properties"""
        try:
            if not self.result_table_view:
                logger.warning("ResultTabManager: result_table_view is None")
                return
            
            # Set column count (5 columns now)
            self.result_table_view.setColumnCount(5)
            
            # Set headers
            headers = ['Frame ID', 'Frame Status', 'Sensor IN', 'Sensor OUT', 'Status']
            self.result_table_view.setHorizontalHeaderLabels(headers)
            
            # Set column widths
            self.result_table_view.setColumnWidth(0, 80)   # Frame ID
            self.result_table_view.setColumnWidth(1, 100)  # Frame Status (OK/NG)
            self.result_table_view.setColumnWidth(2, 90)   # Sensor IN
            self.result_table_view.setColumnWidth(3, 100)  # Sensor OUT
            self.result_table_view.setColumnWidth(4, 100)  # Status (PENDING/DONE)
            
            # Allow row selection
            self.result_table_view.setSelectionBehavior(self.result_table_view.SelectRows)
            self.result_table_view.setSelectionMode(self.result_table_view.SingleSelection)
            
            logger.info("ResultTabManager: Table setup complete")
            
        except Exception as e:
            logger.error(f"ResultTabManager: Error in setup_table: {e}")
            print(f"DEBUG: ResultTabManager table setup error: {e}")
    
    def add_sensor_in_event(self, sensor_id_in: int) -> int:
        """
        Handle sensor IN event (start_sensor from pico via TCP)
        Creates new frame entry and returns frame_id
        
        Args:
            sensor_id_in: Sensor IN ID from pico
            
        Returns:
            int: Assigned frame_id
        """
        try:
            frame_id = self.fifo_queue.add_sensor_in_event(sensor_id_in)
            self.refresh_table()
            logger.info(f"ResultTabManager: Sensor IN added - frame_id={frame_id}, sensor_id_in={sensor_id_in}")
            return frame_id
            
        except Exception as e:
            logger.error(f"ResultTabManager: Error adding sensor IN: {e}")
            print(f"DEBUG: ResultTabManager sensor IN error: {e}")
            return -1
    
    def add_sensor_out_event(self, sensor_id_out: int) -> bool:
        """
        Handle sensor OUT event (end_sensor from pico via TCP)
        Matches to most recent pending frame
        
        Args:
            sensor_id_out: Sensor OUT ID from pico
            
        Returns:
            bool: True if matched successfully
        """
        try:
            success = self.fifo_queue.add_sensor_out_event(sensor_id_out)
            self.refresh_table()
            logger.info(f"ResultTabManager: Sensor OUT added - sensor_id_out={sensor_id_out}, success={success}")
            return success
            
        except Exception as e:
            logger.error(f"ResultTabManager: Error adding sensor OUT: {e}")
            print(f"DEBUG: ResultTabManager sensor OUT error: {e}")
            return False
    
    def save_pending_job_result(self, status: str, similarity: float = 0.0, 
                               reason: str = "", detection_data: Dict = None, 
                               inference_time: float = 0.0) -> bool:
        """
        NEW: Lưu tạm kết quả job, chờ nhận tín hiệu TCP sensor IN
        
        Gọi từ camera_manager khi job hoàn thành.
        Frame sẽ được tạo khi nhận sensor IN signal từ TCP.
        
        Args:
            status: 'OK', 'NG', or 'PENDING'
            similarity: Độ tương đồng (0-1)
            reason: Lý do kết quả
            detection_data: Dữ liệu detection/classification
            inference_time: Thời gian inference
            
        Returns:
            bool: True nếu lưu thành công
        """
        try:
            import time
            
            pending = PendingJobResult(
                status=status,
                similarity=similarity,
                reason=reason,
                detection_data=detection_data,
                inference_time=inference_time,
                timestamp=time.time()
            )
            
            self.pending_result = pending
            logger.info(f"[ResultTabManager] Saved pending job result: {pending}")
            print(f"DEBUG: [ResultTabManager] Saved pending result: {pending}")
            
            # Log chi tiết
            logger.info(f"[ResultTabManager] Waiting for TCP sensor IN signal...")
            logger.info(f"  - Status: {status}")
            logger.info(f"  - Similarity: {similarity:.2%}")
            logger.info(f"  - Detection count: {detection_data.get('detection_count', 0) if detection_data else 0}")
            
            return True
            
        except Exception as e:
            logger.error(f"[ResultTabManager] Error saving pending result: {e}", exc_info=True)
            print(f"DEBUG: [ResultTabManager] Error saving pending result: {e}")
            return False
    def on_sensor_in_received(self, sensor_id_in: int) -> int:
        """
        NEW: Nhận tín hiệu sensor IN từ TCP, tạo frame entry chờ job result
        
        Gọi từ TCP controller khi nhận start_rising event.
        Tạo frame mới với sensor_id từ TCP.
        Frame status sẽ được cập nhật khi job hoàn thành.
        
        Args:
            sensor_id_in: Sensor ID từ TCP start_rising event
            
        Returns:
            int: frame_id nếu thành công, -1 nếu lỗi
        """
        try:
            import logging
            
            logger.info(f"[ResultTabManager] TCP Sensor IN received: sensor_id_in={sensor_id_in}")
            print(f"DEBUG: [ResultTabManager] TCP Sensor IN received: {sensor_id_in}")
            
            # Tạo frame mới (luôn tạo, không cần check pending_result)
            # Frame sẽ chờ job result để cập nhật frame_status
            frame_id = self.add_sensor_in_event(sensor_id_in)
            
            if frame_id <= 0:
                logger.error(f"[ResultTabManager] Failed to create frame for sensor_id_in={sensor_id_in}")
                return -1
            
            # Mark frame as waiting for result
            self.frame_id_waiting_for_result = frame_id
            logger.info(f"[ResultTabManager] Frame created and waiting for job result: frame_id={frame_id}, sensor_id_in={sensor_id_in}")
            print(f"DEBUG: [ResultTabManager] Frame {frame_id} created, waiting for job result")
            
            # Refresh table to show new frame
            self.refresh_table()
            
            logger.info(f"[ResultTabManager] Sensor IN added - frame_id={frame_id}, sensor_id_in={sensor_id_in}")
            print(f"DEBUG: [ResultTabManager] Sensor IN processed successfully")
            
            return frame_id
            
        except Exception as e:
            logger.error(f"[ResultTabManager] Error in on_sensor_in_received: {e}", exc_info=True)
            print(f"DEBUG: [ResultTabManager] Error in on_sensor_in_received: {e}")
            return -1
            
            logger.info(f"[ResultTabManager] Frame {frame_id} created: sensor_id_in={sensor_id_in}, frame_status={frame_status}, completion_status=PENDING")
            print(f"DEBUG: [ResultTabManager] Frame {frame_id} ready: sensor_id_in={sensor_id_in}, frame_status={frame_status}")
            
            return frame_id
            
        except Exception as e:
            logger.error(f"[ResultTabManager] Error processing sensor IN: {e}", exc_info=True)
            print(f"DEBUG: [ResultTabManager] Error processing sensor IN: {e}")
            return -1
    
    def attach_job_result_to_waiting_frame(self, status: str, detection_data: Dict[str, Any] = None, 
                                           inference_time: float = 0.0, reason: str = "") -> bool:
        """
        NEW: Gắn kết quả job vào frame đang chờ
        
        Gọi từ camera_manager khi job hoàn thành.
        Tìm frame được tạo từ TCP start_rising (waiting), cập nhật frame_status.
        
        Args:
            status: Job result status ('OK', 'NG')
            detection_data: Detection/classification data
            inference_time: Job processing time
            reason: Result reason/explanation
            
        Returns:
            bool: True nếu thành công
        """
        try:
            # Nếu không có frame chờ result, không làm gì
            if self.frame_id_waiting_for_result is None:
                logger.warning(f"[ResultTabManager] No frame waiting for result")
                print(f"DEBUG: [ResultTabManager] No frame waiting for result")
                return False
            
            frame_id = self.frame_id_waiting_for_result
            
            # Cập nhật frame_status (OK/NG)
            success = self.fifo_queue.set_frame_status(frame_id, status)
            if not success:
                logger.error(f"[ResultTabManager] Failed to set frame status for frame_id={frame_id}")
                return False
            
            logger.info(f"[ResultTabManager] Attached job result to frame {frame_id}: status={status}")
            print(f"DEBUG: [ResultTabManager] Job result attached to frame {frame_id}: status={status}")
            
            # Lưu detection data nếu có
            if detection_data:
                self.set_frame_detection_data(frame_id, detection_data)
                logger.info(f"[ResultTabManager] Stored detection data for frame {frame_id}")
                print(f"DEBUG: [ResultTabManager] Detection data stored")
            
            # Refresh table
            self.refresh_table()
            
            # Reset waiting frame
            self.frame_id_waiting_for_result = None
            
            logger.info(f"[ResultTabManager] Frame {frame_id} updated with job result")
            print(f"DEBUG: [ResultTabManager] Frame {frame_id} complete")
            
            return True
            
        except Exception as e:
            logger.error(f"[ResultTabManager] Error attaching job result: {e}", exc_info=True)
            print(f"DEBUG: [ResultTabManager] Error attaching job result: {e}")
            return False
    
    def set_frame_detection_data(self, frame_id: int, detection_data: Dict[str, Any]) -> bool:
        """
        Store detection/classification data for frame
        
        Args:
            frame_id: Frame ID
            detection_data: Detection or classification results
            
        Returns:
            bool: True if successful
        """
        try:
            success = self.fifo_queue.set_frame_detection_data(frame_id, detection_data)
            return success
            
        except Exception as e:
            logger.error(f"ResultTabManager: Error setting detection data: {e}")
            print(f"DEBUG: ResultTabManager detection data error: {e}")
            return False
    
    def create_frame_with_result(self, status: str, similarity: float = 0.0, reason: str = "", 
                                  detection_data: Dict[str, Any] = None, inference_time: float = 0,
                                  frame: Any = None) -> int:
        """
        Create frame and immediately set result (finalize immediately, not pending)
        
        This is called when manual trigger completes processing.
        Creates frame directly with status (no waiting for TCP sensor IN).
        
        Args:
            status: Result status ('OK', 'NG')
            similarity: Similarity score (0-1)
            reason: Result reason/explanation
            detection_data: Detection/classification data
            inference_time: Processing time
            frame: Frame image data (optional)
            
        Returns:
            int: frame_id if successful, -1 if failed
        """
        try:
            logger.info(f"[ResultTabManager] Creating frame with immediate result: status={status}")
            print(f"DEBUG: [ResultTabManager] Creating frame with result: status={status}")
            
            # Create frame entry (no sensor_id needed for manual trigger)
            frame_id = self.add_sensor_in_event(sensor_id_in=0)  # 0 = manual trigger
            
            if frame_id <= 0:
                logger.error(f"[ResultTabManager] Failed to create frame")
                return -1
            
            # Set status immediately
            success = self.set_frame_status(frame_id, status)
            if not success:
                logger.error(f"[ResultTabManager] Failed to set frame status")
                return -1
            
            # Set detection data if available
            if detection_data:
                self.set_frame_detection_data(frame_id, detection_data)
            
            logger.info(f"[ResultTabManager] Frame created successfully: frame_id={frame_id}, status={status}")
            print(f"DEBUG: [ResultTabManager] Frame #{frame_id} created with status={status}")
            
            return frame_id
            
        except Exception as e:
            logger.error(f"[ResultTabManager] Error creating frame with result: {e}", exc_info=True)
            print(f"DEBUG: [ResultTabManager] Error creating frame with result: {e}")
            return -1
    
    def set_frame_status(self, frame_id: int, status: str) -> bool:
        """
        Set OK/NG status for frame
        
        Args:
            frame_id: Frame ID
            status: Status ('OK', 'NG', 'PENDING')
            
        Returns:
            bool: True if successful
        """
        try:
            success = self.fifo_queue.set_frame_status(frame_id, status)
            self.refresh_table()
            logger.debug(f"ResultTabManager: Frame status set - frame_id={frame_id}, status={status}")
            return success
            
        except Exception as e:
            logger.error(f"ResultTabManager: Error setting status: {e}")
            print(f"DEBUG: ResultTabManager status error: {e}")
            return False
    
    def refresh_table(self):
        """Refresh table view with current queue data"""
        try:
            if not self.result_table_view:
                logger.warning("ResultTabManager: result_table_view is None")
                print("DEBUG: ResultTabManager refresh_table - result_table_view is None!")
                return
            
            # Get queue data
            queue_data = self.fifo_queue.get_queue_as_table_data()
            logger.info(f"ResultTabManager: Refreshing table with {len(queue_data)} items")
            print(f"DEBUG: ResultTabManager refresh_table - queue_data count: {len(queue_data)}")
            
            # Clear existing rows
            self.result_table_view.setRowCount(0)
            print(f"DEBUG: ResultTabManager refresh_table - cleared table rows")
            
            # Add rows
            for row_idx, item_dict in enumerate(queue_data):
                self.result_table_view.insertRow(row_idx)
                print(f"DEBUG: ResultTabManager refresh_table - inserted row {row_idx}, frame_id={item_dict.get('frame_id')}")
                
                # Frame ID
                frame_id_item = QTableWidgetItem(str(item_dict['frame_id']))
                frame_id_item.setFlags(frame_id_item.flags() & ~Qt.ItemIsEditable)
                self.result_table_view.setItem(row_idx, self.COLUMNS['frame_id'], frame_id_item)
                
                # Frame Status (OK/NG) with color coding
                frame_status_text = item_dict.get('frame_status', 'PENDING')
                frame_status_item = QTableWidgetItem(frame_status_text)
                frame_status_item.setFlags(frame_status_item.flags() & ~Qt.ItemIsEditable)
                
                # Color code frame status
                if frame_status_text == 'OK':
                    frame_status_item.setBackground(Qt.green)
                    print(f"DEBUG: ResultTabManager refresh_table - Row {row_idx}: frame_status=OK (green)")
                elif frame_status_text == 'NG':
                    frame_status_item.setBackground(Qt.red)
                    print(f"DEBUG: ResultTabManager refresh_table - Row {row_idx}: frame_status=NG (red)")
                else:
                    frame_status_item.setBackground(Qt.yellow)
                    print(f"DEBUG: ResultTabManager refresh_table - Row {row_idx}: frame_status=PENDING (yellow)")
                
                self.result_table_view.setItem(row_idx, self.COLUMNS['frame_status'], frame_status_item)
                
                # Sensor IN
                sensor_in_text = str(item_dict.get('sensor_id_in', '')) if item_dict.get('sensor_id_in') is not None else '-'
                sensor_in_item = QTableWidgetItem(sensor_in_text)
                sensor_in_item.setFlags(sensor_in_item.flags() & ~Qt.ItemIsEditable)
                self.result_table_view.setItem(row_idx, self.COLUMNS['sensor_id_in'], sensor_in_item)
                
                # Sensor OUT
                sensor_out_text = str(item_dict.get('sensor_id_out', '')) if item_dict.get('sensor_id_out') else '-'
                sensor_out_item = QTableWidgetItem(sensor_out_text)
                sensor_out_item.setFlags(sensor_out_item.flags() & ~Qt.ItemIsEditable)
                self.result_table_view.setItem(row_idx, self.COLUMNS['sensor_id_out'], sensor_out_item)
                
                # Completion Status (PENDING/DONE) with color coding
                completion_status_text = item_dict.get('completion_status', 'PENDING')
                completion_status_item = QTableWidgetItem(completion_status_text)
                completion_status_item.setFlags(completion_status_item.flags() & ~Qt.ItemIsEditable)
                
                # Color code completion status
                if completion_status_text == 'DONE':
                    completion_status_item.setBackground(Qt.cyan)
                    print(f"DEBUG: ResultTabManager refresh_table - Row {row_idx}: completion_status=DONE (cyan)")
                else:  # PENDING
                    completion_status_item.setBackground(Qt.yellow)
                    print(f"DEBUG: ResultTabManager refresh_table - Row {row_idx}: completion_status=PENDING (yellow)")
                
                self.result_table_view.setItem(row_idx, self.COLUMNS['completion_status'], completion_status_item)
            
            logger.info(f"ResultTabManager: Table refreshed successfully - {len(queue_data)} rows displayed")
            print(f"DEBUG: ResultTabManager refresh_table - COMPLETE with {len(queue_data)} rows")
            
        except Exception as e:
            logger.error(f"ResultTabManager: Error refreshing table: {e}", exc_info=True)
            print(f"DEBUG: ResultTabManager refresh error: {e}")
    
    def on_delete_clicked(self):
        """Handle Delete Object button click"""
        try:
            if not self.result_table_view:
                logger.warning("ResultTabManager: result_table_view is None")
                return
            
            # Get selected row
            selected_rows = self.result_table_view.selectedIndexes()
            if not selected_rows:
                QMessageBox.warning(self.main_window, "Warning", "Please select a row to delete")
                return
            
            row_index = selected_rows[0].row()
            
            # Confirm deletion
            reply = QMessageBox.question(
                self.main_window,
                "Confirm Delete",
                f"Delete row {row_index + 1}?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Delete from queue
                success = self.fifo_queue.delete_item_by_row(row_index)
                if success:
                    self.refresh_table()
                    logger.info(f"ResultTabManager: Row deleted - row_index={row_index}")
                else:
                    QMessageBox.critical(self.main_window, "Error", "Failed to delete row")
            
        except Exception as e:
            logger.error(f"ResultTabManager: Error in on_delete_clicked: {e}")
            print(f"DEBUG: ResultTabManager delete error: {e}")
            QMessageBox.critical(self.main_window, "Error", f"Error deleting row: {e}")
    
    def on_clear_queue_clicked(self):
        """Handle Clear Queue button click"""
        try:
            # Confirm clearing
            reply = QMessageBox.question(
                self.main_window,
                "Confirm Clear",
                "Clear entire queue? This cannot be undone.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                count = self.fifo_queue.clear_queue()
                self.refresh_table()
                QMessageBox.information(
                    self.main_window,
                    "Success",
                    f"Queue cleared. {count} items removed."
                )
                logger.info(f"ResultTabManager: Queue cleared - {count} items removed")
            
        except Exception as e:
            logger.error(f"ResultTabManager: Error in on_clear_queue_clicked: {e}")
            print(f"DEBUG: ResultTabManager clear error: {e}")
            QMessageBox.critical(self.main_window, "Error", f"Error clearing queue: {e}")
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.fifo_queue.get_queue_size()
    
    def get_pending_frames(self) -> List[ResultQueueItem]:
        """Get frames waiting for sensor OUT"""
        return self.fifo_queue.get_pending_items()
    
    def get_completed_frames(self) -> List[ResultQueueItem]:
        """Get frames with both sensor IN and OUT"""
        return self.fifo_queue.get_completed_items()
    
    def enable_auto_refresh(self, interval_ms: int = 1000):
        """Enable periodic table refresh (useful for status updates)"""
        try:
            if not self.update_timer.isActive():
                self.update_timer.start(interval_ms)
                logger.info(f"ResultTabManager: Auto-refresh enabled - interval={interval_ms}ms")
        except Exception as e:
            logger.error(f"ResultTabManager: Error enabling auto-refresh: {e}")
    
    def disable_auto_refresh(self):
        """Disable periodic table refresh"""
        try:
            if self.update_timer.isActive():
                self.update_timer.stop()
                logger.info("ResultTabManager: Auto-refresh disabled")
        except Exception as e:
            logger.error(f"ResultTabManager: Error disabling auto-refresh: {e}")
