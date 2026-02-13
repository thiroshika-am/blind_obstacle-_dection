# Smart AI Cap - Development & Implementation Plan

This document outlines the roadmap to take the Smart AI Cap from its current state (code fixed, theoretically functional) to a fully deployed and optimized assistive device.

---

## 🟢 Phase 1: Code Stabilization & Mock Testing (Current Status)
**Goal:** Ensure the software stack works reliably on the PC before involving complex hardware.

- [x] **Codebase Recovery** (Completed)
    - Fix critical import errors in `backend/main.py`.
    - Resolve GPIO pin conflicts in `firmware/esp32_main.cpp`.
    - Harmonize WiFi protocol formats.
    - Patch security vulnerabilities in TTS.
- [ ] **Dependency Verification**
    - Install full requirements: `pip install -r config/requirements.txt`.
    - Verify heavy libraries (`torch`, `ultralytics`, `easyocr`) function on the host machine.
- [ ] **Mock Simulation**
    - Run the backend in "Mock Mode" (simulated camera/sensors).
    - Verify that TTS speaks correctly when objects are "detected".
    - Verify that vibration commands are generated (logged) for "obstacles".

## 🟡 Phase 2: Hardware Assembly & Firmware
**Goal:** Build the physical device and establish a connection.

- [ ] **Component Sourcing**
    - ESP32-CAM, Ultrasonic Sensor (HC-SR04), Vibration Motor, Battery.
- [ ] **Wiring & Soldering**
    - Follow the **UPDATED** pinout (Trigger: 12, Echo: 13, Vibro: 14).
    - **Critical:** Ensure common ground between all components.
- [ ] **Firmware Flashing**
    - Configure WiFi SSID/Password in `esp32_main.cpp`.
    - Flash ESP32 using Arduino IDE/PlatformIO.
    - Monitor Serial output to confirm camera initialization and WiFi connection.

## 🟠 Phase 3: System Integration
**Goal:** Connect the physical cap to the Python backend.

- [ ] **Network Discovery**
    - Identify ESP32 IP address.
    - Update `config/backend_config.json` with the correct IP.
- [ ] **Stream Latency Test**
    - Measure delay between real movement and backend reception.
    - Target: < 200ms latency.
    - Optimization: Adjust JPEG quality in firmware if laggy.
- [ ] **Calibration**
    - **Ultrasonic:** Calibrate distances (e.g., does 30cm reading actually mean 30cm?).
    - **Camera:** Adjust rotation/orientation if the camera is mounted upside down.

## 🔵 Phase 4: Field Testing & Tuning
**Goal:** Optimize for real-world usability by a visually impaired user.

- [ ] **Threshold Tuning**
    - Adjust `WARNING` vs `CRITICAL` distance zones based on walking speed.
    - Tune `detection_confidence` to minimize false alarms (e.g., detecting a poster as a real person).
- [ ] **UX Refinement**
    - Test different vibration patterns (are they distinguishable?).
    - Adjust TTS speed and verbosity (is it too chatty?).
- [ ] **Power Optimization**
    - Measure battery life in "Active" vs "Balanced" modes.
    - Implement deep sleep triggers for the ESP32.

## 🟣 Phase 5: Advanced Features (Future Roadmap)
**Goal:** Add capabilities outlined in `docs/FUTURE_UPGRADES.md`.

- [ ] **GPS Navigation:** Add NEO-6M module for location tracking.
- [ ] **Offline Mode:** Transition basic object detection to run locally on ESP32 (TensorFlow Lite Micro) or specialized edge hardware (Luxonis OAK-D).
- [ ] **Mobile App:** Build a Flutter/React Native companion app for settings control.
