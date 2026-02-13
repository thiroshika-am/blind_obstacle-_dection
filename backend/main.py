"""
==========================================
SMART AI CAP - PYTHON BACKEND
Main processing engine for image analysis and decision making
==========================================

Features:
  - Real-time image reception from ESP32
  - Object detection using YOLO
  - Text recognition using OCR
  - Priority-based alert generation
  - Wireless transmission of commands
  - Error handling and graceful degradation

Requirements:
  pip install opencv-python
  pip install torch torchvision
  pip install yolov5  OR ultralytics
  pip install easyocr
  pip install pyttsx3
  pip install pybluetoothctl
"""

import cv2
import numpy as np
import socket
import threading
import time
import json
import logging
from datetime import datetime
from collections import deque
import sys

# AI Modules (import separately)
from ai_modules.object_detection import ObjectDetector
from ai_modules.ocr_engine import TextRecognizer
from ai_modules.voice_output import VoiceEngine
from ai_modules.vibration_control import VibrationController
from communication.wireless_protocol import WirelessProtocol
from utils.config_loader import ConfigLoader, FrameBuffer, PerformanceMonitor

# ============================================
# CONFIGURATION & CONSTANTS
# ============================================

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('smartcap.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Alert priority levels
class AlertLevel:
    SAFE = 0
    WARNING = 1
    CRITICAL = 2

# Alert categories
class AlertCategory:
    OBSTACLE = "obstacle"
    MOVING_OBJECT = "moving_object"
    TEXT = "text"
    OBJECT = "object"

# ============================================
# MAIN BACKEND ENGINE
# ============================================

class SmartCapBackend:
    """
    Main backend processing engine that:
    1. Receives frames from ESP32
    2. Runs object detection & OCR
    3. Generates alerts
    4. Controls wireless output (audio, vibration)
    """
    
    def __init__(self, config_path="config/backend_config.json"):
        """Initialize the backend system"""
        
        logger.info("=" * 50)
        logger.info("Smart AI Cap Backend Starting...")
        logger.info("=" * 50)
        
        # Load configuration
        self.config = ConfigLoader(config_path)
        
        # Initialize modules
        self.object_detector = ObjectDetector(
            model_path=self.config.get("yolo_model_path"),
            confidence_threshold=self.config.get("detection_confidence", 0.5)
        )
        
        self.text_recognizer = TextRecognizer(
            languages=['en'],
            device='cuda' if self.config.get("use_gpu", False) else 'cpu'
        )
        
        self.voice_engine = VoiceEngine(
            tts_engine=self.config.get("tts_engine", "pyttsx3"),
            voice_speed=self.config.get("voice_speed", 1.0)
        )
        
        self.vibration_controller = VibrationController(
            bluetooth_device=self.config.get("bluetooth_device", "SmartCap_BLE")
        )
        
        self.wireless = WirelessProtocol(
            backend_ip=self.config.get("backend_ip", "0.0.0.0"),
            backend_port=self.config.get("backend_port", 5000),
            esp32_ip=self.config.get("esp32_ip", ""),
        )
        
        # Frame buffering
        self.frame_buffer = FrameBuffer(max_size=10)
        
        # Tracking variables
        self.current_alert_level = AlertLevel.SAFE
        self.last_alert_time = 0
        self.alert_cooldown = self.config.get("alert_cooldown", 500)  # ms
        self.is_running = False
        self.processing_stats = {
            'frames_processed': 0,
            'detections_made': 0,
            'ocr_recognitions': 0,
            'avg_latency_ms': 0
        }
        
        # Alert history for filtering duplicates
        self.recent_alerts = deque(maxlen=5)
        
        logger.info("✓ Backend initialized successfully")
        logger.info(f"  - Detection model: {self.config.get('yolo_model_path')}")
        logger.info(f"  - GPU acceleration: {self.config.get('use_gpu', False)}")
        logger.info(f"  - Bluetooth device: {self.config.get('bluetooth_device')}")
        
    def start(self):
        """Start the backend processing engine"""
        
        self.is_running = True
        logger.info("Starting backend listening...")
        
        # Start wireless receiver in separate thread
        receiver_thread = threading.Thread(
            target=self._receive_frame_thread,
            daemon=True
        )
        receiver_thread.start()
        
        # Main processing loop
        try:
            while self.is_running:
                self._process_next_frame()
                time.sleep(0.01)  # 100Hz processing loop
                
        except KeyboardInterrupt:
            logger.info("Shutdown signal received")
        finally:
            self.shutdown()
    
    def _receive_frame_thread(self):
        """Background thread for receiving frames from ESP32"""
        
        logger.info("Frame receiver thread started")
        
        while self.is_running:
            try:
                # Wait for frame from wireless
                frame_data = self.wireless.receive_frame(timeout=2.0)
                
                if frame_data is not None:
                    # Decode frame
                    frame = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
                    metadata = self.wireless.get_metadata()
                    
                    # Add to buffer
                    self.frame_buffer.add_frame(frame, metadata)
                    
            except socket.timeout:
                # No frame received - acceptable
                pass
            except Exception as e:
                logger.error(f"Frame reception error: {e}")
                time.sleep(0.5)
    
    def _process_next_frame(self):
        """Process the next frame in the buffer"""
        
        # Check if frame is available
        if not self.frame_buffer.has_frame():
            return
        
        frame, metadata = self.frame_buffer.get_frame()
        if frame is None:
            return
        
        # Start timer for latency measurement
        start_time = time.time()
        
        # Extract metadata
        distance_mm = metadata.get('distance', 0)
        frame_id = metadata.get('frame_id', 0)
        timestamp = metadata.get('timestamp', 0)
        
        # ==========================================
        # STEP 1: OBJECT DETECTION
        # ==========================================
        
        detections = self.object_detector.detect(frame)
        self.processing_stats['detections_made'] += len(detections)
        
        logger.debug(f"Frame {frame_id}: {len(detections)} objects detected")
        
        # ==========================================
        # STEP 2: OBSTACLE ANALYSIS (from distance sensor)
        # ==========================================
        
        obstacle_alert = self._check_obstacles(distance_mm, detections)
        
        # ==========================================
        # STEP 3: TEXT RECOGNITION (if needed)
        # ==========================================
        
        text_detections = []
        if self.config.get("enable_ocr", True):
            # Only run OCR if text-like objects detected
            if self._should_run_ocr(detections):
                text_detections = self.text_recognizer.recognize(frame)
                self.processing_stats['ocr_recognitions'] += len(text_detections)
                logger.debug(f"OCR: Found {len(text_detections)} text regions")
        
        # ==========================================
        # STEP 4: PRIORITY-BASED DECISION MAKING
        # ==========================================
        
        alert = self._make_decision(
            detections, 
            text_detections, 
            obstacle_alert, 
            distance_mm
        )
        
        # ==========================================
        # STEP 5: GENERATE OUTPUT (Audio + Haptic)
        # ==========================================
        
        if alert is not None:
            self._execute_alert(alert)
        
        # ==========================================
        # TELEMETRY & LOGGING
        # ==========================================
        
        latency_ms = (time.time() - start_time) * 1000
        self.processing_stats['frames_processed'] += 1
        self.processing_stats['avg_latency_ms'] = (
            0.9 * self.processing_stats['avg_latency_ms'] + 
            0.1 * latency_ms
        )
        
        if self.processing_stats['frames_processed'] % 30 == 0:
            logger.info(f"Stats: "
                       f"Frames={self.processing_stats['frames_processed']}, "
                       f"Latency={self.processing_stats['avg_latency_ms']:.1f}ms, "
                       f"Detections={self.processing_stats['detections_made']}"
            )
    
    def _check_obstacles(self, distance_mm, detections):
        """
        Analyze distance sensor and object detection for obstacles
        
        Returns: Alert dict if obstacle detected, None otherwise
        """
        
        if distance_mm <= 0:
            return None  # No valid reading
        
        distance_cm = distance_mm / 10.0
        
        # Define danger zones
        CRITICAL_DISTANCE_CM = 50   # < 50cm = CRITICAL
        WARNING_DISTANCE_CM = 100   # < 100cm = WARNING
        
        if distance_cm < CRITICAL_DISTANCE_CM:
            # Check if it's actually an obstacle (not just clutter)
            has_obstacle = any(
                det['class'] in ['person', 'car', 'truck', 'bicycle', 'chair', 'door']
                for det in detections
            )
            
            if has_obstacle or distance_cm < 30:
                return {
                    'category': AlertCategory.OBSTACLE,
                    'level': AlertLevel.CRITICAL,
                    'distance_cm': distance_cm,
                    'message': f"CRITICAL: Obstacle {distance_cm:.0f}cm ahead"
                }
        
        elif distance_cm < WARNING_DISTANCE_CM:
            return {
                'category': AlertCategory.OBSTACLE,
                'level': AlertLevel.WARNING,
                'distance_cm': distance_cm,
                'message': f"Warning: Object {distance_cm:.0f}cm ahead"
            }
        
        return None
    
    def _should_run_ocr(self, detections):
        """
        Decide whether to run expensive OCR processing
        
        Only run if:
        - Text-like objects detected, OR
        - High-value region of interest exists
        """
        
        ocr_triggers = ['text', 'sign', 'label', 'book', 'screen']
        
        for detection in detections:
            if detection['class'].lower() in ocr_triggers:
                return True
        
        # Also run if confidence is high for book/document-like objects
        for detection in detections:
            if (detection['class'] in ['backpack', 'book'] and 
                detection['confidence'] > 0.8):
                return True
        
        return False
    
    def _make_decision(self, detections, text_detections, obstacle_alert, distance_mm):
        """
        Priority-based decision engine:
        1. CRITICAL obstacles override everything
        2. Moving objects (high threat)
        3. Text/signage (informational)
        4. Other objects (low priority)
        """
        
        # Priority 1: Critical obstacles
        if obstacle_alert and obstacle_alert['level'] == AlertLevel.CRITICAL:
            return obstacle_alert
        
        # Priority 2: Moving objects (rough detection based on image features)
        moving_objects = [d for d in detections 
                         if d['class'] in ['person', 'car', 'truck']]
        if moving_objects:
            obj = moving_objects[0]
            return {
                'category': AlertCategory.MOVING_OBJECT,
                'level': AlertLevel.WARNING,
                'object': obj['class'],
                'confidence': obj['confidence'],
                'message': f"{obj['class'].capitalize()} detected"
            }
        
        # Priority 3: Text/Signage
        if text_detections:
            text = text_detections[0].get('text', 'sign')
            return {
                'category': AlertCategory.TEXT,
                'level': AlertLevel.SAFE,
                'text': text,
                'message': f"Sign: {text}"
            }
        
        # Priority 4: Regular object detection
        high_conf_objects = [d for d in detections 
                            if d['confidence'] > self.config.get("detection_confidence")]
        if high_conf_objects:
            obj = high_conf_objects[0]
            return {
                'category': AlertCategory.OBJECT,
                'level': AlertLevel.SAFE,
                'object': obj['class'],
                'confidence': obj['confidence'],
                'message': f"Object: {obj['class']}"
            }
        
        # Priority 5: Warning obstacles
        if obstacle_alert:
            return obstacle_alert
        
        # No alert
        return None
    
    def _execute_alert(self, alert):
        """
        Execute alert output:
        1. Speaker output (text-to-speech)
        2. Vibration pattern
        """
        
        # Check cooldown to avoid alert spam
        current_time = time.time() * 1000  # Convert to ms
        if current_time - self.last_alert_time < self.alert_cooldown:
            return
        
        # Check for duplicate alerts in recent history
        alert_key = (alert['category'], alert.get('message', ''))
        if alert_key in self.recent_alerts:
            return
        
        self.last_alert_time = current_time
        self.recent_alerts.append(alert_key)
        
        message = alert.get('message', 'Alert')
        level = alert.get('level', AlertLevel.SAFE)
        
        logger.info(f"ALERT [{level}]: {message}")
        
        # ==========================================
        # TEXT-TO-SPEECH OUTPUT
        # ==========================================
        
        try:
            self.voice_engine.speak(message)
        except Exception as e:
            logger.error(f"Voice output failed: {e}")
        
        # ==========================================
        # VIBRATION FEEDBACK
        # ==========================================
        
        try:
            self.vibration_controller.vibrate_alert(level)
        except Exception as e:
            logger.error(f"Vibration control failed: {e}")
        
        # Update current alert level
        self.current_alert_level = level
    
    def shutdown(self):
        """Graceful shutdown"""
        
        logger.info("Shutting down backend...")
        self.is_running = False
        
        # Stop vibrations
        try:
            self.vibration_controller.vibrate(0)
        except:
            pass
        
        # Stop audio
        try:
            self.voice_engine.stop()
        except:
            pass
        
        # Close connections
        if self.wireless:
            try:
                self.wireless.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down wireless: {e}")
        
        logger.info("Backend shutdown complete")
    
    def get_stats(self):
        """Return processing statistics"""
        return self.processing_stats.copy()


# ============================================
# MAIN ENTRY POINT
# ============================================

def main():
    """Main entry point"""
    
    print("""
    ╔════════════════════════════════════════╗
    ║   SMART AI CAP - BACKEND PROCESSOR     ║
    ║   Version 1.0 (Engineering-Level)      ║
    ╚════════════════════════════════════════╝
    """)
    
    # Create backend instance
    backend = SmartCapBackend("config/backend_config.json")
    
    # Start processing
    try:
        backend.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
