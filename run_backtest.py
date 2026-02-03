#!/usr/bin/env python3
"""Run a quick backtest demo with simulated data"""

import numpy as np
from datetime import datetime, timedelta
from utils.backtest import BacktestEngine

print('🔄 Generating simulated historical data...')
print('=' * 50)

# Generate simulated historical market data
# Each market has multiple price observations before resolution
np.random.seed(42)
historical_data = []

base_date = datetime(2025, 1, 1)

for market_id in range(20):  # 20 markets
    # Each market has 5-10 price observations
    num_observations = np.random.randint(5, 11)
    
    # Determine actual outcome
    actual_outcome = 1 if np.random.random() > 0.5 else 0
    
    # Generate price path that moves toward actual outcome
    if actual_outcome == 1:
        # Price trends up
        start_price = np.random.uniform(0.35, 0.50)
        end_price = np.random.uniform(0.60, 0.85)
    else:
        # Price trends down  
        start_price = np.random.uniform(0.50, 0.65)
        end_price = np.random.uniform(0.15, 0.40)
    
    # Create price path
    for obs_id in range(num_observations):
        progress = obs_id / (num_observations - 1)
        price = start_price + (end_price - start_price) * progress
        price += np.random.normal(0, 0.02)  # Add noise
        price = np.clip(price, 0.05, 0.95)
        
        date = base_date + timedelta(days=market_id * 2 + obs_id)
        
        historical_data.append({
            'timestamp': date.isoformat(),
            'market_slug': f'market-{market_id}',
            'question': f'Test market {market_id}?',
            'price': price,
            'outcome': actual_outcome if obs_id == num_observations - 1 else None,
            'category': 'general'
        })

print(f'Generated {len(historical_data)} observations across 20 markets')
print('\n🔄 Running Backtest...')
print('=' * 50)

engine = BacktestEngine(initial_bankroll=10000)

# Test ensemble strategy
result = engine.run_backtest(historical_data, strategy='ensemble', verbose=True)

print('\n' + '=' * 50)
print('📊 ENSEMBLE STRATEGY RESULTS')
print('=' * 50)
print(f'Initial Bankroll: ${result.initial_bankroll:,.2f}')
print(f'Final Bankroll:   ${result.final_bankroll:,.2f}')
print(f'Total P&L:        ${result.total_pnl:+.2f} ({result.total_pnl/result.initial_bankroll:+.2%})')
print(f'Total Trades:     {result.total_trades}')
print(f'Win Rate:         {result.win_rate:.1%}')
print(f'Sharpe Ratio:     {result.sharpe_ratio:.2f}')
print(f'Sortino Ratio:    {result.sortino_ratio:.2f}')
print(f'Max Drawdown:     {result.max_drawdown_pct:.1%}')
print('=' * 50)

# Compare with other strategies
print('\n🏆 STRATEGY COMPARISON:')
strategies = ['momentum', 'mean_reversion']

for strat in strategies:
    res = engine.run_backtest(historical_data, strategy=strat, verbose=False)
    print(f'  {strat:15}: P&L=${res.total_pnl:+8.2f} | Sharpe={res.sharpe_ratio:5.2f} | Win={res.win_rate:.1%}')

print('\n✅ Backtest complete!')
