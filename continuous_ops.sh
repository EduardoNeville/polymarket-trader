#!/bin/bash
# Continuous Operations Manager
# Manages all background processes for Polymarket trading system
# Timestamp: 2026-02-06 19:30 GMT+1

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
      sleep 1
      if pgrep -f "run_live_continuous.py" > /dev/null; then
        echo "✅ Live collector started"
      else
        echo "❌ Failed to start live collector"
      fi
    else
      echo "⚠️  Live collector already running"
    fi
    
    # 2. Paper Trading Monitor (every 5 minutes, replaces old cron jobs)
    echo "Starting paper trading monitor..."
    cd $WORK_DIR
    if python3 run_paper_trading_continuous.py status > /dev/null 2>&1; then
      echo "⚠️  Paper trading monitor already running"
    else
      cd $WORK_DIR && nohup python3 run_paper_trading_continuous.py > $LOG_DIR/paper_trading_monitor.log 2>&1 &
      sleep 1
      if python3 run_paper_trading_continuous.py status > /dev/null 2>&1; then
        echo "✅ Paper trading monitor started"
      else
        echo "❌ Failed to start paper trading monitor"
      fi
    fi
    
    # Remove old cron jobs (replaced by continuous monitor)
    echo "Removing old cron jobs (replaced by continuous monitor)..."
    crontab -l 2>/dev/null | grep -v "daily_paper_trading\|high_edge_scanner" | crontab -
    echo "✅ Old cron jobs removed"
    
    echo ""
    echo "✅ All continuous operations started!"
    echo ""
    echo "Active Processes:"
    echo "  • Live Data Collector - collects market data every 60s"
    echo "  • Paper Trading Monitor - checks TP/SL & trades every 5min"
    echo ""
    echo "Run './continuous_ops.sh status' to check status"
    ;;
    
  stop)
    echo "🛑 Stopping continuous operations..."
    
    # Stop live collector
    if pgrep -f "run_live_continuous.py" > /dev/null; then
      pkill -f "run_live_continuous.py" 2>/dev/null
      echo "✅ Live collector stopped"
    else
      echo "⚠️  Live collector not running"
    fi
    
    # Stop paper trading monitor
    cd $WORK_DIR
    if python3 run_paper_trading_continuous.py status > /dev/null 2>&1; then
      python3 run_paper_trading_continuous.py stop
    else
      echo "⚠️  Paper trading monitor not running"
    fi
    
    # Also remove any stale PID files
    rm -f $LOG_DIR/paper_trading_monitor.pid
    
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
    
    # Check paper trading monitor
    echo ""
    cd $WORK_DIR && python3 run_paper_trading_continuous.py status
    
    # Show data stats
    echo ""
    echo "📈 Data Collection:"
    LATEST_PARQUET=$(ls -t $WORK_DIR/data/live_markets/*.parquet 2>/dev/null | head -1)
    if [ -n "$LATEST_PARQUET" ]; then
      SIZE=$(ls -lh "$LATEST_PARQUET" | awk '{print $5}')
      echo "  • Latest data: $SIZE ($(basename $LATEST_PARQUET))"
    else
      echo "  • No parquet files found"
    fi
    
    # Show paper trading stats
    echo ""
    echo "📊 Paper Trading:"
    cd $WORK_DIR && python3 -c "
from utils.paper_trading_db import PaperTradingDB
db = PaperTradingDB()
open_trades = db.get_open_trades()
closed_trades = db.get_closed_trades()

if open_trades or closed_trades:
    open_exposure = sum(t.get('intended_size', 0) for t in open_trades)
    realized_pnl = sum(t.get('pnl', 0) for t in closed_trades)
    available = 1000 - open_exposure + realized_pnl
    
    print(f'  • Open positions: {len(open_trades)}')
    print(f'  • Closed trades: {len(closed_trades)}')
    print(f'  • Deployed: \${open_exposure:.2f}')
    print(f'  • Realized PnL: \${realized_pnl:+.2f}')
    print(f'  • Available: \${available:.2f}')
else:
    print('  • No trades in database')
" 2>/dev/null || echo "  • Database check failed"
    
    echo ""
    echo "📋 Log Files:"
    echo "  • Live collector: $LOG_DIR/live_collector.log"
    echo "  • Paper trading: $LOG_DIR/paper_trading_monitor.log"
    ;;
    
  restart)
    echo "🔄 Restarting continuous operations..."
    $0 stop
    sleep 2
    $0 start
    ;;
    
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    echo ""
    echo "Commands:"
    echo "  start    - Start all continuous operations"
    echo "  stop     - Stop all continuous operations"
    echo "  restart  - Restart all operations"
    echo "  status   - Check status of all operations"
    echo ""
    echo "Paper Trading Monitor (individual control):"
    echo "  python3 run_paper_trading_continuous.py start   # Start in foreground"
    echo "  python3 run_paper_trading_continuous.py stop    # Stop"
    echo "  python3 run_paper_trading_continuous.py status  # Check status"
    ;;
esac
