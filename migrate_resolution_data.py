#!/usr/bin/env python3
"""
Migration: Add resolution time data to existing trades
Populates resolution_date, days_to_resolve, and priority_score for existing trades
"""

import sys
from datetime import datetime, timezone
sys.path.insert(0, '/home/eduardoneville/projects/polymarket-trader')

from utils.paper_trading_db import PaperTradingDB
from scanner import PolymarketScanner, Market


def calculate_time_to_resolution(end_date: str) -> float:
    """Calculate days until market resolution"""
    if not end_date:
        return None
    
    try:
        # Parse ISO 8601 datetime
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = end - now
        return max(0, delta.days + delta.seconds / 86400)
    except (ValueError, TypeError):
        return None


def get_resolution_priority(days_to_resolve: float, edge: float) -> float:
    """Calculate priority score balancing time and edge"""
    if days_to_resolve is None:
        return edge
    
    # Time bonus: +50% for <7 days, +25% for <30 days, +10% for <90 days
    if days_to_resolve < 7:
        time_multiplier = 1.5
    elif days_to_resolve < 30:
        time_multiplier = 1.25
    elif days_to_resolve < 90:
        time_multiplier = 1.1
    else:
        time_multiplier = 1.0
    
    return edge * time_multiplier


def main():
    print("=" * 80)
    print("📊 MIGRATION: Adding Resolution Time Data to Existing Trades")
    print("=" * 80)
    
    db = PaperTradingDB()
    scanner = PolymarketScanner()
    
    # Get open trades
    open_trades = db.get_open_trades()
    print(f"\nFound {len(open_trades)} open trades to update\n")
    
    # Fetch all active markets to get end dates
    print("Fetching market data from Polymarket...")
    markets = scanner.get_active_markets(limit=300)
    market_map = {m.slug: m for m in markets}
    print(f"Fetched {len(markets)} markets\n")
    
    # Update each trade
    updated = 0
    skipped = 0
    failed = 0
    
    for trade in open_trades:
        trade_id = trade.get('id')
        slug = trade.get('market_slug')
        question = trade.get('market_question', 'Unknown')[:50]
        
        if not slug:
            print(f"⚠️  Skipping trade {trade_id}: No market slug")
            skipped += 1
            continue
        
        # Check if market is still active
        if slug in market_map:
            market = market_map[slug]
            end_date = market.end_date
            
            if end_date:
                days = calculate_time_to_resolution(end_date)
                edge = trade.get('edge', 0)
                priority = get_resolution_priority(days, abs(edge)) if days else None
                
                # Update the trade
                success = db.update_resolution_data(
                    trade_id=trade_id,
                    resolution_date=end_date,
                    days_to_resolve=days,
                    priority_score=priority
                )
                
                if success:
                    time_str = f"{days:.0f} days" if days and days < 365 else f"{days/365:.1f} years" if days else "Unknown"
                    print(f"✅ Updated: {question}... | Resolves: {time_str}")
                    updated += 1
                else:
                    print(f"❌ Failed to update: {slug}")
                    failed += 1
            else:
                print(f"⚠️  No end date: {question}...")
                skipped += 1
        else:
            # Market not found in active markets - may have resolved
            print(f"⚠️  Market not found (may be resolved/archived): {question}...")
            skipped += 1
    
    print("\n" + "=" * 80)
    print(f"📊 MIGRATION COMPLETE")
    print(f"   Updated: {updated} trades")
    print(f"   Skipped: {skipped} trades")
    print(f"   Failed:  {failed} trades")
    print("=" * 80)
    
    # Show summary by time bucket
    print("\n📈 Resolution Time Distribution:")
    trades = db.get_open_trades()
    short_term = sum(1 for t in trades if t.get('days_to_resolve', 999) < 30)
    medium_term = sum(1 for t in trades if 30 <= t.get('days_to_resolve', 0) < 90)
    long_term = sum(1 for t in trades if t.get('days_to_resolve', 0) >= 90)
    unknown = len(trades) - short_term - medium_term - long_term
    
    print(f"   < 30 days:  {short_term} trades")
    print(f"   30-90 days: {medium_term} trades")
    print(f"   90+ days:   {long_term} trades")
    print(f"   Unknown:    {unknown} trades")


if __name__ == "__main__":
    main()
