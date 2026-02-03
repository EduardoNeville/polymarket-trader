"""
Test Parquet backtest functionality
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.backtest import BacktestEngine


class TestParquetBacktest(unittest.TestCase):
    
    def test_load_from_parquet(self):
        """Test loading data from Parquet file"""
        parquet_file = 'data/resolved_markets.parquet'
        
        data = BacktestEngine.load_from_parquet(parquet_file)
        
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        
        # Check required fields
        if data:
            self.assertIn('market_slug', data[0])
            self.assertIn('price', data[0])
    
    def test_backtest_with_parquet_data(self):
        """Test running backtest with Parquet-loaded data"""
        data = BacktestEngine.load_from_parquet('data/resolved_markets.parquet')
        
        # Sample first 100 records for speed
        sample_data = data[:100]
        
        engine = BacktestEngine(initial_bankroll=1000, max_position_pct=0.20)
        result = engine.run_backtest(sample_data, strategy='ensemble', verbose=False)
        
        # Should complete without errors
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.total_trades)
    
    def test_load_from_directory(self):
        """Test loading all Parquet files from directory"""
        directory = 'data/live_markets'
        
        # Skip if directory doesn't exist
        if not Path(directory).exists():
            self.skipTest('Live markets directory not found')
        
        data = BacktestEngine.load_from_parquet_directory(directory)
        
        self.assertIsInstance(data, list)


if __name__ == '__main__':
    unittest.main()
