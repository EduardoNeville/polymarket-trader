#!/usr/bin/env python3
"""
Latency Analysis and Benchmarking Tool
Compares current system latency vs professional standards
Timestamp: 2026-02-03 19:02 GMT+1
"""

import requests
import time
import statistics
from datetime import datetime
import json

GAMMA_API = "https://gamma-api.polymarket.com"

class LatencyBenchmark:
    """Benchmark API latency"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Latency-Benchmark/1.0'
        })
    
    def measure_http_latency(self, iterations=10):
        """Measure HTTP request/response latency"""
        latencies = []
        
        url = f"{GAMMA_API}/events"
        params = {'active': 'true', 'limit': 10}
        
        print(f"Measuring HTTP latency ({iterations} iterations)...")
        
        for i in range(iterations):
            start = time.time()
            response = self.session.get(url, params=params, timeout=30)
            end = time.time()
            
            latency = (end - start) * 1000  # Convert to ms
            latencies.append(latency)
            
            print(f"  Request {i+1}: {latency:.1f}ms")
            
            # Small delay between requests
            time.sleep(0.1)
        
        return {
            'min': min(latencies),
            'max': max(latencies),
            'mean': statistics.mean(latencies),
            'median': statistics.median(latencies),
            'stdev': statistics.stdev(latencies) if len(latencies) > 1 else 0
        }
    
    def measure_processing_latency(self):
        """Measure Python processing overhead"""
        import random
        
        # Simulate processing 100 markets
        markets = [{'price': random.random()} for _ in range(100)]
        
        iterations = 1000
        times = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            # Simulate typical processing
            for m in markets:
                price = m['price']
                if price > 0.5:
                    signal = 'BUY'
                else:
                    signal = 'SELL'
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        return {
            'min': min(times),
            'max': max(times),
            'mean': statistics.mean(times),
            'median': statistics.median(times)
        }
    
    def compare_with_professional(self):
        """Compare current vs professional latency"""
        print("=" * 70)
        print("🔍 LATENCY ANALYSIS")
        print("=" * 70)
        
        # Measure HTTP latency
        http_stats = self.measure_http_latency(iterations=5)
        
        print(f"\n📊 HTTP Request Latency:")
        print(f"  Min:    {http_stats['min']:.1f}ms")
        print(f"  Max:    {http_stats['max']:.1f}ms")
        print(f"  Mean:   {http_stats['mean']:.1f}ms")
        print(f"  Median: {http_stats['median']:.1f}ms")
        print(f"  StdDev: {http_stats['stdev']:.1f}ms")
        
        # Measure processing
        proc_stats = self.measure_processing_latency()
        
        print(f"\n⚙️ Python Processing Latency (100 markets):")
        print(f"  Min:    {proc_stats['min']:.3f}ms")
        print(f"  Max:    {proc_stats['max']:.3f}ms")
        print(f"  Mean:   {proc_stats['mean']:.3f}ms")
        print(f"  Median: {proc_stats['median']:.3f}ms")
        
        # Total estimated latency
        total_min = http_stats['min'] + proc_stats['min']
        total_max = http_stats['max'] + proc_stats['max']
        total_mean = http_stats['mean'] + proc_stats['mean']
        
        print(f"\n⏱️ TOTAL SYSTEM LATENCY:")
        print(f"  Min:    {total_min:.1f}ms")
        print(f"  Max:    {total_max:.1f}ms")
        print(f"  Mean:   {total_mean:.1f}ms")
        
        # Compare with professional
        print(f"\n🏢 COMPARISON WITH PROFESSIONAL SETUPS:")
        print(f"  {'Your System':<20} {total_mean:>8.1f}ms")
        print(f"  {'HFT (C++/FPGA)':<20} {'<1':>8}ms")
        print(f"  {'Pro (C++/Rust)':<20} {'5-10':>8}ms")
        print(f"  {'Retail (Python)':<20} {'50-200':>8}ms")
        print(f"  {'Your Current':<20} {total_mean:>8.1f}ms")
        
        # Calculate improvement potential
        if total_mean > 50:
            improvement = (total_mean - 50) / total_mean * 100
            print(f"\n💡 POTENTIAL IMPROVEMENT:")
            print(f"  Target: <50ms (professional Python)")
            print(f"  Gap: {total_mean - 50:.1f}ms ({improvement:.0f}% slower)")
        
        print("=" * 70)
        
        return {
            'http': http_stats,
            'processing': proc_stats,
            'total_mean': total_mean
        }


def main():
    benchmark = LatencyBenchmark()
    results = benchmark.compare_with_professional()
    
    print("\n✅ Latency analysis complete!")
    print(f"\nCurrent latency: {results['total_mean']:.1f}ms")
    
    if results['total_mean'] > 100:
        print("⚠️  High latency detected - optimization recommended")
    elif results['total_mean'] > 50:
        print("⚡ Moderate latency - some optimization possible")
    else:
        print("✓ Good latency for retail trading")


if __name__ == '__main__':
    main()
