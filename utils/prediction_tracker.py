"""
Prediction Tracking System
Tracks prediction accuracy to calibrate Kelly fraction and model performance.
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional


@dataclass
class PredictionRecord:
    """Single prediction record"""
    market_slug: str
    question: str
    predicted_prob: float
    market_price: float
    edge: float
    side: str
    position_size: float
    timestamp: str
    resolved: bool = False
    actual_outcome: Optional[int] = None
    pnl: Optional[float] = None
    brier_score: Optional[float] = None
    model_predictions: Optional[Dict[str, float]] = None


class PredictionTracker:
    """
    Track prediction accuracy to calibrate Kelly fraction.
    This is the foundation for all adaptive algorithms.
    """
    
    def __init__(self, file_path: str = "data/predictions.json"):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.predictions: List[PredictionRecord] = []
        self.load()
    
    def load(self):
        """Load predictions from file"""
        if self.file_path.exists():
            with open(self.file_path, 'r') as f:
                data = json.load(f)
                self.predictions = [PredictionRecord(**p) for p in data]
        else:
            self.predictions = []
    
    def save(self):
        """Save predictions to file"""
        with open(self.file_path, 'w') as f:
            json.dump([asdict(p) for p in self.predictions], f, indent=2)
    
    def record_prediction(
        self,
        market_slug: str,
        question: str,
        predicted_prob: float,
        market_price: float,
        side: str,
        position_size: float,
        model_predictions: Optional[Dict[str, float]] = None
    ) -> PredictionRecord:
        """
        Log a prediction for later evaluation.
        
        Args:
            market_slug: Unique market identifier
            question: Market question text
            predicted_prob: Your estimated probability (0-1)
            market_price: Current market price (0-1)
            side: 'YES' or 'NO'
            position_size: Dollar amount bet
            model_predictions: Individual model predictions for ensemble tracking
        
        Returns:
            The created PredictionRecord
        """
        record = PredictionRecord(
            market_slug=market_slug,
            question=question,
            predicted_prob=predicted_prob,
            market_price=market_price,
            edge=predicted_prob - market_price,
            side=side,
            position_size=position_size,
            timestamp=datetime.now().isoformat(),
            model_predictions=model_predictions
        )
        
        self.predictions.append(record)
        self.save()
        return record
    
    def record_outcome(self, market_slug: str, actual_outcome: int) -> Optional[PredictionRecord]:
        """
        When market resolves, record actual outcome and calculate P&L.
        
        Args:
            market_slug: Market identifier
            actual_outcome: 1 if YES resolved, 0 if NO resolved
        
        Returns:
            Updated PredictionRecord or None if not found
        """
        for p in self.predictions:
            if p.market_slug == market_slug and not p.resolved:
                p.resolved = True
                p.actual_outcome = actual_outcome
                
                # Calculate Brier score
                p.brier_score = (p.predicted_prob - actual_outcome) ** 2
                
                # Calculate P&L
                if p.side == 'YES':
                    # P&L = (payout - cost) / cost as percentage
                    if p.market_price > 0:
                        payout = actual_outcome  # $1 if win, $0 if lose
                        cost = p.market_price
                        pnl_per_dollar = (payout - cost) / cost
                        p.pnl = pnl_per_dollar * p.position_size
                else:  # NO
                    no_price = 1 - p.market_price
                    if no_price > 0:
                        payout = 1 - actual_outcome  # $1 if NO wins
                        pnl_per_dollar = (payout - no_price) / no_price
                        p.pnl = pnl_per_dollar * p.position_size
                
                self.save()
                return p
        
        return None
    
    def get_calibration_report(self) -> Dict:
        """
        Analyze prediction accuracy and return comprehensive report.
        
        Returns:
            Dict with calibration metrics and Kelly recommendations
        """
        resolved = [p for p in self.predictions if p.resolved]
        
        if not resolved:
            return {
                'status': 'insufficient_data',
                'message': 'No resolved predictions yet. Make predictions and wait for markets to resolve.',
                'total_predictions': len(self.predictions),
                'resolved': 0
            }
        
        brier_scores = [p.brier_score for p in resolved if p.brier_score is not None]
        pnls = [p.pnl for p in resolved if p.pnl is not None]
        edges = [p.edge for p in resolved]
        
        # Bin predictions and check calibration
        bins = {i/10: [] for i in range(10)}
        for p in resolved:
            bin_key = int(p.predicted_prob * 10) / 10
            bins[bin_key].append(p.actual_outcome)
        
        calibration = {}
        for bin_key, outcomes in bins.items():
            if outcomes:
                calibration[f"{bin_key:.1f}-{bin_key+0.1:.1f}"] = {
                    'predicted_avg': bin_key + 0.05,
                    'actual_rate': sum(outcomes) / len(outcomes),
                    'count': len(outcomes)
                }
        
        # Calculate metrics by edge size
        positive_edge = [p for p in resolved if p.edge > 0]
        negative_edge = [p for p in resolved if p.edge <= 0]
        
        report = {
            'status': 'success',
            'total_predictions': len(self.predictions),
            'resolved': len(resolved),
            'unresolved': len(self.predictions) - len(resolved),
            'mean_brier_score': sum(brier_scores) / len(brier_scores) if brier_scores else None,
            'total_pnl': sum(pnls) if pnls else 0,
            'avg_pnl_per_trade': sum(pnls) / len(pnls) if pnls else 0,
            'sharpe_ratio': self._calculate_sharpe(pnls) if pnls else 0,
            'win_rate': sum(1 for p in resolved if p.pnl and p.pnl > 0) / len([p for p in resolved if p.pnl]) if any(p.pnl for p in resolved) else 0,
            'calibration': calibration,
            'edge_analysis': {
                'positive_edge_trades': len(positive_edge),
                'positive_edge_win_rate': sum(1 for p in positive_edge if p.pnl and p.pnl > 0) / len([p for p in positive_edge if p.pnl]) if positive_edge else 0,
                'negative_edge_trades': len(negative_edge),
                'negative_edge_win_rate': sum(1 for p in negative_edge if p.pnl and p.pnl > 0) / len([p for p in negative_edge if p.pnl]) if negative_edge else 0,
            },
            'recommended_kelly_fraction': self._recommend_kelly(brier_scores),
            'model_performance': self._analyze_model_performance(resolved)
        }
        
        return report
    
    def _calculate_sharpe(self, returns: List[float]) -> float:
        """Calculate annualized Sharpe ratio"""
        if len(returns) < 2:
            return 0.0
        
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Assume ~252 trading days, but we don't have time data
        # So just return simple Sharpe
        return avg_return / std_return
    
    def _recommend_kelly(self, brier_scores: List[float]) -> float:
        """Suggest Kelly fraction based on calibration"""
        if not brier_scores:
            return 0.25  # Default conservative
        
        mean_brier = sum(brier_scores) / len(brier_scores)
        
        # Perfect calibration for binary = 0 (impossible)
        # Random guessing = 0.25
        # Good forecaster = 0.10-0.15
        if mean_brier < 0.10:
            return 0.50  # Very well calibrated
        elif mean_brier < 0.15:
            return 0.35
        elif mean_brier < 0.20:
            return 0.25
        elif mean_brier < 0.25:
            return 0.15
        else:
            return 0.10  # Poor calibration, be conservative
    
    def _analyze_model_performance(self, resolved: List[PredictionRecord]) -> Dict:
        """Analyze performance of individual models in ensemble"""
        if not resolved or not any(p.model_predictions for p in resolved):
            return {}
        
        # Collect model names
        model_names = set()
        for p in resolved:
            if p.model_predictions:
                model_names.update(p.model_predictions.keys())
        
        performance = {}
        for model_name in model_names:
            model_briers = []
            for p in resolved:
                if p.model_predictions and model_name in p.model_predictions:
                    pred = p.model_predictions[model_name]
                    actual = p.actual_outcome
                    if actual is not None:
                        model_briers.append((pred - actual) ** 2)
            
            if model_briers:
                performance[model_name] = {
                    'mean_brier': sum(model_briers) / len(model_briers),
                    'predictions_count': len(model_briers)
                }
        
        return performance
    
    def get_unresolved_predictions(self) -> List[PredictionRecord]:
        """Get list of unresolved predictions"""
        return [p for p in self.predictions if not p.resolved]
    
    def get_prediction_history(self, market_slug: Optional[str] = None) -> List[PredictionRecord]:
        """Get prediction history, optionally filtered by market"""
        if market_slug:
            return [p for p in self.predictions if p.market_slug == market_slug]
        return self.predictions
    
    def display_report(self):
        """Print calibration report to console"""
        report = self.get_calibration_report()
        
        print("=" * 80)
        print("📊 PREDICTION CALIBRATION REPORT")
        print("=" * 80)
        print()
        
        if report['status'] == 'insufficient_data':
            print(report['message'])
            print(f"Total predictions logged: {report['total_predictions']}")
            return
        
        print(f"Total Predictions: {report['total_predictions']}")
        print(f"Resolved: {report['resolved']} | Unresolved: {report['unresolved']}")
        print()
        
        print("📈 PERFORMANCE METRICS")
        print(f"  Mean Brier Score: {report['mean_brier_score']:.4f} (lower is better)")
        print(f"  Total P&L: ${report['total_pnl']:+.2f}")
        print(f"  Avg P&L per Trade: ${report['avg_pnl_per_trade']:+.2f}")
        print(f"  Win Rate: {report['win_rate']:.1%}")
        print(f"  Sharpe Ratio: {report['sharpe_ratio']:.2f}")
        print()
        
        print("🎯 EDGE ANALYSIS")
        ea = report['edge_analysis']
        print(f"  Positive Edge Trades: {ea['positive_edge_trades']}")
        print(f"  Positive Edge Win Rate: {ea['positive_edge_win_rate']:.1%}")
        print(f"  Negative Edge Trades: {ea['negative_edge_trades']}")
        print(f"  Negative Edge Win Rate: {ea['negative_edge_win_rate']:.1%}")
        print()
        
        print("📊 CALIBRATION BY BIN")
        for bin_range, data in report['calibration'].items():
            if data['count'] > 0:
                bias = data['actual_rate'] - data['predicted_avg']
                bias_emoji = "🟢" if abs(bias) < 0.05 else "🟡" if abs(bias) < 0.10 else "🔴"
                print(f"  {bin_range}: Predicted {data['predicted_avg']:.1%} | Actual {data['actual_rate']:.1%} | {bias:+.1%} bias {bias_emoji} | n={data['count']}")
        print()
        
        print(f"💡 RECOMMENDED KELLY FRACTION: {report['recommended_kelly_fraction']:.0%}")
        print()
        
        if report['model_performance']:
            print("🤖 MODEL PERFORMANCE (Individual)")
            for model, perf in report['model_performance'].items():
                print(f"  {model}: Brier={perf['mean_brier']:.4f} | n={perf['predictions_count']}")
            print()
        
        print("=" * 80)


# Simple test
if __name__ == "__main__":
    tracker = PredictionTracker()
    
    # Simulate some predictions
    print("Testing PredictionTracker...")
    
    # Add a test prediction
    record = tracker.record_prediction(
        market_slug="test-market-1",
        question="Will it rain tomorrow?",
        predicted_prob=0.70,
        market_price=0.55,
        side="YES",
        position_size=1000,
        model_predictions={'momentum': 0.65, 'sentiment': 0.75}
    )
    print(f"Recorded prediction: {record}")
    
    # Display report
    tracker.display_report()
    
    # Resolve the market
    tracker.record_outcome("test-market-1", 1)  # YES won
    
    # Display updated report
    print("\nAfter resolution:")
    tracker.display_report()
