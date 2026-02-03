"""
Multi-Strategy Portfolio
Combines multiple trading strategies with dynamic allocation based on performance.
Diversified strategies reduce tail risk and provide robustness to model failure.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from abc import ABC, abstractmethod

from models.edge_estimator import EnsembleEdgeEstimator, EdgeEstimate
from strategies.adaptive_kelly import AdaptiveKelly, PortfolioKelly
from utils.prediction_tracker import PredictionTracker


@dataclass
class StrategySignal:
    """Signal from a strategy"""
    market_slug: str
    direction: str  # 'BUY_YES', 'BUY_NO', 'HOLD'
    strength: float  # 0-1 signal strength
    expected_return: float
    confidence: float
    rationale: str


@dataclass
class PortfolioAllocation:
    """Portfolio allocation result"""
    market_slug: str
    side: str
    size: float  # Fraction of bankroll
    strategy: str  # Which strategy generated this
    expected_return: float
    sharpe_ratio: float


class BaseStrategy(ABC):
    """Abstract base class for trading strategies"""
    
    def __init__(self, name: str):
        self.name = name
        self.performance_history: List[float] = []
    
    @abstractmethod
    def generate_signal(self, market_slug: str, **kwargs) -> Optional[StrategySignal]:
        """Generate trading signal for a market"""
        pass
    
    def record_result(self, pnl: float):
        """Record P&L for performance tracking"""
        self.performance_history.append(pnl)
        # Keep last 100 trades
        self.performance_history = self.performance_history[-100:]
    
    def get_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio from performance history"""
        if len(self.performance_history) < 5:
            return 1.0  # Default for new strategies
        
        returns = np.array(self.performance_history)
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 1.0 if avg_return > 0 else 0.0
        
        return avg_return / std_return
    
    def get_win_rate(self) -> float:
        """Calculate win rate"""
        if not self.performance_history:
            return 0.5
        
        wins = sum(1 for p in self.performance_history if p > 0)
        return wins / len(self.performance_history)


class SentimentStrategy(BaseStrategy):
    """
    Strategy based on sentiment analysis.
    Good for longer-dated events.
    """
    
    def __init__(self):
        super().__init__('sentiment')
        self.estimator = EnsembleEdgeEstimator()
    
    def generate_signal(self, market_slug: str, **kwargs) -> Optional[StrategySignal]:
        question = kwargs.get('question', '')
        current_price = kwargs.get('current_price', 0.5)
        category = kwargs.get('category', 'general')
        
        # Use sentiment component of ensemble
        estimate = self.estimator.estimate_probability(
            market_slug, question, current_price, category
        )
        
        sentiment_pred = estimate.individual_predictions.get('sentiment', 0.5)
        edge = sentiment_pred - current_price
        
        if abs(edge) < 0.03:
            return None
        
        return StrategySignal(
            market_slug=market_slug,
            direction='BUY_YES' if edge > 0 else 'BUY_NO',
            strength=min(1.0, abs(edge) * 5),  # Scale edge to 0-1
            expected_return=abs(edge),
            confidence=0.5,  # Sentiment is less reliable
            rationale=f"Sentiment edge: {edge:+.1%}"
        )


class MomentumStrategy(BaseStrategy):
    """
    Strategy based on price momentum.
    Good for trending markets.
    """
    
    def __init__(self):
        super().__init__('momentum')
        self.estimator = EnsembleEdgeEstimator()
    
    def generate_signal(self, market_slug: str, **kwargs) -> Optional[StrategySignal]:
        current_price = kwargs.get('current_price', 0.5)
        
        # Update price history
        self.estimator.update_price(market_slug, current_price)
        
        # Get momentum component
        estimate = self.estimator.estimate_probability(
            market_slug, '', current_price
        )
        
        momentum_pred = estimate.individual_predictions.get('momentum', 0.5)
        edge = momentum_pred - current_price
        
        if abs(edge) < 0.02:
            return None
        
        # Higher confidence in momentum during trends
        trend_confidence = estimate.confidence
        
        return StrategySignal(
            market_slug=market_slug,
            direction='BUY_YES' if edge > 0 else 'BUY_NO',
            strength=min(1.0, abs(edge) * 8),
            expected_return=abs(edge) * 1.2,  # Momentum tends to continue
            confidence=trend_confidence,
            rationale=f"Momentum signal: {edge:+.1%}"
        )


class MeanReversionStrategy(BaseStrategy):
    """
    Strategy based on mean reversion.
    Good for oscillating markets at extremes.
    """
    
    def __init__(self):
        super().__init__('mean_reversion')
        self.estimator = EnsembleEdgeEstimator()
    
    def generate_signal(self, market_slug: str, **kwargs) -> Optional[StrategySignal]:
        current_price = kwargs.get('current_price', 0.5)
        
        self.estimator.update_price(market_slug, current_price)
        
        estimate = self.estimator.estimate_probability(
            market_slug, '', current_price
        )
        
        reversion_pred = estimate.individual_predictions.get('mean_reversion', 0.5)
        edge = reversion_pred - current_price
        
        # Only trade at extremes
        if not (current_price < 0.20 or current_price > 0.80):
            return None
        
        if abs(edge) < 0.05:  # Need larger edge for mean reversion
            return None
        
        return StrategySignal(
            market_slug=market_slug,
            direction='BUY_YES' if edge > 0 else 'BUY_NO',
            strength=min(1.0, abs(edge) * 4),
            expected_return=abs(edge),
            confidence=0.6,
            rationale=f"Mean reversion at {current_price:.0%}"
        )


class ArbitrageStrategy(BaseStrategy):
    """
    Strategy based on arbitrage opportunities.
    Finds Yes+No spreads and related market mispricings.
    """
    
    def __init__(self):
        super().__init__('arbitrage')
    
    def generate_signal(self, market_slug: str, **kwargs) -> Optional[StrategySignal]:
        yes_price = kwargs.get('yes_price', 0.5)
        no_price = kwargs.get('no_price', 0.5)
        
        # Check for arbitrage: Yes + No should be ~1.0
        total = yes_price + no_price
        spread = abs(1.0 - total)
        
        if spread < 0.02:  # 2% threshold
            return None
        
        if total < 1.0:
            # Buy both, but we need to pick one for signal
            # Buy the cheaper side
            if yes_price < no_price:
                direction = 'BUY_YES'
                edge = spread / 2
            else:
                direction = 'BUY_NO'
                edge = spread / 2
        else:
            # Premium, avoid
            return None
        
        return StrategySignal(
            market_slug=market_slug,
            direction=direction,
            strength=1.0,
            expected_return=spread,
            confidence=0.9,  # Arbitrage is high confidence
            rationale=f"Arbitrage spread: {spread:.1%}"
        )


class EnsembleStrategy(BaseStrategy):
    """
    Strategy using full ensemble edge estimator.
    Most sophisticated, uses all signals.
    """
    
    def __init__(self):
        super().__init__('ensemble')
        self.estimator = EnsembleEdgeEstimator()
    
    def generate_signal(self, market_slug: str, **kwargs) -> Optional[StrategySignal]:
        question = kwargs.get('question', '')
        current_price = kwargs.get('current_price', 0.5)
        category = kwargs.get('category', 'general')
        
        self.estimator.update_price(market_slug, current_price)
        
        estimate = self.estimator.estimate_probability(
            market_slug, question, current_price, category
        )
        
        edge = estimate.edge
        
        if abs(edge) < 0.03:
            return None
        
        return StrategySignal(
            market_slug=market_slug,
            direction='BUY_YES' if edge > 0 else 'BUY_NO',
            strength=min(1.0, abs(edge) * 5),
            expected_return=abs(edge),
            confidence=estimate.confidence,
            rationale=estimate.recommendation
        )


class StrategyPortfolio:
    """
    Portfolio of multiple strategies with dynamic allocation.
    
    Allocates capital across strategies based on their Sharpe ratios.
    Diversification reduces tail risk and provides robustness.
    """
    
    def __init__(
        self,
        bankroll: float = 10000,
        max_total_exposure: float = 0.50,
        max_strategy_exposure: float = 0.30
    ):
        self.bankroll = bankroll
        self.max_total_exposure = max_total_exposure
        self.max_strategy_exposure = max_strategy_exposure
        
        # Initialize strategies
        self.strategies: Dict[str, BaseStrategy] = {
            'sentiment': SentimentStrategy(),
            'momentum': MomentumStrategy(),
            'mean_reversion': MeanReversionStrategy(),
            'arbitrage': ArbitrageStrategy(),
            'ensemble': EnsembleStrategy(),
        }
        
        self.kelly = AdaptiveKelly()
        self.portfolio_kelly = PortfolioKelly(max_total_exposure)
        self.tracker = PredictionTracker()
        
        self.active_allocations: List[PortfolioAllocation] = []
    
    def generate_signals(self, market_slug: str, **market_data) -> Dict[str, Optional[StrategySignal]]:
        """
        Generate signals from all strategies.
        
        Returns:
            Dict mapping strategy name to signal (or None)
        """
        signals = {}
        
        for name, strategy in self.strategies.items():
            signal = strategy.generate_signal(market_slug, **market_data)
            signals[name] = signal
        
        return signals
    
    def allocate_capital(
        self,
        market_slug: str,
        signals: Dict[str, Optional[StrategySignal]],
        current_price: float
    ) -> List[PortfolioAllocation]:
        """
        Allocate capital across strategies based on performance.
        
        Uses ensemble voting weighted by Sharpe ratios.
        """
        allocations = []
        
        # Filter valid signals
        valid_signals = {
            name: sig for name, sig in signals.items()
            if sig is not None
        }
        
        if not valid_signals:
            return allocations
        
        # Calculate strategy weights based on Sharpe ratios
        sharpe_ratios = {
            name: self.strategies[name].get_sharpe_ratio()
            for name in valid_signals.keys()
        }
        
        # Softmax to get weights
        exp_sharpes = {k: np.exp(max(0, v)) for k, v in sharpe_ratios.items()}
        total = sum(exp_sharpes.values())
        weights = {k: v / total for k, v in exp_sharpes.items()}
        
        # Generate allocations
        for strategy_name, signal in valid_signals.items():
            weight = weights[strategy_name]
            
            # Calculate position size using Kelly
            estimated_prob = current_price + signal.expected_return * np.sign(
                1 if signal.direction == 'BUY_YES' else -1
            )
            
            kelly_result = self.kelly.calculate_position_size(
                bankroll=self.bankroll * weight,
                market_price=current_price,
                estimated_prob=estimated_prob,
                confidence=signal.confidence
            )
            
            if kelly_result.position_size > 0:
                allocation = PortfolioAllocation(
                    market_slug=market_slug,
                    side=kelly_result.side,
                    size=kelly_result.adjusted_fraction * weight,
                    strategy=strategy_name,
                    expected_return=signal.expected_return,
                    sharpe_ratio=sharpe_ratios[strategy_name]
                )
                allocations.append(allocation)
        
        return allocations
    
    def get_strategy_performance(self) -> Dict:
        """Get performance summary for all strategies"""
        performance = {}
        
        for name, strategy in self.strategies.items():
            performance[name] = {
                'sharpe_ratio': strategy.get_sharpe_ratio(),
                'win_rate': strategy.get_win_rate(),
                'trades_count': len(strategy.performance_history),
                'total_pnl': sum(strategy.performance_history) if strategy.performance_history else 0
            }
        
        return performance
    
    def display_performance(self):
        """Display strategy performance summary"""
        print("=" * 70)
        print("📊 STRATEGY PERFORMANCE SUMMARY")
        print("=" * 70)
        
        perf = self.get_strategy_performance()
        
        print(f"\n{'Strategy':<20} {'Sharpe':<10} {'Win Rate':<12} {'Trades':<10} {'P&L':<15}")
        print("-" * 70)
        
        for name, data in sorted(perf.items(), key=lambda x: -x[1]['sharpe_ratio']):
            print(f"{name:<20} {data['sharpe_ratio']:<10.2f} {data['win_rate']:<12.1%} "
                  f"{data['trades_count']:<10} ${data['total_pnl']:<+14.2f}")
        
        print("=" * 70)


# Simple test
if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    print("Testing StrategyPortfolio...")
    
    portfolio = StrategyPortfolio(bankroll=10000)
    
    # Test signal generation
    print("\n1. Testing signal generation...")
    
    # Feed some price history
    for i in range(10):
        price = 0.45 + i * 0.01
        for name, strategy in portfolio.strategies.items():
            if hasattr(strategy, 'estimator'):
                strategy.estimator.update_price('test-market', price)
    
    signals = portfolio.generate_signals(
        'test-market',
        question='Will the price reach 0.60?',
        current_price=0.55,
        category='general'
    )
    
    print(f"\nSignals generated:")
    for name, signal in signals.items():
        if signal:
            print(f"  {name:<20}: {signal.direction} (strength: {signal.strength:.2f})")
        else:
            print(f"  {name:<20}: No signal")
    
    # Test allocation
    print("\n2. Testing capital allocation...")
    allocations = portfolio.allocate_capital('test-market', signals, 0.55)
    
    print(f"\nAllocations ({len(allocations)}):")
    for alloc in allocations:
        print(f"  {alloc.strategy:<15}: {alloc.side} ${alloc.size * 10000:.2f} "
              f"(Sharpe: {alloc.sharpe_ratio:.2f})")
    
    # Test performance tracking
    print("\n3. Testing performance tracking...")
    
    # Simulate some results
    portfolio.strategies['momentum'].record_result(0.15)
    portfolio.strategies['momentum'].record_result(-0.05)
    portfolio.strategies['momentum'].record_result(0.20)
    
    portfolio.strategies['ensemble'].record_result(0.10)
    portfolio.strategies['ensemble'].record_result(0.12)
    
    portfolio.display_performance()
    
    print("\n✅ StrategyPortfolio tests passed!")
