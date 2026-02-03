#!/usr/bin/env python3
"""
Fetch large dataset of resolved markets from Polymarket API
Target: 10,000 markets
Timestamp: 2026-02-03 18:31 GMT+1
"""

import requests
import json
from datetime import datetime
from pathlib import Path
import time

def fetch_resolved_markets_batch(offset=0, limit=100):
    """Fetch a batch of resolved markets"""
    base_url = 'https://gamma-api.polymarket.com'
    
    url = f'{base_url}/markets'
    params = {
        'closed': 'true',
        'archived': 'false',
        'limit': limit,
        'offset': offset,
        'order': 'closedTime',
        'ascending': 'false'
    }
    
    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f'Error at offset {offset}: {e}')
        return None

def process_market(market):
    """Extract relevant data from a market"""
    outcome_prices_str = market.get('outcomePrices', '[]')
    try:
        outcome_prices = json.loads(outcome_prices_str)
        if len(outcome_prices) >= 2:
            yes_price = float(outcome_prices[0]) if outcome_prices[0] else 0.0
            no_price = float(outcome_prices[1]) if outcome_prices[1] else 0.0
        else:
            yes_price = 0.0
            no_price = 0.0
    except (json.JSONDecodeError, ValueError):
        yes_price = 0.0
        no_price = 0.0
    
    # Determine outcome
    if yes_price >= 0.99:
        outcome = 1
    elif no_price >= 0.99:
        outcome = 0
    else:
        outcome = None
    
    return {
        'timestamp': market.get('updatedAt', datetime.now().isoformat()),
        'market_slug': market.get('slug', ''),
        'question': market.get('question', ''),
        'price': yes_price,
        'outcome': outcome,
        'category': 'general'
    }

def main():
    print('=' * 70)
    print('🔍 FETCHING LARGE DATASET - TARGET: 10,000 MARKETS')
    print('=' * 70)
    
    all_data = []
    batch_size = 100
    target_markets = 10000
    
    # Calculate how many batches we need
    # Each offset gives us ~80-90 resolved markets
    max_offset = 15000  # Fetch more to get 10K resolved
    
    for offset in range(0, max_offset, batch_size):
        try:
            markets = fetch_resolved_markets_batch(offset=offset, limit=batch_size)
            
            if markets is None:
                print(f'  Offset {offset}: API error, retrying...')
                time.sleep(2)
                markets = fetch_resolved_markets_batch(offset=offset, limit=batch_size)
            
            if not markets:
                print(f'  Offset {offset}: No more markets')
                break
            
            # Process markets
            resolved_count = 0
            for market in markets:
                record = process_market(market)
                if record['outcome'] is not None:
                    all_data.append(record)
                    resolved_count += 1
            
            total_resolved = len([r for r in all_data if r['outcome'] is not None])
            print(f'  Offset {offset:5d}: +{resolved_count:3d} resolved | Total: {total_resolved:5d}')
            
            # Check if we've reached target
            if total_resolved >= target_markets:
                print(f'\n✅ Reached target of {target_markets} resolved markets!')
                break
            
            # Rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            print(f'  Offset {offset}: Error - {e}')
            time.sleep(2)
            continue
    
    print(f'\n✅ Fetch complete!')
    print(f'   Total markets fetched: {len(all_data)}')
    
    # Show breakdown
    yes_count = sum(1 for r in all_data if r['outcome'] == 1)
    no_count = sum(1 for r in all_data if r['outcome'] == 0)
    
    print(f'\n📊 Outcomes:')
    print(f'   YES: {yes_count}')
    print(f'   NO:  {no_count}')
    
    # Save to file
    output_file = 'data/large_resolved_markets.json'
    print(f'\n💾 Saving to {output_file}...')
    
    with open(output_file, 'w') as f:
        json.dump(all_data, f, indent=2)
    
    # Get file size
    file_size = Path(output_file).stat().st_size / (1024 * 1024)  # MB
    print(f'✅ Saved {len(all_data)} records ({file_size:.1f} MB)')

if __name__ == '__main__':
    main()
