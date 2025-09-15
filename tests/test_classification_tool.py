#!/usr/bin/env python3
"""
Test script for Classification Tool with yolov11n-cls model
Usage: python test_classification_tool.py [--image PATH] [--model MODEL_NAME]
"""

import os
import sys
import cv2
import json
import argparse
import numpy as np
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from tools.classification_tool import ClassificationTool
except ImportError:
    print("❌ Error: Could not import ClassificationTool")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


class ClassificationTester:
    """Test harness for Classification Tool"""
    
    def __init__(self, model_name="yolov11n-cls"):
        self.model_name = model_name
        self.tool = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_tool(self):
        """Setup Classification Tool with specified model"""
        try:
            self.logger.info(f"🔧 Setting up Classification Tool with model: {self.model_name}")
            
            # Check if model files exist
            model_path = f"model/classification/{self.model_name}.onnx"
            json_path = f"model/classification/{self.model_name}.json"
            
            if not os.path.exists(model_path):
                self.logger.error(f"❌ Model file not found: {model_path}")
                return False
                
            if not os.path.exists(json_path):
                self.logger.error(f"❌ Model config not found: {json_path}")
                return False
            
            # Load model configuration
            with open(json_path, 'r') as f:
                model_config = json.load(f)
            
            self.logger.info(f"📋 Model config: {model_config}")
            
            # Create tool configuration
            config = {
                'model_name': self.model_name,
                'expected_class': 'pilsner333',  # Default expected class
                'draw_result': True,
                'result_display': True,
                'use_rgb': True,
                'normalize': True,
                'confidence_threshold': 0.5
            }
            
            # Initialize Classification Tool
            self.tool = ClassificationTool("test_classification", config)
            
            self.logger.info("✅ Classification Tool setup successful")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to setup Classification Tool: {e}")
            return False
    
    def load_image(self, image_path):
        """Load and preprocess image"""
        try:
            if not os.path.exists(image_path):
                self.logger.error(f"❌ Image file not found: {image_path}")
                return None
            
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                self.logger.error(f"❌ Failed to load image: {image_path}")
                return None
            
            self.logger.info(f"📷 Loaded image: {image_path}")
            self.logger.info(f"   Shape: {image.shape}")
            self.logger.info(f"   Size: {image.shape[1]}x{image.shape[0]}")
            
            return image
            
        except Exception as e:
            self.logger.error(f"❌ Error loading image: {e}")
            return None
    
    def create_test_image(self, test_type="gradient"):
        """Create synthetic test image"""
        try:
            self.logger.info(f"🎨 Creating test image: {test_type}")
            
            if test_type == "gradient":
                # Create gradient image
                image = np.zeros((480, 640, 3), dtype=np.uint8)
                for i in range(480):
                    image[i, :] = [i // 2, 255 - i // 2, 128]
                    
            elif test_type == "pilsner":
                # Create pilsner-like image (golden color)
                image = np.ones((480, 640, 3), dtype=np.uint8)
                image[:, :] = [30, 215, 255]  # BGR golden color
                
            elif test_type == "noise":
                # Create random noise
                image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
                
            elif test_type == "solid":
                # Create solid color
                image = np.ones((480, 640, 3), dtype=np.uint8) * 128
                
            else:
                # Default: checkerboard pattern
                image = np.zeros((480, 640, 3), dtype=np.uint8)
                tile_size = 40
                for i in range(0, 480, tile_size):
                    for j in range(0, 640, tile_size):
                        if (i // tile_size + j // tile_size) % 2 == 0:
                            image[i:i+tile_size, j:j+tile_size] = [255, 255, 255]
            
            self.logger.info(f"✅ Created test image: {image.shape}")
            return image
            
        except Exception as e:
            self.logger.error(f"❌ Error creating test image: {e}")
            return None
    
    def run_classification(self, image, image_name="test"):
        """Run classification on image"""
        try:
            self.logger.info(f"🧪 Running classification on: {image_name}")
            self.logger.info(f"   Input shape: {image.shape}")
            
            # Process image through classification tool
            result_image, result_data = self.tool.process(image)
            
            # Display results
            self.logger.info("📊 Classification Results:")
            
            if result_data and isinstance(result_data, dict):
                # Show predictions
                if 'predictions' in result_data:
                    predictions = result_data['predictions']
                    self.logger.info(f"   Number of predictions: {len(predictions)}")
                    
                    for i, pred in enumerate(predictions):
                        if isinstance(pred, dict):
                            class_name = pred.get('class_name', 'unknown')
                            confidence = pred.get('confidence', 0.0)
                            self.logger.info(f"   Prediction {i+1}: {class_name} (confidence: {confidence:.4f})")
                        else:
                            self.logger.info(f"   Prediction {i+1}: {pred}")
                
                # Show OK/NG result
                if 'ok_ng_result' in result_data:
                    ok_ng = result_data['ok_ng_result']
                    status_emoji = "✅" if ok_ng == "OK" else "❌"
                    self.logger.info(f"   {status_emoji} OK/NG Result: {ok_ng}")
                
                # Show additional data
                for key, value in result_data.items():
                    if key not in ['predictions', 'ok_ng_result']:
                        self.logger.info(f"   {key}: {value}")
            
            # Check result image
            if result_image is not None:
                self.logger.info(f"   ✅ Result image generated: {result_image.shape}")
                return result_image, result_data
            else:
                self.logger.warning("   ⚠️  No result image generated")
                return None, result_data
                
        except Exception as e:
            self.logger.error(f"❌ Classification failed: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def save_result(self, result_image, output_path):
        """Save result image"""
        try:
            if result_image is not None:
                cv2.imwrite(output_path, result_image)
                self.logger.info(f"💾 Result saved to: {output_path}")
                return True
            else:
                self.logger.warning("⚠️  No result image to save")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error saving result: {e}")
            return False
    
    def run_test_suite(self):
        """Run comprehensive test suite"""
        self.logger.info("🚀 Running Classification Test Suite")
        
        test_types = ["gradient", "pilsner", "noise", "solid", "checkerboard"]
        results = []
        
        for test_type in test_types:
            self.logger.info(f"\n--- Testing: {test_type} ---")
            
            # Create test image
            image = self.create_test_image(test_type)
            if image is None:
                continue
            
            # Run classification
            result_image, result_data = self.run_classification(image, test_type)
            
            # Save result
            if result_image is not None:
                output_path = f"test_output_{test_type}.jpg"
                self.save_result(result_image, output_path)
            
            results.append({
                'test_type': test_type,
                'success': result_image is not None,
                'data': result_data
            })
        
        # Summary
        self.logger.info("\n📋 Test Suite Summary:")
        successful = sum(1 for r in results if r['success'])
        total = len(results)
        self.logger.info(f"   Successful tests: {successful}/{total}")
        
        for result in results:
            status = "✅" if result['success'] else "❌"
            self.logger.info(f"   {status} {result['test_type']}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Test Classification Tool with yolov11n-cls")
    parser.add_argument('--image', '-i', type=str, help='Path to input image')
    parser.add_argument('--model', '-m', type=str, default='yolov11n-cls', 
                       help='Model name (default: yolov11n-cls)')
    parser.add_argument('--output', '-o', type=str, default='classification_result.jpg',
                       help='Output image path (default: classification_result.jpg)')
    parser.add_argument('--test-suite', '-t', action='store_true',
                       help='Run comprehensive test suite')
    parser.add_argument('--create-test', '-c', type=str,
                       choices=['gradient', 'pilsner', 'noise', 'solid', 'checkerboard'],
                       help='Create and test synthetic image')
    
    args = parser.parse_args()
    
    print("🧪 Classification Tool Tester")
    print(f"Model: {args.model}")
    print("-" * 40)
    
    # Initialize tester
    tester = ClassificationTester(args.model)
    
    # Setup tool
    if not tester.setup_tool():
        print("❌ Failed to setup tool, exiting...")
        sys.exit(1)
    
    # Run test suite
    if args.test_suite:
        tester.run_test_suite()
        return
    
    # Create synthetic test image
    if args.create_test:
        print(f"🎨 Creating test image: {args.create_test}")
        image = tester.create_test_image(args.create_test)
        if image is None:
            print("❌ Failed to create test image")
            sys.exit(1)
        
        # Save test image
        test_image_path = f"test_image_{args.create_test}.jpg"
        cv2.imwrite(test_image_path, image)
        print(f"💾 Test image saved: {test_image_path}")
        
        # Use created image
        args.image = test_image_path
    
    # Load and process image
    if args.image:
        image = tester.load_image(args.image)
        if image is None:
            print("❌ Failed to load image")
            sys.exit(1)
    else:
        print("⚠️  No image specified, creating default test image...")
        image = tester.create_test_image("gradient")
        if image is None:
            print("❌ Failed to create test image")
            sys.exit(1)
    
    # Run classification
    result_image, result_data = tester.run_classification(image, 
                                                         args.image or "synthetic")
    
    # Save result
    if result_image is not None:
        tester.save_result(result_image, args.output)
        print(f"\n🎉 Classification completed! Result saved to: {args.output}")
    else:
        print("\n❌ Classification failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()