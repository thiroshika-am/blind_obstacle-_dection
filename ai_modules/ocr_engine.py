"""
==========================================
OCR (TEXT RECOGNITION) MODULE
Optical Character Recognition using EasyOCR
==========================================

Recognizes text in images for signage, labels, documents
Returns: List of text regions with text and confidence
"""

import cv2
import numpy as np
import logging
import time

logger = logging.getLogger(__name__)

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logger.warning("EasyOCR not installed - install: pip install easyocr")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


class TextRecognizer:
    """
    Optical Character Recognition (OCR) for text detection and recognition
    
    Lightweight version optimized for real-time cap usage
    """
    
    def __init__(self, languages=['en'], device='cpu', use_gpu=False):
        """
        Initialize OCR engine
        
        Args:
            languages: Language codes ['en', 'es', 'fr', etc]
            device: 'cpu' or 'cuda'
            use_gpu: Force GPU usage
        """
        
        self.languages = languages
        self.device = 'cuda' if use_gpu else device
        
        logger.info(f"Initializing OCR: languages={languages}, device={self.device}")
        
        try:
            if EASYOCR_AVAILABLE:
                self.reader = easyocr.Reader(
                    languages,
                    gpu=(self.device == 'cuda'),
                    model_storage_directory=None,
                    user_network_directory=None,
                    recog_network='standard',
                    download_enabled=True,
                    detector=True,
                    recognizer=True
                )
                self.engine = "easyocr"
                logger.info("✓ OCR initialized with EasyOCR")
            else:
                logger.warning("EasyOCR not available")
                self.reader = None
                self.engine = None
                
        except Exception as e:
            logger.error(f"Failed to initialize OCR: {e}")
            self.reader = None
            self.engine = None
    
    def recognize(self, frame, conf_threshold=0.3):
        """
        Recognize text in frame
        
        Args:
            frame: OpenCV image (BGR)
            conf_threshold: Minimum confidence for text
        
        Returns:
            List of text detections:
            [
                {
                    'text': 'Stop Sign',
                    'confidence': 0.89,
                    'bbox': ((x,y), (x,y), (x,y), (x,y)),  # 4 corners
                    'x1': x, 'y1': y, 'x2': X, 'y2': Y
                },
                ...
            ]
        """
        
        if self.reader is None:
            return []
        
        try:
            start = time.time()
            
            # Convert BGR to RGB for EasyOCR
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Run OCR
            if self.engine == "easyocr":
                results = self.reader.readtext(rgb_frame, detail=1)
            else:
                return []
            
            # Process results
            text_detections = []
            
            for detection in results:
                bbox, text, confidence = detection
                
                if confidence >= conf_threshold:
                    # bbox is list of 4 corner points
                    x_coords = [p[0] for p in bbox]
                    y_coords = [p[1] for p in bbox]
                    
                    text_detections.append({
                        'text': text,
                        'confidence': float(confidence),
                        'bbox': bbox,  # 4 corner points
                        'x1': int(min(x_coords)),
                        'y1': int(min(y_coords)),
                        'x2': int(max(x_coords)),
                        'y2': int(max(y_coords))
                    })
            
            elapsed = (time.time() - start) * 1000
            logger.debug(f"OCR took {elapsed:.1f}ms, found {len(text_detections)} text regions")
            
            return text_detections
            
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return []
    
    def recognize_region(self, frame, x1, y1, x2, y2):
        """
        Recognize text in specific region of interest
        
        Useful for focusing on detected objects
        
        Args:
            frame: Input image
            x1, y1, x2, y2: Region coordinates
        
        Returns:
            Recognized text string
        """
        
        if self.reader is None:
            return ""
        
        # Crop region
        region = frame[y1:y2, x1:x2]
        
        try:
            rgb_region = cv2.cvtColor(region, cv2.COLOR_BGR2RGB)
            results = self.reader.readtext(rgb_region, detail=0)
            
            # Concatenate all text
            text = " ".join(results)
            return text
            
        except Exception as e:
            logger.error(f"Region OCR error: {e}")
            return ""
    
    def visualize(self, frame, detections):
        """
        Draw text detections on frame
        
        Args:
            frame: Input image
            detections: List of text detections
        
        Returns:
            Annotated frame
        """
        
        vis_frame = frame.copy()
        
        for det in detections:
            bbox = det['bbox']
            text = det['text']
            conf = det['confidence']
            
            # Draw polygon around text
            pts = np.array(bbox, dtype=np.int32)
            cv2.polylines(vis_frame, [pts], True, (0, 255, 255), 2)
            
            # Draw text label
            label = f"{text} ({conf:.2f})"
            cv2.putText(vis_frame, label, 
                       (int(bbox[0][0]), int(bbox[0][1]) - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        
        return vis_frame
    
    def filter_by_area(self, detections, min_area=100):
        """
        Filter out very small text regions (likely noise)
        
        Args:
            detections: List of text detections
            min_area: Minimum bounding box area
        
        Returns:
            Filtered detections
        """
        
        filtered = []
        
        for det in detections:
            area = (det['x2'] - det['x1']) * (det['y2'] - det['y1'])
            if area >= min_area:
                filtered.append(det)
        
        return filtered
    
    def get_largest_text(self, detections):
        """
        Return the largest (most prominent) text detection
        
        Args:
            detections: List of text detections
        
        Returns:
            Largest detection dict, or None
        """
        
        if not detections:
            return None
        
        detections_by_area = sorted(
            detections,
            key=lambda d: (d['x2'] - d['x1']) * (d['y2'] - d['y1']),
            reverse=True
        )
        
        return detections_by_area[0]


class SimpleOCRFallback:
    """
    Fallback simple OCR for when EasyOCR is not available
    
    Uses frame differencing and contour analysis
    to detect text regions (not actual recognition)
    """
    
    def __init__(self):
        self.engine = "fallback"
    
    def recognize(self, frame):
        """
        Detect text regions (simplified, no actual recognition)
        
        Returns: List of potential text bounding boxes
        """
        
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Threshold to find high contrast regions (text is usually high contrast)
        _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter by aspect ratio and size (text tends to be wider than tall)
            aspect_ratio = w / (h + 1)
            area = w * h
            
            if 0.5 < aspect_ratio < 20 and area > 50:
                detections.append({
                    'text': 'text_region',
                    'confidence': 0.2,  # Low confidence for fallback
                    'bbox': None,
                    'x1': x, 'y1': y, 'x2': x + w, 'y2': y + h
                })
        
        return detections

