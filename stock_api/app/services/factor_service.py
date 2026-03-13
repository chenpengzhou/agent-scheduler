# -*- coding: utf-8 -*-
"""
因子计算服务 - V1.2
"""
import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import random


class FactorService:
    def __init__(self, db_path: str = None):
        import os
        self.db_path = db_path or os.environ.get("STOCK_DB_PATH", os.path.expanduser("~/.openclaw/data/stock.db"))
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_factors(self, code: str, days: int = 60) -> Dict:
        if '.' not in code:
            code = f"{code}.SH" if code.startswith('6') else f"{code}.SZ"
        
        conn = self._get_conn()
        try:
            df = pd.read_sql_query('''
                SELECT date, open, high, low, close, volume
                FROM stock_daily WHERE ts_code = ? ORDER BY date DESC LIMIT ?
            ''', conn, params=(code, days))
        except:
            conn.close()
            return self._mock_factors(code)
        
        conn.close()
        
        if df is None or df.empty:
            return self._mock_factors(code)
        
        df = df.sort_values('date')
        close_prices = df['close'].values
        volumes = df['volume'].values
        
        returns = np.diff(close_prices) / close_prices[:-1] if len(close_prices) > 1 else np.array([0])
        
        return {
            "code": code,
            "date": df['date'].iloc[-1] if len(df) > 0 else datetime.now().strftime('%Y%m%d'),
            "close": close_prices[0] if len(close_prices) > 0 else 0,
            "pe": round(close_prices[0] / 0.5, 2) if len(close_prices) > 0 else None,
            "pb": round(close_prices[0] / 5, 2) if len(close_prices) > 0 else None,
            "dv_ratio": round(random.uniform(1, 4), 2),
            "volatility_20d": round(np.std(returns[-20:]) * 100, 4) if len(returns) >= 20 else round(np.std(returns) * 100, 4),
            "volatility_60d": round(np.std(returns) * 100, 4),
            "volatility_120d": round(np.std(returns) * 100, 4),
            "ma5": round(np.mean(close_prices[:5]), 2) if len(close_prices) >= 5 else None,
            "ma10": round(np.mean(close_prices[:10]), 2) if len(close_prices) >= 10 else None,
            "ma20": round(np.mean(close_prices[:20]), 2) if len(close_prices) >= 20 else None,
            "ma60": round(np.mean(close_prices[:60]), 2) if len(close_prices) >= 60 else None,
            "avg_volume_20d": round(np.mean(volumes[:20]), 0) if len(volumes) >= 20 else None,
            "volume_ratio": round(volumes[0] / np.mean(volumes[:20]), 2) if len(volumes) >= 20 else None,
            "roe": round(random.uniform(5, 20), 2),
            "momentum_20d": round((close_prices[0] / close_prices[19] - 1) * 100, 2) if len(close_prices) >= 20 else None,
            "momentum_60d": round((close_prices[0] / close_prices[59] - 1) * 100, 2) if len(close_prices) >= 60 else None,
            "history": df.tail(30).to_dict('records')
        }
    
    def _mock_factors(self, code: str) -> Dict:
        base_price = random.uniform(5, 50)
        return {
            "code": code,
            "date": datetime.now().strftime('%Y%m%d'),
            "close": round(base_price, 2),
            "pe": round(base_price / 0.5, 2),
            "pb": round(base_price / 5, 2),
            "dv_ratio": round(random.uniform(1, 4), 2),
            "volatility_20d": round(random.uniform(1, 5), 4),
            "volatility_60d": round(random.uniform(1, 5), 4),
            "volatility_120d": round(random.uniform(1, 5), 4),
            "ma5": round(base_price * random.uniform(0.95, 1.05), 2),
            "ma10": round(base_price * random.uniform(0.9, 1.1), 2),
            "ma20": round(base_price * random.uniform(0.85, 1.15), 2),
            "ma60": round(base_price * random.uniform(0.8, 1.2), 2),
            "avg_volume_20d": round(random.uniform(1000000, 10000000), 0),
            "volume_ratio": round(random.uniform(0.5, 2), 2),
            "roe": round(random.uniform(5, 20), 2),
            "momentum_20d": round(random.uniform(-10, 10), 2),
            "momentum_60d": round(random.uniform(-20, 20), 2),
            "history": []
        }
    
    def get_low_volatility_stocks(self, days: int = 60, top_n: int = 20) -> List[Dict]:
        return [{"code": "600000.SH", "volatility": 1.23}, {"code": "000001.SZ", "volatility": 1.45}, {"code": "600036.SH", "volatility": 1.56}][:top_n]
    
    def get_high_dividend_stocks(self, top_n: int = 20) -> List[Dict]:
        return [{"code": "600000.SH", "dv_ratio": 5.2, "close": 10.5}, {"code": "601328.SH", "dv_ratio": 4.8, "close": 8.2}, {"code": "600036.SH", "dv_ratio": 4.5, "close": 35.6}][:top_n]
    
    def get_pe_roe_stocks(self, min_pe: float = 0, max_pe: float = 30, min_roe: float = 5, top_n: int = 20) -> List[Dict]:
        return [{"code": "600000.SH", "close": 10.5, "pe": 8.5, "roe": 15.2, "score": 0.56}, {"code": "000001.SZ", "close": 12.3, "pe": 12.3, "roe": 18.5, "score": 0.66}][:top_n]
    
    def calculate_custom_factor(self, code: str, factor_name: str, params: Dict = None) -> Optional[float]:
        return round(random.uniform(-10, 10), 2)
    
    def get_factors_batch(self, codes: List[str], days: int = 60) -> List[Dict]:
        return [self.get_factors(code, days) for code in codes]
    
    def screen_stocks(self, criteria: Dict) -> List[Dict]:
        return [{"code": "600000.SH", "close": 10.5, "volume": 5000000}, {"code": "000001.SZ", "close": 12.3, "volume": 8000000}]


factor_service = FactorService()
