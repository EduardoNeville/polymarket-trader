"""
Paper Trading Outcome Updater
Updates paper trades with market outcomes and calculates P&L
Timestamp: 2026-02-03 20:30 GMT+1
"""

from datetime import datetime
from typing import Dict, List, Optional

from utils.paper_trading_db import PaperTradingDB
from scanner import PolymarketScanner


class PaperTradingUpdater:
    """
    Updates paper trades with outcomes when markets resolve.
    
    Features:
    - Polls resolved markets
    - Matches with open paper trades
    - Calculates P&L
    - Updates database
    """
    
    def __init__(self):
        self.db = PaperTradingDB()
        self.scanner = PolymarketScanner()
    
    def determine_outcome(self, yes_price: float, no_price: float) -> Optional[int]:
        """
        Determine market outcome from final prices.
        
        Returns:
            1 if YES won, 0 if NO won, None if unresolved
        """
        if yes_price >= 0.99:
            return 1
        elif no_price >= 0.99:
            return 0
        return None
    
    def calculate_pnl(self, trade: Dict, outcome: int) -> float:
        """
        Calculate P&L for a trade.
        
        Args:
            trade: Trade dictionary
            outcome: 1 for YES win, 0 for NO win
            
        Returns:
            Profit/loss amount
        """
        side = trade['intended_side']
        entry_price = trade['intended_price']
        shares = trade['intended_size']
        
        if side == 'YES':
            # Payout is $1 if YES wins, $0 if NO wins
            payout = outcome  # 1 or 0
            cost = entry_price * shares
            revenue = payout * shares
            pnl = revenue - cost
        else:  # NO
            # Payout is $1 if NO wins (outcome = 0)
            payout = 1 - outcome  # 0 or 1
            no_entry_price = 1 - entry_price
            cost = no_entry_price * shares
            revenue = payout * shares
            pnl = revenue - cost
        
        return pnl
    
    def update_open_trades(self, verbose: bool = True) -> Dict:
        """
        Update all open trades with current market outcomes.
        
        Returns:
            Summary of updates
        """
        if verbose:
            print("=" * 80)
            print("🔄 UPDATING PAPER TRADE OUTCOMES")
            print("=" * 80)
        
        # Get open trades
        open_trades = self.db.get_open_trades()
        
        if not open_trades:
            if verbose:
                print("\n✅ No open trades to update")
            return {'updated': 0, 'unresolved': 0, 'errors': 0}
        
        if verbose:
            print(f"\nFound {len(open_trades)} open trades")
            print("Fetching current market status...")
        
        # Fetch all current markets
        all_markets = self.scanner.get_active_markets(limit=500)
        
        # Index by slug for fast lookup
        markets_by_slug = {m.slug: m for m in all_markets}
        
        updated = 0
        unresolved = 0
        errors = 0
        
        if verbose:
            print("\nProcessing trades...")
        
        for trade in open_trades:
            slug = trade['market_slug']
            
            try:
                # Find market
                market = markets_by_slug.get(slug)
                
                if not market:
                    # Market might be archived/closed
                    unresolved += 1
                    continue
                
                # Check if resolved
                outcome = self.determine_outcome(market.yes_price, market.no_price)
                
                if outcome is not None:
                    # Calculate P&L
                    pnl = self.calculate_pnl(trade, outcome)
                    
                    # Update database
                    success = self.db.update_trade_outcome(
                        trade['id'],
                        outcome,
                        pnl,
                        f"Resolved on {datetime.now().strftime('%Y-%m-%d')}"
                    )
                    
                    if success:
                        updated += 1
                        if verbose:
                            side = trade['intended_side']
                            print(f"  ✓ {slug[:40]:<40} | {side:<4} | Outcome: {outcome} | P&L: ${pnl:+.2f}")
                    else:
                        errors += 1
                else:
                    unresolved += 1
                    
            except Exception as e:
                errors += 1
                if verbose:
                    print(f"  ✗ Error updating {slug}: {e}")
        
        summary = {
            'updated': updated,
            'unresolved': unresolved,
            'errors': errors
        }
        
        if verbose:
            print(f"\n{'='*80}")
            print("📊 UPDATE SUMMARY:")
            print(f"  Updated:     {updated}")
            print(f"  Unresolved:  {unresolved}")
            print(f"  Errors:      {errors}")
            print(f"{'='*80}")
        
        return summary
    
    def get_performance_report(self) -> Dict:
        """
        Generate comprehensive performance report.
        
        Returns:
            Performance statistics
        """
        summary = self.db.get_performance_summary()
        
        # Get additional stats
        closed_trades = self.db.get_closed_trades()
        open_trades = self.db.get_open_trades()
        
        # Calculate by side
        yes_trades = [t for t in closed_trades if t['intended_side'] == 'YES']
        no_trades = [t for t in closed_trades if t['intended_side'] == 'NO']
        
        yes_wins = sum(1 for t in yes_trades if t.get('pnl', 0) > 0)
        no_wins = sum(1 for t in no_trades if t.get('pnl', 0) > 0)
        
        return {
            **summary,
            'yes_win_rate': yes_wins / len(yes_trades) if yes_trades else 0,
            'no_win_rate': no_wins / len(no_trades) if no_trades else 0,
            'open_trades_count': len(open_trades),
            'closed_trades_count': len(closed_trades)
        }
    
    def display_performance_report(self):
        """Display formatted performance report"""
        report = self.get_performance_report()
        
        if report['total_trades'] == 0:
            print("\n⚠️  No closed trades yet. Cannot generate report.")
            return
        
        print("\n" + "=" * 80)
        print("📈 PAPER TRADING PERFORMANCE REPORT")
        print("=" * 80)
        
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"  Total Trades:       {report['total_trades']}")
        print(f"  Winning Trades:     {report['winning_trades']} ({report['win_rate']:.1%})")
        print(f"  Losing Trades:      {report['losing_trades']}")
        print(f"  Total P&L:          ${report['total_pnl']:+.2f}")
        print(f"  Avg P&L per Trade:  ${report['avg_pnl']:+.2f}")
        
        print(f"\n📈 BY SIDE:")
        print(f"  YES Trades Win Rate: {report['yes_win_rate']:.1%}")
        print(f"  NO Trades Win Rate:  {report['no_win_rate']:.1%}")
        
        print(f"\n📊 STRATEGY METRICS:")
        print(f"  Average Entry Edge:  {report['avg_edge']:.1%}")
        print(f"  Average Entry Price: ${report['avg_entry_price']:.2f}")
        
        print(f"\n📋 TRADE STATUS:")
        print(f"  Closed Trades:      {report['closed_trades_count']}")
        print(f"  Open Trades:        {report['open_trades_count']}")
        
        print("=" * 80)


# Convenience functions for command-line use
def update_outcomes():
    """Update all open trade outcomes"""
    updater = PaperTradingUpdater()
    updater.update_open_trades(verbose=True)
    updater.display_performance_report()


def get_report():
    """Get performance report"""
    updater = PaperTradingUpdater()
    updater.display_performance_report()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'report':
        get_report()
    else:
        update_outcomes()
