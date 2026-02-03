#!/usr/bin/env python3
"""
Polymarket Odds Calculator & Position Sizer
Calculate expected value, Kelly criterion, and optimal position sizes
"""

import math
from dataclasses import dataclass
from typing import Optional

@dataclass
class Position:
    market: str
    side: str  # 'YES' or 'NO'
    entry_price: float
    shares: float
    estimated_prob: float  # Your probability estimate

class OddsCalculator:
    """Calculate betting odds and optimal position sizes"""
    
    @staticmethod
    def calculate_expected_value(market_price: float, estimated_prob: float) -> float:
        """
        Calculate expected value of a bet
        
        Args:
            market_price: Current market price (0.0 to 1.0)
            estimated_prob: Your estimated probability of YES (0.0 to 1.0)
        
        Returns:
            Expected value per $1 bet
        """
        if market_price <= 0 or market_price >= 1:
            return 0.0
        
        # If buying YES
        if estimated_prob > market_price:
            # Win: (1 - market_price) * estimated_prob
            # Lose: -market_price * (1 - estimated_prob)
            ev = ((1 - market_price) * estimated_prob) - (market_price * (1 - estimated_prob))
        else:
            # Buy NO instead
            no_price = 1 - market_price
            no_prob = 1 - estimated_prob
            ev = ((1 - no_price) * no_prob) - (no_price * (1 - no_prob))
        
        return ev
    
    @staticmethod
    def calculate_kelly_criterion(
        bankroll: float,
        market_price: float,
        estimated_prob: float,
        fraction: float = 0.25
    ) -> dict:
        """
        Calculate Kelly Criterion optimal bet size
        
        Kelly Formula: f* = (bp - q) / b
        where:
        - b = odds received (decimal - 1)
        - p = probability of winning
        - q = probability of losing (1 - p)
        
        Args:
            bankroll: Total bankroll
            market_price: Current market price
            estimated_prob: Your estimated probability
            fraction: Kelly fraction (0.25 = quarter Kelly for safety)
        
        Returns:
            Dictionary with bet sizing recommendations
        """
        if market_price <= 0:
            return {'error': 'Invalid market price'}
        
        # Calculate odds
        if estimated_prob > market_price:
            # Bet YES
            side = 'YES'
            win_amount = 1 - market_price
            loss_amount = market_price
            b = win_amount / market_price  # Decimal odds
            p = estimated_prob
        else:
            # Bet NO
            side = 'NO'
            no_price = 1 - market_price
            win_amount = 1 - no_price
            loss_amount = no_price
            b = win_amount / no_price
            p = 1 - estimated_prob
        
        q = 1 - p
        
        # Kelly Criterion
        if b <= 0:
            kelly_fraction = 0
        else:
            kelly_fraction = (b * p - q) / b
        
        # Apply fractional Kelly for safety
        safe_kelly = kelly_fraction * fraction
        
        # Calculate position size
        kelly_bet = bankroll * kelly_fraction
        safe_bet = bankroll * safe_kelly
        
        # Calculate expected profit
        expected_profit = kelly_bet * ((b * p) - q) if kelly_bet > 0 else 0
        
        return {
            'side': side,
            'kelly_fraction': kelly_fraction,
            'safe_fraction': safe_kelly,
            'kelly_bet': kelly_bet,
            'safe_bet': safe_bet,
            'expected_profit': expected_profit,
            'confidence': 'High' if abs(estimated_prob - market_price) > 0.2 else 'Medium' if abs(estimated_prob - market_price) > 0.1 else 'Low'
        }
    
    @staticmethod
    def calculate_position_pnl(position: Position, current_price: float) -> dict:
        """Calculate P&L for an existing position"""
        if position.side == 'YES':
            pnl_per_share = current_price - position.entry_price
            pnl_percent = (pnl_per_share / position.entry_price) * 100 if position.entry_price > 0 else 0
        else:  # NO
            no_entry = 1 - position.entry_price
            no_current = 1 - current_price
            pnl_per_share = no_current - no_entry
            pnl_percent = (pnl_per_share / no_entry) * 100 if no_entry > 0 else 0
        
        total_pnl = pnl_per_share * position.shares
        total_value = position.shares * current_price if position.side == 'YES' else position.shares * (1 - current_price)
        
        return {
            'market': position.market,
            'side': position.side,
            'shares': position.shares,
            'entry_price': position.entry_price,
            'current_price': current_price,
            'pnl_per_share': pnl_per_share,
            'pnl_percent': pnl_percent,
            'total_pnl': total_pnl,
            'current_value': total_value
        }
    
    @staticmethod
    def calculate_implied_probability(odds_american: int = None, odds_decimal: float = None) -> float:
        """Convert odds to implied probability"""
        if odds_decimal:
            return 1 / odds_decimal
        elif odds_american:
            if odds_american > 0:
                return 100 / (odds_american + 100)
            else:
                return abs(odds_american) / (abs(odds_american) + 100)
        return 0.0
    
    @staticmethod
    def find_correlation_arbitrage(market1: dict, market2: dict) -> Optional[dict]:
        """
        Find arbitrage between correlated markets
        
        Example: 
        - Market A: "Team wins championship" = $0.40
        - Market B: "Team makes finals" = $0.35
        - Can't win championship without making finals
        - So Market A should be <= Market B
        """
        price1 = market1.get('yes_price', 0)
        price2 = market2.get('yes_price', 0)
        
        # If market2 implies market1 (must happen first)
        if price2 < price1:
            spread = price1 - price2
            return {
                'market1': market1.get('question', ''),
                'market2': market2.get('question', ''),
                'price1': price1,
                'price2': price2,
                'spread': spread,
                'arb_profit': spread * 100,
                'action': f"Buy YES in {market2.get('question', '')[:30]}...",
                'reason': f"Can't happen in Market 1 without Market 2"
            }
        
        return None
    
    @staticmethod
    def calculate_portfolio_value(positions: list, current_prices: dict) -> dict:
        """Calculate total portfolio value and P&L"""
        total_value = 0
        total_cost = 0
        position_details = []
        
        for pos in positions:
            current = current_prices.get(pos.market, pos.entry_price)
            pnl_data = OddsCalculator.calculate_position_pnl(pos, current)
            
            position_details.append(pnl_data)
            total_value += pnl_data['current_value']
            total_cost += pos.shares * pos.entry_price
        
        total_pnl = total_value - total_cost
        pnl_percent = (total_pnl / total_cost) * 100 if total_cost > 0 else 0
        
        return {
            'positions': position_details,
            'total_value': total_value,
            'total_cost': total_cost,
            'total_pnl': total_pnl,
            'pnl_percent': pnl_percent,
            'position_count': len(positions)
        }


def interactive_calculator():
    """Interactive odds calculator"""
    print("=" * 80)
    print("POLYMARKET ODDS CALCULATOR & POSITION SIZER")
    print("=" * 80)
    print()
    
    calc = OddsCalculator()
    
    # Get inputs
    try:
        bankroll = float(input("Enter your bankroll ($): "))
        market_price = float(input("Enter current market YES price (0.00-1.00): "))
        estimated_prob = float(input("Enter your estimated YES probability (0.00-1.00): "))
        kelly_fraction = float(input("Enter Kelly fraction (0.25 = quarter Kelly, default): ") or 0.25)
    except ValueError:
        print("Invalid input. Please enter numeric values.")
        return
    
    print()
    print("-" * 80)
    
    # Calculate EV
    ev = calc.calculate_expected_value(market_price, estimated_prob)
    print(f"Expected Value: ${ev:.4f} per $1 bet")
    
    if ev <= 0:
        print("⚠️  Negative EV - Avoid this bet!")
        return
    
    # Calculate Kelly
    kelly = calc.calculate_kelly_criterion(bankroll, market_price, estimated_prob, kelly_fraction)
    
    print(f"\n📊 KELLY CRITERION ANALYSIS")
    print(f"  Recommended Side: {kelly['side']}")
    print(f"  Kelly Fraction: {kelly['kelly_fraction']*100:.2f}%")
    print(f"  Safe Fraction ({kelly_fraction*100:.0f}% Kelly): {kelly['safe_fraction']*100:.2f}%")
    print(f"\n💰 POSITION SIZING")
    print(f"  Full Kelly Bet: ${kelly['kelly_bet']:,.2f}")
    print(f"  Safe Kelly Bet: ${kelly['safe_bet']:,.2f}")
    print(f"  Expected Profit: ${kelly['expected_profit']:,.2f}")
    print(f"  Confidence: {kelly['confidence']}")
    
    # Show potential returns
    print(f"\n📈 POTENTIAL RETURNS")
    if kelly['side'] == 'YES':
        win_amount = (1 - market_price) * kelly['safe_bet'] / market_price
        lose_amount = kelly['safe_bet']
        print(f"  If YES wins: +${win_amount:,.2f} ({(win_amount/kelly['safe_bet'])*100:.0f}% return)")
        print(f"  If NO wins: -${lose_amount:,.2f} (100% loss)")
    else:
        no_price = 1 - market_price
        win_amount = (1 - no_price) * kelly['safe_bet'] / no_price
        lose_amount = kelly['safe_bet']
        print(f"  If NO wins: +${win_amount:,.2f} ({(win_amount/kelly['safe_bet'])*100:.0f}% return)")
        print(f"  If YES wins: -${lose_amount:,.2f} (100% loss)")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    interactive_calculator()
