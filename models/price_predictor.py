"""
Price Prediction Models
LSTM-inspired and other models for forecasting market prices.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path


@dataclass
class PricePrediction:
    """Result from price prediction model"""
    market_slug: str
    predicted_price: float
    confidence: float  # 0-1, higher = more confident
    trend_direction: str  # 'UP', 'DOWN', 'NEUTRAL'
    features_used: List[str]
    model_name: str


class SimplePricePredictor:
    """
    LSTM-inspired price predictor using momentum and mean reversion.
    
    This is a simplified version that captures key LSTM concepts:
    - Temporal dependencies (momentum)
    - Feature extraction (volatility, distance from mean)
    - Confidence estimation
    
    Future upgrade: Replace with actual LSTM using tensorflow/pytorch
    """
    
    def __init__(self, lookback: int = 10, memory_size: int = 100):
        self.lookback = lookback
        self.memory_size = memory_size
        self.price_memory: Dict[str, List[Dict]] = {}  # Store recent prices with timestamps
    
    def update(self, market_slug: str, price: float, timestamp: Optional[datetime] = None):
        """
        Add new price observation.
        
        Args:
            market_slug: Market identifier
            price: Current price (0-1)
            timestamp: Optional timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        if market_slug not in self.price_memory:
            self.price_memory[market_slug] = []
        
        self.price_memory[market_slug].append({
            'price': price,
            'timestamp': timestamp.isoformat()
        })
        
        # Keep only recent history
        if len(self.price_memory[market_slug]) > self.memory_size:
            self.price_memory[market_slug] = self.price_memory[market_slug][-self.memory_size:]
    
    def predict(self, market_slug: str) -> PricePrediction:
        """
        Predict next price using momentum + mean reversion heuristics.
        
        Args:
            market_slug: Market to predict
            
        Returns:
            PricePrediction with forecast and confidence
        """
        prices_data = self.price_memory.get(market_slug, [])
        
        if len(prices_data) < 5:
            # Not enough data
            current = prices_data[-1]['price'] if prices_data else 0.5
            return PricePrediction(
                market_slug=market_slug,
                predicted_price=current,
                confidence=0.3,
                trend_direction='NEUTRAL',
                features_used=['insufficient_data'],
                model_name='SimplePricePredictor'
            )
        
        prices = [p['price'] for p in prices_data]
        current_price = prices[-1]
        
        # Extract features (like LSTM would learn)
        features = self._extract_features(prices)
        
        # Apply heuristics based on features
        predicted_price = self._apply_heuristics(current_price, features)
        
        # Calculate confidence based on data quality and volatility
        confidence = self._calculate_confidence(features)
        
        # Determine trend direction
        trend = self._determine_trend(features['momentum'])
        
        return PricePrediction(
            market_slug=market_slug,
            predicted_price=predicted_price,
            confidence=confidence,
            trend_direction=trend,
            features_used=list(features.keys()),
            model_name='SimplePricePredictor'
        )
    
    def _extract_features(self, prices: List[float]) -> Dict:
        """Extract features from price history"""
        n = len(prices)
        
        # Short and long term windows
        short_window = min(5, n)
        long_window = min(self.lookback, n)
        
        recent = prices[-short_window:]
        longer = prices[-long_window:]
        
        features = {
            'current_price': prices[-1],
            'short_ma': np.mean(recent),
            'long_ma': np.mean(longer),
            'momentum': (recent[-1] - recent[0]) / recent[0] if recent[0] > 0 else 0,
            'volatility': np.std(prices[-10:]) if len(prices) >= 10 else np.std(prices),
            'distance_from_mid': abs(prices[-1] - 0.5),
            'price_velocity': prices[-1] - prices[-2] if len(prices) >= 2 else 0,
            'max_recent': max(prices[-10:]) if len(prices) >= 10 else max(prices),
            'min_recent': min(prices[-10:]) if len(prices) >= 10 else min(prices),
            'data_points': len(prices)
        }
        
        return features
    
    def _apply_heuristics(self, current_price: float, features: Dict) -> float:
        """Apply trading heuristics to predict price"""
        
        # Base prediction: follow momentum slightly
        prediction = current_price + features['momentum'] * 0.05
        
        # Mean reversion at extremes
        if current_price > 0.85:
            # Overbought - pull back toward 0.75
            prediction -= features['volatility'] * 0.3
        elif current_price < 0.15:
            # Oversold - bounce toward 0.25
            prediction += features['volatility'] * 0.3
        
        # Trend following in middle range
        if 0.20 <= current_price <= 0.80:
            if features['momentum'] > 0.05:
                prediction += features['momentum'] * 0.03
            elif features['momentum'] < -0.05:
                prediction += features['momentum'] * 0.03
        
        # Volatility dampening
        if features['volatility'] > 0.1:
            # High volatility = less predictable, pull toward current
            prediction = 0.7 * prediction + 0.3 * current_price
        
        # Clip to valid range
        return np.clip(prediction, 0.05, 0.95)
    
    def _calculate_confidence(self, features: Dict) -> float:
        """Calculate prediction confidence"""
        
        # More data = higher confidence
        data_confidence = min(1.0, features['data_points'] / 20)
        
        # Lower volatility = higher confidence
        vol_confidence = max(0.0, 1.0 - features['volatility'] * 5)
        
        # Extreme prices = lower confidence (harder to predict)
        extreme_penalty = 1.0 - features['distance_from_mid'] * 0.5
        
        # Combine factors
        confidence = (data_confidence * 0.4 + 
                     vol_confidence * 0.4 + 
                     extreme_penalty * 0.2)
        
        return np.clip(confidence, 0.1, 0.95)
    
    def _determine_trend(self, momentum: float) -> str:
        """Determine trend direction from momentum"""
        if momentum > 0.03:
            return 'UP'
        elif momentum < -0.03:
            return 'DOWN'
        return 'NEUTRAL'
    
    def get_price_history(self, market_slug: str, n: int = 10) -> List[float]:
        """Get recent price history for a market"""
        data = self.price_memory.get(market_slug, [])
        return [d['price'] for d in data[-n:]]
    
    def has_sufficient_data(self, market_slug: str, min_points: int = 5) -> bool:
        """Check if we have enough data for reliable prediction"""
        return len(self.price_memory.get(market_slug, [])) >= min_points
    
    def save_state(self, filepath: str):
        """Save price memory to file"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.price_memory, f, indent=2)
    
    def load_state(self, filepath: str):
        """Load price memory from file"""
        if Path(filepath).exists():
            with open(filepath, 'r') as f:
                self.price_memory = json.load(f)


class MomentumPredictor:
    """
    Simple momentum-based predictor.
    Good for trending markets.
    """
    
    def __init__(self, short_window: int = 3, long_window: int = 10):
        self.short_window = short_window
        self.long_window = long_window
        self.price_memory: Dict[str, List[float]] = {}
    
    def update(self, market_slug: str, price: float):
        """Add price observation"""
        if market_slug not in self.price_memory:
            self.price_memory[market_slug] = []
        self.price_memory[market_slug].append(price)
        # Keep limited history
        self.price_memory[market_slug] = self.price_memory[market_slug][-50:]
    
    def predict(self, market_slug: str) -> PricePrediction:
        """Generate momentum signal"""
        prices = self.price_memory.get(market_slug, [])
        
        if len(prices) < self.long_window:
            return PricePrediction(
                market_slug=market_slug,
                predicted_price=prices[-1] if prices else 0.5,
                confidence=0.2,
                trend_direction='NEUTRAL',
                features_used=['insufficient_data'],
                model_name='MomentumPredictor'
            )
        
        short_ma = np.mean(prices[-self.short_window:])
        long_ma = np.mean(prices[-self.long_window:])
        
        # Momentum signal
        momentum = (short_ma - long_ma) / long_ma if long_ma > 0 else 0
        
        current = prices[-1]
        predicted = current + momentum * current * 0.5
        predicted = np.clip(predicted, 0.05, 0.95)
        
        # Confidence based on momentum strength
        confidence = min(0.9, 0.5 + abs(momentum) * 2)
        
        trend = 'UP' if momentum > 0.02 else 'DOWN' if momentum < -0.02 else 'NEUTRAL'
        
        return PricePrediction(
            market_slug=market_slug,
            predicted_price=predicted,
            confidence=confidence,
            trend_direction=trend,
            features_used=['short_ma', 'long_ma', 'momentum'],
            model_name='MomentumPredictor'
        )


class MeanReversionPredictor:
    """
    Mean reversion predictor.
    Good for oscillating markets.
    """
    
    def __init__(self, window: int = 20, mean: float = 0.5):
        self.window = window
        self.mean = mean
        self.price_memory: Dict[str, List[float]] = {}
    
    def update(self, market_slug: str, price: float):
        """Add price observation"""
        if market_slug not in self.price_memory:
            self.price_memory[market_slug] = []
        self.price_memory[market_slug].append(price)
        self.price_memory[market_slug] = self.price_memory[market_slug][-50:]
    
    def predict(self, market_slug: str) -> PricePrediction:
        """Generate mean reversion signal"""
        prices = self.price_memory.get(market_slug, [])
        
        if len(prices) < 5:
            return PricePrediction(
                market_slug=market_slug,
                predicted_price=prices[-1] if prices else 0.5,
                confidence=0.2,
                trend_direction='NEUTRAL',
                features_used=['insufficient_data'],
                model_name='MeanReversionPredictor'
            )
        
        current = prices[-1]
        ma = np.mean(prices[-self.window:]) if len(prices) >= self.window else np.mean(prices)
        
        # Distance from mean
        distance = current - self.mean
        
        # Predict reversion toward mean
        reversion_strength = abs(distance) * 0.3
        predicted = current - np.sign(distance) * reversion_strength
        predicted = np.clip(predicted, 0.05, 0.95)
        
        # Confidence higher when far from mean
        confidence = min(0.9, 0.4 + abs(distance) * 0.8)
        
        trend = 'DOWN' if distance > 0.1 else 'UP' if distance < -0.1 else 'NEUTRAL'
        
        return PricePrediction(
            market_slug=market_slug,
            predicted_price=predicted,
            confidence=confidence,
            trend_direction=trend,
            features_used=['mean', 'distance_from_mean', 'ma'],
            model_name='MeanReversionPredictor'
        )


# Simple test
if __name__ == "__main__":
    print("Testing Price Predictors...")
    
    # Test SimplePricePredictor
    predictor = SimplePricePredictor()
    
    # Simulate price data for a trending market
    market = "test-trending"
    base_price = 0.45
    for i in range(20):
        # Upward trend
        price = base_price + i * 0.01 + np.random.normal(0, 0.01)
        price = np.clip(price, 0.05, 0.95)
        predictor.update(market, price)
    
    pred = predictor.predict(market)
    print(f"\nTrending Market Prediction:")
    print(f"  Predicted: {pred.predicted_price:.2%}")
    print(f"  Confidence: {pred.confidence:.0%}")
    print(f"  Trend: {pred.trend_direction}")
    print(f"  Features: {pred.features_used}")
    
    # Test extreme market
    market2 = "test-extreme"
    for price in [0.88, 0.89, 0.90, 0.91, 0.90, 0.89, 0.90]:
        predictor.update(market2, price)
    
    pred2 = predictor.predict(market2)
    print(f"\nExtreme Market (Overbought) Prediction:")
    print(f"  Predicted: {pred2.predicted_price:.2%}")
    print(f"  Confidence: {pred2.confidence:.0%}")
    print(f"  Trend: {pred2.trend_direction}")
    
    # Test MomentumPredictor
    momentum = MomentumPredictor()
    for price in [0.4, 0.42, 0.41, 0.43, 0.45, 0.47, 0.48, 0.50, 0.52, 0.53]:
        momentum.update("momentum-test", price)
    
    mom_pred = momentum.predict("momentum-test")
    print(f"\nMomentum Predictor:")
    print(f"  Predicted: {mom_pred.predicted_price:.2%}")
    print(f"  Trend: {mom_pred.trend_direction}")
    
    # Test MeanReversionPredictor
    reversion = MeanReversionPredictor()
    for price in [0.75, 0.76, 0.78, 0.77, 0.79, 0.80, 0.78, 0.79]:
        reversion.update("reversion-test", price)
    
    rev_pred = reversion.predict("reversion-test")
    print(f"\nMean Reversion Predictor:")
    print(f"  Predicted: {rev_pred.predicted_price:.2%}")
    print(f"  Trend: {rev_pred.trend_direction}")
    
    print("\n✅ All predictors working!")
