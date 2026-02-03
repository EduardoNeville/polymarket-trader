#!/usr/bin/env python3
"""
Daily Paper Trading - Run at Market Open
Option 1: Daily automated paper trading
Timestamp: 2026-02-03 21:39 GMT+1
"""

import sys
sys.path.insert(0, '/home/eduardoneville/projects/polymarket-trader')

from datetime import datetime
from utils.paper_trading_signals import PaperTradingSignalGenerator
from utils.paper_trading_db import PaperTradingDB
from utils.paper_trading_updater import PaperTradingUpdater


def daily_paper_trading():
    """Run paper trading routine for the day"""
    print("="*70)
    print("📅 DAILY PAPER TRADING ROUTINE")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Step 1: Update any resolved trades from yesterday
    print("\n1️⃣ Updating yesterday's trade outcomes...")
    updater = PaperTradingUpdater()
    summary = updater.update_open_trades(verbose=False)
    print(f"   Updated: {summary['updated']} | Still open: {summary['unresolved']}")
    
    # Step 2: Generate new signals for today
    print("\n2️⃣ Generating new paper trading signals...")
    generator = PaperTradingSignalGenerator(bankroll=1000, min_edge=0.05)
    signals = generator.generate_signals_for_markets(
        max_markets=30,
        save_to_db=True
    )
    
    # Step 3: Display summary
    print("\n3️⃣ Daily Summary:")
    db = PaperTradingDB()
    open_trades = db.get_open_trades()
    closed_trades = db.get_closed_trades()
    perf = db.get_performance_summary()
    
    print(f"   New signals today: {len(signals)}")
    print(f"   Total open trades: {len(open_trades)}")
    print(f"   Total closed trades: {len(closed_trades)}")
    
    if perf['total_trades'] > 0:
        print(f"   Win rate: {perf['win_rate']:.1%}")
        print(f"   Total P&L: ${perf['total_pnl']:+.2f}")
    
    print("\n" + "="*70)
    print("✅ Daily routine complete!")
    print("Next run: Tomorrow at market open")
    print("="*70)


if __name__ == '__main__':
    daily_paper_trading()
