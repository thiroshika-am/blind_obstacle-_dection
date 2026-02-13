"""
==========================================
OBJECT DETECTION TEST
Verify YOLOv5 detection pipeline
==========================================
"""

import cv2
import numpy as np
import logging
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_modules.object_detection import ObjectDetector

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_object_detection():
    """Test object detection on sample image"""
    
    print("\n" + "="*60)
    print("TEST: Object Detection (YOLO)")
    print("="*60)
    
    try:
        # Initialize detector
        print("\n[1] Initializing detector...")
        detector = ObjectDetector(model_path='yolov5s', confidence_threshold=0.5)
        print("✓ Detector initialized")
        
        # Create a sample image (640x480 blank with some shapes)
        print("\n[2] Creating test image...")
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 255
        
        # Add some shapes to detect (mostly images would be camera capture)
        cv2.rectangle(frame, (100, 50), (200, 150), (0, 0, 255), -1)     # Red rectangle
        cv2.rectangle(frame, (400, 200), (550, 350), (0, 255, 0), -1)    # Green rectangle
        cv2.circle(frame, (320, 240), 50, (255, 0, 0), -1)               # Blue circle
        cv2.putText(frame, 'Test Image', (50, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        print("✓ Test image created (640x480)")
        
        # Run detection
        print("\n[3] Running detection...")
        detections = detector.detect(frame, verbose=True)
        
        print(f"✓ Detection complete: {len(detections)} objects found")
        
        # Display results
        print("\n[4] Detection Results:")
        print("-" * 60)
        for i, det in enumerate(detections, 1):
            print(f"  [{i}] {det['class']}")
            print(f"      Confidence: {det['confidence']:.2%}")
            print(f"      BBox: ({det['x1']}, {det['y1']}) → ({det['x2']}, {det['y2']})")
            print()
        
        # Visualize detections
        print("\n[5] Visualizing detections...")
        vis_frame = detector.visualize(frame, detections)
        
        # Save visualization
        output_path = Path(__file__).parent.parent / "debug_frames"
        output_path.mkdir(exist_ok=True)
        
        cv2.imwrite(str(output_path / "detection_test.jpg"), vis_frame)
        print(f"✓ Visualization saved: {output_path / 'detection_test.jpg'}")
        
        # Get inference statistics
        print("\n[6] Performance Metrics:")
        print(f"  Average Inference Time: {detector.get_avg_inference_time():.1f}ms")
        print(f"  Model: {detector.model}")
        print(f"  Device: {detector.device}")
        
        print("\n" + "="*60)
        print("✓ DETECTION TEST PASSED")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_detection_filtering():
    """Test detection filtering capabilities"""
    
    print("\n" + "="*60)
    print("TEST: Detection Filtering")
    print("="*60)
    
    try:
        print("\n[1] Creating mock detections...")
        
        detections = [
            {'class': 'person', 'confidence': 0.95, 'x1': 10, 'y1': 10, 'x2': 100, 'y2': 200},
            {'class': 'car', 'confidence': 0.87, 'x1': 150, 'y1': 50, 'x2': 300, 'y2': 150},
            {'class': 'dog', 'confidence': 0.45, 'x1': 350, 'y1': 200, 'x2': 400, 'y2': 250},
            {'class': 'person', 'confidence': 0.62, 'x1': 500, 'y1': 100, 'x2': 550, 'y2': 200},
        ]
        
        print(f"✓ Created {len(detections)} mock detections")
        
        # Initialize detector (for filter methods)
        print("\n[2] Testing filter methods...")
        detector = ObjectDetector()
        
        # Filter by class
        people = detector.filter_detections(detections, classes=['person'])
        print(f"✓ Filter by class 'person': {len(people)} results")
        
        # Filter by confidence
        high_conf = detector.filter_detections(detections, min_confidence=0.8)
        print(f"✓ Filter by confidence > 0.8: {len(high_conf)} results")
        
        # Get closest detection
        closest = detector.get_closest_detection(detections)
        print(f"✓ Closest detection: {closest['class']} (confidence: {closest['confidence']:.2%})")
        
        print("\n" + "="*60)
        print("✓ FILTERING TEST PASSED")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n╔════════════════════════════════════════╗")
    print("║   OBJECT DETECTION TEST SUITE          ║")
    print("╚════════════════════════════════════════╝")
    
    results = []
    
    # Run tests
    results.append(("Object Detection", test_object_detection()))
    results.append(("Detection Filtering", test_detection_filtering()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:.<40} {status}")
    
    all_passed = all(result for _, result in results)
    
    print("="*60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("="*60 + "\n")
    
    exit(0 if all_passed else 1)
