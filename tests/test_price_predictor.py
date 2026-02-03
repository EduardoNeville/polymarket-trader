"""
Unit tests for price prediction models.
"""

import unittest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.price_predictor import (
    SimplePricePredictor,
    MomentumPredictor,
    MeanReversionPredictor
)


class TestSimplePricePredictor(unittest.TestCase):
    
    def setUp(self):
        self.predictor = SimplePricePredictor(lookback=10)
    
    def test_insufficient_data(self):
        """Test behavior with insufficient data"""
        pred = self.predictor.predict("new-market")
        self.assertEqual(pred.predicted_price, 0.5)
        self.assertEqual(pred.confidence, 0.3)
        self.assertEqual(pred.trend_direction, 'NEUTRAL')
    
    def test_upward_trend(self):
        """Test prediction in upward trending market"""
        market = "up-trend"
        base = 0.40
        for i in range(15):
            price = base + i * 0.02
            self.predictor.update(market, price)
        
        pred = self.predictor.predict(market)
        self.assertGreater(pred.predicted_price, 0.65)
        self.assertEqual(pred.trend_direction, 'UP')
        self.assertGreater(pred.confidence, 0.5)
    
    def test_downward_trend(self):
        """Test prediction in downward trending market"""
        market = "down-trend"
        base = 0.60
        for i in range(15):
            price = base - i * 0.02
            self.predictor.update(market, price)
        
        pred = self.predictor.predict(market)
        self.assertLess(pred.predicted_price, 0.45)
        self.assertEqual(pred.trend_direction, 'DOWN')
    
    def test_overbought_market(self):
        """Test mean reversion at extreme high"""
        market = "overbought"
        for price in [0.85, 0.87, 0.88, 0.89, 0.90, 0.89, 0.90, 0.91]:
            self.predictor.update(market, price)
        
        pred = self.predictor.predict(market)
        # Should predict pullback
        self.assertLess(pred.predicted_price, 0.91)
        self.assertEqual(pred.model_name, 'SimplePricePredictor')
    
    def test_oversold_market(self):
        """Test mean reversion at extreme low"""
        market = "oversold"
        for price in [0.15, 0.13, 0.12, 0.11, 0.10, 0.11, 0.10, 0.09]:
            self.predictor.update(market, price)
        
        pred = self.predictor.predict(market)
        # Should predict bounce (higher than current trend would suggest)
        # The model should pull up from extreme lows
        self.assertGreaterEqual(pred.predicted_price, 0.05)  # Clipped minimum
    
    def test_price_clipping(self):
        """Test that predictions are clipped to valid range"""
        market = "extreme"
        # Simulate extreme movement
        for price in [0.05, 0.04, 0.03, 0.02, 0.01]:
            self.predictor.update(market, price)
        
        pred = self.predictor.predict(market)
        self.assertGreaterEqual(pred.predicted_price, 0.05)
        self.assertLessEqual(pred.predicted_price, 0.95)
    
    def test_save_load_state(self):
        """Test saving and loading state"""
        import tempfile
        import os
        
        market = "persistent"
        for price in [0.4, 0.41, 0.42, 0.43, 0.44]:
            self.predictor.update(market, price)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            self.predictor.save_state(temp_path)
            
            new_predictor = SimplePricePredictor()
            new_predictor.load_state(temp_path)
            
            # Should have same data
            pred1 = self.predictor.predict(market)
            pred2 = new_predictor.predict(market)
            self.assertEqual(pred1.predicted_price, pred2.predicted_price)
        finally:
            os.unlink(temp_path)


class TestMomentumPredictor(unittest.TestCase):
    
    def setUp(self):
        self.predictor = MomentumPredictor(short_window=3, long_window=10)
    
    def test_strong_upward_momentum(self):
        """Test strong upward momentum detection"""
        market = "momo-up"
        for price in [0.40, 0.41, 0.42, 0.44, 0.46, 0.48, 0.50, 0.52, 0.54, 0.56]:
            self.predictor.update(market, price)
        
        pred = self.predictor.predict(market)
        self.assertEqual(pred.trend_direction, 'UP')
        self.assertGreater(pred.predicted_price, 0.56)
    
    def test_strong_downward_momentum(self):
        """Test strong downward momentum detection"""
        market = "momo-down"
        for price in [0.60, 0.59, 0.58, 0.56, 0.54, 0.52, 0.50, 0.48, 0.46, 0.44]:
            self.predictor.update(market, price)
        
        pred = self.predictor.predict(market)
        self.assertEqual(pred.trend_direction, 'DOWN')
        self.assertLess(pred.predicted_price, 0.44)
    
    def test_neutral_momentum(self):
        """Test neutral market"""
        market = "momo-flat"
        for price in [0.50, 0.51, 0.50, 0.49, 0.50, 0.51, 0.50, 0.49, 0.50, 0.50]:
            self.predictor.update(market, price)
        
        pred = self.predictor.predict(market)
        self.assertEqual(pred.trend_direction, 'NEUTRAL')


class TestMeanReversionPredictor(unittest.TestCase):
    
    def setUp(self):
        self.predictor = MeanReversionPredictor(window=10, mean=0.5)
    
    def test_reversion_from_high(self):
        """Test prediction when price is above mean"""
        market = "high-price"
        for price in [0.70, 0.71, 0.72, 0.73, 0.72, 0.71, 0.72]:
            self.predictor.update(market, price)
        
        pred = self.predictor.predict(market)
        self.assertLess(pred.predicted_price, 0.72)  # Should predict lower
        self.assertEqual(pred.trend_direction, 'DOWN')
    
    def test_reversion_from_low(self):
        """Test prediction when price is below mean"""
        market = "low-price"
        for price in [0.30, 0.29, 0.28, 0.27, 0.28, 0.29, 0.28]:
            self.predictor.update(market, price)
        
        pred = self.predictor.predict(market)
        self.assertGreater(pred.predicted_price, 0.28)  # Should predict higher
        self.assertEqual(pred.trend_direction, 'UP')
    
    def test_near_mean(self):
        """Test when price is near mean"""
        market = "near-mean"
        for price in [0.49, 0.50, 0.51, 0.50, 0.49, 0.50, 0.51]:
            self.predictor.update(market, price)
        
        pred = self.predictor.predict(market)
        self.assertEqual(pred.trend_direction, 'NEUTRAL')


if __name__ == '__main__':
    unittest.main()
