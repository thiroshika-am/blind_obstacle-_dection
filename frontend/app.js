/**
 * ==========================================
 * SMART AI CAP — Dashboard Frontend Logic
 * Live camera feed + GPS map tracking
 * ==========================================
 */

// ============================================
// CONFIGURATION
// ============================================

const API_BASE = window.location.origin;
const POLL_INTERVAL_MS = 3000;  // Poll GPS & status every 3s
const STREAM_RETRY_MS = 5000;   // Retry camera stream every 5s

// ============================================
// DOM REFERENCES
// ============================================

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
    // Status dots
    statusDot: $('#status-dot'),
    deviceLabel: $('#device-label'),

    // Stat values
    valDistance: $('#val-distance'),
    valAlert: $('#val-alert'),
    valBattery: $('#val-battery'),
    valSignal: $('#val-signal'),

    // Camera
    cameraFeed: $('#camera-feed'),
    cameraOverlay: $('#camera-overlay'),
    btnRefreshCamera: $('#btn-refresh-camera'),
    btnFullscreen: $('#btn-fullscreen'),
    panelCamera: $('#panel-camera'),

    // Map
    coordLat: $('#coord-lat'),
    coordLng: $('#coord-lng'),
    valSpeed: $('#val-speed'),
    valAltitude: $('#val-altitude'),
    valAccuracy: $('#val-accuracy'),
    valLastUpdate: $('#val-last-update'),
};

// ============================================
// MAP INITIALIZATION (Leaflet)
// ============================================

let map, marker, accuracyCircle;

function initMap() {
    map = L.map('map', {
        center: [12.9716, 77.5946],
        zoom: 15,
        zoomControl: true,
        attributionControl: true,
    });

    // Dark map tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
        maxZoom: 19,
    }).addTo(map);

    // Custom pulsing marker
    const pulseIcon = L.divIcon({
        className: 'marker-pulse-wrapper',
        html: '<div class="marker-pulse"></div>',
        iconSize: [20, 20],
        iconAnchor: [10, 10],
    });

    marker = L.marker([12.9716, 77.5946], { icon: pulseIcon }).addTo(map);

    // Accuracy circle
    accuracyCircle = L.circle([12.9716, 77.5946], {
        radius: 50,
        color: '#6C63FF',
        fillColor: '#6C63FF',
        fillOpacity: 0.08,
        weight: 1,
    }).addTo(map);
}

// ============================================
// GPS DATA POLLING
// ============================================

async function fetchGPS() {
    try {
        const res = await fetch(`${API_BASE}/api/gps`);
        if (!res.ok) return;
        const data = await res.json();

        const lat = data.latitude;
        const lng = data.longitude;
        const acc = data.accuracy || 0;

        // Update map
        const pos = [lat, lng];
        marker.setLatLng(pos);
        accuracyCircle.setLatLng(pos);
        accuracyCircle.setRadius(Math.max(acc, 10));
        map.setView(pos, map.getZoom(), { animate: true, duration: 1 });

        // Update UI
        dom.coordLat.textContent = lat.toFixed(6);
        dom.coordLng.textContent = lng.toFixed(6);
        dom.valSpeed.textContent = `${(data.speed || 0).toFixed(1)} km/h`;
        dom.valAltitude.textContent = `${(data.altitude || 0).toFixed(0)} m`;
        dom.valAccuracy.textContent = `${acc.toFixed(0)} m`;
        dom.valLastUpdate.textContent = formatTime(data.timestamp);
    } catch (e) {
        console.warn('GPS fetch error:', e);
    }
}

// ============================================
// DEVICE STATUS POLLING
// ============================================

async function fetchStatus() {
    try {
        const res = await fetch(`${API_BASE}/api/status`);
        if (!res.ok) return;
        const data = await res.json();

        // Online / Offline
        const online = data.online;
        dom.statusDot.className = `status-dot ${online ? 'online' : 'offline'}`;
        dom.deviceLabel.textContent = online ? 'ESP32 Online' : 'ESP32 Offline';

        // Distance
        if (data.distance_mm !== null && data.distance_mm !== undefined) {
            const cm = (data.distance_mm / 10).toFixed(0);
            dom.valDistance.textContent = `${cm} cm`;
        } else {
            dom.valDistance.textContent = '—';
        }

        // Alert level
        const alertLevel = (data.alert_level || 'SAFE').toUpperCase();
        dom.valAlert.textContent = alertLevel;
        dom.valAlert.className = 'stat-value';
        if (alertLevel === 'SAFE') dom.valAlert.classList.add('level-safe');
        else if (alertLevel === 'WARNING') dom.valAlert.classList.add('level-warning');
        else if (alertLevel === 'CRITICAL') dom.valAlert.classList.add('level-critical');

        // Battery
        if (data.battery !== null && data.battery !== undefined) {
            dom.valBattery.textContent = `${data.battery}%`;
        } else {
            dom.valBattery.textContent = '—';
        }

        // WiFi signal
        if (data.wifi_rssi !== null && data.wifi_rssi !== undefined) {
            dom.valSignal.textContent = `${data.wifi_rssi} dBm`;
        } else {
            dom.valSignal.textContent = '—';
        }
    } catch (e) {
        console.warn('Status fetch error:', e);
        dom.statusDot.className = 'status-dot offline';
        dom.deviceLabel.textContent = 'Backend Offline';
    }
}

// ============================================
// CAMERA STREAM
// ============================================

let streamRetryTimer = null;

function connectCameraStream() {
    const feed = dom.cameraFeed;
    const overlay = dom.cameraOverlay;

    // Set MJPEG stream URL
    feed.src = `${API_BASE}/api/stream`;

    feed.onload = () => {
        overlay.classList.add('hidden');
        clearTimeout(streamRetryTimer);
    };

    feed.onerror = () => {
        overlay.classList.remove('hidden');
        // Retry
        streamRetryTimer = setTimeout(connectCameraStream, STREAM_RETRY_MS);
    };
}

// ============================================
// FULLSCREEN TOGGLE
// ============================================

function toggleFullscreen() {
    const panel = dom.panelCamera;
    panel.classList.toggle('fullscreen');

    if (panel.classList.contains('fullscreen')) {
        document.body.style.overflow = 'hidden';
    } else {
        document.body.style.overflow = '';
    }
}

// ============================================
// UTILITY
// ============================================

function formatTime(isoString) {
    if (!isoString) return '—';
    try {
        const d = new Date(isoString);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
        return '—';
    }
}

// ============================================
// INITIALIZATION
// ============================================

function init() {
    // Init map
    initMap();

    // Start camera stream
    connectCameraStream();

    // Button handlers
    dom.btnRefreshCamera.addEventListener('click', () => {
        dom.cameraOverlay.classList.remove('hidden');
        connectCameraStream();
    });

    dom.btnFullscreen.addEventListener('click', toggleFullscreen);

    // ESC to exit fullscreen
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && dom.panelCamera.classList.contains('fullscreen')) {
            toggleFullscreen();
        }
    });

    // Initial data fetch
    fetchGPS();
    fetchStatus();

    // Polling intervals
    setInterval(fetchGPS, POLL_INTERVAL_MS);
    setInterval(fetchStatus, POLL_INTERVAL_MS);

    console.log('%c🧢 SmartCap Dashboard Initialized', 'color: #6C63FF; font-weight: bold; font-size: 14px;');
}

// Start when DOM is ready
document.addEventListener('DOMContentLoaded', init);
