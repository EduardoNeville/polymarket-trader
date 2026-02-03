#!/usr/bin/env python3
"""
Polymarket Trading Toolkit - Master CLI
All-in-one interface for Polymarket trading tools
"""

import sys
import os

# Add tools directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scanner import PolymarketScanner
from odds_calculator import OddsCalculator, interactive_calculator
from position_tracker import PositionTracker, Position
from alert_system import AlertSystem, Alert
from utils.ai_calculator import interactive_ai_calculator
from datetime import datetime

def print_header():
    print("=" * 80)
    print("🎯 POLYMARKET TRADING TOOLKIT")
    print("=" * 80)
    print()

def print_menu():
    print("Available Commands:")
    print()
    print("  1. scan       - Scan markets for opportunities")
    print("  2. calc       - Calculate odds and position sizes")
    print("  3. ai-calc    - 🤖 AI-powered calculator with ensemble")
    print("  4. portfolio  - View and manage your portfolio")
    print("  5. alerts     - Set up price alerts")
    print("  6. help       - Show detailed help")
    print("  7. quit       - Exit")
    print()

def cmd_scan():
    print("🔍 MARKET SCANNER")
    print("-" * 80)
    
    scanner = PolymarketScanner()
    
    print("\n1. Full Market Scan")
    print("2. Find Arbitrage Opportunities")
    print("3. High Volume Markets")
    print("4. Markets Closing Soon")
    print("5. Value Opportunities")
    print()
    
    choice = input("Select option (1-5): ")
    
    if choice == '1':
        markets = scanner.get_active_markets(limit=20)
        print(f"\n📊 TOP 20 ACTIVE MARKETS BY VOLUME")
        print("-" * 80)
        for m in markets:
            print(f"  {m.question[:60]:<60} | YES: ${m.yes_price:.2f} | Vol: ${m.volume:,.0f}")
    
    elif choice == '2':
        opps = scanner.find_arbitrage_opportunities()
        if opps:
            print("\n💰 ARBITRAGE OPPORTUNITIES")
            print("-" * 80)
            for opp in opps[:5]:
                print(f"\n{opp['question']}")
                print(f"  YES: ${opp['yes_price']:.2f} | NO: ${opp['no_price']:.2f}")
                print(f"  Spread: {opp['spread']*100:.1f}% | Action: {opp['action']}")
        else:
            print("\n✅ No arbitrage opportunities found (efficient pricing)")
    
    elif choice == '3':
        markets = scanner.find_momentum_markets(min_volume=100000)
        print("\n📈 HIGH VOLUME MARKETS")
        print("-" * 80)
        for m in markets[:10]:
            print(f"  {m['question'][:55]:<55} | YES: ${m['yes_price']:.2f}")
    
    elif choice == '4':
        markets = scanner.get_markets_closing_soon(days=7)
        print("\n⏰ MARKETS CLOSING IN 7 DAYS")
        print("-" * 80)
        for m in markets[:10]:
            print(f"  {m['question'][:50]:<50} | {m['days_left']}d | ${m['yes_price']:.2f}")
    
    elif choice == '5':
        opps = scanner.find_value_opportunities()
        print("\n💎 VALUE OPPORTUNITIES")
        print("-" * 80)
        for opp in opps[:5]:
            print(f"\n{opp['question']}")
            print(f"  Type: {opp['type']} | Price: ${opp['price']:.2f}")

def cmd_calc():
    interactive_calculator()

def cmd_ai_calc():
    interactive_ai_calculator()

def cmd_portfolio():
    tracker = PositionTracker()
    
    print("💼 PORTFOLIO MANAGER")
    print("-" * 80)
    print()
    print("1. View Dashboard")
    print("2. Add Position")
    print("3. Close Position")
    print()
    
    choice = input("Select option (1-3): ")
    
    if choice == '1':
        tracker.display_dashboard()
    
    elif choice == '2':
        print("\nAdd New Position")
        print("-" * 50)
        slug = input("Market slug: ")
        question = input("Market question: ")
        side = input("Side (YES/NO): ").upper()
        entry = float(input("Entry price ($0.00-$1.00): "))
        shares = float(input("Number of shares: "))
        
        pos = Position(
            market_slug=slug,
            market_question=question,
            side=side,
            entry_price=entry,
            shares=shares,
            date_opened=datetime.now().isoformat()
        )
        tracker.add_position(pos)
        print()
        tracker.display_dashboard()
    
    elif choice == '3':
        summary = tracker.get_portfolio_summary()
        if summary['positions']:
            print("\nOpen Positions:")
            for i, pos in enumerate(summary['positions']):
                print(f"  {i}. {pos['market'][:50]} ({pos['side']})")
            
            idx = int(input("\nSelect position to close (number): "))
            if 0 <= idx < len(summary['positions']):
                pos = summary['positions'][idx]
                exit_price = float(input(f"Exit price (current ~${pos['current']:.2f}): ") or pos['current'])
                tracker.close_position(pos['slug'], exit_price)
        else:
            print("\nNo open positions to close.")

def cmd_alerts():
    alerts = AlertSystem()
    
    print("🔔 ALERT SYSTEM")
    print("-" * 80)
    print()
    print("1. View Alerts")
    print("2. Add Alert")
    print("3. Remove Alert")
    print("4. Check Now")
    print("5. Start Monitor")
    print()
    
    choice = input("Select option (1-5): ")
    
    if choice == '1':
        alerts.display_alerts()
    
    elif choice == '2':
        print("\nCreate New Alert")
        print("-" * 50)
        slug = input("Market slug: ")
        name = input("Market name: ")
        print("\nConditions: above | below | changes_by")
        condition = input("Condition: ")
        threshold = float(input("Threshold ($ or %): "))
        
        alert = Alert(
            market_slug=slug,
            market_name=name,
            condition=condition,
            threshold=threshold
        )
        alerts.add_alert(alert)
    
    elif choice == '3':
        alerts.display_alerts()
        idx = int(input("\nAlert index to remove: "))
        alerts.remove_alert(idx)
    
    elif choice == '4':
        triggered = alerts.check_alerts()
        if triggered:
            print(f"\n🚨 {len(triggered)} ALERT(S) TRIGGERED")
            for t in triggered:
                print(f"\n{t['alert'].market_name}")
                print(f"   {t['message']}")
        else:
            print("\n✅ No alerts triggered")
    
    elif choice == '5':
        interval = int(input("Check interval in seconds (default 60): ") or 60)
        print()
        alerts.run_monitor(interval)

def cmd_help():
    print("""
POLYMARKET TRADING TOOLKIT - HELP
=================================

This toolkit provides four main components:

1. MARKET SCANNER (scan)
   - Find arbitrage opportunities
   - Discover high-volume markets
   - Identify markets closing soon
   - Spot value opportunities

2. ODDS CALCULATOR (calc)
   - Calculate expected value
   - Apply Kelly Criterion
   - Determine optimal position sizes
   - Analyze risk/reward

3. AI-POWERED CALCULATOR (ai-calc)
   - Ensemble model predictions
   - Adaptive Kelly with calibration
   - Tracks prediction accuracy
   - Learns from outcomes

4. PORTFOLIO TRACKER (portfolio)
   - Track open positions
   - Monitor P&L in real-time
   - Calculate total portfolio value
   - Set targets and stop losses

4. ALERT SYSTEM (alerts)
   - Set price thresholds
   - Monitor multiple markets
   - Get notified of opportunities
   - Run continuous monitoring

QUICK START:
1. Run 'scan' to find opportunities
2. Use 'calc' to size your position
3. Add positions with 'portfolio'
4. Set alerts with 'alerts'

TIPS:
- Always use fractional Kelly (25% recommended)
- Check markets closing soon for time decay
- Set alerts on your positions
- Monitor high-volume markets for liquidity

For more details, see README.md
    """)

def main():
    print_header()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command in ['scan', 'scanner']:
            cmd_scan()
        elif command in ['calc', 'calculator']:
            cmd_calc()
        elif command in ['ai-calc', 'ai', 'ai-calculator']:
            cmd_ai_calc()
        elif command in ['portfolio', 'pos', 'positions']:
            cmd_portfolio()
        elif command in ['alerts', 'alert']:
            cmd_alerts()
        elif command == 'help':
            cmd_help()
        else:
            print(f"Unknown command: {command}")
            print()
            print_menu()
    else:
        print_menu()
        
        while True:
            try:
                command = input("Enter command: ").lower().strip()
                
                if command in ['1', 'scan', 'scanner']:
                    cmd_scan()
                elif command in ['2', 'calc', 'calculator']:
                    cmd_calc()
                elif command in ['3', 'ai-calc', 'ai', 'ai-calculator']:
                    cmd_ai_calc()
                elif command in ['4', 'portfolio', 'pos']:
                    cmd_portfolio()
                elif command in ['5', 'alerts', 'alert']:
                    cmd_alerts()
                elif command in ['6', 'help']:
                    cmd_help()
                elif command in ['7', 'quit', 'exit', 'q']:
                    print("\n👋 Good luck trading!")
                    break
                else:
                    print("Unknown command. Type 'help' for options.")
                
                print()
                
            except KeyboardInterrupt:
                print("\n\n👋 Good luck trading!")
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    main()
