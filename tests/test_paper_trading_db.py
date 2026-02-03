"""
Tests for paper trading database
"""

import unittest
import sys
from pathlib import Path
from datetime import datetime
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.paper_trading_db import PaperTradingDB


class TestPaperTradingDB(unittest.TestCase):
    
    def setUp(self):
        """Create temporary database for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = PaperTradingDB(str(self.db_path))
    
    def tearDown(self):
        """Clean up temporary database"""
        if self.db_path.exists():
            self.db_path.unlink()
        Path(self.temp_dir).rmdir()
    
    def test_save_and_retrieve_trade(self):
        """Test saving and retrieving a trade"""
        trade = {
            'timestamp': datetime.now().isoformat(),
            'market_slug': 'test-market',
            'market_question': 'Test question?',
            'intended_side': 'YES',
            'intended_price': 0.65,
            'intended_size': 100.0,
            'strategy': 'ensemble',
            'edge': 0.15,
            'confidence': 0.8
        }
        
        trade_id = self.db.save_trade(trade)
        self.assertIsNotNone(trade_id)
        self.assertEqual(len(trade_id), 36)  # UUID length
        
        retrieved = self.db.get_trade(trade_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['market_slug'], 'test-market')
        self.assertEqual(retrieved['intended_side'], 'YES')
        self.assertEqual(retrieved['intended_price'], 0.65)
    
    def test_update_outcome(self):
        """Test updating trade with outcome"""
        trade = {
            'timestamp': datetime.now().isoformat(),
            'market_slug': 'test-market',
            'intended_side': 'YES',
            'intended_price': 0.65,
            'intended_size': 100.0,
            'strategy': 'ensemble'
        }
        
        trade_id = self.db.save_trade(trade)
        
        # Update outcome
        success = self.db.update_trade_outcome(trade_id, 1, 35.0, "Win")
        self.assertTrue(success)
        
        # Verify update
        retrieved = self.db.get_trade(trade_id)
        self.assertEqual(retrieved['outcome'], 1)
        self.assertEqual(retrieved['pnl'], 35.0)
        self.assertEqual(retrieved['status'], 'closed')
    
    def test_get_open_trades(self):
        """Test getting open trades"""
        # Create open trade
        open_trade = {
            'timestamp': datetime.now().isoformat(),
            'market_slug': 'open-market',
            'intended_side': 'YES',
            'intended_price': 0.5,
            'intended_size': 100.0
        }
        self.db.save_trade(open_trade)
        
        # Create closed trade
        closed_trade = {
            'timestamp': datetime.now().isoformat(),
            'market_slug': 'closed-market',
            'intended_side': 'NO',
            'intended_price': 0.6,
            'intended_size': 100.0
        }
        closed_id = self.db.save_trade(closed_trade)
        self.db.update_trade_outcome(closed_id, 0, -20.0)
        
        # Get open trades
        open_trades = self.db.get_open_trades()
        self.assertEqual(len(open_trades), 1)
        self.assertEqual(open_trades[0]['market_slug'], 'open-market')
    
    def test_performance_summary(self):
        """Test performance summary"""
        # Create winning trade
        win_trade = {
            'timestamp': datetime.now().isoformat(),
            'market_slug': 'win-market',
            'intended_side': 'YES',
            'intended_price': 0.5,
            'intended_size': 100.0,
            'edge': 0.10
        }
        win_id = self.db.save_trade(win_trade)
        self.db.update_trade_outcome(win_id, 1, 50.0)
        
        # Create losing trade
        loss_trade = {
            'timestamp': datetime.now().isoformat(),
            'market_slug': 'loss-market',
            'intended_side': 'NO',
            'intended_price': 0.6,
            'intended_size': 100.0,
            'edge': 0.10
        }
        loss_id = self.db.save_trade(loss_trade)
        self.db.update_trade_outcome(loss_id, 1, -40.0)  # NO lost
        
        summary = self.db.get_performance_summary()
        
        self.assertEqual(summary['total_trades'], 2)
        self.assertEqual(summary['winning_trades'], 1)
        self.assertEqual(summary['losing_trades'], 1)
        self.assertEqual(summary['win_rate'], 0.5)
        self.assertEqual(summary['total_pnl'], 10.0)


if __name__ == '__main__':
    unittest.main()
