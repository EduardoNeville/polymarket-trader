"""
Unit tests for ensemble edge estimator.
"""

import unittest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.edge_estimator import EnsembleEdgeEstimator, EdgeEstimate


class TestEnsembleEdgeEstimator(unittest.TestCase):
    
    def setUp(self):
        self.estimator = EnsembleEdgeEstimator()
    
    def test_basic_estimate(self):
        """Test basic probability estimation"""
        # Feed some price history
        market = "test-market"
        for price in [0.45, 0.46, 0.47, 0.48, 0.49, 0.50]:
            self.estimator.update_price(market, price)
        
        estimate = self.estimator.estimate_probability(
            market_slug=market,
            market_question="Test question?",
            current_price=0.50,
            category="general"
        )
        
        self.assertIsInstance(estimate, EdgeEstimate)
        self.assertEqual(estimate.market_slug, market)
        self.assertGreaterEqual(estimate.ensemble_probability, 0.05)
        self.assertLessEqual(estimate.ensemble_probability, 0.95)
    
    def test_upward_trend_estimate(self):
        """Test that upward trend produces higher prediction"""
        market = "up-trend"
        for price in [0.40, 0.42, 0.44, 0.46, 0.48, 0.50, 0.52, 0.54]:
            self.estimator.update_price(market, price)
        
        estimate = self.estimator.estimate_probability(
            market_slug=market,
            market_question="Upward trend?",
            current_price=0.54,
            category="general"
        )
        
        # Should predict higher than current due to momentum
        self.assertGreater(estimate.ensemble_probability, 0.50)
    
    def test_edge_calculation(self):
        """Test edge calculation"""
        market = "edge-test"
        for price in [0.45, 0.46, 0.47]:
            self.estimator.update_price(market, price)
        
        estimate = self.estimator.estimate_probability(
            market_slug=market,
            market_question="Edge test?",
            current_price=0.47,
            category="general"
        )
        
        expected_edge = estimate.ensemble_probability - 0.47
        self.assertAlmostEqual(estimate.edge, expected_edge, places=5)
    
    def test_confidence_range(self):
        """Test that confidence is in valid range"""
        market = "conf-test"
        for price in [0.50, 0.51, 0.52]:
            self.estimator.update_price(market, price)
        
        estimate = self.estimator.estimate_probability(
            market_slug=market,
            market_question="Confidence test?",
            current_price=0.52,
            category="general"
        )
        
        self.assertGreaterEqual(estimate.confidence, 0.0)
        self.assertLessEqual(estimate.confidence, 1.0)
    
    def test_individual_predictions_exist(self):
        """Test that individual model predictions are included"""
        market = "individual-test"
        for price in [0.50, 0.51]:
            self.estimator.update_price(market, price)
        
        estimate = self.estimator.estimate_probability(
            market_slug=market,
            market_question="Individual test?",
            current_price=0.51,
            category="general"
        )
        
        self.assertIn('individual_predictions', estimate.__dict__)
        self.assertGreater(len(estimate.individual_predictions), 0)
        
        # Check specific models
        self.assertIn('simple_price', estimate.individual_predictions)
        self.assertIn('momentum', estimate.individual_predictions)
        self.assertIn('mean_reversion', estimate.individual_predictions)
        self.assertIn('fundamental', estimate.individual_predictions)
    
    def test_model_weights_sum_to_one(self):
        """Test that model weights sum to approximately 1"""
        weights = self.estimator.get_model_weights()
        total = sum(weights.values())
        self.assertAlmostEqual(total, 1.0, places=2)
    
    def test_weights_updated(self):
        """Test that weights are initialized"""
        weights = self.estimator.get_model_weights()
        
        # Should have weights for all models
        self.assertIn('simple_price', weights)
        self.assertIn('momentum', weights)
        self.assertIn('mean_reversion', weights)
        
        # All weights should be positive
        for w in weights.values():
            self.assertGreater(w, 0)
    
    def test_fundamental_by_category(self):
        """Test fundamental predictions by category"""
        market = "fundamental-test"
        
        # Politics should be around 0.50
        est_politics = self.estimator.estimate_probability(
            market_slug=market,
            market_question="Politics?",
            current_price=0.50,
            category="politics"
        )
        
        # The fundamental model prediction should be ~0.50
        self.assertAlmostEqual(
            est_politics.individual_predictions['fundamental'],
            0.50,
            places=2
        )
    
    def test_recommendation_generation(self):
        """Test that recommendations are generated"""
        market = "rec-test"
        for price in [0.50, 0.51]:
            self.estimator.update_price(market, price)
        
        # Test with small edge
        estimate_small = self.estimator.estimate_probability(
            market_slug=market,
            market_question="Small edge?",
            current_price=0.505,  # Very close to estimate
            category="general"
        )
        self.assertIn("PASS", estimate_small.recommendation)
        
        # Test with large edge
        estimate_large = self.estimator.estimate_probability(
            market_slug=market,
            market_question="Large edge?",
            current_price=0.30,  # Far from estimate
            category="general"
        )
        self.assertTrue(
            "BUY" in estimate_large.recommendation or
            "CAUTION" in estimate_large.recommendation
        )
    
    def test_expected_return_calculation(self):
        """Test expected return calculation"""
        market = "return-test"
        for price in [0.50, 0.55, 0.60]:
            self.estimator.update_price(market, price)
        
        estimate = self.estimator.estimate_probability(
            market_slug=market,
            market_question="Return test?",
            current_price=0.60,
            category="general"
        )
        
        # Expected return should be a number
        self.assertIsInstance(estimate.expected_return, float)
    
    def test_sharpe_calculation(self):
        """Test Sharpe ratio estimation"""
        market = "sharpe-test"
        for price in [0.50, 0.51]:
            self.estimator.update_price(market, price)
        
        estimate = self.estimator.estimate_probability(
            market_slug=market,
            market_question="Sharpe test?",
            current_price=0.51,
            category="general"
        )
        
        # Sharpe should be a number
        self.assertIsInstance(estimate.sharpe_ratio, float)
    
    def test_probability_clipping(self):
        """Test that probabilities are clipped to valid range"""
        market = "clip-test"
        
        # Even with extreme inputs, output should be in [0.05, 0.95]
        estimate = self.estimator.estimate_probability(
            market_slug=market,
            market_question="Clip test?",
            current_price=0.99,
            category="general"
        )
        
        self.assertGreaterEqual(estimate.ensemble_probability, 0.05)
        self.assertLessEqual(estimate.ensemble_probability, 0.95)


if __name__ == '__main__':
    unittest.main()
