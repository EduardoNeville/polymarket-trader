#!/usr/bin/env python3
"""
High-Edge Opportunity Scanner
Option 2: Run when edge > 10% found
Timestamp: 2026-02-03 21:39 GMT+1
"""

import sys
sys.path.insert(0, '/home/eduardoneville/projects/polymarket-trader')

from datetime import datetime
from utils.paper_trading_signals import PaperTradingSignalGenerator
from utils.paper_trading_db import PaperTradingDB
from scanner import PolymarketScanner


class HighEdgeScanner:
    """Scan for high-edge opportunities (>10%)"""
    
    def __init__(self, edge_threshold: float = 0.10):
        self.edge_threshold = edge_threshold
        self.generator = PaperTradingSignalGenerator(bankroll=1000, min_edge=edge_threshold)
        self.scanner = PolymarketScanner()
        self.db = PaperTradingDB()
    
    def scan_for_opportunities(self, max_markets: int = 100) -> list:
        """Scan markets for high-edge opportunities"""
        print("🔍 Scanning for high-edge opportunities...")
        print(f"   Edge threshold: {self.edge_threshold:.1%}")
        
        # Scan more markets than usual
        markets = self.scanner.get_active_markets(limit=max_markets)
        
        high_edge_signals = []
        
        for market in markets:
            # Check liquidity
            if market.liquidity < 50000:
                continue
            
            if market.yes_price >= 0.98 or market.yes_price <= 0.02:
                continue
            
            # Generate signal
            signal = self.generator.generate_signal(market)
            
            if signal and abs(signal['edge']) >= self.edge_threshold:
                high_edge_signals.append(signal)
        
        return high_edge_signals
    
    def display_opportunities(self, signals: list):
        """Display high-edge opportunities"""
        if not signals:
            print("\n⚠️  No high-edge opportunities found today")
            print(f"   (Threshold: {self.edge_threshold:.1%})")
            return
        
        print("\n" + "="*80)
        print(f"🎯 HIGH-EDGE OPPORTUNITIES FOUND: {len(signals)}")
        print("="*80)
        
        # Sort by edge
        signals_sorted = sorted(signals, key=lambda x: abs(x['edge']), reverse=True)
        
        for i, signal in enumerate(signals_sorted, 1):
            print(f"\n{i}. {signal['market_question'][:55]}...")
            print(f"   💰 Edge:       {signal['edge']:+.1%}")
            print(f"   📊 Price:      ${signal['intended_price']:.2f}")
            print(f"   📈 Side:       {signal['intended_side']}")
            print(f"   💵 Size:       ${signal['intended_size']:.2f}")
            print(f"   🎯 Conf:       {signal['confidence']:.0%}")
        
        print("\n" + "="*80)
        print(f"Total high-edge signals: {len(signals)}")
        print("="*80)
    
    def run(self, auto_save: bool = True) -> list:
        """Run high-edge scanner"""
        print("="*80)
        print("🚀 HIGH-EDGE OPPORTUNITY SCANNER")
        print("="*80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Threshold: {self.edge_threshold:.1%} edge")
        print("="*80)
        
        # Find opportunities
        signals = self.scan_for_opportunities()
        
        # Display
        self.display_opportunities(signals)
        
        # Save if found
        if auto_save and signals:
            print("\n💾 Saving to database...")
            saved = 0
            for signal in signals:
                try:
                    self.db.save_trade(signal)
                    saved += 1
                except Exception as e:
                    print(f"   Error saving: {e}")
            
            print(f"✅ Saved {saved} high-edge signals")
        
        return signals


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='High-Edge Opportunity Scanner')
    parser.add_argument('--threshold', type=float, default=0.10,
                        help='Edge threshold (default: 0.10 = 10%)')
    parser.add_argument('--no-save', action='store_true',
                        help='Don\'t save to database (preview only)')
    
    args = parser.parse_args()
    
    scanner = HighEdgeScanner(edge_threshold=args.threshold)
    signals = scanner.run(auto_save=not args.no_save)
    
    # Exit code based on results
    if signals:
        print(f"\n✅ Found {len(signals)} opportunities with edge >= {args.threshold:.1%}")
        sys.exit(0)
    else:
        print(f"\n⏳ No opportunities >= {args.threshold:.1%} found")
        sys.exit(1)


if __name__ == '__main__':
    main()
