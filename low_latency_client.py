#!/usr/bin/env python3
"""
Low-Latency Trading Client
Implements async/await and connection pooling for reduced latency
Timestamp: 2026-02-03 19:05 GMT+1
"""

import asyncio
import aiohttp
import time
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd

GAMMA_API = "https://gamma-api.polymarket.com"


class LowLatencyClient:
    """
    Optimized client for low-latency trading.
    
    Features:
    - Connection pooling (keep-alive)
    - Async/concurrent requests
    - Connection reuse
    - Reduced overhead
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.latency_stats = []
    
    async def __aenter__(self):
        """Async context manager entry"""
        # Create session with connection pooling
        connector = aiohttp.TCPConnector(
            limit=100,           # Max concurrent connections
            limit_per_host=10,   # Max per host
            ttl_dns_cache=300,   # DNS cache TTL
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=30)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'Accept': 'application/json',
                'User-Agent': 'LowLatency-Client/1.0',
                'Connection': 'keep-alive'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def fetch_markets(self, limit: int = 100) -> List[Dict]:
        """Fetch markets with low latency"""
        url = f"{GAMMA_API}/events"
        params = {
            'active': 'true',
            'closed': 'false',
            'limit': limit,
            'order': 'volume'
        }
        
        start = time.time()
        
        async with self.session.get(url, params=params) as response:
            data = await response.json()
            
            elapsed = (time.time() - start) * 1000
            self.latency_stats.append(elapsed)
            
            # Parse markets
            markets = []
            for event in data:
                for market in event.get('markets', []):
                    markets.append({
                        'slug': market.get('slug'),
                        'question': market.get('question'),
                        'price': market.get('outcomePrices'),
                        'timestamp': datetime.now()
                    })
            
            return markets
    
    async def fetch_multiple_batches(self, num_batches: int = 5) -> List[List[Dict]]:
        """Fetch multiple batches concurrently"""
        tasks = [self.fetch_markets(limit=100) for _ in range(num_batches)]
        results = await asyncio.gather(*tasks)
        return results
    
    def get_latency_stats(self) -> Dict:
        """Get latency statistics"""
        if not self.latency_stats:
            return {}
        
        import statistics
        return {
            'count': len(self.latency_stats),
            'min': min(self.latency_stats),
            'max': max(self.latency_stats),
            'mean': statistics.mean(self.latency_stats),
            'median': statistics.median(self.latency_stats)
        }


async def benchmark_async():
    """Benchmark async client vs sync"""
    print("=" * 70)
    print("⚡ LOW-LATENCY CLIENT BENCHMARK")
    print("=" * 70)
    
    # Test async client
    print("\n1. Testing Async Client (with connection pooling)...")
    async with LowLatencyClient() as client:
        # Warmup
        await client.fetch_markets(limit=10)
        client.latency_stats = []  # Reset after warmup
        
        # Fetch 5 batches concurrently
        start = time.time()
        results = await client.fetch_multiple_batches(num_batches=5)
        elapsed = (time.time() - start) * 1000
        
        stats = client.get_latency_stats()
        
        print(f"   Concurrent requests: 5")
        print(f"   Total time: {elapsed:.1f}ms")
        print(f"   Avg per request: {stats['mean']:.1f}ms")
        print(f"   Markets fetched: {sum(len(r) for r in results)}")
    
    # Compare with sync
    print("\n2. Testing Sync Client (requests library)...")
    import requests
    
    session = requests.Session()
    session.headers.update({
        'Accept': 'application/json',
        'User-Agent': 'Sync-Benchmark/1.0'
    })
    
    sync_latencies = []
    start = time.time()
    
    for i in range(5):
        req_start = time.time()
        response = session.get(
            f"{GAMMA_API}/events",
            params={'active': 'true', 'limit': 100, 'order': 'volume'},
            timeout=30
        )
        req_elapsed = (time.time() - req_start) * 1000
        sync_latencies.append(req_elapsed)
    
    total_sync = (time.time() - start) * 1000
    
    import statistics
    print(f"   Sequential requests: 5")
    print(f"   Total time: {total_sync:.1f}ms")
    print(f"   Avg per request: {statistics.mean(sync_latencies):.1f}ms")
    
    # Compare
    print("\n" + "=" * 70)
    print("📊 COMPARISON:")
    print("=" * 70)
    improvement = (total_sync - elapsed) / total_sync * 100
    print(f"  Sync (sequential):   {total_sync:>8.1f}ms")
    print(f"  Async (concurrent):  {elapsed:>8.1f}ms")
    print(f"  Improvement:         {improvement:>7.1f}%")
    
    if improvement > 20:
        print("\n✅ Significant latency improvement with async!")
    
    print("=" * 70)


def main():
    """Run benchmark"""
    asyncio.run(benchmark_async())


if __name__ == '__main__':
    main()
