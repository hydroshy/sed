"""
Unit Tests for FIFO Result Queue System

Tests queue operations, sensor matching, and table management
"""

import unittest
from datetime import datetime
from gui.fifo_result_queue import FIFOResultQueue, ResultQueueItem


class TestFIFOResultQueue(unittest.TestCase):
    """Test FIFO result queue operations"""
    
    def setUp(self):
        """Initialize queue before each test"""
        self.queue = FIFOResultQueue()
    
    def test_add_single_sensor_in(self):
        """Test adding single sensor IN event"""
        frame_id = self.queue.add_sensor_in_event(sensor_id_in=5)
        
        self.assertEqual(frame_id, 1)
        self.assertEqual(len(self.queue.queue), 1)
        self.assertEqual(self.queue.queue[0].frame_id, 1)
        self.assertEqual(self.queue.queue[0].sensor_id_in, 5)
        self.assertIsNone(self.queue.queue[0].sensor_id_out)
    
    def test_add_multiple_sensor_in(self):
        """Test adding multiple sensor IN events"""
        frame_id_1 = self.queue.add_sensor_in_event(sensor_id_in=1)
        frame_id_2 = self.queue.add_sensor_in_event(sensor_id_in=2)
        frame_id_3 = self.queue.add_sensor_in_event(sensor_id_in=3)
        
        self.assertEqual(frame_id_1, 1)
        self.assertEqual(frame_id_2, 2)
        self.assertEqual(frame_id_3, 3)
        self.assertEqual(len(self.queue.queue), 3)
    
    def test_fifo_order(self):
        """Test FIFO queue order is maintained"""
        frame_ids = []
        for i in range(5):
            frame_id = self.queue.add_sensor_in_event(sensor_id_in=i+1)
            frame_ids.append(frame_id)
        
        # Verify order
        for i, item in enumerate(self.queue.queue):
            self.assertEqual(item.frame_id, i + 1)
    
    def test_add_sensor_out_to_pending(self):
        """Test adding sensor OUT matches to most recent pending frame"""
        frame_id_1 = self.queue.add_sensor_in_event(sensor_id_in=1)
        frame_id_2 = self.queue.add_sensor_in_event(sensor_id_in=2)
        
        # Add sensor OUT - should match to frame_id_2 (most recent)
        success = self.queue.add_sensor_out_event(sensor_id_out=10)
        
        self.assertTrue(success)
        self.assertIsNone(self.queue.queue[0].sensor_id_out)  # frame_1 still pending
        self.assertEqual(self.queue.queue[1].sensor_id_out, 10)  # frame_2 matched
    
    def test_add_sensor_out_to_empty_queue(self):
        """Test adding sensor OUT to empty queue fails"""
        success = self.queue.add_sensor_out_event(sensor_id_out=10)
        
        self.assertFalse(success)
        self.assertEqual(len(self.queue.queue), 0)
    
    def test_set_frame_detection_data(self):
        """Test storing detection data with frame"""
        frame_id = self.queue.add_sensor_in_event(sensor_id_in=5)
        
        detection_data = {
            'objects': [{'class': 'defect', 'confidence': 0.95}],
            'timestamp': datetime.now()
        }
        
        success = self.queue.set_frame_detection_data(frame_id, detection_data)
        
        self.assertTrue(success)
        self.assertEqual(self.queue.queue[0].detection_data, detection_data)
    
    def test_set_frame_status(self):
        """Test setting frame status"""
        frame_id = self.queue.add_sensor_in_event(sensor_id_in=5)
        
        # Test OK
        success = self.queue.set_frame_status(frame_id, 'OK')
        self.assertTrue(success)
        self.assertEqual(self.queue.queue[0].status, 'OK')
        
        # Test NG
        success = self.queue.set_frame_status(frame_id, 'NG')
        self.assertTrue(success)
        self.assertEqual(self.queue.queue[0].status, 'NG')
        
        # Test PENDING
        success = self.queue.set_frame_status(frame_id, 'PENDING')
        self.assertTrue(success)
        self.assertEqual(self.queue.queue[0].status, 'PENDING')
    
    def test_set_invalid_status(self):
        """Test setting invalid status fails"""
        frame_id = self.queue.add_sensor_in_event(sensor_id_in=5)
        
        success = self.queue.set_frame_status(frame_id, 'INVALID')
        
        self.assertFalse(success)
    
    def test_delete_item_by_frame_id(self):
        """Test deleting item by frame_id"""
        frame_id_1 = self.queue.add_sensor_in_event(sensor_id_in=1)
        frame_id_2 = self.queue.add_sensor_in_event(sensor_id_in=2)
        frame_id_3 = self.queue.add_sensor_in_event(sensor_id_in=3)
        
        success = self.queue.delete_item_by_frame_id(frame_id_2)
        
        self.assertTrue(success)
        self.assertEqual(len(self.queue.queue), 2)
        self.assertEqual(self.queue.queue[0].frame_id, 1)
        self.assertEqual(self.queue.queue[1].frame_id, 3)
    
    def test_delete_item_by_row(self):
        """Test deleting item by row index"""
        self.queue.add_sensor_in_event(sensor_id_in=1)
        self.queue.add_sensor_in_event(sensor_id_in=2)
        self.queue.add_sensor_in_event(sensor_id_in=3)
        
        success = self.queue.delete_item_by_row(1)
        
        self.assertTrue(success)
        self.assertEqual(len(self.queue.queue), 2)
        self.assertEqual(self.queue.queue[0].sensor_id_in, 1)
        self.assertEqual(self.queue.queue[1].sensor_id_in, 3)
    
    def test_clear_queue(self):
        """Test clearing entire queue"""
        self.queue.add_sensor_in_event(sensor_id_in=1)
        self.queue.add_sensor_in_event(sensor_id_in=2)
        self.queue.add_sensor_in_event(sensor_id_in=3)
        
        count = self.queue.clear_queue()
        
        self.assertEqual(count, 3)
        self.assertEqual(len(self.queue.queue), 0)
    
    def test_get_pending_items(self):
        """Test getting pending items (no sensor OUT)"""
        frame_id_1 = self.queue.add_sensor_in_event(sensor_id_in=1)
        frame_id_2 = self.queue.add_sensor_in_event(sensor_id_in=2)
        frame_id_3 = self.queue.add_sensor_in_event(sensor_id_in=3)
        
        # Mark frame_3 as completed (most recent)
        self.queue.add_sensor_out_event(sensor_id_out=10)
        
        pending = self.queue.get_pending_items()
        
        self.assertEqual(len(pending), 2)
        self.assertEqual(pending[0].frame_id, 1)
        self.assertEqual(pending[1].frame_id, 2)
    
    def test_get_completed_items(self):
        """Test getting completed items (with sensor OUT)"""
        frame_id_1 = self.queue.add_sensor_in_event(sensor_id_in=1)
        frame_id_2 = self.queue.add_sensor_in_event(sensor_id_in=2)
        frame_id_3 = self.queue.add_sensor_in_event(sensor_id_in=3)
        
        # Complete frame_3
        self.queue.add_sensor_out_event(sensor_id_out=10)
        # Complete frame_2
        self.queue.add_sensor_out_event(sensor_id_out=11)
        
        completed = self.queue.get_completed_items()
        
        self.assertEqual(len(completed), 2)
    
    def test_max_queue_size(self):
        """Test queue size limit"""
        # Add items beyond max_queue_size
        for i in range(150):
            self.queue.add_sensor_in_event(sensor_id_in=i)
        
        # Should not exceed max size
        self.assertLessEqual(len(self.queue.queue), self.queue.max_queue_size)
    
    def test_get_queue_as_table_data(self):
        """Test converting queue to table display format"""
        frame_id = self.queue.add_sensor_in_event(sensor_id_in=5)
        self.queue.set_frame_status(frame_id, 'OK')
        
        table_data = self.queue.get_queue_as_table_data()
        
        self.assertEqual(len(table_data), 1)
        self.assertEqual(table_data[0]['frame_id'], 1)
        self.assertEqual(table_data[0]['sensor_id_in'], 5)
        self.assertEqual(table_data[0]['status'], 'OK')
    
    def test_frame_counter_increment(self):
        """Test frame ID counter increments correctly"""
        frame_id_1 = self.queue.add_sensor_in_event(sensor_id_in=1)
        frame_id_2 = self.queue.add_sensor_in_event(sensor_id_in=2)
        frame_id_3 = self.queue.add_sensor_in_event(sensor_id_in=3)
        
        self.assertEqual(frame_id_1, 1)
        self.assertEqual(frame_id_2, 2)
        self.assertEqual(frame_id_3, 3)
        self.assertEqual(self.queue.next_frame_id, 4)
    
    def test_reset_frame_counter(self):
        """Test resetting frame counter"""
        self.queue.add_sensor_in_event(sensor_id_in=1)
        self.queue.add_sensor_in_event(sensor_id_in=2)
        
        self.queue.reset_frame_counter()
        
        self.assertEqual(self.queue.next_frame_id, 1)
    
    def test_realistic_workflow(self):
        """Test realistic workflow: multiple objects, sensor in/out, status"""
        print("\n=== Realistic Workflow Test ===")
        
        # Object 1 enters
        frame_id_1 = self.queue.add_sensor_in_event(sensor_id_in=1)
        self.assertEqual(frame_id_1, 1)
        
        # Object 2 enters
        frame_id_2 = self.queue.add_sensor_in_event(sensor_id_in=2)
        self.assertEqual(frame_id_2, 2)
        
        # Object 3 enters
        frame_id_3 = self.queue.add_sensor_in_event(sensor_id_in=3)
        self.assertEqual(frame_id_3, 3)
        
        # Set detection data for all
        self.queue.set_frame_detection_data(frame_id_1, {'defect': False})
        self.queue.set_frame_detection_data(frame_id_2, {'defect': True})
        self.queue.set_frame_detection_data(frame_id_3, {'defect': False})
        
        # Object 1 exits
        success = self.queue.add_sensor_out_event(sensor_id_out=10)
        self.assertTrue(success)
        self.queue.set_frame_status(frame_id_1, 'OK')
        
        # Object 2 exits
        success = self.queue.add_sensor_out_event(sensor_id_out=11)
        self.assertTrue(success)
        self.queue.set_frame_status(frame_id_2, 'NG')
        
        # Object 3 exits
        success = self.queue.add_sensor_out_event(sensor_id_out=12)
        self.assertTrue(success)
        self.queue.set_frame_status(frame_id_3, 'OK')
        
        # Verify final state
        self.assertEqual(len(self.queue.queue), 3)
        
        items = self.queue.get_queue_items()
        self.assertEqual(items[0].status, 'OK')
        self.assertEqual(items[1].status, 'NG')
        self.assertEqual(items[2].status, 'OK')
        
        completed = self.queue.get_completed_items()
        self.assertEqual(len(completed), 3)
        
        pending = self.queue.get_pending_items()
        self.assertEqual(len(pending), 0)
        
        print("✓ Workflow test passed")


class TestResultQueueItem(unittest.TestCase):
    """Test ResultQueueItem dataclass"""
    
    def test_to_dict(self):
        """Test converting item to dictionary"""
        item = ResultQueueItem(
            frame_id=1,
            sensor_id_in=5,
            sensor_id_out=10,
            status='OK'
        )
        
        item_dict = item.to_dict()
        
        self.assertEqual(item_dict['frame_id'], 1)
        self.assertEqual(item_dict['sensor_id_in'], 5)
        self.assertEqual(item_dict['sensor_id_out'], 10)
        self.assertEqual(item_dict['status'], 'OK')
    
    def test_sensor_out_none_to_empty_string(self):
        """Test None sensor_out converts to empty string in dict"""
        item = ResultQueueItem(
            frame_id=1,
            sensor_id_in=5,
            status='PENDING'
        )
        
        item_dict = item.to_dict()
        
        self.assertEqual(item_dict['sensor_id_out'], '')


if __name__ == '__main__':
    unittest.main(verbosity=2)
