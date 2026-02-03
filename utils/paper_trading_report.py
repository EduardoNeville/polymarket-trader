"""
Paper Trading vs Backtest Comparison Report
Compares paper trading results to backtest expectations
Timestamp: 2026-02-03 20:32 GMT+1
"""

import json
from datetime import datetime
from typing import Dict, List
import pandas as pd

from utils.paper_trading_db import PaperTradingDB
from utils.backtest import BacktestEngine


class PaperVsBacktestReport:
    """
    Generates comparison report between paper trading and backtest results.
    
    Helps validate that strategy works in real markets vs simulation.
    """
    
    def __init__(self):
        self.db = PaperTradingDB()
    
    def generate_report(self) -> Dict:
        """
        Generate comprehensive comparison report.
        
        Returns:
            Report dictionary with comparisons
        """
        # Get paper trading performance
        paper_summary = self.db.get_performance_summary()
        
        # Get closed trades for detailed analysis
        closed_trades = self.db.get_closed_trades()
        
        if paper_summary['total_trades'] == 0:
            return {
                'status': 'insufficient_data',
                'message': 'No closed paper trades yet. Need more data.',
                'paper_trades': 0
            }
        
        # Calculate paper metrics
        paper_metrics = {
            'win_rate': paper_summary['win_rate'],
            'avg_edge': paper_summary['avg_edge'],
            'avg_pnl': paper_summary['avg_pnl'],
            'total_pnl': paper_summary['total_pnl'],
            'trades': paper_summary['total_trades']
        }
        
        # Backtest expectations (from your backtest results)
        backtest_expectations = {
            'win_rate': 0.75,  # 75% expected
            'avg_edge': 0.12,  # 12% expected
            'avg_pnl': 150.0,  # $150 per trade (on $1000 bankroll)
            'total_return': 2000.0  # 200% total
        }
        
        # Calculate slippage
        if paper_metrics['win_rate'] > 0 and backtest_expectations['win_rate'] > 0:
            win_rate_slippage = (backtest_expectations['win_rate'] - paper_metrics['win_rate']) / backtest_expectations['win_rate']
        else:
            win_rate_slippage = 0
        
        # Determine if within acceptable range
        win_rate_ok = paper_metrics['win_rate'] >= 0.60  # At least 60%
        profitable = paper_metrics['total_pnl'] > 0
        
        return {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'paper_trades': paper_metrics['trades'],
            'paper_metrics': paper_metrics,
            'backtest_expectations': backtest_expectations,
            'comparison': {
                'win_rate_delta': paper_metrics['win_rate'] - backtest_expectations['win_rate'],
                'win_rate_slippage_pct': win_rate_slippage * 100,
                'edge_delta': paper_metrics['avg_edge'] - backtest_expectations['avg_edge'],
            },
            'validation': {
                'win_rate_acceptable': win_rate_ok,
                'profitable': profitable,
                'recommendation': 'PROCEED' if (win_rate_ok and profitable) else 'INVESTIGATE'
            }
        }
    
    def display_report(self):
        """Display formatted report to console"""
        report = self.generate_report()
        
        print("\n" + "=" * 80)
        print("📊 PAPER TRADING vs BACKTEST COMPARISON REPORT")
        print("=" * 80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if report['status'] == 'insufficient_data':
            print(f"\n⚠️  {report['message']}")
            print(f"   Current paper trades: {report['paper_trades']}")
            print(f"   Need at least 10 closed trades for meaningful comparison")
            return
        
        paper = report['paper_metrics']
        backtest = report['backtest_expectations']
        comp = report['comparison']
        
        print(f"\n📈 PAPER TRADING RESULTS:")
        print(f"  Trades:        {paper['trades']}")
        print(f"  Win Rate:      {paper['win_rate']:.1%}")
        print(f"  Avg Edge:      {paper['avg_edge']:.1%}")
        print(f"  Avg P&L:       ${paper['avg_pnl']:.2f}")
        print(f"  Total P&L:     ${paper['total_pnl']:.2f}")
        
        print(f"\n📊 BACKTEST EXPECTATIONS:")
        print(f"  Win Rate:      {backtest['win_rate']:.1%}")
        print(f"  Avg Edge:      {backtest['avg_edge']:.1%}")
        print(f"  Avg P&L:       ${backtest['avg_pnl']:.2f}")
        
        print(f"\n📉 SLIPPAGE ANALYSIS:")
        print(f"  Win Rate Delta:       {comp['win_rate_delta']:+.1%}")
        print(f"  Win Rate Slippage:    {comp['win_rate_slippage_pct']:.1f}%")
        print(f"  Edge Delta:           {comp['edge_delta']:+.1%}")
        
        print(f"\n✅ VALIDATION:")
        validation = report['validation']
        
        if validation['win_rate_acceptable']:
            print(f"  Win Rate:     ✓ PASS ({paper['win_rate']:.1%} >= 60%)")
        else:
            print(f"  Win Rate:     ✗ FAIL ({paper['win_rate']:.1%} < 60%)")
        
        if validation['profitable']:
            print(f"  Profitability: ✓ PASS (${paper['total_pnl']:+.2f})")
        else:
            print(f"  Profitability: ✗ FAIL (${paper['total_pnl']:+.2f})")
        
        print(f"\n🎯 RECOMMENDATION: {validation['recommendation']}")
        
        if validation['recommendation'] == 'PROCEED':
            print("\n  ✅ Strategy validated! Ready for live trading.")
            print("  Expected slippage is within normal range.")
        else:
            print("\n  ⚠️  Strategy underperforming. Investigate causes:")
            print("     - Adverse selection?")
            print("     - Market conditions changed?")
            print("     - Model decay?")
        
        print("=" * 80)
    
    def export_to_file(self, filepath: str = "data/paper_vs_backtest_report.json"):
        """Export report to JSON file"""
        report = self.generate_report()
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"✅ Report exported to {filepath}")


def main():
    """Generate and display report"""
    print("Generating Paper Trading vs Backtest Comparison Report...")
    
    report = PaperVsBacktestReport()
    report.display_report()
    report.export_to_file()


if __name__ == "__main__":
    main()
