"""
Unit tests for prediction tracking system.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.prediction_tracker import PredictionTracker, PredictionRecord


class TestPredictionTracker(unittest.TestCase):
    
    def setUp(self):
        """Create temporary directory for test data"""
        self.test_dir = tempfile.mkdtemp()
        self.tracker = PredictionTracker(file_path=f"{self.test_dir}/predictions.json")
    
    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.test_dir)
    
    def test_record_prediction(self):
        """Test recording a prediction"""
        record = self.tracker.record_prediction(
            market_slug="test-market",
            question="Test question?",
            predicted_prob=0.70,
            market_price=0.55,
            side="YES",
            position_size=1000
        )
        
        self.assertEqual(record.market_slug, "test-market")
        self.assertEqual(record.predicted_prob, 0.70)
        self.assertAlmostEqual(record.edge, 0.15)
        self.assertFalse(record.resolved)
    
    def test_record_outcome_yes_wins(self):
        """Test resolving a market where YES wins"""
        self.tracker.record_prediction(
            market_slug="test-market",
            question="Test?",
            predicted_prob=0.70,
            market_price=0.55,
            side="YES",
            position_size=1000
        )
        
        resolved = self.tracker.record_outcome("test-market", 1)
        
        self.assertIsNotNone(resolved)
        self.assertTrue(resolved.resolved)
        self.assertEqual(resolved.actual_outcome, 1)
        self.assertEqual(resolved.brier_score, (0.70 - 1) ** 2)
        # P&L = (1 - 0.55) / 0.55 * 1000
        expected_pnl = (1 - 0.55) / 0.55 * 1000
        self.assertAlmostEqual(resolved.pnl, expected_pnl, places=2)
    
    def test_record_outcome_no_wins(self):
        """Test resolving a market where NO wins"""
        self.tracker.record_prediction(
            market_slug="test-market",
            question="Test?",
            predicted_prob=0.30,
            market_price=0.60,
            side="NO",
            position_size=1000
        )
        
        resolved = self.tracker.record_outcome("test-market", 0)
        
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.actual_outcome, 0)
        # P&L calculation for NO
        no_price = 1 - 0.60  # 0.40
        expected_pnl = (1 - no_price) / no_price * 1000  # NO wins, payout is 1
        self.assertAlmostEqual(resolved.pnl, expected_pnl, places=2)
    
    def test_calibration_report_insufficient_data(self):
        """Test report with no resolved predictions"""
        report = self.tracker.get_calibration_report()
        
        self.assertEqual(report['status'], 'insufficient_data')
        self.assertEqual(report['resolved'], 0)
    
    def test_calibration_report_with_data(self):
        """Test report with resolved predictions"""
        # Add and resolve multiple predictions
        for i in range(5):
            self.tracker.record_prediction(
                market_slug=f"market-{i}",
                question=f"Test {i}?",
                predicted_prob=0.60,
                market_price=0.50,
                side="YES",
                position_size=100
            )
            self.tracker.record_outcome(f"market-{i}", 1 if i < 3 else 0)
        
        report = self.tracker.get_calibration_report()
        
        self.assertEqual(report['status'], 'success')
        self.assertEqual(report['resolved'], 5)
        self.assertEqual(report['win_rate'], 0.6)  # 3 out of 5
    
    def test_kelly_recommendation(self):
        """Test Kelly fraction recommendations"""
        # Test with various Brier scores
        self.assertEqual(self.tracker._recommend_kelly([0.05]), 0.50)
        self.assertEqual(self.tracker._recommend_kelly([0.12]), 0.35)
        self.assertEqual(self.tracker._recommend_kelly([0.18]), 0.25)
        self.assertEqual(self.tracker._recommend_kelly([0.22]), 0.15)
        self.assertEqual(self.tracker._recommend_kelly([0.30]), 0.10)
    
    def test_model_performance_tracking(self):
        """Test tracking individual model performance"""
        self.tracker.record_prediction(
            market_slug="test-market",
            question="Test?",
            predicted_prob=0.70,
            market_price=0.55,
            side="YES",
            position_size=1000,
            model_predictions={'model_a': 0.65, 'model_b': 0.75}
        )
        self.tracker.record_outcome("test-market", 1)
        
        report = self.tracker.get_calibration_report()
        
        self.assertIn('model_performance', report)
        self.assertIn('model_a', report['model_performance'])
        self.assertIn('model_b', report['model_performance'])


if __name__ == '__main__':
    unittest.main()
