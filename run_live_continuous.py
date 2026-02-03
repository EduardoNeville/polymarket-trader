#!/usr/bin/env python3
"""
Live Data Collector - Continuous Run
Polls Polymarket every 60 seconds and saves to Parquet
Timestamp: 2026-02-03 21:16 GMT+1
Runs continuously until stopped
"""

import sys
sys.path.insert(0, '/home/eduardoneville/projects/polymarket-trader')

from collect_live_data import LiveDataCollector

if __name__ == '__main__':
    print("="*70)
    print("🚀 STARTING LIVE DATA COLLECTOR (Continuous)")
    print("="*70)
    print("Poll interval: 60 seconds")
    print("Format: Parquet (daily rotation)")
    print("Output: data/live_markets/")
    print("="*70)
    
    collector = LiveDataCollector(poll_interval=60)
    
    try:
        collector.run()
    except KeyboardInterrupt:
        print("\n✅ Stopped by user")
        sys.exit(0)
