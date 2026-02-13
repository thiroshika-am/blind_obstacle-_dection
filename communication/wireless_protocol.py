"""
==========================================
WIRELESS COMMUNICATION PROTOCOL
WiFi + Bluetooth data transmission
==========================================

Protocol:
- WiFi: Large data (images, frames) - Port 5000
- Bluetooth: Control commands & alerts - BLE
- Format: Binary with header/metadata
"""

import socket
import struct
import json
import logging
import threading
import time
from collections import deque

logger = logging.getLogger(__name__)


class ProtocolFormat:
    """
    Binary communication protocol format
    
    Frame Structure:
    ┌─────────────────────────────────────────┐
    │ HEADER (4 bytes)                        │
    │ 0x4D 0x43 0x41 0x50  [MCAP magic]       │
    ├─────────────────────────────────────────┤
    │ VERSION (1 byte)                        │
    │ 0x01 = version 1                        │
    ├─────────────────────────────────────────┤
    │ TYPE (1 byte)                          │
    │ 0x01 = image frame                     │
    │ 0x02 = sensor data                     │
    │ 0x03 = command response                │
    ├─────────────────────────────────────────┤
    │ LENGTH (4 bytes, little-endian)        │
    │ Size of payload                        │
    ├─────────────────────────────────────────┤
    │ METADATA (variable)                    │
    │ JSON: {timestamp, distance, rssi}      │
    ├─────────────────────────────────────────┤
    │ PAYLOAD (variable)                     │
    │ Image data or sensor data              │
    ├─────────────────────────────────────────┤
    │ CHECKSUM (4 bytes)                     │
    │ CRC32 of entire frame                  │
    └─────────────────────────────────────────┘
    """
    
    MAGIC_BYTES = b'MCAP'
    VERSION = 1
    
    # Frame types
    FRAME_IMAGE = 0x01
    FRAME_SENSOR = 0x02
    FRAME_COMMAND = 0x03
    FRAME_RESPONSE = 0x04


class WirelessProtocol:
    """
    Manages WiFi and Bluetooth communication with ESP32
    """
    
    def __init__(self, backend_ip="0.0.0.0", backend_port=5000, esp32_ip="", esp32_port=5000):
        """
        Initialize wireless protocol handler
        
        Args:
            backend_ip: IP to listen on (server)
            backend_port: TCP port for WiFi frames
            esp32_ip: IP of ESP32 (if pushing data)
            esp32_port: ESP32 port
        """
        
        self.backend_ip = backend_ip
        self.backend_port = backend_port
        self.esp32_ip = esp32_ip
        self.esp32_port = esp32_port
        
        # Socket connections
        self.server_socket = None
        self.client_socket = None
        self.esp32_socket = None
        
        # Frame buffering
        self.frame_buffer = deque(maxlen=10)
        self.last_metadata = {}
        
        # Statistics
        self.stats = {
            'frames_received': 0,
            'frames_sent': 0,
            'bytes_received': 0,
            'bytes_sent': 0,
            'connection_errors': 0
        }
        
        logger.info(f"Wireless protocol initialized")
        logger.info(f"  Backend: {backend_ip}:{backend_port}")
        logger.info(f"  ESP32: {esp32_ip}:{esp32_port}")
        
        # Start listening for connections
        self._start_server()
    
    def _start_server(self):
        """Start TCP server to receive frames from ESP32"""
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.backend_ip, self.backend_port))
            self.server_socket.listen(1)
            
            logger.info(f"✓ Server listening on {self.backend_ip}:{self.backend_port}")
            
            # Accept connection in background thread
            def accept_connection():
                while True:
                    try:
                        client_sock, addr = self.server_socket.accept()
                        logger.info(f"Client connected: {addr}")
                        self.client_socket = client_sock
                        
                        # Receive frames from this client
                        self._receive_from_client(client_sock)
                        
                    except Exception as e:
                        logger.error(f"Connection error: {e}")
                        self.stats['connection_errors'] += 1
                        time.sleep(1)
            
            # Start in background thread
            thread = threading.Thread(target=accept_connection, daemon=True)
            thread.start()
            
        except Exception as e:
            logger.error(f"Server start failed: {e}")
    
    def _receive_from_client(self, client_sock):
        """Receive frames from connected ESP32 client"""
        
        try:
            while True:
                # Receive frame
                frame_data = self._receive_frame_data(client_sock)
                
                if frame_data is None:
                    logger.warning("Client disconnected")
                    break
                
                self.frame_buffer.append(frame_data)
                self.stats['frames_received'] += 1
                
        except Exception as e:
            logger.error(f"Receive error: {e}")
    
    def _receive_frame_data(self, sock):
        """
        Receive a single frame from socket
        
        Returns: (frame_bytes, metadata_dict, frame_type) or None
        """
        
        def _receive_n_bytes(n):
            """Helper to receive exactly n bytes"""
            data = b''
            while len(data) < n:
                try:
                    chunk = sock.recv(n - len(data))
                    if not chunk:
                        return None
                    data += chunk
                except Exception:
                    return None
            return data

        try:
            # Read header (4 + 1 + 1 + 4 = 10 bytes)
            header = _receive_n_bytes(10)
            if not header:
                return None
            
            magic, version, frame_type, length = struct.unpack('<4sBBI', header)
            
            # Verify magic bytes
            if magic != ProtocolFormat.MAGIC_BYTES:
                logger.warning("Invalid magic bytes")
                return None
            
            logger.debug(f"Frame type: 0x{frame_type:02x}, Length: {length}")
            
            # Read metadata (JSON)
            len_bytes = _receive_n_bytes(4)
            if not len_bytes: return None
            metadata_len = struct.unpack('<I', len_bytes)[0]
            
            metadata_bytes = _receive_n_bytes(metadata_len)
            if not metadata_bytes: return None
            metadata_json = metadata_bytes.decode('utf-8')
            metadata = json.loads(metadata_json)
            
            # Read payload
            payload = b''
            remaining = length - metadata_len - 4
            if remaining > 0:
                payload = _receive_n_bytes(remaining)
                if not payload: return None
            
            # Read checksum
            checksum_bytes = _receive_n_bytes(4)
            if not checksum_bytes: return None
            checksum = struct.unpack('<I', checksum_bytes)[0]
            
            # Verify checksum (CRC32)
            import zlib
            calculated_crc = zlib.crc32(header + struct.pack('<I', metadata_len) + 
                                       metadata_json.encode() + payload) & 0xffffffff
            
            if calculated_crc != checksum:
                logger.warning("Checksum mismatch")
                return None
            
            # Update statistics
            self.stats['bytes_received'] += len(header) + len(metadata_json) + len(payload)
            self.last_metadata = metadata
            
            logger.debug(f"Frame received: type=0x{frame_type:02x}, "
                        f"distance={metadata.get('distance')}mm")
            
            return (payload, metadata, frame_type)
            
        except Exception as e:
            logger.error(f"Frame receive error: {e}")
            return None
    
    def receive_frame(self, timeout=2.0):
        """
        Get next frame from buffer
        
        Args:
            timeout: Wait timeout in seconds
        
        Returns:
            Frame bytes or None
        """
        
        start = time.time()
        
        while (time.time() - start) < timeout:
            if self.frame_buffer:
                frame_data = self.frame_buffer.popleft()
                return frame_data[0]  # Return just the payload
            
            time.sleep(0.01)
        
        return None
    
    def get_metadata(self):
        """Return last received metadata"""
        return self.last_metadata.copy()
    
    def send_command(self, command_type, data):
        """
        Send command to ESP32
        
        Args:
            command_type: Command code
            data: Command data (bytes or dict)
        """
        
        if self.client_socket is None:
            logger.warning("No ESP32 connected")
            return False
        
        try:
            # Build frame
            if isinstance(data, dict):
                payload = json.dumps(data).encode()
            else:
                payload = data
            
            metadata = {
                'timestamp': time.time(),
                'command': command_type
            }
            metadata_json = json.dumps(metadata).encode()
            
            # Build header
            # The total length of the frame payload (metadata_len + metadata_json + payload)
            # The receiver expects length to be (metadata_len + metadata_json_bytes + payload_bytes)
            # metadata_len is 4 bytes (I)
            # metadata_json_bytes is len(metadata_json)
            # payload_bytes is len(payload)
            # So, length = 4 + len(metadata_json) + len(payload)
            length = 4 + len(metadata_json) + len(payload)
            
            # Format: [MAGIC][VER][TYPE][LEN]
            # <4s B B I
            header = struct.pack('<4sBBI',
                                ProtocolFormat.MAGIC_BYTES,
                                ProtocolFormat.VERSION,
                                ProtocolFormat.FRAME_COMMAND, # This is the frame type for commands
                                length
            )
            
            # Calculate checksum
            import zlib
            checksum = zlib.crc32(header + metadata_json + payload) & 0xffffffff
            
            # Send frame
            self.client_socket.sendall(header)
            self.client_socket.sendall(struct.pack('<I', len(metadata_json)))
            self.client_socket.sendall(metadata_json)
            self.client_socket.sendall(payload)
            self.client_socket.sendall(struct.pack('<I', checksum))
            
            self.stats['frames_sent'] += 1
            self.stats['bytes_sent'] += len(header) + len(metadata_json) + len(payload) + 4
            
            logger.debug(f"Command sent: type=0x{command_type:02x}")
            return True
            
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False
    
    def vibrate_remote(self, intensity, duration_ms=100):
        """Send vibration command to ESP32"""
        
        self.send_command(0x10, {
            'action': 'vibrate',
            'intensity': intensity,
            'duration_ms': duration_ms
        })
    
    def shutdown(self):
        """Close connections"""
        
        logger.info("Closing wireless connections...")
        
        try:
            if self.client_socket:
                self.client_socket.close()
            if self.server_socket:
                self.server_socket.close()
        except:
            pass
    
    def get_stats(self):
        """Return communication statistics"""
        return self.stats.copy()


class BluetoothLE:
    """
    Simplified Bluetooth Low Energy (BLE) communication
    
    For control commands and low-bandwidth alerts
    """
    
    def __init__(self, device_name="SmartCap_BLE"):
        """Initialize BLE"""
        
        self.device_name = device_name
        self.connected = False
        
        logger.info(f"BLE initialized: {device_name}")
    
    def send(self, data):
        """Send data via BLE"""
        
        logger.info(f"BLE send: {data}")
    
    def receive(self, timeout=1.0):
        """Receive data via BLE"""
        
        # Placeholder
        return None

