"""
Performance Monitor Module for SED
==================================

This module provides real-time performance monitoring capabilities that can be
integrated into the existing SED application. It tracks:
- Frame processing times
- Tool execution times
- Memory usage
- CPU utilization
- FPS statistics

Usage:
    from utils.performance_monitor import PerformanceMonitor
    
    monitor = PerformanceMonitor()
    
    # Monitor an operation
    with monitor.profile_operation("ocr_processing"):
        # Your processing code here
        pass
    
    # Get current stats
    stats = monitor.get_current_stats()
"""

import time
import psutil
import threading
from typing import Dict, List, Optional, Any, Callable
from collections import deque, defaultdict
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class OperationStats:
    """Statistics for a specific operation"""
    name: str
    count: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    last_time: float
    avg_memory_mb: float
    avg_cpu_percent: float


@dataclass
class FrameStats:
    """Frame processing statistics"""
    fps_current: float
    fps_average: float
    frame_time_ms: float
    processing_time_ms: float
    frame_drops: int
    total_frames: int


class PerformanceMonitor:
    """Real-time performance monitor for SED application"""
    
    def __init__(self, history_size: int = 100):
        """
        Initialize performance monitor
        
        Args:
            history_size: Number of recent measurements to keep for averaging
        """
        self.history_size = history_size
        self.process = psutil.Process()
        
        # Operation tracking
        self.operation_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self.operation_memory: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self.operation_cpu: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self.operation_counts: Dict[str, int] = defaultdict(int)
        
        # Frame tracking
        self.frame_times = deque(maxlen=history_size)
        self.processing_times = deque(maxlen=history_size)
        self.last_frame_time = time.time()
        self.frame_count = 0
        self.frame_drops = 0
        
        # System monitoring
        self.memory_usage = deque(maxlen=history_size)
        self.cpu_usage = deque(maxlen=history_size)
        
        # Threading
        self._lock = threading.Lock()
        self._monitoring = False
        self._monitor_thread = None
        
        # Callbacks for warnings
        self.warning_callbacks: List[Callable[[str, float, float], None]] = []
        
        # Performance thresholds
        self.thresholds = {
            'fps_min': 15.0,
            'frame_time_max_ms': 100.0,
            'memory_max_mb': 500.0,
            'cpu_max_percent': 85.0,
            'operation_time_max_ms': 200.0
        }
    
    def start_monitoring(self, interval: float = 1.0):
        """Start background system monitoring"""
        if self._monitoring:
            return
            
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_system, 
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        logger.info("Performance monitoring stopped")
    
    def _monitor_system(self, interval: float):
        """Background system monitoring thread"""
        while self._monitoring:
            try:
                # Collect system metrics
                memory_mb = self.process.memory_info().rss / (1024 * 1024)
                cpu_percent = self.process.cpu_percent()
                
                with self._lock:
                    self.memory_usage.append(memory_mb)
                    self.cpu_usage.append(cpu_percent)
                
                # Check thresholds and trigger warnings
                self._check_thresholds(memory_mb, cpu_percent)
                
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
            
            time.sleep(interval)
    
    def _check_thresholds(self, memory_mb: float, cpu_percent: float):
        """Check performance thresholds and trigger warnings"""
        if memory_mb > self.thresholds['memory_max_mb']:
            self._trigger_warning("high_memory", memory_mb, self.thresholds['memory_max_mb'])
        
        if cpu_percent > self.thresholds['cpu_max_percent']:
            self._trigger_warning("high_cpu", cpu_percent, self.thresholds['cpu_max_percent'])
        
        # Check FPS
        current_fps = self.get_current_fps()
        if current_fps > 0 and current_fps < self.thresholds['fps_min']:
            self._trigger_warning("low_fps", current_fps, self.thresholds['fps_min'])
    
    def _trigger_warning(self, warning_type: str, current_value: float, threshold: float):
        """Trigger warning callbacks"""
        for callback in self.warning_callbacks:
            try:
                callback(warning_type, current_value, threshold)
            except Exception as e:
                logger.error(f"Error in warning callback: {e}")
    
    def add_warning_callback(self, callback: Callable[[str, float, float], None]):
        """Add a callback for performance warnings"""
        self.warning_callbacks.append(callback)
    
    def profile_operation(self, operation_name: str):
        """Context manager for profiling operations"""
        return OperationProfiler(self, operation_name)
    
    def record_operation(self, operation_name: str, execution_time: float, 
                        memory_mb: float, cpu_percent: float):
        """Record operation performance"""
        with self._lock:
            self.operation_times[operation_name].append(execution_time)
            self.operation_memory[operation_name].append(memory_mb)
            self.operation_cpu[operation_name].append(cpu_percent)
            self.operation_counts[operation_name] += 1
        
        # Check operation-specific thresholds
        if execution_time * 1000 > self.thresholds['operation_time_max_ms']:
            self._trigger_warning(
                f"slow_operation_{operation_name}", 
                execution_time * 1000, 
                self.thresholds['operation_time_max_ms']
            )
    
    def record_frame(self, processing_time_ms: Optional[float] = None):
        """Record frame timing"""
        current_time = time.time()
        frame_time = current_time - self.last_frame_time
        
        with self._lock:
            self.frame_times.append(frame_time)
            if processing_time_ms is not None:
                self.processing_times.append(processing_time_ms)
            self.frame_count += 1
            self.last_frame_time = current_time
        
        # Check frame timing thresholds
        if frame_time * 1000 > self.thresholds['frame_time_max_ms']:
            self._trigger_warning("slow_frame", frame_time * 1000, self.thresholds['frame_time_max_ms'])
    
    def record_frame_drop(self):
        """Record a dropped frame"""
        with self._lock:
            self.frame_drops += 1
    
    def get_operation_stats(self, operation_name: str) -> Optional[OperationStats]:
        """Get statistics for a specific operation"""
        with self._lock:
            if operation_name not in self.operation_times:
                return None
            
            times = list(self.operation_times[operation_name])
            memory = list(self.operation_memory[operation_name])
            cpu = list(self.operation_cpu[operation_name])
            
            if not times:
                return None
            
            return OperationStats(
                name=operation_name,
                count=self.operation_counts[operation_name],
                total_time=sum(times),
                avg_time=sum(times) / len(times),
                min_time=min(times),
                max_time=max(times),
                last_time=times[-1] if times else 0,
                avg_memory_mb=sum(memory) / len(memory) if memory else 0,
                avg_cpu_percent=sum(cpu) / len(cpu) if cpu else 0
            )
    
    def get_frame_stats(self) -> FrameStats:
        """Get current frame statistics"""
        with self._lock:
            if not self.frame_times:
                return FrameStats(0, 0, 0, 0, 0, 0)
            
            recent_times = list(self.frame_times)
            recent_processing = list(self.processing_times)
            
            current_fps = 1.0 / recent_times[-1] if recent_times[-1] > 0 else 0
            avg_fps = len(recent_times) / sum(recent_times) if sum(recent_times) > 0 else 0
            avg_frame_time = sum(recent_times) / len(recent_times) * 1000  # ms
            avg_processing_time = sum(recent_processing) / len(recent_processing) if recent_processing else 0
            
            return FrameStats(
                fps_current=current_fps,
                fps_average=avg_fps,
                frame_time_ms=avg_frame_time,
                processing_time_ms=avg_processing_time,
                frame_drops=self.frame_drops,
                total_frames=self.frame_count
            )
    
    def get_current_fps(self) -> float:
        """Get current FPS"""
        frame_stats = self.get_frame_stats()
        return frame_stats.fps_current
    
    def get_system_stats(self) -> Dict[str, float]:
        """Get current system statistics"""
        with self._lock:
            memory_usage = list(self.memory_usage)
            cpu_usage = list(self.cpu_usage)
            
            return {
                'memory_current_mb': memory_usage[-1] if memory_usage else 0,
                'memory_average_mb': sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                'cpu_current_percent': cpu_usage[-1] if cpu_usage else 0,
                'cpu_average_percent': sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0,
                'memory_peak_mb': max(memory_usage) if memory_usage else 0,
                'cpu_peak_percent': max(cpu_usage) if cpu_usage else 0
            }
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get comprehensive current statistics"""
        frame_stats = self.get_frame_stats()
        system_stats = self.get_system_stats()
        
        # Get all operation stats
        operation_stats = {}
        with self._lock:
            for op_name in self.operation_times.keys():
                op_stats = self.get_operation_stats(op_name)
                if op_stats:
                    operation_stats[op_name] = op_stats
        
        return {
            'frame_stats': frame_stats,
            'system_stats': system_stats,
            'operation_stats': operation_stats,
            'thresholds': self.thresholds.copy()
        }
    
    def reset_stats(self):
        """Reset all statistics"""
        with self._lock:
            self.operation_times.clear()
            self.operation_memory.clear()
            self.operation_cpu.clear()
            self.operation_counts.clear()
            self.frame_times.clear()
            self.processing_times.clear()
            self.memory_usage.clear()
            self.cpu_usage.clear()
            self.frame_count = 0
            self.frame_drops = 0
        
        logger.info("Performance statistics reset")
    
    def get_optimization_suggestions(self) -> List[str]:
        """Get optimization suggestions based on current performance"""
        suggestions = []
        frame_stats = self.get_frame_stats()
        system_stats = self.get_system_stats()
        
        # FPS-related suggestions
        if frame_stats.fps_average < self.thresholds['fps_min']:
            suggestions.append(f"LOW FPS ({frame_stats.fps_average:.1f}): Consider reducing image resolution or processing complexity")
        
        if frame_stats.frame_drops > 0:
            suggestions.append(f"FRAME DROPS ({frame_stats.frame_drops}): Implement frame skipping or async processing")
        
        # Memory suggestions
        if system_stats['memory_current_mb'] > self.thresholds['memory_max_mb']:
            suggestions.append(f"HIGH MEMORY ({system_stats['memory_current_mb']:.1f}MB): Implement buffer pooling or reduce image sizes")
        
        # CPU suggestions
        if system_stats['cpu_current_percent'] > self.thresholds['cpu_max_percent']:
            suggestions.append(f"HIGH CPU ({system_stats['cpu_current_percent']:.1f}%): Consider multi-threading or algorithm optimization")
        
        # Operation-specific suggestions
        with self._lock:
            for op_name in self.operation_times.keys():
                op_stats = self.get_operation_stats(op_name)
                if op_stats and op_stats.avg_time * 1000 > self.thresholds['operation_time_max_ms']:
                    suggestions.append(f"SLOW {op_name.upper()} ({op_stats.avg_time*1000:.1f}ms): Optimize algorithm or reduce input size")
        
        return suggestions
    
    def export_stats(self) -> Dict[str, Any]:
        """Export all statistics for external analysis"""
        stats = self.get_current_stats()
        stats['export_timestamp'] = time.time()
        stats['monitoring_active'] = self._monitoring
        return stats


class OperationProfiler:
    """Context manager for profiling individual operations"""
    
    def __init__(self, monitor: PerformanceMonitor, operation_name: str):
        self.monitor = monitor
        self.operation_name = operation_name
        self.start_time = None
        self.start_memory = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        try:
            self.start_memory = self.monitor.process.memory_info().rss / (1024 * 1024)
        except:
            self.start_memory = 0
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        execution_time = end_time - self.start_time
        
        try:
            end_memory = self.monitor.process.memory_info().rss / (1024 * 1024)
            cpu_percent = self.monitor.process.cpu_percent()
        except:
            end_memory = self.start_memory
            cpu_percent = 0
        
        self.monitor.record_operation(
            self.operation_name,
            execution_time,
            end_memory,
            cpu_percent
        )


# Global performance monitor instance
_global_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def profile_operation(operation_name: str):
    """Convenience function for profiling operations"""
    return get_performance_monitor().profile_operation(operation_name)


def record_frame(processing_time_ms: Optional[float] = None):
    """Convenience function for recording frame timing"""
    get_performance_monitor().record_frame(processing_time_ms)


def record_frame_drop():
    """Convenience function for recording frame drops"""
    get_performance_monitor().record_frame_drop()


def get_current_fps() -> float:
    """Convenience function for getting current FPS"""
    return get_performance_monitor().get_current_fps()


def start_monitoring(interval: float = 1.0):
    """Start background performance monitoring"""
    get_performance_monitor().start_monitoring(interval)


def stop_monitoring():
    """Stop background performance monitoring"""
    get_performance_monitor().stop_monitoring()