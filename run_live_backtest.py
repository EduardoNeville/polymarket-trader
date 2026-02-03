#!/usr/bin/env python3
"""
Run backtest on resolved_markets.json historical data
Timestamp: 2026-02-03 17:53 GMT+1
"""

import json
import sys
from datetime import datetime
from utils.backtest import BacktestEngine

print('=' * 70)
print('🔄 LOADING HISTORICAL DATA FOR BACKTEST')
print('=' * 70)

# Load the data
print('\nLoading resolved_markets.json (110 MB)...')
with open('data/resolved_markets.json', 'r') as f:
    data = json.load(f)

print(f'Loaded {len(data):,} records')

# Group by market - we need price history for each market
print('\nGrouping by market...')
markets = {}
for record in data:
    slug = record['market_slug']
    if slug not in markets:
        markets[slug] = []
    markets[slug].append(record)

print(f'Found {len(markets)} unique markets')

# Filter to markets with outcomes
resolved_slugs = []
for slug, records in markets.items():
    has_outcome = any(r.get('outcome') is not None for r in records)
    if has_outcome:
        resolved_slugs.append(slug)

print(f'Resolved markets: {len(resolved_slugs)}')

# Sample: take first 20 resolved markets for testing
sample_slugs = resolved_slugs[:20]
print(f'Using sample of {len(sample_slugs)} markets for backtest')

# Prepare data in format BacktestEngine expects
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

print(f'Prepared {len(historical_data)} observations for backtest')

# Run backtest
print('\n' + '=' * 70)
print('🚀 RUNNING BACKTEST - ENSEMBLE STRATEGY')
print('=' * 70)

engine = BacktestEngine(initial_bankroll=10000)
result = engine.run_backtest(historical_data, strategy='ensemble', min_edge=0.03, verbose=False)

print('\n' + '=' * 70)
print('📊 ENSEMBLE BACKTEST RESULTS')
print('=' * 70)
print(f'Initial Bankroll:      ${result.initial_bankroll:>12,.2f}')
print(f'Final Bankroll:        ${result.final_bankroll:>12,.2f}')
print(f'Total P&L:             ${result.total_pnl:>+12,.2f} ({result.total_pnl_pct:+.2f}%)')
print(f'Total Trades:          {result.total_trades:>12}')
print(f'Winning Trades:        {result.winning_trades:>12} ({result.win_rate:.1f}%)')
print(f'Losing Trades:         {result.losing_trades:>12}')
print(f'Avg Trade P&L:         ${result.avg_trade_pnl:>+12,.2f}')
print(f'Max Drawdown:          ${result.max_drawdown:>12,.2f} ({result.max_drawdown_pct:.2f}%)')
print(f'Sharpe Ratio:          {result.sharpe_ratio:>12.2f}')
print(f'Sortino Ratio:         {result.sortino_ratio:>12.2f}')
print('=' * 70)

# Compare with other strategies
print('\n🏆 STRATEGY COMPARISON:')
print('-' * 70)
print(f'{"Strategy":<15} {"P&L":>14} {"Win Rate":>10} {"Sharpe":>8} {"Trades":>8}')
print('-' * 70)

strategies = ['ensemble', 'momentum', 'mean_reversion']
for strat in strategies:
    res = engine.run_backtest(historical_data, strategy=strat, min_edge=0.03, verbose=False)
    print(f'{strat:<15} {res.total_pnl:>+14,.2f} {res.win_rate:>9.1%} {res.sharpe_ratio:>8.2f} {res.total_trades:>8}')

print('=' * 70)
print('\n✅ Backtest complete!')
