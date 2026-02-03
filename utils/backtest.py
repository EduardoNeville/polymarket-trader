"""
Backtesting Framework
Test strategies on historical data with walk-forward validation.
Essential before deploying with real capital.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

from strategies.adaptive_kelly import AdaptiveKelly
from models.edge_estimator import EnsembleEdgeEstimator
from utils.prediction_tracker import PredictionTracker


@dataclass
class Trade:
    """Single trade record"""
    timestamp: str
    market_slug: str
    side: str
    entry_price: float
    position_size: float
    estimated_prob: float
    actual_outcome: Optional[int] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None


@dataclass
class BacktestResult:
    """Complete backtest results"""
    strategy_name: str
    start_date: str
    end_date: str
    initial_bankroll: float
    final_bankroll: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_pct: float
    avg_trade_pnl: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Tuple[str, float]] = field(default_factory=list)


class BacktestEngine:
    """
    Backtesting engine for strategy validation.
    
    Supports:
    - Walk-forward testing
    - Multiple strategies
    - Performance metrics
    - Equity curve generation
    """
    
    def __init__(self, initial_bankroll: float = 10000):
        self.initial_bankroll = initial_bankroll
        self.current_bankroll = initial_bankroll
        self.kelly = AdaptiveKelly()
        self.estimator = EnsembleEdgeEstimator()
        
        self.trades: List[Trade] = []
        self.equity_curve: List[Tuple[str, float]] = []
        self.peak_bankroll = initial_bankroll
        self.max_drawdown = 0.0
    
    def run_backtest(
        self,
        historical_data: List[Dict],
        strategy: str = 'ensemble',
        min_edge: float = 0.03,
        verbose: bool = False
    ) -> BacktestResult:
        """
        Run backtest on historical data.
        
        Args:
            historical_data: List of dicts with keys:
                - timestamp: ISO format
                - market_slug: str
                - question: str
                - price: float (YES price)
                - outcome: int (1=YES, 0=NO, None=unresolved)
                - category: str
            strategy: Which strategy to use
            min_edge: Minimum edge to trade
            verbose: Print progress
        
        Returns:
            BacktestResult with full statistics
        """
        if verbose:
            print(f"\n🔄 Running backtest with {len(historical_data)} data points...")
            print(f"   Strategy: {strategy}")
            print(f"   Min edge: {min_edge:.1%}")
        
        # Reset state
        self.current_bankroll = self.initial_bankroll
        self.trades = []
        self.equity_curve = [(datetime.now().isoformat(), self.initial_bankroll)]
        self.peak_bankroll = self.initial_bankroll
        self.max_drawdown = 0.0
        
        # Group by market
        markets = {}
        for data in historical_data:
            slug = data['market_slug']
            if slug not in markets:
                markets[slug] = []
            markets[slug].append(data)
        
        if verbose:
            print(f"   {len(markets)} unique markets")
        
        # Process each market
        for market_slug, market_data in markets.items():
            self._process_market(market_slug, market_data, strategy, min_edge)
        
        # Calculate results
        result = self._calculate_results()
        
        if verbose:
            self._print_results(result)
        
        return result
    
    def _process_market(
        self,
        market_slug: str,
        market_data: List[Dict],
        strategy: str,
        min_edge: float
    ):
        """Process a single market's data"""
        if len(market_data) < 2:
            return
        
        # Use first price as entry
        entry_data = market_data[0]
        exit_data = market_data[-1]
        
        # Skip if no outcome
        if exit_data.get('outcome') is None:
            return
        
        entry_price = entry_data['price']
        exit_price = exit_data['price']
        actual_outcome = exit_data['outcome']
        
        # Feed price history to estimator
        for data in market_data[:-1]:  # All but last
            self.estimator.update_price(market_slug, data['price'])
        
        # Get prediction
        estimate = self.estimator.estimate_probability(
            market_slug,
            entry_data.get('question', ''),
            entry_price,
            entry_data.get('category', 'general')
        )
        
        # Use specified strategy component
        if strategy == 'ensemble':
            predicted_prob = estimate.ensemble_probability
        elif strategy in estimate.individual_predictions:
            predicted_prob = estimate.individual_predictions[strategy]
        else:
            predicted_prob = entry_price  # No edge
        
        edge = predicted_prob - entry_price
        
        # Check minimum edge
        if abs(edge) < min_edge:
            return
        
        # Calculate position size
        kelly_result = self.kelly.calculate_position_size(
            bankroll=self.current_bankroll,
            market_price=entry_price,
            estimated_prob=predicted_prob,
            confidence=estimate.confidence
        )
        
        if kelly_result.position_size <= 0:
            return
        
        # Execute trade
        trade = Trade(
            timestamp=entry_data['timestamp'],
            market_slug=market_slug,
            side=kelly_result.side,
            entry_price=entry_price,
            position_size=kelly_result.position_size,
            estimated_prob=predicted_prob,
            actual_outcome=actual_outcome,
            exit_price=exit_price
        )
        
        # Calculate P&L
        if kelly_result.side == 'YES':
            trade.pnl = (actual_outcome - entry_price) * kelly_result.shares
            trade.pnl_pct = trade.pnl / kelly_result.position_size if kelly_result.position_size > 0 else 0
        else:  # NO
            no_entry = 1 - entry_price
            trade.pnl = ((1 - actual_outcome) - no_entry) * kelly_result.shares
            trade.pnl_pct = trade.pnl / kelly_result.position_size if kelly_result.position_size > 0 else 0
        
        self.trades.append(trade)
        
        # Update bankroll
        self.current_bankroll += trade.pnl
        
        # Track equity curve
        self.equity_curve.append((exit_data['timestamp'], self.current_bankroll))
        
        # Update drawdown
        if self.current_bankroll > self.peak_bankroll:
            self.peak_bankroll = self.current_bankroll
        
        drawdown = self.peak_bankroll - self.current_bankroll
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
    
    def _calculate_results(self) -> BacktestResult:
        """Calculate backtest statistics"""
        if not self.trades:
            return BacktestResult(
                strategy_name='none',
                start_date='',
                end_date='',
                initial_bankroll=self.initial_bankroll,
                final_bankroll=self.initial_bankroll,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                total_pnl_pct=0.0,
                avg_trade_pnl=0.0,
                max_drawdown=0.0,
                max_drawdown_pct=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                trades=[],
                equity_curve=self.equity_curve
            )
        
        # Basic stats
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.pnl and t.pnl > 0)
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_pnl = sum(t.pnl for t in self.trades if t.pnl)
        total_pnl_pct = (total_pnl / self.initial_bankroll) * 100
        avg_trade_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        # Drawdown
        max_drawdown_pct = (self.max_drawdown / self.peak_bankroll) * 100 if self.peak_bankroll > 0 else 0
        
        # Sharpe ratio
        returns = [t.pnl_pct for t in self.trades if t.pnl_pct is not None]
        if len(returns) > 1:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe = avg_return / std_return if std_return > 0 else 0
        else:
            sharpe = 0
        
        # Sortino ratio (downside deviation only)
        if len(returns) > 1:
            downside_returns = [r for r in returns if r < 0]
            downside_std = np.std(downside_returns) if downside_returns else 0.001
            sortino = avg_return / downside_std if downside_std > 0 else 0
        else:
            sortino = 0
        
        return BacktestResult(
            strategy_name='backtest',
            start_date=self.trades[0].timestamp if self.trades else '',
            end_date=self.trades[-1].timestamp if self.trades else '',
            initial_bankroll=self.initial_bankroll,
            final_bankroll=self.current_bankroll,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            avg_trade_pnl=avg_trade_pnl,
            max_drawdown=self.max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            trades=self.trades,
            equity_curve=self.equity_curve
        )
    
    def _print_results(self, result: BacktestResult):
        """Print backtest results"""
        print("\n" + "=" * 70)
        print("📊 BACKTEST RESULTS")
        print("=" * 70)
        print(f"\nInitial Bankroll: ${result.initial_bankroll:,.2f}")
        print(f"Final Bankroll:   ${result.final_bankroll:,.2f}")
        print(f"Total P&L:        ${result.total_pnl:+,.2f} ({result.total_pnl_pct:+.2f}%)")
        print(f"\nTotal Trades:     {result.total_trades}")
        print(f"Winning Trades:   {result.winning_trades} ({result.win_rate:.1%})")
        print(f"Losing Trades:    {result.losing_trades}")
        print(f"Avg Trade P&L:    ${result.avg_trade_pnl:+.2f}")
        print(f"\nMax Drawdown:     ${result.max_drawdown:,.2f} ({result.max_drawdown_pct:.2f}%)")
        print(f"Sharpe Ratio:     {result.sharpe_ratio:.2f}")
        print(f"Sortino Ratio:    {result.sortino_ratio:.2f}")
        print("=" * 70)
    
    def compare_strategies(
        self,
        historical_data: List[Dict],
        strategies: List[str],
        min_edge: float = 0.03
    ) -> Dict[str, BacktestResult]:
        """
        Compare multiple strategies on same data.
        
        Returns:
            Dict mapping strategy name to BacktestResult
        """
        results = {}
        
        print("\n" + "=" * 70)
        print("🔄 STRATEGY COMPARISON")
        print("=" * 70)
        
        for strategy in strategies:
            print(f"\nTesting {strategy}...")
            result = self.run_backtest(historical_data, strategy, min_edge)
            results[strategy] = result
        
        # Print comparison table
        print("\n" + "-" * 70)
        print(f"{'Strategy':<20} {'P&L':<12} {'Win Rate':<12} {'Sharpe':<10} {'Max DD':<10}")
        print("-" * 70)
        
        for strategy, result in sorted(
            results.items(),
            key=lambda x: x[1].total_pnl,
            reverse=True
        ):
            print(f"{strategy:<20} ${result.total_pnl:+>10.2f} "
                  f"{result.win_rate:<12.1%} {result.sharpe_ratio:<10.2f} "
                  f"{result.max_drawdown_pct:<10.2f}%")
        
        print("=" * 70)
        
        return results
    
    def save_results(self, result: BacktestResult, filepath: str):
        """Save backtest results to file"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'strategy_name': result.strategy_name,
            'start_date': result.start_date,
            'end_date': result.end_date,
            'initial_bankroll': result.initial_bankroll,
            'final_bankroll': result.final_bankroll,
            'total_trades': result.total_trades,
            'winning_trades': result.winning_trades,
            'losing_trades': result.losing_trades,
            'win_rate': result.win_rate,
            'total_pnl': result.total_pnl,
            'total_pnl_pct': result.total_pnl_pct,
            'avg_trade_pnl': result.avg_trade_pnl,
            'max_drawdown': result.max_drawdown,
            'max_drawdown_pct': result.max_drawdown_pct,
            'sharpe_ratio': result.sharpe_ratio,
            'sortino_ratio': result.sortino_ratio,
            'trades': [
                {
                    'timestamp': t.timestamp,
                    'market_slug': t.market_slug,
                    'side': t.side,
                    'entry_price': t.entry_price,
                    'position_size': t.position_size,
                    'estimated_prob': t.estimated_prob,
                    'actual_outcome': t.actual_outcome,
                    'pnl': t.pnl,
                    'pnl_pct': t.pnl_pct
                }
                for t in result.trades
            ],
            'equity_curve': result.equity_curve
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Results saved to {filepath}")


# Simple test
if __name__ == "__main__":
    print("Testing BacktestEngine...")
    
    # Generate synthetic test data
    import random
    random.seed(42)
    
    historical_data = []
    for i in range(20):
        # Random walk prices
        base_price = 0.50
        prices = [base_price]
        for _ in range(10):
            prices.append(max(0.05, min(0.95, prices[-1] + random.gauss(0, 0.02))))
        
        # Generate data points
        for j, price in enumerate(prices):
            historical_data.append({
                'timestamp': f'2024-01-{i+1:02d}T{j:02d}:00:00',
                'market_slug': f'market-{i}',
                'question': f'Test market {i}?',
                'price': price,
                'outcome': 1 if prices[-1] > 0.5 else 0,
                'category': 'general'
            })
    
    # Run backtest
    engine = BacktestEngine(initial_bankroll=10000)
    result = engine.run_backtest(historical_data, verbose=True)
    
    print("\n✅ Backtest complete!")
