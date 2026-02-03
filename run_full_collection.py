#!/usr/bin/env python3
"""
Full Paper Trading Data Collection System
Runs comprehensive data collection for paper trading validation
Timestamp: 2026-02-03 20:51 GMT+1

Usage:
    python3 run_full_collection.py          # One-time collection
    python3 run_full_collection.py daily    # For cron jobs
"""

import sys
import json
from datetime import datetime
from pathlib import Path

from utils.paper_trading_signals import PaperTradingSignalGenerator
from utils.paper_trading_db import PaperTradingDB
from utils.paper_trading_updater import PaperTradingUpdater
from utils.paper_trading_report import PaperVsBacktestReport
from utils.slippage_model import SlippageModel
from utils.adverse_selection_monitor import AdverseSelectionMonitor, AlphaDecayTracker
from scanner import PolymarketScanner


class FullDataCollector:
    """
    Comprehensive data collection for paper trading.
    Collects signals, slippage data, and monitoring metrics.
    """
    
    def __init__(self, bankroll: float = 1000):
        self.bankroll = bankroll
        self.db = PaperTradingDB()
        self.signal_gen = PaperTradingSignalGenerator(bankroll=bankroll)
        self.updater = PaperTradingUpdater()
        self.slippage_model = SlippageModel()
        self.monitor = AdverseSelectionMonitor()
        self.scanner = PolymarketScanner()
        
        self.collection_dir = Path('data/collection_sessions')
        self.collection_dir.mkdir(parents=True, exist_ok=True)
    
    def collect_signals(self, max_markets: int = 30) -> dict:
        """Step 1: Generate and collect paper trading signals"""
        print("\n" + "="*80)
        print("STEP 1: COLLECTING PAPER TRADING SIGNALS")
        print("="*80)
        
        signals = self.signal_gen.generate_signals_for_markets(
            max_markets=max_markets,
            save_to_db=True
        )
        
        stats = self.signal_gen.get_signal_statistics(signals)
        
        print(f"\n📊 SIGNAL COLLECTION RESULTS:")
        print(f"  Signals Generated: {stats.get('total_signals', 0)}")
        print(f"  YES Signals:       {stats.get('yes_signals', 0)}")
        print(f"  NO Signals:        {stats.get('no_signals', 0)}")
        print(f"  Average Edge:      {stats.get('avg_edge', 0):.1%}")
        print(f"  Average Confidence: {stats.get('avg_confidence', 0):.0%}")
        print(f"  Total Exposure:    ${stats.get('total_exposure', 0):.2f}")
        
        return {
            'step': 'signals',
            'signals_count': len(signals),
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }
    
    def collect_slippage_data(self) -> dict:
        """Step 2: Analyze slippage across active markets"""
        print("\n" + "="*80)
        print("STEP 2: COLLECTING SLIPPAGE DATA")
        print("="*80)
        
        # Fetch active markets
        markets = self.scanner.get_active_markets(limit=50)
        
        # Analyze liquid markets
        slippage_data = []
        for market in markets:
            if market.liquidity >= 25000:  # At least $25K liquidity
                # Estimate slippage for $200 position
                est = self.slippage_model.estimate_slippage(
                    position_size=200,
                    liquidity=market.liquidity
                )
                
                slippage_data.append({
                    'market_slug': market.slug,
                    'question': market.question[:60],
                    'liquidity': market.liquidity,
                    'yes_price': market.yes_price,
                    'slippage_pct': est['total_slippage'] * 100,
                    'market_impact': est['market_impact'] * 100
                })
        
        # Calculate averages
        avg_slippage = sum(s['slippage_pct'] for s in slippage_data) / len(slippage_data) if slippage_data else 0
        
        print(f"\n📊 SLIPPAGE ANALYSIS:")
        print(f"  Markets Analyzed:  {len(slippage_data)}")
        print(f"  Average Slippage:  {avg_slippage:.2f}%")
        print(f"\n  Top 5 Highest Slippage:")
        sorted_by_slip = sorted(slippage_data, key=lambda x: x['slippage_pct'], reverse=True)[:5]
        for s in sorted_by_slip:
            print(f"    - {s['question'][:40]:<40} {s['slippage_pct']:>5.2f}%")
        
        return {
            'step': 'slippage',
            'markets_analyzed': len(slippage_data),
            'avg_slippage_pct': avg_slippage,
            'data': slippage_data,
            'timestamp': datetime.now().isoformat()
        }
    
    def update_outcomes(self) -> dict:
        """Step 3: Update any resolved trades with outcomes"""
        print("\n" + "="*80)
        print("STEP 3: UPDATING TRADE OUTCOMES")
        print("="*80)
        
        summary = self.updater.update_open_trades(verbose=False)
        
        print(f"\n📊 OUTCOME UPDATE RESULTS:")
        print(f"  Trades Updated:   {summary['updated']}")
        print(f"  Still Open:       {summary['unresolved']}")
        print(f"  Errors:           {summary['errors']}")
        
        # Get performance summary
        perf = self.db.get_performance_summary()
        
        if perf['total_trades'] > 0:
            print(f"\n📈 PERFORMANCE TO DATE:")
            print(f"  Closed Trades:    {perf['total_trades']}")
            print(f"  Win Rate:         {perf['win_rate']:.1%}")
            print(f"  Total P&L:        ${perf['total_pnl']:+.2f}")
            print(f"  Avg per Trade:    ${perf['avg_pnl']:+.2f}")
        
        return {
            'step': 'outcomes',
            'updated': summary['updated'],
            'unresolved': summary['unresolved'],
            'performance': perf,
            'timestamp': datetime.now().isoformat()
        }
    
    def run_adverse_selection_monitor(self) -> dict:
        """Step 4: Check for adverse selection and alpha decay"""
        print("\n" + "="*80)
        print("STEP 4: ADVERSE SELECTION & ALPHA DECAY MONITORING")
        print("="*80)
        
        # Run adverse selection analysis
        analysis = self.monitor.analyze_recent_trades()
        
        if analysis.get('status') == 'insufficient_data':
            print(f"\n{analysis['message']}")
            return {
                'step': 'monitoring',
                'status': 'insufficient_data',
                'timestamp': datetime.now().isoformat()
            }
        
        print(f"\n📊 MONITORING RESULTS:")
        print(f"  Win Rate:         {analysis['win_rate']:.1%}")
        print(f"  Trades Analyzed:  {analysis['trades_analyzed']}")
        print(f"  Total P&L:        ${analysis['total_pnl']:+.2f}")
        
        if analysis.get('alerts'):
            print(f"\n🚨 ALERTS ({len(analysis['alerts'])}):")
            for alert in analysis['alerts']:
                print(f"  [{alert['severity']}] {alert['message']}")
        else:
            print(f"\n✅ No adverse selection detected")
        
        # Check alpha decay
        decay_tracker = AlphaDecayTracker()
        decay = decay_tracker.detect_decay()
        
        if decay.get('status') == 'success':
            print(f"\n📉 ALPHA DECAY:")
            print(f"  Early Win Rate:   {decay['early_win_rate']:.1%}")
            print(f"  Recent Win Rate:  {decay['recent_win_rate']:.1%}")
            print(f"  Decay:            {decay['decay']:+.1%}")
            
            if decay.get('concerning'):
                print(f"  ⚠️  Significant alpha decay detected!")
        
        return {
            'step': 'monitoring',
            'analysis': analysis,
            'decay': decay if decay.get('status') == 'success' else None,
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_comparison_report(self) -> dict:
        """Step 5: Generate paper vs backtest comparison"""
        print("\n" + "="*80)
        print("STEP 5: PAPER vs BACKTEST COMPARISON")
        print("="*80)
        
        report = PaperVsBacktestReport()
        result = report.generate_report()
        
        if result.get('status') == 'insufficient_data':
            print(f"\n{result['message']}")
            return {
                'step': 'comparison',
                'status': 'insufficient_data',
                'timestamp': datetime.now().isoformat()
            }
        
        paper = result['paper_metrics']
        comp = result['comparison']
        
        print(f"\n📊 COMPARISON RESULTS:")
        print(f"  Paper Win Rate:     {paper['win_rate']:.1%}")
        print(f"  Expected Win Rate:  75%")
        print(f"  Slippage:           {comp['win_rate_slippage_pct']:.1f}%")
        
        print(f"\n🎯 RECOMMENDATION: {result['validation']['recommendation']}")
        
        return {
            'step': 'comparison',
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
    
    def save_session(self, results: list):
        """Save collection session to file"""
        session_file = self.collection_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(session_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Session saved to: {session_file}")
    
    def run_full_collection(self) -> list:
        """Run complete data collection pipeline"""
        print("="*80)
        print("🚀 FULL PAPER TRADING DATA COLLECTION")
        print("="*80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Bankroll: ${self.bankroll:,.2f}")
        print("="*80)
        
        results = []
        
        # Run all steps
        try:
            results.append(self.collect_signals(max_markets=30))
            results.append(self.collect_slippage_data())
            results.append(self.update_outcomes())
            results.append(self.run_adverse_selection_monitor())
            results.append(self.generate_comparison_report())
            
            # Save session
            self.save_session(results)
            
        except Exception as e:
            print(f"\n❌ Error during collection: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*80)
        print("✅ COLLECTION COMPLETE")
        print("="*80)
        print(f"\nNext steps:")
        print("1. Review collected data above")
        print("2. Run again tomorrow: python3 run_full_collection.py")
        print("3. After 3-7 days, analyze trends in data/collection_sessions/")
        print("4. Compare paper results to backtest expectations")
        print("="*80)
        
        return results


def main():
    """Main entry point"""
    collector = FullDataCollector(bankroll=1000)
    collector.run_full_collection()


if __name__ == "__main__":
    main()
