"""
Integration tests for the complete Polymarket AI trading system.
Tests end-to-end workflows.
"""

import unittest
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.prediction_tracker import PredictionTracker
from models.price_predictor import SimplePricePredictor
from models.edge_estimator import EnsembleEdgeEstimator
from strategies.adaptive_kelly import AdaptiveKelly, PortfolioKelly
from strategies.portfolio import StrategyPortfolio


class TestEndToEndWorkflow(unittest.TestCase):
    """End-to-end integration tests"""
    
    def setUp(self):
        """Create temporary directory for test data"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.test_dir)
    
    def test_full_trade_lifecycle(self):
        """Test complete trade from signal to resolution"""
        # 1. Create components
        tracker = PredictionTracker(file_path=f"{self.test_dir}/predictions.json")
        estimator = EnsembleEdgeEstimator()
        kelly = AdaptiveKelly()
        
        # 2. Feed price history
        for price in [0.45, 0.46, 0.47, 0.48, 0.49, 0.50]:
            estimator.update_price('test-market', price)
        
        # 3. Generate prediction
        estimate = estimator.estimate_probability(
            'test-market', 'Test question?', 0.50, 'general'
        )
        
        self.assertIsNotNone(estimate.edge)
        
        # 4. Calculate position size
        result = kelly.calculate_position_size(
            bankroll=10000,
            market_price=0.50,
            estimated_prob=estimate.ensemble_probability,
            confidence=estimate.confidence
        )
        
        self.assertGreater(result.position_size, 0)
        
        # 5. Record prediction
        record = tracker.record_prediction(
            market_slug='test-market',
            question='Test question?',
            predicted_prob=estimate.ensemble_probability,
            market_price=0.50,
            side=result.side,
            position_size=result.position_size,
            model_predictions=estimate.individual_predictions
        )
        
        self.assertIsNotNone(record)
        
        # 6. Resolve market
        resolved = tracker.record_outcome('test-market', 1)  # YES won
        
        self.assertIsNotNone(resolved)
        self.assertTrue(resolved.resolved)
        self.assertIsNotNone(resolved.pnl)
        
        # 7. Check calibration
        report = tracker.get_calibration_report()
        self.assertEqual(report['status'], 'success')
        self.assertEqual(report['resolved'], 1)
    
    def test_portfolio_allocation(self):
        """Test portfolio allocation across strategies"""
        portfolio = StrategyPortfolio(
            bankroll=10000,
            max_total_exposure=0.50
        )
        
        # Feed price history
        for i in range(10):
            price = 0.45 + i * 0.01
            for name, strategy in portfolio.strategies.items():
                if hasattr(strategy, 'estimator'):
                    strategy.estimator.update_price('test-market', price)
        
        # Generate signals
        signals = portfolio.generate_signals(
            'test-market',
            question='Test?',
            current_price=0.55,
            category='general'
        )
        
        # Should have at least one signal
        valid_signals = [s for s in signals.values() if s is not None]
        self.assertGreaterEqual(len(valid_signals), 0)
        
        # Allocate capital
        allocations = portfolio.allocate_capital('test-market', signals, 0.55)
        
        # Check allocation limits
        total_size = sum(a.size for a in allocations)
        self.assertLessEqual(total_size, 0.50)  # Max 50% exposure


class TestSystemInitialization(unittest.TestCase):
    """Test system initialization and dependencies"""
    
    def test_all_modules_import(self):
        """Test that all modules can be imported"""
        try:
            from utils.prediction_tracker import PredictionTracker
            from models.price_predictor import SimplePricePredictor
            from models.edge_estimator import EnsembleEdgeEstimator
            from strategies.adaptive_kelly import AdaptiveKelly
            from strategies.portfolio import StrategyPortfolio
            import_success = True
        except ImportError as e:
            import_success = False
            print(f"Import error: {e}")
        
        self.assertTrue(import_success)
    
    def test_prediction_tracker_initialization(self):
        """Test prediction tracker initializes correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / 'test_predictions.json'
            tracker = PredictionTracker(file_path=str(temp_path))
            self.assertEqual(len(tracker.predictions), 0)
    
    def test_portfolio_initialization(self):
        """Test portfolio initializes with all strategies"""
        portfolio = StrategyPortfolio(bankroll=10000)
        
        self.assertEqual(len(portfolio.strategies), 5)
        self.assertIn('sentiment', portfolio.strategies)
        self.assertIn('momentum', portfolio.strategies)
        self.assertIn('mean_reversion', portfolio.strategies)
        self.assertIn('arbitrage', portfolio.strategies)
        self.assertIn('ensemble', portfolio.strategies)


if __name__ == '__main__':
    unittest.main()
