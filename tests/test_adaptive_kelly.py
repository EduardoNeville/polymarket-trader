"""
Unit tests for adaptive Kelly criterion.
"""

import unittest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.adaptive_kelly import AdaptiveKelly, PortfolioKelly


class TestAdaptiveKelly(unittest.TestCase):
    
    def setUp(self):
        self.kelly = AdaptiveKelly(
            base_fraction=0.25,
            max_fraction=0.50,
            min_fraction=0.05
        )
    
    def test_basic_kelly_calculation(self):
        """Test basic Kelly calculation"""
        result = self.kelly.calculate_position_size(
            bankroll=10000,
            market_price=0.50,
            estimated_prob=0.70,  # 20% edge
            confidence=0.8,
            correlated_exposure=0.0,
            current_drawdown=0.0
        )
        
        self.assertEqual(result.side, 'YES')
        self.assertGreater(result.kelly_fraction, 0)
        self.assertGreater(result.position_size, 0)
        self.assertEqual(result.confidence_adjustment, 0.9)  # 0.5 + 0.8*0.5
    
    def test_no_bet_when_negative_ev(self):
        """Test that no bet is recommended for negative EV"""
        # When market price equals estimated prob, no edge
        result = self.kelly.calculate_position_size(
            bankroll=10000,
            market_price=0.50,
            estimated_prob=0.50,  # No edge
            confidence=0.8
        )
        
        self.assertLess(result.kelly_fraction, 0.01)  # Should be near zero
        self.assertTrue(any('avoid' in r.lower() for r in result.recommendations))
    
    def test_high_confidence_increases_size(self):
        """Test that high confidence increases position size"""
        result_low = self.kelly.calculate_position_size(
            bankroll=10000,
            market_price=0.50,
            estimated_prob=0.70,
            confidence=0.3,  # Low confidence
            correlated_exposure=0.0,
            current_drawdown=0.0
        )
        
        result_high = self.kelly.calculate_position_size(
            bankroll=10000,
            market_price=0.50,
            estimated_prob=0.70,
            confidence=0.9,  # High confidence
            correlated_exposure=0.0,
            current_drawdown=0.0
        )
        
        self.assertGreater(result_high.adjusted_fraction, result_low.adjusted_fraction)
        self.assertGreater(result_high.confidence_adjustment, result_low.confidence_adjustment)
    
    def test_correlation_penalty(self):
        """Test that high correlation reduces position size"""
        result_low = self.kelly.calculate_position_size(
            bankroll=10000,
            market_price=0.50,
            estimated_prob=0.70,
            confidence=0.8,
            correlated_exposure=0.05,  # Low correlation
            current_drawdown=0.0
        )
        
        result_high = self.kelly.calculate_position_size(
            bankroll=10000,
            market_price=0.50,
            estimated_prob=0.70,
            confidence=0.8,
            correlated_exposure=0.25,  # High correlation (near 30% limit)
            current_drawdown=0.0
        )
        
        self.assertGreater(result_low.adjusted_fraction, result_high.adjusted_fraction)
        self.assertLess(result_high.correlation_penalty, result_low.correlation_penalty)
    
    def test_drawdown_penalty(self):
        """Test that drawdown reduces position size"""
        result_normal = self.kelly.calculate_position_size(
            bankroll=10000,
            market_price=0.50,
            estimated_prob=0.70,
            confidence=0.8,
            correlated_exposure=0.0,
            current_drawdown=0.02  # Small drawdown
        )
        
        result_drawdown = self.kelly.calculate_position_size(
            bankroll=10000,
            market_price=0.50,
            estimated_prob=0.70,
            confidence=0.8,
            correlated_exposure=0.0,
            current_drawdown=0.15  # 15% drawdown (high)
        )
        
        self.assertGreater(result_normal.adjusted_fraction, result_drawdown.adjusted_fraction)
        self.assertLess(result_drawdown.drawdown_penalty, 1.0)
        self.assertTrue(any('drawdown' in r.lower() for r in result_drawdown.recommendations))
    
    def test_max_drawdown_stops_trading(self):
        """Test that max drawdown prevents new positions"""
        result = self.kelly.calculate_position_size(
            bankroll=10000,
            market_price=0.50,
            estimated_prob=0.70,
            confidence=0.8,
            correlated_exposure=0.0,
            current_drawdown=0.20  # At max drawdown limit
        )
        
        self.assertEqual(result.drawdown_penalty, 0.0)
        self.assertTrue(any('stop trading' in r.lower() for r in result.recommendations))
    
    def test_small_edge_warning(self):
        """Test warning for small edge trades"""
        result = self.kelly.calculate_position_size(
            bankroll=10000,
            market_price=0.50,
            estimated_prob=0.53,  # Only 3% edge
            confidence=0.8
        )
        
        self.assertTrue(any('small edge' in r.lower() for r in result.recommendations))
    
    def test_buy_no_when_appropriate(self):
        """Test that system correctly buys NO when that's optimal"""
        result = self.kelly.calculate_position_size(
            bankroll=10000,
            market_price=0.70,  # Market thinks 70%
            estimated_prob=0.40,  # We think 40%
            confidence=0.8
        )
        
        self.assertEqual(result.side, 'NO')
        self.assertGreater(result.kelly_fraction, 0)
    
    def test_position_within_bounds(self):
        """Test that final position is within min/max bounds"""
        result = self.kelly.calculate_position_size(
            bankroll=10000,
            market_price=0.50,
            estimated_prob=0.95,  # Huge edge
            confidence=1.0,
            correlated_exposure=0.0,
            current_drawdown=0.0
        )
        
        # Should be capped at max_fraction
        self.assertLessEqual(result.adjusted_fraction, 0.50)


class TestPortfolioKelly(unittest.TestCase):
    
    def setUp(self):
        self.portfolio = PortfolioKelly(max_total_exposure=0.50)
    
    def test_add_position(self):
        """Test adding positions to portfolio"""
        self.portfolio.add_position('market-1', 'YES', 0.10, 0.15, 0.05, 'politics')
        
        self.assertIn('market-1', self.portfolio.positions)
        self.assertEqual(self.portfolio.positions['market-1']['size'], 0.10)
    
    def test_correlated_exposure(self):
        """Test calculating exposure by category"""
        self.portfolio.add_position('market-1', 'YES', 0.10, 0.15, 0.05, 'politics')
        self.portfolio.add_position('market-2', 'NO', 0.05, 0.10, 0.03, 'politics')
        self.portfolio.add_position('market-3', 'YES', 0.08, 0.12, 0.04, 'sports')
        
        politics_exp = self.portfolio.get_correlated_exposure('politics')
        sports_exp = self.portfolio.get_correlated_exposure('sports')
        
        self.assertAlmostEqual(politics_exp, 0.15)  # 10% + 5%
        self.assertAlmostEqual(sports_exp, 0.08)
    
    def test_can_add_position_within_limits(self):
        """Test that positions within limits are allowed"""
        self.portfolio.add_position('market-1', 'YES', 0.10, 0.15, 0.05, 'politics')
        
        can_add, reason = self.portfolio.can_add_position(0.15, 'sports')
        
        self.assertTrue(can_add)
        self.assertEqual(reason, 'OK')
    
    def test_can_add_position_exceeds_category(self):
        """Test rejection when category limit would be exceeded"""
        self.portfolio.add_position('market-1', 'YES', 0.20, 0.15, 0.05, 'politics')
        
        can_add, reason = self.portfolio.can_add_position(0.15, 'politics')
        
        self.assertFalse(can_add)
        self.assertIn('politics', reason.lower())
    
    def test_can_add_position_exceeds_total(self):
        """Test rejection when total exposure would be exceeded"""
        self.portfolio.add_position('market-1', 'YES', 0.25, 0.15, 0.05, 'politics')
        self.portfolio.add_position('market-2', 'YES', 0.20, 0.15, 0.05, 'sports')
        
        can_add, reason = self.portfolio.can_add_position(0.10, 'crypto')
        
        self.assertFalse(can_add)
        self.assertIn('total exposure', reason.lower())
    
    def test_optimize_allocation(self):
        """Test portfolio optimization"""
        opportunities = [
            {'market_slug': 'm1', 'expected_return': 0.20, 'variance': 0.05, 'category': 'politics', 'kelly_fraction': 0.15},
            {'market_slug': 'm2', 'expected_return': 0.15, 'variance': 0.03, 'category': 'sports', 'kelly_fraction': 0.10},
            {'market_slug': 'm3', 'expected_return': 0.10, 'variance': 0.10, 'category': 'politics', 'kelly_fraction': 0.08},
        ]
        
        allocated = self.portfolio.optimize_allocation(10000, opportunities)
        
        # Should allocate to at least some opportunities
        self.assertGreater(len(allocated), 0)
        
        # Should have calculated Sharpe ratios
        for opp in allocated:
            self.assertIn('sharpe', opp)
            self.assertIn('allocated_size', opp)


if __name__ == '__main__':
    unittest.main()
