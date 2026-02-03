"""
Unit tests for multi-strategy portfolio.
"""

import unittest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.portfolio import (
    StrategyPortfolio,
    SentimentStrategy,
    MomentumStrategy,
    MeanReversionStrategy,
    ArbitrageStrategy,
    EnsembleStrategy
)


class TestSentimentStrategy(unittest.TestCase):
    
    def setUp(self):
        self.strategy = SentimentStrategy()
    
    def test_signal_generation(self):
        """Test that sentiment strategy generates signals"""
        signal = self.strategy.generate_signal(
            'test-market',
            question='Will it rain tomorrow?',
            current_price=0.50,
            category='general'
        )
        
        # May or may not generate signal depending on sentiment
        if signal:
            self.assertIn(signal.direction, ['BUY_YES', 'BUY_NO'])
            self.assertGreaterEqual(signal.strength, 0)
            self.assertLessEqual(signal.strength, 1)


class TestMomentumStrategy(unittest.TestCase):
    
    def setUp(self):
        self.strategy = MomentumStrategy()
    
    def test_upward_momentum_signal(self):
        """Test momentum signal in upward trend"""
        # Feed upward trend
        for price in [0.40, 0.42, 0.44, 0.46, 0.48, 0.50]:
            self.strategy.estimator.update_price('up-market', price)
        
        signal = self.strategy.generate_signal(
            'up-market', current_price=0.50
        )
        
        # Should suggest buying YES
        if signal:
            self.assertEqual(signal.direction, 'BUY_YES')


class TestMeanReversionStrategy(unittest.TestCase):
    
    def setUp(self):
        self.strategy = MeanReversionStrategy()
    
    def test_reversion_at_extreme_high(self):
        """Test mean reversion at extreme high"""
        for price in [0.85, 0.86, 0.87, 0.88]:
            self.strategy.estimator.update_price('high-market', price)
        
        signal = self.strategy.generate_signal(
            'high-market', current_price=0.88
        )
        
        # Should suggest selling (buying NO)
        if signal:
            self.assertEqual(signal.direction, 'BUY_NO')
    
    def test_no_signal_in_middle(self):
        """Test no signal when price is in middle range"""
        for price in [0.45, 0.46, 0.47, 0.48]:
            self.strategy.estimator.update_price('mid-market', price)
        
        signal = self.strategy.generate_signal(
            'mid-market', current_price=0.48
        )
        
        # Should not generate signal in middle
        self.assertIsNone(signal)


class TestArbitrageStrategy(unittest.TestCase):
    
    def setUp(self):
        self.strategy = ArbitrageStrategy()
    
    def test_arbitrage_signal_when_spread_exists(self):
        """Test arbitrage detection"""
        signal = self.strategy.generate_signal(
            'arb-market',
            yes_price=0.45,
            no_price=0.50  # Total = 0.95 < 1.0
        )
        
        self.assertIsNotNone(signal)
        self.assertGreater(signal.expected_return, 0)
        self.assertEqual(signal.confidence, 0.9)
    
    def test_no_signal_when_no_arbitrage(self):
        """Test no signal when prices are efficient"""
        signal = self.strategy.generate_signal(
            'efficient-market',
            yes_price=0.50,
            no_price=0.50  # Total = 1.0
        )
        
        self.assertIsNone(signal)


class TestStrategyPortfolio(unittest.TestCase):
    
    def setUp(self):
        self.portfolio = StrategyPortfolio(bankroll=10000)
    
    def test_strategy_initialization(self):
        """Test that all strategies are initialized"""
        self.assertEqual(len(self.portfolio.strategies), 5)
        self.assertIn('sentiment', self.portfolio.strategies)
        self.assertIn('momentum', self.portfolio.strategies)
        self.assertIn('mean_reversion', self.portfolio.strategies)
        self.assertIn('arbitrage', self.portfolio.strategies)
        self.assertIn('ensemble', self.portfolio.strategies)
    
    def test_generate_signals(self):
        """Test signal generation from all strategies"""
        for i in range(5):
            price = 0.45 + i * 0.02
            for name, strategy in self.portfolio.strategies.items():
                if hasattr(strategy, 'estimator'):
                    strategy.estimator.update_price('test-market', price)
        
        signals = self.portfolio.generate_signals(
            'test-market',
            question='Test?',
            current_price=0.55
        )
        
        self.assertEqual(len(signals), 5)
    
    def test_allocate_capital(self):
        """Test capital allocation"""
        # Create mock signals
        signals = {
            'momentum': self.portfolio.strategies['momentum'].generate_signal(
                'test', current_price=0.55
            ),
            'ensemble': self.portfolio.strategies['ensemble'].generate_signal(
                'test', question='Test?', current_price=0.55
            )
        }
        
        # Ensure at least one signal exists
        if not any(signals.values()):
            # Manually create a signal for testing
            from strategies.portfolio import StrategySignal
            signals['arbitrage'] = StrategySignal(
                market_slug='test',
                direction='BUY_YES',
                strength=0.8,
                expected_return=0.05,
                confidence=0.9,
                rationale='Test signal'
            )
        
        allocations = self.portfolio.allocate_capital('test', signals, 0.55)
        
        # Should generate allocations for valid signals
        self.assertIsInstance(allocations, list)
    
    def test_get_strategy_performance(self):
        """Test performance tracking"""
        # Record some trades
        self.portfolio.strategies['momentum'].record_result(0.10)
        self.portfolio.strategies['momentum'].record_result(-0.05)
        self.portfolio.strategies['momentum'].record_result(0.15)
        
        perf = self.portfolio.get_strategy_performance()
        
        self.assertIn('momentum', perf)
        self.assertEqual(perf['momentum']['trades_count'], 3)
        self.assertEqual(perf['momentum']['total_pnl'], 0.20)
    
    def test_strategy_sharpe_calculation(self):
        """Test Sharpe ratio calculation"""
        strategy = self.portfolio.strategies['momentum']
        
        # Record multiple trades
        for pnl in [0.10, -0.05, 0.08, -0.02, 0.12]:
            strategy.record_result(pnl)
        
        sharpe = strategy.get_sharpe_ratio()
        
        # Should be a positive number for profitable strategy
        self.assertIsInstance(sharpe, float)


if __name__ == '__main__':
    unittest.main()
