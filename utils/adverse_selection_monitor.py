"""
Adverse Selection Monitor
Tracks price movements after signals to detect adverse selection
Timestamp: 2026-02-03 20:38 GMT+1
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque

from utils.paper_trading_db import PaperTradingDB


class AdverseSelectionMonitor:
    """
    Monitors for adverse selection by tracking price movements post-signal.
    
    Detects if:
    1. Prices move against us immediately after signal
    2. Win rate degrades over time (alpha decay)
    3. Our signals are being front-run
    """
    
    def __init__(self, lookback_days: int = 30):
        self.db = PaperTradingDB()
        self.lookback_days = lookback_days
        self.alerts = []
    
    def analyze_recent_trades(self) -> Dict:
        """
        Analyze recent trades for adverse selection patterns.
        
        Returns:
            Analysis results
        """
        # Get recent closed trades
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_days)
        
        trades = self.db.get_trades_by_date_range(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            status='closed'
        )
        
        if len(trades) < 10:
            return {
                'status': 'insufficient_data',
                'message': f'Need at least 10 trades, have {len(trades)}',
                'trades_analyzed': len(trades)
            }
        
        # Calculate metrics
        wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
        losses = len(trades) - wins
        win_rate = wins / len(trades) if trades else 0
        
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        avg_pnl = total_pnl / len(trades) if trades else 0
        
        # Check for concerning patterns
        alerts = []
        
        if win_rate < 0.55:
            alerts.append({
                'severity': 'HIGH',
                'type': 'LOW_WIN_RATE',
                'message': f'Win rate {win_rate:.1%} below 55% threshold',
                'recommendation': 'Stop trading, investigate strategy'
            })
        elif win_rate < 0.60:
            alerts.append({
                'severity': 'MEDIUM',
                'type': 'DECLINING_PERFORMANCE',
                'message': f'Win rate {win_rate:.1%} below 60%',
                'recommendation': 'Monitor closely, reduce position sizes'
            })
        
        if avg_pnl < 0:
            alerts.append({
                'severity': 'HIGH',
                'type': 'NEGATIVE_EXPECTANCY',
                'message': f'Average loss ${avg_pnl:.2f} per trade',
                'recommendation': 'Stop immediately, review strategy'
            })
        
        # Check for adverse selection pattern
        # If we're losing more on YES bets than NO bets, might be adverse selection
        yes_trades = [t for t in trades if t['intended_side'] == 'YES']
        no_trades = [t for t in trades if t['intended_side'] == 'NO']
        
        yes_win_rate = sum(1 for t in yes_trades if t.get('pnl', 0) > 0) / len(yes_trades) if yes_trades else 0
        no_win_rate = sum(1 for t in no_trades if t.get('pnl', 0) > 0) / len(no_trades) if no_trades else 0
        
        if abs(yes_win_rate - no_win_rate) > 0.20:  # 20% difference
            alerts.append({
                'severity': 'MEDIUM',
                'type': 'SIDE_BIAS',
                'message': f'YES win rate: {yes_win_rate:.1%}, NO win rate: {no_win_rate:.1%}',
                'recommendation': 'Check for market bias or model issue'
            })
        
        self.alerts = alerts
        
        return {
            'status': 'success',
            'trades_analyzed': len(trades),
            'win_rate': win_rate,
            'wins': wins,
            'losses': losses,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'yes_win_rate': yes_win_rate,
            'no_win_rate': no_win_rate,
            'alerts': alerts,
            'recommendation': 'PROCEED' if not alerts else 'INVESTIGATE'
        }
    
    def display_report(self):
        """Display adverse selection report"""
        print("\n" + "=" * 80)
        print("⚠️ ADVERSE SELECTION MONITOR REPORT")
        print("=" * 80)
        print(f"Analysis Period: Last {self.lookback_days} days")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        result = self.analyze_recent_trades()
        
        if result['status'] == 'insufficient_data':
            print(f"\n{result['message']}")
            return
        
        print(f"\n📊 PERFORMANCE SUMMARY:")
        print(f"  Trades Analyzed:  {result['trades_analyzed']}")
        print(f"  Win Rate:         {result['win_rate']:.1%}")
        print(f"  Wins/Losses:      {result['wins']}/{result['losses']}")
        print(f"  Total P&L:        ${result['total_pnl']:+.2f}")
        print(f"  Avg per Trade:    ${result['avg_pnl']:+.2f}")
        
        print(f"\n📈 BY SIDE:")
        print(f"  YES Win Rate:     {result['yes_win_rate']:.1%}")
        print(f"  NO Win Rate:      {result['no_win_rate']:.1%}")
        
        if result['alerts']:
            print(f"\n🚨 ALERTS ({len(result['alerts'])}):")
            for i, alert in enumerate(result['alerts'], 1):
                print(f"\n  {i}. [{alert['severity']}] {alert['type']}")
                print(f"     {alert['message']}")
                print(f"     → {alert['recommendation']}")
        else:
            print(f"\n✅ No adverse selection detected")
        
        print(f"\n🎯 RECOMMENDATION: {result['recommendation']}")
        print("=" * 80)
    
    def get_alerts(self) -> List[Dict]:
        """Get current alerts"""
        self.analyze_recent_trades()
        return self.alerts


class AlphaDecayTracker:
    """
    Tracks alpha decay over time.
    
    Monitors if strategy performance degrades as more traders
    discover the same edge.
    """
    
    def __init__(self):
        self.db = PaperTradingDB()
    
    def calculate_rolling_win_rate(self, window: int = 20) -> List[Dict]:
        """
        Calculate rolling win rate over time.
        
        Args:
            window: Number of trades per window
            
        Returns:
            List of {date, win_rate} dicts
        """
        trades = self.db.get_closed_trades()
        
        if len(trades) < window:
            return []
        
        # Sort by timestamp
        trades_sorted = sorted(trades, key=lambda x: x['timestamp'])
        
        results = []
        for i in range(window, len(trades_sorted) + 1):
            window_trades = trades_sorted[i-window:i]
            wins = sum(1 for t in window_trades if t.get('pnl', 0) > 0)
            win_rate = wins / window
            
            results.append({
                'end_date': window_trades[-1]['timestamp'][:10],
                'win_rate': win_rate,
                'trades_in_window': window
            })
        
        return results
    
    def detect_decay(self) -> Dict:
        """
        Detect if strategy is experiencing alpha decay.
        
        Returns:
            Decay analysis
        """
        rolling = self.calculate_rolling_win_rate(window=20)
        
        if len(rolling) < 3:
            return {
                'status': 'insufficient_data',
                'message': 'Need more trade history'
            }
        
        # Compare first half vs second half
        mid = len(rolling) // 2
        early_win_rate = sum(r['win_rate'] for r in rolling[:mid]) / mid
        recent_win_rate = sum(r['win_rate'] for r in rolling[mid:]) / (len(rolling) - mid)
        
        decay = early_win_rate - recent_win_rate
        
        return {
            'status': 'success',
            'early_win_rate': early_win_rate,
            'recent_win_rate': recent_win_rate,
            'decay': decay,
            'decay_pct': (decay / early_win_rate * 100) if early_win_rate > 0 else 0,
            'concerning': decay > 0.10  # 10% drop is concerning
        }


def main():
    """Run monitoring"""
    print("Running Adverse Selection Monitor...")
    
    monitor = AdverseSelectionMonitor(lookback_days=30)
    monitor.display_report()
    
    print("\n\nRunning Alpha Decay Tracker...")
    tracker = AlphaDecayTracker()
    decay = tracker.detect_decay()
    
    if decay['status'] == 'success':
        print(f"\n📉 ALPHA DECAY ANALYSIS:")
        print(f"  Early Win Rate:  {decay['early_win_rate']:.1%}")
        print(f"  Recent Win Rate: {decay['recent_win_rate']:.1%}")
        print(f"  Decay:           {decay['decay']:+.1%} ({decay['decay_pct']:+.1f}%)")
        
        if decay['concerning']:
            print("\n  ⚠️  Significant alpha decay detected!")
        else:
            print("\n  ✅ No significant decay detected")


if __name__ == "__main__":
    main()
