# 🔌 Smart AI Cap - Wiring Diagram

This guide details how to wire the components for the Smart AI Cap project based on the current firmware configuration.

## 🧠 Core Component: ESP32-CAM (AI-Thinker)

The project uses the **ESP32-CAM** module to handle both vision and sensors.

> **⚠️ PINOUT WARNING:** The ESP32-CAM has limited available pins.  We must use specific pins to avoid conflicts with the camera, SD card, or boot process.

---

## 📐 Visual Wiring Structure

```text
       [ POWER SOURCE (5V) ] 
               | + (Red)
               v
      /------------------\ 
      |  ESP32-CAM Board | 
      |                  |
      |          GND o---+----------------------------------------+-----------------+
      |                  |                                        |                 |
      |           5V o---+--------------------+-------------------|-----------------|------+
      |                  |                    |                   |                 |      |
      |      GPIO 12 o---|----[ Trig ]        |                   |                 |      |
      |      GPIO 13 o---|----[ Echo ]        |                   |                 |      |
      |                  |   (HC-SR04)        |                   |                 |      |
      |                  |                    |                   |                 |      |
      |      GPIO 14 o---|--------------------|----[ Signal ]     |                 |      |
      |                  |                    |    (Vibration)    |                 |      |
      |                  |                    |                   |                 |      |
      |       GPIO 2 o---|--------------------|-------------------|----[ OUT ]      |      |
      |                  |                    |                   |  (IR Sensor)    |      |
      |                  |                    |                   |                 |      |
      |      GPIO 16 o---|--------------------|-------------------|-----------------|----[ TX ]
      |      (U2RX)      |                    |                   |                 |    [ RX ] (Not connected)
      \------------------/                    |                   |                 |   (GPS Module)
                                              |                   |                 |
                                           [ GND ]             [ GND ]           [ GND ]
```

### 📌 Pinout Reference (AI-Thinker Board)

```text
          +--------------------+
          |      ANTENNA       |
          |                    |
          |    [ CAMERA ]      |
          |                    |
          |                    |
   5V  ---| 5V             3V3 |---
  GND  ---| GND            IO16|--- GPS_TX (Yellow)
 IO12  ---| IO12           IO0 |--- (Flash Mode: GND)
 IO13  ---| IO13           IO2 |--- IR_OUT (Green)
 IO15  ---| IO15           IO4 |--- (Flash LED)
 IO14  ---| IO14           IO1 |--- (TX0)
  IO2  ---| IO2            IO3 |--- (RX0)
          +--------------------+
             (SD Card Slot)
```

---

## 📝 Pin Connection Table

| Component | Pin Label | Connection on ESP32-CAM | Description |
| :--- | :--- | :--- | :--- |
| **HC-SR04** | VCC | **5V** | Power |
| | GND | **GND** | Ground |
| | Trig | **GPIO 12** | Trigger Pulse |
| | Echo | **GPIO 13** | Echo Detection |
| **IR Sensor** | VCC | **5V / 3.3V** | Power |
| | GND | **GND** | Ground |
| | OUT | **GPIO 2** | Obstacle Signal (High/Low) |
| **Vibration Motor** | VCC | **5V** | Motor Power |
| | GND | **GND** | Ground |
| | IN / Sig | **GPIO 14** | PWM Control |
| **GPS (NEO-6M)** | VCC | **5V / 3.3V** | Power |
| | GND | **GND** | Ground |
| | TX | **GPIO 16** (U2RX) | GPS sends data to ESP32 |
| | RX | **Not Connected** | ESP32 doesn't need to write to GPS |

### ⚠️ Critical Notes
1. **GPIO 0**: Must be connected to **GND** only when flashing firmware. Disconnect to run.
2. **GPIO 2** (IR Sensor): This pin is also the on-board LED. It might flash during boot. Ensure the IR sensor doesn't pull it strongly to Ground during boot, or flashing might fail.
3. **Power**: The ESP32-CAM consumes a lot of power. Use a **separate 5V regulator** (like LM7805 or a power bank), do not power everything from a laptop USB port if possible.

---

## 🔧 Dual-Board Option (Alternative)

If you have a separate **standard ESP32 Dev Board** ("ESP32 S") in addition to the ESP32-CAM:

1. **ESP32-CAM**: Handles ONLY the Camera and WiFi video stream.
2. **ESP32 Dev Board**: Handles Ultrasonic, IR, Vibration, and GPS.

*This requires changing the code to run on two separate devices.*
