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
        for price in [0.45, 0.46, 0.47, 0.48, 0.49]:
            self.estimator.update_price('test-market', price)
        
        estimate = self.estimator.estimate_probability(
            market_slug='test-market',
            market_question='Test question?',
            current_price=0.50,
            category='general'
        )
        
        self.assertIsInstance(estimate, EdgeEstimate)
        self.assertEqual(estimate.market_slug, 'test-market')
        self.assertEqual(estimate.current_price, 0.50)
        self.assertGreaterEqual(estimate.ensemble_probability, 0.05)
        self.assertLessEqual(estimate.ensemble_probability, 0.95)
    
    def test_upward_trend_positive_edge(self):
        """Test that upward trend predicts positive edge for YES"""
        # Strong upward trend
        for price in [0.40, 0.42, 0.44, 0.46, 0.48, 0.50, 0.52]:
            self.estimator.update_price('up-market', price)
        
        estimate = self.estimator.estimate_probability(
            'up-market', 'Test?', 0.52, 'general'
        )
        
        # Momentum models should push prediction higher
        self.assertGreater(estimate.ensemble_probability, 0.50)
    
    def test_model_weights_sum_to_one(self):
        """Test that model weights sum to approximately 1"""
        weights = self.estimator.get_model_weights()
        total = sum(weights.values())
        self.assertAlmostEqual(total, 1.0, places=2)
    
    def test_fundamental_category_prediction(self):
        """Test fundamental predictions by category"""
        # Politics should be around 50%
        self.estimator.update_price('pol-market', 0.50)
        pol_estimate = self.estimator.estimate_probability(
            'pol-market', 'Political question?', 0.50, 'politics'
        )
        
        # Sports favorite should be higher
        self.estimator.update_price('sports-market', 0.50)
        sports_estimate = self.estimator.estimate_probability(
            'sports-market', 'Sports question?', 0.50, 'sports_favorite'
        )
        
        # The fundamental component should differ
        pol_fund = pol_estimate.individual_predictions.get('fundamental', 0.5)
        sports_fund = sports_estimate.individual_predictions.get('fundamental', 0.5)
        
        # Sports should have higher base rate
        self.assertGreater(sports_fund, pol_fund)
    
    def test_recommendation_format(self):
        """Test that recommendation is properly formatted"""
        for price in [0.45, 0.46, 0.47]:
            self.estimator.update_price('rec-market', price)
        
        estimate = self.estimator.estimate_probability(
            'rec-market', 'Test?', 0.47, 'general'
        )
        
        self.assertIsInstance(estimate.recommendation, str)
        self.assertGreater(len(estimate.recommendation), 0)
    
    def test_confidence_calculation(self):
        """Test confidence is between 0 and 1"""
        for price in [0.50, 0.51, 0.52, 0.53, 0.54]:
            self.estimator.update_price('conf-market', price)
        
        estimate = self.estimator.estimate_probability(
            'conf-market', 'Test?', 0.54, 'general'
        )
        
        self.assertGreaterEqual(estimate.confidence, 0)
        self.assertLessEqual(estimate.confidence, 1)
    
    def test_expected_return_calculation(self):
        """Test expected return calculation"""
        for price in [0.45, 0.46, 0.47]:
            self.estimator.update_price('ret-market', price)
        
        estimate = self.estimator.estimate_probability(
            'ret-market', 'Test?', 0.47, 'general'
        )
        
        # Expected return should be a float
        self.assertIsInstance(estimate.expected_return, float)
    
    def test_sharpe_calculation(self):
        """Test Sharpe ratio calculation"""
        for price in [0.50, 0.51]:
            self.estimator.update_price('sharpe-market', price)
        
        estimate = self.estimator.estimate_probability(
            'sharpe-market', 'Test?', 0.51, 'general'
        )
        
        self.assertIsInstance(estimate.sharpe_ratio, float)
    
    def test_individual_predictions_present(self):
        """Test that individual model predictions are included"""
        self.estimator.update_price('ind-market', 0.50)
        
        estimate = self.estimator.estimate_probability(
            'ind-market', 'Test?', 0.50, 'general'
        )
        
        self.assertIn('individual_predictions', estimate.__dict__)
        self.assertGreater(len(estimate.individual_predictions), 0)
    
    def test_model_confidences_present(self):
        """Test that model confidences are tracked"""
        self.estimator.update_price('conf-market', 0.50)
        
        estimate = self.estimator.estimate_probability(
            'conf-market', 'Test?', 0.50, 'general'
        )
        
        self.assertIn('model_confidences', estimate.__dict__)
        self.assertGreater(len(estimate.model_confidences), 0)
    
    def test_edge_clipping(self):
        """Test that ensemble probability is clipped to valid range"""
        # Feed extreme values
        for _ in range(10):
            self.estimator.update_price('extreme-market', 0.99)
        
        estimate = self.estimator.estimate_probability(
            'extreme-market', 'Test?', 0.99, 'general'
        )
        
        self.assertLessEqual(estimate.ensemble_probability, 0.95)
        self.assertGreaterEqual(estimate.ensemble_probability, 0.05)


if __name__ == '__main__':
    unittest.main()
