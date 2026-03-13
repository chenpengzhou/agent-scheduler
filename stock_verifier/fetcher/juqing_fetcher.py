# -*- coding: utf-8 -*-
"""
聚宽数据获取器
"""
import os
import json
from datetime import date
from typing import Optional, Dict
import urllib.request
import ssl
from .base import DataFetcher
from ..models import DataSource, SourceConfig


class JuqingFetcher(DataFetcher):
    """聚宽数据获取器"""
    
    def __init__(self, api_key: str = None):
        config = SourceConfig(
            name=DataSource.JUQING,
            enabled=bool(api_key),
            timeout=10.0
        )
        super().__init__(DataSource.JUQING, config)
        
        self.api_key = api_key or os.environ.get('JUQING_API_KEY', '')
        self.base_url = "https://dataapi.joinquant.com"
        
        if not self.api_key:
            print("⚠️ 未配置聚宽 API Key")
    
    def fetch(self, stock_code: str, trade_date: date) -> Optional[Dict]:
        """获取数据"""
        if not self.is_enabled:
            return None
        
        self._rate_limit_wait()
        
        try:
            # 转换股票代码格式
            jq_code = self._to_jq_code(stock_code)
            date_str = trade_date.strftime('%Y-%m-%d')
            
            # 构建请求
            method = "get_price"
            kwargs = {
                "code": jq_code,
                "date": date_str,
                "count": 1
            }
            
            params = {
                "method": method,
                "params": json.dumps(kwargs),
                "token": self.api_key
            }
            
            # 发送请求
            ssl_context = ssl.create_default_context()
            
            req = urllib.request.Request(
                self.base_url,
                data=json.dumps(params).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, 
                                       timeout=self.config.timeout,
                                       context=ssl_context) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            
            if not data or len(data) == 0:
                self.record_failure()
                return None
            
            # 解析数据
            row = data[0]
            self.record_success()
            
            return {
                'stock_code': stock_code,
                'trade_date': trade_date.strftime('%Y%m%d'),
                'open': float(row.get('open', 0)),
                'high': float(row.get('high', 0)),
                'low': float(row.get('low', 0)),
                'close': float(row.get('close', 0)),
                'volume': float(row.get('volume', 0)),
                'amount': float(row.get('amount', 0)),
                'source': self.source_name
            }
            
        except Exception as e:
            print(f"⚠️ 聚宽获取失败: {e}")
            self.record_failure()
            return None
    
    def _to_jq_code(self, stock_code: str) -> str:
        """转换为聚宽格式"""
        if '.' in stock_code:
            code, market = stock_code.split('.')
            if market == 'SH':
                return f"{code}.XSHG"
            else:
                return f"{code}.XSHE"
        return stock_code
    
    def test_connection(self) -> bool:
        if not self.is_enabled:
            return False
        try:
            result = self.fetch("000001.SZ", date.today())
            return result is not None
        except:
            return False
