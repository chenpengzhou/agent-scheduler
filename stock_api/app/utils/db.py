# -*- coding: utf-8 -*-
"""
数据库工具
"""
import sqlite3
import os
from typing import Optional, List, Dict

# 数据库路径配置
STOCK_DB_PATH = os.environ.get('STOCK_DB_PATH', os.path.expanduser('~/.openclaw/data/stock.db'))


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """获取数据库连接"""
    path = db_path or STOCK_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = None):
    """初始化数据库表"""
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
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_daily_code ON stock_daily(ts_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_daily_date ON stock_daily(date)')
    
    conn.commit()
    conn.close()


def get_stock_connection():
    """获取股票数据库连接"""
    return get_connection(STOCK_DB_PATH)


def query_one(sql: str, params: tuple = None, db_path: str = None) -> Optional[Dict]:
    """查询单条记录"""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def query_all(sql: str, params: tuple = None, db_path: str = None) -> List[Dict]:
    """查询多条记录"""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


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
    
    return last_id
