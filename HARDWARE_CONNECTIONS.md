# Hardware Connections & Wiring Diagram

## 1. COMPLETE WIRING DIAGRAM

```
                        ┌─────────────────────────────────────────┐
                        │    ESP32 DEV BOARD  (30-Pin)            │
                        │                                         │
                        │  3V3  GND  D23  D22  TXD  RXD  D21  D20 │
                        │   │    │    │    │    │    │    │    │ │
                        │   └────┘    │    │    │    │    │    │ │
                        │             │    │    │    │    │    │ │
                        │  D19  D18  D5  D17  D16  D4  D2  D15│
                        │   │    │   │   │    │   │   │    │ │
                        │   │    │   │   │    │   │   │    │ │
                        │  D14  D27 D26 D25  D33 D32  RX  TX │
                        │                                       │
                        │  GND            5V                    │
                        └───┬────────────┬────────────────────┘
                            │            │
        ┌───────────────────┼────────────┼──────────────┐
        │                   │            │              │
        │                   │            │              │
        ↓                   ↓            ↓              ↓
    
    ┌──────────────┐   ┌──────────┐  ┌──────────┐  ┌─────────────┐
    │ ESP32 CAM    │   │HC-SR04   │  │Vibration │  │ Microphone  │
    │              │   │Ultrasonic│  │ Motor    │  │(Earphone)   │
    ├──────────────┤   ├──────────┤  ├──────────┤  ├─────────────┤
    │ GND          │───│GND       │  │GND    ───┼──│GND          │
    │ 5V           │───│VCC(5V)   │  │VCC(+3.3V)│  │MIC+         │
    │ D4 (SDA)     │   │TRIG(D5)  │  │D27(PWM)  │  │ (A12 or X4) │
    │ D18(SCL)     │   │ECHO(D19) │  │          │  │             │
    │ D12(MISO)    │   └──────────┘  └──────────┘  └─────────────┘
    │ D13(MOSI)    │
    │ D14(CLK)     │                  ┌──────────────────┐
    │ D15(CS)      │                  │ 5000mAh Li-Po    │
    │ GND          │                  │ Battery          │
    │ 3V3          │                  ├──────────────────┤
    │ GND          │                  │ Red (+ ) ────────┼───→ 5V Rail
    │ (all pins)   │                  │ Black (- ) ──────┼───→ GND Rail
    │              │                  │                  │
    └──────────────┘                  │ Disconnect when  │
                                      │ not in use!      │
                                      └──────────────────┘


    Optional Components:
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ GPS Module   │  │ IR Camera    │  │ Power        │
    │ (NEO-6M)     │  │ (Thermal)    │  │ Bank         │
    ├──────────────┤  ├──────────────┤  ├──────────────┤
    │ GND → GND    │  │ GND → GND    │  │ 5V → 5V      │
    │ VCC → 3V3    │  │ VCC → 3V3    │  │ GND → GND    │
    │ RX → D1(TX)  │  │ SDA → D21    │  │              │
    │ TX → D3(RX)  │  │ SCL → D22    │  │              │
    └──────────────┘  └──────────────┘  └──────────────┘
```

---

## 2. DETAILED PIN ASSIGNMENTS

### ESP32 GPIO Pin Mapping

```
PIN CONFIGURATION FOR SMART CAP
════════════════════════════════════════════════════════════

CAMERA (ESP32-CAM Module)
─────────────────────────
 ESP32 Pin    →  Function
 D4           →  SDA (I2C)
 D18          →  SCL (I2C)
 D12          →  MISO (SPI)
 D13          →  MOSI (SPI)
 D14          →  CLK  (SPI)
 D15          →  CS   (SPI)
 3V3          →  3.3V Power
 GND          →  Ground

ULTRASONIC SENSOR (HC-SR04)
───────────────────────────
 D5           →  TRIGGER (Output, pulse 10µs)
 D19          →  ECHO (Input, measures pulse width)
 5V Rail      →  VCC Power (use voltage divider for ECHO)
 GND          →  Ground

VIBRATION MOTOR
───────────────
 D27          →  PWM Control (0-255 for intensity)
 3V3 (via relay/FET)  →  Motor Power
 GND          →  Ground

MICROPHONE (Earphone Jack)
──────────────────────────
 A12 (ADC Capable)  →  MIC+ (Audio input)
 GND                →  Common Ground

GPS MODULE (Optional, NEO-6M)
──────────────────────────────
 D1 (TX)      →  RX pin on module
 D3 (RX)      →  TX pin on module
 3V3          →  VCC
 GND          →  Ground

IR CAMERA (Optional, Thermal)
──────────────────────────────
 D21          →  SDA (I2C)
 D22          →  SCL (I2C)
 3V3          →  VCC
 GND          →  Ground

BLUETOOTH/AUDIO (Internal)
───────────────────────────
 Internal     →  Uses WiFi/BLE radio
 Earphone Jack  →  Bluetooth A2DP output

POWER DISTRIBUTION
──────────────────
 5V Rail      →  Generated from Li-Po battery (3.7V → 5V boost)
 3V3 Rail     →  ESP32 internal regulator
 GND (0V)     →  Common ground (all components)
```

---

## 3. POWER DISTRIBUTION SCHEMATIC

```
                    ┌─────────────────────────┐
                    │   5000mAh Li-Po 3.7V    │
                    │      Battery Pack       │
                    └────────┬────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ↓                 ↓
            ┌──────────────┐   ┌─────────────┐
            │ Boost Module │   │ TP4056 LiPo │
            │ 3.7V → 5V    │   │ Charger     │
            │ USB-C Input  │   │             │
            └───────┬──────┘   └────────┬────┘
                    │                   │
                    ├───────────────────┤
                    │   5V Power Rail   │
                    │   (1A max out)    │
                    └────┬──────────────┘
                         │
        ┌────────┬────────┼─────────┬──────────┐
        │        │        │         │          │
        ↓        ↓        ↓         ↓          ↓
    ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
    │ESP32 │ │ESP-32│ │HS-04 │ │Motor │ │ MIC  │
    │3V3R │ │CAM   │ │Ultra │ │Driver│ │Amp   │
    │(600m│ │(5V)  │ │(5V)  │ │(5V)  │ │(5V)  │
    │A)   │ │      │ │      │ │      │ │      │
    └──────┘ └──────┘ └──────┘ └──────┘ └──────┘
        │
        │ 240mA max
        │
    ┌───┴──────────────────────────────────────┐
    │  3.3V Power Rail (from ESP32 regulator)  │
    └────┬──────────────────────────────────┬──┘
         │                                  │
         ↓                                  ↓
    ┌────────────┐                  ┌─────────────┐
    │ GPS Module │                  │ IR Camera   │
    │ (if used)  │                  │ (if used)   │
    └────────────┘                  └─────────────┘


VOLTAGE DIVIDER for HC-SR04 ECHO (Important!)
───────────────────────────────────────────────
The ECHO pin outputs 5V logic, but ESP32 pins are 3.3V max

        5V (from HC-SR04 ECHO)
        │
        ├─────[2.2kΩ resistor]─────┐
        │                          │
        └─────[3.3kΩ resistor]─────┼───→ D19 (GPIO on ESP32)
                                   │
                                   ┴ GND (0V)

Result: ~3.2V → 3.3V max at GPIO (Safe)
```

---

## 4. CIRCUIT BOARD LAYOUT (Compact Cap Design)

```
Top View of Cap (Inside visor):
═════════════════════════════════════════════════════════

        ┌─────────────────────────────────────┐
        │           CAP VISOR                 │
        │     ┌─────────────────────┐        │
        │     │   ESP32 CAM Module  │        │
        │     │  (front, pointing   │        │
        │     │   forward)          │        │
        │     └─────────────────────┘        │
        │                                    │
        │  ┌──────────────────────────────┐  │
        │  │  HC-SR04 Ultrasonic Sensor   │  │
        │  │  (Mounted on sides/front)    │  │
        │  └──────────────────────────────┘  │
        │                                    │
        │     ┌──────────────────────┐      │
        │     │  ESP32 Dev Board     │      │
        │     │  (Main controller)   │      │
        │     └──────────────────────┘      │
        └─────────────────────────────────────┘

Side View (Cross-section):
═════════════════════════════════════════════════════════

        ┌──────────────────────────┐
        │     Foam/Mesh Material   │  ← Lightweight
        │                          │
        │  ┌────────────────────┐  │
        │  │ PCB + Components   │  │  ← Weight: ~150g
        │  └────────────────────┘  │
        │                          │
        └──────────────────────────┘
         ↓
        Head

Weight Distribution:
───────────────────
 ESP32 CAM:        20g
 ESP32 DevBoard:    8g
 HC-SR04 × 2:      12g
 Li-Po Battery:    150g
 Motor & Driver:   20g
 Wiring/PCB:       30g
 Casing/Visor:     100g
 ───────────────────────
 TOTAL:           ~340g (within 400g target)
```

---

## 5. CONNECTOR SPECIFICATIONS

### Recommended Connectors for Reliability

```
Connector Type              Usage                  Advantage
──────────────────────────────────────────────────────────────
USB-C (TP4056)              Battery Charging       Fast, reversible
XT60 or XT90                Battery Main Power     High current, stable
Micro USB (Dev Board)       Programming/Power      Standard, accessible
JST-GH 1.25mm               Sensor connections     Compact, reliable
Dupont 2.54mm (IEC)         Breadboard prototyping Quick testing
                            (DON'T USE in final product)
```

---

## 6. ASSEMBLY INSTRUCTIONS

### Step 1: Prepare PCB
```
1. Mount power distribution board
2. Solder battery (XT60 connector)
3. Add boost converter (3.7V → 5V)
4. Test voltage: 5V at rail, 3.3V at ESP32
```

### Step 2: Mount Main Controller
```
1. Mount ESP32 Dev Board on standoffs
2. Attach USB cable for programming
3. Add power connections (VCC, GND from 5V rail)
```

### Step 3: Attach Sensors
```
1. Mount ESP32 CAM (secure with tape/mount)
   - Pointing directly forward
   - Height: eye level when wearing cap
   
2. Mount HC-SR04 Ultrasonic
   - Trigger: D5
   - Echo: D19
   - Distance: < 5cm above camera
   
3. Connect Vibration Motor
   - PWM to D27
   - GND to common ground
   - Power: 3V through FET driver
```

### Step 4: Add Audio
```
1. Route earphone jack to ear
2. Connect Bluetooth wireless audio
3. Test with speaker before wearing
```

### Step 5: Final Integration
```
1. Test all sensors (See tests/ folder)
2. Secure all wires with silicone loom
3. Mount in cap casing
4. Balance weight (battery at lower back)
5. Enable power → All lights should be on
```

---

## 7. TESTING CHECKLIST

### Hardware Verification

```
□ Battery Output
  - Measure: 3.7V nominal, < 4.2V charged
  - Test: Voltage under load (> 3.5V indicates good battery)

□ Boost Converter
  - Measure: 5V ± 0.2V output
  - Test: Load test with all modules (should stay stable)

□ ESP32 Power
  - Measure: 3.3V at VCC pin
  - Indicator: Blue LED should light up

□ ESP32 CAM
  - Visual: Image should display when powered
  - Command: Send "SNAP" command via serial
  - Result: Should respond with camera frame

□ Ultrasonic Sensor
  - Distance Test: Place hand 30cm away
  - Expected: Should read 30cm ± 2cm
  - Test Code: (See tests/test_ultrasonic.py)

□ Vibration Motor
  - Test: Should vibrate at 50% PWM
  - Visual: Should not rotate (only oscillate)

□ Microphone
  - Record 3 seconds of audio
  - Playback: Should hear clear sample

□ Wireless
  - WiFi: Connect to router, measure RSSI
  - BLE: Scan and verify in Bluetooth devices
  - Data: Transfer 1MB file, verify integrity
```

---

## 8. POWER MANAGEMENT SEQUENCE

```
Startup Sequence:
─────────────────
1. Press power switch → Battery connect
2. ESP32 starts (blue LED flashes)
3. Boot firmware (5-10 seconds)
4. Initialize sensors
5. Connect to WiFi (auto-search known networks)
6. Ready for operation (solid blue LED)

Runtime Power Saving:
───────────────────
- WiFi off when idle → BLE only (20mA)
- Camera low FPS mode → 5 fps at idle
- Motor controlled PWM → Only pulse when needed
- Sleep after 10 min inactivity

Shutdown Sequence:
──────────────────
1. User presses power button (2 seconds)
2. Graceful WiFi disconnect
3. Save session state (optional)
4. GPIO → LOW (power down sensors)
5. ESP32 deep sleep mode (< 1mA)
6. LED off
```

---

## 9. TROUBLESHOOTING GUIDE

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| ESP32 not powering on | Low battery voltage < 3V | Charge battery 4+ hours |
| Camera shows black frame | Lens covered/dirty | Clean lens with soft cloth |
| Ultrasonic reading 0cm | Sensor facing wrong direction | Rotate sensor 180° |
| Wireless connection drops | Weak WiFi signal | Move closer to router |
| Motor not vibrating | PWM pin not connected | Check D27 connection |
| Audio not working | Bluetooth device disconnected | Pair device manually |
| Overheating (> 85°C) | Continuous streaming | Enable sleep mode in firmware |

---

## 10. CAP MECHANICAL DESIGN

```
Front View:
───────────
        ┌─────────────────────────┐
        │   VISOR (Polycarbonate) │
        │                         │
        │  ┌─────────────────┐   │
        │  │   ESP32 CAM     │   │ ← Small lens cutout
        │  │  (Visible lens) │   │
        │  └─────────────────┘   │
        │                         │
        │  ○ ○ ← Ultrasonic        │
        │  (sensors on sides)     │
        └─────────────────────────┘
                  │
              ┌──┴──┐
           FOREHEAD
           
Side View:
───────────
        ─── EAR PIECE FOR
        │   AUDIO
        │
    ┌───┴──────────────┐
    │    CAP INTERIOR  │
    │  ┌────────────┐  │
    │  │ PCB Module │  │ ← Light, compact
    │  └────────────┘  │
    │                  │
    └───────────────┬──┘
                    │
                ┌───┴───┐
                │ chinstrap (velcro)
                │ for secure fit
```

---

## 11. HEAT DISSIPATION STRATEGY

```
Primary Heat Sources:
─────────────────────
1. ESP32 dual-core (max 160mA @ 80°C over time)
2. WiFi radio (peaks at 120mA)
3. Battery internal resistance (low, ~50mΩ)

Heat Management:
────────────────
- Aluminum PCB for better heat sinking
- Thermal pads under ESP32 IC
- Air flow through cap vents
- Temp sensor on D34 (analog input)
- Throttle CPU if > 85°C
- Reduce WiFi power if > 75°C
```

---

## 12. SAFETY REGULATIONS COMPLIANCE

### Electrical Safety
- ✓ Battery protection: TP4056 with over-charge & discharge protection
- ✓ Short circuit protection: Polyfuse on battery line
- ✓ Thermal safety: Temperature monitoring on ESP32
- ✓ EMI compliance: Ferrite beads on WiFi antenna line

### User Safety (for blind users)
- ✓ No dangling wires (all secured in loom)
- ✓ Smooth edges (no sharp PCB corners)
- ✓ Ventilation holes (prevent heat buildup)
- ✓ Emergency disconnect (power button easily accessible)

