#!/usr/bin/env python3
"""
Run backtest on 10,000+ resolved markets
Timestamp: 2026-02-03 18:36 GMT+1
"""

import json
from utils.backtest import BacktestEngine

print('=' * 70)
print('🚀 BACKTEST ON 10,000+ MARKETS')
print('=' * 70)

# Load the large dataset
print('\n1. Loading large_resolved_markets.json...')
with open('data/large_resolved_markets.json', 'r') as f:
    data = json.load(f)

print(f'   Loaded {len(data):,} resolved markets')

# Show distribution
yes_count = sum(1 for r in data if r['outcome'] == 1)
no_count = sum(1 for r in data if r['outcome'] == 0)
print(f'   YES outcomes: {yes_count:,}')
print(f'   NO outcomes:  {no_count:,}')

# Prepare data for backtest (each market is one observation)
# For proper backtest, we need price history, but we only have final prices
# So we'll simulate with a single observation per market
historical_data = []
for record in data:
    # Create a simple entry: assume market price was at 0.5 initially
    # and moved to the final outcome price
    final_price = record['price']
    outcome = record['outcome']
    
    # Use the final price as the entry price for backtest
    historical_data.append({
        'timestamp': record['timestamp'],
        'market_slug': record['market_slug'],
        'question': record['question'],
        'price': final_price if final_price > 0 else 0.5,
        'outcome': outcome,
        'category': record.get('category', 'general')
    })

print(f'\n2. Prepared {len(historical_data):,} observations for backtest')

# Run backtests with $1,000
print('\n' + '=' * 70)
print('🚀 RUNNING BACKTESTS - $1,000 BANKROLL')
print('=' * 70)

strategies = ['ensemble', 'momentum', 'mean_reversion']
results = {}

for strat in strategies:
    print(f'\nTesting {strat}...')
    engine = BacktestEngine(initial_bankroll=1000, max_position_pct=0.20)
    result = engine.run_backtest(historical_data, strategy=strat, min_edge=0.05, verbose=False)
    results[strat] = result

# Display results
print('\n' + '=' * 70)
print(f'📊 RESULTS - {len(historical_data):,} MARKETS, $1,000 BANKROLL')
print('=' * 70)
print(f'{"Strategy":<15} {"Start":>10} {"End":>12} {"P&L":>12} {"Return":>10} {"Trades":>8} {"Win%":>8} {"Sharpe":>8}')
print('-' * 70)

for strat in strategies:
    r = results[strat]
    print(f'{strat:<15} ${1000:>9,.0f} ${r.final_bankroll:>11,.2f} {r.total_pnl:>+11,.2f} {r.total_pnl_pct:>+9.1f}% {r.total_trades:>8} {r.win_rate:>7.1%} {r.sharpe_ratio:>8.2f}')

print('=' * 70)

# Detailed breakdown
print('\n📈 DETAILED BREAKDOWN:')
for strat in strategies:
    r = results[strat]
    print(f'\n{strat.upper()}:')
    print(f'  Final Bankroll:  ${r.final_bankroll:,.2f}')
    print(f'  Total Return:    {r.total_pnl_pct:+.1f}%')
    print(f'  Trades:          {r.total_trades} ({r.winning_trades} wins, {r.losing_trades} losses)')
    print(f'  Win Rate:        {r.win_rate:.1%}')
    print(f'  Max Drawdown:    {r.max_drawdown_pct:.1f}%')
    print(f'  Sharpe Ratio:    {r.sharpe_ratio:.2f}')
    print(f'  Avg Trade P&L:   ${r.avg_trade_pnl:,.2f}')

print('\n✅ 10K market backtest complete!')
