#!/usr/bin/env python3
"""
Paper Trading - All Three Options Combined
Option 1: Daily at market open
Option 2: When high-edge found (>10%)  
Option 3: Manual on-demand

Usage:
    python3 paper_trading_all_options.py [daily|high-edge|manual]
    
    daily     - Run daily routine
    high-edge - Scan for >10% edge opportunities
    manual    - Interactive signal generation
"""

import sys
sys.path.insert(0, '/home/eduardoneville/projects/polymarket-trader')

from datetime import datetime


def option_1_daily():
    """Option 1: Daily at market open"""
    print("\n" + "="*80)
    print("📅 OPTION 1: DAILY PAPER TRADING")
    print("="*80)
    
    import daily_paper_trading
    daily_paper_trading.daily_paper_trading()


def option_2_high_edge():
    """Option 2: When high-edge opportunities found"""
    print("\n" + "="*80)
    print("🎯 OPTION 2: HIGH-EDGE OPPORTUNITIES (>10%)")
    print("="*80)
    
    import high_edge_scanner
    scanner = high_edge_scanner.HighEdgeScanner(edge_threshold=0.10)
    signals = scanner.run(auto_save=True)
    
    return len(signals) > 0


def option_3_manual():
    """Option 3: Manual on-demand"""
    print("\n" + "="*80)
    print("🎮 OPTION 3: MANUAL ON-DEMAND")
    print("="*80)
    
    import utils.paper_trading_signals as pts
    
    print("\nManual Paper Trading Signal Generator")
    print("-" * 80)
    
    # Get user input
    max_markets = input("Max markets to scan (default 20): ").strip()
    max_markets = int(max_markets) if max_markets.isdigit() else 20
    
    min_edge = input("Minimum edge % (default 5): ").strip()
    min_edge = float(min_edge) / 100 if min_edge.replace('.', '').isdigit() else 0.05
    
    bankroll = input("Paper bankroll $ (default 1000): ").strip()
    bankroll = float(bankroll) if bankroll.replace('.', '').isdigit() else 1000
    
    print(f"\nConfig: {max_markets} markets, {min_edge:.1%} min edge, ${bankroll} bankroll\n")
    
    # Generate signals
    generator = pts.PaperTradingSignalGenerator(bankroll=bankroll, min_edge=min_edge)
    signals = generator.generate_signals_for_markets(
        max_markets=max_markets,
        save_to_db=True
    )
    
    # Display
    generator.display_signals(signals)
    
    stats = generator.get_signal_statistics(signals)
    if stats:
        print(f"\n📈 STATISTICS:")
        print(f"  Total signals: {stats.get('total_signals', 0)}")
        print(f"  Average edge: {stats.get('avg_edge', 0):.1%}")


def show_menu():
    """Show main menu"""
    print("\n" + "="*80)
    print("📊 PAPER TRADING - ALL OPTIONS")
    print("="*80)
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print("\nSelect option:")
    print("  1. 📅 Daily at market open (automated routine)")
    print("  2. 🎯 High-edge opportunities (>10% edge)")
    print("  3. 🎮 Manual on-demand (custom settings)")
    print("  4. 📊 View current paper trading stats")
    print("  5. 🚪 Exit")
    print("-"*80)


def view_stats():
    """View paper trading statistics"""
    from utils.paper_trading_db import PaperTradingDB
    
    db = PaperTradingDB()
    open_trades = db.get_open_trades()
    closed_trades = db.get_closed_trades()
    summary = db.get_performance_summary()
    
    print("\n" + "="*80)
    print("📊 PAPER TRADING STATISTICS")
    print("="*80)
    print(f"Open trades:     {len(open_trades)}")
    print(f"Closed trades:   {len(closed_trades)}")
    print(f"Total tracked:   {len(open_trades) + len(closed_trades)}")
    
    if summary['total_trades'] > 0:
        print(f"\nPerformance:")
        print(f"  Win rate:      {summary['win_rate']:.1%}")
        print(f"  Total P&L:     ${summary['total_pnl']:+.2f}")
        print(f"  Avg per trade: ${summary['avg_pnl']:+.2f}")
    else:
        print(f"\n⏳ No closed trades yet (waiting for outcomes)")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Paper Trading - All Three Options'
    )
    parser.add_argument(
        'mode',
        nargs='?',
        choices=['daily', 'high-edge', 'manual', 'stats'],
        help='Run mode: daily, high-edge, manual, or stats'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'daily':
        option_1_daily()
    elif args.mode == 'high-edge':
        option_2_high_edge()
    elif args.mode == 'manual':
        option_3_manual()
    elif args.mode == 'stats':
        view_stats()
    else:
        # Interactive menu
        while True:
            show_menu()
            choice = input("\nEnter option (1-5): ").strip()
            
            if choice == '1':
                option_1_daily()
            elif choice == '2':
                option_2_high_edge()
            elif choice == '3':
                option_3_manual()
            elif choice == '4':
                view_stats()
            elif choice == '5':
                print("\n✅ Exiting. Goodbye!")
                break
            else:
                print("\n❌ Invalid option")
            
            input("\nPress Enter to continue...")


if __name__ == '__main__':
    main()
