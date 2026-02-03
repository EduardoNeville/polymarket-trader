"""
Tests for paper trading system components
"""

import unittest
import sys
from pathlib import Path
from datetime import datetime
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.paper_trading_db import PaperTradingDB
from utils.paper_trading_signals import PaperTradingSignalGenerator
from utils.paper_trading_updater import PaperTradingUpdater


class TestPaperTradingSystem(unittest.TestCase):
    
    def setUp(self):
        """Set up test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = PaperTradingDB(str(self.db_path))
    
    def tearDown(self):
        """Clean up"""
        if self.db_path.exists():
            self.db_path.unlink()
        Path(self.temp_dir).rmdir()
    
    def test_signal_generator_creation(self):
        """Test signal generator initializes correctly"""
        generator = PaperTradingSignalGenerator(bankroll=1000, min_edge=0.05)
        self.assertEqual(generator.bankroll, 1000)
        self.assertEqual(generator.min_edge, 0.05)
    
    def test_updater_creation(self):
        """Test updater initializes correctly"""
        updater = PaperTradingUpdater()
        self.assertIsNotNone(updater.db)
    
    def test_determine_outcome(self):
        """Test outcome determination"""
        updater = PaperTradingUpdater()
        
        # YES wins
        self.assertEqual(updater.determine_outcome(1.0, 0.0), 1)
        self.assertEqual(updater.determine_outcome(0.99, 0.01), 1)
        
        # NO wins
        self.assertEqual(updater.determine_outcome(0.0, 1.0), 0)
        self.assertEqual(updater.determine_outcome(0.01, 0.99), 0)
        
        # Unresolved
        self.assertIsNone(updater.determine_outcome(0.5, 0.5))
        self.assertIsNone(updater.determine_outcome(0.8, 0.2))
    
    def test_calculate_pnl_yes_win(self):
        """Test P&L calculation for YES win"""
        updater = PaperTradingUpdater()
        
        trade = {
            'intended_side': 'YES',
            'intended_price': 0.60,
            'intended_size': 100
        }
        
        # YES wins (outcome = 1)
        pnl = updater.calculate_pnl(trade, 1)
        # Payout = $100, Cost = $60, P&L = $40
        self.assertEqual(pnl, 40.0)
    
    def test_calculate_pnl_yes_loss(self):
        """Test P&L calculation for YES loss"""
        updater = PaperTradingUpdater()
        
        trade = {
            'intended_side': 'YES',
            'intended_price': 0.60,
            'intended_size': 100
        }
        
        # NO wins (outcome = 0)
        pnl = updater.calculate_pnl(trade, 0)
        # Payout = $0, Cost = $60, P&L = -$60
        self.assertEqual(pnl, -60.0)
    
    def test_calculate_pnl_no_win(self):
        """Test P&L calculation for NO win"""
        updater = PaperTradingUpdater()
        
        trade = {
            'intended_side': 'NO',
            'intended_price': 0.70,  # YES at 0.70 means NO at 0.30
            'intended_size': 100
        }
        
        # NO wins (outcome = 0 means NO won)
        pnl = updater.calculate_pnl(trade, 0)
        # Payout = $100, Cost = $30 (NO price), P&L = $70
        self.assertEqual(pnl, 70.0)


if __name__ == '__main__':
    unittest.main()
