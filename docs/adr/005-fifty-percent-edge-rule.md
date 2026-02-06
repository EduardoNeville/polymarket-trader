# ADR 005: 75% Edge Rule Take-Profit Strategy

## Status
Proposed

## Context
The current backtesting and paper trading systems hold all positions until market resolution. This approach:
- Ties up capital for extended periods (days to weeks)
- Exposes positions to time decay and new information risk
- Misses opportunities to recycle capital into new trades

We need a systematic take-profit mechanism that captures a portion of our edge while freeing up capital for reuse.

## Decision
Implement the **75% Edge Rule** take-profit strategy with the following formula:

### Formula

```
Take-Profit % = (Initial Edge × 0.75) / Entry Price
```

Where:
- **Initial Edge** = Estimated Probability - Market Price
- **Entry Price** = Market price at position entry
- **0.75** = Capture 75% of the edge (configurable)

### Target Price Calculation

**For YES positions:**
```
Target Price = Entry Price + (Entry Price × Take-Profit %)
```

**For NO positions:**
```
NO Entry Price = 1 - YES Entry Price
Target NO Price = NO Entry Price - (NO Entry Price × Take-Profit %)
Target YES Price = 1 - Target NO Price
```

### Examples

#### Example 1: YES Position
- Market Price: $0.40
- Estimated Probability: 50% (0.50)
- Initial Edge: 10% (0.10)
- Take-Profit %: (0.10 × 0.75) / 0.40 = 18.75%
- Target Price: 0.40 + (0.40 × 0.1875) = **$0.475**
- Captured Edge: $0.075 (75% of original $0.10 edge)

#### Example 2: NO Position
- Market Price (YES): $0.65
- Estimated Probability (YES): 50% (0.50)
- Initial Edge (YES): -15% (-0.15) → Trade NO side
- NO Entry Price: 1 - 0.65 = $0.35
- Take-Profit %: (0.15 × 0.75) / 0.35 = 32.1%
- Target NO Price: 0.35 - (0.35 × 0.321) = $0.238
- Target YES Price: 1 - 0.238 = **$0.762**
- Captured Edge: $0.112 (75% of original $0.15 edge)

#### Example 3: Small Edge Position
- Market Price: $0.55
- Estimated Probability: 60% (0.60)
- Initial Edge: 5% (0.05)
- Take-Profit %: (0.05 × 0.75) / 0.55 = 6.8%
- Target Price: 0.55 + (0.55 × 0.068) = **$0.587**

## Edge Cases and Validation Rules

### 1. Price Bounds
- **Rule**: Target price must be within [0.01, 0.99]
- **Rationale**: Polymarket prices cannot reach 0 or 1 until resolution
- **Action**: If calculated target is outside bounds, mark as `is_reachable = False`

### 2. Minimum Edge Threshold
- **Rule**: Only apply take-profit if |Initial Edge| ≥ 5%
- **Rationale**: Small edges produce tiny TP targets that may trigger too frequently
- **Action**: For edges < 5%, hold to resolution

### 3. Extreme Entry Prices
- **Rule**: For entry prices > 0.90 or < 0.10, skip take-profit
- **Rationale**: Limited price movement room makes TP impractical
- **Action**: Hold to resolution for extreme prices

### 4. Negative Edges
- **Rule**: Do not trade if edge is negative
- **Rationale**: Trading with negative expected value is unprofitable
- **Action**: Signal should not generate a trade

### 5. Edge Capture Ratio
- **Default**: 0.75 (75%)
- **Range**: Configurable from 0.5 to 0.9
- **Rationale**: 
  - < 50%: TP triggers too frequently, leaving profit on table
  - 75%: Balanced - captures most edge while allowing capital recycling
  - > 90%: TP becomes unlikely to trigger, defeating the purpose

## Trade Exit Reasons

When a trade closes, record the reason:

| Exit Reason | Description |
|-------------|-------------|
| `tp` | Take-profit level was hit |
| `resolution` | Market resolved (original behavior) |
| `stop_loss` | Stop-loss triggered (future enhancement) |
| `manual` | Manual intervention |
| `expired` | Market expired without resolution |

## Expected Benefits

1. **Faster Capital Recycling**: Reduce average holding time by ~20-30%
2. **Reduced Time Exposure**: Less exposure to new information and volatility
3. **Higher Win Rate**: Capture smaller, more frequent wins
4. **Compounding Effect**: Reinvest profits sooner

## Expected Trade-offs

1. **Smaller Per-Trade Profits**: Capture 75% of edge vs. full potential (better than 50%)
2. **Missed Runners**: Some trades would have been more profitable if held
3. **Target Calculation Overhead**: Additional computation for each trade

## Validation Targets

- TP hit rate: 15-20% of trades
- Average holding time reduction: 20-30%
- Overall P&L impact: Neutral to slightly positive
- Win rate improvement: +5-10%

## Implementation Plan

See GitHub issues #42-48 for detailed implementation steps:
- Issue #42: Documentation (this ADR)
- Issue #43: Trade dataclass enhancement
- Issue #44: Database schema update
- Issue #45: TP calculator utility
- Issue #46: Backtest engine modification
- Issue #47: Comparison script
- Issue #48: Validation and decision

## Related Decisions

- ADR 003: Adaptive Kelly Criterion (position sizing)
- ADR 004: Ensemble Edge Estimator (edge calculation)

## Notes

- The 50% capture ratio is a starting point; may be optimized based on backtest results
- Consider asymmetric rules (different capture ratios for winning vs losing positions)
- Monitor for adverse selection: do TP-triggered trades tend to resolve differently?

## References

- Original proposal: GitHub issue discussion, 2026-02-06
- Kelly Criterion: "A New Interpretation of Information Rate" (Kelly, 1956)
- Take-profit strategies: "Profit Target and Stop-Loss in Trading" (various)
