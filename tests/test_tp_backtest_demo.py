#!/usr/bin/env python3
"""
Test script for 50% Edge Rule take-profit in backtest engine.
Demonstrates TP hit vs resolution exit scenarios.
"""

import sys
sys.path.insert(0, '/home/eduardoneville/projects/polymarket-trader')

from utils.backtest import BacktestEngine

def test_take_profit_backtest():
    """Test backtest with take-profit enabled"""
    
    print("=" * 80)
    print("🧪 Testing 50% Edge Rule Take-Profit in Backtest Engine")
    print("=" * 80)
    
    # Create test data: Market that hits TP
    # Entry: $0.40, Estimated: 50%, Edge: 10%
    # TP Target: $0.45 (12.5% move)
    # Price history: 0.40 → 0.42 → 0.44 → 0.46 (TP hit at 0.46)
    market_tp_hit = []
    for i, price in enumerate([0.40, 0.42, 0.44, 0.46, 0.48]):
        market_tp_hit.append({
            'timestamp': f'2024-01-{i+1:02d}T12:00:00',
            'market_slug': 'test-tp-hit',
            'question': 'Will TP be hit?',
            'price': price,
            'outcome': 1,  # Resolved YES
            'category': 'test'
        })
    
    # Create test data: Market that does NOT hit TP
    # Entry: $0.40, Estimated: 50%, Edge: 10%
    # TP Target: $0.45 (12.5% move)
    # Price history: 0.40 → 0.42 → 0.43 → 0.44 (never hits 0.45)
    market_tp_miss = []
    for i, price in enumerate([0.40, 0.42, 0.43, 0.44, 0.41]):
        market_tp_miss.append({
            'timestamp': f'2024-01-{i+1:02d}T12:00:00',
            'market_slug': 'test-tp-miss',
            'question': 'Will TP be missed?',
            'price': price,
            'outcome': 0,  # Resolved NO
            'category': 'test'
        })
    
    # Combine data
    historical_data = market_tp_hit + market_tp_miss
    
    print("\n1️⃣  Running WITHOUT take-profit (baseline)")
    print("-" * 80)
    engine_baseline = BacktestEngine(initial_bankroll=10000)
    result_baseline = engine_baseline.run_backtest(
        historical_data,
        strategy='ensemble',
        min_edge=0.05,
        use_take_profit=False,
        verbose=False
    )
    
    print(f"Total Trades: {result_baseline.total_trades}")
    print(f"Total P&L: ${result_baseline.total_pnl:+.2f}")
    print(f"Win Rate: {result_baseline.win_rate:.1%}")
    
    for trade in result_baseline.trades:
        print(f"\n  Trade: {trade.market_slug}")
        print(f"    Side: {trade.side}, Entry: ${trade.entry_price:.2f}")
        print(f"    Exit: ${trade.exit_price:.2f}, P&L: ${trade.pnl:+.2f}")
        print(f"    Exit Reason: {trade.exit_reason or 'N/A'}")
        print(f"    Holding Days: {trade.holding_days}")
    
    print("\n2️⃣  Running WITH take-profit (50% Edge Rule)")
    print("-" * 80)
    engine_tp = BacktestEngine(initial_bankroll=10000)
    result_tp = engine_tp.run_backtest(
        historical_data,
        strategy='ensemble',
        min_edge=0.05,
        use_take_profit=True,
        verbose=False
    )
    
    print(f"Total Trades: {result_tp.total_trades}")
    print(f"Total P&L: ${result_tp.total_pnl:+.2f}")
    print(f"Win Rate: {result_tp.win_rate:.1%}")
    print(f"\n🎯 Take-Profit Metrics:")
    print(f"  TP Exits: {result_tp.tp_exit_count} ({result_tp.tp_hit_rate:.1%})")
    print(f"  Resolution Exits: {result_tp.resolution_exit_count}")
    print(f"  Avg Holding Time: {result_tp.avg_holding_days:.1f} days")
    
    for trade in result_tp.trades:
        print(f"\n  Trade: {trade.market_slug}")
        print(f"    Side: {trade.side}, Entry: ${trade.entry_price:.2f}")
        print(f"    TP Target: ${trade.take_profit_price:.2f}" if trade.take_profit_price else "    TP: N/A")
        print(f"    Exit: ${trade.exit_price:.2f}, P&L: ${trade.pnl:+.2f}")
        print(f"    Exit Reason: {trade.exit_reason}")
        print(f"    Holding Days: {trade.holding_days}")
    
    print("\n3️⃣  Comparison Summary")
    print("-" * 80)
    print(f"{'Metric':<30} {'Baseline':<15} {'With TP':<15} {'Delta':<15}")
    print("-" * 80)
    print(f"{'Total P&L':<30} ${result_baseline.total_pnl:+>13.2f} ${result_tp.total_pnl:+>13.2f} ${result_tp.total_pnl - result_baseline.total_pnl:+>13.2f}")
    print(f"{'Win Rate':<30} {result_baseline.win_rate:>13.1%} {result_tp.win_rate:>13.1%} {(result_tp.win_rate - result_baseline.win_rate):>+13.1%}")
    print(f"{'Avg Holding Days':<30} {result_baseline.avg_holding_days:>13.1f} {result_tp.avg_holding_days:>13.1f} {(result_tp.avg_holding_days - result_baseline.avg_holding_days):>+13.1f}")
    print(f"{'TP Hit Rate':<30} {'N/A':<15} {result_tp.tp_hit_rate:>13.1%}")
    
    print("\n" + "=" * 80)
    print("✅ Take-profit backtest test complete!")
    print("=" * 80)

if __name__ == "__main__":
    test_take_profit_backtest()
