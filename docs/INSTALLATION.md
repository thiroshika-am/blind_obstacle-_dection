# Installation & Setup Guide

## Complete Step-by-Step Installation

This guide walks through every step to get the Smart AI Cap system running.

---

## PART 1: Hardware Assembly (30-45 mins)

### 1.1 Gather Components

✓ **REQUIRED COMPONENTS**

```
□ ESP32 Dev Board ($8-12)
□ ESP32-CAM Module ($10-15) 
□ HC-SR04 Ultrasonic Sensor ($2-3)
□ 6mm Vibration Motor ($3-5)
□ 5000mAh Li-Po Battery ($10-15)
□ TP4056 Charger Module ($2-3)
□ MT3608 5V Boost Converter ($1-2)
□ Resistors: 2x 2.2kΩ, 3x 3.3kΩ
□ Capacitors: 100µF, 10µF
□ Connecting wires (22 AWG)
□ Soldering iron + solder
□ Cap/helmet with visor
```

✓ **OPTIONAL COMPONENTS**

```
□ HR-04 (optional redundant sensor)
□ NEO-6M GPS Module
□ Thermal camera (IR)
□ Small speaker
□ Microphone amplifier
```

### 1.2 Prepare ESP32 Boards

1. Lay out ESP32 Dev Board and ESP32-CAM side-by-side
2. Add 10µF capacitor across power pins on both
3. Add TP4056 charger (if integrating battery)

### 1.3 Wire Ultrasonic Sensor

```
HC-SR04 Connection:
┌──────────────┬─────────────────┐
│ HC-SR04 Pin  │ ESP32 Pin       │
├──────────────┼─────────────────┤
│ VCC (5V)     │ 5V Rail         │
│ GND          │ GND             │
│ TRIG         │ GPIO5           │
│ ECHO         │ GPIO19 (w/ divid)
└──────────────┴─────────────────┘

Voltage Divider for ECHO:
   5V
   │
   ├─[2.2kΩ]─┬─→ GPIO19
   │         │
   └─[3.3kΩ]─┴─ GND
   
   Result: ~3.3V input (safe for ESP32)
```

### 1.4 Wire Vibration Motor

```
Motor Connection:
   3.3V
   │
   ├─[FET Gate Driver]─┬─ PWM from GPIO27
   │                  │
   Motor ──┬──────────┴─ +3.3V
           │
           └─────────────────── GND
```

### 1.5 Wire Camera Module

```
ESP32-CAM Module:
SDA (D4) ──→ I2C on OV2640
SCL (D18) ──→ I2C on OV2640
Power pins connected to 3.3V rail
```

See `HARDWARE_CONNECTIONS.md` for complete pinout!

### 1.6 Final Assembly

1. Mount ESP32 modules on aluminum PCB
2. Connect battery via XT60 connector
3. Mount in cap casing
4. Secure all wires with silicone loom
5. Test all connections with multimeter

---

## PART 2: Firmware Setup (15-20 mins)

### 2.1 Install Arduino IDE

**Windows:**
```powershell
# Download from https://www.arduino.cc/en/software
# Run installer, follow prompts

# Or use chocolatey:
choco install arduino
```

**Linux/Mac:**
```bash
# Download from https://www.arduino.cc/en/software
# Or via package manager:
sudo apt-get install arduino  # Linux
brew install arduino           # macOS
```

### 2.2 Add ESP32 Board Support

1. Open Arduino IDE
2. **File** → **Preferences**
3. In "Additional Boards Manager URLs", add:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Click **OK**
5. Go to **Tools** → **Board** → **Boards Manager**
6. Search for "esp32"
7. Click **Install** (select latest version)
8. Wait for installation to complete

### 2.3 Configure Arduino IDE for ESP32

1. **Tools** → **Board** → Select **ESP32 Dev Module**
2. **Tools** → **Port** → Select your COM port
3. **Tools** → **Flash Frequency** → **80 MHz**
4. **Tools** → **Upload Speed** → **921600**
5. **Tools** → **Serial Monitor** → **115200 baud**

### 2.4 Upload Firmware

1. Copy `firmware/esp32_main.cpp` to a new Arduino sketch
2. **EDIT THESE LINES:**
   ```cpp
   #define WIFI_SSID          "your_wifi_ssid"        // Change this!
   #define WIFI_PASSWORD      "your_wifi_password"    // Change this!
   #define BACKEND_IP         "192.168.x.x"           // Your PC IP
   ```
3. Click **Sketch** → **Verify** (compile check)
4. Click **Sketch** → **Upload**
5. Wait for "Leaving... hard resetting via RTS pin"

### 2.5 Verify Firmware Works

1. Open **Tools** → **Serial Monitor**
2. Should see startup messages:
   ```
   ===== Smart AI Cap Startup =====
   ✓ GPIO pins initialized
   ✓ Camera initialized
   ✓ WiFi connected
   ===== Startup Complete =====
   ```

If not, troubleshoot (see below).

---

## PART 3: Python Backend Setup (20-30 mins)

### 3.1 Install Python 3.8+

**Windows:**
```powershell
# Download from https://www.python.org
# Check "Add Python to PATH" during installation

# Verify:
python --version
```

**Linux:**
```bash
sudo apt-get install python3.9 python3-pip
python3 --version
```

**macOS:**
```bash
brew install python@3.9
python3 --version
```

### 3.2 Install Dependencies

```bash
# Navigate to project directory
cd c:\Smart_AI_Cap\blind_obstacle-_dection

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install requirements
pip install -r config/requirements.txt

# This will download:
# - PyTorch (500MB+)
# - YOLOv5 models (100MB+)
# - OpenCV (50MB+)
# - EasyOCR (500MB+)
# Total: ~1.5GB, takes 10-20 minutes
```

### 3.3 Download AI Models

```bash
# PyTorch/YOLOv5 models
python -c "import yolov5; yolov5.load('yolov5s')"

# EasyOCR models
python -c "import easyocr; reader = easyocr.Reader(['en'])"

# Wait for downloads to complete (~500MB total)
```

### 3.4 Configure Backend

**Edit `config/backend_config.json`:**

```json
{
  "network": {
    "backend_ip": "0.0.0.0",
    "backend_port": 5000,
    "esp32_ip": "192.168.1.100"  ← CHANGE THIS!
  },
  "audio_output": {
    "bluetooth_device": "SmartCap_BLE"  ← CHANGE THIS!
  }
}
```

To find ESP32 IP:
```bash
# From ESP32 Serial Monitor output, or:
arp -a | findstr esp32  # Windows
arp -a | grep esp32     # Linux
```

---

## PART 4: Verify Complete System

### 4.1 Hardware Verification

```bash
# With ESP32 powered and Serial Monitor open:

# Check ultrasonic:
# - Place hand 30cm away
# - Should read ~30cm in Serial Monitor

# Check camera:
# - Should show frame data periodically

# Check motor:
# - Should vibrate when command sent
```

### 4.2 Backend Verification

```bash
# Terminal 1: Start Python backend
python backend/main.py

# Expected output:
# ╔════════════════════════════════════════╗
# ║   SMART AI CAP - BACKEND PROCESSOR     ║
# ╚════════════════════════════════════════╝
# [*] Server listening on 0.0.0.0:5000
# [*] Waiting for ESP32 connection...
```

### 4.3 Connection Test

```bash
# Terminal 2: Test connectivity
curl http://localhost:5000/status

# Should return:
# {"frames_processed": 0, "latency_ms": 0, ...}
```

### 4.4 Full Integration Test

```bash
# With backend running and ESP32 powered:

# Terminal 2:
# 1. Power on ESP32 cap
# 2. Check backend logs for connection
# 3. Allow 10-15 seconds for frames to arrive
# 4. Check Processing logs showing detections

# You should see in backend terminal:
# [INFO] Frame received: type=0x01, distance=450mm
# [INFO] 2 objects detected
# [INFO] Latency: 156.3ms
```

---

## TROUBLESHOOTING INSTALLATION

### Issue: "Python not recognized"

```bash
# Windows - Add to PATH:
# 1. Press Windows+R
# 2. Type: sysdm.cpl
# 3. Advanced → Environment Variables
# 4. Edit PATH, add: C:\Users\YourUser\AppData\Local\Programs\Python\Python39

# Verify:
python --version
```

### Issue: "Arduino COM port not showing"

```bash
# 1. Install CH340 driver (USB-to-UART)
#    Download from: https://sparks.gogo.co.nz/ch340.html
# 
# 2. Restart Arduino IDE
# 
# 3. Check Device Manager (Windows)
#    Should show COM port for CH340 device
```

### Issue: "Upload fails - serial port error"

```
Solution 1: Power cycle ESP32 (disconnect/reconnect power)
Solution 2: Try different USB cable
Solution 3: Hold down Boot button while uploading
Solution 4: Replace CH340 driver
```

### Issue: "WiFi fails - can't connect"

```
Check: 
1. SSID and password correct (case-sensitive)
2. WiFi is 2.4GHz (NOT 5GHz)
3. ESP32 is in WiFi range
4. Other devices can connect to same network
```

### Issue: "Backend can't find models"

```bash
# Manually download:
python -c "import torch; torch.hub.load('ultralytics/yolov5', 'yolov5s')"
python -c "import easyocr; easyocr.Reader(['en'])"

# This ensures models are in cache (~500MB)
```

### Issue: "CUDA not found (GPU error)"

```
Solution: Either:
1. Install NVIDIA CUDA: https://developer.nvidia.com/cuda-downloads
2. Disable GPU in config:
   "use_gpu": false

# GPU is optional - CPU works fine!
```

---

## QUICK REFERENCE: Key Commands

```bash
# Activate Python environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Start backend
python backend/main.py

# Run tests
pytest tests/

# Check ESP32
curl http://localhost:5000/status

# Monitor ESP32 Serial
python -m serial.tools.list_ports  # List ports
# Then open in Arduino IDE Serial Monitor

# Deactivate environment
deactivate
```

---

## NEXT STEPS

✓ Hardware assembled and tested
✓ Firmware uploaded and running  
✓ Python environment working
✓ Backend connected to ESP32

**What's next?**

1. Read [README.md](../README.md) for operation guide
2. Check [HARDWARE_CONNECTIONS.md](../HARDWARE_CONNECTIONS.md) for detailed schematics
3. See [API_REFERENCE.md](API_REFERENCE.md) for programming help
4. Run [tests](../tests) to verify each module

---

**Installation Complete! 🎉**

Your Smart AI Cap is ready to use. Power it on and watch for startup messages!

