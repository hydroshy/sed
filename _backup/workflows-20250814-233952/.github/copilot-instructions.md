# Copilot Instructions for SED Project

## Overview
The Smart Eye Detection (SED) project is a computer vision application designed to run on a Raspberry Pi as an edge device. It processes images for tasks such as object detection, optical character recognition (OCR), and edge detection. The project is organized into several modular components, each responsible for specific functionalities.

## Project Structure
- **`camera/`**: Handles camera streaming and related utilities.
  - `camera_stream.py`: Manages live camera feeds.
- **`detection/`**: Contains detection algorithms and tools.
  - `edge_detection.py`: Implements edge detection.
  - `ocr_tool.py`: Provides OCR capabilities.
- **`gui/`**: Implements the graphical user interface.
  - `main_window.py`: Main application window logic.
  - `ui_mainwindow.py`: Auto-generated UI code.
- **`job/`**: Manages background jobs and tasks.
  - `job_manager.py`: Core job management logic.
- **`utils/`**: Utility functions for image processing.
  - `image_utils.py`: Common image manipulation utilities.
- **`docs/`**: Documentation files.
- **`requirements.txt`**: Lists Python dependencies.

## Key Workflows
### Setting Up the Environment
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Ensure the Raspberry Pi camera module is enabled and accessible.

### Running the Application
1. Start the main application:
   ```bash
   python main.py
   ```

### Debugging
- Use `print` statements or logging in key modules like `camera_stream.py` or `main_window.py` to trace issues.
- Check the `README.md` for additional setup instructions.

## Patterns and Conventions
- **Modular Design**: Each directory corresponds to a specific functionality (e.g., `camera/`, `detection/`).
- **GUI Separation**: UI logic is separated into `ui_mainwindow.py` (auto-generated) and `main_window.py` (custom logic).
- **Pre-trained Models**: OCR and detection rely on pre-trained models (`PP-OCRv5_mobile_det_pretrained.pdparams`, `PP-OCRv5_mobile_rec_pretrained.pdparams`).

## External Dependencies
- **PaddleOCR**: Used for OCR tasks.
- **OpenCV**: Utilized for image processing and camera handling.

## Example Code Patterns
### Using the Camera Stream
```python
from camera.camera_stream import CameraStream

camera = CameraStream()
camera.start()
frame = camera.get_frame()
```

### Performing Edge Detection
```python
from detection.edge_detection import detect_edges

edges = detect_edges(image)
```

## Notes
- Ensure all dependencies are installed before running the application.
- The project is designed to run on a Raspberry Pi but can be tested on other systems with minor modifications.

For further details, refer to the source code and comments within each module.
