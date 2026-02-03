"""
AI-Enhanced Odds Calculator
Integrates ensemble predictions with adaptive Kelly criterion.
"""

import numpy as np
from typing import Optional

from models.edge_estimator import EnsembleEdgeEstimator
from strategies.adaptive_kelly import AdaptiveKelly
from strategies.portfolio import StrategyPortfolio
from utils.prediction_tracker import PredictionTracker


class AIOddsCalculator:
    """
    AI-powered odds calculator that:
    1. Uses ensemble models to estimate probabilities
    2. Applies adaptive Kelly for position sizing
    3. Tracks predictions for calibration
    4. Learns from outcomes to improve
    """
    
    def __init__(self, bankroll: float = 10000):
        self.bankroll = bankroll
        self.estimator = EnsembleEdgeEstimator()
        self.kelly = AdaptiveKelly()
        self.portfolio = StrategyPortfolio(bankroll=bankroll)
        self.tracker = PredictionTracker()
    
    def calculate(
        self,
        market_slug: str,
        market_question: str,
        current_price: float,
        category: str = 'general',
        use_ai: bool = True
    ) -> dict:
        """
        Calculate optimal position with AI assistance.
        
        Args:
            market_slug: Market identifier
            market_question: Market question text
            current_price: Current market price
            category: Market category
            use_ai: Whether to use AI prediction or manual input
        
        Returns:
            Dict with full calculation results
        """
        print("\n🤖 AI-Enhanced Odds Calculator")
        print("=" * 70)
        
        # Step 1: Get AI estimate
        self.estimator.update_price(market_slug, current_price)
        
        ai_estimate = self.estimator.estimate_probability(
            market_slug, market_question, current_price, category
        )
        
        # Step 2: Display AI prediction
        print(f"\n📊 AI ENSEMBLE PREDICTION")
        print(f"  Current Market Price: {current_price:.2%}")
        print(f"  AI Predicted Prob:    {ai_estimate.ensemble_probability:.2%}")
        print(f"  Edge:                 {ai_estimate.edge:+.2%}")
        print(f"  Confidence:           {ai_estimate.confidence:.0%}")
        print(f"  Expected Return:      {ai_estimate.expected_return:.2%}")
        print(f"  Sharpe Ratio:         {ai_estimate.sharpe_ratio:.2f}")
        
        # Step 3: Individual model breakdown
        print(f"\n🧠 INDIVIDUAL MODEL PREDICTIONS")
        for model, pred in sorted(ai_estimate.individual_predictions.items()):
            weight = ai_estimate.model_weights.get(model, 0)
            conf = ai_estimate.model_confidences.get(model, 0)
            print(f"  {model:20s}: {pred:.2%} (w={weight:.1%}, c={conf:.0%})")
        
        # Step 4: User choice
        print(f"\n💡 AI RECOMMENDATION: {ai_estimate.recommendation}")
        
        if use_ai:
            print(f"\nUse AI prediction ({ai_estimate.ensemble_probability:.2%})?")
            choice = input("  [Y]es / [N]o (manual) / [S]how calibration: ").strip().upper()
            
            if choice == 'S':
                self.tracker.display_report()
                choice = input("\nUse AI prediction? [Y/N]: ").strip().upper()
            
            if choice == 'Y' or choice == '':
                estimated_prob = ai_estimate.ensemble_probability
                confidence = ai_estimate.confidence
                model_predictions = ai_estimate.individual_predictions
            else:
                # Manual input
                estimated_prob = float(input(f"\nEnter your estimated YES probability (0-1): "))
                confidence = float(input("Enter your confidence (0-1): "))
                model_predictions = {'manual': estimated_prob}
        else:
            estimated_prob = float(input(f"\nEnter your estimated YES probability (0-1): "))
            confidence = float(input("Enter your confidence (0-1): "))
            model_predictions = {'manual': estimated_prob}
        
        # Step 5: Calculate position size with Adaptive Kelly
        result = self.kelly.calculate_position_size(
            bankroll=self.bankroll,
            market_price=current_price,
            estimated_prob=estimated_prob,
            confidence=confidence
        )
        
        # Step 6: Display results
        print(f"\n📈 POSITION SIZING (Adaptive Kelly)")
        print(f"  Side:                 {result.side}")
        print(f"  Kelly Fraction:       {result.kelly_fraction:.2%}")
        print(f"  Adjusted Fraction:    {result.adjusted_fraction:.2%}")
        print(f"  Position Size:        ${result.position_size:,.2f}")
        print(f"  Shares to Buy:        {result.shares:.2f}")
        
        print(f"\n🔧 ADJUSTMENTS")
        print(f"  Confidence:           ×{result.confidence_adjustment:.2f}")
        print(f"  Correlation:          ×{result.correlation_penalty:.2f}")
        print(f"  Drawdown:             ×{result.drawdown_penalty:.2f}")
        print(f"  Rationale:            {result.rationale}")
        
        if result.recommendations:
            print(f"\n⚠️  WARNINGS")
            for rec in result.recommendations:
                print(f"  • {rec}")
        
        # Step 7: Record prediction
        print(f"\n📝 Record this prediction for calibration?")
        record = input("  [Y]es / [N]o: ").strip().upper()
        
        if record == 'Y' or record == '':
            self.tracker.record_prediction(
                market_slug=market_slug,
                question=market_question,
                predicted_prob=estimated_prob,
                market_price=current_price,
                side=result.side,
                position_size=result.position_size,
                model_predictions=model_predictions
            )
            print("  ✅ Prediction recorded!")
        
        print("=" * 70)
        
        return {
            'side': result.side,
            'position_size': result.position_size,
            'shares': result.shares,
            'estimated_prob': estimated_prob,
            'edge': estimated_prob - current_price,
            'ai_recommendation': ai_estimate.recommendation,
            'recorded': record == 'Y' or record == ''
        }
    
    def resolve_market(self, market_slug: str, outcome: int):
        """
        Record market outcome for calibration.
        
        Args:
            market_slug: Market identifier
            outcome: 1 if YES won, 0 if NO won
        """
        result = self.tracker.record_outcome(market_slug, outcome)
        
        if result:
            print(f"\n✅ Market resolved!")
            print(f"  Market: {result.question}")
            print(f"  Predicted: {result.predicted_prob:.2%}")
            print(f"  Actual: {'YES' if outcome == 1 else 'NO'}")
            print(f"  Brier Score: {result.brier_score:.4f}")
            print(f"  P&L: ${result.pnl:+.2f}")
            
            # Show updated calibration
            report = self.tracker.get_calibration_report()
            if report['status'] == 'success':
                print(f"\n📊 Updated Kelly Fraction: {report['recommended_kelly_fraction']:.0%}")
        else:
            print(f"⚠️  No prediction found for {market_slug}")
    
    def show_calibration(self):
        """Display calibration report"""
        self.tracker.display_report()
    
    def show_strategy_performance(self):
        """Display strategy portfolio performance"""
        self.portfolio.display_performance()


def interactive_ai_calculator():
    """Interactive AI-powered calculator"""
    print("=" * 70)
    print("🤖 AI-POWERED ODDS CALCULATOR")
    print("=" * 70)
    
    bankroll = float(input("\nEnter your bankroll ($): "))
    calc = AIOddsCalculator(bankroll=bankroll)
    
    while True:
        print("\n" + "-" * 70)
        print("Options:")
        print("  1. Calculate new position")
        print("  2. Resolve a market (record outcome)")
        print("  3. View calibration report")
        print("  4. View strategy performance")
        print("  5. Exit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == '1':
            print("\n--- New Position ---")
            market_slug = input("Market slug: ").strip()
            market_question = input("Market question: ").strip()
            current_price = float(input("Current YES price (0-1): "))
            category = input("Category [general]: ").strip() or 'general'
            
            calc.calculate(
                market_slug=market_slug,
                market_question=market_question,
                current_price=current_price,
                category=category
            )
            
        elif choice == '2':
            print("\n--- Resolve Market ---")
            market_slug = input("Market slug: ").strip()
            outcome = int(input("Outcome (1=YES, 0=NO): "))
            
            calc.resolve_market(market_slug, outcome)
            
        elif choice == '3':
            print("\n--- Calibration Report ---")
            calc.show_calibration()
            
        elif choice == '4':
            print("\n--- Strategy Performance ---")
            calc.show_strategy_performance()
            
        elif choice == '5':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("Invalid option")


# Simple test
if __name__ == "__main__":
    print("Testing AIOddsCalculator...")
    
    calc = AIOddsCalculator(bankroll=10000)
    
    # Test calculation (non-interactive)
    print("\nAI Calculator initialized successfully!")
    print(f"Bankroll: ${calc.bankroll:,.2f}")
    print(f"Components: {len(calc.portfolio.strategies)} strategies")
    
    print("\n✅ AIOddsCalculator ready!")
