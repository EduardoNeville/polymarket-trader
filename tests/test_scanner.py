"""
Unit tests for scanner - Issue #9 fix
Tests the updated API structure.
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner import PolymarketScanner, Market


class TestScanner(unittest.TestCase):
    
    def setUp(self):
        self.scanner = PolymarketScanner()
    
    @patch('scanner.requests.Session.get')
    def test_get_active_markets_success(self, mock_get):
        """Test fetching markets with new API structure"""
        # Mock the API response with new structure
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'id': 'event-1',
                'title': 'Test Event',
                'category': 'politics',
                'markets': [
                    {
                        'conditionId': 'market-1',
                        'question': 'Will it rain?',
                        'slug': 'rain-market',
                        'outcomePrices': '["0.65", "0.35"]',
                        'volume': '100000',
                        'liquidity': '50000',
                        'endDate': '2025-12-31T23:59:59Z',
                        'description': 'Test market',
                        'resolutionSource': 'source'
                    }
                ]
            }
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        markets = self.scanner.get_active_markets(limit=10)
        
        self.assertEqual(len(markets), 1)
        self.assertEqual(markets[0].question, 'Will it rain?')
        self.assertEqual(markets[0].yes_price, 0.65)
        self.assertEqual(markets[0].no_price, 0.35)
    
    @patch('scanner.requests.Session.get')
    def test_parse_market_with_none_prices(self, mock_get):
        """Test handling None prices gracefully"""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'markets': [
                    {
                        'outcomePrices': None,  # Missing prices
                    }
                ]
            }
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        markets = self.scanner.get_active_markets(limit=10)
        
        # Should skip markets with no prices
        self.assertEqual(len(markets), 0)
    
    @patch('scanner.requests.Session.get')
    def test_parse_market_with_empty_prices(self, mock_get):
        """Test handling empty price arrays"""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'markets': [
                    {
                        'conditionId': 'market-1',
                        'question': 'Test?',
                        'outcomePrices': '["0", "0"]',
                        'volume': '0',
                        'liquidity': '0',
                    }
                ]
            }
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        markets = self.scanner.get_active_markets(limit=10)
        
        # Should skip markets with zero prices
        self.assertEqual(len(markets), 0)
    
    @patch('scanner.requests.Session.get')
    def test_find_arbitrage_opportunities(self, mock_get):
        """Test arbitrage detection"""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'markets': [
                    {
                        'conditionId': 'market-1',
                        'question': 'Arbitrage test?',
                        'slug': 'arb-market',
                        'outcomePrices': '["0.48", "0.48"]',  # Sum = 0.96 < 1.0
                        'volume': '100000',
                        'liquidity': '50000',
                        'endDate': '2025-12-31T23:59:59Z',
                        'description': 'Test',
                        'resolutionSource': ''
                    }
                ]
            }
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        opps = self.scanner.find_arbitrage_opportunities()
        
        self.assertEqual(len(opps), 1)
        self.assertAlmostEqual(opps[0]['spread'], 0.04, places=5)  # 1.0 - 0.96
    
    @patch('scanner.requests.Session.get')
    def test_api_error_handling(self, mock_get):
        """Test graceful handling of API errors"""
        mock_get.side_effect = Exception("Network error")
        
        markets = self.scanner.get_active_markets(limit=10)
        
        # Should return empty list on error
        self.assertEqual(len(markets), 0)


if __name__ == '__main__':
    unittest.main()
