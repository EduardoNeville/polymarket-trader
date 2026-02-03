"""
Unit tests for backtesting framework.
"""

import unittest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.backtest import BacktestEngine, Trade, BacktestResult


class TestBacktestEngine(unittest.TestCase):
    
    def setUp(self):
        self.engine = BacktestEngine(initial_bankroll=10000)
        
        # Generate synthetic test data
        self.historical_data = []
        import random
        random.seed(42)
        
        for i in range(10):
            base_price = 0.50
            prices = [base_price]
            for _ in range(5):
                prices.append(max(0.05, min(0.95, prices[-1] + random.gauss(0, 0.03))))
            
            for j, price in enumerate(prices):
                self.historical_data.append({
                    'timestamp': f'2024-01-{i+1:02d}T{j:02d}:00:00',
                    'market_slug': f'market-{i}',
                    'question': f'Test market {i}?',
                    'price': price,
                    'outcome': 1 if prices[-1] > 0.5 else 0,
                    'category': 'general'
                })
    
    def test_initialization(self):
        """Test engine initialization"""
        self.assertEqual(self.engine.initial_bankroll, 10000)
        self.assertEqual(self.engine.current_bankroll, 10000)
        self.assertEqual(len(self.engine.trades), 0)
    
    def test_run_backtest(self):
        """Test running a backtest"""
        result = self.engine.run_backtest(self.historical_data, verbose=False)
        
        self.assertIsInstance(result, BacktestResult)
        self.assertEqual(result.initial_bankroll, 10000)
        # Should have some trades
        self.assertIsInstance(result.total_trades, int)
    
    def test_backtest_result_structure(self):
        """Test that result has all required fields"""
        result = self.engine.run_backtest(self.historical_data, verbose=False)
        
        required_fields = [
            'strategy_name', 'start_date', 'end_date',
            'initial_bankroll', 'final_bankroll',
            'total_trades', 'winning_trades', 'losing_trades',
            'win_rate', 'total_pnl', 'total_pnl_pct',
            'avg_trade_pnl', 'max_drawdown', 'max_drawdown_pct',
            'sharpe_ratio', 'sortino_ratio', 'trades', 'equity_curve'
        ]
        
        for field in required_fields:
            self.assertTrue(hasattr(result, field), f"Missing field: {field}")
    
    def test_win_rate_calculation(self):
        """Test win rate calculation"""
        result = self.engine.run_backtest(self.historical_data, verbose=False)
        
        if result.total_trades > 0:
            expected_win_rate = result.winning_trades / result.total_trades
            self.assertAlmostEqual(result.win_rate, expected_win_rate, places=4)
    
    def test_total_pnl_calculation(self):
        """Test total P&L calculation"""
        result = self.engine.run_backtest(self.historical_data, verbose=False)
        
        expected_pnl = result.final_bankroll - result.initial_bankroll
        self.assertAlmostEqual(result.total_pnl, expected_pnl, places=2)
    
    def test_compare_strategies(self):
        """Test strategy comparison"""
        strategies = ['ensemble', 'momentum', 'mean_reversion']
        
        results = self.engine.compare_strategies(
            self.historical_data,
            strategies,
            min_edge=0.05
        )
        
        self.assertEqual(len(results), len(strategies))
        
        for strategy in strategies:
            self.assertIn(strategy, results)
            self.assertIsInstance(results[strategy], BacktestResult)


class TestTrade(unittest.TestCase):
    
    def test_trade_creation(self):
        """Test creating a trade"""
        trade = Trade(
            timestamp='2024-01-01T00:00:00',
            market_slug='test-market',
            side='YES',
            entry_price=0.55,
            position_size=1000,
            estimated_prob=0.70
        )
        
        self.assertEqual(trade.market_slug, 'test-market')
        self.assertEqual(trade.side, 'YES')
        self.assertEqual(trade.entry_price, 0.55)


if __name__ == '__main__':
    unittest.main()
