"""
==========================================
VISIONX SMART AI CAP — Single File Application
==========================================
All-in-one backend server with embedded frontend, 
YOLO object detection, OCR text reading, and voice guidance.

Run with: python app.py
Open browser: http://localhost:5000
==========================================
"""

import os
import json
import time
import logging
import threading
import base64
import random
import re
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
from io import BytesIO

# ============================================
# DEPENDENCIES CHECK
# ============================================

try:
    from flask import Flask, Response, jsonify, request, abort
    from flask_cors import CORS
except ImportError:
    print("Installing Flask dependencies...")
    os.system("pip install flask flask-cors")
    from flask import Flask, Response, jsonify, request, abort
    from flask_cors import CORS

try:
    import requests
except ImportError:
    print("Installing requests...")
    os.system("pip install requests")
    import requests

try:
    import cv2
    import numpy as np
    import torch
    from ultralytics import YOLO
except ImportError:
    print("Installing AI dependencies...")
    os.system("pip install opencv-python numpy torch ultralytics")
    import cv2
    import numpy as np
    import torch
    from ultralytics import YOLO

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("Warning: EasyOCR not installed. Run: pip install easyocr")

# Optional LLM support
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# ============================================
# CONFIGURATION
# ============================================

BACKEND_PORT = 5000
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(MODEL_DIR, "yolov8n.pt")
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

# ESP32 configuration (optional)
ESP32_STREAM_URL = "http://192.168.1.100:80/stream"
ESP32_STATUS_URL = "http://192.168.1.100:80/status"
ESP32_DISTANCE_URL = "http://192.168.1.100:80/distance"

# ============================================
# LOGGING
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("visionx")

# ============================================
# OBJECT DETECTOR MODULE
# ============================================

class ObjectDetector:
    """YOLO-based object detector for obstacle detection"""
    
    def __init__(self, confidence_threshold: float = 0.4):
        self.confidence_threshold = confidence_threshold
        self.model = None
        self._load_model()
        
        self.priority_objects = {
            'person', 'bicycle', 'car', 'motorcycle', 'bus', 'truck', 'traffic light',
            'stop sign', 'bench', 'chair', 'dog', 'cat', 'fire hydrant', 'parking meter',
            'potted plant', 'dining table', 'couch', 'bed', 'door', 'stairs'
        }
        
        self.reference_heights = {
            'person': 170, 'bicycle': 100, 'car': 150, 'motorcycle': 110,
            'bus': 280, 'truck': 250, 'chair': 90, 'dog': 50, 'cat': 30,
            'bottle': 25, 'cup': 10, 'laptop': 25, 'cell phone': 14,
            'book': 20, 'backpack': 50, 'handbag': 30, 'umbrella': 100,
        }
        
        self.tracked_objects = {}
        self.next_track_id = 1
        self.track_timeout = 2.0
        self.iou_threshold = 0.25
        self.movement_threshold = 15
        self.approach_threshold = 0.05
    
    def _load_model(self):
        try:
            print(f"Loading YOLOv8n model from {MODEL_PATH}...")
            print(f"Device: {DEVICE.upper()}")
            if DEVICE == 'cuda':
                print(f"GPU: {torch.cuda.get_device_name(0)}")
            self.model = YOLO(MODEL_PATH)
            self.model.to(DEVICE)
            print("Model loaded successfully!")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
    
    def _calculate_iou(self, box1: Dict, box2: Dict) -> float:
        x1 = max(box1['x1'], box2['x1'])
        y1 = max(box1['y1'], box2['y1'])
        x2 = min(box1['x2'], box2['x2'])
        y2 = min(box1['y2'], box2['y2'])
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1['x2'] - box1['x1']) * (box1['y2'] - box1['y1'])
        area2 = (box2['x2'] - box2['x1']) * (box2['y2'] - box2['y1'])
        union = area1 + area2 - intersection
        return intersection / union if union > 0 else 0
    
    def _get_center(self, bbox: Dict) -> Tuple[float, float]:
        return ((bbox['x1'] + bbox['x2']) / 2, (bbox['y1'] + bbox['y2']) / 2)
    
    def _calculate_movement(self, track_id: int, current_center: Tuple[float, float], 
                           current_distance: float, frame_width: int) -> Dict:
        track = self.tracked_objects.get(track_id)
        if not track or len(track['history']) < 2:
            return {'direction': 'stationary', 'approaching': None, 'lateral': None, 'speed': 0}
        
        prev_center = track['history'][-1]['center']
        prev_distance = track['history'][-1]['distance']
        dx = current_center[0] - prev_center[0]
        
        movement = {'direction': 'stationary', 'approaching': None, 'lateral': None, 'speed': 0}
        
        if abs(dx) > self.movement_threshold:
            movement['lateral'] = 'moving_right' if dx > 0 else 'moving_left'
        
        if prev_distance and current_distance:
            distance_change = prev_distance - current_distance
            if distance_change > self.approach_threshold:
                movement['approaching'] = True
                movement['direction'] = 'approaching'
                movement['speed'] = abs(distance_change)
            elif distance_change < -self.approach_threshold:
                movement['approaching'] = False
                movement['direction'] = 'receding'
                movement['speed'] = abs(distance_change)
        
        if movement['lateral'] and movement['approaching'] is not None:
            lateral = 'right' if movement['lateral'] == 'moving_right' else 'left'
            depth = 'approaching' if movement['approaching'] else 'receding'
            movement['direction'] = f'{depth}_{lateral}'
        elif movement['lateral']:
            movement['direction'] = movement['lateral']
        
        return movement
    
    def _update_tracks(self, detections: List[Dict], frame_width: int) -> List[Dict]:
        current_time = time.time()
        
        stale_ids = [tid for tid, track in self.tracked_objects.items() 
                     if current_time - track['last_seen'] > self.track_timeout]
        for tid in stale_ids:
            del self.tracked_objects[tid]
        
        matched_tracks = set()
        
        for det_idx, detection in enumerate(detections):
            best_iou = 0
            best_track_id = None
            
            for track_id, track in self.tracked_objects.items():
                if track_id in matched_tracks or track['class'] != detection['class']:
                    continue
                prev_bbox = track.get('bbox', detection['bbox'])
                iou = self._calculate_iou(detection['bbox'], prev_bbox)
                if iou > best_iou and iou > self.iou_threshold:
                    best_iou = iou
                    best_track_id = track_id
            
            current_center = self._get_center(detection['bbox'])
            current_distance = detection.get('distance_m')
            
            if best_track_id:
                matched_tracks.add(best_track_id)
                movement = self._calculate_movement(best_track_id, current_center, current_distance, frame_width)
                self.tracked_objects[best_track_id]['history'].append({
                    'center': current_center, 'distance': current_distance, 'time': current_time
                })
                if len(self.tracked_objects[best_track_id]['history']) > 10:
                    self.tracked_objects[best_track_id]['history'].pop(0)
                self.tracked_objects[best_track_id]['last_seen'] = current_time
                self.tracked_objects[best_track_id]['bbox'] = detection['bbox']
                detection['track_id'] = best_track_id
                detection['movement'] = movement
            else:
                new_id = self.next_track_id
                self.next_track_id += 1
                self.tracked_objects[new_id] = {
                    'class': detection['class'], 'bbox': detection['bbox'],
                    'last_seen': current_time,
                    'history': [{'center': current_center, 'distance': current_distance, 'time': current_time}]
                }
                detection['track_id'] = new_id
                detection['movement'] = {'direction': 'new', 'approaching': None, 'lateral': None, 'speed': 0}
        
        return detections
    
    def detect_from_base64(self, base64_image: str) -> Dict:
        if "," in base64_image:
            base64_image = base64_image.split(",")[1]
        img_bytes = base64.b64decode(base64_image)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            return {"error": "Invalid image", "detections": [], "count": 0, "alert_level": "SAFE"}
        return self.detect(img)
    
    def detect(self, frame: np.ndarray) -> Dict:
        results = self.model(frame, conf=self.confidence_threshold, device=DEVICE, verbose=False)
        detections = []
        result = results[0]
        focal_length_pixels = frame.shape[0] * 0.8
        
        if result.boxes is not None and len(result.boxes) > 0:
            boxes = result.boxes
            for i in range(len(boxes)):
                box = boxes.xyxy[i].cpu().numpy()
                x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
                conf = float(boxes.conf[i].cpu().numpy())
                cls_id = int(boxes.cls[i].cpu().numpy())
                cls_name = result.names[cls_id]
                
                bbox_height = y2 - y1
                ref_height_cm = self.reference_heights.get(cls_name, 50)
                if bbox_height > 0:
                    estimated_distance_cm = (ref_height_cm * focal_length_pixels) / bbox_height
                    estimated_distance_m = max(0.3, min(10.0, estimated_distance_cm / 100))
                    estimated_distance_m = round(estimated_distance_m, 1)
                    if estimated_distance_m <= 1.0:
                        alert_level = 'CRITICAL'
                    elif estimated_distance_m <= 2.5:
                        alert_level = 'WARNING'
                    else:
                        alert_level = 'SAFE'
                else:
                    estimated_distance_m = None
                    alert_level = 'SAFE'
                
                frame_width = frame.shape[1]
                center_x = (x1 + x2) / 2
                relative_x = center_x / frame_width
                position = 'left' if relative_x < 0.33 else ('right' if relative_x > 0.67 else 'center')
                
                detection = {
                    "class": cls_name, "confidence": round(conf, 2),
                    "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                    "priority": cls_name in self.priority_objects,
                    "distance_m": estimated_distance_m,
                    "distance": f"{estimated_distance_m}m" if estimated_distance_m else "Unknown",
                    "alert_level": alert_level, "position": position,
                    "position_x": round(relative_x, 2)
                }
                detections.append(detection)
        
        detections.sort(key=lambda x: (not x['priority'], -x['confidence']))
        detections = self._update_tracks(detections, frame.shape[1])
        
        annotated = result.plot()
        _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        annotated_b64 = base64.b64encode(buffer).decode('utf-8')
        
        overall_alert = 'SAFE'
        if any(d['alert_level'] == 'CRITICAL' for d in detections):
            overall_alert = 'CRITICAL'
        elif any(d['alert_level'] == 'WARNING' for d in detections):
            overall_alert = 'WARNING'
        
        return {
            "detections": detections, "count": len(detections),
            "alert_level": overall_alert,
            "annotated_frame": f"data:image/jpeg;base64,{annotated_b64}"
        }

# Singleton
_detector = None
def get_detector() -> ObjectDetector:
    global _detector
    if _detector is None:
        _detector = ObjectDetector()
    return _detector

# ============================================
# OCR ENGINE MODULE
# ============================================

class OCREngine:
    """OCR engine for text detection and recognition."""
    
    def __init__(self, languages: List[str] = ['en']):
        self.reader = None
        self.languages = languages
        self.text_cooldown = {}
        
        if EASYOCR_AVAILABLE:
            try:
                print(f"Loading EasyOCR with languages: {languages}")
                use_gpu = torch.cuda.is_available()
                self.reader = easyocr.Reader(languages, gpu=use_gpu, verbose=False)
                print(f"EasyOCR loaded (GPU: {use_gpu})")
            except Exception as e:
                print(f"Error loading EasyOCR: {e}")
    
    def detect_from_base64(self, image_b64: str, min_confidence: float = 0.3) -> Dict:
        try:
            if ',' in image_b64:
                image_b64 = image_b64.split(',')[1]
            img_bytes = base64.b64decode(image_b64)
            img_array = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if frame is None:
                return {"texts": [], "error": "Failed to decode image"}
            return self.detect(frame, min_confidence)
        except Exception as e:
            return {"texts": [], "error": str(e)}
    
    def detect(self, frame: np.ndarray, min_confidence: float = 0.3) -> Dict:
        if self.reader is None:
            return {"texts": [], "error": "OCR not available"}
        try:
            results = self.reader.readtext(frame)
            texts = []
            full_text_parts = []
            
            for detection in results:
                bbox, text, confidence = detection
                if confidence < min_confidence:
                    continue
                cleaned_text = self._clean_text(text)
                if not cleaned_text:
                    continue
                bbox_points = np.array(bbox).astype(int)
                texts.append({
                    "text": cleaned_text, "confidence": round(confidence, 2),
                    "bbox": {
                        "x1": int(min(p[0] for p in bbox_points)),
                        "y1": int(min(p[1] for p in bbox_points)),
                        "x2": int(max(p[0] for p in bbox_points)),
                        "y2": int(max(p[1] for p in bbox_points))
                    }
                })
                full_text_parts.append(cleaned_text)
            
            return {"texts": texts, "combined_text": " ".join(full_text_parts), "count": len(texts)}
        except Exception as e:
            return {"texts": [], "error": str(e)}
    
    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = " ".join(text.split())
        if len(text) < 2 or re.match(r'^[^\w\s]+$', text):
            return ""
        return text.strip()

# Singleton
_ocr_reader = None
def get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        _ocr_reader = OCREngine()
    return _ocr_reader

# ============================================
# SMART ALERT GENERATOR (LLM)
# ============================================

class SmartAlertGenerator:
    """Generates natural language navigation alerts."""
    
    def __init__(self):
        self.llm_provider = None
        self.llm_client = None
        self._init_llm()
    
    def _init_llm(self):
        groq_key = os.getenv("GROQ_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        google_key = os.getenv("GOOGLE_API_KEY")
        
        if groq_key and OPENAI_AVAILABLE:
            self.llm_provider = "groq"
            self.llm_client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
            print("LLM: Using Groq API")
        elif openai_key and OPENAI_AVAILABLE:
            self.llm_provider = "openai"
            self.llm_client = OpenAI(api_key=openai_key)
            print("LLM: Using OpenAI API")
        elif google_key and GEMINI_AVAILABLE:
            self.llm_provider = "gemini"
            genai.configure(api_key=google_key)
            self.llm_client = genai.GenerativeModel('gemini-pro')
            print("LLM: Using Google Gemini")
        else:
            self.llm_provider = "template"
            print("LLM: Using template-based alerts")
    
    def generate_alert(self, detections, location=None) -> str:
        if not detections:
            return None
        
        critical = [d for d in detections if d.get('alert_level') == 'CRITICAL']
        warning = [d for d in detections if d.get('alert_level') == 'WARNING']
        
        if self.llm_provider == "template":
            return self._generate_with_templates(detections, critical, warning, location)
        return self._generate_with_templates(detections, critical, warning, location)
    
    def _generate_with_templates(self, detections, critical, warning, location) -> str:
        if critical:
            obj = critical[0]
            distance = obj.get('distance', 'very close')
            obj_name = obj.get('class', 'obstacle')
            is_approaching = obj.get('movement', {}).get('approaching', False)
            
            if is_approaching:
                return random.choice([
                    f"Warning! {obj_name} approaching fast, {distance}",
                    f"Alert! {obj_name} coming toward you, {distance}"
                ])
            return random.choice([
                f"Careful! {obj_name} {distance} ahead",
                f"Stop! {obj_name} directly ahead, {distance}"
            ])
        elif warning:
            obj = warning[0]
            distance = obj.get('distance', 'nearby')
            obj_name = obj.get('class', 'object')
            return f"{obj_name.capitalize()} {distance} ahead"
        elif detections:
            obj = detections[0]
            return f"{obj.get('class', 'object')} in view, {obj.get('distance', 'ahead')}"
        return None

# Singleton
_alert_generator = None
def get_alert_generator():
    global _alert_generator
    if _alert_generator is None:
        _alert_generator = SmartAlertGenerator()
    return _alert_generator

# ============================================
# IN-MEMORY STATE
# ============================================

gps_data = {
    "latitude": 12.9716, "longitude": 77.5946,
    "accuracy": 0, "speed": 0, "altitude": 0,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "source": "placeholder",
}

device_status = {
    "online": False, "last_seen": None, "battery": None,
    "wifi_rssi": None, "distance_mm": None,
    "alert_level": "SAFE", "uptime": 0,
}

gps_lock = threading.Lock()
status_lock = threading.Lock()

# ============================================
# EMBEDDED FRONTEND HTML
# ============================================

FRONTEND_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VisionX Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        :root {
            --primary: #00D4FF;
            --secondary: #7C3AED;
            --dark-bg: #0F172A;
            --card-bg: rgba(15, 23, 42, 0.6);
            --success: #10B981;
            --warning: #F59E0B;
            --danger: #EF4444;
            --text-primary: #F1F5F9;
            --text-secondary: #CBD5E1;
            --radius-md: 1rem;
            --gap-sm: 1rem;
            --gap-md: 1.5rem;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Orbitron', sans-serif;
            background: var(--dark-bg);
            color: var(--text-primary);
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 1rem; }
        .header {
            padding: 1rem;
            margin-bottom: 1rem;
            background: rgba(15, 23, 42, 0.9);
            border-radius: var(--radius-md);
            border: 1px solid rgba(0, 212, 255, 0.2);
        }
        .logo { font-size: 1.8rem; font-weight: 800; color: var(--primary); }
        .main-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 1rem; }
        .panel {
            background: rgba(15, 23, 42, 0.95);
            border: 1px solid rgba(0, 212, 255, 0.2);
            border-radius: var(--radius-md);
            padding: 1rem;
        }
        .panel-title {
            font-size: 1rem;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 1rem;
        }
        .camera-viewport {
            position: relative;
            aspect-ratio: 16/9;
            background: #000;
            border-radius: 0.5rem;
            overflow: hidden;
        }
        #camera-feed { width: 100%; height: 100%; object-fit: cover; }
        #detection-canvas { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
        .camera-overlay {
            position: absolute;
            inset: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: rgba(15, 23, 42, 0.9);
        }
        .camera-overlay.hidden { display: none; }
        .spinner {
            width: 40px; height: 40px;
            border: 3px solid rgba(0, 212, 255, 0.2);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .detection-display { min-height: 100px; padding: 1rem; }
        .detection-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem;
            margin-bottom: 0.5rem;
            background: rgba(0, 212, 255, 0.1);
            border-radius: 0.5rem;
        }
        .object-name { color: var(--text-primary); font-weight: 600; }
        .object-distance { color: var(--primary); }
        .alert-critical { color: var(--danger) !important; }
        .alert-warning { color: var(--warning) !important; }
        .alert-safe { color: var(--success) !important; }
        .status-lights { display: flex; flex-wrap: wrap; gap: 0.5rem; }
        .status-item { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; }
        .light-indicator {
            width: 10px; height: 10px;
            border-radius: 50%;
            background: #6B7280;
        }
        .light-indicator.on { background: var(--success); box-shadow: 0 0 8px var(--success); }
        .voice-panel { margin-top: 1rem; }
        .voice-status { font-size: 0.85rem; color: var(--text-secondary); }
        #map { height: 200px; border-radius: 0.5rem; }
        .ocr-text-display {
            position: absolute;
            bottom: 10px;
            left: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: var(--primary);
            padding: 10px;
            border-radius: 8px;
            font-family: monospace;
            z-index: 100;
        }
        @media (max-width: 768px) {
            .main-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <span class="logo">⚡ VisionX</span>
        </header>
        <main class="main-grid">
            <section>
                <div class="panel">
                    <div class="panel-title">Live Feed</div>
                    <div class="camera-viewport">
                        <video id="camera-feed" autoplay playsinline muted></video>
                        <canvas id="detection-canvas"></canvas>
                        <div class="camera-overlay" id="camera-overlay">
                            <div class="spinner"></div>
                            <p style="color: var(--primary); margin-top: 1rem;">Initializing Camera...</p>
                        </div>
                    </div>
                </div>
                <div class="panel" style="margin-top: 1rem;">
                    <div class="panel-title">Current Detections</div>
                    <div class="detection-display" id="detection-display">
                        <p style="color: var(--text-secondary);">Scanning environment...</p>
                    </div>
                </div>
            </section>
            <section>
                <div class="panel">
                    <div class="panel-title">System Status</div>
                    <div class="status-lights">
                        <div class="status-item"><div class="light-indicator" id="light-camera"></div><span>Camera</span></div>
                        <div class="status-item"><div class="light-indicator" id="light-ai"></div><span>AI</span></div>
                        <div class="status-item"><div class="light-indicator" id="light-voice"></div><span>Voice</span></div>
                        <div class="status-item"><div class="light-indicator" id="light-gps"></div><span>GPS</span></div>
                    </div>
                </div>
                <div class="panel voice-panel">
                    <div class="panel-title">Voice Guidance</div>
                    <span class="voice-status" id="voice-status">Ready</span>
                </div>
                <div class="panel" style="margin-top: 1rem;">
                    <div class="panel-title">Location</div>
                    <div id="map"></div>
                </div>
            </section>
        </main>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
const CONFIG = {
    API_BASE: window.location.origin,
    DETECTION_INTERVAL: 100,
    OCR_INTERVAL: 2000,
};

const STATE = {
    voiceActive: true,
    isDetecting: false,
    isReadingText: false,
    lastDetections: [],
    announcedTexts: new Set(),
    voiceSpeed: 0.9,
};

let webcamStream = null;
let detectionCanvas = null;
let detectionCtx = null;
let detectionTimer = null;
let ocrTimer = null;
let preferredVoice = null;

// DOM Elements
const DOM = {};

function initDOMRefs() {
    DOM.cameraFeed = document.getElementById('camera-feed');
    DOM.cameraOverlay = document.getElementById('camera-overlay');
    DOM.detectionDisplay = document.getElementById('detection-display');
}

// Camera
async function connectCamera() {
    try {
        webcamStream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'environment' },
            audio: false
        });
        DOM.cameraFeed.srcObject = webcamStream;
        await DOM.cameraFeed.play();
        DOM.cameraOverlay.classList.add('hidden');
        updateLight('camera', true);
        setTimeout(startDetection, 1000);
    } catch (err) {
        console.error('Camera error:', err);
        setTimeout(connectCamera, 3000);
    }
}

// Detection
function startDetection() {
    if (detectionTimer) return;
    detectionCanvas = document.getElementById('detection-canvas');
    detectionCtx = detectionCanvas.getContext('2d');
    updateLight('ai', true);
    detectionTimer = setInterval(runDetection, CONFIG.DETECTION_INTERVAL);
    ocrTimer = setInterval(runOCR, CONFIG.OCR_INTERVAL);
}

async function runDetection() {
    if (STATE.isDetecting || !DOM.cameraFeed || !webcamStream?.active) return;
    if (DOM.cameraFeed.readyState < 2) return;
    
    STATE.isDetecting = true;
    try {
        const canvas = document.createElement('canvas');
        canvas.width = 640;
        canvas.height = 480;
        canvas.getContext('2d').drawImage(DOM.cameraFeed, 0, 0, 640, 480);
        const imageData = canvas.toDataURL('image/jpeg', 0.6);
        
        const response = await fetch(CONFIG.API_BASE + '/api/detect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        });
        
        if (response.ok) {
            const result = await response.json();
            handleDetectionResult(result);
        }
    } catch (err) {
        console.error('Detection error:', err);
    } finally {
        STATE.isDetecting = false;
    }
}

function handleDetectionResult(result) {
    STATE.lastDetections = result.detections || [];
    drawDetections(result.detections);
    updateDetectionDisplay(result.detections);
    announceDetections(result.detections);
}

function drawDetections(detections) {
    if (!detectionCanvas || !detectionCtx) return;
    const video = DOM.cameraFeed;
    detectionCanvas.width = video.offsetWidth;
    detectionCanvas.height = video.offsetHeight;
    const scaleX = detectionCanvas.width / 640;
    const scaleY = detectionCanvas.height / 480;
    detectionCtx.clearRect(0, 0, detectionCanvas.width, detectionCanvas.height);
    
    if (!detections?.length) return;
    
    detections.forEach(det => {
        const { bbox, class: label, alert_level } = det;
        const x = bbox.x1 * scaleX;
        const y = bbox.y1 * scaleY;
        const w = (bbox.x2 - bbox.x1) * scaleX;
        const h = (bbox.y2 - bbox.y1) * scaleY;
        
        let color = '#10B981';
        if (alert_level === 'CRITICAL') color = '#EF4444';
        else if (alert_level === 'WARNING') color = '#F59E0B';
        
        detectionCtx.strokeStyle = color;
        detectionCtx.lineWidth = 3;
        detectionCtx.strokeRect(x, y, w, h);
        
        const labelText = `${label} - ${det.distance}`;
        detectionCtx.font = 'bold 14px sans-serif';
        const tw = detectionCtx.measureText(labelText).width;
        detectionCtx.fillStyle = color;
        detectionCtx.fillRect(x, y - 24, tw + 16, 24);
        detectionCtx.fillStyle = '#FFF';
        detectionCtx.fillText(labelText, x + 8, y - 7);
    });
}

function updateDetectionDisplay(detections) {
    if (!detections?.length) {
        DOM.detectionDisplay.innerHTML = '<p style="color: var(--text-secondary);">Scanning...</p>';
        return;
    }
    DOM.detectionDisplay.innerHTML = detections.slice(0, 5).map(det => `
        <div class="detection-item">
            <span class="object-name">${det.class}</span>
            <span class="object-distance alert-${det.alert_level.toLowerCase()}">${det.distance}</span>
        </div>
    `).join('');
}

// OCR
async function runOCR() {
    if (STATE.isReadingText || !DOM.cameraFeed || !webcamStream?.active) return;
    if (DOM.cameraFeed.readyState < 2) return;
    
    STATE.isReadingText = true;
    try {
        const canvas = document.createElement('canvas');
        canvas.width = 800;
        canvas.height = 600;
        canvas.getContext('2d').drawImage(DOM.cameraFeed, 0, 0, 800, 600);
        const imageData = canvas.toDataURL('image/jpeg', 0.7);
        
        const response = await fetch(CONFIG.API_BASE + '/api/ocr', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.combined_text?.trim().length > 2) {
                handleOCRResult(result);
            }
        }
    } catch (err) {
        console.error('OCR error:', err);
    } finally {
        STATE.isReadingText = false;
    }
}

function handleOCRResult(result) {
    const text = result.combined_text.trim();
    const normalized = text.toLowerCase();
    
    if (STATE.announcedTexts.has(normalized)) return;
    
    STATE.announcedTexts.add(normalized);
    setTimeout(() => STATE.announcedTexts.delete(normalized), 30000);
    
    announceText(text);
    displayDetectedText(text);
}

function displayDetectedText(text) {
    let display = document.getElementById('ocr-text-display');
    if (!display) {
        display = document.createElement('div');
        display.id = 'ocr-text-display';
        display.className = 'ocr-text-display';
        document.querySelector('.camera-viewport')?.appendChild(display);
    }
    display.innerHTML = '<span style="color: #10B981;">📝 TEXT:</span> ' + escapeHtml(text);
    clearTimeout(display._hideTimeout);
    display._hideTimeout = setTimeout(() => display.remove(), 5000);
}

// Voice
function initVoice() {
    if (!window.speechSynthesis) {
        updateLight('voice', false);
        return;
    }
    updateLight('voice', true);
    const loadVoices = () => {
        const voices = speechSynthesis.getVoices();
        preferredVoice = voices.find(v => v.name.includes('Samantha') || v.name.includes('Google')) || voices[0];
    };
    speechSynthesis.onvoiceschanged = loadVoices;
    loadVoices();
}

function speak(text) {
    if (!STATE.voiceActive || !speechSynthesis || !text) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = STATE.voiceSpeed;
    if (preferredVoice) utterance.voice = preferredVoice;
    speechSynthesis.speak(utterance);
}

function announceText(text) {
    if (!STATE.voiceActive || !speechSynthesis) return;
    speechSynthesis.cancel();
    const announcement = text.length > 100 ? text.substring(0, 100) + '...' : text;
    const utterance = new SpeechSynthesisUtterance('Text says: ' + announcement);
    utterance.rate = STATE.voiceSpeed;
    if (preferredVoice) utterance.voice = preferredVoice;
    speechSynthesis.speak(utterance);
}

let lastAnnounceTime = 0;
function announceDetections(detections) {
    if (!STATE.voiceActive || !speechSynthesis || !detections?.length) return;
    const now = Date.now();
    if (now - lastAnnounceTime < 5000) return;
    
    const critical = detections.find(d => d.alert_level === 'CRITICAL');
    if (critical) {
        speak(`Careful! ${critical.class} ${critical.distance} ahead`);
        lastAnnounceTime = now;
    }
}

// Utilities
function updateLight(type, on) {
    const light = document.getElementById('light-' + type);
    if (light) light.classList.toggle('on', on);
}

function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Map
let map = null;
function initMap() {
    const mapEl = document.getElementById('map');
    if (!mapEl) return;
    try {
        map = L.map('map').setView([0, 0], 15);
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            maxZoom: 19
        }).addTo(map);
        
        if (navigator.geolocation) {
            navigator.geolocation.watchPosition(pos => {
                const { latitude, longitude } = pos.coords;
                map.setView([latitude, longitude], 17);
                updateLight('gps', true);
            }, null, { enableHighAccuracy: true });
        }
    } catch (e) {
        console.error('Map error:', e);
    }
}

// Initialize
function init() {
    initDOMRefs();
    connectCamera();
    initVoice();
    initMap();
}

document.readyState === 'loading' 
    ? document.addEventListener('DOMContentLoaded', init) 
    : init();
    </script>
</body>
</html>'''

# ============================================
# FLASK APP
# ============================================

app = Flask(__name__)
CORS(app)

@app.route("/")
def serve_index():
    """Serve embedded HTML frontend."""
    return FRONTEND_HTML

@app.route("/api/detect", methods=["POST"])
def detect_objects():
    """Run YOLO object detection on a frame."""
    try:
        data = request.get_json(force=True)
        image_b64 = data.get("image")
        if not image_b64:
            return jsonify({"error": "No image provided", "detections": []}), 400
        
        detector = get_detector()
        result = detector.detect_from_base64(image_b64)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Detection error: {e}")
        return jsonify({"error": str(e), "detections": []}), 500

@app.route("/api/ocr", methods=["POST"])
def detect_text():
    """Detect text using OCR."""
    try:
        data = request.get_json(force=True)
        image_b64 = data.get("image")
        if not image_b64:
            return jsonify({"error": "No image provided", "texts": []}), 400
        
        ocr = get_ocr_reader()
        result = ocr.detect_from_base64(image_b64)
        if result.get("combined_text"):
            logger.info(f"OCR: '{result['combined_text'][:60]}'")
        return jsonify(result)
    except Exception as e:
        logger.error(f"OCR error: {e}")
        return jsonify({"error": str(e), "texts": []}), 500

@app.route("/api/gps", methods=["GET"])
def get_gps():
    """Return GPS data."""
    with gps_lock:
        return jsonify(gps_data)

@app.route("/api/gps", methods=["POST"])
def update_gps():
    """Update GPS from ESP32."""
    data = request.get_json(force=True)
    with gps_lock:
        gps_data.update({
            "latitude": data.get("latitude", gps_data["latitude"]),
            "longitude": data.get("longitude", gps_data["longitude"]),
            "accuracy": data.get("accuracy", 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "esp32"
        })
    return jsonify({"status": "ok"})

@app.route("/api/status", methods=["GET"])
def get_status():
    """Return device status."""
    with status_lock:
        return jsonify(device_status)

@app.route("/api/status", methods=["POST"])
def update_status():
    """Update status from ESP32."""
    data = request.get_json(force=True)
    with status_lock:
        device_status.update({
            "online": True,
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "battery": data.get("battery"),
            "wifi_rssi": data.get("wifi_rssi"),
            "distance_mm": data.get("distance_mm"),
            "alert_level": data.get("alert_level", "SAFE")
        })
    return jsonify({"status": "ok"})

@app.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "time": datetime.now(timezone.utc).isoformat()})

@app.route("/api/generate-alert", methods=["POST"])
def generate_alert():
    """Generate LLM-based alert."""
    try:
        data = request.get_json(force=True)
        detections = data.get("detections", [])
        if not detections:
            return jsonify({"alert": None})
        generator = get_alert_generator()
        alert_text = generator.generate_alert(detections, data.get("location"))
        return jsonify({"alert": alert_text})
    except Exception as e:
        return jsonify({"alert": None, "error": str(e)}), 500

@app.route("/api/stream")
def stream_proxy():
    """Proxy ESP32-CAM stream."""
    def generate():
        try:
            resp = requests.get(ESP32_STREAM_URL, stream=True, timeout=(3, 10))
            for chunk in resp.iter_content(chunk_size=4096):
                yield chunk
        except:
            pass
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

# ============================================
# BACKGROUND TASKS
# ============================================

def device_watchdog():
    """Mark device offline if no heartbeat."""
    while True:
        time.sleep(10)
        with status_lock:
            if device_status["last_seen"]:
                try:
                    last = datetime.fromisoformat(device_status["last_seen"])
                    if last.tzinfo is None:
                        last = last.replace(tzinfo=timezone.utc)
                    delta = (datetime.now(timezone.utc) - last).total_seconds()
                    if delta > 30:
                        device_status["online"] = False
                except:
                    pass

# ============================================
# MAIN
# ============================================

def main():
    print("=" * 50)
    print("  VISIONX SMART AI CAP — Single File App")
    print(f"  Frontend: http://localhost:{BACKEND_PORT}")
    print(f"  Device: {DEVICE.upper()}")
    print("=" * 50)
    
    # Start watchdog
    threading.Thread(target=device_watchdog, daemon=True).start()
    
    # Run server
    app.run(host="0.0.0.0", port=BACKEND_PORT, debug=False, threaded=True)

if __name__ == "__main__":
    main()
