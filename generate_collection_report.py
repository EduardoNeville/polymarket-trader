#!/usr/bin/env python3
"""
Generate comprehensive report from multiple collection sessions
Timestamp: 2026-02-03 20:58 GMT+1
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def load_all_sessions():
    """Load all collection session files"""
    sessions_dir = Path('data/collection_sessions')
    sessions = []
    
    for session_file in sorted(sessions_dir.glob('*.json')):
        with open(session_file) as f:
            sessions.append(json.load(f))
    
    return sessions


def generate_comprehensive_report():
    """Generate report from all sessions"""
    sessions = load_all_sessions()
    
    print("="*80)
    print("📊 COMPREHENSIVE DATA COLLECTION REPORT")
    print("="*80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Sessions: {len(sessions)}")
    print("="*80)
    
    # Aggregate data across sessions
    total_signals = 0
    avg_slippages = []
    all_outcome_updates = []
    
    for session in sessions:
        for step in session:
            if step.get('step') == 'signals':
                total_signals += step.get('signals_count', 0)
            elif step.get('step') == 'slippage':
                avg_slippages.append(step.get('avg_slippage_pct', 0))
            elif step.get('step') == 'outcomes':
                all_outcome_updates.append(step.get('updated', 0))
    
    # Session summary
    print("\n📁 SESSION SUMMARY:")
    print(f"  Total Collection Sessions:  {len(sessions)}")
    print(f"  Total Signals Generated:    {total_signals}")
    print(f"  Avg Slippage (across all):  {sum(avg_slippages)/len(avg_slippages):.2f}%" if avg_slippages else "  No slippage data")
    print(f"  Total Outcomes Updated:     {sum(all_outcome_updates)}")
    
    # Load paper trading DB
    print("\n" + "="*80)
    print("📊 PAPER TRADING DATABASE STATUS")
    print("="*80)
    
    from utils.paper_trading_db import PaperTradingDB
    db = PaperTradingDB()
    
    open_trades = db.get_open_trades()
    closed_trades = db.get_closed_trades()
    summary = db.get_performance_summary()
    
    print(f"\n📈 TRADE STATISTICS:")
    print(f"  Open Trades:    {len(open_trades)}")
    print(f"  Closed Trades:  {len(closed_trades)}")
    print(f"  Total Tracked:  {len(open_trades) + len(closed_trades)}")
    
    # Side breakdown
    yes_open = sum(1 for t in open_trades if t['intended_side'] == 'YES')
    no_open = sum(1 for t in open_trades if t['intended_side'] == 'NO')
    
    print(f"\n📊 SIDE BREAKDOWN:")
    print(f"  YES Signals:  {yes_open} ({yes_open/len(open_trades)*100:.1f}%)" if open_trades else "  YES Signals: 0")
    print(f"  NO Signals:   {no_open} ({no_open/len(open_trades)*100:.1f}%)" if open_trades else "  NO Signals: 0")
    
    # Edge analysis
    if open_trades:
        edges = [t['edge'] for t in open_trades]
        print(f"\n📈 EDGE ANALYSIS:")
        print(f"  Average Edge:      {sum(edges)/len(edges):.1%}")
        print(f"  Min Edge:          {min(edges):.1%}")
        print(f"  Max Edge:          {max(edges):.1%}")
    
    # Performance (if any closed)
    if closed_trades:
        print(f"\n💰 PERFORMANCE (Closed Trades):")
        print(f"  Win Rate:          {summary['win_rate']:.1%}")
        print(f"  Total P&L:         ${summary['total_pnl']:+.2f}")
        print(f"  Avg per Trade:     ${summary['avg_pnl']:+.2f}")
    else:
        print(f"\n⏳ PERFORMANCE:")
        print(f"  No closed trades yet. Markets need to resolve.")
        print(f"  Check back in 1-7 days for outcomes.")
    
    # Slippage analysis
    print("\n" + "="*80)
    print("📉 SLIPPAGE ANALYSIS")
    print("="*80)
    
    # Collect slippage data from all sessions
    all_slippage_data = []
    for session in sessions:
        for step in session:
            if step.get('step') == 'slippage' and 'data' in step:
                all_slippage_data.extend(step['data'])
    
    if all_slippage_data:
        # Average by liquidity tier
        liquidity_tiers = defaultdict(list)
        for s in all_slippage_data:
            if s['liquidity'] < 25000:
                tier = 'Low (<$25K)'
            elif s['liquidity'] < 50000:
                tier = 'Medium ($25-50K)'
            elif s['liquidity'] < 100000:
                tier = 'High ($50-100K)'
            else:
                tier = 'Very High (>$100K)'
            liquidity_tiers[tier].append(s['slippage_pct'])
        
        print(f"\n📊 SLIPPAGE BY LIQUIDITY TIER:")
        for tier, slips in sorted(liquidity_tiers.items()):
            avg = sum(slips) / len(slips)
            print(f"  {tier:<20}: {avg:.2f}% (n={len(slips)})")
        
        # Overall
        all_slips = [s['slippage_pct'] for s in all_slippage_data]
        print(f"\n📈 OVERALL:")
        print(f"  Average Slippage:    {sum(all_slips)/len(all_slips):.2f}%")
        print(f"  Min Slippage:        {min(all_slips):.2f}%")
        print(f"  Max Slippage:        {max(all_slips):.2f}%")
        print(f"  Markets Analyzed:    {len(set(s['market_slug'] for s in all_slippage_data))}")
    
    # Recommendations
    print("\n" + "="*80)
    print("💡 RECOMMENDATIONS")
    print("="*80)
    
    if len(open_trades) >= 20:
        print(f"✅ Good signal generation: {len(open_trades)} trades tracked")
    else:
        print(f"⚠️  Consider generating more signals (currently {len(open_trades)})")
    
    if avg_slippages and sum(avg_slippages)/len(avg_slippages) < 2.0:
        print(f"✅ Slippage acceptable: ~{sum(avg_slippages)/len(avg_slippages):.1f}%")
    else:
        print(f"⚠️  High slippage detected: ~{sum(avg_slippages)/len(avg_slippages):.1f}%")
        print(f"   Focus on high-liquidity markets only")
    
    if len(closed_trades) < 10:
        print(f"⏳  Need more resolved trades for adverse selection analysis")
        print(f"    Current: {len(closed_trades)}, Need: 10+")
    
    print("\n" + "="*80)
    print("📋 NEXT STEPS")
    print("="*80)
    print("1. Continue running: python3 run_full_collection.py")
    print("2. Daily for 3-7 days to accumulate data")
    print("3. Wait for markets to resolve")
    print("4. Run: python3 utils/paper_trading_updater.py")
    print("5. Generate final comparison report")
    print("="*80)


if __name__ == "__main__":
    generate_comprehensive_report()
