"""
Smart AI Cap - Python Package Initialization
Imports all modules for easy access
"""

# AI Modules
from ai_modules.object_detection import ObjectDetector
from ai_modules.ocr_engine import TextRecognizer, SimpleOCRFallback
from ai_modules.voice_output import VoiceEngine, AlertVoicePresets
from ai_modules.vibration_control import VibrationController, SimpleVibrationMock

# Communication
from communication.wireless_protocol import WirelessProtocol, ProtocolFormat

# Utilities
from utils.config_loader import ConfigLoader, FrameBuffer, PerformanceMonitor

# Backend
from backend.main import SmartCapBackend, AlertLevel, AlertCategory

# Version
__version__ = "1.0.0"
__title__ = "Smart AI Assistive Cap for Visually Impaired"
__author__ = "Engineering Team"
__license__ = "MIT"

__all__ = [
    'ObjectDetector',
    'TextRecognizer',
    'VoiceEngine',
    'VibrationController',
    'WirelessProtocol',
    'ConfigLoader',
    'FrameBuffer',
    'SmartCapBackend',
    'AlertLevel',
    'AlertCategory',
]
