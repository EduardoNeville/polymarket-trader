"""
Paper Trading Signal Generator
Generates and records trading signals without executing
Timestamp: 2026-02-03 20:26 GMT+1
"""

from datetime import datetime
from typing import Dict, List, Optional
import json

from utils.paper_trading_db import PaperTradingDB
from utils.take_profit_calculator import calculate_take_profit, calculate_stop_loss
from models.edge_estimator import EnsembleEdgeEstimator
from strategies.adaptive_kelly import AdaptiveKelly
from scanner import PolymarketScanner, Market


class PaperTradingSignalGenerator:
    """
    Generates paper trading signals and saves them to database.
    
    Features:
    - Scans markets for opportunities
    - Generates signals using AI ensemble
    - Calculates position sizes with Kelly
    - Records to database (doesn't execute)
    """
    
    def __init__(self, bankroll: float = 1000, min_edge: float = 0.05):
        self.bankroll = bankroll
        self.min_edge = min_edge
        self.db = PaperTradingDB()
        self.estimator = EnsembleEdgeEstimator()
        self.kelly = AdaptiveKelly()
        self.scanner = PolymarketScanner()
    
    def should_trade_market(self, market: Market) -> bool:
        """
        Filter markets suitable for trading.
        
        Criteria:
        - Sufficient liquidity (>$50K)
        - Price not at extremes (<0.95, >0.05)
        - Active market
        """
        # Check liquidity
        if market.liquidity < 50000:
            return False
        
        # Check price not at extremes
        if market.yes_price >= 0.98 or market.yes_price <= 0.02:
            return False
        
        # Check has valid end date
        if not market.end_date:
            return False
        
        return True
    
    def generate_signal(self, market: Market) -> Optional[Dict]:
        """
        Generate trading signal for a market.
        
        Returns:
            Signal dict or None if no trade
        """
        # Update estimator with price history
        self.estimator.update_price(market.slug, market.yes_price)
        
        # Get ensemble prediction
        estimate = self.estimator.estimate_probability(
            market_slug=market.slug,
            market_question=market.question,
            current_price=market.yes_price,
            category=market.category
        )
        
        # Check minimum edge
        if abs(estimate.edge) < self.min_edge:
            return None
        
        # Calculate position size
        kelly_result = self.kelly.calculate_position_size(
            bankroll=self.bankroll,
            market_price=market.yes_price,
            estimated_prob=estimate.ensemble_probability,
            confidence=estimate.confidence
        )
        
        if kelly_result.position_size <= 0:
            return None
        
        # Calculate Take-Profit level (75% edge capture)
        tp_level = calculate_take_profit(
            entry_price=market.yes_price,
            estimated_prob=estimate.ensemble_probability,
            side=kelly_result.side,
            edge_capture_ratio=0.75,
            min_edge_threshold=self.min_edge
        )
        
        # Calculate Stop-Loss level (50% risk)
        sl_level = calculate_stop_loss(
            entry_price=market.yes_price,
            side=kelly_result.side,
            risk_pct=0.50
        )
        
        signal = {
            'timestamp': datetime.now().isoformat(),
            'market_slug': market.slug,
            'market_question': market.question,
            'intended_side': kelly_result.side,
            'intended_price': market.yes_price,
            'intended_size': kelly_result.position_size,
            'estimated_prob': estimate.ensemble_probability,
            'market_price': market.yes_price,
            'edge': estimate.edge,
            'confidence': estimate.confidence,
            'strategy': 'ensemble',
            'recommendation': estimate.recommendation,
            'take_profit_price': tp_level.target_price if tp_level else None,
            'take_profit_pct': tp_level.target_pct_move if tp_level else None,
            'stop_loss_price': sl_level.stop_price if sl_level else None,
            'stop_loss_pct': sl_level.stop_pct_move if sl_level else None,
        }
        
        return signal
    
    def get_current_exposure(self) -> float:
        """Get total exposure from open trades"""
        open_trades = self.db.get_open_trades()
        return sum(t.get('intended_size', 0) for t in open_trades)
    
    def generate_signals_for_markets(
        self,
        max_markets: int = 50,
        save_to_db: bool = True
    ) -> List[Dict]:
        """
        Generate signals for multiple markets.
        
        Args:
            max_markets: Maximum markets to analyze
            save_to_db: Whether to save signals to database
            
        Returns:
            List of signal dictionaries
        """
        print(f"Scanning for paper trading signals...")
        
        # Check current exposure
        current_exposure = self.get_current_exposure()
        available_capital = self.bankroll - current_exposure
        
        print(f"Current exposure: ${current_exposure:.2f} / ${self.bankroll:.2f}")
        print(f"Available capital: ${available_capital:.2f}")
        
        # Don't trade if less than $20 available (min trade size)
        MIN_TRADE_SIZE = 20
        if available_capital < MIN_TRADE_SIZE:
            print(f"❌ Insufficient capital. Need at least ${MIN_TRADE_SIZE} to trade.")
            return []
        
        # NO MAX POSITIONS - take as many as capital allows
        open_trade_count = len(self.db.get_open_trades())
        print(f"Open positions: {open_trade_count} (no limit, capital constrained only)")
        
        # Fetch markets
        markets = self.scanner.get_active_markets(limit=100)
        print(f"Fetched {len(markets)} markets")
        
        # Filter to suitable markets
        suitable = [m for m in markets if self.should_trade_market(m)]
        print(f"{len(suitable)} markets pass filters")
        
        # Generate signals (capital constrained only - no position count limit)
        signals = []
        for market in suitable[:max_markets]:
            # Check if we still have capital
            if available_capital < MIN_TRADE_SIZE:
                break
            
            signal = self.generate_signal(market)
            if signal:
                # Size based on available capital (can use up to all remaining)
                position_size = min(signal['intended_size'], available_capital)
                if position_size < MIN_TRADE_SIZE:  # Minimum $20 trade
                    continue
                
                signal['intended_size'] = position_size
                available_capital -= position_size
                signals.append(signal)
        
        print(f"Generated {len(signals)} trading signals")
        
        # Save to database
        if save_to_db and signals:
            saved_count = 0
            for signal in signals:
                try:
                    self.db.save_trade(signal)
                    saved_count += 1
                except Exception as e:
                    print(f"Error saving signal: {e}")
            
            print(f"Saved {saved_count} signals to database")
        
        return signals
    
    def display_signals(self, signals: List[Dict]):
        """Display generated signals in readable format"""
        if not signals:
            print("\nNo signals generated.")
            return
        
        print("\n" + "=" * 80)
        print("📊 PAPER TRADING SIGNALS")
        print("=" * 80)
        
        for i, signal in enumerate(signals, 1):
            print(f"\n{i}. {signal['market_question'][:60]}...")
            print(f"   Side:      {signal['intended_side']}")
            print(f"   Price:     ${signal['intended_price']:.2f}")
            print(f"   Size:      ${signal['intended_size']:.2f}")
            print(f"   Edge:      {signal['edge']:+.1%}")
            print(f"   Conf:      {signal['confidence']:.0%}")
            print(f"   Strategy:  {signal['strategy']}")
            
            # Display TP/SL info
            tp = signal.get('take_profit_price')
            sl = signal.get('stop_loss_price')
            if tp:
                print(f"   🎯 TP:      ${tp:.2f} ({signal['take_profit_pct']:.1%})")
            if sl:
                side = signal['intended_side']
                sl_pct = signal.get('stop_loss_pct', 0) * 100
                print(f"   🛑 SL:      ${sl:.2f} ({sl_pct:.0f}% risk)")
        
        print("\n" + "=" * 80)
        print(f"Total signals: {len(signals)}")
        print("=" * 80)
    
    def get_signal_statistics(self, signals: List[Dict]) -> Dict:
        """Calculate statistics for generated signals"""
        if not signals:
            return {}
        
        edges = [s['edge'] for s in signals]
        confidences = [s['confidence'] for s in signals]
        sizes = [s['intended_size'] for s in signals]
        
        yes_signals = sum(1 for s in signals if s['intended_side'] == 'YES')
        no_signals = sum(1 for s in signals if s['intended_side'] == 'NO')
        
        return {
            'total_signals': len(signals),
            'yes_signals': yes_signals,
            'no_signals': no_signals,
            'avg_edge': sum(edges) / len(edges),
            'max_edge': max(edges),
            'min_edge': min(edges),
            'avg_confidence': sum(confidences) / len(confidences),
            'avg_position_size': sum(sizes) / len(sizes),
            'total_exposure': sum(sizes)
        }


# Command-line interface
if __name__ == "__main__":
    import sys
    
    print("=" * 80)
    print("🚀 PAPER TRADING SIGNAL GENERATOR")
    print("=" * 80)
    
    # Parse arguments
    max_markets = 20
    if len(sys.argv) > 1:
        try:
            max_markets = int(sys.argv[1])
        except ValueError:
            pass
    
    bankroll = 1000
    if len(sys.argv) > 2:
        try:
            bankroll = float(sys.argv[2])
        except ValueError:
            pass
    
    print(f"\nConfiguration:")
    print(f"  Max markets to analyze: {max_markets}")
    print(f"  Paper bankroll: ${bankroll:,.2f}")
    print(f"  Min edge threshold: 5%")
    print()
    
    # Generate signals
    generator = PaperTradingSignalGenerator(bankroll=bankroll)
    signals = generator.generate_signals_for_markets(
        max_markets=max_markets,
        save_to_db=True
    )
    
    # Display results
    generator.display_signals(signals)
    
    # Show statistics
    stats = generator.get_signal_statistics(signals)
    if stats:
        print("\n📈 SIGNAL STATISTICS:")
        print(f"  Average edge:      {stats['avg_edge']:+.1%}")
        print(f"  Average confidence: {stats['avg_confidence']:.0%}")
        print(f"  Total exposure:    ${stats['total_exposure']:.2f}")
        print(f"  YES signals:       {stats['yes_signals']}")
        print(f"  NO signals:        {stats['no_signals']}")
    
    print("\n✅ Signals generated and saved to database!")
    print("\nNext steps:")
    print("1. Monitor these markets for resolution")
    print("2. Run: python3 -c \"from utils.paper_trading_updater import update_outcomes; update_outcomes()\"")
    print("3. View results in database")
