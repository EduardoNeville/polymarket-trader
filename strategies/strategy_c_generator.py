"""
Strategy C: Tiered Approach
Strict tiers with capital allocation limits:
- Tier 1 (<30 days): 70% max, 2.5x multiplier, 5% min edge
- Tier 2 (30-90 days): 30% max, 1.0x multiplier, 7% min edge
- Tier 3 (>90 days): Exception only (>15% edge), 10% max single position
"""

import sys
sys.path.insert(0, '/home/eduardoneville/projects/polymarket-trader')

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from utils.paper_trading_db import PaperTradingDB
from utils.take_profit_calculator import calculate_take_profit, calculate_stop_loss
from models.edge_estimator import EnsembleEdgeEstimator
from strategies.adaptive_kelly import AdaptiveKelly
from scanner import PolymarketScanner, Market


class StrategyCSignalGenerator:
    """
    Strategy C: Tiered capital allocation by resolution time.
    Most sophisticated approach with strict tier limits.
    """
    
    STRATEGY_NAME = "Strategy_C_Tiered"
    DB_PATH = "data/paper_trading_strategy_c.db"
    
    # Tier Configuration
    TIER_LIMITS = {
        'tier1': {'max_pct': 0.70, 'multiplier': 2.5, 'min_edge': 0.05, 'max_days': 30},
        'tier2': {'max_pct': 0.30, 'multiplier': 1.0, 'min_edge': 0.07, 'max_days': 90},
        'tier3': {'max_pct': 0.10, 'multiplier': 0.5, 'min_edge': 0.15, 'max_days': float('inf')},
    }
    
    def __init__(self, bankroll: float = 1000):
        self.bankroll = bankroll
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
    
    def assign_tier(self, days_to_resolve: float) -> str:
        """Assign market to tier based on resolution time."""
        if days_to_resolve < 30:
            return 'tier1'
        elif days_to_resolve < 90:
            return 'tier2'
        else:
            return 'tier3'
    
    def get_tier_exposure(self, tier: str) -> float:
        """Get current exposure for a specific tier."""
        open_trades = self.db.get_open_trades()
        total = 0
        for t in open_trades:
            days = t.get('days_to_resolve', 999)
            trade_tier = self.assign_tier(days)
            if trade_tier == tier:
                total += t.get('intended_size', 0)
        return total
    
    def can_allocate_to_tier(self, tier: str, amount: float) -> Tuple[bool, str]:
        """Check if we can allocate more capital to a tier."""
        current = self.get_tier_exposure(tier)
        max_allowed = self.bankroll * self.TIER_LIMITS[tier]['max_pct']
        
        if current + amount > max_allowed:
            remaining = max_allowed - current
            return False, f"Tier {tier} limit reached (${remaining:.2f} remaining)"
        
        return True, "OK"
    
    def should_trade_market(self, market: Market) -> bool:
        """Basic filters."""
        if market.liquidity < 50000:
            return False
        
        if market.yes_price >= 0.98 or market.yes_price <= 0.02:
            return False
        
        if not market.end_date:
            return False
        
        days = self.calculate_time_to_resolution(market)
        if days is None or days > 365 * 2:
            return False
        
        return True
    
    def generate_signal(self, market: Market) -> Optional[Dict]:
        """Generate trading signal with tier assignment."""
        days = self.calculate_time_to_resolution(market)
        tier = self.assign_tier(days)
        tier_config = self.TIER_LIMITS[tier]
        
        self.estimator.update_price(market.slug, market.yes_price)
        
        estimate = self.estimator.estimate_probability(
            market_slug=market.slug,
            market_question=market.question,
            current_price=market.yes_price,
            category=market.category
        )
        
        # Check tier-specific minimum edge
        if abs(estimate.edge) < tier_config['min_edge']:
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
            min_edge_threshold=tier_config['min_edge']
        )
        
        sl_level = calculate_stop_loss(
            entry_price=market.yes_price,
            side=kelly_result.side,
            risk_pct=0.50
        )
        
        priority_score = abs(estimate.edge) * tier_config['multiplier']
        
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
            'tier': tier,
            'tier_multiplier': tier_config['multiplier'],
            'tier_min_edge': tier_config['min_edge'],
            'priority_score': priority_score,
        }
        
        return signal
    
    def get_current_exposure(self) -> float:
        """Get total exposure from open trades."""
        open_trades = self.db.get_open_trades()
        return sum(t.get('intended_size', 0) for t in open_trades)
    
    def generate_signals(self, max_markets: int = 100) -> List[Dict]:
        """Generate signals with tiered allocation."""
        current_exposure = self.get_current_exposure()
        available_capital = self.bankroll - current_exposure
        
        MIN_TRADE_SIZE = 20
        if available_capital < MIN_TRADE_SIZE:
            print(f"[{self.STRATEGY_NAME}] Insufficient capital: ${available_capital:.2f}")
            return []
        
        markets = self.scanner.get_active_markets(limit=300)
        suitable = [m for m in markets if self.should_trade_market(m)]
        
        # Generate all signals with tier info
        all_signals = []
        for market in suitable:
            signal = self.generate_signal(market)
            if signal:
                all_signals.append(signal)
        
        # Sort by priority score (tier-weighted edge)
        all_signals.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Allocate with tier limits
        allocated = []
        tier_allocations = {'tier1': 0, 'tier2': 0, 'tier3': 0}
        
        for signal in all_signals:
            if available_capital < MIN_TRADE_SIZE:
                break
            
            tier = signal['tier']
            position_size = min(signal['intended_size'], available_capital)
            
            if position_size < MIN_TRADE_SIZE:
                continue
            
            # Check tier limit
            can_allocate, reason = self.can_allocate_to_tier(tier, position_size)
            if not can_allocate:
                # Skip if tier full (except tier1 which is priority)
                if tier != 'tier1':
                    continue
                # For tier1, try smaller size
                remaining = (self.bankroll * self.TIER_LIMITS[tier]['max_pct']) - self.get_tier_exposure(tier)
                if remaining >= MIN_TRADE_SIZE:
                    position_size = min(position_size, remaining)
                else:
                    continue
            
            signal['intended_size'] = position_size
            available_capital -= position_size
            tier_allocations[tier] += position_size
            allocated.append(signal)
        
        # Save to database
        for signal in allocated:
            try:
                self.db.save_trade(signal)
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
        
        # Show current tier allocation
        t1 = self.get_tier_exposure('tier1')
        t2 = self.get_tier_exposure('tier2')
        t3 = self.get_tier_exposure('tier3')
        print(f"  Tier allocation: T1=${t1:.0f} (max ${self.bankroll*0.7:.0f}) | "
              f"T2=${t2:.0f} (max ${self.bankroll*0.3:.0f}) | "
              f"T3=${t3:.0f} (max ${self.bankroll*0.1:.0f})")
        
        signals = self.generate_signals()
        
        if signals:
            new_t1 = sum(1 for s in signals if s['tier'] == 'tier1')
            new_t2 = sum(1 for s in signals if s['tier'] == 'tier2')
            new_t3 = sum(1 for s in signals if s['tier'] == 'tier3')
            print(f"  New signals by tier: T1={new_t1}, T2={new_t2}, T3={new_t3}")
        
        print(f"  Total new signals: {len(signals)}")
        print(f"[{self.STRATEGY_NAME}] Cycle Complete\n")
        
        return signals


if __name__ == "__main__":
    print("=" * 70)
    print(f"🚀 {StrategyCSignalGenerator.STRATEGY_NAME}")
    print("   Tiered Capital Allocation")
    print("   T1: <30d (70%, 5% edge, 2.5x)")
    print("   T2: 30-90d (30%, 7% edge, 1.0x)")
    print("   T3: >90d (10%, 15% edge, 0.5x)")
    print("=" * 70)
    
    gen = StrategyCSignalGenerator(bankroll=1000)
    signals = gen.run_cycle()
    
    if signals:
        print(f"\nGenerated {len(signals)} signals")
        for s in signals[:5]:
            tier = s['tier']
            print(f"  - {s['market_question'][:40]}")
            print(f"    Tier {tier} | Edge: {s['edge']:.1%} (min {s['tier_min_edge']:.0%}) | "
                  f"Days: {s['days_to_resolve']:.0f}")
    else:
        print("\nNo signals generated (no suitable markets or capital)")
