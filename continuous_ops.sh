#!/bin/bash
# Continuous Operations Manager
# Manages all background processes for Polymarket trading system
# Timestamp: 2026-02-03 21:52 GMT+1

WORK_DIR="/home/eduardoneville/projects/polymarket-trader"
LOG_DIR="$WORK_DIR/logs"

mkdir -p $LOG_DIR

case "$1" in
  start)
    echo "🚀 Starting continuous operations..."
    
    # 1. Live Data Collector (every 60 seconds)
    echo "Starting live data collector..."
    if ! pgrep -f "run_live_continuous.py" > /dev/null; then
      cd $WORK_DIR && nohup python3 run_live_continuous.py > $LOG_DIR/live_collector.log 2>&1 &
      echo "✅ Live collector started (PID: $!)"
    else
      echo "⚠️  Live collector already running"
    fi
    
    # 2. Daily Paper Trading (will be run via cron)
    echo "Setting up daily paper trading cron..."
    (crontab -l 2>/dev/null | grep -v "daily_paper_trading"; echo "0 9 * * * cd $WORK_DIR && python3 daily_paper_trading.py >> $LOG_DIR/daily_paper.log 2>&1") | crontab -
    echo "✅ Daily paper trading scheduled for 9:00 AM"
    
    # 3. High-Edge Scanner (every 6 hours)
    echo "Setting up high-edge scanner cron..."
    (crontab -l 2>/dev/null | grep -v "high_edge_scanner"; echo "0 */6 * * * cd $WORK_DIR && python3 high_edge_scanner.py >> $LOG_DIR/high_edge.log 2>&1") | crontab -
    echo "✅ High-edge scanner scheduled every 6 hours"
    
    echo ""
    echo "✅ All continuous operations started!"
    echo "Run '$0 status' to check status"
    ;;
    
  stop)
    echo "🛑 Stopping continuous operations..."
    
    # Stop live collector
    pkill -f "run_live_continuous.py" 2>/dev/null && echo "✅ Live collector stopped" || echo "⚠️  Live collector not running"
    
    # Remove cron jobs
    crontab -l 2>/dev/null | grep -v "daily_paper_trading\|high_edge_scanner" | crontab -
    echo "✅ Cron jobs removed"
    
    echo ""
    echo "✅ All operations stopped"
    ;;
    
  status)
    echo "📊 CONTINUOUS OPERATIONS STATUS"
    echo "=================================="
    
    # Check live collector
    if pgrep -f "run_live_continuous.py" > /dev/null; then
      PID=$(pgrep -f "run_live_continuous.py")
      echo "✅ Live Data Collector: RUNNING (PID: $PID)"
    else
      echo "❌ Live Data Collector: STOPPED"
    fi
    
    # Check cron jobs
    echo ""
    echo "📅 Scheduled Jobs:"
    crontab -l 2>/dev/null | grep -E "(daily_paper|high_edge)" | while read line; do
      echo "  • $line"
    done || echo "  (none configured)"
    
    # Show data stats
    echo ""
    echo "📈 Data Collection:"
    if [ -f "$WORK_DIR/data/live_markets/markets_2026-02-03.parquet" ]; then
      SIZE=$(ls -lh "$WORK_DIR/data/live_markets/markets_2026-02-03.parquet" | awk '{print $5}')
      echo "  • Live data: $SIZE"
    fi
    ;;
    
  *)
    echo "Usage: $0 {start|stop|status}"
    echo ""
    echo "Commands:"
    echo "  start   - Start all continuous operations"
    echo "  stop    - Stop all continuous operations"
    echo "  status  - Check status of all operations"
    ;;
esac
