#!/bin/bash
# Daily strategy report generator
# Run this daily to get an email/summary of all strategy performance

cd /home/eduardoneville/projects/polymarket-trader

echo "========================================"
echo "DAILY STRATEGY REPORT"
echo "Date: $(date)"
echo "========================================"
echo ""

# Run dashboard
python3 strategy_dashboard.py

echo ""
echo "========================================"
echo "Report saved to: results/"
echo "Next report: Tomorrow"
echo "========================================"
