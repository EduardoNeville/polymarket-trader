#!/usr/bin/env python3
"""
Fetch additional resolved market data from Polymarket API
Timestamp: 2026-02-03 18:20 GMT+1
"""

import requests
import json
from datetime import datetime
from pathlib import Path

def fetch_resolved_markets(limit=500, offset=0):
    """Fetch resolved/closed markets from Polymarket"""
    base_url = 'https://gamma-api.polymarket.com'
    
    # Get closed markets
    url = f'{base_url}/markets'
    params = {
        'closed': 'true',
        'archived': 'false',
        'limit': limit,
        'offset': offset,
        'order': 'closedTime',
        'ascending': 'false'
    }
    
    print(f'Fetching markets (offset={offset}, limit={limit})...')
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    
    return response.json()

def process_market(market):
    """Extract relevant data from a market"""
    # Parse outcome prices
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
    
    # Determine outcome from prices
    # If YES price is 1.0 (or close), YES won
    # If NO price is 1.0 (or close), NO won
    if yes_price >= 0.99:
        outcome = 1  # YES won
    elif no_price >= 0.99:
        outcome = 0  # NO won
    else:
        outcome = None  # Unclear
    
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
    print('🔍 FETCHING ADDITIONAL RESOLVED MARKETS')
    print('=' * 70)
    
    all_data = []
    
    # Fetch in batches
    batch_size = 100
    total_fetched = 0
    
    for offset in range(0, 500, batch_size):
        try:
            markets = fetch_resolved_markets(limit=batch_size, offset=offset)
            
            if not markets:
                print(f'No more markets at offset {offset}')
                break
            
            # Process each market
            for market in markets:
                record = process_market(market)
                # Only include if we have a valid outcome
                if record['outcome'] is not None:
                    all_data.append(record)
            
            total_fetched += len(markets)
            resolved_count = len([r for r in all_data if r['outcome'] is not None])
            print(f'  Offset {offset}: Got {len(markets)} markets, {resolved_count} resolved')
            
        except Exception as e:
            print(f'Error at offset {offset}: {e}')
            break
    
    print(f'\n✅ Fetched {total_fetched} total markets')
    print(f'✅ {len(all_data)} have clear outcomes')
    
    # Save to file
    output_file = 'data/additional_resolved_markets.json'
    print(f'\n💾 Saving to {output_file}...')
    
    with open(output_file, 'w') as f:
        json.dump(all_data, f, indent=2)
    
    print(f'✅ Saved {len(all_data)} records')
    
    # Show breakdown
    yes_count = sum(1 for r in all_data if r['outcome'] == 1)
    no_count = sum(1 for r in all_data if r['outcome'] == 0)
    
    print(f'\n📊 Outcomes:')
    print(f'  YES: {yes_count}')
    print(f'  NO: {no_count}')
    
    print('\n✅ Done!')

if __name__ == '__main__':
    main()
