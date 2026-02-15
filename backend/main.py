"""
==========================================
SMART AI CAP — Backend Server
Serves the frontend, proxies ESP32-CAM stream, and handles GPS data
==========================================
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timezone
from flask import Flask, Response, jsonify, send_from_directory, request, abort
from flask_cors import CORS
import requests

# ============================================
# CONFIGURATION
# ============================================

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "backend_config.json")

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

ESP32_STREAM_URL = config.get("esp32", {}).get("stream_url", "http://192.168.1.100:80/stream")
ESP32_STATUS_URL = config.get("esp32", {}).get("status_url", "http://192.168.1.100:80/status")
ESP32_DISTANCE_URL = config.get("esp32", {}).get("distance_url", "http://192.168.1.100:80/distance")
BACKEND_PORT = config.get("network", {}).get("backend_port", 5000)

# ============================================
# LOGGING
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("smartcap")

# ============================================
# IN-MEMORY STATE
# ============================================

# Latest GPS data received from ESP32
gps_data = {
    "latitude": 12.9716,    # Default: Bangalore, India (placeholder)
    "longitude": 77.5946,
    "accuracy": 0,
    "speed": 0,
    "altitude": 0,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "source": "placeholder",
}

# Device status
device_status = {
    "online": False,
    "last_seen": None,
    "battery": None,
    "wifi_rssi": None,
    "distance_mm": None,
    "alert_level": "SAFE",
    "uptime": 0,
}

gps_lock = threading.Lock()
status_lock = threading.Lock()

# ============================================
# FLASK APP
# ============================================

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR)
CORS(app)


# --- Serve Frontend ---

@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    # Don't serve /api/* as static files — let Flask handle those routes
    if path.startswith("api/"):
        abort(404)
    return send_from_directory(FRONTEND_DIR, path)


# --- API: Camera Stream Proxy ---

@app.route("/api/stream")
def stream_proxy():
    """
    Proxies the ESP32-CAM MJPEG stream to the frontend.
    The ESP32 serves an MJPEG stream at /stream.
    """
    def generate():
        try:
            resp = requests.get(ESP32_STREAM_URL, stream=True, timeout=(3, 10))
            for chunk in resp.iter_content(chunk_size=4096):
                yield chunk
        except requests.exceptions.RequestException as e:
            logger.warning(f"ESP32 stream unavailable: {e}")
            return

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


# --- API: GPS Data ---

@app.route("/api/gps", methods=["GET"])
def get_gps():
    """Return latest GPS coordinates."""
    with gps_lock:
        return jsonify(gps_data)


@app.route("/api/gps", methods=["POST"])
def update_gps():
    """
    ESP32 posts GPS data here.
    Expected JSON: { "latitude": float, "longitude": float, "accuracy": float, ... }
    """
    data = request.get_json(force=True)
    with gps_lock:
        gps_data["latitude"] = data.get("latitude", gps_data["latitude"])
        gps_data["longitude"] = data.get("longitude", gps_data["longitude"])
        gps_data["accuracy"] = data.get("accuracy", 0)
        gps_data["speed"] = data.get("speed", 0)
        gps_data["altitude"] = data.get("altitude", 0)
        gps_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        gps_data["source"] = "esp32"
    logger.info(f"GPS updated: {gps_data['latitude']}, {gps_data['longitude']}")
    return jsonify({"status": "ok"})


# --- API: Device Status ---

@app.route("/api/status", methods=["GET"])
def get_status():
    """Return device status."""
    with status_lock:
        return jsonify(device_status)


@app.route("/api/status", methods=["POST"])
def update_status():
    """
    ESP32 posts heartbeat/status here.
    Expected JSON: { "battery": int, "wifi_rssi": int, "distance_mm": int, "alert_level": str, "uptime": int }
    """
    data = request.get_json(force=True)
    with status_lock:
        device_status["online"] = True
        device_status["last_seen"] = datetime.now(timezone.utc).isoformat()
        device_status["battery"] = data.get("battery")
        device_status["wifi_rssi"] = data.get("wifi_rssi")
        device_status["distance_mm"] = data.get("distance_mm")
        device_status["alert_level"] = data.get("alert_level", "SAFE")
        device_status["uptime"] = data.get("uptime", 0)
    return jsonify({"status": "ok"})


# --- API: Distance (proxy to ESP32) ---

@app.route("/api/distance")
def get_distance():
    """Proxy distance request to ESP32."""
    try:
        resp = requests.get(ESP32_DISTANCE_URL, timeout=3)
        return jsonify(resp.json())
    except Exception:
        return jsonify({"distance_mm": None, "error": "ESP32 unreachable"})


# --- Health Check ---

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now(timezone.utc).isoformat()})


# ============================================
# BACKGROUND: Device Online Checker
# ============================================

def device_watchdog():
    """Marks device as offline if no heartbeat received in 30 seconds."""
    while True:
        time.sleep(10)
        with status_lock:
            if device_status["last_seen"]:
                last = datetime.fromisoformat(device_status["last_seen"])
                now = datetime.now(timezone.utc)
                # Ensure both are timezone-aware for comparison
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                delta = (now - last).total_seconds()
                if delta > 30:
                    device_status["online"] = False


# ============================================
# MAIN ENTRY POINT
# ============================================

def main():
    logger.info("=" * 50)
    logger.info("  SMART AI CAP — Backend Server")
    logger.info(f"  Frontend: http://localhost:{BACKEND_PORT}")
    logger.info(f"  ESP32 Stream: {ESP32_STREAM_URL}")
    logger.info("=" * 50)

    # Start watchdog thread
    watchdog = threading.Thread(target=device_watchdog, daemon=True)
    watchdog.start()

    app.run(host="0.0.0.0", port=BACKEND_PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
