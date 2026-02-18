"""
OCR Engine for SmartCap AI
Detects and reads text from camera frames
Uses EasyOCR for fast, accurate text recognition
"""

import os
import cv2
import numpy as np
import base64
from typing import Dict, List, Optional
import re

# Try to import EasyOCR, fall back to basic detection if not available
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("Warning: EasyOCR not installed. Run: pip install easyocr")

# Singleton OCR reader instance
_ocr_reader = None


def get_ocr_reader():
    """Get or create singleton OCR reader."""
    global _ocr_reader
    if _ocr_reader is None:
        _ocr_reader = OCREngine()
    return _ocr_reader


class OCREngine:
    """OCR engine for text detection and recognition."""
    
    def __init__(self, languages: List[str] = ['en']):
        """
        Initialize OCR engine.
        
        Args:
            languages: List of language codes to detect
        """
        self.reader = None
        self.languages = languages
        self.last_detected_text = ""
        self.text_cooldown = {}  # Prevent repeating same text
        
        if EASYOCR_AVAILABLE:
            try:
                print(f"Loading EasyOCR with languages: {languages}")
                # gpu=True if CUDA available, False otherwise
                import torch
                use_gpu = torch.cuda.is_available()
                self.reader = easyocr.Reader(languages, gpu=use_gpu, verbose=False)
                print(f"EasyOCR loaded successfully (GPU: {use_gpu})")
            except Exception as e:
                print(f"Error loading EasyOCR: {e}")
                self.reader = None
        else:
            print("EasyOCR not available - OCR disabled")
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR results."""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Apply adaptive thresholding for better text contrast
        # This helps with varying lighting conditions
        processed = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        return processed
    
    def detect_from_base64(self, image_b64: str, min_confidence: float = 0.3) -> Dict:
        """
        Detect text from base64 encoded image.
        
        Args:
            image_b64: Base64 encoded image (with or without data URI prefix)
            min_confidence: Minimum confidence threshold (lowered for better detection)
            
        Returns:
            Dict with detected text, bounding boxes, and confidence
        """
        try:
            # Remove data URI prefix if present
            if ',' in image_b64:
                image_b64 = image_b64.split(',')[1]
            
            # Decode base64 to image
            img_bytes = base64.b64decode(image_b64)
            img_array = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if frame is None:
                return {"texts": [], "error": "Failed to decode image"}
            
            return self.detect(frame, min_confidence)
            
        except Exception as e:
            return {"texts": [], "error": str(e)}
    
    def detect(self, frame: np.ndarray, min_confidence: float = 0.3) -> Dict:
        """
        Detect text in an image frame.
        
        Args:
            frame: OpenCV image (BGR format)
            min_confidence: Minimum confidence threshold (lowered for better detection)
            
        Returns:
            Dict with detected texts and their locations
        """
        if self.reader is None:
            return {"texts": [], "error": "OCR not available"}
        
        try:
            # Run OCR detection
            results = self.reader.readtext(frame)
            
            texts = []
            full_text_parts = []
            
            for detection in results:
                bbox, text, confidence = detection
                
                if confidence < min_confidence:
                    continue
                
                # Clean the text
                cleaned_text = self._clean_text(text)
                if not cleaned_text:
                    continue
                
                # Get bounding box coordinates
                bbox_points = np.array(bbox).astype(int)
                x_min = int(min(point[0] for point in bbox_points))
                y_min = int(min(point[1] for point in bbox_points))
                x_max = int(max(point[0] for point in bbox_points))
                y_max = int(max(point[1] for point in bbox_points))
                
                texts.append({
                    "text": cleaned_text,
                    "confidence": round(confidence, 2),
                    "bbox": {
                        "x1": x_min,
                        "y1": y_min,
                        "x2": x_max,
                        "y2": y_max
                    }
                })
                
                full_text_parts.append(cleaned_text)
            
            # Combine all detected text
            combined_text = " ".join(full_text_parts)
            
            return {
                "texts": texts,
                "combined_text": combined_text,
                "count": len(texts)
            }
            
        except Exception as e:
            return {"texts": [], "error": str(e)}
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize detected text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = " ".join(text.split())
        
        # Remove very short strings (likely noise)
        if len(text) < 2:
            return ""
        
        # Remove strings that are only special characters
        if re.match(r'^[^\w\s]+$', text):
            return ""
        
        return text.strip()
    
    def is_new_text(self, text: str, cooldown_seconds: float = 5.0) -> bool:
        """
        Check if this text is new (not recently announced).
        
        Args:
            text: The detected text
            cooldown_seconds: How long to wait before re-announcing same text
            
        Returns:
            True if text is new or cooldown expired
        """
        import time
        now = time.time()
        
        # Normalize text for comparison
        normalized = text.lower().strip()
        
        if normalized in self.text_cooldown:
            last_time = self.text_cooldown[normalized]
            if now - last_time < cooldown_seconds:
                return False
        
        self.text_cooldown[normalized] = now
        
        # Clean up old entries
        expired = [k for k, v in self.text_cooldown.items() if now - v > 60]
        for k in expired:
            del self.text_cooldown[k]
        
        return True
