# Smart AI Assistive Cap - System Architecture

## 1. SYSTEM OVERVIEW

### Project Vision
A lightweight, wearable smart cap that provides real-time environmental awareness to visually impaired users through AI-powered object detection, text recognition, and multi-modal feedback (audio + haptic).

### Key Objectives
- Real-time obstacle detection (< 500ms latency)
- Object recognition and classification
- Text recognition (OCR) for signage/documents
- Multi-modal feedback (voice + vibration alerts)
- Battery life: 4-6 hours continuous use
- Lightweight: < 400g total weight
- Low power consumption: < 5W average

---

## 2. SYSTEM ARCHITECTURE LAYERS

### Layer 1: Sensor Layer (Hardware)
```
┌─────────────────────────────────────────┐
│        SENSOR LAYER (Hardware)          │
├─────────────────────────────────────────┤
│ • ESP32 CAM (640x480 @ 30fps)          │
│ • Ultrasonic Sensor (HC-SR04)          │
│ • IR Camera (Optional, night vision)    │
│ • GPS Module (Optional, navigation)     │
│ • Microphone (Audio input)              │
│ • Vibration Motor (Haptic feedback)     │
│ • Lithium Battery (5000mAh)             │
└─────────────────────────────────────────┘
```

### Layer 2: Firmware Layer (ESP32)
```
┌─────────────────────────────────────────┐
│    FIRMWARE LAYER (ESP32)               │
├─────────────────────────────────────────┤
│ • Real-time sensor polling              │
│ • Image capture & compression           │
│ • Ultrasonic distance calculation       │
│ • Wireless transmission (WiFi/BLE)      │
│ • Low-latency sensor fusion             │
│ • Power management & sleep modes        │
└─────────────────────────────────────────┘
```

### Layer 3: Communication Layer (Wireless)
```
┌─────────────────────────────────────────┐
│  COMMUNICATION LAYER (WiFi/Bluetooth)   │
├─────────────────────────────────────────┤
│ • WiFi: Fast data (images, video)      │
│ • Bluetooth: Low-power control/alerts   │
│ • Protocol: Custom binary format        │
│ • Encryption: AES-128 (future)          │
│ • Latency: < 200ms one-way             │
└─────────────────────────────────────────┘
```

### Layer 4: Processing Layer (Python Backend)
```
┌─────────────────────────────────────────┐
│   PROCESSING LAYER (Python Backend)     │
├─────────────────────────────────────────┤
│ • Image reception & buffering           │
│ • Pre-processing (resize, normalize)    │
│ • Object detection (YOLO/MobileNet)     │
│ • OCR processing (Tesseract/EasyOCR)    │
│ • Decision making & prioritization      │
│ • Output command generation             │
└─────────────────────────────────────────┘
```

### Layer 5: Output Layer (User Feedback)
```
┌─────────────────────────────────────────┐
│    OUTPUT LAYER (Feedback to User)      │
├─────────────────────────────────────────┤
│ • Text-to-Speech (Bluetooth audio)      │
│ • Vibration patterns (Haptic motor)     │
│ • Multi-priority alert system           │
└─────────────────────────────────────────┘
```

---

## 3. COMPLETE SYSTEM DATA FLOW

```
USER WEARING CAP
       ↓
   Sensors Capture Data
   ├── ESP32 CAM: Takes 640x480 image
   ├── Ultrasonic: Measures distance (0-4m)
   └── Microphone: Captures audio (optional)
       ↓
   ESP32 Firmware Processing
   ├── Compress image (JPEG 85% quality)
   ├── Extract frame metadata
   └── Bundle sensor data
       ↓
   Wireless Transmission (WiFi)
   └── Send to backend PC/Server
       ↓
   Python Backend Processing
   ├── Receive & decode frame
   ├── Run Object Detection (YOLO)
   ├── Run OCR if text detected
   └── Analyze ultrasonic data
       ↓
   Decision Engine
   ├── Prioritize detected objects
   ├── Generate alert messages
   └── Create vibration patterns
       ↓
   Multi-Modal Output
   ├── Text-to-Speech: "Car approaching from left"
   ├── Vibration: 3 pulses (danger level)
   └── Send to Bluetooth audio
       ↓
   USER RECEIVES FEEDBACK (< 500ms latency)
```

---

## 4. DETAILED BLOCK DIAGRAM

```
                       ┌──────────────────────────────┐
                       │     SENSOR LAYER             │
                       ├──────────────────────────────┤
                       │  ESP32 CAM    Ultrasonic     │
                       │      ↓             ↓         │
                       │   CMOS        Dist Meter    │
                       │  640x480      (0-4m)        │
                       └──────────────┬───────────────┘
                                      │
                                      ↓
                       ┌──────────────────────────────┐
                       │    ESP32 DEV BOARD           │
                       │  (Main Controller)           │
                       ├──────────────────────────────┤
                       │ • Dual-core 240MHz ARM       │
                       │ • 4MB Flash, 520KB RAM       │
                       │ • WiFi 802.11b/g/n           │
                       │ • Bluetooth 4.2 (BLE)        │
                       │ • GPIO for sensors           │
                       │ • ADC for ultrasonic         │
                       └─────────┬──────────────────┐──┘
                                 │                  │
                    ┌────────────┴─┐         ┌──────┴────┐
                    ↓               ↓        ↓            ↓
            ┌───────────────┐ ┌──────────┐ ┌──┐    ┌──────────┐
            │   WiFi TX     │ │ Bluetooth│ │  │    │  Motor   │
            │   (Images)    │ │ (Audio)  │ │  │    │ Driver   │
            │               │ │          │ │  │    │ (Haptic) │
            └───────┬───────┘ └─────┬────┘ │  │    └──────────┘
                    │               │      │  │
                    ↓               ↓      │  │ Power Control
            ┌───────────────────────┐      │  │
            │   WIRELESS NETWORK    │      │  │
            │  (WiFi to Backend PC) │      │  │
            └───────────┬───────────┘      │  │
                        │                  │  │
                   ┌────┴────────────────┐ │  │
                   │                     ↓ ↓  ↓
                   │           ┌──────────────────┐
                   │           │ POWER MANAGEMENT │
                   │           ├──────────────────┤
                   │           │ 5000mAh Li Battery
                   │           │ Voltage regulator
                   │           │ Low-power mode
                   │           └──────────────────┘
                   ↓
         ┌──────────────────────────────────┐
         │  BACKEND PROCESSING (Python PC)  │
         ├──────────────────────────────────┤
         │ • Image Receiver                 │
         │ • Object Detection (YOLO)        │
         │ • OCR Module (EasyOCR)           │
         │ • Decision Engine                │
         │ • Bluetooth TTS Output           │
         │ • Vibration Alert Control       │
         └──────────────────┬───────────────┘
                            │
                    ┌───────┴──────┐
                    ↓              ↓
            ┌────────────────┐ ┌─────────────┐
            │ Bluetooth TTS  │ │ Vibration   │
            │  (Speaker)     │ │ Control     │
            └────────────────┘ └─────────────┘
                    ↓                ↓
            ┌─────────────────────────────┐
            │    FEEDBACK TO USER         │
            │  Audio + Haptic Alerts      │
            └─────────────────────────────┘
```

---

## 5. COMPONENT SPECIFICATIONS

| Component | Model | Power | Specs |
|-----------|-------|-------|-------|
| Main MCU | ESP32 Dev Board | 80-160mA | Dual-core, WiFi/BLE |
| Camera | ESP32 CAM | 160-180mA | OV2640 CMOS, 640x480 |
| Distance Sensor | HC-SR04 | 15mA | 2cm-4m range, 40kHz |
| Vibration Motor | 6mm Micro | 20mA | 3V operating, 9000RPM |
| Battery | 5000mAh Li-Po | - | 3.7V nominal, 18.5Wh |
| TTS | Via Bluetooth | 50mA | Bluetooth A2DP |
| GPS (Optional) | NEO-6M | 40mA | 5Hz update rate |

---

## 6. POWER BUDGET ANALYSIS

### Worst-Case Power Consumption
```
Component               Active Mode    Sleep Mode
────────────────────────────────────────────────
ESP32 Core             160mA          15mA
ESP32 CAM              160mA          5mA
Ultrasonic Sensor      15mA           0mA
Vibration Motor        20mA (brief)   0mA
WiFi/Bluetooth         80-120mA       0mA (BLE only: 20mA)
────────────────────────────────────────────────
TOTAL Active:          ~535mA
Idle (BLE only):       ~35mA
```

### Battery Life Calculation
```
5000mAh battery @ 300mA average (mixed operation)
= 5000 / 300 = 16.7 hours theoretical
With losses (80% efficiency) = ~13 hours
Continuous heavy use (500mA) = ~6 hours
Light use (150mA) = ~30 hours
```

---

## 7. LATENCY ANALYSIS

### End-to-End Latency Budget (Target: < 500ms)

```
1. Image Capture:              ~33ms   (30fps)
2. JPEG Compression:           ~50ms
3. WiFi Transmission:          ~100ms  (typical WiFi RTT)
4. Python Reception:           ~10ms
5. Pre-processing:             ~30ms
6. Object Detection (YOLO):    ~150ms  (lightweight model)
7. Post-processing:            ~20ms
8. Decision + Text Generation: ~20ms
9. TTS Generation:             ~50ms
10. Audio Transmission:        ~30ms
────────────────────────────────────────
TOTAL:                         ~493ms ✓ (Within budget)
```

---

## 8. PRIORITY-BASED ALERT SYSTEM

### Alert Hierarchy

```
Priority 1: CRITICAL OBSTACLES (Collision Risk)
├── Type: Stationary object < 50cm away
├── Ultrasonic distance < threshold
├── Audio: "OBSTACLE AHEAD - STOP!"
└── Haptic: 5 rapid pulses (danger mode)

Priority 2: MOVING OBJECTS (Dynamic Threats)
├── Type: Person, vehicle, moving obstacle
├── Velocity > threshold
├── Audio: "Car approaching from left"
└── Haptic: 3 medium pulses (warning)

Priority 3: TEXT/SIGNAGE (Information)
├── Type: Road signs, labels, text on objects
├── Confidence > 80%
├── Audio: "Street sign: One Way"
└── Haptic: 1 soft pulse (notification)

Priority 4: OBJECTS (Environmental Awareness)
├── Type: Chair, door, stairs, etc.
├── Confidence > 70%
├── Audio: (Optional, low priority)
└── Haptic: Single pulse (informational)
```

---

## 9. SAFETY FEATURES

### Real-Time Safety Mechanisms

1. **Watchdog Timer**: Resets ESP32 if firmware hangs
2. **Connection Loss Detection**: Alert if WiFi disconnects for > 2 seconds
3. **Sensor Validation**: Check ultrasonic readings for anomalies
4. **Over-Temperature Protection**: Throttle if > 80°C
5. **Battery Low Warning**: Alert at 10%, power-off at 5%
6. **Emergency Failsafe**: Continuous audio beep if backend disconnects
7. **Motion Detection**: Alert if unstable/falling motion detected

---

## 10. MODULAR DESIGN PHILOSOPHY

### Independent Modules
- Each subsystem (detection, OCR, vibration) is standalone
- Failure in one module doesn't crash entire system
- Components can be swapped or disabled
- Future: Easy to add GPS, cloud processing, etc.

### Communication Contracts
- Fixed protocol between firmware and backend
- Backward compatible versions
- JSON + binary hybrid format
- Graceful degradation on protocol mismatch

---

## 11. SCALABILITY & FUTURE EXPANSION

### Phase 1 (Current)
- Basic obstacle detection
- Object recognition
- Simple OCR

### Phase 2 (Near-term)
- GPS navigation
- Local ML inference (edge computing)
- Cloud backup processing
- Mobile app control

### Phase 3 (Long-term)
- Offline AI on ESP32 (TensorFlow Lite)
- Advanced gesture recognition
- Multi-user network
- Cloud analytics dashboard

---

## 12. DESIGN CONSTRAINTS & TRADE-OFFS

| Constraint | Solution | Trade-off |
|-----------|----------|-----------|
| Limited RAM on ESP32 | Stream compression, small buffers | Lower image quality |
| WiFi power consumption | Use BLE for control, WiFi for data | Slightly higher latency |
| Processing capacity | Lightweight YOLO models | Reduced accuracy vs. heavy models |
| Cap weight limit | Modular design, aluminum PCBs | Complex assembly |
| Cost requirement | Budget parts, open-source AI | Some features optional |

