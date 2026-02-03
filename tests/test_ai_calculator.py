"""
Unit tests for AI calculator.
"""

import unittest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.ai_calculator import AIOddsCalculator


class TestAIOddsCalculator(unittest.TestCase):
    
    def setUp(self):
        self.calc = AIOddsCalculator(bankroll=10000)
    
    def test_initialization(self):
        """Test calculator initialization"""
        self.assertEqual(self.calc.bankroll, 10000)
        self.assertIsNotNone(self.calc.estimator)
        self.assertIsNotNone(self.calc.kelly)
        self.assertIsNotNone(self.calc.portfolio)
        self.assertIsNotNone(self.calc.tracker)
    
    def test_show_calibration(self):
        """Test calibration report display"""
        # Should not raise error
        try:
            self.calc.show_calibration()
        except Exception as e:
            self.fail(f"show_calibration() raised {e}")
    
    def test_show_strategy_performance(self):
        """Test strategy performance display"""
        # Should not raise error
        try:
            self.calc.show_strategy_performance()
        except Exception as e:
            self.fail(f"show_strategy_performance() raised {e}")


if __name__ == '__main__':
    unittest.main()
