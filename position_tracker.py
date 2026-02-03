#!/usr/bin/env python3
"""
Polymarket Position Tracker & P&L Dashboard
Track your open positions and monitor performance
"""

import json
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass, asdict

GAMMA_API = "https://gamma-api.polymarket.com"

@dataclass
class Position:
    market_slug: str
    market_question: str
    side: str  # 'YES' or 'NO'
    entry_price: float
    shares: float
    date_opened: str
    notes: str = ""
    target_price: float = None
    stop_loss: float = None

class PositionTracker:
    def __init__(self, data_file: str = "positions.json"):
        self.data_file = Path(data_file)
        self.positions: List[Position] = []
        self.session = requests.Session()
        self.load_positions()
    
    def load_positions(self):
        """Load positions from file"""
        if self.data_file.exists():
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.positions = [Position(**p) for p in data]
    
    def save_positions(self):
        """Save positions to file"""
        with open(self.data_file, 'w') as f:
            json.dump([asdict(p) for p in self.positions], f, indent=2)
    
    def add_position(self, position: Position):
        """Add a new position"""
        self.positions.append(position)
        self.save_positions()
        print(f"✅ Added position: {position.side} {position.shares} shares @ ${position.entry_price:.2f}")
    
    def close_position(self, market_slug: str, exit_price: float):
        """Close a position"""
        for i, pos in enumerate(self.positions):
            if pos.market_slug == market_slug:
                # Calculate P&L
                if pos.side == 'YES':
                    pnl = (exit_price - pos.entry_price) * pos.shares
                    pnl_pct = ((exit_price - pos.entry_price) / pos.entry_price) * 100
                else:
                    entry_no = 1 - pos.entry_price
                    exit_no = 1 - exit_price
                    pnl = (exit_no - entry_no) * pos.shares
                    pnl_pct = ((exit_no - entry_no) / entry_no) * 100
                
                self.positions.pop(i)
                self.save_positions()
                
                print(f"✅ Closed position: {pos.market_question[:50]}")
                print(f"   P&L: ${pnl:,.2f} ({pnl_pct:+.1f}%)")
                return pnl
        
        print(f"❌ No position found for {market_slug}")
        return 0
    
    def get_current_price(self, market_slug: str) -> float:
        """Fetch current market price"""
        try:
            url = f"{GAMMA_API}/markets"
            params = {'slug': market_slug}
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data and len(data) > 0:
                prices = json.loads(data[0].get('outcomePrices', '{}'))
                return float(prices.get('Yes', 0))
        except Exception as e:
            print(f"Error fetching price: {e}")
        
        return 0.0
    
    def get_portfolio_summary(self) -> Dict:
        """Get summary of all positions"""
        summary = {
            'positions': [],
            'total_invested': 0,
            'current_value': 0,
            'total_pnl': 0,
            'open_count': len(self.positions)
        }
        
        for pos in self.positions:
            current_price = self.get_current_price(pos.market_slug)
            
            if pos.side == 'YES':
                current_value = pos.shares * current_price
                invested = pos.shares * pos.entry_price
                pnl = current_value - invested
                pnl_pct = (pnl / invested) * 100 if invested > 0 else 0
            else:
                current_no_price = 1 - current_price
                entry_no_price = 1 - pos.entry_price
                current_value = pos.shares * current_no_price
                invested = pos.shares * entry_no_price
                pnl = current_value - invested
                pnl_pct = (pnl / invested) * 100 if invested > 0 else 0
            
            summary['positions'].append({
                'market': pos.market_question[:50],
                'slug': pos.market_slug,
                'side': pos.side,
                'shares': pos.shares,
                'entry': pos.entry_price,
                'current': current_price if pos.side == 'YES' else (1 - current_price),
                'invested': invested,
                'value': current_value,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'opened': pos.date_opened
            })
            
            summary['total_invested'] += invested
            summary['current_value'] += current_value
        
        summary['total_pnl'] = summary['current_value'] - summary['total_invested']
        summary['pnl_percent'] = (summary['total_pnl'] / summary['total_invested']) * 100 if summary['total_invested'] > 0 else 0
        
        return summary
    
    def check_alerts(self) -> List[Dict]:
        """Check for price alerts (targets and stop losses)"""
        alerts = []
        
        for pos in self.positions:
            if pos.target_price or pos.stop_loss:
                current_price = self.get_current_price(pos.market_slug)
                
                if pos.side == 'YES':
                    if pos.target_price and current_price >= pos.target_price:
                        alerts.append({
                            'type': 'TARGET_HIT',
                            'market': pos.market_question,
                            'side': pos.side,
                            'target': pos.target_price,
                            'current': current_price,
                            'action': 'Consider taking profits'
                        })
                    
                    if pos.stop_loss and current_price <= pos.stop_loss:
                        alerts.append({
                            'type': 'STOP_LOSS',
                            'market': pos.market_question,
                            'side': pos.side,
                            'stop': pos.stop_loss,
                            'current': current_price,
                            'action': 'Consider cutting losses'
                        })
                else:  # NO position
                    current_no = 1 - current_price
                    
                    if pos.target_price and current_no >= pos.target_price:
                        alerts.append({
                            'type': 'TARGET_HIT',
                            'market': pos.market_question,
                            'side': pos.side,
                            'target': pos.target_price,
                            'current': current_no,
                            'action': 'Consider taking profits'
                        })
                    
                    if pos.stop_loss and current_no <= pos.stop_loss:
                        alerts.append({
                            'type': 'STOP_LOSS',
                            'market': pos.market_question,
                            'side': pos.side,
                            'stop': pos.stop_loss,
                            'current': current_no,
                            'action': 'Consider cutting losses'
                        })
        
        return alerts
    
    def display_dashboard(self):
        """Display portfolio dashboard"""
        print("=" * 100)
        print("📊 POLYMARKET PORTFOLIO DASHBOARD")
        print("=" * 100)
        print()
        
        summary = self.get_portfolio_summary()
        
        # Portfolio summary
        print(f"💰 PORTFOLIO SUMMARY")
        print(f"   Open Positions: {summary['open_count']}")
        print(f"   Total Invested: ${summary['total_invested']:,.2f}")
        print(f"   Current Value:  ${summary['current_value']:,.2f}")
        
        pnl = summary['total_pnl']
        pnl_pct = summary['pnl_percent']
        emoji = "🟢" if pnl >= 0 else "🔴"
        print(f"   Total P&L:      {emoji} ${pnl:+,.2f} ({pnl_pct:+.2f}%)")
        print()
        
        # Individual positions
        if summary['positions']:
            print("📋 OPEN POSITIONS")
            print("-" * 100)
            print(f"{'Market':<50} {'Side':<6} {'Shares':<10} {'Entry':<8} {'Current':<8} {'P&L':<12} {'%':<8}")
            print("-" * 100)
            
            for pos in summary['positions']:
                market_name = pos['market'][:48]
                pnl_emoji = "🟢" if pos['pnl'] >= 0 else "🔴"
                print(f"{market_name:<50} {pos['side']:<6} {pos['shares']:<10.0f} ${pos['entry']:<7.2f} ${pos['current']:<7.2f} {pnl_emoji} ${pos['pnl']:+>10.2f} {pos['pnl_pct']:+>7.1f}%")
            
            print()
        
        # Check alerts
        alerts = self.check_alerts()
        if alerts:
            print("🚨 ALERTS")
            print("-" * 100)
            for alert in alerts:
                emoji = "🎯" if alert['type'] == 'TARGET_HIT' else "⛔"
                print(f"{emoji} {alert['type']}: {alert['market'][:50]}")
                print(f"   Current: ${alert['current']:.2f} | {'Target' if alert['type'] == 'TARGET_HIT' else 'Stop'}: ${alert['stop']:.2f}")
                print(f"   Action: {alert['action']}")
            print()
        
        print("=" * 100)


def main():
    tracker = PositionTracker()
    
    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'add':
            # Add position interactively
            print("Add New Position")
            print("-" * 50)
            slug = input("Market slug: ")
            question = input("Market question: ")
            side = input("Side (YES/NO): ").upper()
            entry = float(input("Entry price: "))
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
        
        elif command == 'close':
            slug = input("Market slug to close: ")
            exit_price = float(input("Exit price: "))
            tracker.close_position(slug, exit_price)
        
        else:
            tracker.display_dashboard()
    else:
        tracker.display_dashboard()


if __name__ == "__main__":
    main()
