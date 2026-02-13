
"""
==========================================
ULTRASONIC SENSOR TEST POOL
Verify distance measurement logic
==========================================
"""

import unittest
from unittest.mock import MagicMock, patch
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestUltrasonicLogic(unittest.TestCase):
    
    def test_distance_calculation(self):
        """Test the conversion of pulse time to distance"""
        # Speed of sound: 343m/s = 0.0343 cm/us = 0.343 mm/us
        # Distance = (Time * Speed) / 2
        
        # Case 1: 1000us pulse
        # Dist = (1000 * 0.343) / 2 = 171.5 mm
        pulse_time_us = 1000
        expected_mm = 171
        
        # Calculation formula verification
        calculated = int((pulse_time_us * 0.343) / 2)
        self.assertAlmostEqual(calculated, expected_mm, delta=1)
        
        logger.info(f"✓ Calculated distance for {pulse_time_us}us: {calculated}mm")

    def test_threshold_alerts(self):
        """Test obstacle alert thresholds"""
        
        def check_alert(distance_mm):
            if distance_mm < 500:
                return "CRITICAL"
            elif distance_mm < 1000:
                return "WARNING"
            else:
                return "SAFE"
        
        self.assertEqual(check_alert(400), "CRITICAL")
        self.assertEqual(check_alert(800), "WARNING")
        self.assertEqual(check_alert(1500), "SAFE")
        
        logger.info("✓ Alert threshold logic verified")

if __name__ == '__main__':
    print("RUNNING ULTRASONIC LOGIC TESTS...")
    unittest.main()
