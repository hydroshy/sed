"""
Simplified Detect Tool Manager - No draw area functionality
Manages model selection and class/threshold configuration UI
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional
from PyQt5.QtWidgets import QScrollArea, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal

from tools.detection.model_manager import ModelManager

logger = logging.getLogger(__name__)


class DetectToolManager:
    """Simplified manager for Detect Tool UI components - No draw area"""
    
    def __init__(self, main_window):
        """
        Initialize DetectToolManager
        
        Args:
            main_window: Reference to MainWindow instance
        """
        self.main_window = main_window
        self.model_manager = ModelManager()
        
        # Current selections
        self.current_model = None
        self.selected_classes = []  # List of selected class names
        self.loading_config = False  # Flag to prevent signal recursion during config loading
        
        # UI components
        self.algorithm_combo = None
        self.classification_combo = None
        self.add_classification_btn = None
        self.remove_classification_btn = None
        self.classification_scroll_area = None
        self.classification_model = None  # QStandardItemModel for QTableView
        self.classification_table = None  # QTableView for displaying classes and thresholds
        
        logger.info("DetectToolManager (Simplified) initialized")
    
    def _setup_classification_table(self):
        """Setup the QStandardItemModel for the classification QTableView"""
        from PyQt5.QtGui import QStandardItemModel
        
        self.classification_model = QStandardItemModel(0, 2)
        self.classification_model.setHorizontalHeaderLabels(["Class Name", "Threshold"])
        
        if self.classification_table:
            self.classification_table.setModel(self.classification_model)
            self.classification_table.setColumnWidth(0, 150)
            self.classification_table.setColumnWidth(1, 80)
            self.classification_table.setEditTriggers(
                self.classification_table.DoubleClicked | self.classification_table.SelectedClicked
            )
            logger.info("Classification table setup completed")
        else:
            logger.warning("classification_table (QTableView) is not set!")
    
    def setup_ui_components(self, algorithm_combo, classification_combo, add_btn, remove_btn, scroll_area, table_view=None):
        """
        Setup UI components for detect tool manager
        
        Args:
            algorithm_combo: QComboBox for model selection
            classification_combo: QComboBox for class selection
            add_btn: QPushButton to add class
            remove_btn: QPushButton to remove class
            scroll_area: QScrollArea for class list (kept for compatibility)
            table_view: QTableView for class/threshold configuration
        """
        self.algorithm_combo = algorithm_combo
        self.classification_combo = classification_combo
        self.add_classification_btn = add_btn
        self.remove_classification_btn = remove_btn
        self.classification_scroll_area = scroll_area
        self.classification_table = table_view
        
        logger.info("Simplified DetectToolManager UI components setup started")
        
        # Setup table view
        self._setup_classification_table()
        
        # Connect signals
        self._connect_signals()
        
        # Load models
        self.load_available_models()
        
        logger.info("Simplified DetectToolManager UI components setup completed")
    
    def _connect_signals(self):
        """Connect UI signals to handlers"""
        if self.algorithm_combo:
            self.algorithm_combo.currentTextChanged.connect(self._on_model_changed)
            self.algorithm_combo.currentIndexChanged.connect(self._on_model_index_changed)
            logger.info("Connected algorithm combo signals")
        
        if self.add_classification_btn:
            self.add_classification_btn.clicked.connect(self._on_add_classification)
            logger.info("Connected add classification button signal")
        
        if self.remove_classification_btn:
            self.remove_classification_btn.clicked.connect(self._on_remove_classification)
            logger.info("Connected remove classification button signal")
    
    def _force_refresh_connections(self):
        """Force refresh all signal connections - called when switching to detect page"""
        logger.info("Force refreshing DetectToolManager connections...")
        # Simply reconnect all signals
        self._connect_signals()
        logger.info("DetectToolManager connections refreshed")
    
    def load_available_models(self):
        """Load available ONNX models into algorithm combo box"""
        if self.algorithm_combo is None:
            logger.warning("Algorithm combo box not available")
            return
        
        try:
            # Clear existing items
            self.algorithm_combo.clear()
            
            # Get available models
            models = self.model_manager.get_available_models()
            
            if not models:
                self.algorithm_combo.addItem("No models found")
                logger.warning("No ONNX models found in models directory")
                return
            
            # Add default item
            self.algorithm_combo.addItem("Select Model...")
            
            # Add models to combo box
            for model in models:
                self.algorithm_combo.addItem(model)
            
            self.algorithm_combo.setEnabled(True)
            
            logger.info(f"Loaded {len(models)} models into algorithm combo box")
            
        except Exception as e:
            logger.error(f"Error loading available models: {e}")
            if self.algorithm_combo:
                self.algorithm_combo.clear()
                self.algorithm_combo.addItem("Error loading models")
    
    def _on_model_index_changed(self, index: int):
        """Handle model selection change by index"""
        logger.debug(f"Model index changed to {index}")
        
        if self.loading_config:
            logger.debug("Skipping signal - currently loading config")
            return
        
        if not self.algorithm_combo or index < 0:
            return
        
        model_name = self.algorithm_combo.itemText(index)
        self._on_model_changed(model_name)
    
    def _on_model_changed(self, model_name: str):
        """Handle model selection change"""
        logger.info(f"Model changed to: {model_name}")
        
        # Note: We now allow processing even if loading_config=True
        # because we explicitly call this during config loading
        # This was causing model classes to not load during edit
        
        # Handle invalid selections
        if not model_name or model_name in ["Select Model...", "No models found", "Error loading models"]:
            logger.info("Clearing classification combo - no valid model selected")
            self.current_model = None
            self._clear_classification_combo()
            return
        
        try:
            # Get model info
            model_info = self.model_manager.get_model_info(model_name)
            if not model_info:
                logger.error(f"Could not load model info for: {model_name}")
                self._clear_classification_combo()
                return
            
            self.current_model = model_info
            logger.info(f"Loaded model: {model_name} with {len(model_info['classes'])} classes")
            
            # Load classes into classification combo
            self._load_model_classes(model_info['classes'])
            
        except Exception as e:
            logger.error(f"Error handling model change: {e}")
            self._clear_classification_combo()
    
    def _load_model_classes(self, classes: List[str]):
        """Load model classes into classification combo box"""
        if self.classification_combo is None:
            logger.warning("Classification combo box not available")
            return
        
        try:
            # Clear existing items
            self.classification_combo.clear()
            
            # Add default item
            self.classification_combo.addItem("Select Class...")
            
            # Add all classes
            for class_name in classes:
                self.classification_combo.addItem(class_name)
            
            self.classification_combo.setEnabled(True)
            
            logger.info(f"Loaded {len(classes)} classes into classification combo box")
            
        except Exception as e:
            logger.error(f"Error loading model classes: {e}")
    
    def _clear_classification_combo(self):
        """Clear classification combo box"""
        if self.classification_combo:
            self.classification_combo.clear()
            self.classification_combo.addItem("No model selected")
            logger.debug("Classification combo cleared")
    
    def _on_add_classification(self):
        """Handle add classification button click"""
        if not self.classification_combo or not self.classification_table or self.classification_model is None:
            logger.warning("Required UI components not available")
            return
        
        try:
            selected_class = self.classification_combo.currentText()
            
            # Validate selection
            if not selected_class or selected_class == "Select Class...":
                logger.warning("No class selected for addition")
                return
            
            # Check if class already exists in table
            for row in range(self.classification_model.rowCount()):
                item = self.classification_model.item(row, 0)
                if item is not None and item.text() == selected_class:
                    logger.warning(f"Class '{selected_class}' already added")
                    return
            
            # Add class to table with default threshold
            from PyQt5.QtGui import QStandardItem
            
            class_item = QStandardItem(selected_class)
            class_item.setEditable(False)
            
            threshold_item = QStandardItem("0.5")  # Default threshold
            
            self.classification_model.appendRow([class_item, threshold_item])
            
            # Add to selected classes list
            if selected_class not in self.selected_classes:
                self.selected_classes.append(selected_class)
            
            # Reset combo box to default
            self.classification_combo.setCurrentIndex(0)
            
            logger.info(f"Added class: {selected_class}")
            
        except Exception as e:
            logger.error(f"Error adding classification: {e}")
    
    def _on_remove_classification(self):
        """Handle remove classification button click"""
        if not self.classification_table or self.classification_model is None:
            logger.warning("Required UI components not available")
            return
        
        try:
            selected_rows = self.classification_table.selectionModel().selectedRows()
            
            if not selected_rows:
                logger.warning("No class selected for removal")
                return
            
            # Remove rows in reverse order to maintain correct indices
            for index in sorted(selected_rows, key=lambda x: x.row(), reverse=True):
                row = index.row()
                
                # Get class name before removing
                class_item = self.classification_model.item(row, 0)
                if class_item and class_item.text() in self.selected_classes:
                    self.selected_classes.remove(class_item.text())
                    logger.info(f"Removed class: {class_item.text()}")
                
                # Remove row from model
                self.classification_model.removeRow(row)
            
            logger.info(f"Removed {len(selected_rows)} class(es)")
            
        except Exception as e:
            logger.error(f"Error removing classification: {e}")
    
    def get_selected_classes(self) -> List[str]:
        """Get list of currently selected classes"""
        return self.selected_classes.copy()
    
    def get_current_model(self) -> Optional[Dict]:
        """Get current model info"""
        return self.current_model
    
    def get_class_thresholds(self) -> Dict[str, float]:
        """Get current class thresholds from the table"""
        thresholds = {}
        
        try:
            if self.classification_model is None:
                logger.warning("Classification model not available")
                return thresholds
            
            logger.info(f"Reading thresholds from table - Rows: {self.classification_model.rowCount()}")  # ✅ Debug
            
            for row in range(self.classification_model.rowCount()):
                class_item = self.classification_model.item(row, 0)
                threshold_item = self.classification_model.item(row, 1)
                
                if class_item and threshold_item:
                    class_name = class_item.text()
                    
                    try:
                        threshold = float(threshold_item.text())
                    except ValueError:
                        threshold = 0.5  # Default threshold
                    
                    thresholds[class_name] = threshold
                    logger.info(f"  Row {row}: {class_name} = {threshold}")  # ✅ Debug
        
        except Exception as e:
            logger.error(f"Error getting class thresholds: {e}")
        
        logger.info(f"Final thresholds dict: {thresholds}")  # ✅ Debug
        return thresholds
    
    def set_selected_classes(self, classes: List[str]):
        """Set selected classes with default threshold"""
        try:
            # Clear current selection
            self.selected_classes.clear()
            
            # Clear the table model
            if self.classification_model is not None:
                self.classification_model.clear()
                self.classification_model.setHorizontalHeaderLabels(["Class Name", "Threshold"])
            
            # Add new classes
            from PyQt5.QtGui import QStandardItem
            
            for class_name in classes:
                if class_name not in self.selected_classes:
                    self.selected_classes.append(class_name)
                    
                    # Add to table model if it exists
                    if self.classification_model is not None:
                        class_item = QStandardItem(class_name)
                        class_item.setEditable(False)
                        threshold_item = QStandardItem("0.5")  # Default threshold
                        self.classification_model.appendRow([class_item, threshold_item])
            
            logger.info(f"Set selected classes: {classes}")
            
        except Exception as e:
            logger.error(f"Error setting selected classes: {e}")
    
    def load_selected_classes_with_thresholds(self, classes: List[str], class_thresholds: Dict[str, float]):
        """Load selected classes with their thresholds into the classification table"""
        try:
            # Clear current selection
            self.selected_classes.clear()
            
            # Clear the table model
            if self.classification_model is not None:
                self.classification_model.clear()
                self.classification_model.setHorizontalHeaderLabels(["Class Name", "Threshold"])
            else:
                logger.warning("Classification model is None, cannot load class thresholds")
                return
            
            # Add classes with their specific thresholds
            from PyQt5.QtGui import QStandardItem
            
            for class_name in classes:
                if class_name not in self.selected_classes:
                    self.selected_classes.append(class_name)
                    
                    # Get threshold for this class, default to 0.5 if not specified
                    threshold = class_thresholds.get(class_name, 0.5)
                    
                    # Add to table model
                    class_item = QStandardItem(class_name)
                    class_item.setEditable(False)
                    threshold_item = QStandardItem(str(threshold))
                    self.classification_model.appendRow([class_item, threshold_item])
            
            logger.info(f"Loaded {len(classes)} classes with thresholds: {class_thresholds}")
            
        except Exception as e:
            logger.error(f"Error loading classes with thresholds: {e}")
    
    def set_current_model(self, model_name: str):
        """Set current model (for loading tool configuration)"""
        try:
            if self.algorithm_combo:
                # Temporarily block signals to prevent multiple triggers
                self.algorithm_combo.blockSignals(True)
                
                # Find and select the model in combo box
                index = self.algorithm_combo.findText(model_name)
                if index >= 0:
                    self.algorithm_combo.setCurrentIndex(index)
                    logger.info(f"Set current model: {model_name}")
                    
                    # Re-enable signals and manually trigger the model change
                    self.algorithm_combo.blockSignals(False)
                    self._on_model_changed(model_name)
                else:
                    self.algorithm_combo.blockSignals(False)
                    logger.warning(f"Model not found in combo box: {model_name}")
            
        except Exception as e:
            # Ensure signals are re-enabled even if error occurs
            if self.algorithm_combo:
                self.algorithm_combo.blockSignals(False)
            logger.error(f"Error setting current model: {e}")
    
    def get_tool_config(self) -> Dict:
        """Get current tool configuration (simplified - no detection area)"""
        # Get class names from current model
        class_names = []
        if self.current_model and 'classes' in self.current_model:
            class_names = self.current_model['classes']
        
        # Get current thresholds from table
        thresholds = self.get_class_thresholds()
        
        config = {
            'model_name': self.current_model['name'] if self.current_model else None,
            'model_path': self.current_model['path'] if self.current_model else None,
            'class_names': class_names,  # Add class_names from model
            'selected_classes': self.selected_classes.copy(),
            'class_thresholds': thresholds,
            'num_classes': len(self.selected_classes),
            'confidence_threshold': 0.5,  # Default confidence threshold
            'nms_threshold': 0.45,  # Default NMS threshold
            'imgsz': 640,  # Image size for YOLO
            'detection_region': None,  # DetectTool only needs camera images
            'detection_area': None,  # Not used by DetectTool
            'visualize_results': True,
            'show_confidence': True,
            'show_class_names': True
        }
        
        logger.debug(f"Generated config - Model: {config['model_name']}, Selected classes: {config['selected_classes']}, Thresholds: {config['class_thresholds']}")
        logger.info(f"get_tool_config() - Thresholds from table: {thresholds}")  # ✅ Debug
        
        return config
    
    def load_tool_config(self, config: Dict):
        """Load tool configuration (simplified - no detection area)"""
        try:
            logger.info(f"Loading tool config: {config}")
            
            # Set model if specified
            if 'model_name' in config and config['model_name']:
                model_name = config['model_name']
                logger.info(f"Setting model: {model_name}")
                
                # First, set the combo box to the correct model
                if self.algorithm_combo:
                    index = self.algorithm_combo.findText(model_name)
                    if index >= 0:
                        self.algorithm_combo.blockSignals(True)
                        self.algorithm_combo.setCurrentIndex(index)
                        self.algorithm_combo.blockSignals(False)
                        logger.info(f"Set algorithm combo to: {model_name} (index {index})")
                    else:
                        logger.warning(f"Model {model_name} not found in combo box")
                
                # Now manually trigger model change to load classes
                # (this will run without loading_config flag blocking it)
                self._on_model_changed(model_name)
                
                # Give UI time to update
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()
            
            # Handle selected classes with thresholds if they exist
            if 'selected_classes' in config and config['selected_classes']:
                selected_classes = config['selected_classes']
                class_thresholds = config.get('class_thresholds', {})
                
                logger.info(f"Loading selected classes: {selected_classes}")
                logger.info(f"Class thresholds: {class_thresholds}")
                
                # Load classes with their thresholds
                self.load_selected_classes_with_thresholds(selected_classes, class_thresholds)
                
                logger.info(f"Loaded {len(selected_classes)} classes with thresholds")
            else:
                logger.warning("No selected_classes in config to load")
            
            logger.info("Tool configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading tool configuration: {e}")
            import traceback
            traceback.print_exc()
        finally:
            pass
    
    def create_detect_tool_job(self):
        """Create DetectTool job from current configuration"""
        try:
            logger.info("=" * 80)
            logger.info("🔧 create_detect_tool_job() START")
            logger.info("=" * 80)
            
            from tools.detection.detect_tool import create_detect_tool_from_manager_config
            
            # Get current tool configuration
            config = self.get_tool_config()
            logger.info(f"✓ Got config: model={config['model_name']}, classes={len(config['selected_classes'])}")
            
            # Validate configuration
            if (not config['model_name'] or not config['model_path'] or
                config['model_name'] in ["Select Model...", "No models found", "Error loading models"]):
                logger.error("❌ Cannot create DetectTool: No model selected")
                return None
            
            if not config['selected_classes']:
                logger.warning("⚠️  No classes selected for detection")
            
            # Create detect tool
            logger.info(f"📦 Creating DetectTool with config...")
            detect_tool = create_detect_tool_from_manager_config(config)
            logger.info(f"✅ Created DetectTool job - Model: {config['model_name']}, Classes: {len(config['selected_classes'])}")
            logger.info(f"   Tool display_name: {detect_tool.display_name}")
            logger.info(f"   Tool is_initialized: {detect_tool.is_initialized}")
            logger.info("=" * 80)
            
            return detect_tool
            
        except ImportError as e:
            logger.error(f"❌ Cannot create DetectTool: Import error - {e}")
            import traceback
            traceback.print_exc()
            return None
        except Exception as e:
            logger.error(f"❌ Error creating DetectTool job: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def apply_detect_tool_to_job(self):
        """Apply current detect tool configuration to job manager (DetectTool + ResultTool)"""
        try:
            logger.info("=" * 80)
            logger.info("🚀 apply_detect_tool_to_job() START")
            logger.info("=" * 80)
            
            # Create detect tool
            logger.info("📦 Creating DetectTool...")
            detect_tool = self.create_detect_tool_job()
            if not detect_tool:
                logger.error("❌ Failed to create DetectTool job")
                return False
            
            logger.info(f"✅ DetectTool created: {detect_tool.name} (ID: {detect_tool.tool_id})")
            
            # Create result tool
            logger.info("📦 Creating ResultTool...")
            result_tool = self.create_result_tool()
            if not result_tool:
                logger.warning("⚠️  Failed to create ResultTool, continuing without it")
                result_tool = None
            else:
                logger.info(f"✅ ResultTool created: {result_tool.name}")
            
            # Add to job manager via main window
            if hasattr(self.main_window, 'job_manager'):
                job_manager = self.main_window.job_manager
                current_job = job_manager.get_current_job()
                
                if current_job is None:
                    # Create new job with detect tool
                    logger.info("ℹ️  No current job, creating new one...")
                    from job.job_manager import Job
                    job_manager.add_job(Job("Detection Job"))
                    current_job = job_manager.get_current_job()
                    logger.info(f"✅ Created new job: {current_job.name}")
                
                if current_job:
                    # Add detect tool to current job
                    logger.info(f"🔗 Adding DetectTool to job (current tools: {len(current_job.tools)})...")
                    current_job.add_tool(detect_tool)
                    logger.info(f"✅ Added DetectTool to job. Current tools: {len(current_job.tools)}")
                    
                    # Add result tool if created successfully
                    if result_tool:
                        logger.info(f"🔗 Adding ResultTool to job...")
                        current_job.add_tool(result_tool)
                        logger.info(f"✅ Added ResultTool to job. Current tools: {len(current_job.tools)}")
                    
                    logger.info(f"   Workflow: {[tool.name for tool in current_job.tools]}")
                    logger.info("=" * 80)
                    
                    return True
                else:
                    logger.error("❌ No current job available")
                    return False
            else:
                logger.error("❌ Job manager not available")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error applying DetectTool to job: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_result_tool(self):
        """Create ResultTool (separate from DetectTool)"""
        try:
            from tools.result_tool import ResultTool
            
            # Create result tool
            result_tool = ResultTool("Result Tool")
            result_tool.setup_config()
            
            logger.info(f"Created ResultTool: {result_tool.name}")
            return result_tool
            
        except ImportError as e:
            logger.error(f"Cannot create ResultTool: Import error - {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating ResultTool: {e}")
            return None
    
    def apply_result_tool_to_job(self):
        """Apply ResultTool to job manager (separate operation)"""
        try:
            # Create result tool
            result_tool = self.create_result_tool()
            if not result_tool:
                logger.error("Failed to create ResultTool")
                return False
            
            # Add to job manager
            if hasattr(self.main_window, 'job_manager'):
                job_manager = self.main_window.job_manager
                current_job = job_manager.get_current_job()
                
                if current_job is None:
                    logger.error("No current job available - create DetectTool first")
                    return False
                
                if current_job:
                    # Add result tool to current job
                    current_job.add_tool(result_tool)
                    logger.info(f"✓ Added ResultTool to job. Current tools: {len(current_job.tools)}")
                    logger.info(f"  Workflow: {[tool.name for tool in current_job.tools]}")
                    
                    return True
                else:
                    logger.error("No current job available")
                    return False
            else:
                logger.error("Job manager not available")
                return False
                
        except Exception as e:
            logger.error(f"Error applying ResultTool to job: {e}")
            return False
