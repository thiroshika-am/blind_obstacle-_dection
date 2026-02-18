/**
 * VisionX Dashboard - Production Version
 * Optimized for performance and maintainability
 */

/* ============================================
   LOADING SCREEN MANAGEMENT
   ============================================ */

const LoadingScreen = {
    screen: null,
    progressFill: null,
    progressPercentage: null,
    messageItems: null,
    currentMessageIndex: 0,
    hideTimeout: null,

    init() {
        this.screen = document.getElementById('loading-screen');
        this.progressFill = document.querySelector('.progress-fill');
        this.progressPercentage = document.querySelector('.progress-percentage');
        this.messageItems = document.querySelectorAll('.message-item');
        
        // Start the loading sequence
        this.startLoadingSequence();
        
        // Hide loading screen after 5 seconds
        this.scheduleHide(5000);
    },

    startLoadingSequence() {
        let currentProgress = 0;
        let currentMessage = 0;

        const progressInterval = setInterval(() => {
            currentProgress += Math.random() * 40;
            if (currentProgress > 90) currentProgress = 90; // Cap at 90% until completion

            this.updateProgress(currentProgress);

            if (Math.random() > 0.6 && currentMessage < this.messageItems.length) {
                this.showMessage(currentMessage);
                currentMessage++;
            }
        }, 800);

        // Store interval ID for cleanup
        this.progressInterval = progressInterval;
    },

    updateProgress(percentage) {
        percentage = Math.min(percentage, 100);
        if (this.progressFill) {
            this.progressFill.style.width = percentage + '%';
        }
        if (this.progressPercentage) {
            this.progressPercentage.textContent = Math.round(percentage) + '%';
        }
    },

    showMessage(index) {
        if (this.messageItems[index]) {
            this.messageItems[index].style.opacity = '1';
            this.messageItems[index].style.animation = 'slideInMessage 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards';
        }
    },

    scheduleHide(delay) {
        clearTimeout(this.hideTimeout);
        this.hideTimeout = setTimeout(() => {
            this.complete();
        }, delay);
    },

    complete() {
        // Complete the progress bar
        this.updateProgress(100);
        
        // Clear the progress interval
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }

        // Hide loading screen after completion animation
        setTimeout(() => {
            if (this.screen) {
                this.screen.classList.add('hidden');
            }
        }, 500);
    },

    hide() {
        this.complete();
    }
};

// Initialize loading screen when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        LoadingScreen.init();
    });
} else {
    LoadingScreen.init();
}

/* ============================================
   END LOADING SCREEN MANAGEMENT
   ============================================ */

const CONFIG = {
    API_BASE: window.location.origin,
    POLL_INTERVAL: 3000,
    STREAM_RETRY_INTERVAL: 5000,
    DETECTION_HISTORY_MAX: 10,
    DETECTION_INTERVAL: 100, // Run detection every 100ms for fast real-time tracking
    OCR_INTERVAL: 2000, // Run OCR every 2 seconds (text doesn't change as fast)
};

const STATE = {
    detectionHistory: [],
    voiceActive: true, // Voice always on by default
    systemStatus: { esp32: false, camera: false, ai: false, voice: true, gps: false },
    pollingTimer: null,
    streamRetryTimer: null,
    accuracyCircle: null,
    detectionTimer: null,
    ocrTimer: null, // OCR detection timer
    isDetecting: false,
    isReadingText: false, // OCR in progress
    lastDetections: [],
    lastOcrText: '', // Last detected text
    announcedTexts: new Set(), // Texts already announced
    capConnected: false,
    hasInitialLocation: false,
    environment: 'detecting',
    voiceSpeed: 1.0,
    detectionSensitivity: 0.4,
    sessionStart: Date.now(),
    safetyScore: 100,
};

// DOM references - populated after DOMContentLoaded
let DOM = {};
let statusLights = {};
let alertZones = {};

function initDOMRefs() {
    DOM = {
        cameraFeed: document.getElementById('camera-feed'),
        cameraOverlay: document.getElementById('camera-overlay'),
        detectionDisplay: document.getElementById('detection-display'),
        confidenceBadge: document.getElementById('confidence-badge'),
        detectionDistance: document.getElementById('detection-distance'),
        alertLevel: document.getElementById('alert-level'),
        // historyList: document.getElementById('history-list'),  // Removed
        // historyCount: document.getElementById('history-count'),  // Removed
        voiceVis: document.getElementById('voice-vis'),
        voiceStatus: document.getElementById('voice-status'),
        statBattery: document.getElementById('stat-battery'),
        statSignal: document.getElementById('stat-signal'),
        // coordLat: document.getElementById('coord-lat'),  // Removed from display
        // coordLng: document.getElementById('coord-lng'),  // Removed from display
        capConnection: document.getElementById('cap-connection'),
        capStatus: document.getElementById('cap-status'),
        capIndicator: document.getElementById('cap-indicator'),
    };

    statusLights = {
        esp32: document.getElementById('light-esp32'),
        camera: document.getElementById('light-camera'),
        ai: document.getElementById('light-ai'),
        voice: document.getElementById('light-voice'),
        gps: document.getElementById('light-gps'),
    };

    alertZones = {
        critical: document.getElementById('alert-critical'),
        warning: document.getElementById('alert-warning'),
        safe: document.getElementById('alert-safe'),
    };
}

// ============================================
// WEBCAM MANAGEMENT (Browser Camera)
// ============================================

let webcamStream = null;
let cameraWatchdog = null;

async function connectCameraStream() {
    const feed = DOM.cameraFeed;
    const overlay = DOM.cameraOverlay;

    console.log('Attempting camera connection...', { feed: !!feed, overlay: !!overlay });
    if (!feed || !overlay) {
        console.error('Missing camera elements:', { feed, overlay });
        return;
    }

    try {
        // Request webcam access
        console.log('Requesting webcam access...');
        webcamStream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'environment' // Use back camera on mobile
            },
            audio: false
        });

        feed.srcObject = webcamStream;
        await feed.play();
        
        overlay.classList.add('hidden');
        updateStatusLight('camera', true);
        console.log('Webcam connected successfully');
        
        // Start AI detection after a short delay
        setTimeout(startDetection, 1000);
        
        // Start watchdog to keep camera and detection always on
        startCameraWatchdog();
        
    } catch (err) {
        console.error('Webcam error:', err.message);
        overlay.classList.remove('hidden');
        overlay.querySelector('p').textContent = 'Camera access denied';
        updateStatusLight('camera', false);
        // Retry camera connection after 3 seconds
        setTimeout(connectCameraStream, 3000);
    }
}

// Watchdog to ensure camera and detection stay always on
function startCameraWatchdog() {
    if (cameraWatchdog) clearInterval(cameraWatchdog);
    
    cameraWatchdog = setInterval(() => {
        // Check if camera stream is still active
        if (!webcamStream || !webcamStream.active) {
            console.log('Camera disconnected, reconnecting...');
            connectCameraStream();
            return;
        }
        
        // Ensure detection is running when camera is on
        if (webcamStream && webcamStream.active && !STATE.detectionTimer) {
            console.log('Detection stopped, restarting...');
            startDetection();
        }
    }, 2000); // Check every 2 seconds
}

function stopWebcam() {
    // Clear watchdog when manually stopping
    if (cameraWatchdog) {
        clearInterval(cameraWatchdog);
        cameraWatchdog = null;
    }
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
        webcamStream = null;
    }
    stopDetection();
}

// ============================================
// OBJECT DETECTION
// ============================================

let detectionCanvas = null;
let detectionCtx = null;

function startDetection() {
    if (STATE.detectionTimer) return;
    
    detectionCanvas = document.getElementById('detection-canvas');
    if (!detectionCanvas) return;
    
    detectionCtx = detectionCanvas.getContext('2d');
    updateStatusLight('ai', true);
    
    // Run detection at regular intervals
    STATE.detectionTimer = setInterval(runDetection, CONFIG.DETECTION_INTERVAL);
    console.log('Detection started');
    
    // Start OCR detection (less frequent)
    startOCR();
}

function stopDetection() {
    if (STATE.detectionTimer) {
        clearInterval(STATE.detectionTimer);
        STATE.detectionTimer = null;
    }
    stopOCR();
    updateStatusLight('ai', false);
}

// ============================================
// OCR TEXT DETECTION
// ============================================

function startOCR() {
    if (STATE.ocrTimer) return;
    STATE.ocrTimer = setInterval(runOCR, CONFIG.OCR_INTERVAL);
    console.log('OCR started');
}

function stopOCR() {
    if (STATE.ocrTimer) {
        clearInterval(STATE.ocrTimer);
        STATE.ocrTimer = null;
    }
}

async function runOCR() {
    if (STATE.isReadingText || !DOM.cameraFeed || !webcamStream || !webcamStream.active) {
        return;
    }
    
    const video = DOM.cameraFeed;
    if (video.readyState < 2) return;
    
    STATE.isReadingText = true;
    
    try {
        // Capture frame for OCR (higher resolution than object detection for better text reading)
        const canvas = document.createElement('canvas');
        canvas.width = 800;
        canvas.height = 600;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, 800, 600);
        
        const imageData = canvas.toDataURL('image/jpeg', 0.7);
        
        const response = await fetch(`${CONFIG.API_BASE}/api/ocr`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        });
        
        if (!response.ok) return;
        
        const result = await response.json();
        handleOCRResult(result);
        
    } catch (err) {
        console.error('OCR error:', err.message);
    } finally {
        STATE.isReadingText = false;
    }
}

// OCR distance threshold (in meters) - only detect text within this range
const OCR_MAX_DISTANCE = 5.0;

// Estimate text distance based on bounding box height
// Assumes average text height of 5cm and 800x600 OCR image
function estimateTextDistance(bbox, frameHeight = 600) {
    if (!bbox) return null;
    
    const bboxHeight = bbox.y2 - bbox.y1;
    if (bboxHeight <= 0) return null;
    
    // Reference: average text/sign height ~5cm, focal length approximation
    const refHeightCm = 5;
    const focalLength = frameHeight * 0.8;
    
    // Distance = (real height * focal length) / pixel height
    const distanceCm = (refHeightCm * focalLength) / bboxHeight;
    const distanceM = distanceCm / 100;
    
    // Clamp to reasonable range
    return Math.max(0.2, Math.min(15.0, distanceM));
}

function handleOCRResult(result) {
    const { texts, combined_text, count } = result;
    
    if (!texts || texts.length === 0) {
        return; // No text detected
    }
    
    // Filter texts within 5 meter range
    const nearbyTexts = texts.filter(t => {
        const distance = estimateTextDistance(t.bbox);
        t.distance_m = distance; // Store for later use
        return distance !== null && distance <= OCR_MAX_DISTANCE;
    });
    
    if (nearbyTexts.length === 0) {
        return; // No text within range
    }
    
    // Combine only nearby text
    const nearbyText = nearbyTexts.map(t => t.text).join(' ').trim();
    
    if (nearbyText.length < 3) {
        return; // No meaningful text
    }
    
    // Check if this is new text (not recently announced)
    const normalizedText = nearbyText.toLowerCase();
    if (STATE.announcedTexts.has(normalizedText)) {
        return; // Already announced this text
    }
    
    // Get closest text distance for display
    const closestDistance = Math.min(...nearbyTexts.map(t => t.distance_m || 5));
    
    // Update state
    STATE.lastOcrText = nearbyText;
    STATE.announcedTexts.add(normalizedText);
    
    // Clear old announced texts after 30 seconds
    setTimeout(() => {
        STATE.announcedTexts.delete(normalizedText);
    }, 30000);
    
    // Announce the text via voice with distance
    announceText(nearbyText, closestDistance);
    
    // Display the text on screen with distance
    displayDetectedText(nearbyText, nearbyTexts, closestDistance);
    
    console.log(`OCR detected (${closestDistance.toFixed(1)}m):`, nearbyText);
}

function announceText(text, distance) {
    if (!STATE.voiceActive || !speechSynthesis) return;
    
    // Limit text length for announcement
    let announcement = text;
    if (text.length > 100) {
        announcement = text.substring(0, 100) + '...';
    }
    
    // Include distance in announcement
    const distanceText = distance ? `, ${distance.toFixed(1)} meters away` : '';
    
    console.log('Announcing text via voice:', announcement);
    
    // Cancel any current speech to prioritize text reading
    speechSynthesis.cancel();
    
    // Create and speak the utterance directly
    const utterance = new SpeechSynthesisUtterance(`Text says: ${announcement}${distanceText}`);
    utterance.rate = STATE.voiceSpeed || 0.9;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    
    if (preferredVoice) utterance.voice = preferredVoice;
    
    utterance.onstart = () => {
        console.log('Voice started speaking text');
        const status = document.getElementById('voice-status');
        if (status) status.textContent = 'Reading text...';
    };
    
    utterance.onend = () => {
        const status = document.getElementById('voice-status');
        if (status) status.textContent = 'Ready';
    };
    
    utterance.onerror = (e) => {
        console.error('Speech error:', e);
    };
    
    speechSynthesis.speak(utterance);
}

function displayDetectedText(text, textItems, distance) {
    // Display in Alert System panel
    const textContent = document.getElementById('detected-text-content');
    if (textContent) {
        const distanceStr = distance ? ` <span style="color: var(--primary);">(${distance.toFixed(1)}m)</span>` : '';
        textContent.innerHTML = `<span class="detected-text">${escapeHtml(text)}${distanceStr}</span>`;
        textContent.classList.add('has-text');
        
        // Auto-clear after 10 seconds
        clearTimeout(textContent._clearTimeout);
        textContent._clearTimeout = setTimeout(() => {
            textContent.innerHTML = '<span class="no-text">No text detected</span>';
            textContent.classList.remove('has-text');
        }, 10000);
    }
    
    // Also show briefly on camera overlay for immediate feedback
    let textDisplay = document.getElementById('ocr-text-display');
    if (!textDisplay) {
        textDisplay = document.createElement('div');
        textDisplay.id = 'ocr-text-display';
        textDisplay.className = 'ocr-text-display';
        textDisplay.style.cssText = `
            position: absolute;
            bottom: 10px;
            left: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: #00D4FF;
            padding: 10px 15px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 14px;
            z-index: 100;
            max-height: 60px;
            overflow-y: auto;
            border: 1px solid #00D4FF;
        `;
        const cameraPanel = document.querySelector('.camera-panel');
        if (cameraPanel) cameraPanel.appendChild(textDisplay);
    }
    
    textDisplay.innerHTML = `<span style="color: #10B981; font-weight: bold;">TEXT:</span> ${escapeHtml(text)}`;
    textDisplay.style.opacity = '1';
    
    // Brief overlay - auto-hide after 3 seconds
    clearTimeout(textDisplay._hideTimeout);
    textDisplay._hideTimeout = setTimeout(() => {
        textDisplay.style.opacity = '0';
        setTimeout(() => textDisplay.remove(), 300);
    }, 3000);
}

async function runDetection() {
    if (STATE.isDetecting) {
        return; // Already running a detection
    }
    
    if (!DOM.cameraFeed || !webcamStream || !webcamStream.active) {
        // Camera not ready, watchdog will reconnect
        return;
    }
    
    const video = DOM.cameraFeed;
    if (video.readyState < 2) {
        // Video not ready yet, will retry on next interval
        return;
    }
    
    STATE.isDetecting = true;
    
    try {
        // Capture frame from video at reduced resolution for faster processing
        const canvas = document.createElement('canvas');
        // Use 640x480 for fast detection instead of full resolution
        const targetWidth = 640;
        const targetHeight = 480;
        canvas.width = targetWidth;
        canvas.height = targetHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, targetWidth, targetHeight);
        
        // Convert to base64 with lower quality for faster transfer
        const imageData = canvas.toDataURL('image/jpeg', 0.6);
        
        // Send to backend for detection
        const response = await fetch(`${CONFIG.API_BASE}/api/detect`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        });
        
        if (!response.ok) throw new Error('Detection failed');
        
        const result = await response.json();
        
        // Update UI with detections
        handleDetectionResult(result);
        
    } catch (err) {
        console.error('Detection error:', err.message, err);
        // Don't spam errors, just continue
    } finally {
        STATE.isDetecting = false;
    }
}

function handleDetectionResult(result) {
    const { detections, alert_level, count } = result;
    
    STATE.lastDetections = detections || [];
    
    // Draw bounding boxes on canvas overlay
    drawDetections(detections);
    
    // Update detection display
    updateDetectionDisplay(detections, alert_level);
    
    // Update alert zones
    updateAlertZones(detections);
    
    // Update mini radar
    updateRadar(detections);
    
    // Update environment badge
    if (detections && detections.length > 0) {
        updateEnvironmentBadge();
    }
    
    // Detection history feature removed
    // if (detections && detections.length > 0) {
    //     addToHistory(detections);
    // }
}

function drawDetections(detections) {
    if (!detectionCanvas || !detectionCtx) return;
    
    const video = DOM.cameraFeed;
    if (!video) return;
    
    // Resize canvas to match video display
    detectionCanvas.width = video.offsetWidth;
    detectionCanvas.height = video.offsetHeight;
    
    // Detection was done on 640x480 image, scale bboxes from that size
    const DETECTION_WIDTH = 640;
    const DETECTION_HEIGHT = 480;
    const scaleX = detectionCanvas.width / DETECTION_WIDTH;
    const scaleY = detectionCanvas.height / DETECTION_HEIGHT;
    
    // Clear previous drawings
    detectionCtx.clearRect(0, 0, detectionCanvas.width, detectionCanvas.height);
    
    if (!detections || detections.length === 0) return;
    
    detections.forEach(det => {
        const { bbox, class: label, confidence, alert_level } = det;
        const trackId = det.track_id || `${label}_${det.position || 'c'}`;
        
        // Get motion state from objectState
        const state = objectState.get(trackId);
        const isApproaching = state?.isApproaching || false;
        const isStationary = state?.isStationary || true;
        
        // Scale bbox to canvas size
        const x = bbox.x1 * scaleX;
        const y = bbox.y1 * scaleY;
        const w = (bbox.x2 - bbox.x1) * scaleX;
        const h = (bbox.y2 - bbox.y1) * scaleY;
        
        // Color based on alert level and motion
        let color = '#10B981'; // green - safe
        if (alert_level === 'CRITICAL') color = '#EF4444'; // red
        else if (alert_level === 'WARNING') color = '#F59E0B'; // orange
        
        // Override color if approaching (pulsing effect handled by lineWidth)
        if (isApproaching) {
            color = '#EF4444'; // red for approaching
        }
        
        // Draw bounding box with motion-aware style
        detectionCtx.strokeStyle = color;
        detectionCtx.lineWidth = isApproaching ? 4 : 3;
        
        // Dashed line for stationary, solid for moving
        if (isStationary && !isApproaching) {
            detectionCtx.setLineDash([5, 5]);
        } else {
            detectionCtx.setLineDash([]);
        }
        detectionCtx.strokeRect(x, y, w, h);
        detectionCtx.setLineDash([]); // Reset
        
        // Motion indicator icon
        let motionIcon = '';
        if (isApproaching) motionIcon = ' ↓';
        else if (!isStationary) motionIcon = ' →';
        
        // Draw label with object name, distance, and motion
        const distanceText = det.distance || '';
        const labelText = `${label}${motionIcon} - ${distanceText}`;
        detectionCtx.font = 'bold 14px Inter, sans-serif';
        const textWidth = detectionCtx.measureText(labelText).width;
        
        // Label background
        detectionCtx.fillStyle = color;
        detectionCtx.fillRect(x, y - 28, textWidth + 16, 28);
        
        // Label text
        detectionCtx.fillStyle = '#FFFFFF';
        detectionCtx.fillText(labelText, x + 8, y - 9);
        
        // Draw distance badge at bottom of box
        if (distanceText) {
            const distBadge = distanceText;
            const distWidth = detectionCtx.measureText(distBadge).width;
            detectionCtx.fillStyle = 'rgba(0,0,0,0.7)';
            detectionCtx.fillRect(x + w/2 - distWidth/2 - 8, y + h - 24, distWidth + 16, 24);
            detectionCtx.fillStyle = color;
            detectionCtx.fillText(distBadge, x + w/2 - distWidth/2, y + h - 8);
        }
    });
}

// ============================================
// MOVEMENT TRACKING HELPERS
// ============================================

function getMovementIcon(movement) {
    if (!movement || !movement.direction) return '';
    
    const direction = movement.direction;
    
    if (direction === 'new') return '🆕';
    if (direction === 'stationary') return '';
    if (direction === 'approaching') return '⚠️↓';
    if (direction === 'receding') return '↑';
    if (direction === 'moving_left') return '←';
    if (direction === 'moving_right') return '→';
    if (direction === 'approaching_left') return '↙️';
    if (direction === 'approaching_right') return '↘️';
    if (direction === 'receding_left') return '↖️';
    if (direction === 'receding_right') return '↗️';
    
    return '';
}

function getMovementClass(movement) {
    if (!movement || !movement.direction) return '';
    
    if (movement.approaching === true) return 'approaching';
    if (movement.approaching === false) return 'receding';
    if (movement.direction === 'new') return 'new-object';
    if (movement.lateral) return 'lateral';
    
    return '';
}

function getMovementText(movement) {
    if (!movement || movement.direction === 'stationary') return '';
    
    const dir = movement.direction;
    
    if (dir === 'new') return 'detected';
    if (dir === 'approaching') return 'getting closer';
    if (dir === 'receding') return 'moving away';
    if (dir === 'moving_left') return 'moving left';
    if (dir === 'moving_right') return 'moving right';
    if (dir === 'approaching_left') return 'approaching from left';
    if (dir === 'approaching_right') return 'approaching from right';
    if (dir === 'receding_left') return 'moving away left';
    if (dir === 'receding_right') return 'moving away right';
    
    return '';
}

function updateDetectionDisplay(detections, alert_level) {
    const display = DOM.detectionDisplay;
    const badge = DOM.confidenceBadge;
    const alertEl = DOM.alertLevel;
    const distanceEl = DOM.detectionDistance;
    
    if (detections && detections.length > 0) {
        // Announce detections via voice (if enabled)
        announceDetections(detections);
        
        // Show up to 3 detected objects with movement info
        const objectsHtml = detections.slice(0, 3).map((det, i) => {
            const alertClass = det.alert_level?.toLowerCase() || 'safe';
            const movement = det.movement || {};
            const movementIcon = getMovementIcon(movement);
            const movementClass = getMovementClass(movement);
            
            // Determine item animation class based on movement
            let itemClass = i === 0 ? 'primary' : 'secondary';
            if (movement.approaching === true && movement.speed > 0.2) {
                itemClass += ' approaching-fast';
            } else if (movement.direction && movement.direction !== 'stationary' && movement.direction !== 'new') {
                itemClass += ' moving';
            }
            
            // Add lateral direction for sliding animation
            let lateralClass = '';
            if (movement.lateral === 'moving_left') lateralClass = ' left';
            if (movement.lateral === 'moving_right') lateralClass = ' right';
            
            return `
                <div class="detection-item ${itemClass}" data-track-id="${det.track_id || ''}">
                    <span class="object-name">${det.class}</span>
                    ${movementIcon ? `<span class="movement-indicator ${movementClass}${lateralClass}" title="${movement.direction}">${movementIcon}</span>` : ''}
                    <span class="object-distance alert-${alertClass}">${det.distance || '—'}</span>
                </div>
            `;
        }).join('');
        
        if (display) {
            display.innerHTML = `
                <div class="detection-list">
                    ${objectsHtml}
                    ${detections.length > 3 ? `<span class="more-objects">+${detections.length - 3} more</span>` : ''}
                </div>
            `;
        }
        
        // Update primary object stats
        const primary = detections[0];
        
        if (badge) {
            badge.textContent = `${Math.round(primary.confidence * 100)}%`;
            badge.className = 'confidence-badge ' + (primary.confidence > 0.7 ? 'high' : 'medium');
        }
        
        if (distanceEl) {
            distanceEl.textContent = primary.distance || '—';
            distanceEl.className = 'stat-value alert-' + (primary.alert_level || 'safe').toLowerCase();
        }
        
    } else {
        if (display) {
            display.innerHTML = `
                <div class="detection-placeholder">
                    <p>Scanning environment...</p>
                    <div class="scan-animation"></div>
                </div>
            `;
        }
        if (badge) badge.textContent = '—';
        if (distanceEl) distanceEl.textContent = '—';
    }
    
    if (alertEl) {
        alertEl.textContent = alert_level || 'CLEAR';
        alertEl.className = 'stat-value alert-' + (alert_level || 'safe').toLowerCase();
    }
}

function updateAlertZones(detections) {
    const critical = detections?.filter(d => d.alert_level === 'CRITICAL').length || 0;
    const warning = detections?.filter(d => d.alert_level === 'WARNING').length || 0;
    const safe = detections?.filter(d => d.alert_level === 'SAFE').length || 0;
    
    if (alertZones.critical) {
        alertZones.critical.querySelector('.zone-value').textContent = `${critical} object${critical !== 1 ? 's' : ''}`;
        alertZones.critical.classList.toggle('active', critical > 0);
    }
    if (alertZones.warning) {
        alertZones.warning.querySelector('.zone-value').textContent = `${warning} object${warning !== 1 ? 's' : ''}`;
        alertZones.warning.classList.toggle('active', warning > 0);
    }
    if (alertZones.safe) {
        alertZones.safe.querySelector('.zone-value').textContent = `${safe} object${safe !== 1 ? 's' : ''}`;
    }
}

// ============================================
// MINI RADAR DISPLAY
// ============================================

function updateRadar(detections) {
    const radarObjects = document.getElementById('radar-objects');
    if (!radarObjects) return;
    
    // Clear existing blips
    radarObjects.innerHTML = '';
    
    if (!detections || detections.length === 0) return;
    
    const radarSize = 120; // Match CSS size
    const centerX = radarSize / 2;
    const centerY = radarSize / 2;
    const maxDistance = 5; // Max distance in meters for radar scale
    
    detections.forEach((det, index) => {
        const distance = det.distance_m || 3;
        const bbox = det.bbox;
        
        // Calculate horizontal position from bbox center
        // Assuming 640px camera width as reference
        let horizontalPos = 0.5; // Default center
        if (bbox) {
            const bboxCenterX = (bbox.x1 + bbox.x2) / 2;
            horizontalPos = bboxCenterX / 640; // Normalize to 0-1
        }
        
        // Convert to radar coordinates
        // Distance determines how far from center (front = top of radar)
        const normalizedDistance = Math.min(distance / maxDistance, 1);
        const radarRadius = normalizedDistance * (radarSize / 2 - 10);
        
        // Horizontal position determines angle (left = -45°, center = 0°, right = 45°)
        const angle = (horizontalPos - 0.5) * Math.PI / 2; // -90° to +90° range
        
        // Calculate x, y position
        const x = centerX + Math.sin(angle) * radarRadius;
        const y = centerY - Math.cos(angle) * radarRadius; // Negative because top is forward
        
        // Create blip element
        const blip = document.createElement('div');
        blip.className = `radar-blip ${det.alert_level?.toLowerCase() || 'safe'}`;
        
        // Add moving class if object is in motion
        const movement = det.movement || {};
        if (movement.direction && movement.direction !== 'stationary' && movement.direction !== 'new') {
            blip.classList.add('moving');
        }
        
        blip.style.left = `${x}px`;
        blip.style.top = `${y}px`;
        blip.title = `${det.class} - ${det.distance}`;
        
        // Store track ID for smooth transitions
        if (det.track_id) {
            blip.dataset.trackId = det.track_id;
        }
        
        radarObjects.appendChild(blip);
    });
}

function addToHistory(detections) {
    const now = new Date();
    const timestamp = now.toLocaleTimeString();
    
    // Add unique detections to history
    const newItems = detections.slice(0, 3).map(det => ({
        class: det.class,
        confidence: det.confidence,
        distance: det.distance,
        alert_level: det.alert_level,
        timestamp
    }));
    
    // Avoid duplicates from last second
    const lastClasses = STATE.detectionHistory.slice(0, 3).map(h => h.class);
    const uniqueNew = newItems.filter(item => !lastClasses.includes(item.class));
    
    if (uniqueNew.length > 0) {
        STATE.detectionHistory = [...uniqueNew, ...STATE.detectionHistory].slice(0, CONFIG.DETECTION_HISTORY_MAX);
        renderHistory();
    }
}

// ============================================
// STATUS LIGHTS
// ============================================

function updateStatusLight(type, isOn) {
    const light = statusLights[type];
    if (!light) return;

    light.classList.toggle('on', isOn);
    light.classList.toggle('off', !isOn);
    STATE.systemStatus[type] = isOn;
}

// ============================================
// DETECTION & ALERTS
// ============================================

function updateDetection(name, confidence, distance) {
    if (!DOM.detectionDisplay) return;
    DOM.detectionDisplay.innerHTML = `
        <div style="text-align: center; width: 100%;">
            <div style="font-size: 2rem; font-weight: 700; color: #48cae4; margin-bottom: 0.5rem; font-family: 'Space Mono', monospace;">
                ${escapeHtml(name)}
            </div>
            <div style="font-size: 0.95rem; color: #cbd5e1;">Object Detected</div>
        </div>`;

    if (DOM.confidenceBadge) DOM.confidenceBadge.textContent = `${Math.round(confidence * 100)}%`;
    if (DOM.detectionDistance) DOM.detectionDistance.textContent = distance ? `${distance} m` : '—';

    updateAlertLevel(distance);
    addToHistory(name, confidence);
}

function updateAlertLevel(distance) {
    const levels = {
        critical: { label: 'CRITICAL', color: '#ef4444', min: 0, max: 0.5 },
        warning: { label: 'WARNING', color: '#f59e0b', min: 0.5, max: 1.0 },
        safe: { label: 'CLEAR', color: '#10b981', min: 1.0, max: Infinity },
    };

    let level = 'CLEAR';
    let color = levels.safe.color;

    if (distance !== null && distance !== undefined) {
        for (const [type, config] of Object.entries(levels)) {
            if (distance >= config.min && distance < config.max) {
                level = config.label;
                color = config.color;
                pulseAlert(type);
                break;
            }
        }
    }

    if (DOM.alertLevel) {
        DOM.alertLevel.textContent = level;
        DOM.alertLevel.style.color = color;
    }
}

function pulseAlert(type) {
    const elem = alertZones[type];
    if (!elem) return;
    elem.style.animation = 'none';
    void elem.offsetWidth; // Trigger reflow
    elem.style.animation = 'pulse 0.6s ease-in-out';
}

// ============================================
// DETECTION HISTORY
// ============================================

function addToHistory(name, confidence) {
    const now = new Date();

    // Deduplicate rapid entries
    const last = STATE.detectionHistory[0];
    if (last && last.name === name && (now - last.timestamp) < 1000) return;

    STATE.detectionHistory.unshift({
        name,
        confidence,
        timestamp: now,
        time: now.toLocaleTimeString(),
    });

    if (STATE.detectionHistory.length > CONFIG.DETECTION_HISTORY_MAX) {
        STATE.detectionHistory.pop();
    }

    renderHistory();
}

function renderHistory() {
    if (!DOM.historyList || !DOM.historyCount) return;
    
    if (!STATE.detectionHistory.length) {
        DOM.historyList.innerHTML = '<div class="history-empty"><p>No detections yet</p></div>';
        DOM.historyCount.textContent = '0 detections';
        return;
    }

    DOM.historyList.innerHTML = STATE.detectionHistory
        .map(item => `
            <div class="history-item">
                <div class="history-name">${escapeHtml(item.name)}</div>
                <div class="history-time">${item.time}</div>
                <div class="history-confidence">${Math.round(item.confidence * 100)}%</div>
            </div>`)
        .join('');

    DOM.historyCount.textContent = `${STATE.detectionHistory.length} detections`;
}

// ============================================
// VOICE ACTIVITY
// ============================================

function setVoiceActive(active) {
    STATE.voiceActive = active;
    updateStatusLight('voice', active);
    if (DOM.voiceVis) DOM.voiceVis.style.opacity = active ? '1' : '0.3';
    if (DOM.voiceStatus) {
        DOM.voiceStatus.textContent = active ? 'Speaking' : 'Idle';
        DOM.voiceStatus.classList.toggle('active', active);
    }
}

// ============================================
// CAP CONNECTION STATUS
// ============================================

function updateCapConnection(isConnected, statusText = null) {
    const { capConnection, capStatus, capIndicator } = DOM;
    
    STATE.capConnected = isConnected;
    
    if (capConnection) {
        capConnection.classList.toggle('connected', isConnected);
        capConnection.classList.toggle('disconnected', !isConnected);
    }
    
    if (capStatus) {
        capStatus.textContent = statusText || (isConnected ? 'Connected' : 'Disconnected');
    }
    
    updateStatusLight('esp32', isConnected);
}

// ============================================
// API POLLING
// ============================================

async function fetchStatus() {
    try {
        const res = await fetch(`${CONFIG.API_BASE}/api/status`);
        if (!res.ok) throw new Error(`Status ${res.status}`);

        const data = await res.json();
        
        // Update cap connection status
        const isCapConnected = data.online === true;
        updateCapConnection(isCapConnected, isCapConnected ? 'Online' : 'Offline');
        
        updateStatusLight('ai', data.online || false);
        updateStatusLight('gps', data.online || false);

        if (data.distance_mm !== null && data.distance_mm !== undefined) {
            updateDetection('Obstacle', 0.95, (data.distance_mm / 1000).toFixed(2));
        }

        if (data.battery !== null && data.battery !== undefined) {
            if (DOM.statBattery) DOM.statBattery.textContent = `${data.battery}%`;
        }

        if (data.wifi_rssi !== null && data.wifi_rssi !== undefined) {
            if (DOM.statSignal) DOM.statSignal.textContent = `${data.wifi_rssi} dBm`;
        }
    } catch (e) {
        console.warn('Status fetch error:', e.message);
        updateCapConnection(false, 'No Connection');
        updateStatusLight('ai', false);
    }
}

async function fetchGPS() {
    try {
        const res = await fetch(`${CONFIG.API_BASE}/api/gps`);
        if (!res.ok) throw new Error(`GPS ${res.status}`);

        const data = await res.json();
        const gpsSource = document.getElementById('gps-source');
        
        // Check if we have valid device GPS data
        if (data.latitude && data.longitude && data.source !== 'placeholder') {
            // Device GPS available - use it!
            // Coordinate display removed
            // if (DOM.coordLat) DOM.coordLat.textContent = data.latitude.toFixed(6);
            // if (DOM.coordLng) DOM.coordLng.textContent = data.longitude.toFixed(6);
            
            const accuracy = data.accuracy || 10;
            // Accuracy display removed
            
            // Update map with device location
            updateMapLocation(data.latitude, data.longitude, accuracy, !STATE.hasInitialLocation);
            updateStatusLight('gps', true);
            
            // Get location name via reverse geocoding
            reverseGeocode(data.latitude, data.longitude);
            
            if (gpsSource) {
                gpsSource.textContent = 'GPS: ESP32 Device';
                gpsSource.classList.add('device-gps');
            }
        } else {
            // No device GPS - show waiting status
            if (gpsSource) {
                gpsSource.textContent = 'GPS: Waiting for device...';
                gpsSource.classList.remove('device-gps');
            }
        }
    } catch (e) {
        console.warn('GPS fetch error:', e.message);
        const gpsSource = document.getElementById('gps-source');
        if (gpsSource) {
            gpsSource.textContent = 'GPS: Offline';
            gpsSource.classList.remove('device-gps');
        }
    }
}

// ============================================
// FULLSCREEN
// ============================================

function toggleFullscreen() {
    const panel = document.querySelector('.camera-panel');
    if (!panel) return;

    const isFullscreen = panel.style.position === 'fixed';
    panel.style.position = isFullscreen ? 'relative' : 'fixed';
    panel.style.inset = isFullscreen ? '' : '0';
    panel.style.zIndex = isFullscreen ? '' : '9999';
    panel.style.borderRadius = isFullscreen ? '' : '0';
    panel.style.width = isFullscreen ? '' : '100vw';
    panel.style.height = isFullscreen ? '' : '100vh';
    document.body.style.overflow = isFullscreen ? 'auto' : 'hidden';
}

// ============================================
// LEAFLET MAP WITH GEOLOCATION (FREE - NO API KEY)
// ============================================

let leafletMap = null;
let locationMarker = null;
let accuracyCircle = null;
let watchId = null;

function initMap() {
    if (leafletMap) return;
    
    const mapContainer = document.getElementById('map');
    if (!mapContainer) return;

    // Hide placeholder
    const placeholder = mapContainer.querySelector('.map-placeholder');
    if (placeholder) placeholder.style.display = 'none';

    try {
        // Initialize Leaflet map
        leafletMap = L.map('map', {
            center: [0, 0],
            zoom: 18,
            zoomControl: true,
        });

        // Satellite view (ESRI World Imagery - free)
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: '&copy; Esri, Maxar, Earthstar Geographics',
            maxZoom: 19,
        }).addTo(leafletMap);

        // Optional: Add labels overlay on satellite
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', {
            maxZoom: 19,
        }).addTo(leafletMap);

        // Custom cyan pulsing marker
        const pulsingIcon = L.divIcon({
            className: 'pulsing-marker',
            html: `<div class="marker-pin"></div><div class="marker-pulse"></div>`,
            iconSize: [20, 20],
            iconAnchor: [10, 10],
        });

        // User location marker
        locationMarker = L.marker([0, 0], { icon: pulsingIcon }).addTo(leafletMap);

        // Accuracy circle
        accuracyCircle = L.circle([0, 0], {
            radius: 50,
            color: '#00D4FF',
            fillColor: '#00D4FF',
            fillOpacity: 0.15,
            weight: 1,
        }).addTo(leafletMap);

        console.log('Leaflet map initialized successfully');

        // Start browser geolocation
        startGeolocation();
        
    } catch (e) {
        console.warn('Map initialization error:', e.message);
    }
}

function startGeolocation() {
    if (!navigator.geolocation) {
        console.warn('Geolocation not supported');
        updateStatusLight('gps', false);
        return;
    }

    // Watch position for continuous updates with maximum accuracy
    watchId = navigator.geolocation.watchPosition(
        handleGeolocationSuccess,
        handleGeolocationError,
        {
            enableHighAccuracy: true,
            timeout: 30000,
            maximumAge: 0,  // Always get fresh position
        }
    );

    // Also get immediate position
    navigator.geolocation.getCurrentPosition(
        handleGeolocationSuccess,
        handleGeolocationError,
        { enableHighAccuracy: true, timeout: 30000, maximumAge: 0 }
    );
    
    // Setup locate button
    const locateBtn = document.getElementById('locate-btn');
    if (locateBtn) {
        locateBtn.addEventListener('click', refreshLocation);
    }
}

function handleGeolocationSuccess(position) {
    const { latitude, longitude, accuracy } = position.coords;
    
    updateStatusLight('gps', true);
    updateMapLocation(latitude, longitude, accuracy);
    
    // Coordinate and accuracy display removed
    // if (DOM.coordLat) DOM.coordLat.textContent = latitude.toFixed(6);
    // if (DOM.coordLng) DOM.coordLng.textContent = longitude.toFixed(6);
    
    // Get location name
    reverseGeocode(latitude, longitude);
}

function handleGeolocationError(error) {
    console.warn('Geolocation error:', error.message);
    updateStatusLight('gps', false);
}

function updateMapLocation(lat, lng, accuracy, zoomToFit = false) {
    if (!leafletMap) return;

    const newPosition = [lat, lng];
    
    // Dynamic zoom based on accuracy (better accuracy = more zoom)
    if (zoomToFit || !STATE.hasInitialLocation) {
        let zoomLevel = 16;
        if (accuracy <= 10) zoomLevel = 19;  // Excellent: <10m
        else if (accuracy <= 30) zoomLevel = 18;  // Good: 10-30m
        else if (accuracy <= 100) zoomLevel = 17;  // Fair: 30-100m
        else zoomLevel = 15;  // Poor: >100m
        
        leafletMap.setView(newPosition, zoomLevel);
        STATE.hasInitialLocation = true;
    } else {
        leafletMap.panTo(newPosition);
    }
    
    if (locationMarker) locationMarker.setLatLng(newPosition);
    if (accuracyCircle && accuracy) {
        accuracyCircle.setLatLng(newPosition);
        accuracyCircle.setRadius(accuracy);
        
        // Color accuracy circle based on quality
        if (accuracy <= 10) {
            accuracyCircle.setStyle({ color: '#10B981', fillColor: '#10B981' });
        } else if (accuracy <= 50) {
            accuracyCircle.setStyle({ color: '#00D4FF', fillColor: '#00D4FF' });
        } else {
            accuracyCircle.setStyle({ color: '#F59E0B', fillColor: '#F59E0B' });
        }
    }
    
    // Accuracy badge display removed
}

function refreshLocation() {
    const locateBtn = document.getElementById('locate-btn');
    if (locateBtn) {
        locateBtn.classList.add('locating');
    }
    
    navigator.geolocation.getCurrentPosition(
        (position) => {
            const { latitude, longitude, accuracy } = position.coords;
            handleGeolocationSuccess(position);
            updateMapLocation(latitude, longitude, accuracy, true);  // Force zoom
            
            if (locateBtn) locateBtn.classList.remove('locating');
        },
        (error) => {
            console.warn('Location refresh failed:', error.message);
            if (locateBtn) locateBtn.classList.remove('locating');
        },
        { enableHighAccuracy: true, timeout: 30000, maximumAge: 0 }
    );
}

// ============================================
// REVERSE GEOCODING (Get location name from coordinates)
// ============================================

let lastGeocodedLat = null;
let lastGeocodedLng = null;
let geocodeTimeout = null;

async function reverseGeocode(lat, lng) {
    // Only geocode if location changed significantly (>50m) to avoid rate limiting
    if (lastGeocodedLat !== null && lastGeocodedLng !== null) {
        const distance = Math.sqrt(
            Math.pow((lat - lastGeocodedLat) * 111000, 2) + 
            Math.pow((lng - lastGeocodedLng) * 111000 * Math.cos(lat * Math.PI / 180), 2)
        );
        if (distance < 50) return;  // Less than 50m change, skip
    }
    
    // Debounce geocoding requests
    if (geocodeTimeout) clearTimeout(geocodeTimeout);
    
    geocodeTimeout = setTimeout(async () => {
        try {
            const locationText = document.getElementById('location-text');
            if (locationText) locationText.textContent = 'Finding location...';
            
            // Use OpenStreetMap Nominatim (free, no API key)
            const response = await fetch(
                `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18`,
                { headers: { 'Accept-Language': 'en' } }
            );
            
            if (!response.ok) throw new Error('Geocoding failed');
            
            const data = await response.json();
            
            if (data && data.address) {
                // Build a readable location name
                const address = data.address;
                let locationName = '';
                
                // Priority: specific place > road > area > city
                if (address.amenity) locationName = address.amenity;
                else if (address.building) locationName = address.building;
                else if (address.leisure) locationName = address.leisure;
                else if (address.shop) locationName = address.shop;
                else if (address.road) locationName = address.road;
                else if (address.neighbourhood) locationName = address.neighbourhood;
                else if (address.suburb) locationName = address.suburb;
                
                // Add area/city for context
                const area = address.suburb || address.neighbourhood || address.city_district || '';
                const city = address.city || address.town || address.village || '';
                
                if (locationName && area && area !== locationName) {
                    locationName += `, ${area}`;
                } else if (locationName && city) {
                    locationName += `, ${city}`;
                } else if (!locationName && area) {
                    locationName = area + (city ? `, ${city}` : '');
                } else if (!locationName && city) {
                    locationName = city;
                } else if (!locationName) {
                    locationName = data.display_name?.split(',').slice(0, 2).join(', ') || 'Unknown location';
                }
                
                if (locationText) locationText.textContent = locationName;
                
                lastGeocodedLat = lat;
                lastGeocodedLng = lng;
            }
        } catch (err) {
            console.warn('Reverse geocoding error:', err);
            const locationText = document.getElementById('location-text');
            if (locationText) locationText.textContent = 'Location unavailable';
        }
    }, 1000);  // Wait 1s before geocoding to avoid spam
}

// Cleanup geolocation on page unload
function stopGeolocation() {
    if (watchId !== null) {
        navigator.geolocation.clearWatch(watchId);
        watchId = null;
    }
}

// ============================================
// VOICE ANNOUNCEMENTS (Text-to-Speech)
// ============================================

let speechSynthesis = window.speechSynthesis;
// ============================================
// INTELLIGENT VOICE GUIDANCE SYSTEM
// ============================================
// Risk-aware, distance-based guidance for blind navigation
// Prioritizes safety over frequent narration
// Calm, short, intelligent announcements

// ==================== RISK CLASSIFICATION ====================
const RISK_CATEGORIES = {
    HIGH: {
        label: 'HIGH',
        priority: 3,
        objects: ['car', 'bus', 'truck', 'train', 'airplane']
    },
    MEDIUM: {
        label: 'MEDIUM',
        priority: 2,
        objects: ['bicycle', 'motorcycle', 'person', 'dog', 'horse']
    },
    LOW: {
        label: 'LOW',
        priority: 1,
        objects: ['chair', 'table', 'bottle', 'cup', 'laptop', 'book', 'couch', 
                  'bed', 'potted plant', 'tv', 'backpack', 'handbag', 'umbrella',
                  'bench', 'dining table', 'toilet', 'sink', 'refrigerator', 'oven',
                  'microwave', 'cell phone', 'keyboard', 'mouse', 'remote', 'clock']
    }
};

// ==================== DISTANCE LEVELS ====================
const DISTANCE_LEVELS = {
    VERY_CLOSE: { threshold: 1.2, label: 'VERY_CLOSE', priority: 3 },
    NEAR: { threshold: 3.0, label: 'NEAR', priority: 2 },
    FAR: { threshold: 6.0, label: 'FAR', priority: 1 },
    CLEAR: { threshold: Infinity, label: 'CLEAR', priority: 0 }
};

// ==================== VOICE CONFIGURATION ====================
const VOICE_CONFIG = {
    globalCooldown: 8000,      // 8 seconds - no spam
    criticalCooldown: 3000,    // 3 seconds for VERY_CLOSE  
    perObjectCooldown: 10000,  // 10 seconds per specific object
    rate: 0.92,                // Calm, clear pace
    pitch: 1.0,
    volume: 1.0,
};

// ==================== MOTION DETECTION CONFIG ====================
const MOTION_CONFIG = {
    approachThreshold: 1.05,   // 5% bbox size increase = approaching
    recedeThreshold: 0.95,     // 5% decrease = receding
    minSamples: 2,             // Need 2+ frames to determine motion
    sizeHistoryLength: 5       // Track last 5 bbox sizes
};

// ==================== STATE TRACKING ====================
const objectState = new Map();  // trackId -> { level, risk, lastAnnounced, class, position, bboxSizes[], isApproaching }
let lastSpeechTime = 0;
let preferredVoice = null;
let voiceReady = false;

// ==================== HELPER FUNCTIONS ====================

// Get risk category for an object class
function getRiskCategory(objectClass) {
    const lowerClass = objectClass.toLowerCase();
    if (RISK_CATEGORIES.HIGH.objects.includes(lowerClass)) return RISK_CATEGORIES.HIGH;
    if (RISK_CATEGORIES.MEDIUM.objects.includes(lowerClass)) return RISK_CATEGORIES.MEDIUM;
    return RISK_CATEGORIES.LOW;
}

// Get distance level
function getDistanceLevel(distanceM) {
    if (distanceM <= DISTANCE_LEVELS.VERY_CLOSE.threshold) return DISTANCE_LEVELS.VERY_CLOSE;
    if (distanceM <= DISTANCE_LEVELS.NEAR.threshold) return DISTANCE_LEVELS.NEAR;
    if (distanceM <= DISTANCE_LEVELS.FAR.threshold) return DISTANCE_LEVELS.FAR;
    return DISTANCE_LEVELS.CLEAR;
}

// Calculate bounding box area from detection
function getBboxSize(det) {
    // Support both bbox array [x1,y1,x2,y2] and individual properties
    if (det.bbox && Array.isArray(det.bbox)) {
        const [x1, y1, x2, y2] = det.bbox;
        return Math.abs((x2 - x1) * (y2 - y1));
    }
    if (det.x1 !== undefined && det.y1 !== undefined) {
        return Math.abs((det.x2 - det.x1) * (det.y2 - det.y1));
    }
    // Fallback: use width/height if available
    if (det.width && det.height) {
        return det.width * det.height;
    }
    return 0;
}

// Calculate motion status from bbox size history
function calculateMotionStatus(sizeHistory) {
    if (!sizeHistory || sizeHistory.length < MOTION_CONFIG.minSamples) {
        return { isApproaching: false, isReceding: false, isStationary: true };
    }
    
    // Compare average of recent sizes vs older sizes
    const recent = sizeHistory.slice(-2);
    const older = sizeHistory.slice(0, -2);
    
    if (older.length === 0) {
        // Only 2 samples - compare them directly
        const ratio = recent[1] / recent[0];
        return {
            isApproaching: ratio >= MOTION_CONFIG.approachThreshold,
            isReceding: ratio <= MOTION_CONFIG.recedeThreshold,
            isStationary: ratio > MOTION_CONFIG.recedeThreshold && ratio < MOTION_CONFIG.approachThreshold
        };
    }
    
    const recentAvg = recent.reduce((a, b) => a + b, 0) / recent.length;
    const olderAvg = older.reduce((a, b) => a + b, 0) / older.length;
    const ratio = recentAvg / olderAvg;
    
    return {
        isApproaching: ratio >= MOTION_CONFIG.approachThreshold,
        isReceding: ratio <= MOTION_CONFIG.recedeThreshold,
        isStationary: ratio > MOTION_CONFIG.recedeThreshold && ratio < MOTION_CONFIG.approachThreshold
    };
}

// Build intelligent guidance message based on risk + distance + position + motion
function buildSmartMessage(objectClass, risk, level, position, motionStatus) {
    const isVehicle = RISK_CATEGORIES.HIGH.objects.includes(objectClass.toLowerCase());
    const isMediumRisk = risk.label === 'MEDIUM';
    const isPerson = objectClass.toLowerCase() === 'person';
    const isApproaching = motionStatus?.isApproaching || false;
    const isStationary = motionStatus?.isStationary || true;
    
    // Direction text (only for VERY_CLOSE)
    let dirText = '';
    if (level.label === 'VERY_CLOSE') {
        if (position === 'left') dirText = ' on left';
        else if (position === 'right') dirText = ' on right';
    }
    
    // ==================== FAR DISTANCE ====================
    if (level.label === 'FAR') {
        // FAR + not approaching = SILENT for all
        if (!isApproaching) return null;
        
        // FAR + approaching HIGH RISK = Early warning
        if (isVehicle && isApproaching) return 'Vehicle approaching ahead.';
        
        // FAR + approaching MEDIUM = Brief notice
        if (isPerson && isApproaching) return 'Person approaching.';
        
        // LOW RISK + FAR = SILENT even if approaching
        if (risk.label === 'LOW') return null;
        
        return isApproaching ? `${objectClass} approaching.` : null;
    }
    
    // ==================== NEAR DISTANCE ====================
    if (level.label === 'NEAR') {
        // STATIONARY objects = reduced alerts
        if (isStationary && !isApproaching) {
            // Only announce HIGH risk stationary objects once
            if (isVehicle) return 'Vehicle nearby.';
            // LOW RISK + NEAR + STATIONARY = Silent
            if (risk.label === 'LOW') return null;
            // MEDIUM stationary = brief
            if (isPerson) return 'Person nearby.';
            return null;  // Other stationary = silent
        }
        
        // APPROACHING objects = full alerts
        if (isApproaching) {
            // HIGH RISK + NEAR + APPROACHING = Alert
            if (isVehicle) return 'Vehicle approaching. Stay alert.';
            
            // MEDIUM RISK + NEAR + APPROACHING
            if (isPerson) return 'Person approaching.';
            if (isMediumRisk) return `${objectClass} approaching.`;
            
            // LOW RISK + NEAR + APPROACHING
            return 'Obstacle approaching.';
        }
        
        // Default NEAR (not clearly stationary or approaching)
        if (isVehicle) return 'Vehicle nearby.';
        if (risk.label === 'LOW') return null;
        return null;
    }
    
    // ==================== VERY CLOSE ====================
    if (level.label === 'VERY_CLOSE') {
        // VERY_CLOSE always announces - critical safety zone
        
        // HIGH RISK + VERY_CLOSE
        if (isVehicle) {
            if (isApproaching) return `Stop. Vehicle very close${dirText}. Moving.`;
            return `Stop. Vehicle very close${dirText}.`;
        }
        
        // MEDIUM RISK + VERY_CLOSE
        if (isPerson) {
            if (isApproaching) return `Careful. Person approaching${dirText || ' ahead'}.`;
            return `Careful. Person${dirText || ' ahead'}.`;
        }
        if (isMediumRisk) {
            if (isApproaching) return `Stop. ${objectClass} approaching${dirText || ''}.`;
            return `Stop. ${objectClass}${dirText || ' ahead'}.`;
        }
        
        // LOW RISK + VERY_CLOSE = Still warn (could trip)
        if (isApproaching) return `Obstacle approaching${dirText || ' ahead'}.`;
        return `Obstacle${dirText || ' ahead'}. Stop.`;
    }
    
    return null;
}

// Select natural, calm voice
function selectNaturalVoice() {
    const voices = speechSynthesis.getVoices();
    if (!voices.length) return null;
    
    // Priority: calm, clear voices
    const preferredNames = [
        'Samantha', 'Karen', 'Daniel', 'Google UK English Female',
        'Google UK English Male', 'Microsoft Zira', 'Microsoft David',
        'Google US English', 'Alex', 'Fiona', 'Moira'
    ];
    
    for (const name of preferredNames) {
        const voice = voices.find(v => v.name.includes(name));
        if (voice) return voice;
    }
    
    const englishVoices = voices.filter(v => v.lang.startsWith('en'));
    return englishVoices.find(v => !v.default) || englishVoices[0] || voices[0];
}

// ==================== VOICE INITIALIZATION ====================
function initVoice() {
    const voiceToggle = document.getElementById('voice-toggle');
    const voiceStatus = document.getElementById('voice-status');
    const voicePanel = document.querySelector('.voice-panel');
    
    if (!voiceToggle) return;
    
    if (!speechSynthesis) {
        voiceStatus.textContent = 'Not supported';
        voiceToggle.disabled = true;
        STATE.voiceActive = false;
        return;
    }
    
    voicePanel?.classList.add('active');
    voiceStatus.textContent = 'Ready';
    updateStatusLight('voice', true);
    
    const loadVoices = () => {
        preferredVoice = selectNaturalVoice();
        voiceReady = true;
        console.log('Voice:', preferredVoice?.name || 'default');
    };
    
    speechSynthesis.onvoiceschanged = loadVoices;
    loadVoices();
    
    setTimeout(() => speak('Guidance ready.'), 1500);
    
    voiceToggle.addEventListener('click', () => {
        STATE.voiceActive = !STATE.voiceActive;
        
        if (STATE.voiceActive) {
            voicePanel?.classList.add('active');
            voiceStatus.textContent = 'Ready';
            updateStatusLight('voice', true);
            speak('Guidance on.');
        } else {
            voicePanel?.classList.remove('active');
            voiceStatus.textContent = 'Off';
            updateStatusLight('voice', false);
            speechSynthesis.cancel();
        }
    });
}

// ==================== CORE SPEAK FUNCTION ====================
function speak(text, priority = 'normal') {
    if (!STATE.voiceActive || !speechSynthesis || !text) return false;
    
    const now = Date.now();
    const cooldown = priority === 'critical' 
        ? VOICE_CONFIG.criticalCooldown 
        : VOICE_CONFIG.globalCooldown;
    
    // Enforce global cooldown (except critical can interrupt)
    if (priority !== 'critical' && now - lastSpeechTime < cooldown) return false;
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = STATE.voiceSpeed || VOICE_CONFIG.rate;
    utterance.pitch = VOICE_CONFIG.pitch;
    utterance.volume = VOICE_CONFIG.volume;
    
    if (preferredVoice) utterance.voice = preferredVoice;
    
    utterance.onstart = () => {
        const status = document.getElementById('voice-status');
        if (status) status.textContent = 'Speaking';
        document.querySelector('.voice-visualizer')?.classList.add('speaking');
    };
    
    utterance.onend = () => {
        const status = document.getElementById('voice-status');
        if (status) status.textContent = 'Ready';
        document.querySelector('.voice-visualizer')?.classList.remove('speaking');
    };
    
    if (priority === 'critical') {
        speechSynthesis.cancel();
    }
    
    speechSynthesis.speak(utterance);
    lastSpeechTime = now;
    return true;
}

// ==================== MAIN DETECTION PROCESSOR ====================
function processDetections(detections) {
    if (!STATE.voiceActive || !voiceReady || !detections?.length) return;
    
    const now = Date.now();
    const currentIds = new Set();
    let announcement = null;
    
    // Sort by risk priority (HIGH first) then by distance (closest first)
    const sorted = [...detections].sort((a, b) => {
        const riskA = getRiskCategory(a.class).priority;
        const riskB = getRiskCategory(b.class).priority;
        if (riskB !== riskA) return riskB - riskA;
        return (a.distance_m || 10) - (b.distance_m || 10);
    });
    
    for (const det of sorted) {
        const trackId = det.track_id || `${det.class}_${det.position || 'c'}`;
        currentIds.add(trackId);
        
        const distance = det.distance_m || 10;
        const level = getDistanceLevel(distance);
        const risk = getRiskCategory(det.class);
        const position = det.position || 'center';
        
        // Calculate bounding box size for motion detection
        const bboxSize = getBboxSize(det);
        
        // Skip objects beyond useful range
        if (level.label === 'CLEAR') continue;
        
        // Get previous state
        const prev = objectState.get(trackId);
        const prevLevel = prev?.level?.label;
        const prevRisk = prev?.risk?.label;
        const prevApproaching = prev?.isApproaching || false;
        
        // Update bbox size history
        let bboxSizes = prev?.bboxSizes ? [...prev.bboxSizes] : [];
        if (bboxSize > 0) {
            bboxSizes.push(bboxSize);
            // Keep only last N samples
            if (bboxSizes.length > MOTION_CONFIG.sizeHistoryLength) {
                bboxSizes = bboxSizes.slice(-MOTION_CONFIG.sizeHistoryLength);
            }
        }
        
        // Calculate motion status
        const motionStatus = calculateMotionStatus(bboxSizes);
        
        // Determine if we should announce
        const isNew = !prev;
        const levelChanged = prev && prevLevel !== level.label;
        const riskChanged = prev && prevRisk !== risk.label;
        const approachingChanged = prev && prevApproaching !== motionStatus.isApproaching;
        const perObjectCooldownOk = !prev?.lastAnnounced || 
            (now - prev.lastAnnounced > VOICE_CONFIG.perObjectCooldown);
        
        // Update state with motion tracking
        objectState.set(trackId, {
            level,
            risk,
            class: det.class,
            position,
            distance,
            bboxSizes,
            isApproaching: motionStatus.isApproaching,
            isStationary: motionStatus.isStationary,
            lastSeen: now,
            lastAnnounced: prev?.lastAnnounced || 0
        });
        
        // Check if announcement needed (including motion changes)
        const shouldAnnounce = (isNew || levelChanged || riskChanged || 
            (approachingChanged && motionStatus.isApproaching)) && perObjectCooldownOk;
        
        if (!shouldAnnounce) continue;
        
        // Build message with motion awareness
        const msg = buildSmartMessage(det.class, risk, level, position, motionStatus);
        
        // Skip silent cases (LOW + FAR = null)
        if (!msg) continue;
        
        // Track best announcement (highest priority)
        const announcePriority = level.priority * 10 + risk.priority;
        if (!announcement || announcePriority > announcement.priority) {
            announcement = {
                trackId,
                message: msg,
                priority: announcePriority,
                isCritical: level.label === 'VERY_CLOSE' || 
                           (risk.label === 'HIGH' && level.label === 'NEAR')
            };
        }
    }
    
    // Cleanup stale tracks (5 seconds)
    for (const [id, state] of objectState) {
        if (!currentIds.has(id) && now - state.lastSeen > 5000) {
            objectState.delete(id);
        }
    }
    
    // Make announcement
    if (announcement) {
        const priority = announcement.isCritical ? 'critical' : 'normal';
        const spoken = speak(announcement.message, priority);
        
        // Update last announced time if actually spoken
        if (spoken) {
            const state = objectState.get(announcement.trackId);
            if (state) state.lastAnnounced = now;
        }
    }
}

// Legacy compatibility
async function announceDetections(detections) {
    processDetections(detections);
}

// ============================================
// UTILITIES
// ============================================

function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// ============================================
// INITIALIZATION
// ============================================

function init() {
    console.log('%c👁️ VisionX PRO Dashboard v2.0', 'color: #00D4FF; font-weight: bold; font-size: 14px; text-shadow: 0 0 10px rgba(0,212,255,0.5);');

    // Initialize DOM references first
    initDOMRefs();

    // Set initial cap connection state
    updateCapConnection(false, 'Checking...');

    connectCameraStream();
    initMap();
    initVoice();
    initPremiumFeatures();

    // Event listeners
    document.getElementById('btn-reconnect')?.addEventListener('click', () => {
        stopWebcam();
        DOM.cameraOverlay?.classList.remove('hidden');
        if (DOM.cameraOverlay) {
            DOM.cameraOverlay.querySelector('p').textContent = 'Reconnecting...';
        }
        connectCameraStream();
    });

    document.getElementById('btn-fullscreen')?.addEventListener('click', toggleFullscreen);

    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
            const panel = document.querySelector('.camera-panel');
            if (panel?.style.position === 'fixed') toggleFullscreen();
        }
    });

    // Polling
    fetchStatus();
    fetchGPS();
    STATE.pollingTimer = setInterval(fetchStatus, CONFIG.POLL_INTERVAL);
    setInterval(fetchGPS, CONFIG.POLL_INTERVAL * 2);

    // Initial render
    renderHistory();
}

// ============================================
// PREMIUM FEATURES
// ============================================

function initPremiumFeatures() {
    // Header settings dropdown toggle
    const settingsBtn = document.getElementById('header-settings-btn');
    const settingsDropdown = document.getElementById('settings-dropdown');
    
    if (settingsBtn && settingsDropdown) {
        settingsBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            settingsBtn.classList.toggle('active');
            settingsDropdown.classList.toggle('show');
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!settingsDropdown.contains(e.target) && !settingsBtn.contains(e.target)) {
                settingsBtn.classList.remove('active');
                settingsDropdown.classList.remove('show');
            }
        });
    }
    
    // Voice speed control
    const voiceSpeedSlider = document.getElementById('voice-speed');
    if (voiceSpeedSlider) {
        voiceSpeedSlider.addEventListener('input', (e) => {
            STATE.voiceSpeed = parseFloat(e.target.value);
        });
    }

    // Detection sensitivity control
    const sensitivitySlider = document.getElementById('detection-sensitivity');
    if (sensitivitySlider) {
        sensitivitySlider.addEventListener('input', (e) => {
            STATE.detectionSensitivity = parseFloat(e.target.value);
        });
    }

    // Initial environment detection
    updateEnvironmentBadge();
}

function updateEnvironmentBadge() {
    const envIcon = document.querySelector('.env-icon');
    const envText = document.getElementById('env-text');
    if (!envIcon || !envText) return;
    
    const detections = STATE.lastDetections || [];
    
    // Analyze detections to guess environment
    let env = { icon: '🏙️', text: 'Urban', type: 'urban' };
    
    const hasVehicles = detections.some(d => ['car', 'bus', 'truck', 'motorcycle', 'bicycle'].includes(d.class));
    const hasPeople = detections.some(d => d.class === 'person');
    const hasIndoor = detections.some(d => ['chair', 'couch', 'bed', 'dining table', 'laptop'].includes(d.class));
    const hasOutdoor = detections.some(d => ['traffic light', 'stop sign', 'fire hydrant', 'parking meter'].includes(d.class));
    
    if (STATE.currentMode !== 'auto') {
        const modes = {
            indoor: { icon: '🏠', text: 'Indoor', type: 'indoor' },
            outdoor: { icon: '🌳', text: 'Outdoor', type: 'outdoor' },
            night: { icon: '🌙', text: 'Night Mode', type: 'night' },
        };
        env = modes[STATE.currentMode] || env;
    } else if (hasIndoor && !hasVehicles) {
        env = { icon: '🏠', text: 'Indoor', type: 'indoor' };
    } else if (hasVehicles || hasOutdoor) {
        env = { icon: '🛣️', text: 'Street', type: 'street' };
    } else if (hasPeople && detections.length > 3) {
        env = { icon: '👥', text: 'Crowded', type: 'crowd' };
    }
    
    STATE.environment = env.type;
    envIcon.textContent = env.icon;
    envText.textContent = env.text;
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    stopWebcam();
    clearTimeout(STATE.streamRetryTimer);
    clearInterval(STATE.pollingTimer);
    stopGeolocation();
});

// Start when ready
document.readyState === 'loading'
    ? document.addEventListener('DOMContentLoaded', init)
    : init();
