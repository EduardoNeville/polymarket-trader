#!/bin/bash
# Start Paper Trading Monitor
# Simple wrapper to start the monitor in background

cd /home/eduardoneville/projects/polymarket-trader

# Kill any existing instance
pkill -f run_paper_trading_continuous.py 2>/dev/null
sleep 1

# Remove stale PID
rm -f logs/paper_trading_monitor.pid

# Start in background
python3 run_paper_trading_continuous.py > logs/paper_trading_monitor.log 2>&1 &
PID=$!

# Wait a moment and check
sleep 2
if ps -p $PID > /dev/null; then
    echo "✅ Paper trading monitor started (PID: $PID)"
    echo $PID > logs/paper_trading_monitor.pid
else
    echo "❌ Failed to start monitor"
    echo "Check logs: logs/paper_trading_monitor.log"
fi
