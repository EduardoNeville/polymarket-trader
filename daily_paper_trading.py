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
from utils.paper_trading_tp_monitor import TPSLMonitor


def daily_paper_trading():
    """Run paper trading routine for the day"""
    print("="*70)
    print("📅 DAILY PAPER TRADING ROUTINE")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Step 1: Check for TP/SL hits first
    print("\n1️⃣ Checking for TP/SL hits...")
    monitor = TPSLMonitor()
    tp_summary = monitor.check_all_trades(verbose=False)
    print(f"   TP hits: {tp_summary['tp_hits']} | SL hits: {tp_summary['sl_hits']} | Checked: {tp_summary['checked']}")
    
    # Step 2: Update any resolved trades from yesterday
    print("\n2️⃣ Updating resolved trade outcomes...")
    updater = PaperTradingUpdater()
    summary = updater.update_open_trades(verbose=False)
    print(f"   Updated: {summary['updated']} | TP exits: {summary.get('tp_exits', 0)} | SL exits: {summary.get('sl_exits', 0)} | Still open: {summary['unresolved']}")
    
    # Step 3: Generate new signals for today
    print("\n3️⃣ Generating new paper trading signals with TP/SL...")
    generator = PaperTradingSignalGenerator(bankroll=1000, min_edge=0.05)
    signals = generator.generate_signals_for_markets(
        max_markets=30,
        save_to_db=True
    )
    
    # Step 4: Display summary
    print("\n4️⃣ Daily Summary:")
    db = PaperTradingDB()
    open_trades = db.get_open_trades()
    closed_trades = db.get_closed_trades()
    perf = db.get_performance_summary()
    
    # Get exit reason breakdown
    exit_summary = db.get_exit_reason_summary()
    
    print(f"   New signals today: {len(signals)}")
    print(f"   Total open trades: {len(open_trades)}")
    print(f"   Total closed trades: {len(closed_trades)}")
    
    if exit_summary:
        print(f"   TP exits: {exit_summary.get('tp', {}).get('count', 0)}")
        print(f"   SL exits: {exit_summary.get('stop_loss', {}).get('count', 0)}")
        print(f"   Resolution exits: {exit_summary.get('resolution', {}).get('count', 0)}")
    
    if perf['total_trades'] > 0:
        print(f"   Win rate: {perf['win_rate']:.1%}")
        print(f"   Total P&L: ${perf['total_pnl']:+.2f}")
    
    print("\n" + "="*70)
    print("✅ Daily routine complete!")
    print("\n💡 To monitor TP/SL continuously, run:")
    print("   python3 -c \"from utils.paper_trading_tp_monitor import run_monitor; run_monitor(5)\"")
    print("="*70)


if __name__ == '__main__':
    daily_paper_trading()
