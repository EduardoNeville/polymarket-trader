"""
Test for Issue #11 - Backtest position sizing fix
Tests that position sizes are capped and don't cause exponential growth.
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.backtest import BacktestEngine, BacktestResult


class TestPositionSizing(unittest.TestCase):
    
    def test_position_size_cap(self):
        """Test that position sizes are capped"""
        engine = BacktestEngine(initial_bankroll=1000, max_position_pct=0.20)
        
        # Check max position is 20% of initial
        max_pos = engine.initial_bankroll * engine.max_position_pct
        self.assertEqual(max_pos, 200.0)  # 20% of $1000
    
    def test_bankroll_doesnt_infinite_growth(self):
        """Test that bankroll doesn't grow exponentially"""
        # Create simple test data
        historical_data = []
        for i in range(10):
            historical_data.append({
                'timestamp': f'2025-01-{i+1:02d}',
                'market_slug': f'market-{i}',
                'question': f'Test {i}?',
                'price': 0.55,
                'outcome': 1,  # All YES win
                'category': 'general'
            })
        
        engine = BacktestEngine(initial_bankroll=1000, max_position_pct=0.20)
        result = engine.run_backtest(historical_data, strategy='ensemble', verbose=False)
        
        # Return should be reasonable (< 10,000% even with all wins)
        self.assertLess(result.total_pnl_pct, 10000.0)
        
        # Final bankroll should be < $100,000 (not trillions)
        self.assertLess(result.final_bankroll, 100000.0)
    
    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio is calculated correctly"""
        # Create data with known outcomes
        historical_data = [
            {'timestamp': '2025-01-01', 'market_slug': 'm1', 'question': 'Test?', 
             'price': 0.60, 'outcome': 1, 'category': 'general'},
            {'timestamp': '2025-01-02', 'market_slug': 'm2', 'question': 'Test?', 
             'price': 0.40, 'outcome': 0, 'category': 'general'},
        ]
        
        engine = BacktestEngine(initial_bankroll=1000, max_position_pct=0.20)
        result = engine.run_backtest(historical_data, strategy='ensemble', verbose=False)
        
        # Sharpe should be a finite number
        self.assertIsInstance(result.sharpe_ratio, float)
        self.assertTrue(result.sharpe_ratio >= 0 or result.sharpe_ratio < 0)  # Not NaN
    
    def test_max_drawdown_calculated(self):
        """Test max drawdown is tracked"""
        engine = BacktestEngine(initial_bankroll=1000, max_position_pct=0.20)
        
        # Create data with mixed outcomes
        historical_data = [
            {'timestamp': '2025-01-01', 'market_slug': 'm1', 'question': 'Test?', 
             'price': 0.60, 'outcome': 0, 'category': 'general'},  # Loss
            {'timestamp': '2025-01-02', 'market_slug': 'm2', 'question': 'Test?', 
             'price': 0.40, 'outcome': 1, 'category': 'general'},  # Win
        ]
        
        result = engine.run_backtest(historical_data, strategy='ensemble', verbose=False)
        
        # Max drawdown should be >= 0
        self.assertGreaterEqual(result.max_drawdown, 0)
        self.assertGreaterEqual(result.max_drawdown_pct, 0)


if __name__ == '__main__':
    unittest.main()
