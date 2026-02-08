#!/usr/bin/env python3
"""
Continuous Paper Trading Monitor
Independent background process (not using OpenClaw cron)
Runs TP/SL checks and trade generation every 5 minutes

Usage:
    python3 run_paper_trading_continuous.py        # Start in foreground
    python3 run_paper_trading_continuous.py &      # Start in background
    python3 run_paper_trading_continuous.py stop   # Stop running instance
    python3 run_paper_trading_continuous.py status # Check if running
"""

import sys
import os
import time
import signal
import psutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from cron_paper_trading import run_paper_trading_cycle, calculate_exposure, BANKROLL

# Configuration
PID_FILE = Path('logs/paper_trading_monitor.pid')
LOG_FILE = Path('logs/paper_trading_continuous.log')
CHECK_INTERVAL = 300  # 5 minutes


def is_already_running():
    """Check if another instance is already running"""
    if PID_FILE.exists():
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process exists
            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                if 'paper_trading' in process.name() or any('paper_trading' in arg for arg in process.cmdline()):
                    return True
        except (ValueError, psutil.NoSuchProcess):
            pass
        
        # Stale PID file
        PID_FILE.unlink()
    return False


def write_pid():
    """Write current PID to file"""
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))


def remove_pid():
    """Remove PID file on exit"""
    if PID_FILE.exists():
        PID_FILE.unlink()


def log_message(message):
    """Log to file with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}\n"
    
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(log_line)
    
    # Also print to console
    print(log_line, end='')


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    log_message("🛑 Shutdown signal received. Stopping...")
    remove_pid()
    sys.exit(0)


def run_continuous():
    """Main continuous loop"""
    # Check if already running
    if is_already_running():
        print("❌ Paper trading monitor is already running!")
        print(f"   PID file: {PID_FILE}")
        print("   Use 'python3 run_paper_trading_continuous.py status' to check")
        sys.exit(1)
    
    # Write PID file
    write_pid()
    
    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Get initial status
    exposure = calculate_exposure()
    
    log_message("=" * 70)
    log_message("🚀 CONTINUOUS PAPER TRADING MONITOR STARTED")
    log_message("=" * 70)
    log_message(f"PID: {os.getpid()}")
    log_message(f"Check interval: {CHECK_INTERVAL} seconds (5 minutes)")
    log_message(f"Log file: {LOG_FILE}")
    log_message(f"Bankroll: ${BANKROLL:.2f}")
    log_message(f"Open positions: {exposure['open_count']}")
    log_message(f"Closed trades: {exposure['closed_count']}")
    log_message(f"Deployed: ${exposure['total_exposure']:.2f}")
    log_message(f"Realized PnL: ${exposure['realized_pnl']:+.2f}")
    log_message(f"Available: ${exposure['available']:.2f}")
    log_message("=" * 70)
    
    cycle_count = 0
    
    try:
        while True:
            cycle_count += 1
            
            # Run one trading cycle
            try:
                result = run_paper_trading_cycle()
                
                # Log summary
                log_message(
                    f"Cycle {cycle_count}: "
                    f"Open={result['open_trades']}, Closed={result['closed_trades']}, "
                    f"Exp=${result['exposure']:.0f}, "
                    f"PnL=${result['realized_pnl']:+.0f}, "
                    f"Avail=${result['available']:.0f}, "
                    f"TP={result['tp_hits']}, SL={result['sl_hits']}, "
                    f"New={result['new_signals']}"
                )
                
            except Exception as e:
                log_message(f"❌ Error in cycle {cycle_count}: {e}")
                import traceback
                log_message(traceback.format_exc())
            
            # Sleep until next check
            log_message(f"💤 Sleeping for {CHECK_INTERVAL} seconds...")
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        log_message("🛑 Interrupted by user")
    finally:
        remove_pid()
        log_message("👋 Monitor stopped")


def stop_monitor():
    """Stop the running monitor"""
    if not PID_FILE.exists():
        print("❌ No PID file found. Monitor may not be running.")
        print(f"   Check: ps aux | grep paper_trading")
        return
    
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        print(f"🛑 Stopping paper trading monitor (PID: {pid})...")
        
        # Send SIGTERM
        os.kill(pid, signal.SIGTERM)
        
        # Wait for process to exit
        for _ in range(10):
            if not psutil.pid_exists(pid):
                print("✅ Monitor stopped successfully")
                return
            time.sleep(0.5)
        
        # Force kill if still running
        print("⚠️  Process didn't exit gracefully. Force killing...")
        os.kill(pid, signal.SIGKILL)
        print("✅ Monitor force stopped")
        
    except (ValueError, ProcessLookupError):
        print("❌ Process not found. Removing stale PID file...")
        remove_pid()
    except Exception as e:
        print(f"❌ Error stopping monitor: {e}")


def check_status():
    """Check if monitor is running. Returns True if running, False otherwise."""
    running = False
    
    if not PID_FILE.exists():
        # Double check with ps
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'run_paper_trading_continuous' in cmdline and proc.info['pid'] != os.getpid():
                    print(f"✅ Monitor is running (PID: {proc.info['pid']})")
                    print(f"   Found via process scan (no PID file)")
                    running = True
                    return running
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        print("❌ Monitor is NOT running")
        return running
    
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        if psutil.pid_exists(pid):
            process = psutil.Process(pid)
            print(f"✅ Monitor is RUNNING (PID: {pid})")
            print(f"   Started: {datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Runtime: {(time.time() - process.create_time()) / 3600:.1f} hours")
            
            # Show current exposure
            exposure = calculate_exposure()
            print(f"   Open: {exposure['open_count']} | Closed: {exposure['closed_count']}")
            print(f"   Deployed: ${exposure['total_exposure']:.2f}")
            print(f"   Realized PnL: ${exposure['realized_pnl']:+.2f}")
            print(f"   Available: ${exposure['available']:.2f}")
            running = True
        else:
            print(f"❌ Monitor is NOT running (stale PID file: {pid})")
            remove_pid()
    except Exception as e:
        print(f"❌ Error checking status: {e}")
    
    return running


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        
        if cmd == 'stop':
            stop_monitor()
            sys.exit(0)
        elif cmd == 'status':
            running = check_status()
            sys.exit(0 if running else 1)
        elif cmd == 'start':
            run_continuous()
        else:
            print(f"Unknown command: {cmd}")
            print("\nUsage:")
            print("  python3 run_paper_trading_continuous.py        # Start in foreground")
            print("  python3 run_paper_trading_continuous.py start  # Start in foreground")
            print("  python3 run_paper_trading_continuous.py stop   # Stop running instance")
            print("  python3 run_paper_trading_continuous.py status # Check status")
            sys.exit(1)
    else:
        run_continuous()


if __name__ == '__main__':
    main()
