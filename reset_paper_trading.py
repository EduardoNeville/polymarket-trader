#!/usr/bin/env python3
"""
Reset Paper Trading Database
Clears all trades to start fresh with $1,000 bankroll limit
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.paper_trading_db import PaperTradingDB

def reset_paper_trading():
    """Clear all paper trades and start fresh"""
    print("="*70)
    print("🗑️  RESETTING PAPER TRADING DATABASE")
    print("="*70)
    
    db = PaperTradingDB()
    
    # Get current stats
    open_trades = db.get_open_trades()
    closed_trades = db.get_closed_trades()
    
    print(f"\nCurrent state:")
    print(f"  Open trades: {len(open_trades)}")
    print(f"  Closed trades: {len(closed_trades)}")
    print(f"  Total exposure: ${sum(t.get('intended_size', 0) for t in open_trades):.2f}")
    
    confirm = input("\n⚠️  This will DELETE ALL TRADES. Type 'yes' to confirm: ")
    
    if confirm.lower() == 'yes':
        count = db.clear_all_trades()
        print(f"\n✅ Cleared {count} trades from database")
        print("Paper trading is now reset with $0 exposure")
        print("\nNext: Run 'python3 cron_paper_trading.py' to start fresh")
    else:
        print("\n❌ Cancelled. No trades were deleted.")

if __name__ == '__main__':
    reset_paper_trading()
