#!/usr/bin/env python3
"""
Polymarket Alert System
Monitor markets and send notifications on price thresholds
"""

import json
import requests
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass, asdict

GAMMA_API = "https://gamma-api.polymarket.com"

@dataclass
class Alert:
    market_slug: str
    market_name: str
    condition: str  # 'above', 'below', 'changes_by'
    threshold: float
    notification_sent: bool = False
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

class AlertSystem:
    def __init__(self, alerts_file: str = "alerts.json"):
        self.alerts_file = Path(alerts_file)
        self.alerts: List[Alert] = []
        self.session = requests.Session()
        self.price_history: Dict[str, float] = {}
        self.load_alerts()
    
    def load_alerts(self):
        """Load alerts from file"""
        if self.alerts_file.exists():
            with open(self.alerts_file, 'r') as f:
                data = json.load(f)
                self.alerts = [Alert(**a) for a in data]
    
    def save_alerts(self):
        """Save alerts to file"""
        with open(self.alerts_file, 'w') as f:
            json.dump([asdict(a) for a in self.alerts], f, indent=2)
    
    def add_alert(self, alert: Alert):
        """Add a new price alert"""
        self.alerts.append(alert)
        self.save_alerts()
        print(f"✅ Alert added: {alert.market_name[:40]}... {alert.condition} ${alert.threshold:.2f}")
    
    def remove_alert(self, index: int):
        """Remove an alert by index"""
        if 0 <= index < len(self.alerts):
            removed = self.alerts.pop(index)
            self.save_alerts()
            print(f"✅ Removed alert: {removed.market_name[:40]}...")
        else:
            print(f"❌ Invalid alert index: {index}")
    
    def get_current_price(self, market_slug: str) -> float:
        """Fetch current YES price"""
        try:
            url = f"{GAMMA_API}/markets"
            params = {'slug': market_slug}
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data and len(data) > 0:
                prices = json.loads(data[0].get('outcomePrices', '{}'))
                return float(prices.get('Yes', 0))
        except Exception as e:
            print(f"Error fetching price for {market_slug}: {e}")
        
        return 0.0
    
    def check_alerts(self) -> List[Dict]:
        """Check all alerts and return triggered ones"""
        triggered = []
        
        for alert in self.alerts:
            if alert.notification_sent:
                continue
            
            current_price = self.get_current_price(alert.market_slug)
            
            if current_price == 0:
                continue
            
            # Check condition
            condition_met = False
            
            if alert.condition == 'above' and current_price >= alert.threshold:
                condition_met = True
                message = f"Price ABOVE ${alert.threshold:.2f} (Current: ${current_price:.2f})"
            
            elif alert.condition == 'below' and current_price <= alert.threshold:
                condition_met = True
                message = f"Price BELOW ${alert.threshold:.2f} (Current: ${current_price:.2f})"
            
            elif alert.condition == 'changes_by':
                # Check percentage change from last known price
                last_price = self.price_history.get(alert.market_slug, current_price)
                if last_price > 0:
                    change_pct = abs((current_price - last_price) / last_price) * 100
                    if change_pct >= alert.threshold:
                        condition_met = True
                        direction = "UP" if current_price > last_price else "DOWN"
                        message = f"Price moved {direction} by {change_pct:.1f}% (Current: ${current_price:.2f})"
            
            if condition_met:
                triggered.append({
                    'alert': alert,
                    'current_price': current_price,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                })
                alert.notification_sent = True
        
        # Update price history
        for alert in self.alerts:
            current = self.get_current_price(alert.market_slug)
            if current > 0:
                self.price_history[alert.market_slug] = current
        
        if triggered:
            self.save_alerts()
        
        return triggered
    
    def reset_alert(self, index: int):
        """Reset notification status for an alert"""
        if 0 <= index < len(self.alerts):
            self.alerts[index].notification_sent = False
            self.save_alerts()
            print(f"✅ Reset alert: {self.alerts[index].market_name[:40]}...")
        else:
            print(f"❌ Invalid alert index: {index}")
    
    def display_alerts(self):
        """Display all alerts"""
        print("=" * 80)
        print("🔔 ACTIVE ALERTS")
        print("=" * 80)
        print()
        
        if not self.alerts:
            print("No alerts set. Use 'add' to create alerts.")
            return
        
        print(f"{'#':<4} {'Market':<45} {'Condition':<12} {'Threshold':<10} {'Status':<10}")
        print("-" * 80)
        
        for i, alert in enumerate(self.alerts):
            status = "✅ Sent" if alert.notification_sent else "⏳ Active"
            market_name = alert.market_name[:43]
            print(f"{i:<4} {market_name:<45} {alert.condition:<12} ${alert.threshold:<9.2f} {status:<10}")
        
        print()
        print("=" * 80)
    
    def run_monitor(self, interval: int = 60):
        """Continuously monitor alerts"""
        print("🔔 Starting Alert Monitor")
        print(f"   Checking every {interval} seconds...")
        print("   Press Ctrl+C to stop")
        print()
        
        try:
            while True:
                triggered = self.check_alerts()
                
                if triggered:
                    print("\n" + "=" * 80)
                    print(f"🚨 ALERTS TRIGGERED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print("=" * 80)
                    
                    for t in triggered:
                        alert = t['alert']
                        print(f"\n📊 {alert.market_name}")
                        print(f"   {t['message']}")
                        print(f"   Time: {t['timestamp']}")
                    
                    print("\n" + "=" * 80 + "\n")
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] No alerts triggered", end='\r')
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n👋 Stopping alert monitor")


def main():
    import sys
    alerts = AlertSystem()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'add':
            print("Create New Alert")
            print("-" * 50)
            slug = input("Market slug: ")
            name = input("Market name: ")
            print("\nConditions: above, below, changes_by")
            condition = input("Condition: ")
            threshold = float(input("Threshold (price or %): "))
            
            alert = Alert(
                market_slug=slug,
                market_name=name,
                condition=condition,
                threshold=threshold
            )
            alerts.add_alert(alert)
        
        elif command == 'remove':
            alerts.display_alerts()
            idx = int(input("\nAlert index to remove: "))
            alerts.remove_alert(idx)
        
        elif command == 'reset':
            alerts.display_alerts()
            idx = int(input("\nAlert index to reset: "))
            alerts.reset_alert(idx)
        
        elif command == 'monitor':
            interval = int(input("Check interval in seconds (default 60): ") or 60)
            alerts.run_monitor(interval)
        
        elif command == 'check':
            triggered = alerts.check_alerts()
            if triggered:
                print(f"\n🚨 {len(triggered)} ALERT(S) TRIGGERED")
                for t in triggered:
                    print(f"\n{t['alert'].market_name}")
                    print(f"   {t['message']}")
            else:
                print("✅ No alerts triggered")
        
        else:
            alerts.display_alerts()
    else:
        alerts.display_alerts()


if __name__ == "__main__":
    main()
