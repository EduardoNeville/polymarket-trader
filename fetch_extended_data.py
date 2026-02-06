#!/usr/bin/env python3
"""
Fetch extended dataset with price history for backtesting.
Target: 200+ markets with full price history
"""

import json
import time
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from utils.market_data import fetch_resolved_backtest_data


def main():
    print("=" * 80)
    print("🔍 FETCHING EXTENDED DATASET WITH PRICE HISTORY")
    print("=" * 80)
    print(f"\nTarget: 200+ markets with full price history")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    all_points = []
    total_stats = {
        'markets_seen': 0,
        'markets_used': 0,
        'markets_skipped': 0,
        'price_history_calls': 0
    }
    
    # Fetch in multiple batches to avoid timeouts
    batches = [
        {'limit': 200, 'offset': 0},
        {'limit': 200, 'offset': 200},
        {'limit': 200, 'offset': 400},
        {'limit': 200, 'offset': 600},
    ]
    
    for i, batch in enumerate(batches, 1):
        print(f"\n📦 Batch {i}/{len(batches)}: Fetching {batch['limit']} markets (offset {batch['offset']})...")
        
        try:
            points, stats = fetch_resolved_backtest_data(
                limit=batch['limit'],
                pause_seconds=0.2
            )
            
            all_points.extend(points)
            total_stats['markets_seen'] += stats.markets_seen
            total_stats['markets_used'] += stats.markets_used
            total_stats['markets_skipped'] += stats.markets_skipped
            total_stats['price_history_calls'] += stats.price_history_calls
            
            print(f"   ✓ Got {len(points)} data points from {stats.markets_used} markets")
            
            # Stop if we have enough
            unique_markets = len(set(p['market_slug'] for p in all_points))
            if unique_markets >= 200:
                print(f"\n✅ Reached target of 200+ markets!")
                break
                
        except Exception as e:
            print(f"   ✗ Error in batch {i}: {e}")
            continue
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 FETCH SUMMARY")
    print("=" * 80)
    print(f"Total markets seen: {total_stats['markets_seen']}")
    print(f"Total markets used: {total_stats['markets_used']}")
    print(f"Total markets skipped: {total_stats['markets_skipped']}")
    print(f"Total price history calls: {total_stats['price_history_calls']}")
    print(f"Total data points: {len(all_points)}")
    
    unique_markets = len(set(p['market_slug'] for p in all_points))
    print(f"Unique markets with price history: {unique_markets}")
    
    # Save to file
    if all_points:
        output_file = 'data/extended_resolved_markets.json'
        print(f"\n💾 Saving to {output_file}...")
        
        with open(output_file, 'w') as f:
            json.dump(all_points, f, indent=2)
        
        file_size = Path(output_file).stat().st_size / (1024 * 1024)
        print(f"✅ Saved {len(all_points)} records ({file_size:.1f} MB)")
        print(f"   {unique_markets} unique markets")
    
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == '__main__':
    main()
