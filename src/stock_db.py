#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据管理模块
- 本地 SQLite 缓存
- 自动从 API 获取缺失数据
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, List

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None

# 数据库路径
DB_PATH = "/home/robin/.openclaw/data/stock.db"

# 环境变量读取 TOKEN（优先）
TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN', '')


def init_db() -> None:
    """初始化数据库表结构"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_code TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            amount REAL,
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ts_code, trade_date)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_ts_date 
        ON stock_daily(ts_code, trade_date)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_trade_date 
        ON stock_daily(trade_date)
    ''')
    
    conn.commit()
    conn.close()


def get_stock_data(ts_code: str, trade_date: str) -> Optional[Dict]:
    """
    获取单只股票单日数据
    先查本地缓存，没有则从 API 获取并缓存
    
    Args:
        ts_code: 股票代码，如 '000001.SZ'
        trade_date: 交易日期，格式 'YYYYMMDD'
    
    Returns:
        数据字典或 None
    """
    # 确保数据库已初始化
    init_db()
    
    # 先查本地缓存
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT ts_code, trade_date, open, high, low, close, volume, amount
        FROM stock_daily 
        WHERE ts_code = ? AND trade_date = ?
    ''', (ts_code, trade_date))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'ts_code': row[0],
            'trade_date': row[1],
            'open': row[2],
            'high': row[3],
            'low': row[4],
            'close': row[5],
            'volume': row[6],
            'amount': row[7],
            'source': 'cache'
        }
    
    # 本地没有，从 API 获取
    return _fetch_from_api(ts_code, trade_date)


def _fetch_from_api(ts_code: str, trade_date: str) -> Optional[Dict]:
    """从 Tushare API 获取数据并缓存"""
    if not TUSHARE_TOKEN:
        print("⚠️ TUSHARE_TOKEN 未设置")
        return None
    
    try:
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        
        df = pro.daily(ts_code=ts_code, trade_date=trade_date)
        
        if df.empty:
            return None
        
        # 转换为字典
        row = df.iloc[0]
        data = {
            'ts_code': row['ts_code'],
            'trade_date': row['trade_date'],
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': float(row['vol']),
            'amount': float(row.get('amount', 0)),
            'source': 'api'
        }
        
        # 保存到本地
        save_stock_data(data)
        return data
        
    except Exception as e:
        print(f"❌ API 获取失败: {e}")
        return None


def save_stock_data(data: Dict) -> bool:
    """
    保存股票数据到本地数据库
    
    Args:
        data: 股票数据字典，包含 ts_code, trade_date, open, high, low, close, volume, amount
    
    Returns:
        是否成功
    """
    try:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO stock_daily 
            (ts_code, trade_date, open, high, low, close, volume, amount, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            data['ts_code'],
            data['trade_date'],
            data.get('open'),
            data.get('high'),
            data.get('low'),
            data.get('close'),
            data.get('volume'),
            data.get('amount')
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 保存数据失败: {e}")
        return False


def save_stock_dataframe(df) -> int:
    """
    批量保存 DataFrame 数据到本地数据库
    
    Args:
        df: DataFrame，包含 ts_code, trade_date, open, high, low, close, vol/volume, amount 列
    
    Returns:
        成功保存的记录数
    """
    if not HAS_PANDAS:
        raise ImportError("需要安装 pandas: pip install pandas")
    
    if df.empty:
        return 0
    
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    count = 0
    for _, row in df.iterrows():
        try:
            # 处理列名差异 (vol vs volume)
            volume = row.get('vol', row.get('volume', 0))
            amount = row.get('amount', 0)
            
            cursor.execute('''
                INSERT OR REPLACE INTO stock_daily 
                (ts_code, trade_date, open, high, low, close, volume, amount, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                row['ts_code'],
                row['trade_date'],
                float(row['open']),
                float(row['high']),
                float(row['low']),
                float(row['close']),
                float(volume),
                float(amount)
            ))
            count += 1
        except Exception as e:
            print(f"⚠️ 跳过异常行: {e}")
            continue
    
    conn.commit()
    conn.close()
    print(f"✅ 批量保存 {count} 条记录")
    return count


def get_daily_data(trade_date: str):
    """
    获取指定日期的所有股票数据
    先查本地，缺失则从 API 获取全量并缓存
    
    Args:
        trade_date: 交易日期，格式 'YYYYMMDD'
    
    Returns:
        DataFrame 包含当日所有股票数据 (需要 pandas)
    """
    if not HAS_PANDAS:
        raise ImportError("需要安装 pandas: pip install pandas")
    
    init_db()
    conn = sqlite3.connect(DB_PATH)
    
    # 先查本地
    df = pd.read_sql_query('''
        SELECT ts_code, trade_date, open, high, low, close, volume, amount
        FROM stock_daily 
        WHERE trade_date = ?
    ''', conn, params=(trade_date,))
    
    conn.close()
    
    if not df.empty:
        df['source'] = 'cache'
        return df
    
    # 本地没有，从 API 获取全量
    if not TUSHARE_TOKEN:
        print("⚠️ TUSHARE_TOKEN 未设置")
        return pd.DataFrame()
    
    try:
        import tushare as ts
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        
        df = pro.daily(trade_date=trade_date)
        
        if not df.empty:
            # 保存到本地
            save_stock_dataframe(df)
            df['source'] = 'api'
        
        return df
        
    except Exception as e:
        print(f"❌ API 获取失败: {e}")
        return pd.DataFrame()


def delete_old_data(days: int = 90) -> int:
    """
    删除 N 天前的旧数据
    
    Args:
        days: 保留最近多少天的数据
    
    Returns:
        删除的记录数
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 计算截止日期
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
    
    cursor.execute('DELETE FROM stock_daily WHERE trade_date < ?', (cutoff,))
    deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    print(f"🗑️ 已删除 {deleted} 条 {cutoff} 前的旧数据")
    return deleted


def get_cache_stats() -> Dict:
    """获取缓存统计信息"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM stock_daily')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT trade_date) FROM stock_daily')
    days = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT ts_code) FROM stock_daily')
    stocks = cursor.fetchone()[0]
    
    cursor.execute('SELECT MIN(trade_date), MAX(trade_date) FROM stock_daily')
    date_range = cursor.fetchone()
    
    conn.close()
    
    return {
        'total_records': total,
        'total_days': days,
        'total_stocks': stocks,
        'date_range': date_range,
        'db_path': DB_PATH
    }


if __name__ == '__main__':
    # 测试
    init_db()
    print("数据库初始化完成")
    
    # 查看缓存统计
    stats = get_cache_stats()
    print(f"\n缓存统计:")
    print(f"  总记录数: {stats['total_records']}")
    print(f"  日期数量: {stats['total_days']}")
    print(f"  股票数量: {stats['total_stocks']}")
    print(f"  数据范围: {stats['date_range']}")
