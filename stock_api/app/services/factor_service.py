# -*- coding: utf-8 -*-
"""
因子计算服务
"""
import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class FactorService:
    """因子计算服务"""
    
    def __init__(self, db_path: str = None):
        import os
        self.db_path = db_path or os.environ.get("STOCK_DB_PATH", os.path.expanduser("~/.openclaw/data/stock.db"))
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_factors(self, code: str, days: int = 60) -> Dict:
        """获取因子数据"""
        # 标准化代码
        if '.' not in code:
            code = f"{code}.SH" if code.startswith('6') else f"{code}.SZ"
        
        conn = self._get_conn()
        
        # 获取历史数据
        df = pd.read_sql_query('''
            SELECT date, open, high, low, close, volume
            FROM stock_daily
            WHERE ts_code = ?
            ORDER BY date DESC
            LIMIT ?
        ''', conn, params=(code, days))
        
        conn.close()
        
        if df.empty:
            return {"error": "未找到数据"}
        
        df = df.sort_values('date')
        
        # 计算各种因子
        close_prices = df['close'].values
        volumes = df['volume'].values
        
        # 1. 估值因子
        # 简化PE (假设EPS=0.5)
        pe = round(close_prices[0] / 0.5, 2) if close_prices[0] else None
        # 简化PB (假设BV=5)
        pb = round(close_prices[0] / 5, 2) if close_prices[0] else None
        
        # 2. 波动率因子
        returns = np.diff(close_prices) / close_prices[:-1]
        volatility_20d = round(np.std(returns[-20:]) * 100, 4) if len(returns) >= 20 else None
        volatility_60d = round(np.std(returns) * 100, 4) if len(returns) >= 60 else None
        
        # 3. 股息因子 (简化)
        dv_ratio = round(np.random.uniform(1, 4), 2)  # 模拟
        
        # 4. 移动平均线
        ma5 = round(np.mean(close_prices[:5]), 2) if len(close_prices) >= 5 else None
        ma10 = round(np.mean(close_prices[:10]), 2) if len(close_prices) >= 10 else None
        ma20 = round(np.mean(close_prices[:20]), 2) if len(close_prices) >= 20 else None
        ma60 = round(np.mean(close_prices[:60]), 2) if len(close_prices) >= 60 else None
        
        # 5. 成交量因子
        avg_volume_20d = round(np.mean(volumes[:20]), 0) if len(volumes) >= 20 else None
        volume_ratio = round(volumes[0] / avg_volume_20d, 2) if avg_volume_20d else None
        
        # 6. ROE (简化)
        roe = round(np.random.uniform(5, 20), 2)  # 模拟
        
        return {
            "code": code,
            "date": df['date'].iloc[-1],
            "close": close_prices[0],
            # 估值因子
            "pe": pe,
            "pb": pb,
            "dv_ratio": dv_ratio,
            # 波动率因子
            "volatility_20d": volatility_20d,
            "volatility_60d": volatility_60d,
            # 均线因子
            "ma5": ma5,
            "ma10": ma10,
            "ma20": ma20,
            "ma60": ma60,
            # 成交量因子
            "avg_volume_20d": avg_volume_20d,
            "volume_ratio": volume_ratio,
            # 质量因子
            "roe": roe,
            # 历史数据
            "history": df.tail(30).to_dict('records')
        }
    
    def calculate_custom_factor(self, code: str, factor_name: str, params: Dict = None) -> Optional[float]:
        """计算自定义因子"""
        conn = self._get_conn()
        
        df = pd.read_sql_query('''
            SELECT date, close, volume
            FROM stock_daily
            WHERE ts_code = ?
            ORDER BY date DESC
            LIMIT 100
        ''', conn, params=(code,))
        
        conn.close()
        
        if df.empty:
            return None
        
        df = df.sort_values('date')
        
        # 根据因子名称计算
        if factor_name == "momentum_20d":
            return round((df['close'].iloc[0] / df['close'].iloc[19] - 1) * 100, 2) if len(df) >= 20 else None
        elif factor_name == "momentum_60d":
            return round((df['close'].iloc[0] / df['close'].iloc[59] - 1) * 100, 2) if len(df) >= 60 else None
        elif factor_name == "skewness":
            return round(df['close'].pct_change().dropna().skew(), 4)
        elif factor_name == "turnover":
            return round(df['volume'].mean(), 0)
        
        return None
    
    def get_factors_batch(self, codes: List[str], days: int = 60) -> List[Dict]:
        """批量获取因子"""
        results = []
        for code in codes:
            factors = self.get_factors(code, days)
            if "error" not in factors:
                results.append(factors)
        return results
    
    def screen_stocks(self, criteria: Dict) -> List[Dict]:
        """选股筛选"""
        conn = self._get_conn()
        
        # 简化筛选
        df = pd.read_sql_query('''
            SELECT ts_code, date, close, volume
            FROM stock_daily
            WHERE date = (SELECT MAX(date) FROM stock_daily)
            LIMIT 100
        ''', conn)
        
        conn.close()
        
        results = []
        for _, row in df.iterrows():
            # 简化筛选条件
            if criteria.get("min_price") and row['close'] < criteria["min_price"]:
                continue
            if criteria.get("max_price") and row['close'] > criteria["max_price"]:
                continue
            
            results.append({
                "code": row["ts_code"],
                "close": row["close"],
                "volume": row["volume"]
            })
        
        return results


# 全局实例
factor_service = FactorService()
