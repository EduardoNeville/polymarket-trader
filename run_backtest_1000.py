#!/usr/bin/env python3
"""
Run backtest on resolved_markets.json with $1,000 bankroll
Timestamp: 2026-02-03 18:15 GMT+1
"""

import json
import sys
from datetime import datetime
from utils.backtest import BacktestEngine

print('=' * 70)
print('🔄 BACKTEST WITH $1,000 BANKROLL')
print('=' * 70)

# Load the data
print('\nLoading resolved_markets.json (110 MB)...')
with open('data/resolved_markets.json', 'r') as f:
    data = json.load(f)

print(f'Loaded {len(data):,} records')

# Group by market
markets = {}
for record in data:
    slug = record['market_slug']
    if slug not in markets:
        markets[slug] = []
    markets[slug].append(record)

print(f'Found {len(markets)} unique markets')

# Use 20 resolved markets
resolved_slugs = [slug for slug, recs in markets.items() 
                  if any(r.get('outcome') is not None for r in recs)]
sample_slugs = resolved_slugs[:20]
print(f'Using {len(sample_slugs)} markets for backtest')

# Prepare data
historical_data = []
for slug in sample_slugs:
    records = sorted(markets[slug], key=lambda x: x['timestamp'])
    outcome = None
    for r in reversed(records):
        if r.get('outcome') is not None:
            outcome = r['outcome']
            break
    
    if outcome is not None:
        for r in records[:-1]:
            if r.get('price') is not None:
                historical_data.append({
                    'timestamp': r['timestamp'],
                    'market_slug': slug,
                    'question': r['question'],
                    'price': r['price'],
                    'outcome': None,
                    'category': r.get('category', 'general')
                })
        final = records[-1]
        historical_data.append({
            'timestamp': final['timestamp'],
            'market_slug': slug,
            'question': final['question'],
            'price': final.get('price', 0.5),
            'outcome': outcome,
            'category': final.get('category', 'general')
        })

print(f'Prepared {len(historical_data)} observations')

# Run backtests with $1,000
print('\n' + '=' * 70)
print('🚀 RUNNING BACKTESTS - $1,000 INITIAL BANKROLL')
print('=' * 70)

strategies = ['ensemble', 'momentum', 'mean_reversion']
results = {}

for strat in strategies:
    engine = BacktestEngine(initial_bankroll=1000)  # $1,000 bankroll
    result = engine.run_backtest(historical_data, strategy=strat, min_edge=0.03, verbose=False)
    results[strat] = result

# Display results
print('\n' + '=' * 70)
print('📊 RESULTS WITH $1,000 BANKROLL')
print('=' * 70)
print(f'{"Strategy":<15} {"Start":>10} {"End":>12} {"P&L":>12} {"Return":>10} {"Win%":>8} {"Sharpe":>8}')
print('-' * 70)

for strat in strategies:
    r = results[strat]
    print(f'{strat:<15} ${1000:>9,.0f} ${r.final_bankroll:>11,.2f} {r.total_pnl:>+11,.2f} {r.total_pnl_pct:>+9.1f}% {r.win_rate:>7.1%} {r.sharpe_ratio:>8.2f}')

print('=' * 70)

# Show individual results
print('\n📈 DETAILED BREAKDOWN:')
for strat in strategies:
    r = results[strat]
    print(f'\n{strat.upper()}:')
    print(f'  Final Bankroll:  ${r.final_bankroll:,.2f}')
    print(f'  Total Return:    {r.total_pnl_pct:+.1f}%')
    print(f'  Trades:          {r.total_trades} ({r.winning_trades} wins, {r.losing_trades} losses)')
    print(f'  Max Drawdown:    {r.max_drawdown_pct:.1f}%')
    print(f'  Sharpe Ratio:    {r.sharpe_ratio:.2f}')

print('\n✅ Backtest complete!')
