"""
Paper Trading Database
SQLite-based storage for paper trading records
Timestamp: 2026-02-03 19:40 GMT+1
"""

import sqlite3
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd


class PaperTradingDB:
    """
    SQLite database for paper trading records.
    
    Features:
    - Persistent storage of paper trades
    - Query by date, market, strategy
    - Update with outcomes and P&L
    - Export to pandas DataFrame
    """
    
    def __init__(self, db_path: str = "data/paper_trading.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create paper_trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    market_slug TEXT NOT NULL,
                    market_question TEXT,
                    intended_side TEXT NOT NULL,
                    intended_price REAL NOT NULL,
                    intended_size REAL NOT NULL,
                    executed_price REAL,
                    executed_timestamp TEXT,
                    outcome INTEGER,
                    pnl REAL,
                    strategy TEXT,
                    edge REAL,
                    confidence REAL,
                    status TEXT DEFAULT 'open',
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_slug 
                ON paper_trades(market_slug)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON paper_trades(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_status 
                ON paper_trades(status)
            """)
            
            conn.commit()
        
        # Migrate: Add take-profit columns if they don't exist
        self._migrate_add_take_profit_columns()
    
    def _migrate_add_take_profit_columns(self):
        """Add take-profit columns to existing database (migration)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get existing columns
            cursor.execute("PRAGMA table_info(paper_trades)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            # Add new columns if they don't exist
            new_columns = {
                'take_profit_price': 'REAL',
                'take_profit_pct': 'REAL',
                'exit_reason': 'TEXT',
                'holding_days': 'INTEGER',
                'exit_timestamp': 'TEXT'
            }
            
            for column, data_type in new_columns.items():
                if column not in existing_columns:
                    cursor.execute(f"""
                        ALTER TABLE paper_trades 
                        ADD COLUMN {column} {data_type}
                    """)
                    print(f"Added column: {column}")
            
            conn.commit()
    
    def save_trade(self, trade: Dict[str, Any]) -> str:
        """
        Save a paper trade to the database.
        
        Args:
            trade: Dict with trade details
            
        Returns:
            Trade ID
        """
        trade_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO paper_trades (
                    id, timestamp, market_slug, market_question,
                    intended_side, intended_price, intended_size,
                    executed_price, executed_timestamp, outcome, pnl,
                    strategy, edge, confidence, status, notes,
                    take_profit_price, take_profit_pct, exit_reason,
                    holding_days, exit_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_id,
                trade.get('timestamp', datetime.now().isoformat()),
                trade.get('market_slug', ''),
                trade.get('market_question', ''),
                trade.get('intended_side', ''),
                trade.get('intended_price', 0.0),
                trade.get('intended_size', 0.0),
                trade.get('executed_price'),
                trade.get('executed_timestamp'),
                trade.get('outcome'),
                trade.get('pnl'),
                trade.get('strategy', 'ensemble'),
                trade.get('edge', 0.0),
                trade.get('confidence', 0.0),
                trade.get('status', 'open'),
                trade.get('notes', ''),
                trade.get('take_profit_price'),
                trade.get('take_profit_pct'),
                trade.get('exit_reason'),
                trade.get('holding_days'),
                trade.get('exit_timestamp')
            ))
            
            conn.commit()
        
        return trade_id
    
    def get_trade(self, trade_id: str) -> Optional[Dict]:
        """Get a single trade by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM paper_trades WHERE id = ?",
                (trade_id,)
            )
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_trades_by_market(self, market_slug: str) -> List[Dict]:
        """Get all trades for a specific market"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM paper_trades WHERE market_slug = ? ORDER BY timestamp",
                (market_slug,)
            )
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_trades_by_date_range(
        self,
        start_date: str,
        end_date: str,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        Get trades within a date range.
        
        Args:
            start_date: ISO format date string (YYYY-MM-DD)
            end_date: ISO format date string
            status: Optional filter by status ('open', 'closed')
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if status:
                cursor.execute("""
                    SELECT * FROM paper_trades 
                    WHERE DATE(timestamp) BETWEEN ? AND ?
                    AND status = ?
                    ORDER BY timestamp
                """, (start_date, end_date, status))
            else:
                cursor.execute("""
                    SELECT * FROM paper_trades 
                    WHERE DATE(timestamp) BETWEEN ? AND ?
                    ORDER BY timestamp
                """, (start_date, end_date))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def update_trade_outcome(
        self,
        trade_id: str,
        outcome: int,
        pnl: float,
        notes: str = ""
    ) -> bool:
        """
        Update a trade with its outcome.
        
        Args:
            trade_id: Trade UUID
            outcome: 1 for YES win, 0 for NO win
            pnl: Profit/loss amount
            notes: Optional notes
            
        Returns:
            True if updated successfully
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE paper_trades 
                SET outcome = ?, pnl = ?, status = 'closed', 
                    notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (outcome, pnl, notes, trade_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def update_executed_price(
        self,
        trade_id: str,
        executed_price: float,
        notes: str = ""
    ) -> bool:
        """Update the actual executed price for a trade"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE paper_trades 
                SET executed_price = ?, executed_timestamp = ?, 
                    notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (executed_price, datetime.now().isoformat(), notes, trade_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def get_open_trades(self) -> List[Dict]:
        """Get all trades that haven't been resolved yet"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM paper_trades WHERE status = 'open' ORDER BY timestamp"
            )
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_closed_trades(self) -> List[Dict]:
        """Get all resolved trades with outcomes"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM paper_trades WHERE status = 'closed' ORDER BY timestamp"
            )
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_performance_summary(self) -> Dict:
        """
        Get summary statistics for paper trading performance.
        
        Returns:
            Dict with win_rate, total_pnl, avg_trade, etc.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get closed trades
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    AVG(intended_price) as avg_entry_price,
                    AVG(edge) as avg_edge
                FROM paper_trades 
                WHERE status = 'closed'
            """)
            
            row = cursor.fetchone()
            if row and row[0] > 0:
                total, wins, losses, total_pnl, avg_pnl, avg_entry, avg_edge = row
                return {
                    'total_trades': total,
                    'winning_trades': wins,
                    'losing_trades': losses,
                    'win_rate': wins / total if total > 0 else 0,
                    'total_pnl': total_pnl or 0,
                    'avg_pnl': avg_pnl or 0,
                    'avg_entry_price': avg_entry or 0,
                    'avg_edge': avg_edge or 0,
                    'open_trades': len(self.get_open_trades())
                }
            
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'avg_entry_price': 0,
                'avg_edge': 0,
                'open_trades': len(self.get_open_trades())
            }
    
    def get_trades_by_exit_reason(self, exit_reason: str) -> List[Dict]:
        """Get all trades with a specific exit reason ('tp', 'resolution', etc.)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM paper_trades WHERE exit_reason = ? ORDER BY timestamp",
                (exit_reason,)
            )
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_avg_holding_time(self) -> Dict:
        """Get average holding time metrics for closed trades"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    AVG(holding_days) as avg_holding_days,
                    MIN(holding_days) as min_holding_days,
                    MAX(holding_days) as max_holding_days,
                    COUNT(*) as closed_with_holding_data
                FROM paper_trades 
                WHERE status = 'closed' AND holding_days IS NOT NULL
            """)
            
            row = cursor.fetchone()
            if row and row[0] is not None:
                return {
                    'avg_holding_days': row[0],
                    'min_holding_days': row[1],
                    'max_holding_days': row[2],
                    'closed_with_holding_data': row[3]
                }
            
            return {
                'avg_holding_days': None,
                'min_holding_days': None,
                'max_holding_days': None,
                'closed_with_holding_data': 0
            }
    
    def update_trade_take_profit(
        self,
        trade_id: str,
        exit_price: float,
        pnl: float,
        exit_reason: str,
        holding_days: int,
        notes: str = ""
    ) -> bool:
        """
        Update a trade when take-profit is hit.
        
        Args:
            trade_id: Trade UUID
            exit_price: Price at exit
            pnl: Profit/loss amount
            exit_reason: 'tp' or 'resolution'
            holding_days: Days held
            notes: Optional notes
            
        Returns:
            True if updated successfully
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE paper_trades 
                SET executed_price = ?, pnl = ?, status = 'closed',
                    exit_reason = ?, holding_days = ?, exit_timestamp = ?,
                    notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (exit_price, pnl, exit_reason, holding_days, 
                  datetime.now().isoformat(), notes, trade_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def get_exit_reason_summary(self) -> Dict:
        """Get summary of trades by exit reason"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    exit_reason,
                    COUNT(*) as count,
                    AVG(pnl) as avg_pnl,
                    SUM(pnl) as total_pnl
                FROM paper_trades 
                WHERE status = 'closed' AND exit_reason IS NOT NULL
                GROUP BY exit_reason
            """)
            
            results = {}
            for row in cursor.fetchall():
                reason = row[0] or 'unknown'
                results[reason] = {
                    'count': row[1],
                    'avg_pnl': row[2],
                    'total_pnl': row[3]
                }
            
            return results
    
    def to_dataframe(self, status: Optional[str] = None) -> pd.DataFrame:
        """Export all trades to pandas DataFrame"""
        with sqlite3.connect(self.db_path) as conn:
            if status:
                query = "SELECT * FROM paper_trades WHERE status = ?"
                df = pd.read_sql_query(query, conn, params=(status,))
            else:
                df = pd.read_sql_query("SELECT * FROM paper_trades", conn)
            
            # Convert timestamp columns
            for col in ['timestamp', 'executed_timestamp', 'created_at', 'updated_at']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            return df
    
    def delete_trade(self, trade_id: str) -> bool:
        """Delete a trade by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM paper_trades WHERE id = ?", (trade_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def clear_all_trades(self) -> int:
        """Clear all trades (use with caution!)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM paper_trades")
            conn.commit()
            return cursor.rowcount


# Simple test
if __name__ == "__main__":
    print("Testing PaperTradingDB...")
    
    db = PaperTradingDB("data/test_paper_trading.db")
    
    # Test save
    trade = {
        'timestamp': datetime.now().isoformat(),
        'market_slug': 'test-market',
        'market_question': 'Will it rain tomorrow?',
        'intended_side': 'YES',
        'intended_price': 0.65,
        'intended_size': 100.0,
        'strategy': 'ensemble',
        'edge': 0.15,
        'confidence': 0.8
    }
    
    trade_id = db.save_trade(trade)
    print(f"✓ Saved trade: {trade_id}")
    
    # Test retrieve
    retrieved = db.get_trade(trade_id)
    print(f"✓ Retrieved trade: {retrieved['market_slug']}")
    
    # Test update outcome
    db.update_trade_outcome(trade_id, 1, 35.0, "Test outcome")
    print(f"✓ Updated outcome")
    
    # Test summary
    summary = db.get_performance_summary()
    print(f"✓ Performance: {summary}")
    
    # Test DataFrame export
    df = db.to_dataframe()
    print(f"✓ DataFrame: {len(df)} rows")
    
    # Cleanup
    db.clear_all_trades()
    Path("data/test_paper_trading.db").unlink()
    
    print("\n✅ All tests passed!")
