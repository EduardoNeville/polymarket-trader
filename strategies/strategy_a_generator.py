"""
Strategy A: Hard 7-Day Time Filter
Only trades markets resolving within 7 days.
Maximum capital velocity strategy.
"""

import sys
sys.path.insert(0, '/home/eduardoneville/projects/polymarket-trader')

from datetime import datetime, timezone
from typing import Dict, List, Optional
from utils.paper_trading_db import PaperTradingDB
from utils.take_profit_calculator import calculate_take_profit, calculate_stop_loss
from models.edge_estimator import EnsembleEdgeEstimator
from strategies.adaptive_kelly import AdaptiveKelly
from scanner import PolymarketScanner, Market


class StrategyASignalGenerator:
    """
    Strategy A: Hard 7-day time filter.
    - Only markets resolving <= 7 days
    - Maximize capital turnover
    - Weekly feedback cycle
    """
    
    STRATEGY_NAME = "Strategy_A_7day"
    DB_PATH = "data/paper_trading_strategy_a.db"
    
    def __init__(self, bankroll: float = 1000, min_edge: float = 0.05):
        self.bankroll = bankroll
        self.min_edge = min_edge
        self.db = PaperTradingDB(db_path=self.DB_PATH)
        self.estimator = EnsembleEdgeEstimator()
        self.kelly = AdaptiveKelly()
        self.scanner = PolymarketScanner()
    
    def calculate_time_to_resolution(self, market: Market) -> Optional[float]:
        """Calculate days until market resolution."""
        if not market.end_date:
            return None
        
        try:
            end = datetime.fromisoformat(market.end_date.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            delta = end - now
            return max(0, delta.days + delta.seconds / 86400)
        except (ValueError, TypeError):
            return None
    
    def should_trade_market(self, market: Market) -> bool:
        """
        Hard filter: Only markets resolving within 7 days.
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
        
        # HARD 7-DAY FILTER
        days = self.calculate_time_to_resolution(market)
        if days is None or days > 7:
            return False
        
        return True
    
    def generate_signal(self, market: Market) -> Optional[Dict]:
        """Generate trading signal for a market."""
        self.estimator.update_price(market.slug, market.yes_price)
        
        estimate = self.estimator.estimate_probability(
            market_slug=market.slug,
            market_question=market.question,
            current_price=market.yes_price,
            category=market.category
        )
        
        if abs(estimate.edge) < self.min_edge:
            return None
        
        kelly_result = self.kelly.calculate_position_size(
            bankroll=self.bankroll,
            market_price=market.yes_price,
            estimated_prob=estimate.ensemble_probability,
            confidence=estimate.confidence
        )
        
        if kelly_result.position_size <= 0:
            return None
        
        tp_level = calculate_take_profit(
            entry_price=market.yes_price,
            estimated_prob=estimate.ensemble_probability,
            side=kelly_result.side,
            edge_capture_ratio=0.75,
            min_edge_threshold=self.min_edge
        )
        
        sl_level = calculate_stop_loss(
            entry_price=market.yes_price,
            side=kelly_result.side,
            risk_pct=0.50
        )
        
        days = self.calculate_time_to_resolution(market)
        
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
            'strategy': self.STRATEGY_NAME,
            'recommendation': estimate.recommendation,
            'take_profit_price': tp_level.target_price if tp_level else None,
            'take_profit_pct': tp_level.target_pct_move if tp_level else None,
            'stop_loss_price': sl_level.stop_price if sl_level else None,
            'stop_loss_pct': sl_level.stop_pct_move if sl_level else None,
            'days_to_resolve': days,
            'resolution_date': market.end_date,
            'priority_score': abs(estimate.edge) * 3.0,  # 3x for <7 days
        }
        
        return signal
    
    def get_current_exposure(self) -> float:
        """Get total exposure from open trades."""
        open_trades = self.db.get_open_trades()
        return sum(t.get('intended_size', 0) for t in open_trades)
    
    def generate_signals(self, max_markets: int = 100) -> List[Dict]:
        """Generate signals for Strategy A."""
        current_exposure = self.get_current_exposure()
        available_capital = self.bankroll - current_exposure
        
        MIN_TRADE_SIZE = 20
        if available_capital < MIN_TRADE_SIZE:
            print(f"[{self.STRATEGY_NAME}] Insufficient capital: ${available_capital:.2f}")
            return []
        
        markets = self.scanner.get_active_markets(limit=200)
        suitable = [m for m in markets if self.should_trade_market(m)]
        
        # Generate signals and sort by edge
        signals = []
        for market in suitable:
            signal = self.generate_signal(market)
            if signal:
                signals.append(signal)
        
        # Sort by edge (highest first)
        signals.sort(key=lambda x: abs(x['edge']), reverse=True)
        
        # Allocate capital
        allocated = []
        for signal in signals[:max_markets]:
            if available_capital < MIN_TRADE_SIZE:
                break
            
            position_size = min(signal['intended_size'], available_capital)
            if position_size < MIN_TRADE_SIZE:
                continue
            
            signal['intended_size'] = position_size
            available_capital -= position_size
            allocated.append(signal)
        
        # Save to database
        saved_count = 0
        for signal in allocated:
            try:
                self.db.save_trade(signal)
                saved_count += 1
            except Exception as e:
                print(f"[{self.STRATEGY_NAME}] Error saving: {e}")
        
        return allocated
    
    def run_cycle(self):
        """Run one complete trading cycle."""
        open_trades = self.db.get_open_trades()
        closed_trades = self.db.get_closed_trades()
        exposure = self.get_current_exposure()
        available = self.bankroll - exposure
        
        print(f"\n[{self.STRATEGY_NAME}] Cycle Start")
        print(f"  Open: {len(open_trades)} | Closed: {len(closed_trades)}")
        print(f"  Exposure: ${exposure:.2f} | Available: ${available:.2f}")
        
        signals = self.generate_signals()
        
        print(f"  New signals: {len(signals)}")
        print(f"[{self.STRATEGY_NAME}] Cycle Complete\n")
        
        return signals


if __name__ == "__main__":
    print("=" * 70)
    print(f"🚀 {StrategyASignalGenerator.STRATEGY_NAME}")
    print("   Hard 7-Day Time Filter")
    print("=" * 70)
    
    gen = StrategyASignalGenerator(bankroll=1000)
    signals = gen.run_cycle()
    
    if signals:
        print(f"\nGenerated {len(signals)} signals")
        for s in signals[:5]:
            print(f"  - {s['market_question'][:50]}")
            print(f"    Side: {s['intended_side']} | Edge: {s['edge']:.1%} | "
                  f"Days: {s['days_to_resolve']:.0f}")
    else:
        print("\nNo signals generated (no suitable markets or capital)")
