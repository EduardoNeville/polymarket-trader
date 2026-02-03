#!/usr/bin/env python3
"""
Live Market Data Collector
Polls Polymarket API every minute and stores data in Parquet format
Timestamp: 2026-02-03 18:45 GMT+1
"""

import requests
import json
import time
import signal
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

GAMMA_API = "https://gamma-api.polymarket.com"
DATA_DIR = Path("data/live_markets")

class LiveDataCollector:
    """Continuously collect market data from Polymarket"""
    
    def __init__(self, poll_interval=60):
        self.poll_interval = poll_interval  # seconds
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Polymarket-Data-Collector/1.0'
        })
        self.running = True
        self.total_records = 0
        
        # Ensure data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Setup graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n{'='*70}")
        print(f"🛑 Received signal {signum}, shutting down gracefully...")
        print(f"📊 Total records collected: {self.total_records:,}")
        print(f"{'='*70}")
        self.running = False
    
    def fetch_active_markets(self):
        """Fetch all active markets from API"""
        url = f"{GAMMA_API}/events"
        params = {
            'active': 'true',
            'closed': 'false',
            'archived': 'false',
            'limit': 500,  # Max per request
            'order': 'volume',
            'ascending': 'false'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error fetching markets: {e}")
            return []
    
    def parse_market_data(self, events):
        """Extract market data from API response"""
        records = []
        timestamp = datetime.now()
        
        for event in events:
            event_markets = event.get('markets', [])
            for market in event_markets:
                try:
                    # Parse outcome prices
                    outcome_prices_str = market.get('outcomePrices', '[]')
                    outcome_prices = json.loads(outcome_prices_str)
                    
                    if len(outcome_prices) >= 2:
                        yes_price = float(outcome_prices[0]) if outcome_prices[0] else None
                        no_price = float(outcome_prices[1]) if outcome_prices[1] else None
                    else:
                        yes_price = None
                        no_price = None
                    
                    # Skip if no valid prices
                    if yes_price is None or yes_price == 0:
                        continue
                    
                    record = {
                        'timestamp': timestamp,
                        'market_slug': market.get('slug', ''),
                        'question': market.get('question', ''),
                        'yes_price': yes_price,
                        'no_price': no_price,
                        'volume': float(market.get('volume', 0) or 0),
                        'liquidity': float(market.get('liquidity', 0) or 0),
                        'end_date': market.get('endDate', ''),
                        'category': event.get('category', 'general'),
                        'event_title': event.get('title', '')
                    }
                    records.append(record)
                except (json.JSONDecodeError, ValueError) as e:
                    continue
        
        return records
    
    def save_to_parquet(self, records):
        """Save records to Parquet file (daily rotation)"""
        if not records:
            return 0
        
        # Create DataFrame
        df = pd.DataFrame(records)
        
        # Generate filename based on date
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = DATA_DIR / f"markets_{date_str}.parquet"
        
        try:
            if filename.exists():
                # Append to existing file
                existing_df = pd.read_parquet(filename)
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                combined_df.to_parquet(filename, index=False, compression='snappy')
            else:
                # Create new file
                df.to_parquet(filename, index=False, compression='snappy')
            
            return len(records)
        except Exception as e:
            print(f"❌ Error saving to Parquet: {e}")
            return 0
    
    def run(self):
        """Main loop - collect data continuously"""
        print('=' * 70)
        print('🚀 LIVE MARKET DATA COLLECTOR')
        print('=' * 70)
        print(f'📊 Polling interval: {self.poll_interval} seconds')
        print(f'💾 Data directory: {DATA_DIR}')
        print(f'📁 File format: Parquet (daily rotation)')
        print('=' * 70)
        print('Press Ctrl+C to stop\n')
        
        poll_count = 0
        
        while self.running:
            poll_count += 1
            start_time = time.time()
            
            # Fetch data
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Poll #{poll_count}: Fetching markets...", end=' ')
            events = self.fetch_active_markets()
            
            if events:
                # Parse and save
                records = self.parse_market_data(events)
                saved_count = self.save_to_parquet(records)
                self.total_records += saved_count
                
                elapsed = time.time() - start_time
                print(f"✓ Saved {saved_count:4d} records | Total: {self.total_records:6,} | {elapsed:.1f}s")
            else:
                print("✗ No data")
            
            # Sleep until next poll
            if self.running:
                sleep_time = max(0, self.poll_interval - (time.time() - start_time))
                time.sleep(sleep_time)
        
        print(f"\n{'='*70}")
        print('✅ Data collector stopped')
        print(f'📊 Total records collected: {self.total_records:,}')
        print(f"{'='*70}")


def main():
    collector = LiveDataCollector(poll_interval=60)
    collector.run()


if __name__ == '__main__':
    main()
