"""
Paper Trading TP/SL Monitor
Monitors open paper trades for take-profit and stop-loss hits
Checks every 5 minutes
Timestamp: 2026-02-06
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

try:
    import schedule
    HAS_SCHEDULE = True
except ImportError:
    HAS_SCHEDULE = False

from utils.paper_trading_db import PaperTradingDB
from utils.take_profit_calculator import (
    TakeProfitLevel, StopLossLevel,
    check_take_profit_hit, check_stop_loss_hit,
    calculate_holding_days
)
from scanner import PolymarketScanner


class TPSLMonitor:
    """
    Monitors open paper trades for TP/SL hits.
    
    Features:
    - Polls open trades with TP/SL levels
    - Fetches current market prices
    - Detects TP/SL hits
    - Updates trades with exit info
    - Runs continuously every 5 minutes
    """
    
    def __init__(self, db_path: str = "data/paper_trading.db"):
        self.db = PaperTradingDB(db_path)
        self.scanner = PolymarketScanner()
        self.check_count = 0
        self.last_check_time = None
    
    def get_open_trades_with_tp_sl(self) -> List[Dict]:
        """Get all open trades that have TP levels set"""
        open_trades = self.db.get_open_trades()
        # Filter to trades with TP price set
        return [t for t in open_trades if t.get('take_profit_price') is not None]
    
    def fetch_current_prices(self, market_slugs: List[str], verbose: bool = True) -> Dict[str, float]:
        """
        Fetch current YES prices for markets.
        
        Returns:
            Dict mapping market_slug -> current yes_price
        """
        prices = {}
        
        try:
            # Fetch all active markets
            all_markets = self.scanner.get_active_markets(limit=500)
            
            # Create lookup by slug
            markets_by_slug = {m.slug: m for m in all_markets}
            
            for slug in market_slugs:
                market = markets_by_slug.get(slug)
                if market:
                    prices[slug] = market.yes_price
                else:
                    # Market might be closed/resolved
                    prices[slug] = None
                    
        except Exception as e:
            # Log error but don't crash - will retry next cycle
            if verbose:
                print(f"⚠️  Could not fetch prices (will retry): {e}")
        
        return prices
    
    def check_trade_exit(self, trade: Dict, current_price: float) -> Optional[Dict]:
        """
        Check if a trade has hit TP or SL.
        
        Args:
            trade: Trade dict from database
            current_price: Current YES price
        
        Returns:
            Dict with exit info if TP/SL hit, None otherwise
        """
        if current_price is None:
            return None
        
        side = trade['intended_side']
        entry_price = trade['intended_price']
        tp_price = trade.get('take_profit_price')
        
        # Reconstruct TP level
        if tp_price is None:
            return None
        
        tp_level = TakeProfitLevel(
            target_price=tp_price,
            target_pct_move=trade.get('take_profit_pct', 0),
            captured_edge=0,
            is_reachable=True,
            edge_capture_ratio=0.75,
            initial_edge=trade.get('edge', 0),
            entry_price=entry_price,
            side=side
        )
        
        # Check TP hit
        tp_hit = check_take_profit_hit(entry_price, current_price, tp_level, side)
        
        # Calculate SL price (50% risk default)
        sl_level = None
        if side == 'YES':
            sl_price = entry_price * 0.5  # 50% loss
        else:
            no_entry = 1 - entry_price
            no_sl = no_entry * 0.5
            sl_price = 1 - no_sl
        
        sl_hit = False
        if side == 'YES':
            sl_hit = current_price <= sl_price
        else:
            sl_hit = current_price >= sl_price
        
        # Determine exit
        if tp_hit:
            # Calculate P&L at TP price
            shares = trade['intended_size'] / entry_price if side == 'YES' else trade['intended_size'] / (1 - entry_price)
            
            if side == 'YES':
                pnl = (tp_price - entry_price) * shares
            else:
                no_entry = 1 - entry_price
                no_tp = 1 - tp_price
                pnl = (no_entry - no_tp) * shares
            
            holding_days = calculate_holding_days(
                trade['timestamp'],
                datetime.now().isoformat()
            )
            
            return {
                'exit_reason': 'tp',
                'exit_price': tp_price,
                'pnl': pnl,
                'holding_days': holding_days
            }
        
        elif sl_hit:
            # Calculate P&L at SL price
            shares = trade['intended_size'] / entry_price if side == 'YES' else trade['intended_size'] / (1 - entry_price)
            
            if side == 'YES':
                pnl = (sl_price - entry_price) * shares
            else:
                no_entry = 1 - entry_price
                no_sl = 1 - sl_price
                pnl = (no_entry - no_sl) * shares
            
            holding_days = calculate_holding_days(
                trade['timestamp'],
                datetime.now().isoformat()
            )
            
            return {
                'exit_reason': 'stop_loss',
                'exit_price': sl_price,
                'pnl': pnl,
                'holding_days': holding_days
            }
        
        return None
    
    def check_all_trades(self, verbose: bool = True) -> Dict:
        """
        Check all open trades for TP/SL hits.
        
        Returns:
            Summary of checks and exits
        """
        self.check_count += 1
        self.last_check_time = datetime.now()
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"🎯 TP/SL CHECK #{self.check_count} - {self.last_check_time.strftime('%H:%M:%S')}")
            print(f"{'='*70}")
        
        # Get open trades with TP
        trades = self.get_open_trades_with_tp_sl()
        
        if not trades:
            if verbose:
                print("No open trades with TP/SL to monitor")
            return {'checked': 0, 'tp_hits': 0, 'sl_hits': 0, 'errors': 0}
        
        if verbose:
            print(f"Monitoring {len(trades)} open trades...")
        
        # Fetch current prices
        slugs = [t['market_slug'] for t in trades]
        prices = self.fetch_current_prices(slugs, verbose=verbose)
        
        # If we couldn't fetch any prices (network error), skip this check
        if not prices:
            if verbose:
                print("⚠️  Could not fetch market prices - skipping check (will retry next cycle)")
            return {'checked': 0, 'tp_hits': 0, 'sl_hits': 0, 'errors': 0, 'skipped': True}
        
        tp_hits = 0
        sl_hits = 0
        errors = 0
        
        for trade in trades:
            try:
                slug = trade['market_slug']
                current_price = prices.get(slug)
                
                if current_price is None:
                    if verbose:
                        print(f"  ⚠️  {slug[:40]:<40} - Price unavailable")
                    continue
                
                # Check for exit
                exit_info = self.check_trade_exit(trade, current_price)
                
                if exit_info:
                    # Update trade in database
                    self.db.update_trade_take_profit(
                        trade['id'],
                        exit_info['exit_price'],
                        exit_info['pnl'],
                        exit_info['exit_reason'],
                        exit_info['holding_days'],
                        f"Auto-exit via {exit_info['exit_reason']} at {datetime.now().strftime('%H:%M:%S')}"
                    )
                    
                    side = trade['intended_side']
                    if exit_info['exit_reason'] == 'tp':
                        tp_hits += 1
                        if verbose:
                            print(f"  ✅ {slug[:40]:<40} | {side:<4} | TP HIT | ${exit_info['pnl']:+.2f}")
                    else:
                        sl_hits += 1
                        if verbose:
                            print(f"  🛑 {slug[:40]:<40} | {side:<4} | SL HIT | ${exit_info['pnl']:+.2f}")
                else:
                    if verbose:
                        side = trade['intended_side']
                        entry = trade['intended_price']
                        tp = trade['take_profit_price']
                        print(f"  ⏳ {slug[:40]:<40} | {side:<4} | Entry: ${entry:.2f} | TP: ${tp:.2f} | Current: ${current_price:.2f}")
                
            except Exception as e:
                errors += 1
                if verbose:
                    print(f"  ❌ Error checking {trade['market_slug']}: {e}")
        
        summary = {
            'checked': len(trades),
            'tp_hits': tp_hits,
            'sl_hits': sl_hits,
            'errors': errors
        }
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"📊 SUMMARY: Checked {summary['checked']} | TP: {summary['tp_hits']} | SL: {summary['sl_hits']} | Errors: {summary['errors']}")
            print(f"{'='*70}")
        
        return summary
    
    def run_once(self, verbose: bool = True):
        """Run a single check"""
        return self.check_all_trades(verbose=verbose)
    
    def run_continuous(self, interval_minutes: int = 5):
        """
        Run TP/SL monitoring continuously.
        
        Args:
            interval_minutes: Minutes between checks (default: 5)
        """
        if not HAS_SCHEDULE:
            print("❌ Error: 'schedule' module not installed.")
            print("   Install with: pip install schedule")
            print("   Or run: python3 paper_trading.py check-tp (one-time check)")
            return
        
        print(f"\n{'='*70}")
        print(f"🔄 CONTINUOUS TP/SL MONITORING")
        print(f"{'='*70}")
        print(f"Check interval: Every {interval_minutes} minutes")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*70}\n")
        
        # Schedule checks
        schedule.every(interval_minutes).minutes.do(self.check_all_trades)
        
        # Run initial check
        self.check_all_trades()
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{'='*70}")
            print(f"🛑 Monitoring stopped by user")
            print(f"Total checks performed: {self.check_count}")
            print(f"{'='*70}")
    
    def get_monitoring_stats(self) -> Dict:
        """Get statistics about TP/SL monitoring"""
        # Get exit reason summary
        exit_summary = self.db.get_exit_reason_summary()
        
        # Get holding time stats
        holding_stats = self.db.get_avg_holding_time()
        
        # Get all closed trades with exit reasons
        closed = self.db.get_closed_trades()
        tp_trades = [t for t in closed if t.get('exit_reason') == 'tp']
        sl_trades = [t for t in closed if t.get('exit_reason') == 'stop_loss']
        
        return {
            'total_closed': len(closed),
            'tp_exits': len(tp_trades),
            'sl_exits': len(sl_trades),
            'resolution_exits': len([t for t in closed if t.get('exit_reason') == 'resolution']),
            'tp_pnl': sum(t.get('pnl', 0) for t in tp_trades),
            'sl_pnl': sum(t.get('pnl', 0) for t in sl_trades),
            'avg_holding_days': holding_stats.get('avg_holding_days'),
            'checks_performed': self.check_count,
            'last_check': self.last_check_time.isoformat() if self.last_check_time else None
        }
    
    def display_stats(self):
        """Display TP/SL monitoring statistics"""
        stats = self.get_monitoring_stats()
        
        print(f"\n{'='*70}")
        print(f"📈 TP/SL MONITORING STATISTICS")
        print(f"{'='*70}")
        
        print(f"\nExit Breakdown:")
        print(f"  Take-Profit Exits:  {stats['tp_exits']}")
        print(f"  Stop-Loss Exits:    {stats['sl_exits']}")
        print(f"  Resolution Exits:   {stats['resolution_exits']}")
        print(f"  Total Closed:       {stats['total_closed']}")
        
        print(f"\nP&L by Exit Type:")
        print(f"  TP P&L:   ${stats['tp_pnl']:+.2f}")
        print(f"  SL P&L:   ${stats['sl_pnl']:+.2f}")
        
        total_exits = stats['tp_exits'] + stats['sl_exits']
        if total_exits > 0:
            tp_rate = stats['tp_exits'] / total_exits * 100
            print(f"\nTP Hit Rate: {tp_rate:.1f}%")
        
        if stats['avg_holding_days'] is not None:
            print(f"Avg Holding Time: {stats['avg_holding_days']:.1f} days")
        
        print(f"\nMonitoring:")
        print(f"  Checks performed: {stats['checks_performed']}")
        if stats['last_check']:
            print(f"  Last check: {stats['last_check']}")
        
        print(f"{'='*70}")


def run_monitor(interval: int = 5):
    """Run TP/SL monitor continuously"""
    monitor = TPSLMonitor()
    monitor.run_continuous(interval_minutes=interval)


def check_once():
    """Run TP/SL check once"""
    monitor = TPSLMonitor()
    monitor.run_once(verbose=True)


def show_stats():
    """Show TP/SL statistics"""
    monitor = TPSLMonitor()
    monitor.display_stats()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "stats":
            show_stats()
        elif sys.argv[1] == "once":
            check_once()
        elif sys.argv[1] == "monitor":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            run_monitor(interval)
        else:
            print("Usage: python3 paper_trading_tp_monitor.py [once|monitor|stats]")
    else:
        # Default: run once
        check_once()
