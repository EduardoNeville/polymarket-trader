"""
Test for Issue #10 - Division by zero fix
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.edge_estimator import EnsembleEdgeEstimator


class TestDivisionByZeroFix(unittest.TestCase):
    
    def setUp(self):
        self.estimator = EnsembleEdgeEstimator()
    
    def test_zero_market_price(self):
        """Test handling of zero market price"""
        # Should not raise ZeroDivisionError
        result = self.estimator._calculate_expected_return(0.0, 0.5, 0.8)
        self.assertEqual(result, 0.0)
    
    def test_extreme_market_price_zero(self):
        """Test market price of 0.0"""
        result = self.estimator._calculate_expected_return(0.0, 0.7, 0.8)
        self.assertEqual(result, 0.0)
    
    def test_extreme_market_price_one(self):
        """Test market price of 1.0"""
        result = self.estimator._calculate_expected_return(1.0, 0.3, 0.8)
        self.assertEqual(result, 0.0)
    
    def test_near_zero_price(self):
        """Test very small market price"""
        result = self.estimator._calculate_expected_return(0.005, 0.7, 0.8)
        self.assertEqual(result, 0.0)
    
    def test_normal_price(self):
        """Test normal market price returns positive expected return"""
        result = self.estimator._calculate_expected_return(0.5, 0.7, 0.8)
        self.assertGreater(result, 0)


if __name__ == '__main__':
    unittest.main()
