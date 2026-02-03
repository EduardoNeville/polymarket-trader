#!/usr/bin/env python3
"""
Run backtest on EXPANDED dataset (original + new data)
Timestamp: 2026-02-03 18:25 GMT+1
"""

import json
from utils.backtest import BacktestEngine

print('=' * 70)
print('🔄 BACKTEST ON EXPANDED DATASET')
print('=' * 70)

# Load original data
print('\n1. Loading original resolved_markets.json...')
with open('data/resolved_markets.json', 'r') as f:
    original_data = json.load(f)
print(f'   Original: {len(original_data):,} records')

# Load additional data
print('\n2. Loading additional_resolved_markets.json...')
with open('data/additional_resolved_markets.json', 'r') as f:
    additional_data = json.load(f)
print(f'   Additional: {len(additional_data):,} records')

# Combine datasets
print('\n3. Combining datasets...')
all_data = original_data + additional_data
print(f'   Total: {len(all_data):,} records')

# Group by market
print('\n4. Grouping by market...')
markets = {}
for record in all_data:
    slug = record['market_slug']
    if slug not in markets:
        markets[slug] = []
    markets[slug].append(record)

print(f'   Unique markets: {len(markets)}')

# Filter to resolved markets
resolved_slugs = [slug for slug, recs in markets.items() 
                  if any(r.get('outcome') is not None for r in recs)]
print(f'   Resolved markets: {len(resolved_slugs)}')

# Use ALL resolved markets for bigger sample
sample_slugs = resolved_slugs  # Use all, not just 20
print(f'   Using ALL {len(sample_slugs)} markets for backtest')

# Prepare data
print('\n5. Preparing historical data...')
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

print(f'   Prepared {len(historical_data):,} observations')

# Run backtests with $1,000
print('\n' + '=' * 70)
print('🚀 RUNNING BACKTESTS - $1,000 BANKROLL')
print('=' * 70)

strategies = ['ensemble', 'momentum', 'mean_reversion']
results = {}

for strat in strategies:
    print(f'\nTesting {strat}...')
    engine = BacktestEngine(initial_bankroll=1000)
    result = engine.run_backtest(historical_data, strategy=strat, min_edge=0.03, verbose=False)
    results[strat] = result

# Display results
print('\n' + '=' * 70)
print(f'📊 RESULTS - {len(sample_slugs)} MARKETS, $1,000 BANKROLL')
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

print('\n✅ Expanded backtest complete!')
