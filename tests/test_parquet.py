"""
Test Parquet data operations
"""

import unittest
import sys
import tempfile
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

class TestParquetOperations(unittest.TestCase):
    
    def test_parquet_file_created(self):
        """Test that Parquet files were created"""
        data_dir = Path('data')
        parquet_files = list(data_dir.glob('*.parquet'))
        self.assertGreater(len(parquet_files), 0, "No Parquet files found")
    
    def test_read_parquet(self):
        """Test reading Parquet files"""
        data_dir = Path('data')
        parquet_file = data_dir / 'predictions.parquet'
        
        if parquet_file.exists():
            df = pd.read_parquet(parquet_file)
            self.assertIsInstance(df, pd.DataFrame)
            self.assertGreater(len(df), 0)
    
    def test_live_data_parquet(self):
        """Test live data collection created Parquet"""
        live_dir = Path('data/live_markets')
        if live_dir.exists():
            parquet_files = list(live_dir.glob('*.parquet'))
            if parquet_files:
                df = pd.read_parquet(parquet_files[0])
                self.assertIn('timestamp', df.columns)
                self.assertIn('market_slug', df.columns)
                self.assertIn('yes_price', df.columns)


if __name__ == '__main__':
    unittest.main()
