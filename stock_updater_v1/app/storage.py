"""SQLite 存储模块"""
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from .config import config
from .utils.logger import logger


class SQLiteStorage:
    """SQLite 存储"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database_path
        self._ensure_db_dir()

    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_tables(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 股票日线数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code VARCHAR(20) NOT NULL,
                date VARCHAR(10) NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                source VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ts_code, date, source)
            )
        """)

        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_daily_code_date 
            ON stock_daily(ts_code, date)
        """)

        # 股票基本信息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_basic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code VARCHAR(20) NOT NULL UNIQUE,
                name VARCHAR(100),
                industry VARCHAR(100),
                list_date VARCHAR(10),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 更新日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS update_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source VARCHAR(50),
                status VARCHAR(20),
                records INT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 任务配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name VARCHAR(50) UNIQUE,
                interval_minutes INT DEFAULT 60,
                enabled BOOLEAN DEFAULT 1,
                last_run TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()
        logger.info("Database tables initialized")

    def save(self, df: pd.DataFrame, table_name: str, if_exists: str = 'replace') -> int:
        """保存数据"""
        if df is None or len(df) == 0:
            logger.warning(f"Empty DataFrame, skipping save to {table_name}")
            return 0

        conn = self._get_connection()
        try:
            df.to_sql(table_name, conn, if_exists=if_exists, index=False)
            row_count = len(df)
            logger.info(f"Saved {row_count} rows to {table_name}")
            return row_count
        except Exception as e:
            logger.error(f"Error saving to {table_name}: {e}")
            raise
        finally:
            conn.close()

    def append(self, df: pd.DataFrame, table_name: str) -> int:
        """追加数据"""
        return self.save(df, table_name, if_exists='append')

    def replace(self, df: pd.DataFrame, table_name: str) -> int:
        """替换数据"""
        return self.save(df, table_name, if_exists='replace')

    def query(self, sql: str, params: tuple = None) -> pd.DataFrame:
        """查询数据"""
        conn = self._get_connection()
        try:
            if params:
                df = pd.read_sql(sql, conn, params=params)
            else:
                df = pd.read_sql(sql, conn)
            return df
        finally:
            conn.close()

    def get_latest_date(self, table_name: str, ts_code: str = None) -> Optional[str]:
        """获取最新日期"""
        if ts_code:
            sql = f"SELECT MAX(date) as max_date FROM {table_name} WHERE ts_code = ?"
            df = self.query(sql, (ts_code,))
        else:
            sql = f"SELECT MAX(date) as max_date FROM {table_name}"
            df = self.query(sql)

        if len(df) > 0 and df.iloc[0]['max_date']:
            return df.iloc[0]['max_date']
        return None

    def log_update(self, source: str, status: str, records: int, message: str = ""):
        """记录更新日志"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO update_log (source, status, records, message) VALUES (?, ?, ?, ?)",
            (source, status, records, message)
        )
        conn.commit()
        conn.close()
        logger.debug(f"Logged update: {source} - {status} - {records} records")

    def get_update_history(self, source: str = None, limit: int = 10) -> pd.DataFrame:
        """获取更新历史"""
        if source:
            sql = "SELECT * FROM update_log WHERE source = ? ORDER BY created_at DESC LIMIT ?"
            return self.query(sql, (source, limit))
        else:
            sql = "SELECT * FROM update_log ORDER BY created_at DESC LIMIT ?"
            return self.query(sql, (limit,))

    def get_table_count(self, table_name: str) -> int:
        """获取表记录数"""
        df = self.query(f"SELECT COUNT(*) as cnt FROM {table_name}")
        return int(df.iloc[0]['cnt']) if len(df) > 0 else 0


# 全局存储实例
storage = SQLiteStorage()
