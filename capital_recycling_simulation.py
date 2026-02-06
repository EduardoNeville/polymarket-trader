#!/usr/bin/env python3
"""
Capital Recycling Simulation

This script properly simulates how the TP strategy would perform over time
by recycling capital into new trades, while baseline holds positions.

Key difference from standard backtest:
- Baseline: Holds positions until resolution (blocks capital)
- TP: Exits early, freeing capital for new opportunities

Over the same time period, TP should make MORE trades.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import heapq
import sys

sys.path.insert(0, str(Path(__file__).parent))

from utils.backtest import BacktestEngine
from utils.take_profit_calculator import calculate_take_profit, check_take_profit_hit, calculate_holding_days


def simulate_capital_recycling(
    historical_data: List[Dict],
    initial_bankroll: float = 1000,
    min_edge: float = 0.05,
    use_take_profit: bool = False,
    verbose: bool = True
) -> Dict:
    """
    Simulate trading with capital constraints.
    
    Key concept: Capital is only available when positions close.
    TP strategy closes positions faster, freeing up capital sooner.
    
    Returns:
        Dict with simulation results
    """
    from models.edge_estimator import EnsembleEdgeEstimator
    from strategies.adaptive_kelly import AdaptiveKelly
    
    if verbose:
        print(f"\n{'='*80}")
        print(f"💰 CAPITAL RECYCLING SIMULATION")
        print(f"{'='*80}")
        print(f"Initial Bankroll: ${initial_bankroll:,.2f}")
        print(f"Use Take-Profit: {use_take_profit}")
        print(f"Min Edge: {min_edge:.1%}")
    
    # Group data by market
    markets = {}
    for data in historical_data:
        slug = data['market_slug']
        if slug not in markets:
            markets[slug] = []
        markets[slug].append(data)
    
    # Sort each market's data by timestamp
    for slug in markets:
        markets[slug].sort(key=lambda x: x['timestamp'])
    
    # Get all market entry events (sorted by time)
    entry_events = []
    for slug, data in markets.items():
        if len(data) >= 2:
            entry_events.append({
                'timestamp': data[0]['timestamp'],
                'market_slug': slug,
                'market_data': data
            })
    
    entry_events.sort(key=lambda x: x['timestamp'])
    
    if verbose:
        print(f"Total entry opportunities: {len(entry_events)}")
    
    # Initialize
    bankroll = initial_bankroll
    available_capital = initial_bankroll
    trades = []
    pending_positions = []  # Heap: (exit_time, position_info)
    estimator = EnsembleEdgeEstimator()
    kelly = AdaptiveKelly()
    
    for event in entry_events:
        slug = event['market_slug']
        market_data = event['market_data']
        
        # Check if any positions have closed (free up capital)
        current_time = market_data[0]['timestamp']
        while pending_positions and pending_positions[0][0] <= current_time:
            exit_time, _, position_size, pnl = heapq.heappop(pending_positions)
            # Return capital + P&L to available pool
            available_capital += position_size + pnl
        
        # Skip if no available capital
        if available_capital < 10:  # Minimum trade size
            continue
        
        # Get prediction
        entry_data = market_data[0]
        exit_data = market_data[-1]
        entry_price = entry_data['price']
        actual_outcome = exit_data['outcome']
        
        if actual_outcome is None:
            continue
        
        # Feed price history
        for data in market_data[:-1]:
            estimator.update_price(slug, data['price'])
        
        # Get prediction
        estimate = estimator.estimate_probability(
            slug,
            entry_data.get('question', ''),
            entry_price,
            entry_data.get('category', 'general')
        )
        
        edge = estimate.ensemble_probability - entry_price
        if abs(edge) < min_edge:
            continue
        
        # Calculate position size (capped by available capital)
        kelly_result = kelly.calculate_position_size(
            bankroll=available_capital,
            market_price=entry_price,
            estimated_prob=estimate.ensemble_probability,
            confidence=estimate.confidence
        )
        
        if kelly_result.position_size <= 0 or kelly_result.position_size > available_capital * 0.2:
            continue
        
        position_size = min(kelly_result.position_size, available_capital)
        
        # Determine exit
        if use_take_profit:
            tp_level = calculate_take_profit(
                entry_price=entry_price,
                estimated_prob=estimate.ensemble_probability,
                side=kelly_result.side
            )
            
            if tp_level and tp_level.is_reachable:
                # Check if TP is hit before resolution
                tp_hit = False
                exit_price = exit_data['price']
                exit_time = exit_data['timestamp']
                exit_reason = 'resolution'
                
                for data in market_data[1:]:
                    if check_take_profit_hit(entry_price, data['price'], tp_level, kelly_result.side):
                        exit_price = tp_level.target_price
                        exit_time = data['timestamp']
                        exit_reason = 'tp'
                        tp_hit = True
                        break
                
                # Calculate P&L
                if kelly_result.side == 'YES':
                    shares = position_size / entry_price
                    if exit_reason == 'tp':
                        pnl = (exit_price - entry_price) * shares
                    else:
                        pnl = (actual_outcome - entry_price) * shares
                else:  # NO
                    no_entry = 1 - entry_price
                    shares = position_size / no_entry
                    no_exit = 1 - exit_price
                    if exit_reason == 'tp':
                        pnl = (no_entry - no_exit) * shares
                    else:
                        pnl = ((1 - actual_outcome) - no_entry) * shares
                
                holding_days = calculate_holding_days(entry_data['timestamp'], exit_time)
                
                trade = {
                    'market_slug': slug,
                    'side': kelly_result.side,
                    'entry_price': entry_price,
                    'position_size': position_size,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'exit_reason': exit_reason,
                    'holding_days': holding_days,
                    'tp_hit': tp_hit
                }
                
                trades.append(trade)
                
                # Block capital until exit
                available_capital -= position_size
                # Use tuple with counter to avoid comparison issues
                heapq.heappush(pending_positions, (exit_time, len(trades), position_size, pnl))
                
                continue  # Position opened
        
        # Baseline: Hold to resolution
        shares = position_size / entry_price if kelly_result.side == 'YES' else position_size / (1 - entry_price)
        
        if kelly_result.side == 'YES':
            pnl = (actual_outcome - entry_price) * shares
        else:
            pnl = ((1 - actual_outcome) - (1 - entry_price)) * shares
        
        holding_days = calculate_holding_days(entry_data['timestamp'], exit_data['timestamp'])
        
        trade = {
            'market_slug': slug,
            'side': kelly_result.side,
            'entry_price': entry_price,
            'position_size': position_size,
            'exit_price': exit_data['price'],
            'pnl': pnl,
            'exit_reason': 'resolution',
            'holding_days': holding_days,
            'tp_hit': False
        }
        
        trades.append(trade)
        
        # Block capital until resolution
        available_capital -= position_size
        # Use tuple with counter to avoid comparison issues
        heapq.heappush(pending_positions, (exit_data['timestamp'], len(trades), position_size, pnl))
    
    # Close any remaining positions
    while pending_positions:
        exit_time, _, position_size, pnl = heapq.heappop(pending_positions)
        available_capital += position_size + pnl
    
    # Calculate results
    final_bankroll = initial_bankroll + sum(t['pnl'] for t in trades)
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t['pnl'] > 0)
    tp_exits = sum(1 for t in trades if t['exit_reason'] == 'tp')
    
    avg_holding = sum(t['holding_days'] for t in trades) / total_trades if total_trades > 0 else 0
    
    results = {
        'strategy': 'take_profit' if use_take_profit else 'baseline',
        'initial_bankroll': initial_bankroll,
        'final_bankroll': final_bankroll,
        'total_pnl': final_bankroll - initial_bankroll,
        'total_pnl_pct': ((final_bankroll - initial_bankroll) / initial_bankroll) * 100,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': total_trades - winning_trades,
        'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
        'tp_exits': tp_exits,
        'resolution_exits': total_trades - tp_exits,
        'tp_hit_rate': tp_exits / total_trades if total_trades > 0 else 0,
        'avg_holding_days': avg_holding,
        'trades': trades
    }
    
    if verbose:
        print(f"\n📊 Results:")
        print(f"  Total Trades: {total_trades}")
        print(f"  Final Bankroll: ${final_bankroll:,.2f}")
        print(f"  Total P&L: ${results['total_pnl']:+,.2f} ({results['total_pnl_pct']:+.1f}%)")
        print(f"  Win Rate: {results['win_rate']:.1%}")
        print(f"  TP Exits: {tp_exits} ({results['tp_hit_rate']:.1%})")
        print(f"  Avg Holding: {avg_holding:.1f} days")
    
    return results


def compare_with_capital_recycling(data_path: str, bankroll: float = 1000, min_edge: float = 0.05):
    """Run proper comparison with capital recycling"""
    
    from utils.backtest import BacktestEngine
    
    print("=" * 80)
    print("🔄 CAPITAL RECYCLING COMPARISON")
    print("=" * 80)
    
    # Load data
    path = Path(data_path)
    if path.suffix == '.parquet':
        historical_data = BacktestEngine.load_from_parquet(path)
    else:
        with open(path, 'r') as f:
            historical_data = json.load(f)
    
    print(f"\nLoaded {len(historical_data)} data points")
    
    # Run baseline (no capital recycling simulation needed - it takes all trades)
    print("\n" + "-" * 80)
    print("📈 BASELINE (Hold to Resolution)")
    print("-" * 80)
    baseline_results = simulate_capital_recycling(
        historical_data,
        initial_bankroll=bankroll,
        min_edge=min_edge,
        use_take_profit=False,
        verbose=True
    )
    
    # Run TP strategy
    print("\n" + "-" * 80)
    print("🎯 75% EDGE RULE (Capital Recycling)")
    print("-" * 80)
    tp_results = simulate_capital_recycling(
        historical_data,
        initial_bankroll=bankroll,
        min_edge=min_edge,
        use_take_profit=True,
        verbose=True
    )
    
    # Comparison
    print("\n" + "=" * 80)
    print("📊 COMPARISON")
    print("=" * 80)
    print(f"\n{'Metric':<30} {'Baseline':<15} {'TP Strategy':<15} {'Delta':<15}")
    print("-" * 80)
    print(f"{'Total Trades':<30} {baseline_results['total_trades']:<15} {tp_results['total_trades']:<15} {tp_results['total_trades'] - baseline_results['total_trades']:+d}")
    print(f"{'Final Bankroll':<30} ${baseline_results['final_bankroll']:>13,.2f} ${tp_results['final_bankroll']:>13,.2f} ${tp_results['final_bankroll'] - baseline_results['final_bankroll']:+,.2f}")
    print(f"{'Total P&L (%)':<30} {baseline_results['total_pnl_pct']:>13.1f}% {tp_results['total_pnl_pct']:>13.1f}% {(tp_results['total_pnl_pct'] - baseline_results['total_pnl_pct']):>+13.1f}%")
    print(f"{'Win Rate':<30} {baseline_results['win_rate']*100:>13.1f}% {tp_results['win_rate']*100:>13.1f}% {(tp_results['win_rate'] - baseline_results['win_rate'])*100:>+13.1f}%")
    print(f"{'Avg Holding Days':<30} {baseline_results['avg_holding_days']:>13.1f} {tp_results['avg_holding_days']:>13.1f} {(tp_results['avg_holding_days'] - baseline_results['avg_holding_days']):>+13.1f}")
    print(f"{'TP Hit Rate':<30} {'N/A':<15} {tp_results['tp_hit_rate']*100:>13.1f}% {'-':<15}")
    
    # Key insight
    if tp_results['total_trades'] > baseline_results['total_trades']:
        extra_trades = tp_results['total_trades'] - baseline_results['total_trades']
        print(f"\n💡 KEY INSIGHT:")
        print(f"   TP strategy made {extra_trades} MORE trades due to capital recycling!")
        print(f"   This is the true advantage of faster capital turnover.")
    
    print("=" * 80)
    
    return baseline_results, tp_results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Capital Recycling Simulation')
    parser.add_argument('--data', required=True, help='Path to historical data')
    parser.add_argument('--bankroll', type=float, default=1000, help='Initial bankroll')
    parser.add_argument('--min-edge', type=float, default=0.05, help='Minimum edge')
    
    args = parser.parse_args()
    
    compare_with_capital_recycling(args.data, args.bankroll, args.min_edge)
