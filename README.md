# Polymarket Trading Toolkit 🤖

A comprehensive, AI-powered suite of tools for analyzing and trading on Polymarket prediction markets.

> **New in v3.0**: Three parallel paper trading strategies (A/B/C) with automated TP/SL monitoring, strategy comparison dashboard, and enhanced documentation.

---

## 🚀 Quick Start

```bash
cd ~/projects/polymarket-trader
python3 polymarket.py
```

**Try the AI-powered calculator:**
```bash
python3 polymarket.py ai-calc
```

**Run all strategies manually:**
```bash
python3 run_all_strategies.py
```

**View strategy dashboard:**
```bash
python3 strategy_dashboard.py
```

---

## 📦 What's New (v3.0)

### 🎯 Three Parallel Trading Strategies

All strategies run every 5 minutes via cron, each with its own database and capital allocation:

| Strategy | Approach | Time Filter | Min Edge | Capital |
|----------|----------|-------------|----------|---------|
| **A** | Hard 7-Day Filter | ≤7 days only | 5% | $1,000 |
| **B** | Aggressive Multipliers | All timeframes | 5% | $1,000 |
| **C** | Tiered Allocation | Strict tier limits | 5-15% | $1,000 |

**Strategy A (7-Day Hard Filter):**
- Only trades markets resolving within 7 days
- Maximum capital velocity
- 3.0x priority multiplier for speed
- Weekly feedback cycle

**Strategy B (Aggressive Multipliers):**
- <7 days: **3.0x** multiplier
- 7-30 days: **2.0x** multiplier  
- 30-90 days: **1.25x** multiplier
- >90 days: **0.5x** penalty

**Strategy C (Tiered Allocation):**
- **Tier 1** (<30 days): 70% max capital, 5% edge, 2.5x multiplier
- **Tier 2** (30-90 days): 30% max capital, 7% edge, 1.0x multiplier
- **Tier 3** (>90 days): 10% max capital, 15% edge, 0.5x multiplier

### 📊 Strategy Comparison Dashboard

Real-time performance tracking across all strategies:

```bash
python3 strategy_dashboard.py
```

**Metrics Tracked:**
- Open/closed trade counts
- Exposure and available capital
- Average edge and holding time
- Win rate and P&L by exit type
- Capital turnover efficiency

### 🤖 Automated Operations

Every 5 minutes (via cron):
1. Check take-profit (TP) hits
2. Check stop-loss (SL) hits
3. Update resolved market outcomes
4. Generate new signals if capital available
5. Save to strategy-specific database

**Logs:** `logs/all_strategies.log`

---

## 📚 Core AI Components (v2.0)

### 1. Ensemble Edge Estimator (`models/edge_estimator.py`)

Two-layer ensemble architecture achieving **20% ROI improvement** over single models.

**Layer 1 - Base Models:**
- **SimplePricePredictor**: LSTM-inspired with momentum + mean reversion
- **MomentumStrategy**: Pure trend-following
- **MeanReversionStrategy**: Extreme price reversion
- **FundamentalModel**: Category base rates
- **SentimentModel**: NLP-based signals

**Layer 2 - Meta-Learner:**
- Dynamic weighting by financial performance (not accuracy!)
- Softmax allocation based on Sharpe ratios

**Usage:**
```python
from models.edge_estimator import EnsembleEdgeEstimator

estimator = EnsembleEdgeEstimator()
estimator.update_price('market-slug', 0.65)

estimate = estimator.estimate_probability(
    'market-slug', 
    'Will it rain tomorrow?', 
    0.65, 
    'weather'
)

print(f"AI Prediction: {estimate.ensemble_probability:.2%}")
print(f"Edge: {estimate.edge:+.2%}")
print(f"Confidence: {estimate.confidence:.0%}")
print(f"Recommendation: {estimate.recommendation}")
```

### 2. Adaptive Kelly Criterion (`strategies/adaptive_kelly.py`)

Dynamic position sizing that learns from your performance.

**Features:**
- ✅ **Calibration tracking**: Adjusts Kelly fraction based on Brier scores
- ✅ **Confidence weighting**: Smaller positions when uncertain
- ✅ **Correlation penalty**: Reduces size when over-exposed
- ✅ **Drawdown protection**: Reduces/stops trading during drawdowns
- ✅ **Portfolio optimization**: Simultaneous Kelly for correlated positions

**Kelly Fraction Recommendations:**
| Brier Score | Recommended Kelly |
|-------------|-------------------|
| < 0.10 | 50% |
| 0.10 - 0.15 | 35% |
| 0.15 - 0.20 | 25% |
| 0.20 - 0.25 | 15% |
| > 0.25 | 10% |

**Usage:**
```python
from strategies.adaptive_kelly import AdaptiveKelly

kelly = AdaptiveKelly()
result = kelly.calculate_position_size(
    bankroll=10000,
    market_price=0.55,
    estimated_prob=0.70,
    confidence=0.8,
    correlated_exposure=0.10,
    current_drawdown=0.05
)

print(f"Position Size: ${result.position_size:.2f}")
print(f"Adjusted Kelly: {result.adjusted_fraction:.2%}")
print(f"Rationale: {result.rationale}")
```

### 3. Multi-Strategy Portfolio (`strategies/portfolio.py`)

Diversified strategies reduce tail risk and provide robustness.

**Included Strategies:**
1. **SentimentStrategy** - NLP-based long-term signals
2. **MomentumStrategy** - Trend following
3. **MeanReversionStrategy** - Oscillation at extremes
4. **ArbitrageStrategy** - Yes+No spread detection
5. **EnsembleStrategy** - Full ensemble prediction

**Features:**
- Dynamic allocation by Sharpe ratio
- Performance tracking per strategy
- Category exposure limits
- Automatic rebalancing

### 4. AI-Powered Calculator (`utils/ai_calculator.py`)

Interactive calculator with full AI integration.

**Features:**
- 🤖 Ensemble probability predictions
- 📊 Adaptive Kelly position sizing
- 📝 Prediction tracking for calibration
- ✅ Market resolution recording
- 📈 Calibration reports
- 🎯 Strategy performance display

### 5. 75% Edge Rule (Take-Profit Strategy)

Capture 75% of your edge and recycle capital faster.

**Formula:** `Take-Profit % = (Initial Edge × 0.75) / Entry Price`

**Example:** 10% edge at $0.40 entry → 18.75% price move target → Exit at $0.475

**Benefits:**
- Faster capital recycling (20-30% shorter hold times)
- Reduced exposure to time decay and new information
- Higher win rate with smaller, more frequent profits

See [ADR 005](docs/adr/005-fifty-percent-edge-rule.md) for full specification.

---

## 📊 Original Tools

### Market Scanner (`scanner.py`)
Find trading opportunities across Polymarket.

**Features:**
- Arbitrage detection (Yes + No prices ≠ $1.00)
- High-volume market finder
- Markets closing soon tracker
- Value opportunity identifier

### Position Tracker (`position_tracker.py`)
Track open positions and monitor P&L.

### Alert System (`alert_system.py`)
Monitor markets and get notified of price movements.

---

## 🎯 Trading Strategies Reference

### Individual Strategy Files

| File | Description |
|------|-------------|
| `strategies/strategy_a_generator.py` | 7-day hard filter implementation |
| `strategies/strategy_b_generator.py` | Aggressive multiplier implementation |
| `strategies/strategy_c_generator.py` | Tiered allocation implementation |
| `strategies/portfolio.py` | Multi-strategy portfolio base classes |
| `strategies/adaptive_kelly.py` | Position sizing with dynamic adjustments |

### Utility Files

| File | Description |
|------|-------------|
| `utils/paper_trading_db.py` | SQLite database interface |
| `utils/paper_trading_signals.py` | Signal generation utilities |
| `utils/paper_trading_tp_monitor.py` | TP/SL hit monitoring |
| `utils/paper_trading_updater.py` | Outcome resolution handling |
| `utils/take_profit_calculator.py` | TP/SL level calculations |
| `utils/prediction_tracker.py` | Calibration tracking |
| `utils/backtest.py` | Strategy backtesting framework |
| `utils/ai_calculator.py` | Interactive AI calculator |
| `utils/adverse_selection_monitor.py` | Alpha decay detection |
| `utils/slippage_model.py` | Market impact modeling |

### Model Files

| File | Description |
|------|-------------|
| `models/edge_estimator.py` | Two-layer ensemble predictor |
| `models/price_predictor.py` | LSTM-inspired price models |

---

## ⚠️ Risk Management

### Position Sizing Rules (AI-Enhanced)

**Adaptive Kelly adjusts automatically based on:**
- Calibration accuracy (Brier scores)
- Model confidence
- Correlated exposure
- Current drawdown

**Default Limits:**
- Max 50% total exposure
- Max 30% per category
- Kelly fraction: 10-50% (dynamic)

### Take-Profit / Stop-Loss Configuration

- **Take-Profit**: 75% edge capture (configurable 50-90%)
- **Stop-Loss**: 50% of position value at risk
- **Monitoring**: Every 5 minutes via cron

### Common Risks

1. **Model Risk**: AI predictions can be wrong
   - *Mitigation*: Track calibration, adjust Kelly fraction

2. **Overfitting**: Models perform well on backtests but fail live
   - *Mitigation*: Walk-forward testing, out-of-sample validation

3. **Regime Change**: Markets change, strategies stop working
   - *Mitigation*: Multiple strategies, dynamic allocation

4. **Liquidity Risk**: Can't exit large positions
   - *Mitigation*: Check volume, use limit orders

---

## 🧪 Testing

### Run All Tests
```bash
cd ~/projects/polymarket-trader

# Unit tests
python3 -m unittest discover tests/ -v

# Integration tests
python3 -m unittest tests.test_integration -v
```

### Test Coverage
- ✅ Prediction tracking (7 tests)
- ✅ Price prediction models (13 tests)
- ✅ Adaptive Kelly (15 tests)
- ✅ Edge estimator (12 tests)
- ✅ Strategy portfolio (11 tests)
- ✅ AI calculator (3 tests)
- ✅ Backtesting (7 tests)
- ✅ Integration (14 tests)

**Total: 82+ tests**

---

## 🔬 Research Basis

This toolkit implements algorithms from cutting-edge research:

1. **LMSR-RQRU Equivalence** (arXiv 2411.08972)
   - Computational geometry for efficient prediction markets

2. **Two-Layer Ensemble Architecture** (arXiv 2411.13559)
   - 20% ROI improvement over single models
   - Financial return optimization (not accuracy)

3. **Deep Learning for Temporal Prediction** (Royal Society 2024)
   - LSTM + ARIMA fusion: 97.66% accuracy
   - Transformer with attention: 19.4% RMSE reduction

4. **Adaptive Kelly Criterion**
   - Simultaneous Kelly for correlated positions
   - Drawdown-constrained sizing

5. **Multi-Agent Learning** (arXiv 1510.02867)
   - Strategy diversification for robustness

---

## 📈 Performance Expectations

Based on research and backtesting:

| Strategy | Expected Alpha | Sharpe | Max DD |
|----------|---------------|--------|--------|
| AI Ensemble | 2-8% annually | 0.8-1.2 | 15-25% |
| Multi-Strategy | 3-14% annually | 1.0-1.5 | 12-20% |
| Arbitrage | 1-3% per event | 2.0+ | 5-10% |

**Disclaimer**: Past performance doesn't guarantee future results. Always backtest before deploying capital.

---

## 🛠️ Installation

### Requirements
```bash
python3 --version  # 3.8+
pip3 install -r requirements.txt
```

### Dependencies
```
numpy>=1.24.0
requests>=2.28.0
```

---

## 📋 Example Workflow

```bash
# 0. View strategy performance
python3 strategy_dashboard.py

# 1. Find opportunities with AI
python3 polymarket.py ai-calc

# 2. Run all strategies manually
python3 run_all_strategies.py

# 3. Check TP/SL hits for specific strategy
python3 -c "from utils.paper_trading_tp_monitor import check_all_tp_sl; check_all_tp_sl('data/paper_trading_strategy_a.db')"

# 4. Update outcomes
python3 -c "from utils.paper_trading_updater import update_outcomes; update_outcomes('data/paper_trading_strategy_a.db')"

# 5. Scan for arbitrage
python3 polymarket.py scan

# 6. Backtest strategy
python3 -c "
from utils.backtest import BacktestEngine
engine = BacktestEngine()
result = engine.run_backtest(historical_data, verbose=True)
"
```

---

## 📁 Project Structure

```
polymarket-trader/
├── models/                 # Prediction models
│   ├── price_predictor.py
│   └── edge_estimator.py
├── strategies/             # Trading strategies
│   ├── adaptive_kelly.py
│   ├── portfolio.py
│   ├── strategy_a_generator.py   # 7-day filter
│   ├── strategy_b_generator.py   # Aggressive multipliers
│   └── strategy_c_generator.py   # Tiered allocation
├── utils/                  # Utilities
│   ├── prediction_tracker.py
│   ├── ai_calculator.py
│   ├── backtest.py
│   ├── paper_trading_db.py
│   ├── paper_trading_signals.py
│   ├── paper_trading_tp_monitor.py
│   ├── paper_trading_updater.py
│   ├── take_profit_calculator.py
│   ├── adverse_selection_monitor.py
│   └── slippage_model.py
├── tests/                  # Unit tests
│   └── test_*.py
├── docs/                   # Documentation
│   └── adr/                # Architecture Decision Records
├── data/                   # Data storage
│   ├── paper_trading_strategy_a.db
│   ├── paper_trading_strategy_b.db
│   ├── paper_trading_strategy_c.db
│   └── live_markets/
├── logs/                   # Log files
├── results/                # Strategy comparison results
├── run_all_strategies.py   # Master strategy runner
├── strategy_dashboard.py   # Performance dashboard
├── polymarket.py          # Main CLI
├── scanner.py             # Market scanner
├── cron_paper_trading.py  # Cron wrapper (legacy)
└── README.md
```

---

## 🔗 Resources

- **Polymarket**: https://polymarket.com
- **Documentation**: https://docs.polymarket.com
- **Research Papers**: See references above
- **GitHub Issues**: Track development progress

---

## ⚖️ Disclaimer

Prediction market trading involves substantial risk. This toolkit is for educational purposes only. Always:
- Backtest strategies before live trading
- Start with small position sizes
- Never risk more than you can afford to lose
- Check local regulations

The AI components provide predictions but are not guarantees. Past performance of models does not guarantee future results.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

See GitHub Issues for planned features and known bugs.

---

## 📜 License

MIT License - Free for personal and commercial use.

---

**Built with 🤖 AI-powered precision. Happy Trading! 🎯**
