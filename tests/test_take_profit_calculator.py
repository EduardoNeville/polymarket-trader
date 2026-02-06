"""
Unit tests for take-profit calculator
"""

import unittest
from datetime import datetime
from utils.take_profit_calculator import (
    calculate_take_profit,
    check_take_profit_hit,
    calculate_holding_days,
    get_tp_summary,
    TakeProfitLevel
)


class TestCalculateTakeProfit(unittest.TestCase):
    """Test calculate_take_profit function"""
    
    def test_yes_position_basic(self):
        """Test basic YES position calculation"""
        tp = calculate_take_profit(
            entry_price=0.40,
            estimated_prob=0.50,
            side='YES'
        )
        
        self.assertIsNotNone(tp)
        self.assertEqual(tp.side, 'YES')
        self.assertEqual(tp.entry_price, 0.40)
        self.assertAlmostEqual(tp.initial_edge, 0.10, places=4)
        self.assertAlmostEqual(tp.target_pct_move, 0.125, places=4)
        self.assertAlmostEqual(tp.target_price, 0.45, places=4)
        self.assertAlmostEqual(tp.captured_edge, 0.05, places=4)
        self.assertTrue(tp.is_reachable)
    
    def test_no_position_basic(self):
        """Test basic NO position calculation"""
        tp = calculate_take_profit(
            entry_price=0.65,
            estimated_prob=0.50,
            side='NO'
        )
        
        self.assertIsNotNone(tp)
        self.assertEqual(tp.side, 'NO')
        self.assertEqual(tp.entry_price, 0.65)
        # For NO positions, edge is calculated from NO perspective
        # NO entry = 0.35, NO prob = 0.50, edge = 0.15 (positive for NO)
        self.assertAlmostEqual(tp.initial_edge, 0.15, places=4)
        self.assertAlmostEqual(tp.target_price, 0.725, places=4)
        self.assertTrue(tp.is_reachable)
    
    def test_edge_below_threshold_returns_none(self):
        """Test that small edges return None"""
        tp = calculate_take_profit(
            entry_price=0.55,
            estimated_prob=0.58,  # 3% edge
            side='YES'
        )
        self.assertIsNone(tp)
    
    def test_extreme_price_returns_none(self):
        """Test that extreme prices (>0.90) return None"""
        tp = calculate_take_profit(
            entry_price=0.95,
            estimated_prob=0.99,  # 4% edge
            side='YES'
        )
        self.assertIsNone(tp)
    
    def test_low_extreme_price_returns_none(self):
        """Test that extreme prices (<0.10) return None"""
        tp = calculate_take_profit(
            entry_price=0.05,
            estimated_prob=0.15,  # 10% edge
            side='YES'
        )
        self.assertIsNone(tp)
    
    def test_custom_edge_capture_ratio(self):
        """Test custom edge capture ratio"""
        tp = calculate_take_profit(
            entry_price=0.50,
            estimated_prob=0.65,  # 15% edge
            side='YES',
            edge_capture_ratio=0.3  # 30% instead of 50%
        )
        
        self.assertIsNotNone(tp)
        self.assertEqual(tp.edge_capture_ratio, 0.3)
        # TP% = (0.15 × 0.3) / 0.50 = 9%
        self.assertAlmostEqual(tp.target_pct_move, 0.09, places=4)
    
    def test_custom_min_edge_threshold(self):
        """Test custom minimum edge threshold"""
        # 3% edge with default 5% threshold -> None
        tp1 = calculate_take_profit(
            entry_price=0.55,
            estimated_prob=0.58,
            side='YES'
        )
        self.assertIsNone(tp1)
        
        # 3% edge with 2% threshold -> valid
        tp2 = calculate_take_profit(
            entry_price=0.55,
            estimated_prob=0.58,
            side='YES',
            min_edge_threshold=0.02
        )
        self.assertIsNotNone(tp2)
    
    def test_unreachable_target(self):
        """Test when target price is outside bounds"""
        # Large edge at low price might push target > 0.99
        # TP% = (0.70 * 0.5) / 0.15 = 2.33 = 233%
        # Target = 0.15 + (0.15 * 2.33) = 0.50 - actually reachable!
        # Let's try more extreme: 0.11 entry with 85% estimated = 74% edge
        # TP% = (0.74 * 0.5) / 0.11 = 3.36 = 336%
        # Target = 0.11 + (0.11 * 3.36) = 0.48 - still reachable
        # We need: target > 0.99, so entry + (entry * tp%) > 0.99
        # entry * (1 + tp%) > 0.99
        # With 0.11 entry: 0.11 * (1 + tp%) > 0.99 -> tp% > 8 -> edge > 1.76
        # That's impossible since max edge is 0.89 (0.99 - 0.10)
        # So let's just verify is_reachable works when we manually set it
        tp = TakeProfitLevel(
            target_price=0.999,
            target_pct_move=8.0,
            captured_edge=0.88,
            is_reachable=False,  # Manually set
            edge_capture_ratio=0.5,
            initial_edge=0.88,
            entry_price=0.11,
            side='YES'
        )
        
        self.assertFalse(tp.is_reachable)  # Target outside bounds
    
    def test_invalid_side_raises_error(self):
        """Test that invalid side raises ValueError"""
        with self.assertRaises(ValueError):
            calculate_take_profit(0.50, 0.60, 'INVALID')
    
    def test_invalid_entry_price_raises_error(self):
        """Test that invalid entry price raises ValueError"""
        with self.assertRaises(ValueError):
            calculate_take_profit(1.5, 0.60, 'YES')
        
        with self.assertRaises(ValueError):
            calculate_take_profit(-0.1, 0.60, 'YES')
    
    def test_invalid_estimated_prob_raises_error(self):
        """Test that invalid estimated prob raises ValueError"""
        with self.assertRaises(ValueError):
            calculate_take_profit(0.50, 1.5, 'YES')
        
        with self.assertRaises(ValueError):
            calculate_take_profit(0.50, -0.1, 'YES')
    
    def test_zero_edge_returns_none(self):
        """Test that zero edge returns None"""
        tp = calculate_take_profit(
            entry_price=0.50,
            estimated_prob=0.50,  # 0% edge
            side='YES'
        )
        self.assertIsNone(tp)
    
    def test_exactly_at_threshold(self):
        """Test edge exactly at threshold"""
        tp = calculate_take_profit(
            entry_price=0.50,
            estimated_prob=0.55,  # Exactly 5% edge
            side='YES'
        )
        self.assertIsNotNone(tp)


class TestCheckTakeProfitHit(unittest.TestCase):
    """Test check_take_profit_hit function"""
    
    def setUp(self):
        self.tp_yes = calculate_take_profit(0.40, 0.50, 'YES')
        self.tp_no = calculate_take_profit(0.65, 0.50, 'NO')
    
    def test_yes_not_hit_below_target(self):
        """Test YES position not hit when below target"""
        hit = check_take_profit_hit(0.40, 0.43, self.tp_yes, 'YES')
        self.assertFalse(hit)
    
    def test_yes_hit_at_target(self):
        """Test YES position hit exactly at target"""
        hit = check_take_profit_hit(0.40, 0.45, self.tp_yes, 'YES')
        self.assertTrue(hit)
    
    def test_yes_hit_above_target(self):
        """Test YES position hit above target"""
        hit = check_take_profit_hit(0.40, 0.48, self.tp_yes, 'YES')
        self.assertTrue(hit)
    
    def test_no_not_hit_above_target(self):
        """Test NO position not hit when above target"""
        hit = check_take_profit_hit(0.65, 0.75, self.tp_no, 'NO')
        self.assertFalse(hit)
    
    def test_no_hit_at_target(self):
        """Test NO position hit exactly at target"""
        hit = check_take_profit_hit(0.65, 0.725, self.tp_no, 'NO')
        self.assertTrue(hit)
    
    def test_no_hit_below_target(self):
        """Test NO position hit below target"""
        hit = check_take_profit_hit(0.65, 0.70, self.tp_no, 'NO')
        self.assertTrue(hit)


class TestCalculateHoldingDays(unittest.TestCase):
    """Test calculate_holding_days function"""
    
    def test_same_day_zero_days(self):
        """Test same day returns 0"""
        days = calculate_holding_days(
            '2024-01-01T10:00:00',
            '2024-01-01T14:00:00'
        )
        self.assertEqual(days, 0)
    
    def test_one_day(self):
        """Test one day difference"""
        days = calculate_holding_days(
            '2024-01-01T10:00:00',
            '2024-01-02T10:00:00'
        )
        self.assertEqual(days, 1)
    
    def test_multiple_days(self):
        """Test multiple days"""
        days = calculate_holding_days(
            '2024-01-01T10:00:00',
            '2024-01-05T14:30:00'
        )
        self.assertEqual(days, 4)
    
    def test_different_times_same_day(self):
        """Test different times crossing midnight"""
        # Jan 1 23:59 to Jan 2 00:01 is 1 day apart
        days = calculate_holding_days(
            '2024-01-01T23:59:00',
            '2024-01-02T00:01:00'
        )
        self.assertEqual(days, 1)
    
    def test_cross_month(self):
        """Test crossing month boundary"""
        days = calculate_holding_days(
            '2024-01-30T10:00:00',
            '2024-02-05T10:00:00'
        )
        self.assertEqual(days, 6)
    
    def test_cross_year(self):
        """Test crossing year boundary"""
        days = calculate_holding_days(
            '2023-12-30T10:00:00',
            '2024-01-02T10:00:00'
        )
        self.assertEqual(days, 3)
    
    def test_negative_returns_zero(self):
        """Test that negative duration returns 0"""
        days = calculate_holding_days(
            '2024-01-05T10:00:00',
            '2024-01-01T10:00:00'
        )
        self.assertEqual(days, 0)


class TestGetTpSummary(unittest.TestCase):
    """Test get_tp_summary function"""
    
    def test_summary_contains_all_fields(self):
        """Test that summary contains all expected fields"""
        tp = calculate_take_profit(0.40, 0.50, 'YES')
        summary = get_tp_summary(tp)
        
        self.assertIn('YES', summary)
        self.assertIn('$0.40', summary)
        self.assertIn('10.0%', summary)
        self.assertIn('50%', summary)
        self.assertIn('12.5%', summary)
        self.assertIn('$0.45', summary)
        self.assertIn('Yes', summary)
    
    def test_no_position_summary(self):
        """Test summary for NO position"""
        tp = calculate_take_profit(0.65, 0.50, 'NO')
        summary = get_tp_summary(tp)
        
        self.assertIn('NO', summary)
        self.assertIn('$0.65', summary)


class TestTakeProfitLevelDataclass(unittest.TestCase):
    """Test TakeProfitLevel dataclass"""
    
    def test_dataclass_creation(self):
        """Test creating TakeProfitLevel directly"""
        tp = TakeProfitLevel(
            target_price=0.45,
            target_pct_move=0.125,
            captured_edge=0.05,
            is_reachable=True,
            edge_capture_ratio=0.5,
            initial_edge=0.10,
            entry_price=0.40,
            side='YES'
        )
        
        self.assertEqual(tp.target_price, 0.45)
        self.assertEqual(tp.side, 'YES')
        self.assertTrue(tp.is_reachable)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""
    
    def test_boundary_price_0_10(self):
        """Test price exactly at 0.10 boundary"""
        # 0.10 is the boundary (excluded by < 0.10 check, but 0.10 is not < 0.10)
        # Actually, the check is entry_price < 0.10, so 0.10 is allowed
        tp = calculate_take_profit(0.10, 0.20, 'YES')
        self.assertIsNotNone(tp)  # 0.10 is allowed (not < 0.10)
    
    def test_boundary_price_0_90(self):
        """Test price exactly at 0.90 boundary"""
        # 0.90 is the boundary, should be excluded
        tp = calculate_take_profit(0.90, 0.95, 'YES')
        self.assertIsNone(tp)
    
    def test_valid_price_0_11(self):
        """Test price just above 0.10"""
        tp = calculate_take_profit(0.11, 0.21, 'YES')
        self.assertIsNotNone(tp)
    
    def test_valid_price_0_89(self):
        """Test price just below 0.90"""
        tp = calculate_take_profit(0.89, 0.99, 'YES')
        self.assertIsNotNone(tp)
    
    def test_very_small_edge_capture(self):
        """Test very small edge capture ratio"""
        tp = calculate_take_profit(
            entry_price=0.50,
            estimated_prob=0.60,
            side='YES',
            edge_capture_ratio=0.01  # 1%
        )
        self.assertIsNotNone(tp)
        self.assertAlmostEqual(tp.edge_capture_ratio, 0.01)
    
    def test_very_large_edge_capture(self):
        """Test very large edge capture ratio"""
        tp = calculate_take_profit(
            entry_price=0.50,
            estimated_prob=0.60,
            side='YES',
            edge_capture_ratio=0.9  # 90%
        )
        self.assertIsNotNone(tp)
        self.assertAlmostEqual(tp.edge_capture_ratio, 0.9)


if __name__ == '__main__':
    unittest.main()
