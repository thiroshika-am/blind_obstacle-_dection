"""
==========================================
VIBRATION ALERT CONTROL MODULE
Haptic feedback via Bluetooth to vibration motor
==========================================

Patterns:
- SAFE: No vibration
- WARNING: 3 pulses
- CRITICAL: Continuous rapid pulses
"""

import logging
import time
import threading
import serial

logger = logging.getLogger(__name__)

try:
    from PyQt5.QtBluetooth import QBluetoothSocket, QBluetoothAddress
    PYQT_BLUETOOTH_AVAILABLE = True
except ImportError:
    PYQT_BLUETOOTH_AVAILABLE = False


class VibrationController:
    """
    Control vibration motor via Bluetooth or serial connection
    """
    
    # Alert patterns
    PATTERNS = {
        0: {'name': 'SAFE', 'intensity': 0, 'pattern': []},
        1: {
            'name': 'WARNING', 
            'intensity': 150,
            'pattern': [(100, 100), (100, 100), (100, 0)]  # (on_ms, off_ms)
        },
        2: {
            'name': 'CRITICAL',
            'intensity': 255,
            'pattern': [(50, 50), (50, 50), (50, 50), (500, 0)]  # 3 rapid pulses then wait
        }
    }
    
    def __init__(self, bluetooth_device="SmartCap_BLE", serial_port=None):
        """
        Initialize vibration controller
        
        Args:
            bluetooth_device: Name of Bluetooth device
            serial_port: Optional serial port for wired connection
        """
        
        self.bluetooth_device = bluetooth_device
        self.serial_port = serial_port
        self.connection = None
        self.is_running = False
        self.current_pattern = None
        
        logger.info(f"Initializing vibration controller")
        logger.info(f"  Bluetooth device: {bluetooth_device}")
        logger.info(f"  Serial port: {serial_port}")
        
        # Try to connect via Bluetooth
        if not self._connect_bluetooth():
            logger.warning("Bluetooth failed, trying serial...")
            self._connect_serial()
        
        logger.info("✓ Vibration controller initialized")
    
    def _connect_bluetooth(self):
        """Connect via Bluetooth"""
        
        try:
            # Try using PyBluez
            try:
                import bluetooth
                
                # Search for device
                nearby_devices = bluetooth.discover_devices()
                target_addr = None
                
                for addr in nearby_devices:
                    name = bluetooth.lookup_name(addr, cached=False)
                    if name and self.bluetooth_device.lower() in name.lower():
                        target_addr = addr
                        break
                
                if target_addr:
                    logger.info(f"Found device: {target_addr}")
                    
                    # Connect
                    sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                    sock.connect((target_addr, 1))
                    self.connection = sock
                    logger.info("✓ Bluetooth connected")
                    return True
                else:
                    logger.warning(f"Device not found: {self.bluetooth_device}")
                    return False
                    
            except ImportError:
                logger.warning("PyBluez not available")
                return False
                
        except Exception as e:
            logger.error(f"Bluetooth connection failed: {e}")
            return False
    
    def _connect_serial(self):
        """Connect via serial port (USB or wired)"""
        
        if not self.serial_port:
            logger.warning("No serial port specified")
            return False
        
        try:
            self.connection = serial.Serial(
                port=self.serial_port,
                baudrate=115200,
                timeout=1.0
            )
            logger.info(f"✓ Serial connected: {self.serial_port}")
            return True
            
        except Exception as e:
            logger.error(f"Serial connection failed: {e}")
            return False
    
    def vibrate(self, intensity, duration_ms=100):
        """
        Simple vibration control
        
        Args:
            intensity: 0-255 (0=off, 255=max)
            duration_ms: Duration in milliseconds
        """
        
        if self.connection is None:
            logger.warning("No connection available")
            return
        
        try:
            # Send vibration command
            # Format: 'V' + intensity (0-255) + duration (ms)
            cmd = bytes([ord('V'), intensity, duration_ms & 0xFF, (duration_ms >> 8) & 0xFF])
            
            if hasattr(self.connection, 'write'):
                self.connection.write(cmd)
            else:
                self.connection.send(cmd)
                
        except Exception as e:
            logger.error(f"Vibration control error: {e}")
    
    def vibrate_alert(self, alert_level):
        """
        Execute pre-defined vibration pattern for alert level
        
        Args:
            alert_level: 0=SAFE, 1=WARNING, 2=CRITICAL
        """
        
        if alert_level not in self.PATTERNS:
            logger.warning(f"Unknown alert level: {alert_level}")
            return
        
        pattern = self.PATTERNS[alert_level]
        logger.info(f"Vibration alert [{pattern['name']}]")
        
        if pattern['pattern']:
            # Execute pattern in background thread
            thread = threading.Thread(
                target=self._execute_pattern,
                args=(pattern,),
                daemon=True
            )
            thread.start()
    
    def _execute_pattern(self, pattern):
        """Execute vibration pattern in background"""
        
        try:
            for on_ms, off_ms in pattern['pattern']:
                if on_ms > 0:
                    self.vibrate(pattern['intensity'], on_ms)
                    time.sleep(on_ms / 1000.0)
                
                if off_ms > 0:
                    time.sleep(off_ms / 1000.0)
                    
        except Exception as e:
            logger.error(f"Pattern execution error: {e}")
    
    def custom_pattern(self, pattern):
        """
        Execute custom vibration pattern
        
        Args:
            pattern: List of (intensity, duration_ms) tuples
        """
        
        thread = threading.Thread(
            target=lambda: self._execute_custom_pattern(pattern),
            daemon=True
        )
        thread.start()
    
    def _execute_custom_pattern(self, pattern):
        """Execute custom pattern"""
        
        try:
            for intensity, duration in pattern:
                self.vibrate(intensity, duration)
                time.sleep(duration / 1000.0)
        except Exception as e:
            logger.error(f"Custom pattern error: {e}")
    
    def pulse(self, count=3, intensity=200, interval_ms=100):
        """
        Simple pulse pattern (commonly used for alerts)
        
        Args:
            count: Number of pulses
            intensity: Pulse intensity (0-255)
            interval_ms: Time between pulses
        """
        
        pattern = [(intensity, interval_ms // 2) for _ in range(count)]
        self.custom_pattern(pattern)
    
    def close(self):
        """Close connection"""
        
        try:
            if self.connection:
                if hasattr(self.connection, 'close'):
                    self.connection.close()
                elif hasattr(self.connection, 'disconnect'):
                    self.connection.disconnect()
                    
            logger.info("Connection closed")
            
        except Exception as e:
            logger.error(f"Close error: {e}")


class SimpleVibrationMock:
    """
    Fallback vibration controller that just logs (for testing without hardware)
    """
    
    def __init__(self, bluetooth_device=None, serial_port=None):
        logger.info("Using MOCK vibration controller (no hardware)")
        self.last_command = None
    
    def vibrate(self, intensity, duration_ms=100):
        self.last_command = f"VIBRATE: intensity={intensity}, duration={duration_ms}ms"
        logger.info(self.last_command)
    
    def vibrate_alert(self, alert_level):
        levels = {0: "SAFE", 1: "WARNING", 2: "CRITICAL"}
        logger.info(f"VIBRATION ALERT: {levels.get(alert_level, 'UNKNOWN')}")
    
    def custom_pattern(self, pattern):
        logger.info(f"CUSTOM PATTERN: {pattern}")
    
    def pulse(self, count=3, intensity=200, interval_ms=100):
        logger.info(f"PULSE: {count} x {intensity} ({interval_ms}ms interval)")
    
    def close(self):
        logger.info("Mock controller closed")

