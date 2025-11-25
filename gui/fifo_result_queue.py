"""
FIFO Result Queue Manager - Manages sensor in/out tracking and frame-based result queue

Purpose:
  - Track frame IDs with sensor IN signal
  - Match sensor OUT signal to corresponding frame
  - Maintain FIFO queue of objects in processing
  - Store frame, detection, and status for each object
  - Support deletion and bulk operations
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ResultQueueItem:
    """Represents one object in the result queue (one row in table)"""
    frame_id: int              # Frame ID assigned when frame created
    sensor_id_in: Optional[int]  # Sensor IN ID (None for manual trigger)
    sensor_id_out: Optional[int] = None  # Sensor OUT ID (None until detected)
    frame_status: str = "PENDING"  # Frame status: OK, NG (result of frame processing)
    completion_status: str = "PENDING"  # Completion status: PENDING (waiting for sensor), DONE (has both sensor_in and sensor_out)
    timestamp_in: Optional[datetime] = None  # When sensor IN was detected
    timestamp_out: Optional[datetime] = None  # When sensor OUT was detected
    detection_data: Optional[Dict[str, Any]] = None  # Frame detection/classification data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for table display"""
        return {
            'frame_id': self.frame_id,
            'frame_status': self.frame_status,
            'sensor_id_in': self.sensor_id_in if self.sensor_id_in is not None else '',
            'sensor_id_out': self.sensor_id_out if self.sensor_id_out is not None else '',
            'completion_status': self.completion_status,
            'detection_data': self.detection_data
        }


class FIFOResultQueue:
    """
    FIFO queue manager for result processing
    
    Workflow:
    1. Sensor IN detected → Create new row with frame_id, sensor_id_in
    2. Frame captured → Store detection data
    3. Sensor OUT detected → Update corresponding frame row with sensor_id_out
    4. Status evaluation → Set OK/NG status
    5. Delete/Clear → Remove rows or clear all
    
    Data structure:
      - Maintains FIFO order of objects
      - Each object tied to frame_id
      - Sensor IN/OUT tracked separately
    """
    
    def __init__(self):
        """Initialize empty FIFO queue"""
        self.queue: List[ResultQueueItem] = []
        self.next_frame_id = 1  # Counter for frame IDs
        self.max_queue_size = 100  # Prevent unlimited growth
        
        logger.info("FIFOResultQueue initialized")
    
    def add_sensor_in_event(self, sensor_id_in: int) -> int:
        """
        Handle sensor IN event - create new frame entry
        
        Args:
            sensor_id_in: Sensor ID from start_sensor (TCP from pico)
            
        Returns:
            int: Assigned frame_id for this object
        """
        try:
            frame_id = self.next_frame_id
            self.next_frame_id += 1
            
            item = ResultQueueItem(
                frame_id=frame_id,
                sensor_id_in=sensor_id_in,
                timestamp_in=datetime.now()
            )
            
            self.queue.append(item)
            
            # Check queue size
            if len(self.queue) > self.max_queue_size:
                removed = self.queue.pop(0)
                logger.warning(f"FIFOResultQueue: Queue exceeded max size, removed frame_id={removed.frame_id}")
            
            logger.debug(f"FIFOResultQueue: Added sensor IN event - frame_id={frame_id}, sensor_id_in={sensor_id_in}")
            print(f"DEBUG: [FIFOResultQueue] Sensor IN: frame_id={frame_id}, sensor_id_in={sensor_id_in}")
            
            return frame_id
            
        except Exception as e:
            logger.error(f"FIFOResultQueue: Error adding sensor IN event: {e}")
            print(f"DEBUG: [FIFOResultQueue] Error adding sensor IN: {e}")
            return -1
    
    def add_sensor_out_event(self, sensor_id_out: int) -> bool:
        """
        Handle sensor OUT event - match to FIRST (oldest) PENDING frame
        
        FIFO (First In First Out): Match to the oldest frame (first one created)
        that doesn't have sensor_out yet
        
        When sensor_out is added, automatically updates completion_status to DONE
        
        Args:
            sensor_id_out: Sensor ID from end_sensor (TCP from pico)
            
        Returns:
            bool: True if matched successfully
        """
        try:
            # FIFO: Find FIRST (oldest) frame without sensor_out
            # Don't use reversed() - we want the oldest frame, not the newest
            for item in self.queue:
                if item.sensor_id_out is None:
                    item.sensor_id_out = sensor_id_out
                    item.timestamp_out = datetime.now()
                    # Mark as DONE now that we have both sensor_in and sensor_out
                    item.completion_status = "DONE"
                    logger.debug(f"FIFOResultQueue: Added sensor OUT - frame_id={item.frame_id}, sensor_id_out={sensor_id_out}, status=DONE")
                    print(f"DEBUG: [FIFOResultQueue] Sensor OUT (FIFO): frame_id={item.frame_id}, sensor_id_out={sensor_id_out}, completion=DONE")
                    return True
            
            logger.warning(f"FIFOResultQueue: Sensor OUT received but no pending frame found - sensor_id_out={sensor_id_out}")
            print(f"DEBUG: [FIFOResultQueue] No pending frame for sensor OUT: {sensor_id_out}")
            return False
            
        except Exception as e:
            logger.error(f"FIFOResultQueue: Error adding sensor OUT event: {e}")
            print(f"DEBUG: [FIFOResultQueue] Error adding sensor OUT: {e}")
            return False
    
    def set_frame_detection_data(self, frame_id: int, detection_data: Dict[str, Any]) -> bool:
        """
        Store detection/classification data for a frame
        
        Args:
            frame_id: Frame ID to associate data with
            detection_data: Detection or classification results
            
        Returns:
            bool: True if frame found and data stored
        """
        try:
            for item in self.queue:
                if item.frame_id == frame_id:
                    item.detection_data = detection_data
                    logger.debug(f"FIFOResultQueue: Set detection data for frame_id={frame_id}")
                    print(f"DEBUG: [FIFOResultQueue] Detection data stored: frame_id={frame_id}")
                    return True
            
            logger.warning(f"FIFOResultQueue: Frame not found - frame_id={frame_id}")
            return False
            
        except Exception as e:
            logger.error(f"FIFOResultQueue: Error setting detection data: {e}")
            print(f"DEBUG: [FIFOResultQueue] Error setting detection data: {e}")
            return False
    
    def set_frame_status(self, frame_id: int, status: str) -> bool:
        """
        Set OK/NG status for a frame (frame_status field)
        
        Args:
            frame_id: Frame ID to set status for
            status: Status value ('OK', 'NG')
            
        Returns:
            bool: True if frame found and status set
        """
        try:
            if status not in ['OK', 'NG']:
                logger.warning(f"FIFOResultQueue: Invalid frame status value - {status}")
                return False
            
            for item in self.queue:
                if item.frame_id == frame_id:
                    item.frame_status = status
                    # Update completion_status: if has both sensor_in and sensor_out, mark as DONE
                    if item.sensor_id_in is not None and item.sensor_id_out is not None:
                        item.completion_status = "DONE"
                    else:
                        item.completion_status = "PENDING"
                    logger.debug(f"FIFOResultQueue: Set frame_status for frame_id={frame_id} - {status}")
                    print(f"DEBUG: [FIFOResultQueue] Frame status: frame_id={frame_id}, frame_status={status}, completion={item.completion_status}")
                    return True
            
            logger.warning(f"FIFOResultQueue: Frame not found - frame_id={frame_id}")
            return False
            
        except Exception as e:
            logger.error(f"FIFOResultQueue: Error setting frame status: {e}")
            print(f"DEBUG: [FIFOResultQueue] Error setting status: {e}")
            return False
    
    def get_queue_items(self) -> List[ResultQueueItem]:
        """
        Get all items in queue (for table display)
        
        Returns:
            List of ResultQueueItem objects in FIFO order
        """
        return self.queue.copy()
    
    def get_queue_as_table_data(self) -> List[Dict[str, Any]]:
        """
        Get queue as list of dictionaries for table display
        
        Returns:
            List of dictionaries with keys: frame_id, sensor_id_in, sensor_id_out, status
        """
        return [item.to_dict() for item in self.queue]
    
    def get_last_done_frame(self) -> Optional[ResultQueueItem]:
        """
        Get the most recently DONE frame (for servo execution)
        
        When sensor OUT arrives, first frame becomes DONE.
        This method returns that frame so servo command can be sent based on its status.
        
        Returns:
            ResultQueueItem if found, None otherwise
        """
        try:
            # Find most recent DONE frame (search from end backwards)
            for item in reversed(self.queue):
                if item.completion_status == "DONE":
                    logger.debug(f"FIFOResultQueue: Found last DONE frame - frame_id={item.frame_id}, status={item.frame_status}")
                    return item
            
            logger.debug("FIFOResultQueue: No DONE frames found")
            return None
            
        except Exception as e:
            logger.error(f"FIFOResultQueue: Error getting last DONE frame: {e}")
            return None
    
    def delete_item_by_frame_id(self, frame_id: int) -> bool:
        """
        Delete single item from queue by frame_id
        
        Args:
            frame_id: Frame ID to delete
            
        Returns:
            bool: True if item found and deleted
        """
        try:
            for i, item in enumerate(self.queue):
                if item.frame_id == frame_id:
                    self.queue.pop(i)
                    logger.debug(f"FIFOResultQueue: Deleted item - frame_id={frame_id}")
                    print(f"DEBUG: [FIFOResultQueue] Item deleted: frame_id={frame_id}")
                    return True
            
            logger.warning(f"FIFOResultQueue: Frame not found for deletion - frame_id={frame_id}")
            return False
            
        except Exception as e:
            logger.error(f"FIFOResultQueue: Error deleting item: {e}")
            print(f"DEBUG: [FIFOResultQueue] Error deleting item: {e}")
            return False
    
    def delete_item_by_row(self, row_index: int) -> bool:
        """
        Delete item by row index in table
        
        Args:
            row_index: Row index (0-based)
            
        Returns:
            bool: True if row found and deleted
        """
        try:
            if 0 <= row_index < len(self.queue):
                item = self.queue.pop(row_index)
                logger.debug(f"FIFOResultQueue: Deleted row - row_index={row_index}, frame_id={item.frame_id}")
                print(f"DEBUG: [FIFOResultQueue] Row deleted: row_index={row_index}, frame_id={item.frame_id}")
                return True
            
            logger.warning(f"FIFOResultQueue: Invalid row index - {row_index}")
            return False
            
        except Exception as e:
            logger.error(f"FIFOResultQueue: Error deleting row: {e}")
            print(f"DEBUG: [FIFOResultQueue] Error deleting row: {e}")
            return False
    
    def clear_queue(self) -> int:
        """
        Clear all items from queue
        
        Returns:
            int: Number of items cleared
        """
        try:
            count = len(self.queue)
            self.queue.clear()
            logger.info(f"FIFOResultQueue: Queue cleared - {count} items removed")
            print(f"DEBUG: [FIFOResultQueue] Queue cleared: {count} items removed")
            return count
            
        except Exception as e:
            logger.error(f"FIFOResultQueue: Error clearing queue: {e}")
            print(f"DEBUG: [FIFOResultQueue] Error clearing queue: {e}")
            return 0
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return len(self.queue)
    
    def get_pending_items(self) -> List[ResultQueueItem]:
        """Get items that are still PENDING (no sensor OUT yet)"""
        return [item for item in self.queue if item.sensor_id_out is None]
    
    def get_completed_items(self) -> List[ResultQueueItem]:
        """Get items that have both sensor IN and OUT"""
        return [item for item in self.queue if item.sensor_id_out is not None]
    
    def reset_frame_counter(self):
        """Reset frame ID counter (for new job or clear)"""
        self.next_frame_id = 1
        logger.info("FIFOResultQueue: Frame counter reset")
