import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QScrollArea, QVBoxLayout, QWidget, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QStringListModel
from detection.model_manager import ModelManager

class DetectToolManager:
    """Manager for Detect Tool UI components and functionality"""
    
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
        
        # UI components will be set during setup
        self.algorithm_combo = None
        self.classification_combo = None
        self.add_classification_btn = None
        self.remove_classification_btn = None
        self.classification_scroll_area = None
        self.classification_list = None  # Custom list widget for selected classes
        
        logging.info("DetectToolManager initialized")
    
    def create_detect_tool_job(self):
        """Create DetectTool job from current configuration"""
        try:
            from detection.detect_tool import create_detect_tool_from_manager_config
            
            # Get current tool configuration
            config = self.get_tool_config()
            
            # Validate configuration
            if not config['model_name'] or not config['model_path']:
                logging.error("Cannot create DetectTool: No model selected")
                return None
            
            if not config['selected_classes']:
                logging.warning("No classes selected for detection")
            
            # Create detect tool
            detect_tool = create_detect_tool_from_manager_config(config)
            
            logging.info(f"Created DetectTool job - Model: {config['model_name']}, Classes: {len(config['selected_classes'])}")
            return detect_tool
            
        except ImportError:
            logging.error("Cannot create DetectTool: Job system not available")
            return None
        except Exception as e:
            logging.error(f"Error creating DetectTool job: {e}")
            return None
    
    def apply_detect_tool_to_job(self):
        """Apply current detect tool configuration to job manager"""
        try:
            # Create detect tool
            detect_tool = self.create_detect_tool_job()
            if not detect_tool:
                logging.error("Failed to create DetectTool job")
                return False
            
            # Add to job manager via main window
            if hasattr(self.main_window, 'job_manager'):
                # Get current job or create new one
                job_manager = self.main_window.job_manager
                current_job = job_manager.get_current_job()
                
                if current_job is None:
                    # Create new job with detect tool
                    job_manager.create_job("Detection Job")
                    current_job = job_manager.get_current_job()
                
                if current_job:
                    # Add detect tool to current job
                    current_job.add_tool(detect_tool)
                    logging.info(f"Added DetectTool to job: {current_job.name}")
                    return True
                else:
                    logging.error("No current job available")
                    return False
            else:
                logging.error("Job manager not available")
                return False
                
        except Exception as e:
            logging.error(f"Error applying DetectTool to job: {e}")
            return False
    
    def setup_ui_components(self, algorithm_combo, classification_combo, add_btn, remove_btn, scroll_area, list_view=None):
        """
        Setup UI components
        
        Args:
            algorithm_combo: QComboBox for algorithm selection
            classification_combo: QComboBox for class selection
            add_btn: QPushButton for adding classes
            remove_btn: QPushButton for removing classes
            scroll_area: QScrollArea for displaying selected classes
            list_view: QListView for displaying selected classes (optional, fallback to creating QListWidget)
        """
        self.algorithm_combo = algorithm_combo
        self.classification_combo = classification_combo
        self.add_classification_btn = add_btn
        self.remove_classification_btn = remove_btn
        self.classification_scroll_area = scroll_area
        self.classification_list = list_view  # Use provided list view if available
        
        # Debug logging for widget availability
        logging.info(f"DetectToolManager setup - Algorithm combo: {algorithm_combo is not None}")
        logging.info(f"DetectToolManager setup - Classification combo: {classification_combo is not None}")
        logging.info(f"DetectToolManager setup - Add button: {add_btn is not None}")
        logging.info(f"DetectToolManager setup - Remove button: {remove_btn is not None}")
        logging.info(f"DetectToolManager setup - Scroll area: {scroll_area is not None}")
        logging.info(f"DetectToolManager setup - List view: {list_view is not None}")
        
        # Setup classification list (use provided or create new)
        self._setup_classification_list()
        
        # Connect signals
        self._connect_signals()
        
        # Force refresh signal connections
        self._force_refresh_connections()
        
        # Initial load
        self.load_available_models()
        
        logging.info("DetectToolManager UI components setup completed")
    
    def _force_refresh_connections(self):
        """Force refresh signal connections to ensure they work"""
        if self.algorithm_combo:
            # Disconnect all existing connections first
            try:
                self.algorithm_combo.currentTextChanged.disconnect()
                self.algorithm_combo.currentIndexChanged.disconnect()
                self.algorithm_combo.activated.disconnect()
            except:
                pass  # Ignore if no connections exist
            
            # Reconnect signals
            self.algorithm_combo.currentTextChanged.connect(self._on_model_changed)
            self.algorithm_combo.currentIndexChanged.connect(self._on_model_index_changed)
            self.algorithm_combo.activated.connect(self._on_model_activated)
            
            logging.info("Force refreshed algorithm combo signal connections")
    
    def _setup_classification_list(self):
        """Setup the classification list widget inside scroll area"""
        # If we already have a list view, set up its model
        if self.classification_list:
            # QListView uses a model, set up a simple string list model
            from PyQt5.QtCore import QStringListModel
            self.classification_model = QStringListModel()
            self.classification_list.setModel(self.classification_model)
            logging.info("Classification list view setup completed with model")
            return
            
        # Fallback: create QListWidget inside scroll area if no ListView provided
        if not self.classification_scroll_area:
            logging.warning("No scroll area or list view available for classification list")
            return
            
        # Create a widget to hold the list
        container_widget = QWidget()
        layout = QVBoxLayout(container_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # Create list widget for selected classes
        from PyQt5.QtWidgets import QListWidget
        self.classification_list = QListWidget()
        self.classification_list.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(self.classification_list)
        
        # Set the container as the scroll area widget
        self.classification_scroll_area.setWidget(container_widget)
        self.classification_scroll_area.setWidgetResizable(True)
        
        logging.info("Classification list widget setup completed (fallback)")
    
    def _connect_signals(self):
        """Connect UI signals to handlers"""
        if self.algorithm_combo:
            # Connect multiple signals to ensure we catch all selection changes
            self.algorithm_combo.currentTextChanged.connect(self._on_model_changed)
            self.algorithm_combo.currentIndexChanged.connect(self._on_model_index_changed)
            self.algorithm_combo.activated.connect(self._on_model_activated)  # When user selects an item
            logging.info("Connected algorithm combo signals: currentTextChanged, currentIndexChanged, activated")
        
        if self.add_classification_btn:
            self.add_classification_btn.clicked.connect(self._on_add_classification)
        
        if self.remove_classification_btn:
            self.remove_classification_btn.clicked.connect(self._on_remove_classification)
        
        if self.classification_list:
            # Connect selection change signals (handle both QListView and QListWidget)
            if hasattr(self.classification_list, 'selectionModel'):
                # QListView
                self.classification_list.selectionModel().selectionChanged.connect(self._on_class_selection_changed)
            elif hasattr(self.classification_list, 'itemSelectionChanged'):
                # QListWidget  
                self.classification_list.itemSelectionChanged.connect(self._on_class_selection_changed)
        
        logging.info("DetectToolManager signals connected")
    
    def load_available_models(self):
        """Load available ONNX models into algorithm combo box"""
        logging.info("Loading available models...")
        logging.info(f"Algorithm combo widget in load: {self.algorithm_combo}")
        logging.info(f"Algorithm combo type: {type(self.algorithm_combo)}")
        
        if self.algorithm_combo is None:
            logging.warning("Algorithm combo box not available")
            return
        
        try:
            # Clear existing items
            self.algorithm_combo.clear()
            logging.info("Cleared algorithm combo box")
            
            # Get available models
            models = self.model_manager.get_available_models()
            logging.info(f"Found models: {models}")
            
            if not models:
                self.algorithm_combo.addItem("No models found")
                self.algorithm_combo.setEnabled(False)
                logging.warning("No ONNX models found in models directory")
                return
            
            # Add models to combo box
            self.algorithm_combo.addItem("Select Model...")  # Default item
            logging.info("Added default 'Select Model...' item")
            
            for model in models:
                self.algorithm_combo.addItem(model)
                logging.info(f"Added model to combo: {model}")
            
            self.algorithm_combo.setEnabled(True)
            
            # Verify items were added
            item_count = self.algorithm_combo.count()
            logging.info(f"Algorithm combo box now has {item_count} items")
            for i in range(item_count):
                logging.info(f"  Item {i}: {self.algorithm_combo.itemText(i)}")
            
            logging.info(f"Loaded {len(models)} models into algorithm combo box")
            
        except Exception as e:
            logging.error(f"Error loading available models: {e}")
            if self.algorithm_combo:
                self.algorithm_combo.clear()
                self.algorithm_combo.addItem("Error loading models")
                self.algorithm_combo.setEnabled(False)
    
    def _on_model_index_changed(self, index: int):
        """Handle model selection change by index"""
        logging.info(f"🔥 _on_model_index_changed triggered with index: {index}")
        
        if not self.algorithm_combo or index < 0:
            return
            
        model_name = self.algorithm_combo.itemText(index)
        logging.info(f"Model index changed to {index}: '{model_name}'")
        self._on_model_changed(model_name)
    
    def _on_model_activated(self, index: int):
        """Handle model activation (user selection) by index"""
        logging.info(f"🔥 _on_model_activated triggered with index: {index}")
        
        if not self.algorithm_combo or index < 0:
            return
            
        model_name = self.algorithm_combo.itemText(index)
        logging.info(f"Model activated at index {index}: '{model_name}' (user clicked)")
        self._on_model_changed(model_name)
    
    def _on_model_changed(self, model_name: str):
        """Handle model selection change"""
        logging.info(f"🔥 _on_model_changed triggered with: '{model_name}'")
        logging.info(f"🔥 Signal received from real UI interaction!")
        
        if not model_name or model_name == "Select Model..." or model_name == "No models found":
            logging.info("Clearing classification combo - no valid model selected")
            self.current_model = None
            self._clear_classification_combo()
            return
        
        try:
            logging.info(f"Loading model info for: {model_name}")
            # Get model info
            model_info = self.model_manager.get_model_info(model_name)
            if not model_info:
                logging.error(f"Could not load model info for: {model_name}")
                self._clear_classification_combo()
                return
            
            self.current_model = model_info
            logging.info(f"Model info loaded: {len(model_info['classes'])} classes found")
            
            # Load classes into classification combo
            self._load_model_classes(model_info['classes'])
            
            logging.info(f"Model changed to: {model_name} with {len(model_info['classes'])} classes")
            
        except Exception as e:
            logging.error(f"Error handling model change: {e}")
            import traceback
            traceback.print_exc()
            self._clear_classification_combo()
    
    def _load_model_classes(self, classes: List[str]):
        """Load model classes into classification combo box"""
        logging.info(f"Loading {len(classes)} classes into classification combo")
        logging.info(f"Classification combo available: {self.classification_combo is not None}")
        logging.info(f"Classification combo object: {self.classification_combo}")
        logging.info(f"Classification combo type: {type(self.classification_combo)}")
        
        # Check if widget is still valid/alive
        try:
            if self.classification_combo is not None:
                # Try to access a property to see if widget is still valid
                test_count = self.classification_combo.count()
                logging.info(f"Classification combo test count: {test_count}")
            else:
                logging.warning("Classification combo is None")
                return
        except Exception as e:
            logging.error(f"Classification combo widget is invalid: {e}")
            return
        
        try:
            # Clear existing items
            self.classification_combo.clear()
            logging.info("Cleared classification combo box")
            
            # Add default item
            self.classification_combo.addItem("Select Class...")
            logging.info("Added default 'Select Class...' item")
            
            # Add all classes
            for i, class_name in enumerate(classes):
                self.classification_combo.addItem(class_name)
                logging.info(f"Added class {i+1}: {class_name}")
            
            # Verify items were added
            item_count = self.classification_combo.count()
            logging.info(f"Classification combo box now has {item_count} items")
            for i in range(item_count):
                logging.info(f"  Item {i}: {self.classification_combo.itemText(i)}")
            
            self.classification_combo.setEnabled(True)
            logging.info(f"Loaded {len(classes)} classes into classification combo box")
            
        except Exception as e:
            logging.error(f"Error loading model classes: {e}")
            import traceback
            traceback.print_exc()
    
    def _clear_classification_combo(self):
        """Clear classification combo box"""
        if self.classification_combo:
            self.classification_combo.clear()
            self.classification_combo.addItem("No model selected")
            self.classification_combo.setEnabled(False)
    
    def _on_add_classification(self):
        """Handle add classification button click"""
        if not self.classification_combo or not self.classification_list:
            return
        
        try:
            # Get selected class
            selected_class = self.classification_combo.currentText()
            
            if not selected_class or selected_class == "Select Class...":
                logging.warning("No class selected for addition")
                return
            
            # Check if class already added
            if selected_class in self.selected_classes:
                logging.warning(f"Class '{selected_class}' already added")
                return
            
            # Add to selected classes list
            self.selected_classes.append(selected_class)
            
            # Add to UI list (handle both QListView and QListWidget)
            self._add_item_to_list(selected_class)
            
            # Reset combo box to "Select Class..." to allow adding more classes
            if self.classification_combo:
                self.classification_combo.setCurrentIndex(0)  # Set to "Select Class..."
            
            # Update button states
            self._update_button_states()
            
            logging.info(f"Added class: {selected_class}")
            
        except Exception as e:
            logging.error(f"Error adding classification: {e}")
    
    def _add_item_to_list(self, item_text: str):
        """Add item to classification list (handles both QListView and QListWidget)"""
        if hasattr(self.classification_list, 'model') and self.classification_list.model():
            # QListView with model
            model = self.classification_list.model()
            current_items = model.stringList()
            current_items.append(item_text)
            model.setStringList(current_items)
        elif hasattr(self.classification_list, 'addItem'):
            # QListWidget
            self.classification_list.addItem(item_text)
        else:
            logging.warning("Unknown list widget type for adding item")
    
    def _remove_item_from_list(self, item_text: str):
        """Remove item from classification list (handles both QListView and QListWidget)"""
        if hasattr(self.classification_list, 'model') and self.classification_list.model():
            # QListView with model
            model = self.classification_list.model()
            current_items = model.stringList()
            if item_text in current_items:
                current_items.remove(item_text)
                model.setStringList(current_items)
        elif hasattr(self.classification_list, 'takeItem'):
            # QListWidget
            for i in range(self.classification_list.count()):
                item = self.classification_list.item(i)
                if item and item.text() == item_text:
                    self.classification_list.takeItem(i)
                    break
        else:
            logging.warning("Unknown list widget type for removing item")
    
    def _clear_classification_list(self):
        """Clear classification list (handles both QListView and QListWidget)"""
        if not self.classification_list:
            return
            
        if hasattr(self.classification_list, 'model') and self.classification_list.model():
            # QListView with model
            model = self.classification_list.model()
            model.setStringList([])
        elif hasattr(self.classification_list, 'clear'):
            # QListWidget
            self.classification_list.clear()
        else:
            logging.warning("Unknown list widget type for clearing")
    
    def _get_selected_item_text(self):
        """Get selected item text (handles both QListView and QListWidget)"""
        if hasattr(self.classification_list, 'currentIndex'):
            # QListView with model
            current_index = self.classification_list.currentIndex()
            if current_index.isValid():
                return current_index.data()
        elif hasattr(self.classification_list, 'currentItem'):
            # QListWidget
            current_item = self.classification_list.currentItem()
            if current_item:
                return current_item.text()
        return None
    
    def _on_remove_classification(self):
        """Handle remove classification button click"""
        if not self.classification_list:
            return
        
        try:
            # Get selected item text
            selected_text = self._get_selected_item_text()
            if not selected_text:
                logging.warning("No class selected for removal")
                return
            
            # Remove from selected classes list
            if selected_text in self.selected_classes:
                self.selected_classes.remove(selected_text)
            
            # Remove from UI list
            self._remove_item_from_list(selected_text)
            
            # Update button states
            self._update_button_states()
            
            logging.info(f"Removed class: {selected_text}")
            
        except Exception as e:
            logging.error(f"Error removing classification: {e}")
    
    def _on_class_selection_changed(self):
        """Handle class selection change in the list"""
        self._update_button_states()
    
    def _update_button_states(self):
        """Update button enabled states based on current selections"""
        if self.add_classification_btn:
            # Enable add button if model and class are selected and class not already added
            current_text = self.classification_combo.currentText() if self.classification_combo else ""
            can_add = (
                self.current_model is not None and
                self.classification_combo and
                current_text not in ["Select Class...", ""] and
                current_text not in self.selected_classes
            )
            self.add_classification_btn.setEnabled(can_add)
            
            # Debug logging
            logging.debug(f"Add button state - Model: {self.current_model is not None}, "
                         f"Current text: '{current_text}', "
                         f"Already selected: {current_text in self.selected_classes}, "
                         f"Can add: {can_add}")
        
        if self.remove_classification_btn:
            # Enable remove button if a class is selected in the list
            can_remove = False
            if self.classification_list:
                # Check for selection in both QListView and QListWidget
                if hasattr(self.classification_list, 'currentIndex'):
                    # QListView
                    can_remove = self.classification_list.currentIndex().isValid()
                elif hasattr(self.classification_list, 'currentItem'):
                    # QListWidget
                    can_remove = self.classification_list.currentItem() is not None
            self.remove_classification_btn.setEnabled(can_remove)
    
    def get_selected_classes(self) -> List[str]:
        """Get list of currently selected classes"""
        return self.selected_classes.copy()
    
    def get_current_model(self) -> Optional[Dict]:
        """Get current model info"""
        return self.current_model
    
    def set_selected_classes(self, classes: List[str]):
        """Set selected classes (for loading tool configuration)"""
        try:
            # Clear current selection
            self.selected_classes.clear()
            self._clear_classification_list()
            
            # Add new classes
            for class_name in classes:
                if class_name not in self.selected_classes:
                    self.selected_classes.append(class_name)
                    self._add_item_to_list(class_name)
            
            # Update button states
            self._update_button_states()
            
            logging.info(f"Set selected classes: {classes}")
            
        except Exception as e:
            logging.error(f"Error setting selected classes: {e}")
    
    def set_current_model(self, model_name: str):
        """Set current model (for loading tool configuration)"""
        try:
            if self.algorithm_combo:
                # Find and select the model in combo box
                index = self.algorithm_combo.findText(model_name)
                if index >= 0:
                    self.algorithm_combo.setCurrentIndex(index)
                    logging.info(f"Set current model: {model_name}")
                else:
                    logging.warning(f"Model not found in combo box: {model_name}")
                    
        except Exception as e:
            logging.error(f"Error setting current model: {e}")
    
    def get_tool_config(self) -> Dict:
        """Get current tool configuration"""
        config = {
            'model_name': self.current_model['name'] if self.current_model else None,
            'model_path': self.current_model['path'] if self.current_model else None,
            'selected_classes': self.selected_classes.copy(),
            'num_classes': len(self.selected_classes)
        }
        return config
    
    def load_tool_config(self, config: Dict):
        """Load tool configuration"""
        try:
            # Set model if specified
            if 'model_name' in config and config['model_name']:
                self.set_current_model(config['model_name'])
            
            # Set selected classes if specified
            if 'selected_classes' in config:
                self.set_selected_classes(config['selected_classes'])
            
            logging.info("Tool configuration loaded successfully")
            
        except Exception as e:
            logging.error(f"Error loading tool configuration: {e}")
