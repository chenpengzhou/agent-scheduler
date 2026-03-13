# -*- coding: utf-8 -*-
"""
Tushare 数据获取器
"""
import os
import time
from datetime import date
from typing import Optional, Dict
from .base import DataFetcher
from ..models import DataSource, SourceConfig


class TushareFetcher(DataFetcher):
    """Tushare 数据获取器"""
    
    def __init__(self, api_token: str = None):
        config = SourceConfig(
            name=DataSource.TUSHARE,
            enabled=bool(api_token),
            timeout=10.0
        )
        super().__init__(DataSource.TUSHARE, config)
        
        self.api_token = api_token or os.environ.get('TUSHARE_TOKEN', '')
        self._pro = None
        
        if self.api_token:
            self._init_api()
    
    def _init_api(self):
        """初始化 API"""
        try:
            import tushare as ts
            ts.set_token(self.api_token)
            self._pro = ts.pro_api()
            self.config.enabled = True
        except ImportError:
            print("⚠️ 请安装 tushare: pip install tushare")
            self.config.enabled = False
        except Exception as e:
            print(f"⚠️ Tushare 初始化失败: {e}")
            self.config.enabled = False
    
    def fetch(self, stock_code: str, trade_date: date) -> Optional[Dict]:
        """获取数据"""
        if not self.is_enabled:
            return None
        
        self._rate_limit_wait()
        
        try:
            date_str = trade_date.strftime('%Y%m%d')
            
            df = self._pro.daily(
                ts_code=stock_code,
                trade_date=date_str
            )
            
            if df is None or df.empty:
                self.record_failure()
                return None
            
            row = df.iloc[0]
            self.record_success()
            
            return {
                'stock_code': row['ts_code'],
                'trade_date': row['trade_date'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['vol']),
                'amount': float(row.get('amount', 0)),
                'source': self.source_name
            }
            
        except Exception as e:
            print(f"⚠️ Tushare 获取失败: {e}")
            self.record_failure()
            return None
    
    def test_connection(self) -> bool:
        if not self._pro:
            return False
        try:
            df = self._pro.trade_cal(
                exchange='SSE',
                start_date=date.today().strftime('%Y%m%d'),
                end_date=date.today().strftime('%Y%m%d')
            )
            return df is not None and not df.empty
        except:
            return False
