#!/usr/bin/env python3
"""
Polymarket Market Scanner
Finds trading opportunities across active markets
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

GAMMA_API = "https://gamma-api.polymarket.com"

@dataclass
class Market:
    id: str
    question: str
    slug: str
    yes_price: float
    no_price: float
    volume: float
    liquidity: float
    end_date: str
    category: str
    description: str
    resolution_source: str

class PolymarketScanner:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Polymarket-Trader-Bot/1.0'
        })
    
    def get_active_markets(self, limit: int = 100) -> List[Market]:
        """Fetch all active markets"""
        url = f"{GAMMA_API}/markets"
        params = {
            'closed': 'false',
            'limit': limit,
            'order': 'volume',
            'ascending': 'false'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            markets = []
            for item in data:
                try:
                    prices = json.loads(item.get('outcomePrices', '{}'))
                    market = Market(
                        id=item.get('conditionId', ''),
                        question=item.get('question', ''),
                        slug=item.get('slug', ''),
                        yes_price=float(prices.get('Yes', 0)),
                        no_price=float(prices.get('No', 0)),
                        volume=float(item.get('volume', 0)),
                        liquidity=float(item.get('liquidity', 0)),
                        end_date=item.get('endDate', ''),
                        category=item.get('category', ''),
                        description=item.get('description', '')[:200],
                        resolution_source=item.get('resolutionSource', '')
                    )
                    markets.append(market)
                except (KeyError, ValueError, json.JSONDecodeError) as e:
                    continue
            
            return markets
        except Exception as e:
            print(f"Error fetching markets: {e}")
            return []
    
    def get_markets_by_category(self, category: str, limit: int = 50) -> List[Market]:
        """Get markets filtered by category"""
        all_markets = self.get_active_markets(limit=200)
        return [m for m in all_markets if category.lower() in m.category.lower()]
    
    def find_arbitrage_opportunities(self) -> List[Dict]:
        """Find markets where Yes + No prices don't sum to ~1.0"""
        markets = self.get_active_markets(limit=100)
        opportunities = []
        
        for market in markets:
            total = market.yes_price + market.no_price
            spread = abs(1.0 - total)
            
            if spread > 0.02:  # 2% arbitrage threshold
                opportunities.append({
                    'question': market.question,
                    'slug': market.slug,
                    'yes_price': market.yes_price,
                    'no_price': market.no_price,
                    'total': total,
                    'spread': spread,
                    'potential_profit': spread * 100,
                    'action': 'Buy both YES and NO' if total < 1.0 else 'Avoid - premium'
                })
        
        return sorted(opportunities, key=lambda x: x['spread'], reverse=True)
    
    def find_momentum_markets(self, min_volume: float = 100000) -> List[Dict]:
        """Find high-volume markets with significant price movement"""
        markets = self.get_active_markets(limit=100)
        momentum = []
        
        for market in markets:
            if market.volume >= min_volume:
                # Calculate implied probability
                yes_prob = market.yes_price
                
                momentum.append({
                    'question': market.question[:80],
                    'slug': market.slug,
                    'yes_price': yes_prob,
                    'volume': market.volume,
                    'liquidity': market.liquidity,
                    'end_date': market.end_date,
                    'category': market.category
                })
        
        return sorted(momentum, key=lambda x: x['volume'], reverse=True)
    
    def find_value_opportunities(self, min_edge: float = 0.1) -> List[Dict]:
        """Find markets where you might have an edge"""
        markets = self.get_active_markets(limit=100)
        opportunities = []
        
        for market in markets:
            # Skip markets with low liquidity
            if market.liquidity < 10000:
                continue
            
            # Calculate edge potential
            yes_prob = market.yes_price
            
            # High-confidence opportunities (extreme prices)
            if yes_prob < 0.15 or yes_prob > 0.85:
                edge_type = "High confidence longshot" if yes_prob < 0.15 else "High confidence favorite"
                opportunities.append({
                    'question': market.question[:80],
                    'slug': market.slug,
                    'price': yes_prob,
                    'type': edge_type,
                    'potential_return': (1 - yes_prob) / yes_prob if yes_prob > 0 else 0,
                    'liquidity': market.liquidity,
                    'analysis': 'Consider if market is over/under-priced'
                })
        
        return opportunities
    
    def get_markets_closing_soon(self, days: int = 7) -> List[Dict]:
        """Find markets closing within specified days"""
        markets = self.get_active_markets(limit=200)
        closing = []
        cutoff = datetime.now() + timedelta(days=days)
        
        for market in markets:
            try:
                end = datetime.fromisoformat(market.end_date.replace('Z', '+00:00'))
                if end <= cutoff:
                    closing.append({
                        'question': market.question[:80],
                        'slug': market.slug,
                        'end_date': market.end_date,
                        'yes_price': market.yes_price,
                        'volume': market.volume,
                        'days_left': (end - datetime.now()).days
                    })
            except:
                continue
        
        return sorted(closing, key=lambda x: x.get('days_left', 999))


def main():
    scanner = PolymarketScanner()
    
    print("=" * 80)
    print("POLYMARKET MARKET SCANNER")
    print("=" * 80)
    print()
    
    # Arbitrage opportunities
    print("🔍 ARBITRAGE OPPORTUNITIES (Yes + No ≠ $1.00)")
    print("-" * 80)
    arb_opps = scanner.find_arbitrage_opportunities()
    if arb_opps:
        for opp in arb_opps[:5]:
            print(f"\n{opp['question'][:70]}")
            print(f"  YES: ${opp['yes_price']:.2f} | NO: ${opp['no_price']:.2f}")
            print(f"  Spread: {opp['spread']*100:.1f}% | Action: {opp['action']}")
    else:
        print("  No arbitrage opportunities found (efficient pricing)")
    print()
    
    # High volume markets
    print("📈 HIGH VOLUME MARKETS (Top 10)")
    print("-" * 80)
    high_vol = scanner.find_momentum_markets(min_volume=50000)
    for market in high_vol[:10]:
        print(f"  {market['question'][:60]:<60} | YES: ${market['yes_price']:.2f} | Vol: ${market['volume']:,.0f}")
    print()
    
    # Closing soon
    print("⏰ MARKETS CLOSING IN 7 DAYS")
    print("-" * 80)
    closing = scanner.get_markets_closing_soon(days=7)
    for market in closing[:10]:
        print(f"  {market['question'][:50]:<50} | {market['days_left']} days | YES: ${market['yes_price']:.2f}")
    print()
    
    # Value opportunities
    print("💎 POTENTIAL VALUE OPPORTUNITIES")
    print("-" * 80)
    value = scanner.find_value_opportunities()
    for opp in value[:5]:
        print(f"\n{opp['question'][:70]}")
        print(f"  Type: {opp['type']} | Price: ${opp['price']:.2f}")
        print(f"  Potential Return: {opp['potential_return']:.1f}x | Liquidity: ${opp['liquidity']:,.0f}")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
