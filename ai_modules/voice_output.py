"""
==========================================
VOICE OUTPUT MODULE
Text-to-Speech (TTS) for audio alerts
==========================================

Converts text messages to audio and outputs via:
- Bluetooth speaker
- System default audio output
- Optional: Cloud TTS API
"""

import logging
import queue
import threading
import time

logger = logging.getLogger(__name__)

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    logger.warning("pyttsx3 not installed - install: pip install pyttsx3")

try:
    from google.cloud import texttospeech
    GOOGLE_TTS_AVAILABLE = True
except ImportError:
    GOOGLE_TTS_AVAILABLE = False

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


class VoiceEngine:
    """
    Text-to-Speech engine for generating audio alerts
    
    Supports:
    - pyttsx3: Offline, fast, low latency
    - Google Cloud TTS: High quality, online
    - Microsoft Edge TTS: High quality, online
    """
    
    def __init__(self, tts_engine='pyttsx3', voice_speed=1.0, 
                 voice_id=None, bluetooth_device=None):
        """
        Initialize voice engine
        
        Args:
            tts_engine: 'pyttsx3', 'google', 'edge', or 'system'
            voice_speed: Speech rate (0.5 = slower, 1.0 = normal, 2.0 = faster)
            voice_id: Specific voice ID (engine-dependent)
            bluetooth_device: Name of bluetooth device for audio output
        """
        
        self.engine_name = tts_engine.lower()
        self.voice_speed = voice_speed
        self.voice_id = voice_id
        self.bluetooth_device = bluetooth_device
        self.is_speaking = False
        
        # Speech queue for async operation
        self.speech_queue = queue.Queue()
        self.stop_flag = False
        
        logger.info(f"Initializing TTS engine: {self.engine_name}")
        logger.info(f"Voice speed: {voice_speed}x, Bluetooth: {bluetooth_device}")
        
        # Initialize appropriate engine
        if self.engine_name == 'pyttsx3':
            self._init_pyttsx3()
        elif self.engine_name == 'google':
            self._init_google_tts()
        elif self.engine_name == 'edge':
            self._init_edge_tts()
        else:
            self._init_system_tts()
        
        # Start background speech thread
        self.speech_thread = threading.Thread(
            target=self._speech_worker,
            daemon=True
        )
        self.speech_thread.start()
        
        logger.info("✓ Voice engine initialized")
    
    def _init_pyttsx3(self):
        """Initialize pyttsx3 offline TTS"""
        
        if not PYTTSX3_AVAILABLE:
            logger.error("pyttsx3 required - install: pip install pyttsx3")
            self.engine = None
            return
        
        try:
            self.engine = pyttsx3.init()
            
            # Set properties
            self.engine.setProperty('rate', int(150 * self.voice_speed))  # WPM
            self.engine.setProperty('volume', 0.9)
            
            # List available voices
            voices = self.engine.getProperty('voices')
            logger.info(f"Available voices: {len(voices)}")
            
            # Set preferred voice
            if self.voice_id is None:
                # Use first female voice if available
                for voice in voices:
                    if 'female' in voice.name.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
            
            self.method = 'pyttsx3'
            
        except Exception as e:
            logger.error(f"pyttsx3 init failed: {e}")
            self.engine = None
    
    def _init_google_tts(self):
        """Initialize Google Cloud TTS"""
        
        if not GOOGLE_TTS_AVAILABLE:
            logger.error("Google Cloud TTS requires: pip install google-cloud-texttospeech")
            self.engine = None
            return
        
        try:
            self.engine = texttospeech.TextToSpeechClient()
            self.google_voices = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Neural2-A" if self.voice_id is None else self.voice_id
            )
            self.method = 'google'
            
        except Exception as e:
            logger.error(f"Google TTS init failed: {e}")
            self.engine = None
    
    def _init_edge_tts(self):
        """Initialize Microsoft Edge TTS"""
        
        if not EDGE_TTS_AVAILABLE:
            logger.error("Edge TTS requires: pip install edge-tts")
            self.engine = None
            return
        
        self.engine = edge_tts
        self.method = 'edge'
    
    def _init_system_tts(self):
        """Fallback to system TTS (espeak on Linux, SAPI on Windows)"""
        
        logger.warning("Using fallback system TTS")
        self.engine = None
        self.method = 'system'
    
    def speak(self, text, wait=False):
        """
        Speak text message
        
        Args:
            text: Text to speak
            wait: Block until speech finishes (default: async)
        """
        
        logger.info(f"SPEAK: {text}")
        
        if wait:
            # Synchronous speech
            self._speak_sync(text)
        else:
            # Async speech via queue
            self.speech_queue.put(text)
    
    def _speak_sync(self, text):
        """Synchronously speak text"""
        
        if self.method == 'pyttsx3':
            self._speak_pyttsx3(text)
        elif self.method == 'google':
            self._speak_google(text)
        elif self.method == 'edge':
            self._speak_edge(text)
        else:
            self._speak_system(text)
    
    def _speak_pyttsx3(self, text):
        """pyttsx3 speech generation"""
        
        if self.engine is None:
            logger.error("pyttsx3 engine not initialized")
            return
        
        try:
            self.is_speaking = True
            self.engine.say(text)
            self.engine.runAndWait()
            self.is_speaking = False
            
        except Exception as e:
            logger.error(f"pyttsx3 speech error: {e}")
            self.is_speaking = False
    
    def _speak_google(self, text):
        """Google Cloud TTS speech generation"""
        
        if self.engine is None:
            logger.error("Google TTS engine not initialized")
            return
        
        try:
            self.is_speaking = True
            
            # Create synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Set audio config
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=self.voice_speed
            )
            
            # Generate speech
            response = self.engine.synthesize_speech(
                input=synthesis_input,
                voice=self.google_voices,
                audio_config=audio_config
            )
            
            # Play audio (save to temp file and play via system)
            import tempfile
            import subprocess
            
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                f.write(response.audio_content)
                audio_file = f.name
            
            # Play with ffplay or similar
            try:
                subprocess.run(['ffplay', '-nodisp', '-autoexit', audio_file],
                              timeout=30)
            except:
                pass
            
            self.is_speaking = False
            
        except Exception as e:
            logger.error(f"Google TTS error: {e}")
            self.is_speaking = False
    
    def _speak_edge(self, text):
        """Microsoft Edge TTS speech generation (async)"""
        
        try:
            import asyncio
            import subprocess
            import tempfile
            import os
            
            self.is_speaking = True
            communicate = self.engine.Communicate(text, "en-US-AriaNeural")
            
            temp_file = "temp_speech.mp3" # Define temp_file
            
            try:
                # Use a new event loop to avoid issues if one is already running
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(communicate.save(temp_file))
                loop.close()
            except Exception as e:
                logger.error(f"Edge TTS save error: {e}")
                self.is_speaking = False
                return
            
            # Play file
            try:
                subprocess.run(['ffplay', '-nodisp', '-autoexit', temp_file],
                              timeout=30)
            except Exception as e:
                logger.error(f"Edge TTS play error: {e}")
            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file) # Clean up temp file
            
            self.is_speaking = False
            
        except Exception as e:
            logger.error(f"Edge TTS general error: {e}")
            self.is_speaking = False
    
    def _speak_system(self, text):
        """Fallback system TTS (espeak/SAPI)"""
        
        import subprocess
        import sys
        import os # Added for os.system
        
        try:
            self.is_speaking = True
            
            if sys.platform == 'linux':
                # Linux: espeak
                subprocess.run(['espeak', '-s', str(int(150 * self.voice_speed)), text])
            elif sys.platform == 'win32':
                # Windows: PowerShell SAPI
                # Sanitize text to prevent command injection
                safe_text = text.replace("'", "''").replace('"', '\\"')
                cmd = f'PowerShell -Command "Add-Type –AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{safe_text}\');"'
                os.system(cmd)
            elif sys.platform == 'darwin':
                # macOS: say command
                subprocess.run(['say', text])
            
            self.is_speaking = False
            
        except Exception as e:
            logger.error(f"System TTS error: {e}")
            self.is_speaking = False
    
    def _speech_worker(self):
        """Background thread worker for async speech"""
        
        while not self.stop_flag:
            try:
                # Get text from queue with timeout
                text = self.speech_queue.get(timeout=0.5)
                
                if text is not None:
                    self._speak_sync(text)
                
                self.speech_queue.task_done()
                
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"Speech worker error: {e}")
    
    def stop(self):
        """Stop speech engine"""
        
        logger.info("Stopping voice engine...")
        self.stop_flag = True
        
        try:
            if self.method == 'pyttsx3' and self.engine:
                self.engine.stop()
        except:
            pass
    
    def set_speed(self, speed):
        """Change speech speed"""
        
        self.voice_speed = speed
        
        if self.method == 'pyttsx3' and self.engine:
            self.engine.setProperty('rate', int(150 * speed))
    
    def wait_for_queue(self):
        """Wait until all queued speech is finished"""
        
        self.speech_queue.join()


class AlertVoicePresets:
    """
    Pre-defined voice alerts for common scenarios
    """
    
    @staticmethod
    def critical_obstacle():
        return "CRITICAL! Obstacle ahead, STOP immediately!"
    
    @staticmethod
    def obstacle_warning(distance_cm):
        return f"Warning: Obstacle {distance_cm} centimeters ahead"
    
    @staticmethod
    def object_detected(obj_class):
        return f"{obj_class.capitalize()} detected"
    
    @staticmethod
    def text_sign(text):
        return f"Sign reads: {text}"
    
    @staticmethod
    def person_nearby():
        return "Person detected ahead"
    
    @staticmethod
    def stairs_detected():
        return "Stairs detected, use caution"
    
    @staticmethod
    def door_detected():
        return "Door ahead"

