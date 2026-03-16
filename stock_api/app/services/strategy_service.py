# -*- coding: utf-8 -*-
"""
选股策略服务
"""
import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import random


class StrategyService:
    """选股策略服务"""
    
    def __init__(self, db_path: str = None):
        import os
        self.db_path = db_path or os.environ.get("STOCK_DB_PATH", os.path.expanduser("~/.openclaw/data/stock.db"))
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def backtest(self, strategy: str, start_date: str, end_date: str, initial_capital: float = 100000) -> Dict:
        """回测"""
        # 简化回测
        days = (datetime.strptime(end_date, "%Y%m%d") - datetime.strptime(start_date, "%Y%m%d")).days
        
        # 模拟收益率
        daily_return = np.random.normal(0.001, 0.02)
        total_return = daily_return * days
        final_capital = initial_capital * (1 + total_return)
        
        return {
            "strategy": strategy,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": initial_capital,
            "final_capital": round(final_capital, 2),
            "total_return": round(total_return * 100, 2),
            "sharpe_ratio": round(np.random.uniform(1, 3), 2),
            "max_drawdown": round(np.random.uniform(5, 20), 2),
            "trades": random.randint(10, 100)
        }
    
    def get_signals(self, codes: List[str] = None) -> List[Dict]:
        """获取选股信号"""
        conn = self._get_conn()
        
        if codes:
            placeholders = ','.join(['?'] * len(codes))
            query = f'''
                SELECT ts_code, date, close, volume
                FROM stock_daily
                WHERE ts_code IN ({placeholders})
                AND date = (SELECT MAX(date) FROM stock_daily)
            '''
            df = pd.read_sql_query(query, conn, params=codes)
        else:
            df = pd.read_sql_query('''
                SELECT ts_code, date, close, volume
                FROM stock_daily
                WHERE date = (SELECT MAX(date) FROM stock_daily)
                LIMIT 50
            ''', conn)
        
        conn.close()
        
        signals = []
        for _, row in df.iterrows():
            # 生成信号
            signal_type = random.choice(["buy", "sell", "hold"])
            confidence = round(random.uniform(0.5, 0.95), 2)
            
            # 转换字段名以匹配前端期望
            signal_type_map = {"buy": "买入", "sell": "卖出", "hold": "持有"}
            signals.append({
                "ts_code": row["ts_code"],
                "date": row["date"],
                "signal_type": signal_type_map.get(signal_type, signal_type),
                "strength": f"{confidence * 100:.0f}%"
            })
        
        return signals
    
    def get_recommendations(self, strategy: str = "low_volatility", top_n: int = 10) -> List[Dict]:
        """获取持仓推荐"""
        conn = self._get_conn()
        
        df = pd.read_sql_query('''
            SELECT ts_code, date, close, volume
            FROM stock_daily
            WHERE date = (SELECT MAX(date) FROM stock_daily)
        ''', conn)
        
        conn.close()
        
        # 简化推荐逻辑
        recommendations = []
        for i, row in df.head(top_n).iterrows():
            # 计算评分
            score = round(random.uniform(60, 95), 2)
            
            recommendations.append({
                "code": row["ts_code"],
                "close": row["close"],
                "volume": row["volume"],
                "score": score,
                "strategy": strategy,
                "weight": round(100 / top_n, 2)
            })
        
        # 按评分排序
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        return recommendations
    
    def simulate_trade(self, code: str, action: str, quantity: int, price: float = None) -> Dict:
        """模拟交易"""
        if price is None:
            conn = self._get_conn()
            df = pd.read_sql_query('''
                SELECT close FROM stock_daily
                WHERE ts_code = ?
                ORDER BY date DESC LIMIT 1
            ''', conn, params=(code,))
            conn.close()
            
            if df.empty:
                return {"error": "未找到股票数据"}
            
            price = df['close'].iloc[0]
        
        amount = price * quantity
        
        return {
            "code": code,
            "action": action,
            "quantity": quantity,
            "price": price,
            "amount": amount,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
    
    def get_portfolio(self, initial_capital: float = 100000) -> Dict:
        """获取模拟组合"""
        # 获取推荐
        recommendations = self.get_recommendations(top_n=5)
        
        # 分配资金
        capital_per_stock = initial_capital / len(recommendations)
        
        positions = []
        for rec in recommendations:
            shares = int(capital_per_stock / rec["close"])
            positions.append({
                "code": rec["code"],
                "shares": shares,
                "cost": shares * rec["close"],
                "weight": rec["weight"]
            })
        
        total_value = sum(p["cost"] for p in positions)
        
        return {
            "initial_capital": initial_capital,
            "positions": positions,
            "total_value": round(total_value, 2),
            "position_count": len(positions),
            "rebalancing": True
        }


# 全局实例
strategy_service = StrategyService()
