# -*- coding: utf-8 -*-
"""
持仓管理服务
"""
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime
import os

STOCK_DB_PATH = os.environ.get('STOCK_DB_PATH', os.path.expanduser('~/.openclaw/data/stock.db'))


class PositionService:
    """持仓管理服务"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or STOCK_DB_PATH
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_positions(self) -> List[Dict]:
        """获取所有持仓"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM positions 
            WHERE quantity > 0 
            ORDER BY weight DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_position(self, ts_code: str) -> Optional[Dict]:
        """获取单个持仓"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM positions WHERE ts_code = ?', (ts_code,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def add_position(self, ts_code: str, name: str, quantity: int, price: float, action: str = "buy") -> Dict:
        """添加持仓"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute('SELECT * FROM positions WHERE ts_code = ?', (ts_code,))
        existing = cursor.fetchone()
        
        if existing:
            # 更新持仓
            old_qty = existing['quantity']
            old_cost = existing['avg_cost']
            
            if action == "sell":
                new_qty = old_qty - quantity
                if new_qty <= 0:
                    cursor.execute('DELETE FROM positions WHERE ts_code = ?', (ts_code,))
                    conn.commit()
                    conn.close()
                    return {"message": "已平仓", "ts_code": ts_code}
            else:
                new_qty = old_qty + quantity
            
            new_avg_cost = ((old_qty * old_cost) + (quantity * price)) / new_qty if new_qty > 0 else 0
            
            cursor.execute('''
                UPDATE positions 
                SET quantity = ?, avg_cost = ?, current_price = ?, updated_at = ?
                WHERE ts_code = ?
            ''', (new_qty, new_avg_cost, price, datetime.now().isoformat(), ts_code))
        else:
            if action == "sell" and quantity > 0:
                conn.close()
                return {"error": "无法卖出不存在的持仓", "ts_code": ts_code}
            
            # 新增持仓
            cursor.execute('''
                INSERT INTO positions (ts_code, name, quantity, avg_cost, current_price, position_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (ts_code, name, quantity, price, price, datetime.now().strftime('%Y%m%d')))
        
        conn.commit()
        conn.close()
        
        return {"message": "持仓已更新", "ts_code": ts_code}
    
    def update_price(self, ts_code: str, current_price: float) -> bool:
        """更新当前价格"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM positions WHERE ts_code = ?', (ts_code,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return False
        
        quantity = row['quantity']
        avg_cost = row['avg_cost']
        
        # 计算盈亏
        pnl = (current_price - avg_cost) * quantity
        pnl_pct = (current_price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0
        
        cursor.execute('''
            UPDATE positions 
            SET current_price = ?, pnl = ?, pnl_pct = ?, updated_at = ?
            WHERE ts_code = ?
        ''', (current_price, pnl, pnl_pct, datetime.now().isoformat(), ts_code))
        
        conn.commit()
        conn.close()
        return True
    
    def update_all_prices(self, prices: Dict[str, float]) -> int:
        """批量更新价格"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        count = 0
        for ts_code, current_price in prices.items():
            cursor.execute('SELECT * FROM positions WHERE ts_code = ?', (ts_code,))
            row = cursor.fetchone()
            
            if row:
                quantity = row['quantity']
                avg_cost = row['avg_cost']
                pnl = (current_price - avg_cost) * quantity
                pnl_pct = (current_price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0
                
                cursor.execute('''
                    UPDATE positions 
                    SET current_price = ?, pnl = ?, pnl_pct = ?, updated_at = ?
                    WHERE ts_code = ?
                ''', (current_price, pnl, pnl_pct, datetime.now().isoformat(), ts_code))
                count += 1
        
        conn.commit()
        conn.close()
        return count
    
    def close_position(self, ts_code: str) -> bool:
        """平仓"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM positions WHERE ts_code = ?', (ts_code,))
        
        conn.commit()
        conn.close()
        return True
    
    def get_position_summary(self) -> Dict:
        """获取持仓汇总"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as count,
                SUM(quantity * current_price) as total_value,
                SUM(pnl) as total_pnl
            FROM positions
            WHERE quantity > 0
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            "position_count": row['count'] or 0,
            "total_value": row['total_value'] or 0,
            "total_pnl": row['total_pnl'] or 0
        }


# 全局实例
position_service = PositionService()
