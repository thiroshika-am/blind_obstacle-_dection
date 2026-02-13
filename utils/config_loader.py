"""
==========================================
UTILITY MODULES
Configuration loader and frame buffering
==========================================
"""

import json
import logging
import os
from collections import deque

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load and manage configuration from JSON"""
    
    def __init__(self, config_path="config/backend_config.json"):
        """Load configuration from file"""
        
        self.config_path = config_path
        self.config = self._load_config()
        self.defaults = self._get_defaults()
        
        logger.info(f"Configuration loaded from: {config_path}")
    
    def _load_config(self):
        """Load JSON configuration"""
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Config load error: {e}")
                return {}
        else:
            logger.warning(f"Config file not found: {self.config_path}")
            return {}
    
    def _get_defaults(self):
        """Get default configuration values"""
        
        return {
            # AI Models
            'yolo_model_path': 'yolov5s',
            'detection_confidence': 0.5,
            'use_gpu': False,
            'enable_ocr': True,
            
            # Network
            'backend_ip': '0.0.0.0',
            'backend_port': 5000,
            'esp32_ip': '',
            
            # Bluetooth/Audio
            'bluetooth_device': 'SmartCap_BLE',
            'tts_engine': 'pyttsx3',
            'voice_speed': 1.0,
            
            # Alert settings
            'alert_cooldown': 500,  # ms
            'critical_distance': 50,  # cm
            'warning_distance': 100,  # cm
            
            # Performance
            'frame_rate': 10,  # fps
            'max_buffer_size': 10,
        }
    
    def get(self, key, default=None):
        """Get configuration value with fallback"""
        
        if key in self.config:
            return self.config[key]
        elif default is not None:
            return default
        else:
            return self.defaults.get(key)
    
    def save(self, output_path=None):
        """Save configuration to file"""
        
        path = output_path or self.config_path
        
        try:
            with open(path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Config saved: {path}")
        except Exception as e:
            logger.error(f"Config save error: {e}")


class FrameBuffer:
    """
    Circular frame buffer for managing image frames
    
    Provides thread-safe frame queuing
    """
    
    def __init__(self, max_size=10):
        """Initialize frame buffer"""
        
        self.max_size = max_size
        self.frames = deque(maxlen=max_size)
        self.lock = None
        
        try:
            import threading
            self.lock = threading.Lock()
        except:
            self.lock = None
    
    def add_frame(self, frame, metadata=None):
        """Add frame to buffer"""
        
        if self.lock:
            self.lock.acquire()
        
        try:
            if metadata is None:
                metadata = {}
            
            self.frames.append((frame, metadata))
            
        finally:
            if self.lock:
                self.lock.release()
    
    def get_frame(self):
        """Get oldest frame from buffer"""
        
        if self.lock:
            self.lock.acquire()
        
        try:
            if len(self.frames) > 0:
                return self.frames.popleft()
            return None, None
        finally:
            if self.lock:
                self.lock.release()
    
    def has_frame(self):
        """Check if buffer has frames"""
        
        return len(self.frames) > 0
    
    def get_size(self):
        """Get current buffer size"""
        
        return len(self.frames)
    
    def clear(self):
        """Clear all frames"""
        
        if self.lock:
            self.lock.acquire()
        
        try:
            self.frames.clear()
        finally:
            if self.lock:
                self.lock.release()


class PerformanceMonitor:
    """Track performance metrics"""
    
    def __init__(self, window_size=30):
        """
        Initialize performance monitor
        
        Args:
            window_size: Number of samples to average
        """
        
        self.window_size = window_size
        self.latencies = deque(maxlen=window_size)
        self.detections = deque(maxlen=window_size)
        self.fps_values = deque(maxlen=window_size)
        
        self.start_time = None
    
    def record_latency(self, latency_ms):
        """Record frame latency"""
        self.latencies.append(latency_ms)
    
    def record_detections(self, count):
        """Record number of detections"""
        self.detections.append(count)
    
    def record_fps(self, fps):
        """Record FPS"""
        self.fps_values.append(fps)
    
    def get_avg_latency(self):
        """Get average latency in ms"""
        if not self.latencies:
            return 0
        return sum(self.latencies) / len(self.latencies)
    
    def get_avg_detections(self):
        """Get average detections per frame"""
        if not self.detections:
            return 0
        return sum(self.detections) / len(self.detections)
    
    def get_avg_fps(self):
        """Get average FPS"""
        if not self.fps_values:
            return 0
        return sum(self.fps_values) / len(self.fps_values)
    
    def get_stats(self):
        """Get all statistics"""
        return {
            'avg_latency_ms': self.get_avg_latency(),
            'avg_detections': self.get_avg_detections(),
            'avg_fps': self.get_avg_fps(),
            'buffer_usage': f"{len(self.latencies)}/{self.window_size}"
        }

