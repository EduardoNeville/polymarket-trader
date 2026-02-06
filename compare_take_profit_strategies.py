#!/usr/bin/env python3
"""
Compare Hold-to-Resolution vs 50% Edge Rule Take-Profit Strategy

This script runs the same backtest data with both strategies and generates
a comprehensive comparison report.

Usage:
    python3 compare_take_profit_strategies.py --data data/resolved_markets.parquet
    python3 compare_take_profit_strategies.py --data data/resolved_markets.json --min-edge 0.05
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent))

from utils.backtest import BacktestEngine, BacktestResult
from utils.market_data import fetch_resolved_backtest_data


def load_historical_data(data_path: str) -> List[Dict]:
    """Load historical data from Parquet or JSON file"""
    path = Path(data_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    if path.suffix == '.parquet':
        return BacktestEngine.load_from_parquet(path)
    elif path.suffix == '.json':
        with open(path, 'r') as f:
            return json.load(f)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}. Use .parquet or .json")


def calculate_capital_turns(avg_holding_days: float) -> float:
    """Calculate capital turns per year"""
    if avg_holding_days <= 0:
        return 0.0
    return 365.0 / avg_holding_days


def compare_strategies(
    data_path: str,
    min_edge: float = 0.05,
    strategy: str = 'ensemble',
    bankroll: float = 10000,
    output_path: Optional[str] = None,
    verbose: bool = True
) -> Dict:
    """
    Run comparison between baseline and take-profit strategies.
    
    Returns:
        Dict with comparison metrics and results
    """
    # Load data
    if verbose:
        print(f"\n📊 Loading historical data from {data_path}...")
    
    historical_data = load_historical_data(data_path)
    
    if verbose:
        print(f"   Loaded {len(historical_data)} data points")
    
    # Count unique markets
    unique_markets = len(set(d['market_slug'] for d in historical_data))
    if verbose:
        print(f"   {unique_markets} unique markets")
    
    # Run baseline (hold to resolution)
    if verbose:
        print("\n" + "=" * 80)
        print("📈 Running BASELINE Strategy (Hold to Resolution)")
        print("=" * 80)
    
    baseline_engine = BacktestEngine(initial_bankroll=bankroll)
    baseline_result = baseline_engine.run_backtest(
        historical_data,
        strategy=strategy,
        min_edge=min_edge,
        use_take_profit=False,
        verbose=verbose
    )
    
    # Run with take-profit
    if verbose:
        print("\n" + "=" * 80)
        print("🎯 Running 50% EDGE RULE Strategy (Take-Profit)")
        print("=" * 80)
    
    tp_engine = BacktestEngine(initial_bankroll=bankroll)
    tp_result = tp_engine.run_backtest(
        historical_data,
        strategy=strategy,
        min_edge=min_edge,
        use_take_profit=True,
        verbose=verbose
    )
    
    # Calculate comparison metrics
    comparison = calculate_comparison_metrics(
        baseline_result, 
        tp_result,
        verbose=verbose
    )
    
    # Generate report
    if verbose:
        generate_comparison_report(comparison, output_path)
    
    return comparison


def calculate_comparison_metrics(
    baseline: BacktestResult,
    tp: BacktestResult,
    verbose: bool = True
) -> Dict:
    """Calculate detailed comparison metrics between strategies"""
    
    # Basic metrics
    pnl_delta = tp.total_pnl - baseline.total_pnl
    pnl_delta_pct = (pnl_delta / baseline.total_pnl * 100) if baseline.total_pnl != 0 else 0
    
    win_rate_delta = tp.win_rate - baseline.win_rate
    
    holding_days_delta = tp.avg_holding_days - baseline.avg_holding_days
    holding_days_pct = (holding_days_delta / baseline.avg_holding_days * 100) if baseline.avg_holding_days > 0 else 0
    
    # Capital turnover
    baseline_turns = calculate_capital_turns(baseline.avg_holding_days)
    tp_turns = calculate_capital_turns(tp.avg_holding_days)
    turns_delta = tp_turns - baseline_turns
    turns_pct = (turns_delta / baseline_turns * 100) if baseline_turns > 0 else 0
    
    # Risk metrics
    sharpe_delta = tp.sharpe_ratio - baseline.sharpe_ratio
    drawdown_delta = tp.max_drawdown_pct - baseline.max_drawdown_pct
    
    comparison = {
        'timestamp': datetime.now().isoformat(),
        'baseline': {
            'total_trades': baseline.total_trades,
            'total_pnl': baseline.total_pnl,
            'total_pnl_pct': baseline.total_pnl_pct,
            'win_rate': baseline.win_rate,
            'sharpe_ratio': baseline.sharpe_ratio,
            'max_drawdown_pct': baseline.max_drawdown_pct,
            'avg_holding_days': baseline.avg_holding_days,
            'capital_turns_per_year': baseline_turns,
            'tp_exit_count': baseline.tp_exit_count,
            'resolution_exit_count': baseline.resolution_exit_count,
        },
        'take_profit': {
            'total_trades': tp.total_trades,
            'total_pnl': tp.total_pnl,
            'total_pnl_pct': tp.total_pnl_pct,
            'win_rate': tp.win_rate,
            'sharpe_ratio': tp.sharpe_ratio,
            'max_drawdown_pct': tp.max_drawdown_pct,
            'avg_holding_days': tp.avg_holding_days,
            'capital_turns_per_year': tp_turns,
            'tp_exit_count': tp.tp_exit_count,
            'resolution_exit_count': tp.resolution_exit_count,
            'tp_hit_rate': tp.tp_hit_rate,
        },
        'deltas': {
            'pnl_absolute': pnl_delta,
            'pnl_percentage': pnl_delta_pct,
            'win_rate': win_rate_delta,
            'avg_holding_days': holding_days_delta,
            'holding_days_percentage': holding_days_pct,
            'capital_turns': turns_delta,
            'capital_turns_percentage': turns_pct,
            'sharpe_ratio': sharpe_delta,
            'max_drawdown_pct': drawdown_delta,
        },
        'validation': {
            'tp_hit_rate_target_met': 0.15 <= tp.tp_hit_rate <= 0.35,  # 15-35% is healthy
            'holding_time_reduced': tp.avg_holding_days < baseline.avg_holding_days,
            'capital_turns_improved': tp_turns > baseline_turns,
        }
    }
    
    return comparison


def generate_comparison_report(comparison: Dict, output_path: Optional[str] = None):
    """Generate formatted comparison report"""
    
    baseline = comparison['baseline']
    tp = comparison['take_profit']
    deltas = comparison['deltas']
    validation = comparison['validation']
    
    print("\n" + "=" * 80)
    print("📊 STRATEGY COMPARISON REPORT")
    print("=" * 80)
    
    # Header
    print(f"\nGenerated: {comparison['timestamp']}")
    
    # Summary Table
    print("\n" + "-" * 80)
    print(f"{'Metric':<30} {'Baseline':<15} {'50% Edge Rule':<15} {'Delta':<15}")
    print("-" * 80)
    
    # P&L metrics
    print(f"{'Total Trades':<30} {baseline['total_trades']:<15} {tp['total_trades']:<15} {'-':<15}")
    print(f"{'Total P&L ($)':<30} ${baseline['total_pnl']:+>13.2f} ${tp['total_pnl']:+>13.2f} ${deltas['pnl_absolute']:+>13.2f}")
    print(f"{'Total P&L (%)':<30} {baseline['total_pnl_pct']:+>13.2f}% {tp['total_pnl_pct']:+>13.2f}% {deltas['pnl_percentage']:+>13.2f}%")
    print(f"{'Win Rate':<30} {baseline['win_rate']*100:>13.1f}% {tp['win_rate']*100:>13.1f}% {deltas['win_rate']*100:+>13.1f}%")
    
    print("-" * 80)
    
    # Holding time metrics
    print(f"{'Avg Holding Days':<30} {baseline['avg_holding_days']:>13.1f} {tp['avg_holding_days']:>13.1f} {deltas['avg_holding_days']:+>13.1f}")
    print(f"{'Capital Turns/Year':<30} {baseline['capital_turns_per_year']:>13.1f} {tp['capital_turns_per_year']:>13.1f} {deltas['capital_turns']:+>13.1f}")
    print(f"{'Capital Turns Change':<30} {'-':<15} {'-':<15} {deltas['capital_turns_percentage']:+>13.1f}%")
    
    print("-" * 80)
    
    # Risk metrics
    print(f"{'Sharpe Ratio':<30} {baseline['sharpe_ratio']:>13.2f} {tp['sharpe_ratio']:>13.2f} {deltas['sharpe_ratio']:+>13.2f}")
    print(f"{'Max Drawdown (%)':<30} {baseline['max_drawdown_pct']:>13.2f}% {tp['max_drawdown_pct']:>13.2f}% {deltas['max_drawdown_pct']:+>13.2f}%")
    
    print("-" * 80)
    
    # Take-profit metrics
    print(f"{'TP Exits':<30} {baseline['tp_exit_count']:<15} {tp['tp_exit_count']:<15} {'-':<15}")
    print(f"{'Resolution Exits':<30} {baseline['resolution_exit_count']:<15} {tp['resolution_exit_count']:<15} {'-':<15}")
    print(f"{'TP Hit Rate':<30} {'N/A':<15} {tp['tp_hit_rate']*100:>13.1f}% {'-':<15}")
    
    print("=" * 80)
    
    # Validation Section
    print("\n✅ VALIDATION CHECKS")
    print("-" * 80)
    
    # TP hit rate check
    tp_rate = tp['tp_hit_rate'] * 100
    tp_rate_ok = 15 <= tp_rate <= 35
    status = "✅ PASS" if tp_rate_ok else "⚠️  WARN"
    print(f"{status} TP Hit Rate: {tp_rate:.1f}% (target: 15-35%)")
    
    # Holding time check
    holding_ok = validation['holding_time_reduced']
    status = "✅ PASS" if holding_ok else "⚠️  WARN"
    print(f"{status} Holding Time Reduced: {baseline['avg_holding_days']:.1f} → {tp['avg_holding_days']:.1f} days")
    
    # Capital turns check
    turns_ok = validation['capital_turns_improved']
    status = "✅ PASS" if turns_ok else "⚠️  WARN"
    print(f"{status} Capital Turns Improved: {baseline['capital_turns_per_year']:.1f} → {tp['capital_turns_per_year']:.1f}/year")
    
    # P&L check
    pnl_ok = deltas['pnl_absolute'] >= -50  # Allow small loss
    status = "✅ PASS" if pnl_ok else "⚠️  WARN"
    print(f"{status} P&L Impact: ${deltas['pnl_absolute']:+.2f}")
    
    print("=" * 80)
    
    # Key Insights
    print("\n💡 KEY INSIGHTS")
    print("-" * 80)
    
    if deltas['capital_turns'] > 0:
        print(f"• Capital recycles {deltas['capital_turns']:.1f}x faster ({deltas['capital_turns_percentage']:.0f}% improvement)")
    
    if deltas['win_rate'] > 0:
        print(f"• Win rate improved by {deltas['win_rate']*100:.1f} percentage points")
    
    if deltas['avg_holding_days'] < 0:
        print(f"• Average holding time reduced by {abs(deltas['avg_holding_days']):.1f} days")
    
    if tp['tp_hit_rate'] > 0:
        print(f"• {tp['tp_hit_rate']*100:.1f}% of trades exited via take-profit")
    
    if deltas['sharpe_ratio'] > 0:
        print(f"• Sharpe ratio improved by {deltas['sharpe_ratio']:.2f}")
    
    print("=" * 80)
    
    # Save to file if requested
    if output_path:
        save_comparison_json(comparison, output_path)


def save_comparison_json(comparison: Dict, output_path: str):
    """Save comparison results to JSON file"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(comparison, f, indent=2, default=str)
    
    print(f"\n💾 Comparison results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Compare Hold-to-Resolution vs 50% Edge Rule Take-Profit Strategy'
    )
    parser.add_argument(
        '--data',
        required=True,
        help='Path to historical data file (.parquet or .json)'
    )
    parser.add_argument(
        '--min-edge',
        type=float,
        default=0.05,
        help='Minimum edge threshold (default: 0.05 = 5%)'
    )
    parser.add_argument(
        '--strategy',
        default='ensemble',
        help='Strategy to use (default: ensemble)'
    )
    parser.add_argument(
        '--bankroll',
        type=float,
        default=10000,
        help='Initial bankroll (default: 10000)'
    )
    parser.add_argument(
        '--output',
        help='Output JSON file path for detailed results'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress console output'
    )
    
    args = parser.parse_args()
    
    # Run comparison
    try:
        comparison = compare_strategies(
            data_path=args.data,
            min_edge=args.min_edge,
            strategy=args.strategy,
            bankroll=args.bankroll,
            output_path=args.output,
            verbose=not args.quiet
        )
        
        if not args.quiet:
            print("\n✅ Comparison complete!")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
