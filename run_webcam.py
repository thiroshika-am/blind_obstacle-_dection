
"""
Script to run the Smart AI Cap backend with local webcam input.
Using camera source 0 (default webcam).
"""
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.getcwd())

from backend.main import SmartCapBackend

if __name__ == "__main__":
    print("Starting Smart AI Cap in WEBCAM MODE...")
    print("Press Ctrl+C to stop.")
    
    # Initialize implementation with video_source=0
    backend = SmartCapBackend(video_source=0)
    
    try:
        backend.start()
    except KeyboardInterrupt:
        print("\nStopping...")
        backend.shutdown()
