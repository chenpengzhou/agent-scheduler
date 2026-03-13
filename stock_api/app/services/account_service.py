# -*- coding: utf-8 -*-
"""
账户管理服务
"""
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime
import os

STOCK_DB_PATH = os.environ.get('STOCK_DB_PATH', os.path.expanduser('~/.openclaw/data/stock.db'))


class AccountService:
    """账户管理服务"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or STOCK_DB_PATH
        self._ensure_default_account()
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _ensure_default_account(self):
        """确保默认账户存在"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM accounts LIMIT 1')
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO accounts (name, initial_capital, current_capital, cash)
                VALUES (?, ?, ?, ?)
            ''', ('默认账户', 100000, 100000, 100000))
            conn.commit()
        
        conn.close()
    
    def get_account(self, account_id: int = 1) -> Optional[Dict]:
        """获取账户信息"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM accounts WHERE id = ?', (account_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # 更新账户汇总
        account = dict(row)
        account.update(self._calculate_summary(account_id))
        
        return account
    
    def _calculate_summary(self, account_id: int) -> Dict:
        """计算账户汇总"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 持仓汇总
        cursor.execute('''
            SELECT 
                COUNT(*) as count,
                COALESCE(SUM(quantity * current_price), 0) as position_value,
                COALESCE(SUM(pnl), 0) as position_pnl
            FROM positions WHERE quantity > 0
        ''')
        pos_row = cursor.fetchone()
        
        # 交易统计
        cursor.execute('''
            SELECT 
                COUNT(*) as trade_count,
                SUM(CASE WHEN action = 'buy' THEN 1 ELSE 0 END) as buy_count,
                SUM(CASE WHEN action = 'sell' THEN 1 ELSE 0 END) as sell_count
            FROM trades
        ''')
        trade_row = cursor.fetchone()
        
        # 获取当前现金
        cursor.execute('SELECT cash FROM accounts WHERE id = ?', (account_id,))
        account_row = cursor.fetchone()
        cash = account_row['cash'] if account_row else 0
        
        conn.close()
        
        position_count = pos_row['count'] or 0
        position_value = pos_row['position_value'] or 0
        position_pnl = pos_row['position_pnl'] or 0
        
        total_value = cash + position_value
        total_pnl = position_pnl
        total_pnl_pct = (total_pnl / (cash + position_value - total_pnl) * 100) if total_value > 0 else 0
        
        # 胜率
        win_count = 0
        trade_count = trade_row['trade_count'] or 0
        win_rate = (win_count / trade_count * 100) if trade_count > 0 else 0
        
        return {
            "position_count": position_count,
            "position_value": position_value,
            "total_value": total_value,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "cash": cash,
            "trade_count": trade_count,
            "win_rate": win_rate
        }
    
    def update_account(self, account_id: int, **kwargs) -> bool:
        """更新账户"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        allowed_fields = ['name', 'initial_capital', 'cash']
        updates = []
        values = []
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(account_id)
        cursor.execute(f"UPDATE accounts SET {', '.join(updates)}, updated_at = ? WHERE id = ?",
                      (*values, datetime.now().isoformat(), account_id))
        
        conn.commit()
        conn.close()
        return True
    
    def get_trades(self, ts_code: str = None, limit: int = 50) -> List[Dict]:
        """获取交易记录"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        if ts_code:
            cursor.execute('''
                SELECT * FROM trades 
                WHERE ts_code = ?
                ORDER BY trade_date DESC, id DESC
                LIMIT ?
            ''', (ts_code, limit))
        else:
            cursor.execute('''
                SELECT * FROM trades 
                ORDER BY trade_date DESC, id DESC
                LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def add_trade(self, ts_code: str, name: str, action: str, quantity: int, 
                  price: float, trade_date: str = None) -> Dict:
        """添加交易记录"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        amount = quantity * price
        commission = amount * 0.0003  # 万三手续费
        
        if not trade_date:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        # 插入交易记录
        cursor.execute('''
            INSERT INTO trades (ts_code, name, action, quantity, price, amount, commission, trade_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ts_code, name, action, quantity, price, amount, commission, trade_date))
        
        # 更新账户现金
        if action == 'buy':
            cursor.execute('''
                UPDATE accounts SET cash = cash - ?, updated_at = ?
                WHERE id = 1
            ''', (amount + commission, datetime.now().isoformat()))
        else:
            cursor.execute('''
                UPDATE accounts SET cash = cash + ?, updated_at = ?
                WHERE id = 1
            ''', (amount - commission, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return {
            "message": "交易已记录",
            "ts_code": ts_code,
            "action": action,
            "quantity": quantity,
            "amount": amount
        }
    
    def get_account_summary(self) -> Dict:
        """获取账户总览"""
        account = self.get_account(1)
        
        if not account:
            return {}
        
        return {
            "name": account['name'],
            "initial_capital": account['initial_capital'],
            "current_capital": account['cash'],
            "total_value": account.get('total_value', 0),
            "total_pnl": account.get('total_pnl', 0),
            "total_pnl_pct": account.get('total_pnl_pct', 0),
            "position_count": account.get('position_count', 0),
            "position_value": account.get('position_value', 0),
            "cash": account.get('cash', 0),
            "trade_count": account.get('trade_count', 0),
            "win_rate": account.get('win_rate', 0)
        }


# 全局实例
account_service = AccountService()
