#!/usr/bin/env python3
"""
Paper Trading Module
Simulates trades without executing to validate strategy
Timestamp: 2026-02-03 19:30 GMT+1
"""

import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import time

from utils.backtest import BacktestEngine
from models.edge_estimator import EnsembleEdgeEstimator
from strategies.adaptive_kelly import AdaptiveKelly
from scanner import PolymarketScanner


class PaperTrader:
    """
    Paper trading system - tracks intended trades without executing.
    
    Use this to:
    1. Validate strategy in real markets without risk
    2. Measure slippage vs intended prices
    3. Compare paper results to backtest
    """
    
    def __init__(self, bankroll: float = 1000):
        self.bankroll = bankroll
        self.initial_bankroll = bankroll
        self.estimator = EnsembleEdgeEstimator()
        self.kelly = AdaptiveKelly()
        self.scanner = PolymarketScanner()
        
        # Paper trade log
        self.data_dir = Path('data/paper_trading')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.trades_file = self.data_dir / 'paper_trades.json'
        
        self.trades: List[Dict] = self.load_trades()
    
    def load_trades(self) -> List[Dict]:
        """Load existing paper trades"""
        if self.trades_file.exists():
            with open(self.trades_file, 'r') as f:
                return json.load(f)
        return []
    
    def save_trades(self):
        """Save paper trades to file"""
        with open(self.trades_file, 'w') as f:
            json.dump(self.trades, f, indent=2, default=str)
    
    def generate_signal(self, market: Dict) -> Optional[Dict]:
        """
        Generate trading signal for a market.
        Same logic as live trading, but doesn't execute.
        """
        slug = market['slug']
        question = market['question']
        current_price = market['yes_price']
        
        # Update estimator with current price
        self.estimator.update_price(slug, current_price)
        
        # Get prediction
        estimate = self.estimator.estimate_probability(
            slug, question, current_price
        )
        
        edge = estimate.edge
        
        # Only trade if edge > 5%
        if abs(edge) < 0.05:
            return None
        
        # Calculate position size
        kelly_result = self.kelly.calculate_position_size(
            bankroll=self.bankroll,
            market_price=current_price,
            estimated_prob=estimate.ensemble_probability,
            confidence=estimate.confidence
        )
        
        if kelly_result.position_size <= 0:
            return None
        
        return {
            'timestamp': datetime.now().isoformat(),
            'market_slug': slug,
            'market_question': question,
            'intended_side': kelly_result.side,
            'intended_price': current_price,
            'intended_shares': kelly_result.shares,
            'intended_position_size': kelly_result.position_size,
            'estimated_prob': estimate.ensemble_probability,
            'market_price': current_price,
            'edge': edge,
            'confidence': estimate.confidence,
            'executed': False,
            'executed_price': None,
            'executed_time': None,
            'outcome': None,
            'pnl': None
        }
    
    def run_paper_session(self, max_markets: int = 20):
        """
        Run a paper trading session.
        Generates signals but doesn't execute.
        """
        print("=" * 70)
        print("📊 PAPER TRADING SESSION")
        print("=" * 70)
        print(f"Paper bankroll: ${self.bankroll:,.2f}")
        print(f"Tracking trades WITHOUT execution\n")
        
        # Fetch markets
        print("Fetching active markets...")
        markets = self.scanner.get_active_markets(limit=100)
        
        # Filter to markets with liquidity
        liquid_markets = [
            m for m in markets 
            if m.liquidity > 50000 and 0.05 < m.yes_price < 0.95
        ]
        
        print(f"Found {len(liquid_markets)} liquid markets")
        
        # Generate signals
        signals = []
        for market in liquid_markets[:max_markets]:
            signal = self.generate_signal({
                'slug': market.slug,
                'question': market.question,
                'yes_price': market.yes_price
            })
            if signal:
                signals.append(signal)
        
        print(f"\nGenerated {len(signals)} trading signals:\n")
        
        # Display signals
        for i, signal in enumerate(signals, 1):
            print(f"{i}. {signal['market_question'][:50]}...")
            print(f"   Side: {signal['intended_side']}")
            print(f"   Price: ${signal['intended_price']:.2f}")
            print(f"   Size: ${signal['intended_position_size']:.2f}")
            print(f"   Edge: {signal['edge']:+.1%}")
            print(f"   Conf: {signal['confidence']:.0%}")
            print()
        
        # Save signals as paper trades
        self.trades.extend(signals)
        self.save_trades()
        
        print(f"✅ Saved {len(signals)} paper trades to {self.trades_file}")
        print("\nNext steps:")
        print("1. Wait for markets to resolve")
        print("2. Run update_paper_trades.py to calculate P&L")
        print("3. Compare to backtest results")
        
        return signals
    
    def update_trade_outcomes(self):
        """
        Update paper trades with actual outcomes.
        Run this after markets resolve.
        """
        print("=" * 70)
        print("🔄 UPDATING PAPER TRADE OUTCOMES")
        print("=" * 70)
        
        updated = 0
        unresolved = 0
        
        for trade in self.trades:
            if trade.get('outcome') is not None:
                continue  # Already resolved
            
            slug = trade['market_slug']
            
            # Fetch current market status
            try:
                markets = self.scanner.get_active_markets(limit=200)
                market = next((m for m in markets if m.slug == slug), None)
                
                if market:
                    # Check if market is resolved
                    if market.yes_price >= 0.99 or market.no_price >= 0.99:
                        outcome = 1 if market.yes_price >= 0.99 else 0
                        trade['outcome'] = outcome
                        
                        # Calculate P&L
                        side = trade['intended_side']
                        entry = trade['intended_price']
                        
                        if side == 'YES':
                            pnl = (outcome - entry) * trade['intended_shares']
                        else:
                            pnl = ((1 - outcome) - (1 - entry)) * trade['intended_shares']
                        
                        trade['pnl'] = pnl
                        updated += 1
                        print(f"✅ {slug}: {side} → Outcome: {outcome}, P&L: ${pnl:+.2f}")
                    else:
                        unresolved += 1
                        
            except Exception as e:
                print(f"❌ Error updating {slug}: {e}")
        
        self.save_trades()
        
        print(f"\n✅ Updated {updated} trades")
        print(f"⏳ {unresolved} trades still unresolved")
        
        # Calculate statistics
        resolved_trades = [t for t in self.trades if t.get('outcome') is not None]
        if resolved_trades:
            wins = sum(1 for t in resolved_trades if t.get('pnl', 0) > 0)
            total_pnl = sum(t.get('pnl', 0) for t in resolved_trades)
            
            print(f"\n📊 PAPER TRADING RESULTS:")
            print(f"   Total trades: {len(resolved_trades)}")
            print(f"   Wins: {wins} ({wins/len(resolved_trades):.1%})")
            print(f"   Losses: {len(resolved_trades) - wins}")
            print(f"   Total P&L: ${total_pnl:+.2f}")
            print(f"   Avg per trade: ${total_pnl/len(resolved_trades):+.2f}")
    
    def compare_to_backtest(self):
        """Compare paper results to backtest expectations"""
        print("=" * 70)
        print("📊 PAPER vs BACKTEST COMPARISON")
        print("=" * 70)
        
        resolved = [t for t in self.trades if t.get('outcome') is not None]
        
        if len(resolved) < 10:
            print(f"⚠️  Only {len(resolved)} resolved trades - need more data")
            return
        
        wins = sum(1 for t in resolved if t.get('pnl', 0) > 0)
        win_rate = wins / len(resolved)
        
        print(f"\nYour Paper Trading:")
        print(f"  Win rate: {win_rate:.1%}")
        print(f"  Trades: {len(resolved)}")
        
        print(f"\nBacktest Expectation:")
        print(f"  Win rate: 70-85%")
        print(f"  Edge: 10-20%")
        
        print(f"\nComparison:")
        if win_rate >= 0.65:
            print(f"  ✅ Win rate within expected range")
        elif win_rate >= 0.55:
            print(f"  ⚠️  Win rate slightly lower - monitor for alpha decay")
        else:
            print(f"  ❌ Win rate significantly lower - investigate adverse selection")


def main():
    """Run paper trading"""
    import sys
    
    trader = PaperTrader(bankroll=1000)
    
    if len(sys.argv) > 1 and sys.argv[1] == 'update':
        trader.update_trade_outcomes()
    elif len(sys.argv) > 1 and sys.argv[1] == 'compare':
        trader.compare_to_backtest()
    else:
        trader.run_paper_session(max_markets=20)


if __name__ == '__main__':
    main()
