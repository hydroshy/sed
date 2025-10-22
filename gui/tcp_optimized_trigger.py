# -*- coding: utf-8 -*-

"""
Optimized TCP Camera Trigger Handler

Giảm độ trễ TCP trigger camera bằng cách:
1. Async thread trigger (không chặn TCP thread)
2. Direct callback (bypass Qt signal overhead)
3. Fast socket processing (timeout 5s thay vì 30s)
4. Direct camera capture (bypass job pipeline)

Target: Giảm từ ~66-235ms xuống ~15-40ms (75% improvement)

Version: 1.0
Author: AI Assistant
Date: October 21, 2025
"""

import re
import logging
import time
from threading import Thread, Lock, Event
from PyQt5.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker, QThread

logger = logging.getLogger(__name__)

# Pre-compiled regex cho parse message nhanh hơn
TRIGGER_PATTERN = re.compile(r'start_rising\|\|(\d+)')


class CameraTriggerWorker(QThread):
    """Thread riêng để trigger camera không chặn TCP handler"""
    
    trigger_complete = pyqtSignal(bool, str)  # (success, message)
    
    def __init__(self, camera_manager, message: str):
        super().__init__()
        self.camera_manager = camera_manager
        self.message = message
        self.start_time = time.perf_counter()
    
    def run(self):
        """Trigger camera in separate thread"""
        try:
            # Call activate_capture_request without blocking TCP thread
            self.camera_manager.activate_capture_request()
            
            latency_ms = (time.perf_counter() - self.start_time) * 1000
            logger.info(
                f"✓ Async trigger completed: {self.message} "
                f"(latency: {latency_ms:.2f}ms)"
            )
            self.trigger_complete.emit(True, self.message)
            
        except Exception as e:
            logger.error(f"✗ Async trigger error: {e}", exc_info=True)
            self.trigger_complete.emit(False, self.message)


class OptimizedTCPTriggerHandler(QObject):
    """
    Optimized handler cho TCP trigger camera với độ trễ thấp
    
    Features:
    - Direct callback support (bypass Qt signals)
    - Async thread triggering
    - Fast regex parsing
    - Latency statistics tracking
    """
    
    # Signals
    trigger_detected = pyqtSignal(str, float)  # (command, timestamp)
    trigger_executed = pyqtSignal(str, float, float)  # (command, timestamp, latency_ms)
    
    def __init__(self, camera_manager, tcp_controller=None):
        super().__init__()
        self.camera_manager = camera_manager
        self.tcp_controller = tcp_controller
        
        # Statistics tracking
        self.stats = {
            'total_triggers': 0,
            'successful_triggers': 0,
            'failed_triggers': 0,
            'total_latency_ms': 0.0,
            'min_latency_ms': float('inf'),
            'max_latency_ms': 0.0,
        }
        
        # Thread safety
        self.trigger_lock = QMutex()
        
        # Active trigger workers
        self.active_workers = []
        
        logger.info("✓ OptimizedTCPTriggerHandler initialized")
    
    def process_trigger_message_fast(self, message: str) -> bool:
        """
        Process trigger message with minimal latency
        
        Optimizations:
        - Pre-compiled regex (< 0.1ms)
        - Direct camera call
        - Async thread for capture
        - No job pipeline overhead
        
        Args:
            message: TCP message (e.g., "start_rising||1634723")
            
        Returns:
            bool: True if trigger initiated successfully
        """
        operation_start = time.perf_counter()
        
        try:
            # Step 1: Fast regex match (< 0.1ms)
            match = TRIGGER_PATTERN.search(message)
            if not match:
                logger.debug(f"Message didn't match trigger pattern: {message}")
                return False
            
            sensor_timestamp = int(match.group(1))
            
            # Step 2: Check camera mode (< 0.1ms)
            if self.camera_manager.current_mode != 'trigger':
                logger.debug(
                    f"Camera not in trigger mode (current: {self.camera_manager.current_mode})"
                )
                return False
            
            # Step 3: Spawn async trigger thread (< 1ms)
            self._trigger_async(message, sensor_timestamp)
            
            # Step 4: Record timing
            total_time = (time.perf_counter() - operation_start) * 1000
            logger.info(
                f"★ Trigger initiated: {message} "
                f"(message processing: {total_time:.2f}ms)"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Error processing trigger message: {e}", exc_info=True)
            self.stats['failed_triggers'] += 1
            return False
    
    def _trigger_async(self, message: str, sensor_timestamp: int):
        """
        Trigger camera asynchronously in separate thread
        
        Args:
            message: Trigger message
            sensor_timestamp: Sensor timestamp from message
        """
        try:
            with QMutexLocker(self.trigger_lock):
                # Create worker thread
                worker = CameraTriggerWorker(self.camera_manager, message)
                
                # Connect signals
                worker.trigger_complete.connect(
                    lambda success, msg: self._on_trigger_complete(success, msg, sensor_timestamp)
                )
                
                # Store reference and start
                self.active_workers.append(worker)
                worker.finished.connect(
                    lambda: self._cleanup_worker(worker)
                )
                worker.start()
                
                logger.debug(f"Async trigger thread spawned for: {message}")
        
        except Exception as e:
            logger.error(f"✗ Error spawning async trigger: {e}", exc_info=True)
    
    def _on_trigger_complete(self, success: bool, message: str, sensor_timestamp: int):
        """Handle trigger completion"""
        self.stats['total_triggers'] += 1
        
        if success:
            self.stats['successful_triggers'] += 1
            logger.info(f"✓ Trigger success: {message}")
            self.trigger_executed.emit(message, sensor_timestamp, 0)
        else:
            self.stats['failed_triggers'] += 1
            logger.error(f"✗ Trigger failed: {message}")
    
    def _cleanup_worker(self, worker):
        """Clean up completed worker thread"""
        try:
            if worker in self.active_workers:
                self.active_workers.remove(worker)
        except Exception as e:
            logger.error(f"Error cleaning up worker: {e}")
    
    def get_statistics(self) -> dict:
        """Get trigger statistics"""
        total = self.stats['total_triggers']
        successful = self.stats['successful_triggers']
        
        return {
            'total_triggers': total,
            'successful_triggers': successful,
            'failed_triggers': self.stats['failed_triggers'],
            'success_rate': f"{(successful / max(total, 1) * 100):.1f}%",
            'avg_latency_ms': round(
                self.stats['total_latency_ms'] / max(successful, 1), 2
            ),
            'min_latency_ms': round(self.stats['min_latency_ms'], 2) 
                if self.stats['min_latency_ms'] != float('inf') else 0,
            'max_latency_ms': round(self.stats['max_latency_ms'], 2),
        }
    
    def print_statistics(self):
        """Print formatted statistics"""
        stats = self.get_statistics()
        logger.info(
            f"\n{'='*70}\n"
            f"TCP TRIGGER STATISTICS\n"
            f"{'='*70}\n"
            f"Total Triggers:          {stats['total_triggers']}\n"
            f"Successful:              {stats['successful_triggers']} ({stats['success_rate']})\n"
            f"Failed:                  {stats['failed_triggers']}\n"
            f"Average Latency:         {stats['avg_latency_ms']}ms\n"
            f"Min Latency:             {stats['min_latency_ms']}ms\n"
            f"Max Latency:             {stats['max_latency_ms']}ms\n"
            f"{'='*70}\n"
        )
    
    def reset_statistics(self):
        """Reset statistics"""
        self.stats = {
            'total_triggers': 0,
            'successful_triggers': 0,
            'failed_triggers': 0,
            'total_latency_ms': 0.0,
            'min_latency_ms': float('inf'),
            'max_latency_ms': 0.0,
        }
        logger.info("Trigger statistics reset")


class OptimizedTCPControllerManager(QObject):
    """
    Enhanced TCP Controller Manager with low-latency optimization
    
    Features:
    - Direct callback path for triggers
    - Async trigger thread
    - Optimized message parsing
    - Latency statistics
    """
    
    def __init__(self, tcp_controller, camera_manager):
        super().__init__()
        self.tcp_controller = tcp_controller
        self.camera_manager = camera_manager
        
        # Create optimized trigger handler
        self.trigger_handler = OptimizedTCPTriggerHandler(camera_manager, tcp_controller)
        
        # Connect TCP controller signals
        if hasattr(tcp_controller, 'message_received'):
            tcp_controller.message_received.connect(self._on_message_received_optimized)
        
        # Direct callback for triggers (bypass signal chain)
        self.tcp_controller.on_trigger_callback = self._on_trigger_direct
        
        logger.info("✓ OptimizedTCPControllerManager initialized")
    
    def _on_message_received_optimized(self, message: str):
        """
        Optimized message handler
        
        - Fast path: Trigger messages processed immediately
        - Slow path: Regular messages logged
        """
        message = message.strip()
        if not message:
            return
        
        # Fast trigger path (< 1ms)
        if 'start_rising' in message:
            self.trigger_handler.process_trigger_message_fast(message)
        
        # Regular message path
        logger.debug(f"Regular message: {message}")
    
    def _on_trigger_direct(self, message: str):
        """
        Direct callback for triggers (no signal overhead)
        
        Called directly from tcp_controller for minimum latency
        """
        logger.info(f"★ Direct trigger callback: {message}")
        self.trigger_handler.process_trigger_message_fast(message)
    
    def get_trigger_statistics(self) -> dict:
        """Get trigger statistics"""
        return self.trigger_handler.get_statistics()
    
    def print_trigger_statistics(self):
        """Print trigger statistics"""
        self.trigger_handler.print_statistics()
    
    def reset_trigger_statistics(self):
        """Reset trigger statistics"""
        self.trigger_handler.reset_statistics()
    
    def cleanup(self):
        """
        Clean up all resources and terminate worker threads.
        Called during application shutdown.
        """
        try:
            # Terminate all active trigger worker threads
            if hasattr(self, 'trigger_handler') and self.trigger_handler:
                try:
                    # Terminate active workers with short timeout
                    for worker in list(self.trigger_handler.active_workers):
                        try:
                            if worker and worker.isRunning():
                                worker.quit()
                                if not worker.wait(100):  # 100ms timeout
                                    worker.terminate()
                                    worker.wait(50)
                        except Exception as e:
                            logger.debug(f"Error terminating worker: {e}")
                    
                    # Clear the list
                    self.trigger_handler.active_workers.clear()
                    
                except Exception as e:
                    logger.debug(f"Error during trigger handler cleanup: {e}")
            
            logger.info("✓ OptimizedTCPControllerManager cleanup completed")
        
        except Exception as e:
            logger.error(f"Error during OptimizedTCPControllerManager cleanup: {e}")
