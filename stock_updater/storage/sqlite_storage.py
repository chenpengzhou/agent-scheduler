# -*- coding: utf-8 -*-
"""
SQLite 存储实现
兼容现有的 stock.db 表结构
"""
import sqlite3
import os
from datetime import date, datetime
from typing import List, Dict, Optional, Tuple
from .base import DataStorage
from ..models import DataType, SaveMode


class SQLiteStorage(DataStorage):
    """SQLite 数据存储"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_tables()
    
    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_tables(self):
        """初始化数据表 - 复用现有表结构"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 检查现有表结构
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='stock_daily'")
        result = cursor.fetchone()
        
        if result:
            # 表已存在，检查是否有需要的列
            cursor.execute("PRAGMA table_info(stock_daily)")
            columns = {row[1] for row in cursor.fetchall()}
            
            # 如果有 ts_code 和 date，使用现有结构
            if 'ts_code' in columns and 'date' in columns:
                self._use_existing_schema = True
            else:
                self._use_existing_schema = False
        else:
            # 创建新表
            self._use_existing_schema = False
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_daily (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    amount REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_code, trade_date)
                )
            ''')
        
        conn.commit()
        conn.close()
    
    def _get_table_name(self, data_type: DataType) -> Optional[str]:
        """获取数据表名"""
        table_map = {
            DataType.OHLCV: "stock_daily",
            DataType.DAILY_BASIC: "stock_daily_basic"
        }
        return table_map.get(data_type)
    
    def _get_code_column(self) -> str:
        """获取股票代码列名"""
        return 'ts_code' if getattr(self, '_use_existing_schema', True) else 'stock_code'
    
    def _get_date_column(self) -> str:
        """获取日期列名"""
        return 'date' if getattr(self, '_use_existing_schema', True) else 'trade_date'
    
    def get_data_range(self, 
                       stock_code: str, 
                       data_type: DataType) -> Tuple[Optional[date], Optional[date]]:
        """获取指定股票数据的日期范围"""
        table_name = self._get_table_name(data_type)
        if not table_name:
            return (None, None)
        
        code_col = self._get_code_column()
        date_col = self._get_date_column()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT MIN({date_col}), MAX({date_col})
            FROM {table_name}
            WHERE {code_col} = ?
        ''', (stock_code,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            try:
                min_date = datetime.strptime(str(row[0]), '%Y%m%d').date()
                max_date = datetime.strptime(str(row[1]), '%Y%m%d').date()
                return (min_date, max_date)
            except:
                return (None, None)
        
        return (None, None)
    
    def save(self, 
             data_type: DataType, 
             records: List[Dict],
             mode: SaveMode = SaveMode.UPSERT) -> int:
        """保存数据"""
        if not records:
            return 0
        
        table_name = self._get_table_name(data_type)
        if not table_name:
            return 0
        
        code_col = self._get_code_column()
        date_col = self._get_date_column()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        count = 0
        for record in records:
            try:
                # 统一字段名
                stock_code = record.get('stock_code') or record.get('ts_code')
                trade_date = record.get('trade_date') or record.get('date')
                
                if mode == SaveMode.REPLACE:
                    cursor.execute(f'''
                        INSERT OR REPLACE INTO {table_name}
                        ({code_col}, {date_col}, open, high, low, close, volume, amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        stock_code,
                        trade_date,
                        record.get('open'),
                        record.get('high'),
                        record.get('low'),
                        record.get('close'),
                        record.get('volume'),
                        record.get('amount')
                    ))
                else:  # UPSERT
                    # 检查是否存在
                    cursor.execute(f'''
                        SELECT 1 FROM {table_name}
                        WHERE {code_col} = ? AND {date_col} = ?
                    ''', (stock_code, trade_date))
                    
                    if not cursor.fetchone():
                        cursor.execute(f'''
                            INSERT INTO {table_name}
                            ({code_col}, {date_col}, open, high, low, close, volume, amount)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            stock_code,
                            trade_date,
                            record.get('open'),
                            record.get('high'),
                            record.get('low'),
                            record.get('close'),
                            record.get('volume'),
                            record.get('amount')
                        ))
                        count += 1
            except Exception as e:
                print(f"⚠️ 保存记录失败: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        return count if mode == SaveMode.UPSERT else len(records)
    
    def exists(self, 
               stock_code: str, 
               data_type: DataType,
               target_date: date) -> bool:
        """检查指定日期数据是否存在"""
        table_name = self._get_table_name(data_type)
        if not table_name:
            return False
        
        code_col = self._get_code_column()
        date_col = self._get_date_column()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        date_str = target_date.strftime('%Y%m%d')
        
        cursor.execute(f'''
            SELECT 1 FROM {table_name}
            WHERE {code_col} = ? AND {date_col} = ?
            LIMIT 1
        ''', (stock_code, date_str))
        
        exists = cursor.fetchone() is not None
        conn.close()
        
        return exists
    
    def get_all_stock_codes(self) -> List[str]:
        """获取所有已存在的股票代码"""
        code_col = self._get_code_column()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f'SELECT DISTINCT {code_col} FROM stock_daily')
        codes = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return codes
    
    def get_stats(self) -> Dict:
        """获取数据库统计信息"""
        code_col = self._get_code_column()
        date_col = self._get_date_column()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # 日线数据统计
        cursor.execute('SELECT COUNT(*) FROM stock_daily')
        stats['daily_count'] = cursor.fetchone()[0]
        
        cursor.execute(f'SELECT COUNT(DISTINCT {code_col}) FROM stock_daily')
        stats['daily_stocks'] = cursor.fetchone()[0]
        
        cursor.execute(f'SELECT MIN({date_col}), MAX({date_col}) FROM stock_daily')
        row = cursor.fetchone()
        stats['daily_range'] = (row[0], row[1]) if row[0] else (None, None)
        
        # 尝试基础数据统计
        try:
            cursor.execute('SELECT COUNT(*) FROM stock_daily_basic')
            stats['basic_count'] = cursor.fetchone()[0]
        except:
            stats['basic_count'] = 0
        
        conn.close()
        return stats
