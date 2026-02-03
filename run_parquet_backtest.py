#!/usr/bin/env python3
"""
Run backtest on Parquet data
Timestamp: 2026-02-03 18:56 GMT+1
"""

from utils.backtest import BacktestEngine

print('=' * 70)
print('🚀 BACKTEST WITH PARQUET DATA')
print('=' * 70)

# Load data from Parquet
print('\n1. Loading data from resolved_markets.parquet...')
historical_data = BacktestEngine.load_from_parquet('data/resolved_markets.parquet')
print(f'   Loaded {len(historical_data):,} records')

# Run backtests
print('\n' + '=' * 70)
print('🚀 RUNNING BACKTESTS - $1,000 BANKROLL')
print('=' * 70)

strategies = ['ensemble', 'momentum', 'mean_reversion']
results = {}

for strat in strategies:
    print(f'\nTesting {strat}...')
    engine = BacktestEngine(initial_bankroll=1000, max_position_pct=0.20)
    result = engine.run_backtest(historical_data, strategy=strat, min_edge=0.03, verbose=False)
    results[strat] = result

# Display results
print('\n' + '=' * 70)
print(f'📊 RESULTS - PARQUET DATA, $1,000 BANKROLL')
print('=' * 70)
print(f'{"Strategy":<15} {"Start":>10} {"End":>12} {"P&L":>12} {"Return":>10} {"Trades":>8} {"Win%":>8} {"Sharpe":>8}')
print('-' * 70)

for strat in strategies:
    r = results[strat]
    print(f'{strat:<15} ${1000:>9,.0f} ${r.final_bankroll:>11,.2f} {r.total_pnl:>+11,.2f} {r.total_pnl_pct:>+9.1f}% {r.total_trades:>8} {r.win_rate:>7.1%} {r.sharpe_ratio:>8.2f}')

print('=' * 70)

# Also test with large dataset
print('\n\n' + '=' * 70)
print('🚀 TESTING WITH LARGE DATASET (10K markets)')
print('=' * 70)

print('\n2. Loading data from large_resolved_markets.parquet...')
large_data = BacktestEngine.load_from_parquet('data/large_resolved_markets.parquet')
print(f'   Loaded {len(large_data):,} records')

engine = BacktestEngine(initial_bankroll=1000, max_position_pct=0.20)
result = engine.run_backtest(large_data, strategy='momentum', min_edge=0.05, verbose=False)

print(f'\nMOMENTUM on {len(large_data):,} markets:')
print(f'  Final: ${result.final_bankroll:,.2f} ({result.total_pnl_pct:+.1f}%)')
print(f'  Trades: {result.total_trades} | Win%: {result.win_rate:.1%} | Sharpe: {result.sharpe_ratio:.2f}')

print('\n✅ Parquet backtest complete!')
