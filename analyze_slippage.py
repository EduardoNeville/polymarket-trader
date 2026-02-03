#!/usr/bin/env python3
"""
Slippage Analysis and Adverse Selection Monitor
Analyzes bid-ask spreads and estimates real-world execution costs
Timestamp: 2026-02-03 19:22 GMT+1
"""

import requests
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import statistics

GAMMA_API = "https://gamma-api.polymarket.com"


class SlippageAnalyzer:
    """
    Analyzes market conditions to estimate slippage and adverse selection.
    
    Key metrics:
    - Bid-ask spread (cost of immediate execution)
    - Market depth (price impact of orders)
    - Volatility (how fast prices move)
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Slippage-Analyzer/1.0'
        })
        self.data_dir = Path('data/slippage_analysis')
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def fetch_market_orderbook(self, market_slug: str) -> Dict:
        """
        Fetch order book data for a market.
        Note: Polymarket CLOB API may require authentication.
        """
        # For now, we'll use the spread data from the markets endpoint
        url = f"{GAMMA_API}/markets"
        params = {'slug': market_slug}
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            data = response.json()
            
            if data and len(data) > 0:
                market = data[0]
                return {
                    'spread': market.get('spread', 0),
                    'best_bid': market.get('bestBid', 0),
                    'best_ask': market.get('bestAsk', 0),
                    'liquidity': market.get('liquidity', 0),
                    'volume': market.get('volume', 0),
                    'one_day_change': market.get('oneDayPriceChange', 0)
                }
        except Exception as e:
            print(f"Error fetching {market_slug}: {e}")
        
        return {}
    
    def analyze_active_markets(self, limit: int = 50) -> Dict:
        """Analyze slippage conditions across active markets"""
        url = f"{GAMMA_API}/events"
        params = {
            'active': 'true',
            'closed': 'false',
            'limit': limit,
            'order': 'volume'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            events = response.json()
        except Exception as e:
            print(f"Error fetching events: {e}")
            return {}
        
        spreads = []
        liquidities = []
        volumes = []
        
        for event in events:
            for market in event.get('markets', []):
                spread = market.get('spread', 0)
                liquidity = float(market.get('liquidity', 0) or 0)
                volume = float(market.get('volume', 0) or 0)
                
                if spread > 0:
                    spreads.append(spread)
                if liquidity > 0:
                    liquidities.append(liquidity)
                if volume > 0:
                    volumes.append(volume)
        
        if not spreads:
            return {}
        
        return {
            'spreads': {
                'mean': statistics.mean(spreads),
                'median': statistics.median(spreads),
                'min': min(spreads),
                'max': max(spreads),
                'count': len(spreads)
            },
            'liquidity': {
                'mean': statistics.mean(liquidities) if liquidities else 0,
                'median': statistics.median(liquidities) if liquidities else 0,
            },
            'volume': {
                'mean': statistics.mean(volumes) if volumes else 0,
                'median': statistics.median(volumes) if volumes else 0,
            }
        }
    
    def estimate_slippage(self, position_size: float, market_liquidity: float) -> float:
        """
        Estimate slippage based on position size and market liquidity.
        
        Simplified model: slippage increases with position size relative to liquidity
        """
        if market_liquidity <= 0:
            return 0.01  # Default 1% slippage for unknown liquidity
        
        # Basic market impact model
        # Slippage = 0.5 * (position_size / liquidity) ^ 0.6
        ratio = position_size / market_liquidity
        slippage = 0.5 * (ratio ** 0.6)
        
        # Cap at 5% (very high slippage)
        return min(slippage, 0.05)
    
    def generate_report(self) -> str:
        """Generate slippage analysis report"""
        print("=" * 70)
        print("📊 SLIPPAGE AND ADVERSE SELECTION ANALYSIS")
        print("=" * 70)
        
        # Analyze markets
        print("\n🔍 Analyzing active markets...")
        analysis = self.analyze_active_markets(limit=100)
        
        if not analysis:
            return "Could not fetch market data"
        
        spreads = analysis['spreads']
        liquidity = analysis['liquidity']
        
        print(f"\n📈 BID-ASK SPREADS (n={spreads['count']}):")
        print(f"  Mean:   {spreads['mean']:.3f} ({spreads['mean']*100:.1f}%)")
        print(f"  Median: {spreads['median']:.3f} ({spreads['median']*100:.1f}%)")
        print(f"  Min:    {spreads['min']:.3f} ({spreads['min']*100:.1f}%)")
        print(f"  Max:    {spreads['max']:.3f} ({spreads['max']*100:.1f}%)")
        
        print(f"\n💰 MARKET LIQUIDITY:")
        print(f"  Mean:   ${liquidity['mean']:,.0f}")
        print(f"  Median: ${liquidity['median']:,.0f}")
        
        # Estimate slippage for different position sizes
        print(f"\n📉 ESTIMATED SLIPPAGE BY POSITION SIZE:")
        print(f"  {'Position':<15} {'Liquidity':<15} {'Slippage':<12} {'Cost on $100':<15}")
        print("-" * 70)
        
        test_liquidities = [10000, 50000, 100000, 500000]
        position_sizes = [100, 500, 1000, 5000]
        
        for liq in test_liquidities:
            for pos in position_sizes:
                if pos <= liq * 0.1:  # Only show if position < 10% of liquidity
                    slip = self.estimate_slippage(pos, liq)
                    cost = slip * 100  # Cost on $100 trade
                    print(f"  ${pos:<14,.0f} ${liq:<14,.0f} {slip*100:<11.2f}% ${cost:<14.2f}")
        
        # Adverse selection analysis
        print(f"\n⚠️ ADVERSE SELECTION ANALYSIS:")
        print(f"  Bid-ask spread (median): {spreads['median']*100:.2f}%")
        print(f"  This is your 'cost of immediacy'")
        
        if spreads['median'] < 0.02:  # < 2% spread
            print(f"  ✅ Low spreads - good for execution")
        elif spreads['median'] < 0.05:  # 2-5% spread
            print(f"  ⚠️  Moderate spreads - factor into edge calculations")
        else:
            print(f"  ❌ High spreads - execution will be costly")
        
        # Key recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        
        avg_liquidity = liquidity['median']
        max_position = avg_liquidity * 0.02  # 2% of median liquidity
        
        print(f"  1. Max position size: ${max_position:,.0f} (2% of median liquidity)")
        print(f"  2. Minimum edge needed: {spreads['median']*100 + 2:.1f}%")
        print(f"     (spread + 2% profit margin)")
        print(f"  3. Avoid markets with <${avg_liquidity/10:,.0f} liquidity")
        
        print("=" * 70)
        
        return f"Analysis complete. Median spread: {spreads['median']*100:.2f}%"


def main():
    analyzer = SlippageAnalyzer()
    analyzer.generate_report()


if __name__ == '__main__':
    main()
