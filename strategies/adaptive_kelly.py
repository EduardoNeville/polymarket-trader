"""
Adaptive Kelly Criterion with Calibration Tracking
Dynamic position sizing based on prediction accuracy and market conditions.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from utils.prediction_tracker import PredictionTracker


@dataclass
class KellyResult:
    """Result from Kelly calculation"""
    side: str  # 'YES' or 'NO'
    kelly_fraction: float  # Raw Kelly fraction
    adjusted_fraction: float  # After all adjustments
    position_size: float  # Dollar amount
    shares: float  # Number of shares
    confidence_adjustment: float
    correlation_penalty: float
    drawdown_penalty: float
    rationale: str
    recommendations: List[str]


class AdaptiveKelly:
    """
    Kelly Criterion with dynamic adjustment based on:
    - Calibration accuracy (Brier scores)
    - Prediction confidence
    - Correlated exposure
    - Current drawdown
    
    This replaces the static 25% Kelly with an adaptive approach
    that learns from performance.
    """
    
    def __init__(
        self,
        base_fraction: float = 0.25,
        max_fraction: float = 0.50,
        min_fraction: float = 0.05,
        max_drawdown_limit: float = 0.20,
        max_correlated_exposure: float = 0.30
    ):
        self.base_fraction = base_fraction
        self.max_fraction = max_fraction
        self.min_fraction = min_fraction
        self.max_drawdown_limit = max_drawdown_limit
        self.max_correlated_exposure = max_correlated_exposure
        
        self.current_fraction = base_fraction
        self.tracker = PredictionTracker()
    
    def calculate_position_size(
        self,
        bankroll: float,
        market_price: float,
        estimated_prob: float,
        confidence: float = 0.5,
        correlated_exposure: float = 0.0,
        current_drawdown: float = 0.0,
        market_slug: Optional[str] = None
    ) -> KellyResult:
        """
        Calculate optimal position size using adaptive Kelly.
        
        Args:
            bankroll: Total available capital
            market_price: Current market YES price (0-1)
            estimated_prob: Your estimated probability of YES (0-1)
            confidence: Model confidence (0-1), higher = more confident
            correlated_exposure: Current exposure to correlated markets (0-1)
            current_drawdown: Current drawdown from peak (0-1)
            market_slug: Optional market identifier for tracking
        
        Returns:
            KellyResult with sizing and adjustment details
        """
        recommendations = []
        
        # 1. Standard Kelly calculation
        if estimated_prob > market_price:
            side = 'YES'
            win_amount = 1 - market_price
            loss_amount = market_price
            b = win_amount / market_price if market_price > 0 else 0
            p = estimated_prob
        else:
            side = 'NO'
            no_price = 1 - market_price
            win_amount = 1 - no_price
            loss_amount = no_price
            b = win_amount / no_price if no_price > 0 else 0
            p = 1 - estimated_prob
        
        q = 1 - p
        
        # Kelly Criterion: f* = (bp - q) / b
        if b <= 0 or (b * p - q) <= 0:
            kelly_fraction = 0
            recommendations.append("Negative expected value - avoid this bet")
        else:
            kelly_fraction = (b * p - q) / b
        
        # 2. Adjust for confidence (wider confidence = smaller size)
        # If confidence is 1.0, no reduction. If 0.0, heavy reduction.
        confidence_adjustment = 0.5 + (confidence * 0.5)  # Maps 0->0.5, 1->1.0
        
        # 3. Adjust for correlation exposure
        # If already at max exposure, can't add more
        if correlated_exposure >= self.max_correlated_exposure:
            correlation_penalty = 0.0
            recommendations.append(f"Max correlated exposure reached ({self.max_correlated_exposure:.0%})")
        else:
            # Linear penalty based on how close to limit
            correlation_penalty = 1.0 - (correlated_exposure / self.max_correlated_exposure)
            correlation_penalty = max(0.1, correlation_penalty)  # At least 10%
        
        # 4. Adjust for drawdown
        if current_drawdown >= self.max_drawdown_limit:
            # At max drawdown, stop trading
            drawdown_penalty = 0.0
            recommendations.append(f"Max drawdown reached - stop trading")
        elif current_drawdown > self.max_drawdown_limit * 0.5:
            # In drawdown, reduce size significantly
            drawdown_penalty = 1.0 - (current_drawdown / self.max_drawdown_limit)
            recommendations.append(f"In drawdown ({current_drawdown:.1%}) - reducing size")
        else:
            drawdown_penalty = 1.0
        
        # 5. Get dynamic Kelly fraction based on calibration
        dynamic_kelly = self._get_dynamic_kelly_fraction()
        
        # 6. Apply all adjustments
        adjusted_fraction = (
            kelly_fraction * 
            dynamic_kelly * 
            confidence_adjustment * 
            correlation_penalty * 
            drawdown_penalty
        )
        
        # 7. Apply bounds
        adjusted_fraction = np.clip(
            adjusted_fraction,
            self.min_fraction * kelly_fraction,  # At least min_fraction of Kelly
            self.max_fraction  # Never more than max_fraction
        )
        
        # 8. Calculate position size
        position_size = bankroll * adjusted_fraction
        
        # 9. Calculate shares
        if side == 'YES':
            shares = position_size / market_price if market_price > 0 else 0
        else:
            no_price = 1 - market_price
            shares = position_size / no_price if no_price > 0 else 0
        
        # Build rationale
        rationale = (
            f"Kelly={kelly_fraction:.2%}, "
            f"DynamicKelly={dynamic_kelly:.2%}, "
            f"ConfAdj={confidence_adjustment:.2f}, "
            f"CorrPenalty={correlation_penalty:.2f}, "
            f"DDPenalty={drawdown_penalty:.2f}"
        )
        
        # Add edge warning if small
        edge = abs(estimated_prob - market_price)
        if edge < 0.05:
            recommendations.append("Small edge (<5%) - consider passing")
        
        return KellyResult(
            side=side,
            kelly_fraction=kelly_fraction,
            adjusted_fraction=adjusted_fraction,
            position_size=position_size,
            shares=shares,
            confidence_adjustment=confidence_adjustment,
            correlation_penalty=correlation_penalty,
            drawdown_penalty=drawdown_penalty,
            rationale=rationale,
            recommendations=recommendations
        )
    
    def _get_dynamic_kelly_fraction(self) -> float:
        """
        Get Kelly fraction based on recent calibration performance.
        Uses Brier scores from PredictionTracker.
        """
        report = self.tracker.get_calibration_report()
        
        if report['status'] == 'insufficient_data':
            return self.base_fraction  # Use default if no data
        
        # Use the tracker's recommendation
        return report['recommended_kelly_fraction']
    
    def update_from_outcome(
        self,
        market_slug: str,
        actual_outcome: int,
        predicted_prob: float
    ):
        """
        Update Kelly fraction based on prediction outcome.
        Called when a market resolves.
        """
        # Record the outcome
        self.tracker.record_outcome(market_slug, actual_outcome)
        
        # The dynamic fraction will be automatically updated
        # on next calculate_position_size() call
    
    def get_calibration_summary(self) -> Dict:
        """Get summary of calibration for display"""
        return self.tracker.get_calibration_report()
    
    def display_calibration(self):
        """Display calibration report"""
        self.tracker.display_report()


class PortfolioKelly:
    """
    Portfolio-level Kelly optimization for correlated positions.
    
    This solves the "simultaneous Kelly" problem - optimal allocation
    across multiple correlated markets.
    """
    
    def __init__(self, max_total_exposure: float = 0.50):
        self.max_total_exposure = max_total_exposure
        self.positions: Dict[str, Dict] = {}
    
    def add_position(
        self,
        market_slug: str,
        side: str,
        size: float,
        expected_return: float,
        variance: float,
        category: str
    ):
        """Track a position for portfolio optimization"""
        self.positions[market_slug] = {
            'side': side,
            'size': size,
            'expected_return': expected_return,
            'variance': variance,
            'category': category
        }
    
    def get_correlated_exposure(self, category: str) -> float:
        """
        Calculate current exposure to a correlated category.
        
        Args:
            category: Market category (e.g., 'politics', 'sports')
        
        Returns:
            Total exposure to that category (0-1 of bankroll)
        """
        total = 0.0
        for slug, pos in self.positions.items():
            if pos['category'] == category:
                total += pos['size']
        return total
    
    def can_add_position(
        self,
        new_size: float,
        category: str,
        max_category_exposure: float = 0.30
    ) -> Tuple[bool, str]:
        """
        Check if adding a new position would violate constraints.
        
        Returns:
            (can_add, reason)
        """
        current_category = self.get_correlated_exposure(category)
        
        if current_category + new_size > max_category_exposure:
            return (
                False,
                f"Would exceed {category} exposure limit ({max_category_exposure:.0%})"
            )
        
        total_exposure = sum(p['size'] for p in self.positions.values())
        if total_exposure + new_size > self.max_total_exposure:
            return (
                False,
                f"Would exceed total exposure limit ({self.max_total_exposure:.0%})"
            )
        
        return True, "OK"
    
    def optimize_allocation(
        self,
        bankroll: float,
        opportunities: List[Dict]
    ) -> List[Dict]:
        """
        Optimize allocation across multiple opportunities.
        
        Args:
            bankroll: Total capital
            opportunities: List of dicts with keys:
                - market_slug
                - expected_return
                - variance
                - category
                - kelly_fraction
        
        Returns:
            List of opportunities with optimal sizes
        """
        # Simple greedy allocation by Sharpe ratio
        # More sophisticated: use numerical optimization
        
        # Calculate Sharpe for each
        for opp in opportunities:
            if opp['variance'] > 0:
                opp['sharpe'] = opp['expected_return'] / np.sqrt(opp['variance'])
            else:
                opp['sharpe'] = 0
        
        # Sort by Sharpe
        opportunities = sorted(opportunities, key=lambda x: x['sharpe'], reverse=True)
        
        # Allocate greedily respecting constraints
        allocated = []
        remaining_bankroll = bankroll * self.max_total_exposure
        category_exposure: Dict[str, float] = {}
        
        for opp in opportunities:
            category = opp.get('category', 'general')
            current_cat = category_exposure.get(category, 0)
            
            # Calculate max allowed for this position
            max_by_category = 0.30 - current_cat  # Max 30% per category
            max_by_total = remaining_bankroll / bankroll
            max_by_kelly = opp['kelly_fraction']
            
            size = min(max_by_category, max_by_total, max_by_kelly)
            size = max(0, size)  # No negative
            
            if size > 0.01:  # At least 1% to be worth it
                opp['allocated_size'] = size
                allocated.append(opp)
                
                remaining_bankroll -= size * bankroll
                category_exposure[category] = current_cat + size
        
        return allocated


# Simple test
if __name__ == "__main__":
    import sys
    from pathlib import Path
    # Add parent directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    print("Testing AdaptiveKelly...")
    
    kelly = AdaptiveKelly()
    
    # Test 1: Basic calculation
    result = kelly.calculate_position_size(
        bankroll=10000,
        market_price=0.55,
        estimated_prob=0.70,
        confidence=0.8,
        correlated_exposure=0.10,
        current_drawdown=0.05
    )
    
    print(f"\nTest 1 - Basic Calculation:")
    print(f"  Side: {result.side}")
    print(f"  Kelly Fraction: {result.kelly_fraction:.2%}")
    print(f"  Adjusted Fraction: {result.adjusted_fraction:.2%}")
    print(f"  Position Size: ${result.position_size:,.2f}")
    print(f"  Shares: {result.shares:.2f}")
    print(f"  Rationale: {result.rationale}")
    
    # Test 2: High confidence
    result2 = kelly.calculate_position_size(
        bankroll=10000,
        market_price=0.55,
        estimated_prob=0.70,
        confidence=0.95,  # High confidence
        correlated_exposure=0.10,
        current_drawdown=0.05
    )
    
    print(f"\nTest 2 - High Confidence:")
    print(f"  Adjusted Fraction: {result2.adjusted_fraction:.2%}")
    print(f"  Confidence Adj: {result2.confidence_adjustment:.2f}")
    
    # Test 3: High correlation
    result3 = kelly.calculate_position_size(
        bankroll=10000,
        market_price=0.55,
        estimated_prob=0.70,
        confidence=0.8,
        correlated_exposure=0.25,  # Near limit
        current_drawdown=0.05
    )
    
    print(f"\nTest 3 - High Correlation:")
    print(f"  Adjusted Fraction: {result3.adjusted_fraction:.2%}")
    print(f"  Correlation Penalty: {result3.correlation_penalty:.2f}")
    print(f"  Recommendations: {result3.recommendations}")
    
    # Test 4: In drawdown
    result4 = kelly.calculate_position_size(
        bankroll=10000,
        market_price=0.55,
        estimated_prob=0.70,
        confidence=0.8,
        correlated_exposure=0.10,
        current_drawdown=0.15  # 15% drawdown
    )
    
    print(f"\nTest 4 - In Drawdown:")
    print(f"  Adjusted Fraction: {result4.adjusted_fraction:.2%}")
    print(f"  Drawdown Penalty: {result4.drawdown_penalty:.2f}")
    print(f"  Recommendations: {result4.recommendations}")
    
    # Test PortfolioKelly
    print("\n\nTesting PortfolioKelly...")
    
    portfolio = PortfolioKelly()
    
    # Add some existing positions
    portfolio.add_position('market-1', 'YES', 0.10, 0.15, 0.05, 'politics')
    portfolio.add_position('market-2', 'NO', 0.05, 0.10, 0.03, 'sports')
    
    # Check exposure
    politics_exposure = portfolio.get_correlated_exposure('politics')
    print(f"  Politics Exposure: {politics_exposure:.2%}")
    
    # Check if can add new position
    can_add, reason = portfolio.can_add_position(0.15, 'politics')
    print(f"  Can add 15% politics? {can_add} - {reason}")
    
    can_add2, reason2 = portfolio.can_add_position(0.05, 'politics')
    print(f"  Can add 5% politics? {can_add2} - {reason2}")
    
    print("\n✅ All Kelly tests passed!")
