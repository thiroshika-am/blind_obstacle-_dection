# 🧢 Smart AI Cap — Blind Obstacle Detection System

> A wearable smart cap for visually impaired users, featuring real-time obstacle detection via ESP32-CAM and GPS location tracking.

---

## 📂 Project Structure

```
blind_obstacle-_dection/
├── backend/
│   └── main.py              # Flask backend — API + frontend server
├── config/
│   ├── backend_config.json   # ESP32 URLs, network settings
│   └── requirements.txt      # Python dependencies
├── firmware/
│   └── esp32_main.cpp        # ESP32-CAM firmware (Arduino)
├── frontend/
│   ├── index.html            # Dashboard UI
│   ├── style.css             # Glassmorphism dark theme
│   └── app.js                # Live camera + GPS map logic
├── TODO.md                   # Project roadmap & checklist
└── README.md                 # This file
```

---

## 🚀 Quick Start

### 1. Install Python Dependencies

```bash
pip install -r config/requirements.txt
```

### 2. Configure ESP32 IP

Edit `config/backend_config.json` and set your ESP32's IP address:

```json
{
  "esp32": {
    "stream_url": "http://<ESP32_IP>:80/stream",
    "status_url": "http://<ESP32_IP>:80/status",
    "distance_url": "http://<ESP32_IP>:80/distance"
  }
}
```

### 3. Run the Backend

```bash
python backend/main.py
```

### 4. Open the Dashboard

Open your browser at **http://localhost:5000**

---

## 🖥️ Dashboard Features

- **Live Camera Feed** — Streams video from the ESP32-CAM in real-time
- **GPS Location Map** — Shows the blind user's location on an interactive dark-themed map
- **Distance Sensor** — Displays obstacle distance in centimeters
- **Alert Level** — Shows SAFE / WARNING / CRITICAL status
- **Battery & WiFi Signal** — Monitor device health
- **Fullscreen Camera** — Click to expand the camera view

---

## ⚡ ESP32 Firmware

Flash `firmware/esp32_main.cpp` to your ESP32-CAM using Arduino IDE or PlatformIO.

**Required Hardware:**
- ESP32-CAM (AI Thinker)
- HC-SR04 Ultrasonic Sensor
- GPS Module (NEO-6M) — *todo*
- Vibration Motor
- Li-Po 5000mAh Battery

---

## 📋 TODO

See [TODO.md](TODO.md) for the full project roadmap.

---

## 📜 License

MIT License — Open source for accessibility.
