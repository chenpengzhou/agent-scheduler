# -*- coding: utf-8 -*-
"""
股票数据服务
"""
import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class StockDataService:
    """股票数据服务"""
    
    # 备选数据库路径列表
    DEFAULT_DB_PATHS = [
        # 环境变量
        os.environ.get('STOCK_DB_PATH'),
        # 服务器部署路径
        "/home/deploy/.openclaw/data/stock.db",
        "/data/stock.db",
        # 开发路径
        "/home/deploy/.openclaw/data/stock.db",
        "/home/deploy/.openclaw/workspace-dev/src/stock.db",
        # 当前目录
        "./stock.db",
        "../stock.db",
        # 相对路径
        "data/stock.db",
    ]
    
    def __init__(self, db_path: str = None):
        # 优先级：参数 > 环境变量 > 自动检测
        self.db_path = self._resolve_db_path(db_path)
        self._ensure_db()
    
    def _resolve_db_path(self, db_path: str = None) -> str:
        """解析数据库路径"""
        # 1. 优先使用传入的参数
        if db_path and os.path.exists(db_path):
            return db_path
        
        # 2. 检查环境变量
        env_path = os.environ.get('STOCK_DB_PATH')
        if env_path and os.path.exists(env_path):
            return env_path
        
        # 3. 尝试自动检测
        for path in self.DEFAULT_DB_PATHS:
            if path and os.path.exists(path):
                logger.info(f"自动检测到数据库: {path}")
                return path
        
        # 4. 返回第一个作为默认值（即使不存在）
        for path in self.DEFAULT_DB_PATHS:
            if path:
                return path
        
        return "stock.db"
    
    def _ensure_db(self):
        """确保数据库存在"""
        if os.path.exists(self.db_path):
            logger.info(f"使用数据库: {self.db_path}")
        else:
            logger.warning(f"数据库文件不存在: {self.db_path}")
    
    def _get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def get_quote(self, code: str, date: str = None) -> Optional[Dict]:
        """获取单只股票数据"""
        if not date:
            date = datetime.now().strftime('%Y%m%d')
        
        code = self._normalize_code(code)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for table in ['stock_daily', 'stock']:
            try:
                cursor.execute(f'''
                    SELECT ts_code, date, open, high, low, close, vol, volume, amount
                    FROM {table}
                    WHERE ts_code = ? AND date = ?
                ''', (code, date))
                
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return self._parse_row(table, row)
            except:
                continue
        
        conn.close()
        return None
    
    def get_quotes(self, codes: List[str], date: str = None) -> List[Dict]:
        """批量获取股票数据"""
        if not date:
            date = datetime.now().strftime('%Y%m%d')
        
        results = []
        for code in codes:
            quote = self.get_quote(code, date)
            if quote:
                results.append(quote)
        return results
    
    def get_recent(self, code: str, days: int = 5) -> List[Dict]:
        """获取最近N天数据"""
        code = self._normalize_code(code)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for table in ['stock_daily', 'stock']:
            try:
                cursor.execute(f'''
                    SELECT ts_code, date, open, high, low, close, vol, volume, amount
                    FROM {table}
                    WHERE ts_code = ?
                    ORDER BY date DESC
                    LIMIT ?
                ''', (code, days))
                
                rows = cursor.fetchall()
                conn.close()
                
                if rows:
                    return [self._parse_row(table, row) for row in rows]
            except:
                continue
        
        conn.close()
        return []
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {'db_path': self.db_path, 'db_records': 0, 'db_stocks': 0}
        
        for table in ['stock_daily', 'stock']:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                stats['db_records'] = cursor.fetchone()[0]
                
                cursor.execute(f'SELECT COUNT(DISTINCT ts_code) FROM {table}')
                stats['db_stocks'] = cursor.fetchone()[0]
                break
            except:
                continue
        
        conn.close()
        return stats
    
    def _normalize_code(self, code: str) -> str:
        """标准化股票代码"""
        if not code:
            return code
        if '.' not in code:
            if code.startswith('6'):
                return f"{code}.SH"
            else:
                return f"{code}.SZ"
        return code
    
    def _parse_row(self, table: str, row: tuple) -> Dict:
        """解析数据行"""
        return {
            'code': row[0],
            'date': row[1],
            'open': float(row[2] or 0),
            'high': float(row[3] or 0),
            'low': float(row[4] or 0),
            'close': float(row[5] or 0),
            'volume': float(row[6] or row[7] or 0),
            'amount': float(row[8] or 0),
            'source': 'local'
        }


# 全局服务实例
_service: Optional[StockDataService] = None


def get_stock_service(db_path: str = None) -> StockDataService:
    """获取股票数据服务实例"""
    global _service
    if _service is None or db_path is not None:
        _service = StockDataService(db_path)
    return _service


def reset_stock_service():
    """重置服务实例（用于测试）"""
    global _service
    _service = None
