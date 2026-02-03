# Polymarket Trading Toolkit

A comprehensive suite of tools for analyzing and trading on Polymarket prediction markets.

## 🚀 Quick Start

```bash
cd tools/polymarket
python3 polymarket.py
```

Or use individual tools:
```bash
python3 scanner.py              # Scan for opportunities
python3 odds_calculator.py      # Calculate position sizes
python3 position_tracker.py     # Track your portfolio
python3 alert_system.py         # Set price alerts
```

## 📦 Tools Overview

### 1. Market Scanner (`scanner.py`)

Find trading opportunities across Polymarket.

**Features:**
- Arbitrage detection (Yes + No prices ≠ $1.00)
- High-volume market finder
- Markets closing soon tracker
- Value opportunity identifier
- Category filtering

**Usage:**
```bash
python3 scanner.py
# or
python3 polymarket.py scan
```

### 2. Odds Calculator (`odds_calculator.py`)

Calculate optimal bet sizes using Kelly Criterion.

**Features:**
- Expected value calculation
- Kelly Criterion position sizing
- Fractional Kelly (25%, 50%, etc.)
- Portfolio correlation analysis
- Arbitrage detection between correlated markets

**Usage:**
```bash
python3 odds_calculator.py
# Interactive mode - enter your estimates
```

**Example:**
```
Bankroll: $10000
Market YES price: 0.45
Your estimated probability: 0.60

Result: Buy YES with $1,111 (quarter Kelly)
Expected profit: $333
```

### 3. Position Tracker (`position_tracker.py`)

Track your open positions and monitor P&L.

**Features:**
- Portfolio dashboard with real-time pricing
- P&L calculation per position
- Total portfolio value tracking
- Target price and stop-loss alerts
- Position history

**Usage:**
```bash
# View dashboard
python3 position_tracker.py

# Add position
python3 position_tracker.py add

# Close position
python3 position_tracker.py close
```

**Data Storage:**
- Positions saved to `positions.json`
- Persistent across sessions

### 4. Alert System (`alert_system.py`)

Monitor markets and get notified of price movements.

**Features:**
- Price threshold alerts (above/below)
- Percentage change alerts
- Continuous monitoring mode
- Persistent alert storage

**Usage:**
```bash
# View alerts
python3 alert_system.py

# Add alert
python3 alert_system.py add

# Start monitoring
python3 alert_system.py monitor

# Check once
python3 alert_system.py check
```

**Alert Types:**
- `above`: Trigger when price goes above threshold
- `below`: Trigger when price goes below threshold
- `changes_by`: Trigger on % price movement

### 5. Master CLI (`polymarket.py`)

Unified interface for all tools.

**Usage:**
```bash
# Interactive mode
python3 polymarket.py

# Direct commands
python3 polymarket.py scan
python3 polymarket.py calc
python3 polymarket.py portfolio
python3 polymarket.py alerts
```

## 📊 Trading Strategies

### 1. Information Edge
Trade when you have better information than the market.

```python
# Example: You know local weather patterns
market_price = 0.30  # 30% chance of rain
your_estimate = 0.60  # You think 60% chance

if your_estimate > market_price + 0.10:  # 10% edge threshold
    action = "Buy YES"
    confidence = "High"
```

### 2. Arbitrage
Exploit price discrepancies between related markets.

```python
# Market A: "Team wins championship" = $0.40
# Market B: "Team makes finals" = $0.35
# Can't win championship without making finals

if market_a_price > market_b_price:
    arbitrage = market_a_price - market_b_price
    action = "Buy Market B"
```

### 3. Kelly Criterion
Optimal position sizing formula:

```
f* = (bp - q) / b

Where:
b = odds received (decimal - 1)
p = probability of winning
q = probability of losing (1 - p)

Example:
- Share price: $0.40
- Your estimate: 60%
- b = 0.60 / 0.40 = 1.5
- p = 0.60
- q = 0.40
- Kelly = (1.5 × 0.60 - 0.40) / 1.5 = 33%

With quarter Kelly: 8.25% of bankroll
```

## 🎯 POLY Token Airdrop Strategy

Confirmed Q1-Q2 2026 distribution. Optimize your trading:

### High-Value Activities
- ✅ Trading volume (most important)
- ✅ Number of markets traded
- ✅ Unique active days
- ✅ Early market participation
- ✅ Liquidity provision

### Weekly Targets
- Trade in 5+ different markets
- $500+ weekly volume
- Activity on 5+ unique days
- At least 1 trade in new market
- Mix of categories (politics, sports, etc.)

## ⚠️ Risk Management

### Position Sizing Rules

**Conservative:**
- Max 5% per position
- Max 20% correlated exposure
- Always have exit plan

**Moderate:**
- Max 10% per position
- Max 30% correlated exposure
- Use stop-losses

**Aggressive:**
- Max 20% per position
- High conviction trades only
- Accept higher variance

### Common Risks

1. **Resolution Risk**: Ambiguous outcomes, disputed results
2. **Liquidity Risk**: Can't exit large positions
3. **Information Risk**: Late/wrong information
4. **Smart Contract Risk**: Potential vulnerabilities
5. **Regulatory Risk**: Future changes

## 🔧 API Reference

### Endpoints Used

```python
# Gamma API - Market data
https://gamma-api.polymarket.com/markets

# CLOB API - Order book (when available)
https://clob.polymarket.com/book
```

### Rate Limits
- Be respectful: Add delays between requests
- Default: 1 request per second
- Use caching for repeated queries

## 📈 Market Categories

### Politics 🏛️
- Elections (US, global)
- Policy decisions
- Legislation outcomes
- Court decisions

### Sports ⚽
- Game outcomes
- Championship winners
- Player performance
- Transfer rumors

### Business 💼
- Earnings reports
- Product launches
- M&A activity
- IPO timing

### Entertainment 🎬
- Award shows
- Box office performance
- TV ratings
- Celebrity events

### Economics 📈
- Fed rate decisions
- Inflation data
- Employment numbers
- GDP reports

## 💡 Pro Tips

1. **Always use fractional Kelly** - Full Kelly is too aggressive
2. **Check markets closing soon** - Time decay creates opportunities
3. **Monitor high-volume markets** - Better liquidity, tighter spreads
4. **Set alerts on positions** - Don't watch charts all day
5. **Diversify across categories** - Reduces correlation risk
6. **Track your edge** - Document why you made each trade
7. **Review regularly** - Learn from wins and losses

## 🛠️ Installation

### Requirements
```bash
python3 --version  # 3.8+
pip3 install requests
```

### Optional Enhancements
```bash
# For notifications
pip3 install python-telegram-bot

# For data analysis
pip3 install pandas matplotlib
```

## 📋 Example Workflow

```bash
# 1. Find opportunities
python3 scanner.py

# 2. Analyze specific market
python3 odds_calculator.py
# Enter: Bankroll=10000, Price=0.45, YourProb=0.60
# Result: Buy YES with $1,111

# 3. Add to portfolio
python3 position_tracker.py add
# Enter market details

# 4. Set alerts
python3 alert_system.py add
# Set target at $0.70, stop at $0.30

# 5. Monitor
python3 alert_system.py monitor
```

## 🔗 Resources

- **Polymarket**: https://polymarket.com
- **Documentation**: https://docs.polymarket.com
- **Community**: Polymarket Discord
- **Twitter**: @Polymarket

## ⚖️ Disclaimer

Prediction market trading involves risk. Past performance doesn't guarantee future results. Always trade responsibly and never risk more than you can afford to lose. This toolkit is for educational purposes only. Check local regulations before trading.

## 🤝 Contributing

To add new features:
1. Create a new tool file
2. Add to `polymarket.py` master CLI
3. Update this README
4. Submit pull request

## 📜 License

MIT License - Free for personal and commercial use.

---

**Happy Trading! 🎯**
