"""
Take-Profit Calculator
Calculate take-profit levels using the 50% Edge Rule.

Formula: Take-Profit % = (Initial Edge × 0.5) / Entry Price
"""

import numpy as np
from typing import Optional
from dataclasses import dataclass


@dataclass
class TakeProfitLevel:
    """Result from take-profit calculation"""
    target_price: float          # Target exit price (YES price)
    target_pct_move: float       # Calculated percentage move
    captured_edge: float         # How much edge we capture
    is_reachable: bool           # False if target outside [0.01, 0.99]
    edge_capture_ratio: float    # Configurable ratio (default 0.5)
    initial_edge: float          # Original edge at entry
    entry_price: float           # Entry price (YES price)
    side: str                    # 'YES' or 'NO'


def calculate_take_profit(
    entry_price: float,
    estimated_prob: float,
    side: str,
    edge_capture_ratio: float = 0.5,
    min_edge_threshold: float = 0.05,
    min_price: float = 0.01,
    max_price: float = 0.99
) -> Optional[TakeProfitLevel]:
    """
    Calculate take-profit level using the 50% Edge Rule.
    
    Formula: TP% = (Initial Edge × Edge_Capture_Ratio) / Entry_Price
    
    Args:
        entry_price: Market YES price at entry (0.0 - 1.0)
        estimated_prob: Your estimated probability of YES (0.0 - 1.0)
        side: 'YES' or 'NO' - which side we're trading
        edge_capture_ratio: How much edge to capture (default 0.5 = 50%)
        min_edge_threshold: Minimum |edge| to apply TP (default 0.05 = 5%)
        min_price: Minimum valid price (default 0.01)
        max_price: Maximum valid price (default 0.99)
    
    Returns:
        TakeProfitLevel if valid, None if:
        - Edge is below minimum threshold
        - Entry price is outside valid range
        - Side is invalid
    
    Examples:
        >>> # YES position: 10% edge at $0.40 entry
        >>> tp = calculate_take_profit(0.40, 0.50, 'YES')
        >>> print(f"Target: ${tp.target_price:.2f}")  # $0.45
        
        >>> # NO position: 15% edge at YES=$0.65 (NO=$0.35)
        >>> tp = calculate_take_profit(0.65, 0.50, 'NO')
        >>> print(f"Target: ${tp.target_price:.2f}")  # $0.725
    """
    # Validate inputs
    if side not in ('YES', 'NO'):
        raise ValueError(f"Side must be 'YES' or 'NO', got '{side}'")
    
    if not (0.0 <= entry_price <= 1.0):
        raise ValueError(f"Entry price must be between 0 and 1, got {entry_price}")
    
    if not (0.0 <= estimated_prob <= 1.0):
        raise ValueError(f"Estimated prob must be between 0 and 1, got {estimated_prob}")
    
    # Calculate edge based on side
    if side == 'YES':
        initial_edge = estimated_prob - entry_price
    else:  # NO
        no_entry_price = 1 - entry_price
        no_estimated_prob = 1 - estimated_prob
        initial_edge = no_estimated_prob - no_entry_price
    
    # Check minimum edge threshold
    if abs(initial_edge) < min_edge_threshold:
        return None
    
    # Check extreme prices - skip TP for prices > 0.90 or < 0.10
    if entry_price > 0.90 or entry_price < 0.10:
        return None
    
    # Calculate take-profit percentage
    # TP% = (Edge × Capture_Ratio) / Entry_Price
    if side == 'YES':
        tp_pct = (abs(initial_edge) * edge_capture_ratio) / entry_price
        target_price = entry_price + (entry_price * tp_pct)
    else:  # NO
        no_entry_price = 1 - entry_price
        tp_pct = (abs(initial_edge) * edge_capture_ratio) / no_entry_price
        target_no_price = no_entry_price - (no_entry_price * tp_pct)
        target_price = 1 - target_no_price
    
    # Check if target is reachable (within bounds)
    is_reachable = min_price <= target_price <= max_price
    
    # Calculate captured edge
    if side == 'YES':
        captured_edge = target_price - entry_price
    else:
        captured_edge = entry_price - target_price
    
    return TakeProfitLevel(
        target_price=round(target_price, 4),
        target_pct_move=round(tp_pct, 4),
        captured_edge=round(captured_edge, 4),
        is_reachable=is_reachable,
        edge_capture_ratio=edge_capture_ratio,
        initial_edge=round(initial_edge, 4),
        entry_price=entry_price,
        side=side
    )


def check_take_profit_hit(
    entry_price: float,
    current_price: float,
    tp_level: TakeProfitLevel,
    side: str
) -> bool:
    """
    Check if price has hit the take-profit level.
    
    Args:
        entry_price: Original entry price (YES price)
        current_price: Current market price (YES price)
        tp_level: TakeProfitLevel from calculate_take_profit()
        side: 'YES' or 'NO'
    
    Returns:
        True if TP level has been hit or exceeded
    
    Examples:
        >>> tp = calculate_take_profit(0.40, 0.50, 'YES')
        >>> hit = check_take_profit_hit(0.40, 0.46, tp, 'YES')
        >>> print(hit)  # True (0.46 > 0.45 target)
    """
    if side == 'YES':
        # For YES positions, TP hit when current >= target
        return current_price >= tp_level.target_price
    else:  # NO
        # For NO positions, TP hit when current <= target
        return current_price <= tp_level.target_price


def calculate_holding_days(
    entry_timestamp: str,
    exit_timestamp: str
) -> int:
    """
    Calculate number of days a position was held (calendar days).
    
    Args:
        entry_timestamp: ISO format entry timestamp
        exit_timestamp: ISO format exit timestamp
    
    Returns:
        Number of calendar days between entry and exit
    
    Example:
        >>> days = calculate_holding_days(
        ...     '2024-01-01T10:00:00',
        ...     '2024-01-05T14:30:00'
        ... )
        >>> print(days)  # 4
    """
    from datetime import datetime
    
    # Parse timestamps (handle various ISO formats)
    for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%d %H:%M:%S']:
        try:
            entry_dt = datetime.strptime(entry_timestamp[:19], fmt[:19])
            exit_dt = datetime.strptime(exit_timestamp[:19], fmt[:19])
            break
        except ValueError:
            continue
    else:
        # Fallback: try pandas if available
        try:
            import pandas as pd
            entry_dt = pd.to_datetime(entry_timestamp)
            exit_dt = pd.to_datetime(exit_timestamp)
        except:
            raise ValueError(f"Could not parse timestamps: {entry_timestamp}, {exit_timestamp}")
    
    # Use calendar days (difference in dates, not 24-hour periods)
    entry_date = entry_dt.date()
    exit_date = exit_dt.date()
    days = (exit_date - entry_date).days
    return max(0, days)


def get_tp_summary(tp_level: TakeProfitLevel) -> str:
    """
    Get a human-readable summary of the take-profit level.
    
    Args:
        tp_level: TakeProfitLevel object
    
    Returns:
        Formatted summary string
    """
    lines = [
        f"Take-Profit Summary:",
        f"  Side: {tp_level.side}",
        f"  Entry Price: ${tp_level.entry_price:.2f}",
        f"  Initial Edge: {tp_level.initial_edge:+.1%}",
        f"  Capture Ratio: {tp_level.edge_capture_ratio:.0%}",
        f"  Target Move: {tp_level.target_pct_move:.1%}",
        f"  Target Price: ${tp_level.target_price:.2f}",
        f"  Captured Edge: ${tp_level.captured_edge:.2f}",
        f"  Reachable: {'Yes' if tp_level.is_reachable else 'No'}"
    ]
    return "\n".join(lines)


# Example/test usage
if __name__ == "__main__":
    print("=" * 70)
    print("🎯 Take-Profit Calculator Examples")
    print("=" * 70)
    
    # Example 1: YES position with 10% edge
    print("\n1. YES Position: 10% edge at $0.40 entry")
    print("-" * 50)
    tp1 = calculate_take_profit(entry_price=0.40, estimated_prob=0.50, side='YES')
    if tp1:
        print(get_tp_summary(tp1))
        print(f"\n  Check: 10% edge × 50% / $0.40 = 12.5% move")
        print(f"  Target: $0.40 + ($0.40 × 12.5%) = $0.45")
    
    # Example 2: NO position with 15% edge
    print("\n\n2. NO Position: 15% edge (YES=$0.65, NO=$0.35)")
    print("-" * 50)
    tp2 = calculate_take_profit(entry_price=0.65, estimated_prob=0.50, side='NO')
    if tp2:
        print(get_tp_summary(tp2))
        print(f"\n  Entry NO price: $0.35")
        print(f"  Check: 15% edge × 50% / $0.35 = 21.4% move")
        print(f"  Target NO: $0.35 - ($0.35 × 21.4%) = $0.275")
        print(f"  Target YES: $1 - $0.275 = $0.725")
    
    # Example 3: Small edge (below threshold)
    print("\n\n3. Small Edge: 3% edge at $0.55 (below 5% threshold)")
    print("-" * 50)
    tp3 = calculate_take_profit(entry_price=0.55, estimated_prob=0.58, side='YES')
    if tp3:
        print(get_tp_summary(tp3))
    else:
        print("  Result: None (edge below 5% threshold)")
    
    # Example 4: Extreme price
    print("\n\n4. Extreme Price: $0.95 entry (above 0.90 threshold)")
    print("-" * 50)
    tp4 = calculate_take_profit(entry_price=0.95, estimated_prob=0.99, side='YES')
    if tp4:
        print(get_tp_summary(tp4))
    else:
        print("  Result: None (extreme price, skip TP)")
    
    # Example 5: Check TP hit
    print("\n\n5. Check TP Hit: Entry $0.40, Target $0.45")
    print("-" * 50)
    tp5 = calculate_take_profit(entry_price=0.40, estimated_prob=0.50, side='YES')
    if tp5:
        print(f"  Current $0.43: {'Hit' if check_take_profit_hit(0.40, 0.43, tp5, 'YES') else 'Not hit'}")
        print(f"  Current $0.45: {'Hit' if check_take_profit_hit(0.40, 0.45, tp5, 'YES') else 'Not hit'}")
        print(f"  Current $0.46: {'Hit' if check_take_profit_hit(0.40, 0.46, tp5, 'YES') else 'Not hit'}")
    
    # Example 6: Calculate holding days
    print("\n\n6. Calculate Holding Days")
    print("-" * 50)
    days = calculate_holding_days('2024-01-01T10:00:00', '2024-01-05T14:30:00')
    print(f"  Jan 1 to Jan 5: {days} days")
    
    days2 = calculate_holding_days('2024-06-15T08:00:00', '2024-06-20T16:45:00')
    print(f"  Jun 15 to Jun 20: {days2} days")
    
    print("\n" + "=" * 70)
    print("✅ All examples complete!")
    print("=" * 70)
