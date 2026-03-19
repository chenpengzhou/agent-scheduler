# -*- coding: utf-8 -*-
"""
数据库连接池和缓存
"""
import sqlite3
import os
import time
from functools import lru_cache, wraps
from typing import Optional

# SQLite配置
STOCK_DB_PATH = os.environ.get('STOCK_DB_PATH', os.path.expanduser("~/.openclaw/data/stock.db"))

# 缓存配置
CACHE_TTL = 300  # 5分钟缓存

# SQLite重试装饰器
def with_retry(retries=3, delay=0.5):
    """数据库操作重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if 'locked' in str(e) and attempt < retries - 1:
                        time.sleep(delay * (attempt + 1))
                        continue
                    raise
            return func(*args, **kwargs)
        return wrapper
    return decorator

# 简单内存缓存
class SimpleCache:
    def __init__(self):
        self._cache = {}
        self._times = {}
    
    def get(self, key: str) -> Optional[any]:
        if key in self._cache:
            if time.time() - self._times[key] < CACHE_TTL:
                return self._cache[key]
            del self._cache[key]
            del self._times[key]
        return None
    
    def set(self, key: str, value: any):
        self._cache[key] = value
        self._times[key] = time.time()
    
    def clear(self):
        self._cache.clear()
        self._times.clear()
    
    def delete(self, key: str):
        if key in self._cache:
            del self._cache[key]
            del self._times[key]


# 全局缓存实例
cache = SimpleCache()


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """获取数据库连接"""
    path = db_path or STOCK_DB_PATH
    conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    
    # SQLite优化：WAL模式 + 超时设置
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA cache_size=10000')
        conn.execute('PRAGMA busy_timeout=30000')  # 30秒超时
    except:
        pass
    
    return conn


def init_db(db_path: str = None):
    """初始化数据库"""
    path = db_path or STOCK_DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    conn = get_connection(path)
    cursor = conn.cursor()
    
    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) DEFAULT 'user',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Token黑名单
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS token_blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token VARCHAR(500) NOT NULL UNIQUE,
            expired_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 同步任务表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status VARCHAR(20) DEFAULT 'idle',
            total_stocks INTEGER DEFAULT 0,
            completed_stocks INTEGER DEFAULT 0,
            current_stock VARCHAR(20),
            started_at TIMESTAMP,
            stopped_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 因子缓存表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_factors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_code VARCHAR(20) NOT NULL,
            date VARCHAR(10) NOT NULL,
            pe REAL,
            pb REAL,
            volatility_20d REAL,
            volatility_60d REAL,
            ma5 REAL,
            ma10 REAL,
            ma20 REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ts_code, date)
        )
    ''')
    
    # 股票日线数据表
    cursor.execute('''
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ts_code, date)
        )
    ''')
    
    # API配置表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            key_value VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            rate_limit INTEGER DEFAULT 100,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    ''')
    
    # 同步配置表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            source VARCHAR(50) NOT NULL,
            interval_minutes INTEGER DEFAULT 60,
            enabled BOOLEAN DEFAULT 1,
            last_sync TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 策略表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            type VARCHAR(50) NOT NULL,
            params TEXT,
            description TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 回测结果表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER NOT NULL,
            start_date VARCHAR(10) NOT NULL,
            end_date VARCHAR(10) NOT NULL,
            initial_capital REAL NOT NULL,
            final_capital REAL,
            total_return REAL,
            annual_return REAL,
            sharpe_ratio REAL,
            max_drawdown REAL,
            trades_count INTEGER,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (strategy_id) REFERENCES strategies(id)
        )
    ''')
    
    # 告警规则表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            type VARCHAR(50) NOT NULL,
            condition TEXT NOT NULL,
            threshold REAL,
            enabled BOOLEAN DEFAULT 1,
            notify_channels TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 告警记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id INTEGER NOT NULL,
            ts_code VARCHAR(20),
            message TEXT,
            severity VARCHAR(20),
            is_resolved BOOLEAN DEFAULT 0,
            resolved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rule_id) REFERENCES alert_rules(id)
        )
    ''')
    
    # 持仓表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_code VARCHAR(20) NOT NULL,
            name VARCHAR(100),
            quantity INTEGER DEFAULT 0,
            avg_cost REAL DEFAULT 0,
            current_price REAL DEFAULT 0,
            pnl REAL DEFAULT 0,
            pnl_pct REAL DEFAULT 0,
            weight REAL DEFAULT 0,
            position_date VARCHAR(10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 账户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) NOT NULL,
            initial_capital REAL NOT NULL,
            current_capital REAL NOT NULL,
            total_value REAL DEFAULT 0,
            total_pnl REAL DEFAULT 0,
            total_pnl_pct REAL DEFAULT 0,
            cash REAL DEFAULT 0,
            position_value REAL DEFAULT 0,
            position_count INTEGER DEFAULT 0,
            trade_count INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 交易记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_code VARCHAR(20) NOT NULL,
            name VARCHAR(100),
            action VARCHAR(10) NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            amount REAL NOT NULL,
            commission REAL DEFAULT 0,
            trade_date VARCHAR(10) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_daily_code ON stock_daily(ts_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_daily_date ON stock_daily(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sync_configs_enabled ON sync_configs(enabled)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_strategies_active ON strategies(is_active)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled ON alert_rules(enabled)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_alert_records_rule ON alert_records(rule_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_code ON positions(ts_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_date ON positions(position_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_code ON trades(ts_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(trade_date)')
    
    conn.commit()
    conn.close()


def get_stock_connection():
    return get_connection(STOCK_DB_PATH)


def query_one(sql: str, params: tuple = None, db_path: str = None, use_cache: bool = False) -> Optional[dict]:
    """查询单条记录"""
    # 尝试从缓存获取
    cache_key = f"query_one:{sql}:{params}"
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    
    row = cursor.fetchone()
    conn.close()
    
    result = dict(row) if row else None
    
    if use_cache and result:
        cache.set(cache_key, result)
    
    return result


def query_all(sql: str, params: tuple = None, db_path: str = None, use_cache: bool = False) -> list:
    """查询多条记录"""
    # 尝试从缓存获取
    cache_key = f"query_all:{sql}:{params}"
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    
    rows = cursor.fetchall()
    conn.close()
    
    result = [dict(row) for row in rows]
    
    if use_cache and result:
        cache.set(cache_key, result)
    
    return result


def execute(sql: str, params: tuple = None, db_path: str = None) -> int:
    """执行SQL"""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    
    # 清除相关缓存
    cache.clear()
    
    return last_id
