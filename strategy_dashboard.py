#!/usr/bin/env python3
"""
Strategy Comparison Dashboard
Tracks and compares performance of all 3 paper trading strategies
"""

import sys
sys.path.insert(0, '/home/eduardoneville/projects/polymarket-trader')

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict

from utils.paper_trading_db import PaperTradingDB


@dataclass
class StrategyMetrics:
    """Metrics for a single strategy"""
    name: str
    db_path: str
    bankroll: float
    open_trades: int
    closed_trades: int
    exposure: float
    available: float
    avg_edge: float
    avg_holding_days: Optional[float]
    total_pnl: float
    win_rate: float
    win_count: int
    loss_count: int
    tp_exits: int
    sl_exits: int
    resolution_exits: int
    tp_pnl: float
    sl_pnl: float
    resolution_pnl: float
    avg_position_size: float
    capital_turnover: float
    

def calculate_strategy_metrics(name: str, db_path: str, bankroll: float = 1000) -> StrategyMetrics:
    """Calculate all metrics for a strategy"""
    db = PaperTradingDB(db_path=db_path)
    
    open_trades = db.get_open_trades()
    closed_trades = db.get_closed_trades()
    
    exposure = sum(t.get('intended_size', 0) for t in open_trades)
    available = bankroll - exposure
    
    # Calculate edge stats
    edges = [t.get('edge', 0) for t in open_trades + closed_trades]
    avg_edge = sum(edges) / len(edges) if edges else 0
    
    # Calculate holding days
    holding_days = []
    for t in closed_trades:
        if t.get('holding_days') is not None:
            holding_days.append(t['holding_days'])
    avg_holding_days = sum(holding_days) / len(holding_days) if holding_days else None
    
    # Calculate P&L and win rate
    total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
    win_count = sum(1 for t in closed_trades if t.get('pnl', 0) > 0)
    loss_count = sum(1 for t in closed_trades if t.get('pnl', 0) <= 0)
    win_rate = win_count / len(closed_trades) if closed_trades else 0
    
    # Exit breakdown
    tp_exits = sum(1 for t in closed_trades if t.get('exit_reason') == 'tp')
    sl_exits = sum(1 for t in closed_trades if t.get('exit_reason') == 'stop_loss')
    resolution_exits = sum(1 for t in closed_trades if t.get('exit_reason') == 'resolution')
    
    tp_pnl = sum(t.get('pnl', 0) for t in closed_trades if t.get('exit_reason') == 'tp')
    sl_pnl = sum(t.get('pnl', 0) for t in closed_trades if t.get('exit_reason') == 'stop_loss')
    resolution_pnl = sum(t.get('pnl', 0) for t in closed_trades if t.get('exit_reason') == 'resolution')
    
    # Position size
    all_sizes = [t.get('intended_size', 0) for t in open_trades + closed_trades]
    avg_position_size = sum(all_sizes) / len(all_sizes) if all_sizes else 0
    
    # Capital turnover (total traded / bankroll)
    total_traded = sum(t.get('intended_size', 0) for t in closed_trades)
    capital_turnover = total_traded / bankroll if bankroll > 0 else 0
    
    return StrategyMetrics(
        name=name,
        db_path=db_path,
        bankroll=bankroll,
        open_trades=len(open_trades),
        closed_trades=len(closed_trades),
        exposure=exposure,
        available=available,
        avg_edge=avg_edge,
        avg_holding_days=avg_holding_days,
        total_pnl=total_pnl,
        win_rate=win_rate,
        win_count=win_count,
        loss_count=loss_count,
        tp_exits=tp_exits,
        sl_exits=sl_exits,
        resolution_exits=resolution_exits,
        tp_pnl=tp_pnl,
        sl_pnl=sl_pnl,
        resolution_pnl=resolution_pnl,
        avg_position_size=avg_position_size,
        capital_turnover=capital_turnover
    )


def print_dashboard(metrics_list: List[StrategyMetrics]):
    """Print formatted dashboard"""
    print("\n" + "=" * 100)
    print("📊 STRATEGY COMPARISON DASHBOARD".center(100))
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(100))
    print("=" * 100)
    
    # Portfolio Overview
    print("\n💰 PORTFOLIO OVERVIEW")
    print("-" * 100)
    print(f"{'Strategy':<20} {'Open':>6} {'Closed':>7} {'Exposure':>10} {'Avail':>10} {'Edge':>8}")
    print("-" * 100)
    
    for m in metrics_list:
        print(f"{m.name:<20} {m.open_trades:>6} {m.closed_trades:>7} "
              f"${m.exposure:>8.0f} ${m.available:>8.0f} {m.avg_edge:>7.1%}")
    
    # Performance Metrics
    print("\n📈 PERFORMANCE METRICS")
    print("-" * 100)
    print(f"{'Strategy':<20} {'Trades':>7} {'Win%':>7} {'Wins':>5} {'Loss':>5} "
          f"{'P&L':>10} {'Avg Pos':>8} {'Turnover':>9}")
    print("-" * 100)
    
    for m in metrics_list:
        pnl_str = f"${m.total_pnl:+.2f}"
        print(f"{m.name:<20} {m.closed_trades:>7} {m.win_rate:>7.1%} "
              f"{m.win_count:>5} {m.loss_count:>5} {pnl_str:>10} "
              f"${m.avg_position_size:>6.0f} {m.capital_turnover:>8.1f}x")
    
    # Exit Analysis
    print("\n🎯 EXIT ANALYSIS")
    print("-" * 100)
    print(f"{'Strategy':<20} {'TP':>5} {'SL':>5} {'Res':>5} {'TP P&L':>10} {'SL P&L':>10} {'Res P&L':>10}")
    print("-" * 100)
    
    for m in metrics_list:
        print(f"{m.name:<20} {m.tp_exits:>5} {m.sl_exits:>5} {m.resolution_exits:>5} "
              f"${m.tp_pnl:>+8.2f} ${m.sl_pnl:>+8.2f} ${m.resolution_pnl:>+8.2f}")
    
    # Holding Time
    print("\n⏱️  HOLDING TIME ANALYSIS")
    print("-" * 100)
    print(f"{'Strategy':<20} {'Avg Hold':>10} {'Min':>6} {'Max':>6}")
    print("-" * 100)
    
    for m in metrics_list:
        db = PaperTradingDB(db_path=m.db_path)
        closed = db.get_closed_trades()
        days = [t.get('holding_days') for t in closed if t.get('holding_days') is not None]
        
        if m.avg_holding_days is not None:
            print(f"{m.name:<20} {m.avg_holding_days:>9.1f}d {min(days) if days else 0:>5.0f} {max(days) if days else 0:>5.0f}")
        else:
            print(f"{m.name:<20} {'N/A (no closes)':>20}")
    
    # Ranking
    print("\n🏆 STRATEGY RANKINGS")
    print("-" * 100)
    
    # Rank by P&L
    ranked_by_pnl = sorted(metrics_list, key=lambda x: x.total_pnl, reverse=True)
    print("\nBy Total P&L:")
    for i, m in enumerate(ranked_by_pnl, 1):
        print(f"  {i}. {m.name}: ${m.total_pnl:+.2f}")
    
    # Rank by Win Rate (if enough trades)
    with_trades = [m for m in metrics_list if m.closed_trades >= 5]
    if with_trades:
        ranked_by_win = sorted(with_trades, key=lambda x: x.win_rate, reverse=True)
        print("\nBy Win Rate (min 5 trades):")
        for i, m in enumerate(ranked_by_win, 1):
            print(f"  {i}. {m.name}: {m.win_rate:.1%} ({m.win_count}/{m.closed_trades})")
    
    # Rank by Capital Efficiency
    ranked_by_turnover = sorted(metrics_list, key=lambda x: x.capital_turnover, reverse=True)
    print("\nBy Capital Turnover:")
    for i, m in enumerate(ranked_by_turnover, 1):
        print(f"  {i}. {m.name}: {m.capital_turnover:.2f}x")
    
    print("\n" + "=" * 100)


def export_to_json(metrics_list: List[StrategyMetrics], filepath: str = None):
    """Export metrics to JSON file"""
    if filepath is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = f"results/strategy_comparison_{timestamp}.json"
    
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        'timestamp': datetime.now().isoformat(),
        'strategies': [asdict(m) for m in metrics_list]
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    return filepath


def generate_report():
    """Generate complete comparison report"""
    strategies = [
        ("Strategy A (7-Day)", "data/paper_trading_strategy_a.db", 1000),
        ("Strategy B (Multipliers)", "data/paper_trading_strategy_b.db", 1000),
        ("Strategy C (Tiered)", "data/paper_trading_strategy_c.db", 1000),
        ("Original (Baseline)", "data/paper_trading.db", 1000),
    ]
    
    metrics_list = []
    for name, db_path, bankroll in strategies:
        try:
            metrics = calculate_strategy_metrics(name, db_path, bankroll)
            metrics_list.append(metrics)
        except Exception as e:
            print(f"❌ Error loading {name}: {e}")
    
    # Print dashboard
    print_dashboard(metrics_list)
    
    # Export to JSON
    try:
        filepath = export_to_json(metrics_list)
        print(f"\n✅ Report exported to: {filepath}")
    except Exception as e:
        print(f"\n❌ Export failed: {e}")
    
    return metrics_list


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'json':
        # Just export, don't print
        strategies = [
            ("Strategy A (7-Day)", "data/paper_trading_strategy_a.db", 1000),
            ("Strategy B (Multipliers)", "data/paper_trading_strategy_b.db", 1000),
            ("Strategy C (Tiered)", "data/paper_trading_strategy_c.db", 1000),
            ("Original (Baseline)", "data/paper_trading.db", 1000),
        ]
        
        metrics_list = []
        for name, db_path, bankroll in strategies:
            try:
                metrics = calculate_strategy_metrics(name, db_path, bankroll)
                metrics_list.append(metrics)
            except Exception as e:
                print(f"❌ Error loading {name}: {e}")
        
        filepath = export_to_json(metrics_list)
        print(f"Report exported to: {filepath}")
    else:
        # Full dashboard
        generate_report()
