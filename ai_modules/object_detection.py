"""
==========================================
OBJECT DETECTION MODULE
Using YOLOv5 for real-time object detection
==========================================

Detects: person, car, bicycle, backpack, chair, door, stairs, etc.
Returns: List of detections with class, confidence, bbox
"""

import cv2
import numpy as np
import torch
import logging

logger = logging.getLogger(__name__)

# Try different YOLOv5 backends
try:
    from ultralytics import YOLO  # New ultralytics library
    YOLO_BACKEND = "ultralytics"
except ImportError:
    try:
        import yolov5
        YOLO_BACKEND = "yolov5"
    except ImportError:
        YOLO_BACKEND = None
        logger.warning("No YOLO library found - install: pip install ultralytics")


class ObjectDetector:
    """
    Real-time object detection using YOLOv5
    
    Optimized for lightweight inference on CPU/GPU
    """
    
    def __init__(self, model_path="yolov5s", confidence_threshold=0.5):
        """
        Initialize detector
        
        Args:
            model_path: Path to model or model name
                       'yolov5n' (nano - fastest)
                       'yolov5s' (small - balanced)
                       'yolov5m' (medium)
                       'yolov5l' (large - slower, more accurate)
            confidence_threshold: Min confidence for detection
        """
        
        self.confidence_threshold = confidence_threshold
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        logger.info(f"Loading YOLO model: {model_path}")
        logger.info(f"Device: {self.device}")
        
        try:
            if YOLO_BACKEND == "ultralytics":
                # New ultralytics library
                self.model = YOLO(model_path)
                self.backend = "ultralytics"
            elif YOLO_BACKEND == "yolov5":
                # Original yolov5 library
                self.model = yolov5.load(model_path)
                self.model.to(self.device)
                self.backend = "yolov5"
            else:
                raise RuntimeError("No YOLO backend available")
                
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
        
        # Inference time tracking
        self.inference_times = []
        
        logger.info("✓ Object detector initialized")
    
    def detect(self, frame, verbose=False):
        """
        Run detection on a frame
        
        Args:
            frame: OpenCV image (BGR format)
            verbose: Print debug info
        
        Returns:
            List of detections:
            [
                {
                    'class': 'person',
                    'confidence': 0.92,
                    'bbox': (x1, y1, x2, y2),  # pixel coordinates
                    'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2
                },
                ...
            ]
        """
        
        try:
            if self.backend == "ultralytics":
                return self._detect_ultralytics(frame, verbose)
            else:
                return self._detect_yolov5(frame, verbose)
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []
    
    def _detect_ultralytics(self, frame, verbose=False):
        """Detection using ultralytics library"""
        
        import time
        start = time.time()
        
        # Run inference
        results = self.model(frame, conf=self.confidence_threshold, verbose=verbose)
        
        detections = []
        
        # Extract detections from results
        for result in results:
            boxes = result.boxes
            
            for box in boxes:
                # Get coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                confidence = float(box.conf[0].cpu().numpy())
                class_id = int(box.cls[0].cpu().numpy())
                class_name = result.names[class_id]
                
                detections.append({
                    'class': class_name,
                    'confidence': confidence,
                    'bbox': (x1, y1, x2, y2),
                    'x1': int(x1), 'y1': int(y1), 
                    'x2': int(x2), 'y2': int(y2),
                    'class_id': class_id
                })
        
        elapsed = (time.time() - start) * 1000
        self.inference_times.append(elapsed)
        
        if verbose:
            logger.debug(f"Detection took {elapsed:.1f}ms, found {len(detections)} objects")
        
        return detections
    
    def _detect_yolov5(self, frame, verbose=False):
        """Detection using yolov5 library"""
        
        import time
        start = time.time()
        
        # Run inference
        results = self.model(frame, size=640)
        
        detections = []
        
        # Extract detections
        pred = results.pred[0]
        
        for detection in pred:
            x1, y1, x2, y2, conf, cls_id = detection.cpu().numpy()
            
            if conf >= self.confidence_threshold:
                class_name = results.names[int(cls_id)]
                
                detections.append({
                    'class': class_name,
                    'confidence': float(conf),
                    'bbox': (int(x1), int(y1), int(x2), int(y2)),
                    'x1': int(x1), 'y1': int(y1),
                    'x2': int(x2), 'y2': int(y2),
                    'class_id': int(cls_id)
                })
        
        elapsed = (time.time() - start) * 1000
        self.inference_times.append(elapsed)
        
        if verbose:
            logger.debug(f"Detection took {elapsed:.1f}ms, found {len(detections)} objects")
        
        return detections
    
    def visualize(self, frame, detections):
        """
        Draw detections on frame for debugging
        
        Args:
            frame: Input image
            detections: List of detections
        
        Returns:
            Annotated frame
        """
        
        vis_frame = frame.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            conf = det['confidence']
            cls_name = det['class']
            
            # Draw bounding box
            cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            label = f"{cls_name} {conf:.2f}"
            cv2.putText(vis_frame, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return vis_frame
    
    def get_avg_inference_time(self):
        """Return average inference time in ms"""
        
        if not self.inference_times:
            return 0
        
        # Return average of last 30 frames
        recent = self.inference_times[-30:]
        return np.mean(recent)
    
    def filter_detections(self, detections, classes=None, min_confidence=None):
        """
        Filter detections by class and confidence
        
        Args:
            detections: List of detections
            classes: List of class names to keep (None = all)
            min_confidence: Minimum confidence threshold
        
        Returns:
            Filtered detections
        """
        
        if min_confidence is None:
            min_confidence = self.confidence_threshold
        
        filtered = [d for d in detections 
                   if d['confidence'] >= min_confidence]
        
        if classes is not None:
            filtered = [d for d in filtered 
                       if d['class'].lower() in [c.lower() for c in classes]]
        
        return filtered
    
    def get_closest_detection(self, detections):
        """
        Return the closest detection (bottom-most = closest in monocular)
        
        Args:
            detections: List of detections
        
        Returns:
            Closest detection dict, or None
        """
        
        if not detections:
            return None
        
        # Assume larger bbox area = closer object
        detections_by_area = sorted(
            detections,
            key=lambda d: (d['x2'] - d['x1']) * (d['y2'] - d['y1']),
            reverse=True
        )
        
        return detections_by_area[0]

