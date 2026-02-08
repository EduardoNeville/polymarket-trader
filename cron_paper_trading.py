#!/usr/bin/env python3
"""
Paper Trading Cron Job - $1,000 Bankroll Limited
Runs every 5 minutes to:
1. Check TP/SL hits on open trades
2. Update resolved trades
3. Generate new signals ONLY if capital available

Bankroll: $1,000 (hard limit)
Min Trade: $20 (no tiny positions)
No max positions - take as many as capital allows
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime
from utils.paper_trading_tp_monitor import TPSLMonitor
from utils.paper_trading_updater import PaperTradingUpdater
from utils.paper_trading_signals import PaperTradingSignalGenerator
from utils.paper_trading_db import PaperTradingDB

# Hard bankroll limit
BANKROLL = 1000.0
MIN_TRADE_SIZE = 20.0  # Minimum $20 per trade (no tiny positions)
# NO MAX_POSITIONS - take as many trades as capital allows


def calculate_exposure():
    """Calculate current exposure and available capital including realized PnL"""
    db = PaperTradingDB()
    open_trades = db.get_open_trades()
    closed_trades = db.get_closed_trades()
    
    # Sum position sizes for open trades
    total_exposure = sum(t.get('intended_size', 0) for t in open_trades)
    
    # Sum realized PnL from closed trades
    realized_pnl = sum(t.get('pnl', 0) for t in closed_trades)
    
    # Available = Bankroll - Open Exposure + Realized PnL
    available = BANKROLL - total_exposure + realized_pnl
    
    return {
        'open_count': len(open_trades),
        'closed_count': len(closed_trades),
        'total_exposure': total_exposure,
        'realized_pnl': realized_pnl,
        'available': available
    }


def run_paper_trading_cycle():
    """Run one complete paper trading cycle with strict bankroll limits"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"\n{'='*70}")
    print(f"📊 PAPER TRADING CYCLE - {timestamp}")
    print(f"💰 Bankroll: ${BANKROLL:,.2f} | Min Trade: ${MIN_TRADE_SIZE:.2f}")
    print(f"📝 Rule: Take as many trades as capital allows")
    print(f"{'='*70}")
    
    # Get current exposure
    exposure = calculate_exposure()
    
    # Step 1: Check TP/SL hits
    print("\n🎯 Step 1: Checking TP/SL hits...")
    monitor = TPSLMonitor()
    tp_result = monitor.check_all_trades(verbose=False)
    print(f"   Checked: {tp_result['checked']} | TP hits: {tp_result['tp_hits']} | SL hits: {tp_result['sl_hits']}")
    
    # Re-check exposure after TP/SL (frees up capital)
    if tp_result['tp_hits'] > 0 or tp_result['sl_hits'] > 0:
        exposure = calculate_exposure()
        print(f"   💰 Capital freed! Available: ${exposure['available']:.2f}")
    
    # Step 2: Update resolved trades
    print("\n🔄 Step 2: Updating resolved trades...")
    updater = PaperTradingUpdater()
    update_result = updater.update_open_trades(verbose=False)
    print(f"   Resolved: {update_result['updated']} | Still open: {update_result['unresolved']}")
    
    # Re-check exposure after resolutions
    if update_result['updated'] > 0:
        exposure = calculate_exposure()
        print(f"   💰 Capital freed! Available: ${exposure['available']:.2f}")
    
    # Step 3: Generate new signals (only if we have capital)
    print("\n📈 Step 3: Checking for new opportunities...")
    print(f"   Open: {exposure['open_count']} positions | Closed: {exposure['closed_count']} trades")
    print(f"   Deployed: ${exposure['total_exposure']:.2f} | Realized PnL: ${exposure['realized_pnl']:+.2f}")
    print(f"   Available: ${exposure['available']:.2f}")
    
    new_signals = []
    
    # Only constraint: must have at least MIN_TRADE_SIZE available
    if exposure['available'] < MIN_TRADE_SIZE:
        print(f"   ⛔ Insufficient capital (${exposure['available']:.2f} < ${MIN_TRADE_SIZE:.2f} min). No new trades.")
    else:
        print(f"   ✅ Can take trades up to ${exposure['available']:.2f} total")
        
        # Generate signals with FULL bankroll (generator calculates available from DB)
        generator = PaperTradingSignalGenerator(bankroll=BANKROLL, min_edge=0.05)
        
        raw_signals = generator.generate_signals_for_markets(
            max_markets=50,  # Check more markets since we can take many
            save_to_db=False  # We'll filter and save manually
        )
        
        # Take as many signals as capital allows
        for signal in raw_signals:
            # Check if we can afford this trade
            if signal['intended_size'] < MIN_TRADE_SIZE:
                continue  # Skip tiny trades
            
            if signal['intended_size'] > exposure['available']:
                # Try to reduce size to fit available capital
                if exposure['available'] >= MIN_TRADE_SIZE:
                    signal['intended_size'] = exposure['available']
                else:
                    break  # Can't afford any more
            
            # Save to DB
            db = PaperTradingDB()
            db.save_trade(signal)
            new_signals.append(signal)
            exposure['available'] -= signal['intended_size']
            exposure['total_exposure'] += signal['intended_size']
            
            # Check if we can still trade
            if exposure['available'] < MIN_TRADE_SIZE:
                break
        
        print(f"   New signals added: {len(new_signals)}")
        
        if new_signals:
            for sig in new_signals[:5]:
                days = sig.get('days_to_resolve')
                if days is not None:
                    if days < 30:
                        time_str = f"{days:.0f}d"
                    elif days < 365:
                        time_str = f"{days/30:.0f}mo"
                    else:
                        time_str = f"{days/365:.1f}yr"
                else:
                    time_str = "?"
                print(f"      • {sig['market_question'][:40]}... | {sig['intended_side']} | ${sig['intended_size']:.2f} | Edge: {sig['edge']:+.1%} | Res: {time_str}")
            if len(new_signals) > 5:
                print(f"      ... and {len(new_signals) - 5} more")
    
    # Final summary
    final_exposure = calculate_exposure()
    
    print(f"\n{'='*70}")
    print(f"✅ CYCLE COMPLETE")
    print(f"   Positions: {final_exposure['open_count']} open | {final_exposure['closed_count']} closed")
    print(f"   Deployed: ${final_exposure['total_exposure']:.2f} | Realized PnL: ${final_exposure['realized_pnl']:+.2f}")
    print(f"   Available: ${final_exposure['available']:.2f}")
    print(f"{'='*70}")
    
    # Return summary for logging
    return {
        'timestamp': timestamp,
        'tp_hits': tp_result['tp_hits'],
        'sl_hits': tp_result['sl_hits'],
        'resolved': update_result['updated'],
        'new_signals': len(new_signals),
        'open_trades': final_exposure['open_count'],
        'closed_trades': final_exposure['closed_count'],
        'exposure': final_exposure['total_exposure'],
        'realized_pnl': final_exposure['realized_pnl'],
        'available': final_exposure['available']
    }


if __name__ == '__main__':
    try:
        result = run_paper_trading_cycle()
        
        # Log to file
        log_line = f"{result['timestamp']}, TP:{result['tp_hits']}, SL:{result['sl_hits']}, Res:{result['resolved']}, New:{result['new_signals']}, Open:{result['open_trades']}, Closed:{result['closed_trades']}, Exp:${result['exposure']:.0f}, PnL:${result['realized_pnl']:+.0f}, Avail:${result['available']:.0f}\n"
        
        log_file = Path('logs/paper_trading_cron.log')
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_file, 'a') as f:
            f.write(log_line)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
