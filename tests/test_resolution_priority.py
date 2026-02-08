"""
Tests for resolution-time prioritization in paper trading signals
Tests the time multiplier logic and priority scoring
"""

import unittest
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.paper_trading_signals import PaperTradingSignalGenerator


class MockMarket:
    """Mock market object for testing"""
    def __init__(self, end_date=None):
        self.end_date = end_date


class TestCalculateTimeToResolution(unittest.TestCase):
    """Tests for calculate_time_to_resolution method"""
    
    def setUp(self):
        self.generator = PaperTradingSignalGenerator()
    
    def test_days_in_future(self):
        """Test calculating days for a future date"""
        future_date = (datetime.now(timezone.utc) + timedelta(days=45)).isoformat()
        market = MockMarket(end_date=future_date)
        
        days = self.generator.calculate_time_to_resolution(market)
        self.assertIsNotNone(days)
        self.assertTrue(44 <= days <= 46)  # Allow small tolerance
    
    def test_past_date_returns_zero(self):
        """Test that past dates return 0 (not negative)"""
        past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        market = MockMarket(end_date=past_date)
        
        days = self.generator.calculate_time_to_resolution(market)
        self.assertEqual(days, 0)
    
    def test_no_end_date_returns_none(self):
        """Test that missing end_date returns None"""
        market = MockMarket(end_date=None)
        
        days = self.generator.calculate_time_to_resolution(market)
        self.assertIsNone(days)
    
    def test_iso_format_with_z(self):
        """Test parsing ISO format with Z suffix"""
        future = datetime.now(timezone.utc) + timedelta(days=30)
        date_str = future.strftime('%Y-%m-%dT%H:%M:%SZ')
        market = MockMarket(end_date=date_str)
        
        days = self.generator.calculate_time_to_resolution(market)
        self.assertIsNotNone(days)
        self.assertTrue(29 <= days <= 31)
    
    def test_fractional_days(self):
        """Test that partial days are calculated correctly"""
        # 12 hours from now
        future = datetime.now(timezone.utc) + timedelta(hours=12)
        market = MockMarket(end_date=future.isoformat())
        
        days = self.generator.calculate_time_to_resolution(market)
        self.assertIsNotNone(days)
        self.assertTrue(0 <= days < 1)  # Should be fractional


class TestResolutionPriority(unittest.TestCase):
    """Tests for get_resolution_priority method"""
    
    def setUp(self):
        self.generator = PaperTradingSignalGenerator()
    
    def test_urgent_priority_less_than_7_days(self):
        """Test 1.5x multiplier for <7 days"""
        edge = 0.10  # 10% edge
        days = 3
        
        priority = self.generator.get_resolution_priority(days, edge)
        expected = edge * 1.5  # 0.15
        
        self.assertAlmostEqual(priority, expected, places=3)
    
    def test_near_term_priority_7_to_30_days(self):
        """Test 1.25x multiplier for 7-30 days"""
        edge = 0.10
        days = 15
        
        priority = self.generator.get_resolution_priority(days, edge)
        expected = edge * 1.25  # 0.125
        
        self.assertAlmostEqual(priority, expected, places=3)
    
    def test_medium_priority_30_to_90_days(self):
        """Test 1.1x multiplier for 30-90 days"""
        edge = 0.10
        days = 60
        
        priority = self.generator.get_resolution_priority(days, edge)
        expected = edge * 1.1  # 0.11
        
        self.assertAlmostEqual(priority, expected, places=3)
    
    def test_standard_priority_90_plus_days(self):
        """Test 1.0x multiplier for 90+ days"""
        edge = 0.10
        days = 120
        
        priority = self.generator.get_resolution_priority(days, edge)
        expected = edge * 1.0  # 0.10
        
        self.assertAlmostEqual(priority, expected, places=3)
    
    def test_boundary_7_days(self):
        """Test boundary at exactly 7 days (should be near-term)"""
        edge = 0.10
        days = 7
        
        priority = self.generator.get_resolution_priority(days, edge)
        # 7 days falls into the <30 category (1.25x)
        expected = edge * 1.25
        
        self.assertAlmostEqual(priority, expected, places=3)
    
    def test_boundary_30_days(self):
        """Test boundary at exactly 30 days"""
        edge = 0.10
        days = 30
        
        priority = self.generator.get_resolution_priority(days, edge)
        # 30 days falls into <90 category (1.1x)
        expected = edge * 1.1
        
        self.assertAlmostEqual(priority, expected, places=3)
    
    def test_boundary_90_days(self):
        """Test boundary at exactly 90 days"""
        edge = 0.10
        days = 90
        
        priority = self.generator.get_resolution_priority(days, edge)
        # 90 days falls into 90+ category (1.0x)
        expected = edge * 1.0
        
        self.assertAlmostEqual(priority, expected, places=3)
    
    def test_zero_days(self):
        """Test same-day resolution (0 days)"""
        edge = 0.15
        days = 0
        
        priority = self.generator.get_resolution_priority(days, edge)
        expected = edge * 1.5  # 0.225
        
        self.assertAlmostEqual(priority, expected, places=3)
    
    def test_very_long_term(self):
        """Test multi-year resolution"""
        edge = 0.12
        days = 365 * 3  # 3 years
        
        priority = self.generator.get_resolution_priority(days, edge)
        expected = edge * 1.0  # Standard multiplier
        
        self.assertAlmostEqual(priority, expected, places=3)


class TestPriorityComparison(unittest.TestCase):
    """Tests comparing priority scores between different timeframes"""
    
    def setUp(self):
        self.generator = PaperTradingSignalGenerator()
    
    def test_urgent_trumps_long_term(self):
        """A lower-edge urgent trade should beat a higher-edge long-term trade"""
        urgent_trade = self.generator.get_resolution_priority(3, 0.08)
        long_term_trade = self.generator.get_resolution_priority(200, 0.10)
        
        # 8% edge × 1.5 = 0.12 vs 10% edge × 1.0 = 0.10
        self.assertGreater(urgent_trade, long_term_trade)
    
    def test_near_term_vs_long_term(self):
        """Near-term with same edge beats long-term"""
        near_term = self.generator.get_resolution_priority(20, 0.10)
        long_term = self.generator.get_resolution_priority(150, 0.10)
        
        # 10% × 1.25 = 0.125 vs 10% × 1.0 = 0.10
        self.assertGreater(near_term, long_term)
    
    def test_same_edge_different_times(self):
        """Same edge should result in priority order: urgent > near > medium > long"""
        edge = 0.10
        
        urgent = self.generator.get_resolution_priority(3, edge)
        near = self.generator.get_resolution_priority(20, edge)
        medium = self.generator.get_resolution_priority(60, edge)
        long = self.generator.get_resolution_priority(120, edge)
        
        self.assertGreater(urgent, near)
        self.assertGreater(near, medium)
        self.assertGreater(medium, long)
    
    def test_higher_edge_can_overcome_time(self):
        """A much higher edge long-term can beat lower edge near-term"""
        near_trade = self.generator.get_resolution_priority(20, 0.06)
        long_trade = self.generator.get_resolution_priority(200, 0.10)
        
        # 6% × 1.25 = 0.075 vs 10% × 1.0 = 0.10
        self.assertGreater(long_trade, near_trade)


class TestTimeMultiplierValues(unittest.TestCase):
    """Tests verifying exact multiplier values"""
    
    def setUp(self):
        self.generator = PaperTradingSignalGenerator()
        self.test_edge = 0.10
    
    def test_exact_multipliers(self):
        """Verify the exact multiplier constants"""
        test_cases = [
            (1, 1.5),    # 1 day
            (6, 1.5),    # 6 days
            (7, 1.25),   # 7 days (boundary)
            (29, 1.25),  # 29 days
            (30, 1.1),   # 30 days (boundary)
            (89, 1.1),   # 89 days
            (90, 1.0),   # 90 days (boundary)
            (365, 1.0),  # 1 year
        ]
        
        for days, expected_multiplier in test_cases:
            with self.subTest(days=days):
                priority = self.generator.get_resolution_priority(days, self.test_edge)
                expected_priority = self.test_edge * expected_multiplier
                
                self.assertAlmostEqual(
                    priority, expected_priority, places=3,
                    msg=f"Failed for days={days}: expected {expected_multiplier}x multiplier"
                )


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and error handling"""
    
    def setUp(self):
        self.generator = PaperTradingSignalGenerator()
    
    def test_negative_edge(self):
        """Test handling of negative edge (NO trades)"""
        days = 30
        edge = -0.10  # Short signal
        
        priority = self.generator.get_resolution_priority(days, edge)
        expected = edge * 1.1  # -0.11 (negative edge is preserved)
        
        self.assertAlmostEqual(priority, expected, places=3)
        self.assertLess(priority, 0)  # Should remain negative
    
    def test_very_small_edge(self):
        """Test with minimum edge threshold"""
        days = 10
        edge = 0.001  # Very small edge
        
        priority = self.generator.get_resolution_priority(days, edge)
        expected = edge * 1.25  # Still applies time multiplier
        
        self.assertAlmostEqual(priority, expected, places=4)
    
    def test_large_edge(self):
        """Test with very high edge"""
        days = 45
        edge = 0.50  # 50% edge
        
        priority = self.generator.get_resolution_priority(days, edge)
        expected = edge * 1.1  # 0.55
        
        self.assertAlmostEqual(priority, expected, places=3)


if __name__ == "__main__":
    unittest.main()
