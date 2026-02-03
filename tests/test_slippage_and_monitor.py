"""
Tests for slippage model and adverse selection monitor
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.slippage_model import SlippageModel
from utils.adverse_selection_monitor import AdverseSelectionMonitor, AlphaDecayTracker


class TestSlippageModel(unittest.TestCase):
    
    def setUp(self):
        self.model = SlippageModel()
    
    def test_get_base_slippage(self):
        """Test base slippage for different liquidity tiers"""
        # Low liquidity
        self.assertEqual(self.model.get_base_slippage(5000), 0.05)
        # Medium liquidity
        self.assertEqual(self.model.get_base_slippage(25000), 0.03)
        # High liquidity
        self.assertEqual(self.model.get_base_slippage(200000), 0.01)
    
    def test_estimate_slippage_components(self):
        """Test slippage estimation includes all components"""
        est = self.model.estimate_slippage(100, 50000, spread=0.02)
        
        self.assertIn('spread_cost', est)
        self.assertIn('market_impact', est)
        self.assertIn('total_slippage', est)
        self.assertGreaterEqual(est['total_slippage'], 0)
    
    def test_slippage_increases_with_position_size(self):
        """Test that larger positions have higher slippage"""
        small = self.model.estimate_slippage(100, 50000)['total_slippage']
        large = self.model.estimate_slippage(1000, 50000)['total_slippage']
        
        self.assertGreater(large, small)
    
    def test_recommend_position_size(self):
        """Test position size recommendation"""
        rec = self.model.recommend_position_size(100000, max_slippage=0.03)
        
        # Verify recommendation is reasonable
        self.assertGreater(rec, 0)
        self.assertLess(rec, 100000 * 0.2)  # Less than 20% of liquidity
        
        # Verify it meets slippage constraint
        est = self.model.estimate_slippage(rec, 100000)
        self.assertLessEqual(est['total_slippage'], 0.03)


class TestAdverseSelectionMonitor(unittest.TestCase):
    
    def setUp(self):
        self.monitor = AdverseSelectionMonitor(lookback_days=30)
    
    def test_analyze_insufficient_data(self):
        """Test handling of insufficient data"""
        result = self.monitor.analyze_recent_trades()
        
        # Should return insufficient_data if no trades
        self.assertIn('status', result)
    
    def test_alerts_list_initially_empty(self):
        """Test that alerts list starts empty"""
        self.assertEqual(self.monitor.alerts, [])


class TestAlphaDecayTracker(unittest.TestCase):
    
    def setUp(self):
        self.tracker = AlphaDecayTracker()
    
    def test_detect_decay_insufficient_data(self):
        """Test decay detection with insufficient data"""
        decay = self.tracker.detect_decay()
        
        # Should return insufficient_data
        self.assertIn('status', decay)


if __name__ == '__main__':
    unittest.main()
