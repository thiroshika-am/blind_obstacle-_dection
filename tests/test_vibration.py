
"""
==========================================
VIBRATION CONTROL TEST SUITE
Verify haptic feedback patterns
==========================================
"""

import unittest
from unittest.mock import MagicMock
import sys

# Mock serial if not present
sys.modules['serial'] = MagicMock()
# Mock visual dependencies to avoid import errors from package level
sys.modules['cv2'] = MagicMock()
sys.modules['numpy'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['easyocr'] = MagicMock()


# Add parent directory to path
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_modules.vibration_control import VibrationController, AlertLevel

class TestVibration(unittest.TestCase):
    
    def setUp(self):
        self.controller = VibrationController(serial_port="COM_MOCK")

        
    def test_pattern_selection(self):
        """Test correct pattern selection for alert levels"""
        
        # Check SAFE pattern
        pattern = self.controller.PATTERNS[AlertLevel.SAFE]
        self.assertEqual(pattern['pattern'], []) # Should be empty/no vibration
        
        # Check CRITICAL pattern
        pattern = self.controller.PATTERNS[AlertLevel.CRITICAL]
        # Should be intense (intensity > 200)
        self.assertTrue(len(pattern['pattern']) > 0)
        self.assertTrue(pattern['intensity'] > 200) 
 
        
        print("✓ Pattern configurations verified")
        
    def test_mock_controller(self):
        """Test the mock controller implementation"""
        from ai_modules.vibration_control import SimpleVibrationMock
        
        mock = SimpleVibrationMock()
        mock.vibrate(255, 100)
        # Should just print, no error
        self.assertTrue(True)

if __name__ == '__main__':
    print("RUNNING VIBRATION TESTS...")
    unittest.main()
