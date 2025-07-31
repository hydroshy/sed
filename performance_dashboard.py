#!/usr/bin/env python3
"""
Real-time Performance Monitor for SED
=====================================

This script monitors the SED application performance in real-time and provides
suggestions for optimization. It integrates with the existing GUI and provides
a performance dashboard.

Usage:
    python performance_dashboard.py
"""

import sys
import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QProgressBar, QPushButton, QTextEdit, 
                            QGroupBox, QGridLayout, QTabWidget, QScrollArea,
                            QFrame, QSplitter)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QColor, QPalette

try:
    from utils.performance_monitor import PerformanceMonitor, get_performance_monitor
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PerformanceWidget(QWidget):
    """Widget for displaying performance metrics"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel(self.title)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Content area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        layout.addWidget(self.content_widget)
        
        self.setLayout(layout)
        
    def add_metric(self, name: str, value: str, warning: bool = False):
        """Add a metric display"""
        metric_layout = QHBoxLayout()
        
        name_label = QLabel(f"{name}:")
        name_label.setMinimumWidth(120)
        
        value_label = QLabel(value)
        if warning:
            value_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            value_label.setStyleSheet("color: green;")
            
        metric_layout.addWidget(name_label)
        metric_layout.addWidget(value_label)
        metric_layout.addStretch()
        
        self.content_layout.addLayout(metric_layout)
        
    def add_progress_bar(self, name: str, value: float, maximum: float = 100.0):
        """Add a progress bar metric"""
        metric_layout = QVBoxLayout()
        
        name_label = QLabel(name)
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(int(maximum))
        progress_bar.setValue(int(value))
        
        # Color coding
        if value > maximum * 0.8:
            progress_bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")
        elif value > maximum * 0.6:
            progress_bar.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
        else:
            progress_bar.setStyleSheet("QProgressBar::chunk { background-color: green; }")
            
        metric_layout.addWidget(name_label)
        metric_layout.addWidget(progress_bar)
        
        self.content_layout.addLayout(metric_layout)
        
    def clear_metrics(self):
        """Clear all metrics"""
        for i in reversed(range(self.content_layout.count())):
            child = self.content_layout.takeAt(i)
            if child.widget():
                child.widget().deleteLater()


class PerformanceDashboard(QWidget):
    """Main performance dashboard widget"""
    
    def __init__(self):
        super().__init__()
        self.monitor = None
        self.update_timer = QTimer()
        self.setup_ui()
        self.setup_monitoring()
        
    def setup_ui(self):
        self.setWindowTitle("SED Performance Dashboard")
        self.setGeometry(100, 100, 1000, 700)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("🔍 SED Performance Dashboard")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(16)
        title_label.setFont(title_font)
        
        self.status_label = QLabel("Monitoring: Disconnected")
        self.status_label.setStyleSheet("color: red;")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        
        main_layout.addLayout(header_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Monitoring")
        self.start_btn.clicked.connect(self.start_monitoring)
        
        self.stop_btn = QPushButton("Stop Monitoring")
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setEnabled(False)
        
        self.reset_btn = QPushButton("Reset Stats")
        self.reset_btn.clicked.connect(self.reset_stats)
        
        self.export_btn = QPushButton("Export Report")
        self.export_btn.clicked.connect(self.export_report)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
        # Create tabs
        self.tab_widget = QTabWidget()
        
        # Overview tab
        self.overview_tab = self.create_overview_tab()
        self.tab_widget.addTab(self.overview_tab, "Overview")
        
        # Camera tab
        self.camera_tab = self.create_camera_tab()
        self.tab_widget.addTab(self.camera_tab, "Camera")
        
        # Tools tab
        self.tools_tab = self.create_tools_tab()
        self.tab_widget.addTab(self.tools_tab, "Tools")
        
        # System tab
        self.system_tab = self.create_system_tab()
        self.tab_widget.addTab(self.system_tab, "System")
        
        # Recommendations tab
        self.recommendations_tab = self.create_recommendations_tab()
        self.tab_widget.addTab(self.recommendations_tab, "Recommendations")
        
        main_layout.addWidget(self.tab_widget)
        
        self.setLayout(main_layout)
        
    def create_overview_tab(self):
        """Create overview tab"""
        tab = QWidget()
        layout = QGridLayout()
        
        # Quick stats
        self.fps_widget = PerformanceWidget("📹 Frame Rate")
        self.memory_widget = PerformanceWidget("💾 Memory Usage")
        self.cpu_widget = PerformanceWidget("⚡ CPU Usage")
        self.operations_widget = PerformanceWidget("🔧 Operations")
        
        layout.addWidget(self.fps_widget, 0, 0)
        layout.addWidget(self.memory_widget, 0, 1)
        layout.addWidget(self.cpu_widget, 1, 0)
        layout.addWidget(self.operations_widget, 1, 1)
        
        tab.setLayout(layout)
        return tab
        
    def create_camera_tab(self):
        """Create camera performance tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        self.camera_stats_widget = PerformanceWidget("📷 Camera Performance")
        layout.addWidget(self.camera_stats_widget)
        
        tab.setLayout(layout)
        return tab
        
    def create_tools_tab(self):
        """Create tools performance tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Scroll area for tools
        scroll_area = QScrollArea()
        scroll_content = QWidget()
        self.tools_layout = QVBoxLayout(scroll_content)
        
        scroll_area.setWidget(scroll_content)
        scroll_area.setWidgetResizable(True)
        
        layout.addWidget(scroll_area)
        tab.setLayout(layout)
        return tab
        
    def create_system_tab(self):
        """Create system performance tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        self.system_stats_widget = PerformanceWidget("🖥️ System Performance")
        layout.addWidget(self.system_stats_widget)
        
        tab.setLayout(layout)
        return tab
        
    def create_recommendations_tab(self):
        """Create recommendations tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        label = QLabel("🚀 Performance Optimization Recommendations")
        label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(label)
        
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setReadOnly(True)
        layout.addWidget(self.recommendations_text)
        
        tab.setLayout(layout)
        return tab
        
    def setup_monitoring(self):
        """Setup performance monitoring"""
        if not MONITORING_AVAILABLE:
            self.status_label.setText("Monitoring: Not Available")
            self.start_btn.setEnabled(False)
            return
            
        try:
            self.monitor = get_performance_monitor()
            self.monitor.add_warning_callback(self.on_performance_warning)
            
            # Setup update timer
            self.update_timer.timeout.connect(self.update_display)
            
        except Exception as e:
            logger.error(f"Failed to setup monitoring: {e}")
            self.status_label.setText("Monitoring: Error")
            
    def start_monitoring(self):
        """Start performance monitoring"""
        if not self.monitor:
            return
            
        try:
            self.monitor.start_monitoring(interval=0.5)  # Update every 500ms
            self.update_timer.start(1000)  # Update UI every second
            
            self.status_label.setText("Monitoring: Active")
            self.status_label.setStyleSheet("color: green;")
            
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            
    def stop_monitoring(self):
        """Stop performance monitoring"""
        if not self.monitor:
            return
            
        try:
            self.monitor.stop_monitoring()
            self.update_timer.stop()
            
            self.status_label.setText("Monitoring: Stopped")
            self.status_label.setStyleSheet("color: orange;")
            
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {e}")
            
    def reset_stats(self):
        """Reset performance statistics"""
        if self.monitor:
            self.monitor.reset_stats()
            self.update_display()
            
    def export_report(self):
        """Export performance report"""
        if not self.monitor:
            return
            
        try:
            stats = self.monitor.export_stats()
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"sed_performance_dashboard_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(stats, f, indent=2, default=str)
                
            self.recommendations_text.append(f"\n✅ Report exported to: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to export report: {e}")
            self.recommendations_text.append(f"\n❌ Export failed: {e}")
            
    def on_performance_warning(self, warning_type: str, current_value: float, threshold: float):
        """Handle performance warnings"""
        warning_msg = f"⚠️ {warning_type.upper()}: {current_value:.1f} > {threshold:.1f}"
        self.recommendations_text.append(warning_msg)
        
    def update_display(self):
        """Update performance display"""
        if not self.monitor:
            return
            
        try:
            stats = self.monitor.get_current_stats()
            
            # Update overview
            self.update_overview(stats)
            
            # Update camera tab
            self.update_camera_display(stats)
            
            # Update tools tab
            self.update_tools_display(stats)
            
            # Update system tab
            self.update_system_display(stats)
            
            # Update recommendations
            self.update_recommendations()
            
        except Exception as e:
            logger.error(f"Failed to update display: {e}")
            
    def update_overview(self, stats: Dict[str, Any]):
        """Update overview tab"""
        frame_stats = stats.get('frame_stats')
        system_stats = stats.get('system_stats')
        operation_stats = stats.get('operation_stats', {})
        
        # Clear and update widgets
        self.fps_widget.clear_metrics()
        self.memory_widget.clear_metrics()
        self.cpu_widget.clear_metrics()
        self.operations_widget.clear_metrics()
        
        if frame_stats:
            self.fps_widget.add_metric("Current FPS", f"{frame_stats.fps_current:.1f}")
            self.fps_widget.add_metric("Average FPS", f"{frame_stats.fps_average:.1f}")
            self.fps_widget.add_metric("Frame Drops", str(frame_stats.frame_drops))
            self.fps_widget.add_metric("Total Frames", str(frame_stats.total_frames))
            
        if system_stats:
            memory_current = system_stats.get('memory_current_mb', 0)
            memory_peak = system_stats.get('memory_peak_mb', 0)
            cpu_current = system_stats.get('cpu_current_percent', 0)
            cpu_peak = system_stats.get('cpu_peak_percent', 0)
            
            self.memory_widget.add_metric("Current", f"{memory_current:.1f} MB")
            self.memory_widget.add_metric("Peak", f"{memory_peak:.1f} MB")
            self.memory_widget.add_progress_bar("Memory Usage", memory_current, 500)
            
            self.cpu_widget.add_metric("Current", f"{cpu_current:.1f}%")
            self.cpu_widget.add_metric("Peak", f"{cpu_peak:.1f}%")
            self.cpu_widget.add_progress_bar("CPU Usage", cpu_current, 100)
            
        # Operations
        total_ops = sum(op.count for op in operation_stats.values() if hasattr(op, 'count'))
        self.operations_widget.add_metric("Total Operations", str(total_ops))
        
        if operation_stats:
            slowest_op = max(operation_stats.values(), key=lambda x: x.avg_time, default=None)
            if slowest_op:
                self.operations_widget.add_metric("Slowest Operation", 
                                                f"{slowest_op.name}: {slowest_op.avg_time*1000:.1f}ms")
                
    def update_camera_display(self, stats: Dict[str, Any]):
        """Update camera tab"""
        frame_stats = stats.get('frame_stats')
        
        self.camera_stats_widget.clear_metrics()
        
        if frame_stats:
            self.camera_stats_widget.add_metric("Current FPS", f"{frame_stats.fps_current:.1f}")
            self.camera_stats_widget.add_metric("Average FPS", f"{frame_stats.fps_average:.1f}")
            self.camera_stats_widget.add_metric("Frame Time", f"{frame_stats.frame_time_ms:.1f} ms")
            self.camera_stats_widget.add_metric("Processing Time", f"{frame_stats.processing_time_ms:.1f} ms")
            self.camera_stats_widget.add_metric("Frame Drops", str(frame_stats.frame_drops))
            self.camera_stats_widget.add_metric("Total Frames", str(frame_stats.total_frames))
            
            # Add progress bars
            fps_efficiency = (frame_stats.fps_current / 30.0) * 100 if frame_stats.fps_current > 0 else 0
            self.camera_stats_widget.add_progress_bar("FPS Efficiency", fps_efficiency, 100)
            
    def update_tools_display(self, stats: Dict[str, Any]):
        """Update tools tab"""
        operation_stats = stats.get('operation_stats', {})
        
        # Clear existing tool widgets
        for i in reversed(range(self.tools_layout.count())):
            child = self.tools_layout.takeAt(i)
            if child.widget():
                child.widget().deleteLater()
                
        # Add tool widgets
        for op_name, op_stats in operation_stats.items():
            if hasattr(op_stats, 'name'):
                tool_widget = PerformanceWidget(f"🛠️ {op_stats.name}")
                tool_widget.add_metric("Executions", str(op_stats.count))
                tool_widget.add_metric("Avg Time", f"{op_stats.avg_time*1000:.1f} ms")
                tool_widget.add_metric("Min Time", f"{op_stats.min_time*1000:.1f} ms")
                tool_widget.add_metric("Max Time", f"{op_stats.max_time*1000:.1f} ms")
                tool_widget.add_metric("Avg Memory", f"{op_stats.avg_memory_mb:.1f} MB")
                
                warning = op_stats.avg_time * 1000 > 100  # Warning if > 100ms
                if warning:
                    tool_widget.add_metric("Status", "⚠️ SLOW", warning=True)
                else:
                    tool_widget.add_metric("Status", "✅ OK")
                    
                self.tools_layout.addWidget(tool_widget)
                
    def update_system_display(self, stats: Dict[str, Any]):
        """Update system tab"""
        system_stats = stats.get('system_stats')
        
        self.system_stats_widget.clear_metrics()
        
        if system_stats:
            self.system_stats_widget.add_metric("Current Memory", f"{system_stats.get('memory_current_mb', 0):.1f} MB")
            self.system_stats_widget.add_metric("Average Memory", f"{system_stats.get('memory_average_mb', 0):.1f} MB")
            self.system_stats_widget.add_metric("Peak Memory", f"{system_stats.get('memory_peak_mb', 0):.1f} MB")
            self.system_stats_widget.add_metric("Current CPU", f"{system_stats.get('cpu_current_percent', 0):.1f}%")
            self.system_stats_widget.add_metric("Average CPU", f"{system_stats.get('cpu_average_percent', 0):.1f}%")
            self.system_stats_widget.add_metric("Peak CPU", f"{system_stats.get('cpu_peak_percent', 0):.1f}%")
            
    def update_recommendations(self):
        """Update recommendations tab"""
        if not self.monitor:
            return
            
        suggestions = self.monitor.get_optimization_suggestions()
        if suggestions:
            self.recommendations_text.clear()
            self.recommendations_text.append("🚀 PERFORMANCE OPTIMIZATION SUGGESTIONS:\n")
            for suggestion in suggestions:
                self.recommendations_text.append(f"• {suggestion}")
                
            self.recommendations_text.append("\n📋 GENERAL RECOMMENDATIONS:")
            self.recommendations_text.append("• Reduce camera resolution if real-time processing isn't critical")
            self.recommendations_text.append("• Use ROI (Region of Interest) for processing instead of full frames")
            self.recommendations_text.append("• Implement frame skipping for heavy operations")
            self.recommendations_text.append("• Consider multi-threading for parallel tool execution")
            self.recommendations_text.append("• Use caching for repeated operations")
            self.recommendations_text.append("• Monitor memory usage and implement buffer pooling")


def main():
    """Main function"""
    app = QApplication(sys.argv)
    app.setApplicationName("SED Performance Dashboard")
    
    # Set application style
    app.setStyle('Fusion')
    
    if not MONITORING_AVAILABLE:
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.warning(None, "Warning", 
                           "Performance monitoring module not available.\n"
                           "Some features may be limited.")
    
    dashboard = PerformanceDashboard()
    dashboard.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()