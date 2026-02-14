#!/usr/bin/env python3
"""
Master script to run all 3 parallel paper trading strategies.
Called by cron every 5 minutes.
"""

import sys
sys.path.insert(0, '/home/eduardoneville/projects/polymarket-trader')

import logging
import os
from datetime import datetime
from pathlib import Path

# Ensure log directory exists
Path('logs').mkdir(exist_ok=True)

# Setup logging
log_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler('logs/all_strategies.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_strategy_a():
    """Run Strategy A: Hard 7-day filter"""
    try:
        from strategies.strategy_a_generator import StrategyASignalGenerator
        
        logger.info("=" * 60)
        logger.info("RUNNING STRATEGY A: Hard 7-Day Filter")
        logger.info("=" * 60)
        
        gen = StrategyASignalGenerator(bankroll=1000)
        
        # Check TP/SL hits and updates
        from utils.paper_trading_tp_monitor import check_all_tp_sl
        tp_hits, sl_hits, resolved = check_all_tp_sl(db_path=gen.DB_PATH)
        logger.info(f"  TP/SL check: TP={tp_hits}, SL={sl_hits}, Resolved={resolved}")
        
        # Update outcomes
        from utils.paper_trading_updater import update_outcomes
        updated = update_outcomes(db_path=gen.DB_PATH)
        logger.info(f"  Outcomes updated: {updated}")
        
        # Generate new signals
        signals = gen.run_cycle()
        
        logger.info(f"✅ Strategy A complete: {len(signals)} new signals")
        return len(signals)
        
    except Exception as e:
        logger.error(f"❌ Strategy A failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

def run_strategy_b():
    """Run Strategy B: Aggressive multipliers"""
    try:
        from strategies.strategy_b_generator import StrategyBSignalGenerator
        
        logger.info("=" * 60)
        logger.info("RUNNING STRATEGY B: Aggressive Time Multipliers")
        logger.info("=" * 60)
        
        gen = StrategyBSignalGenerator(bankroll=1000)
        
        # Check TP/SL hits and updates
        from utils.paper_trading_tp_monitor import check_all_tp_sl
        tp_hits, sl_hits, resolved = check_all_tp_sl(db_path=gen.DB_PATH)
        logger.info(f"  TP/SL check: TP={tp_hits}, SL={sl_hits}, Resolved={resolved}")
        
        # Update outcomes
        from utils.paper_trading_updater import update_outcomes
        updated = update_outcomes(db_path=gen.DB_PATH)
        logger.info(f"  Outcomes updated: {updated}")
        
        # Generate new signals
        signals = gen.run_cycle()
        
        logger.info(f"✅ Strategy B complete: {len(signals)} new signals")
        return len(signals)
        
    except Exception as e:
        logger.error(f"❌ Strategy B failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

def run_strategy_c():
    """Run Strategy C: Tiered approach"""
    try:
        from strategies.strategy_c_generator import StrategyCSignalGenerator
        
        logger.info("=" * 60)
        logger.info("RUNNING STRATEGY C: Tiered Capital Allocation")
        logger.info("=" * 60)
        
        gen = StrategyCSignalGenerator(bankroll=1000)
        
        # Check TP/SL hits and updates
        from utils.paper_trading_tp_monitor import check_all_tp_sl
        tp_hits, sl_hits, resolved = check_all_tp_sl(db_path=gen.DB_PATH)
        logger.info(f"  TP/SL check: TP={tp_hits}, SL={sl_hits}, Resolved={resolved}")
        
        # Update outcomes
        from utils.paper_trading_updater import update_outcomes
        updated = update_outcomes(db_path=gen.DB_PATH)
        logger.info(f"  Outcomes updated: {updated}")
        
        # Generate new signals
        signals = gen.run_cycle()
        
        logger.info(f"✅ Strategy C complete: {len(signals)} new signals")
        return len(signals)
        
    except Exception as e:
        logger.error(f"❌ Strategy C failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

def main():
    """Run all three strategies in sequence."""
    start_time = datetime.now()
    logger.info("\n" + "=" * 70)
    logger.info("🚀 ALL STRATEGIES CYCLE START")
    logger.info(f"Timestamp: {start_time.isoformat()}")
    logger.info("=" * 70)
    
    # Run each strategy
    results = {
        'A': run_strategy_a(),
        'B': run_strategy_b(),
        'C': run_strategy_c(),
    }
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    total_new = sum(results.values())
    
    logger.info("\n" + "=" * 70)
    logger.info("📊 CYCLE SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Strategy A (7-day):    {results['A']} new signals")
    logger.info(f"Strategy B (Multi):    {results['B']} new signals")
    logger.info(f"Strategy C (Tiered):   {results['C']} new signals")
    logger.info(f"Total new signals:     {total_new}")
    logger.info(f"Duration:              {duration:.1f} seconds")
    logger.info(f"Next run:              Every 5 minutes via cron")
    logger.info("=" * 70)
    
    return results

if __name__ == "__main__":
    main()
