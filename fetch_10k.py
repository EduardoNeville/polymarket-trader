#!/usr/bin/env python3
"""
Quick fetch of ~10,000 resolved markets
Timestamp: 2026-02-03 18:45 GMT+1
"""

import requests
import json
from datetime import datetime

def main():
    print('=' * 70)
    print('🔍 QUICK FETCH - TARGET: 10,000 RESOLVED MARKETS')
    print('=' * 70)
    
    all_data = []
    batch_size = 500
    
    # We need ~10,100 fetches to get ~10,000 resolved (99% resolve rate)
    offsets = list(range(0, 10500, batch_size))
    
    print(f'Fetching {len(offsets)} batches of {batch_size}...\n')
    
    for i, offset in enumerate(offsets):
        try:
            url = 'https://gamma-api.polymarket.com/markets'
            params = {
                'closed': 'true',
                'archived': 'false',
                'limit': batch_size,
                'offset': offset,
                'order': 'closedTime',
                'ascending': 'false'
            }
            
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            markets = response.json()
            
            if not markets:
                print(f'  Batch {i+1}/{len(offsets)}: No more data')
                break
            
            # Process resolved markets
            batch_resolved = 0
            for m in markets:
                prices_str = m.get('outcomePrices', '[]')
                try:
                    prices = json.loads(prices_str)
                    if len(prices) >= 2:
                        yes_price = float(prices[0]) if prices[0] else 0.0
                        no_price = float(prices[1]) if prices[1] else 0.0
                        
                        if yes_price >= 0.99:
                            outcome = 1
                        elif no_price >= 0.99:
                            outcome = 0
                        else:
                            continue
                        
                        all_data.append({
                            'timestamp': m.get('updatedAt', datetime.now().isoformat()),
                            'market_slug': m.get('slug', ''),
                            'question': m.get('question', ''),
                            'price': yes_price,
                            'outcome': outcome,
                            'category': 'general'
                        })
                        batch_resolved += 1
                except:
                    continue
            
            total = len(all_data)
            print(f'  Batch {i+1:2d}/{len(offsets)}: +{batch_resolved:3d} resolved | Total: {total:5d}')
            
            # Stop if we have enough
            if total >= 10000:
                print(f'\n✅ Reached 10,000 markets!')
                break
                
        except Exception as e:
            print(f'  Batch {i+1}: Error - {e}')
            continue
    
    print(f'\n✅ Fetch complete: {len(all_data)} resolved markets')
    
    # Save
    print('\n💾 Saving to data/large_resolved_markets.json...')
    with open('data/large_resolved_markets.json', 'w') as f:
        json.dump(all_data, f, indent=2)
    
    # Stats
    yes = sum(1 for r in all_data if r['outcome'] == 1)
    no = sum(1 for r in all_data if r['outcome'] == 0)
    print(f'✅ Saved! YES: {yes}, NO: {no}')

if __name__ == '__main__':
    main()
