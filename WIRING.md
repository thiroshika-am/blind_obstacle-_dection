# 🔌 Smart AI Cap - Wiring Diagram

This guide details how to wire the components for the Smart AI Cap project based on the current firmware configuration.

## 🧠 Core Component: ESP32-CAM

The project uses the **AI-Thinker ESP32-CAM** module.

> **⚠️ PINOUT WARNING:** The ESP32-CAM has limited available pins. We safely use **GPIO 12, 13, 14, and 33** as configured in `firmware/esp32_main.cpp`.

---

## 📐 Wiring Schematic

```mermaid
graph TD
    subgraph ESP32-CAM
        GND[GND]
        V5[5V / VCC]
        P12[GPIO 12]
        P13[GPIO 13]
        P14[GPIO 14]
        P33[GPIO 33]
    end

    subgraph "HC-SR04 (Ultrasonic)"
        VCC_US[VCC]
        TRIG[Trig]
        ECHO[Echo]
        GND_US[GND]
    end

    subgraph "Vibration Motor Module"
        VCC_VIB[VCC]
        IN_VIB[Signal / IN]
        GND_VIB[GND]
    end

    subgraph "Status LED (Optional)"
        ANODE[Anode (+)]
        CATHODE[Cathode (-)]
    end

    %% Power Connections
    V5 --> VCC_US
    V5 --> VCC_VIB
    GND --> GND_US
    GND --> GND_VIB
    GND --> CATHODE

    %% Signal Connections
    P12 -- Trigger Signal --> TRIG
    P13 -- Echo Signal --> ECHO
    P14 -- PWM Control --> IN_VIB
    P33 -- Status Signal --> ANODE
```

---

## 📝 Pin Connection Table

| Component | Pin Label | Connection on ESP32-CAM | Description |
| :--- | :--- | :--- | :--- |
| **HC-SR04** | VCC | **5V** | Power supply (requires 5V) |
| | GND | **GND** | Ground |
| | Trig | **GPIO 12** | Trigger pulse output |
| | Echo | **GPIO 13** | Echo pulse input |
| **Vibration Motor** | VCC | **5V / 3.3V** | Motor power (check motor voltage) |
| | GND | **GND** | Ground |
| | IN / Sig | **GPIO 14** | PWM Control signal |
| **Status LED** | Anode (+) | **GPIO 33** | Connect via 220Ω resistor |
| | Cathode (-) | **GND** | Ground |
| **Power** | 5V | **5V** | Main power input (Battery/USB) |
| | GND | **GND** | Common ground |

### ⚡ Powering the System
* **Input Voltage:** Connect a 5V source (like a USB power bank or 5V regulator) to the **5V** and **GND** pins.
* **Current:** The ESP32-CAM + WiFi + Sensors can draw peaks of **>300mA**. Ensure your power source provides at least **1A**.

---

## 🛠️ Flashing Mode Wiring (FTDI Adapter)

To upload code, you need a USB-to-TTL (FTDI) adapter.

| FTDI Adapter | ESP32-CAM | Note |
| :--- | :--- | :--- |
| 5V / VCC | 5V | Powers the board |
| GND | GND | Common ground |
| TX | **GPIO 3** (U0R) | Receive Data |
| RX | **GPIO 1** (U0T) | Transmit Data |
| **GND** | **GPIO 0** | **MUST** connect during boot to flash! |

> **After Flashing:** Remove the wire between **GPIO 0** and **GND**, then press the Reset button to run the code.

---

## 🔍 Troubleshooting Connections

1. **Camera Failures:** If the camera gives errors, check if the Ultrasonic Sensor is interfering. We specifically avoided camera pins (like GPIO 4, 2, 15) to prevent this.
2. **Brownout / Crash:** If the board resets when WiFi turns on, your power supply is too weak. Add a **470µF capacitor** between 5V and GND.
3. **No Sensor Data:** Ensure the HC-SR04 is getting full 5V. It often fails on 3.3V.
