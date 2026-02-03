"""
Slippage Model
Estimates execution costs based on market conditions
Timestamp: 2026-02-03 20:35 GMT+1
"""

import json
from typing import Dict, List, Tuple
import statistics


class SlippageModel:
    """
    Models market impact and slippage for trade execution.
    
    Based on research and empirical data from Polymarket.
    """
    
    def __init__(self):
        # Base slippage for different liquidity levels
        # Format: (min_liquidity, max_liquidity, base_slippage_pct)
        self.liquidity_tiers = [
            (0, 10000, 0.05),      # <$10K: 5% base slippage
            (10000, 50000, 0.03),  # $10-50K: 3% base
            (50000, 100000, 0.02), # $50-100K: 2% base
            (100000, 500000, 0.01),# $100-500K: 1% base
            (500000, float('inf'), 0.005)  # >$500K: 0.5% base
        ]
    
    def get_base_slippage(self, liquidity: float) -> float:
        """Get base slippage for given liquidity tier"""
        for min_liq, max_liq, slippage in self.liquidity_tiers:
            if min_liq <= liquidity < max_liq:
                return slippage
        return 0.05  # Default 5%
    
    def estimate_slippage(
        self,
        position_size: float,
        liquidity: float,
        spread: float = 0.02
    ) -> Dict:
        """
        Estimate total slippage for a trade.
        
        Components:
        1. Spread cost (bid-ask)
        2. Market impact (position size relative to liquidity)
        3. Volatility adjustment
        
        Returns:
            Dict with slippage breakdown
        """
        # Base slippage from liquidity tier
        base_slippage = self.get_base_slippage(liquidity)
        
        # Market impact: increases with position size
        # Formula: impact = base * (position / liquidity) ^ 0.6
        if liquidity > 0:
            size_ratio = position_size / liquidity
            market_impact = base_slippage * (size_ratio ** 0.6)
        else:
            market_impact = base_slippage
        
        # Spread cost
        spread_cost = spread / 2  # Assume we pay half the spread
        
        # Total slippage (capped at 10%)
        total_slippage = min(spread_cost + market_impact, 0.10)
        
        return {
            'spread_cost': spread_cost,
            'market_impact': market_impact,
            'base_slippage': base_slippage,
            'total_slippage': total_slippage,
            'position_size': position_size,
            'liquidity': liquidity,
            'size_ratio': position_size / liquidity if liquidity > 0 else 0
        }
    
    def get_slippage_table(
        self,
        position_sizes: List[float] = None,
        liquidities: List[float] = None
    ) -> List[Dict]:
        """Generate slippage table for various scenarios"""
        if position_sizes is None:
            position_sizes = [50, 100, 250, 500, 1000]
        
        if liquidities is None:
            liquidities = [10000, 25000, 50000, 100000, 250000]
        
        results = []
        for liq in liquidities:
            for pos in position_sizes:
                if pos <= liq * 0.05:  # Only show if position < 5% of liquidity
                    est = self.estimate_slippage(pos, liq)
                    results.append({
                        'position': pos,
                        'liquidity': liq,
                        'slippage_pct': est['total_slippage'] * 100,
                        'cost': pos * est['total_slippage']
                    })
        
        return results
    
    def recommend_position_size(
        self,
        liquidity: float,
        max_slippage: float = 0.03
    ) -> float:
        """
        Recommend max position size for given slippage tolerance.
        
        Args:
            liquidity: Market liquidity
            max_slippage: Maximum acceptable slippage (default 3%)
            
        Returns:
            Recommended position size
        """
        # Binary search for position size
        low, high = 0, liquidity * 0.2  # Max 20% of liquidity
        
        while high - low > 1:
            mid = (low + high) / 2
            est = self.estimate_slippage(mid, liquidity)
            
            if est['total_slippage'] <= max_slippage:
                low = mid
            else:
                high = mid
        
        return low


if __name__ == "__main__":
    model = SlippageModel()
    
    print("=" * 70)
    print("📊 SLIPPAGE MODEL")
    print("=" * 70)
    
    # Generate slippage table
    table = model.get_slippage_table()
    
    print("\nSlippage by Position Size and Liquidity:")
    print(f"{'Position':<12} {'Liquidity':<15} {'Slippage':<12} {'Cost':<12}")
    print("-" * 70)
    
    for row in table[:20]:  # Show first 20
        print(f"${row['position']:<11,.0f} "
              f"${row['liquidity']:<14,.0f} "
              f"{row['slippage_pct']:>6.2f}%      "
              f"${row['cost']:>6.2f}")
    
    # Recommendations
    print("\n" + "=" * 70)
    print("💡 RECOMMENDATIONS (3% max slippage):")
    print("=" * 70)
    
    for liq in [10000, 25000, 50000, 100000]:
        rec = model.recommend_position_size(liq, max_slippage=0.03)
        print(f"  Liquidity ${liq:>8,.0f}: Max position ${rec:>6,.0f}")
    
    print("=" * 70)
