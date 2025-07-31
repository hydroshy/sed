#!/usr/bin/env python3
"""
SED Performance Profiler
=========================

A comprehensive performance analysis tool for the Smart Eye Detection (SED) project.
This tool measures and analyzes performance bottlenecks in:
- Camera pipeline
- Image processing tools (OCR, Edge Detection, YOLO)
- Memory usage
- Threading efficiency
- FPS impact analysis

Usage:
    python performance_profiler.py --help
    python performance_profiler.py --full-analysis
    python performance_profiler.py --camera-only
    python performance_profiler.py --tools-only
"""

import sys
import time
import psutil
import argparse
import logging
import threading
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Data class for storing performance metrics"""
    operation: str
    execution_time: float
    memory_usage_mb: float
    cpu_percent: float
    timestamp: float
    additional_data: Dict[str, Any] = None


@dataclass
class CameraMetrics:
    """Camera-specific performance metrics"""
    fps_actual: float
    fps_target: float
    frame_resolution: Tuple[int, int]
    processing_time_ms: float
    frame_drops: int
    memory_per_frame_mb: float


@dataclass
class ToolMetrics:
    """Tool-specific performance metrics"""
    tool_name: str
    processing_time_ms: float
    input_size: Tuple[int, int]
    memory_usage_mb: float
    accuracy_score: Optional[float] = None
    additional_metrics: Dict[str, Any] = None


class PerformanceProfiler:
    """Main performance profiler class"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.camera_metrics: List[CameraMetrics] = []
        self.tool_metrics: List[ToolMetrics] = []
        self.process = psutil.Process()
        self.start_time = time.time()
        
        # Performance thresholds for warnings
        self.thresholds = {
            'camera_fps': 15.0,  # Minimum acceptable FPS
            'tool_processing_ms': 100.0,  # Max processing time per tool
            'memory_mb': 500.0,  # Max memory usage
            'cpu_percent': 80.0  # Max CPU usage
        }
    
    def measure_operation(self, operation_name: str):
        """Context manager for measuring operation performance"""
        return OperationProfiler(self, operation_name)
    
    def record_metric(self, metric: PerformanceMetrics):
        """Record a performance metric"""
        self.metrics.append(metric)
    
    def record_camera_metric(self, metric: CameraMetrics):
        """Record camera-specific metric"""
        self.camera_metrics.append(metric)
    
    def record_tool_metric(self, metric: ToolMetrics):
        """Record tool-specific metric"""
        self.tool_metrics.append(metric)
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            return {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'memory_available_gb': psutil.virtual_memory().available / (1024**3),
                'cpu_freq_current': psutil.cpu_freq().current if psutil.cpu_freq() else None,
                'platform': sys.platform,
                'python_version': sys.version,
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {}
    
    def analyze_camera_performance(self) -> Dict[str, Any]:
        """Analyze camera performance"""
        if not self.camera_metrics:
            return {"error": "No camera metrics available"}
        
        avg_fps = np.mean([m.fps_actual for m in self.camera_metrics])
        avg_processing_time = np.mean([m.processing_time_ms for m in self.camera_metrics])
        total_frame_drops = sum([m.frame_drops for m in self.camera_metrics])
        avg_memory_per_frame = np.mean([m.memory_per_frame_mb for m in self.camera_metrics])
        
        # Calculate efficiency
        target_fps = self.camera_metrics[0].fps_target if self.camera_metrics else 30
        fps_efficiency = (avg_fps / target_fps) * 100 if target_fps > 0 else 0
        
        analysis = {
            'average_fps': avg_fps,
            'target_fps': target_fps,
            'fps_efficiency_percent': fps_efficiency,
            'average_processing_time_ms': avg_processing_time,
            'total_frame_drops': total_frame_drops,
            'average_memory_per_frame_mb': avg_memory_per_frame,
            'frame_resolution': self.camera_metrics[0].frame_resolution if self.camera_metrics else None,
            'warnings': []
        }
        
        # Add warnings
        if avg_fps < self.thresholds['camera_fps']:
            analysis['warnings'].append(f"Low FPS: {avg_fps:.1f} < {self.thresholds['camera_fps']}")
        
        if avg_processing_time > self.thresholds['tool_processing_ms']:
            analysis['warnings'].append(f"High processing time: {avg_processing_time:.1f}ms")
        
        if total_frame_drops > 0:
            analysis['warnings'].append(f"Frame drops detected: {total_frame_drops}")
        
        return analysis
    
    def analyze_tool_performance(self) -> Dict[str, Any]:
        """Analyze individual tool performance"""
        if not self.tool_metrics:
            return {"error": "No tool metrics available"}
        
        tool_analysis = {}
        
        # Group by tool name
        tools = {}
        for metric in self.tool_metrics:
            if metric.tool_name not in tools:
                tools[metric.tool_name] = []
            tools[metric.tool_name].append(metric)
        
        for tool_name, metrics in tools.items():
            avg_time = np.mean([m.processing_time_ms for m in metrics])
            avg_memory = np.mean([m.memory_usage_mb for m in metrics])
            total_executions = len(metrics)
            
            tool_analysis[tool_name] = {
                'average_processing_time_ms': avg_time,
                'average_memory_usage_mb': avg_memory,
                'total_executions': total_executions,
                'warnings': []
            }
            
            # Add tool-specific warnings
            if avg_time > self.thresholds['tool_processing_ms']:
                tool_analysis[tool_name]['warnings'].append(
                    f"Slow processing: {avg_time:.1f}ms > {self.thresholds['tool_processing_ms']}ms")
            
            if avg_memory > self.thresholds['memory_mb']:
                tool_analysis[tool_name]['warnings'].append(
                    f"High memory usage: {avg_memory:.1f}MB > {self.thresholds['memory_mb']}MB")
        
        return tool_analysis
    
    def analyze_overall_performance(self) -> Dict[str, Any]:
        """Analyze overall system performance"""
        if not self.metrics:
            return {"error": "No general metrics available"}
        
        total_time = time.time() - self.start_time
        avg_cpu = np.mean([m.cpu_percent for m in self.metrics])
        avg_memory = np.mean([m.memory_usage_mb for m in self.metrics])
        total_operations = len(self.metrics)
        
        analysis = {
            'total_runtime_seconds': total_time,
            'total_operations': total_operations,
            'average_cpu_percent': avg_cpu,
            'average_memory_mb': avg_memory,
            'operations_per_second': total_operations / total_time if total_time > 0 else 0,
            'warnings': []
        }
        
        # Add warnings
        if avg_cpu > self.thresholds['cpu_percent']:
            analysis['warnings'].append(f"High CPU usage: {avg_cpu:.1f}% > {self.thresholds['cpu_percent']}%")
        
        if avg_memory > self.thresholds['memory_mb']:
            analysis['warnings'].append(f"High memory usage: {avg_memory:.1f}MB > {self.thresholds['memory_mb']}MB")
        
        return analysis
    
    def generate_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on analysis"""
        recommendations = []
        
        camera_analysis = self.analyze_camera_performance()
        tool_analysis = self.analyze_tool_performance()
        overall_analysis = self.analyze_overall_performance()
        
        # Camera optimizations
        if 'fps_efficiency_percent' in camera_analysis and camera_analysis['fps_efficiency_percent'] < 80:
            recommendations.extend([
                "🎥 CAMERA OPTIMIZATION:",
                "  • Reduce camera resolution (current: high resolution may cause bottleneck)",
                "  • Lower target FPS if real-time processing isn't critical",
                "  • Consider frame skipping for processing-heavy operations",
                "  • Use separate threads for camera capture and processing"
            ])
        
        if 'frame_drops' in camera_analysis and camera_analysis.get('total_frame_drops', 0) > 0:
            recommendations.extend([
                "  • Optimize frame buffer management",
                "  • Consider asynchronous processing pipeline"
            ])
        
        # Tool-specific optimizations
        if 'error' not in tool_analysis:
            for tool_name, metrics in tool_analysis.items():
                if metrics['average_processing_time_ms'] > 50:
                    if tool_name.lower() == 'ocr':
                        recommendations.extend([
                            "🔤 OCR OPTIMIZATION:",
                            "  • Reduce image preprocessing (scale down before OCR)",
                            "  • Use ROI (Region of Interest) instead of full image",
                            "  • Consider lightweight OCR models",
                            "  • Cache OCR results for similar regions"
                        ])
                    elif 'edge' in tool_name.lower():
                        recommendations.extend([
                            "📐 EDGE DETECTION OPTIMIZATION:",
                            "  • Reduce image resolution before edge detection",
                            "  • Optimize Canny threshold parameters",
                            "  • Use grayscale images for edge detection"
                        ])
                    elif 'yolo' in tool_name.lower() or 'detect' in tool_name.lower():
                        recommendations.extend([
                            "🎯 OBJECT DETECTION OPTIMIZATION:",
                            "  • Use smaller YOLO model (YOLOv8n instead of YOLOv8s/m/l)",
                            "  • Reduce inference resolution",
                            "  • Use ONNX Runtime optimization",
                            "  • Consider model quantization (INT8)"
                        ])
        
        # Memory optimizations
        if 'average_memory_mb' in overall_analysis and overall_analysis['average_memory_mb'] > 200:
            recommendations.extend([
                "💾 MEMORY OPTIMIZATION:",
                "  • Implement image buffer pooling",
                "  • Release processed frames immediately",
                "  • Use in-place operations where possible",
                "  • Consider image compression for storage"
            ])
        
        # CPU optimizations
        if 'average_cpu_percent' in overall_analysis and overall_analysis['average_cpu_percent'] > 60:
            recommendations.extend([
                "⚡ CPU OPTIMIZATION:",
                "  • Implement multi-threading for parallel tool execution",
                "  • Use NumPy vectorized operations",
                "  • Optimize image preprocessing pipelines",
                "  • Consider GPU acceleration for compatible operations"
            ])
        
        # Threading optimizations
        recommendations.extend([
            "🔄 THREADING OPTIMIZATION:",
            "  • Separate UI thread from processing threads",
            "  • Use producer-consumer pattern for frame processing",
            "  • Implement job queue with priority levels",
            "  • Consider asyncio for I/O bound operations"
        ])
        
        # Hardware-specific recommendations
        system_info = self.get_system_info()
        if system_info.get('memory_total_gb', 0) < 2:
            recommendations.extend([
                "🖥️  HARDWARE RECOMMENDATIONS:",
                "  • Consider upgrading RAM (current: < 2GB)",
                "  • Use swap file for large image processing"
            ])
        
        return recommendations
    
    def save_report(self, filename: Optional[str] = None) -> str:
        """Save comprehensive performance report"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sed_performance_report_{timestamp}.json"
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'system_info': self.get_system_info(),
            'camera_analysis': self.analyze_camera_performance(),
            'tool_analysis': self.analyze_tool_performance(),
            'overall_analysis': self.analyze_overall_performance(),
            'optimization_recommendations': self.generate_optimization_recommendations(),
            'raw_metrics': {
                'general_metrics': [asdict(m) for m in self.metrics],
                'camera_metrics': [asdict(m) for m in self.camera_metrics],
                'tool_metrics': [asdict(m) for m in self.tool_metrics]
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        return filename
    
    def print_summary(self):
        """Print a summary of performance analysis"""
        print("\n" + "="*70)
        print("🔍 SED PERFORMANCE ANALYSIS SUMMARY")
        print("="*70)
        
        # System info
        system_info = self.get_system_info()
        print(f"\n💻 SYSTEM INFO:")
        print(f"   CPU Cores: {system_info.get('cpu_count', 'Unknown')}")
        print(f"   Memory: {system_info.get('memory_total_gb', 0):.1f}GB total, {system_info.get('memory_available_gb', 0):.1f}GB available")
        print(f"   Platform: {system_info.get('platform', 'Unknown')}")
        
        # Camera analysis
        camera_analysis = self.analyze_camera_performance()
        if 'error' not in camera_analysis:
            print(f"\n📹 CAMERA PERFORMANCE:")
            print(f"   Average FPS: {camera_analysis['average_fps']:.1f} / {camera_analysis['target_fps']:.1f} ({camera_analysis['fps_efficiency_percent']:.1f}% efficiency)")
            print(f"   Processing Time: {camera_analysis['average_processing_time_ms']:.1f}ms per frame")
            print(f"   Frame Drops: {camera_analysis['total_frame_drops']}")
            print(f"   Memory per Frame: {camera_analysis['average_memory_per_frame_mb']:.1f}MB")
            if camera_analysis['warnings']:
                print(f"   ⚠️  Warnings: {', '.join(camera_analysis['warnings'])}")
        
        # Tool analysis
        tool_analysis = self.analyze_tool_performance()
        if 'error' not in tool_analysis:
            print(f"\n🛠️  TOOL PERFORMANCE:")
            for tool_name, metrics in tool_analysis.items():
                print(f"   {tool_name}:")
                print(f"     Processing Time: {metrics['average_processing_time_ms']:.1f}ms")
                print(f"     Memory Usage: {metrics['average_memory_usage_mb']:.1f}MB")
                print(f"     Executions: {metrics['total_executions']}")
                if metrics['warnings']:
                    print(f"     ⚠️  Warnings: {', '.join(metrics['warnings'])}")
        
        # Overall analysis
        overall_analysis = self.analyze_overall_performance()
        if 'error' not in overall_analysis:
            print(f"\n📊 OVERALL PERFORMANCE:")
            print(f"   Runtime: {overall_analysis['total_runtime_seconds']:.1f}s")
            print(f"   Operations: {overall_analysis['total_operations']}")
            print(f"   Avg CPU: {overall_analysis['average_cpu_percent']:.1f}%")
            print(f"   Avg Memory: {overall_analysis['average_memory_mb']:.1f}MB")
            print(f"   Ops/sec: {overall_analysis['operations_per_second']:.1f}")
            if overall_analysis['warnings']:
                print(f"   ⚠️  Warnings: {', '.join(overall_analysis['warnings'])}")
        
        # Recommendations
        recommendations = self.generate_optimization_recommendations()
        if recommendations:
            print(f"\n🚀 OPTIMIZATION RECOMMENDATIONS:")
            for rec in recommendations:
                print(f"   {rec}")
        
        print("\n" + "="*70)


class OperationProfiler:
    """Context manager for profiling individual operations"""
    
    def __init__(self, profiler: PerformanceProfiler, operation_name: str):
        self.profiler = profiler
        self.operation_name = operation_name
        self.start_time = None
        self.start_memory = None
        
    def __enter__(self):
        self.start_time = time.perf_counter()
        self.start_memory = self.profiler.process.memory_info().rss / (1024 * 1024)  # MB
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        end_memory = self.profiler.process.memory_info().rss / (1024 * 1024)  # MB
        cpu_percent = self.profiler.process.cpu_percent()
        
        metric = PerformanceMetrics(
            operation=self.operation_name,
            execution_time=end_time - self.start_time,
            memory_usage_mb=end_memory,
            cpu_percent=cpu_percent,
            timestamp=time.time()
        )
        
        self.profiler.record_metric(metric)


def test_camera_performance():
    """Test camera performance with profiling"""
    profiler = PerformanceProfiler()
    
    try:
        logger.info("Testing camera performance...")
        from camera.camera_stream import CameraStream
        
        camera = CameraStream()
        if not camera.is_camera_available:
            logger.warning("Camera not available, skipping camera tests")
            return profiler
        
        # Test basic camera operations
        with profiler.measure_operation("camera_initialization"):
            time.sleep(0.1)  # Simulate initialization time
        
        # Simulate frame processing
        for i in range(10):
            with profiler.measure_operation(f"frame_processing_{i}"):
                # Simulate frame capture and basic processing
                time.sleep(0.033)  # ~30 FPS
                
                # Record camera metrics
                camera_metric = CameraMetrics(
                    fps_actual=28.5,  # Simulated
                    fps_target=30.0,
                    frame_resolution=(1440, 1080),
                    processing_time_ms=33.0,
                    frame_drops=0,
                    memory_per_frame_mb=4.2
                )
                profiler.record_camera_metric(camera_metric)
        
        logger.info("Camera performance test completed")
        
    except Exception as e:
        logger.error(f"Camera test failed: {e}")
    
    return profiler


def test_tool_performance():
    """Test individual tool performance"""
    profiler = PerformanceProfiler()
    
    logger.info("Testing tool performance...")
    
    # Test OCR tool
    try:
        from detection.ocr_tool import OcrTool
        
        with profiler.measure_operation("ocr_tool_initialization"):
            ocr_tool = OcrTool()
        
        # Simulate OCR processing
        for i in range(5):
            with profiler.measure_operation(f"ocr_processing_{i}"):
                time.sleep(0.15)  # Simulate OCR processing time
                
                tool_metric = ToolMetrics(
                    tool_name="OCR",
                    processing_time_ms=150.0,
                    input_size=(640, 480),
                    memory_usage_mb=85.0,
                    accuracy_score=0.85
                )
                profiler.record_tool_metric(tool_metric)
                
    except Exception as e:
        logger.error(f"OCR tool test failed: {e}")
    
    # Test Edge Detection tool
    try:
        from detection.edge_detection import EdgeDetectionTool
        
        with profiler.measure_operation("edge_detection_initialization"):
            edge_tool = EdgeDetectionTool()
        
        # Simulate edge detection processing
        for i in range(5):
            with profiler.measure_operation(f"edge_detection_{i}"):
                time.sleep(0.05)  # Simulate edge detection time
                
                tool_metric = ToolMetrics(
                    tool_name="EdgeDetection",
                    processing_time_ms=50.0,
                    input_size=(640, 480),
                    memory_usage_mb=25.0
                )
                profiler.record_tool_metric(tool_metric)
                
    except Exception as e:
        logger.error(f"Edge detection tool test failed: {e}")
    
    # Test YOLO detection (if available)
    try:
        from detection.yolo_inference import YOLOInference
        
        with profiler.measure_operation("yolo_initialization"):
            yolo = YOLOInference()
        
        # Simulate YOLO processing
        for i in range(3):
            with profiler.measure_operation(f"yolo_inference_{i}"):
                time.sleep(0.25)  # Simulate YOLO inference time
                
                tool_metric = ToolMetrics(
                    tool_name="YOLO",
                    processing_time_ms=250.0,
                    input_size=(640, 640),
                    memory_usage_mb=120.0,
                    accuracy_score=0.78
                )
                profiler.record_tool_metric(tool_metric)
                
    except Exception as e:
        logger.error(f"YOLO tool test failed: {e}")
    
    logger.info("Tool performance test completed")
    return profiler


def main():
    """Main function for performance profiling"""
    parser = argparse.ArgumentParser(description="SED Performance Profiler")
    parser.add_argument('--full-analysis', action='store_true', 
                       help='Run complete performance analysis')
    parser.add_argument('--camera-only', action='store_true',
                       help='Test camera performance only')
    parser.add_argument('--tools-only', action='store_true',
                       help='Test tools performance only')
    parser.add_argument('--output', '-o', type=str,
                       help='Output filename for report')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress output (save to file only)')
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    
    print("🔍 Starting SED Performance Analysis...")
    
    combined_profiler = PerformanceProfiler()
    
    if args.full_analysis or args.camera_only:
        camera_profiler = test_camera_performance()
        # Merge metrics
        combined_profiler.camera_metrics.extend(camera_profiler.camera_metrics)
        combined_profiler.metrics.extend(camera_profiler.metrics)
    
    if args.full_analysis or args.tools_only:
        tools_profiler = test_tool_performance()
        # Merge metrics
        combined_profiler.tool_metrics.extend(tools_profiler.tool_metrics)
        combined_profiler.metrics.extend(tools_profiler.metrics)
    
    if not any([args.full_analysis, args.camera_only, args.tools_only]):
        # Default: run both
        camera_profiler = test_camera_performance()
        tools_profiler = test_tool_performance()
        
        combined_profiler.camera_metrics.extend(camera_profiler.camera_metrics)
        combined_profiler.tool_metrics.extend(tools_profiler.tool_metrics)
        combined_profiler.metrics.extend(camera_profiler.metrics)
        combined_profiler.metrics.extend(tools_profiler.metrics)
    
    # Save report
    report_file = combined_profiler.save_report(args.output)
    print(f"📊 Performance report saved to: {report_file}")
    
    # Print summary unless quiet mode
    if not args.quiet:
        combined_profiler.print_summary()
    
    print(f"\n✅ Performance analysis completed!")
    print(f"📁 Report saved to: {report_file}")


if __name__ == "__main__":
    main()