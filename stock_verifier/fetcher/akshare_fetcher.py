# -*- coding: utf-8 -*-
"""
AkShare 数据获取器
"""
from datetime import date
from typing import Optional, Dict
from .base import DataFetcher
from ..models import DataSource, SourceConfig


class AkShareFetcher(DataFetcher):
    """AkShare 数据获取器"""
    
    def __init__(self):
        config = SourceConfig(
            name=DataSource.AKSHARE,
            enabled=True,
            timeout=5.0,  # 免费源特殊处理：5s超时
            max_retries=3  # 连续失败3次禁用
        )
        super().__init__(DataSource.AKSHARE, config)
        
        self._ak = None
        self._init_api()
    
    def _init_api(self):
        """初始化 API"""
        try:
            import akshare as ak
            self._ak = ak
        except ImportError:
            print("⚠️ 请安装 akshare: pip install akshare")
            self.config.enabled = False
    
    def fetch(self, stock_code: str, trade_date: date) -> Optional[Dict]:
        """获取数据"""
        if not self.is_enabled or not self._ak:
            return None
        
        self._rate_limit_wait(min_interval=1.0)
        
        try:
            # 转换代码格式
            symbol = stock_code.replace('.SZ', '').replace('.SH', '')
            
            # AkShare 需要特定日期格式
            date_str = trade_date.strftime('%Y%m%d')
            
            # 获取历史数据
            df = self._ak.stock_zh_a_hist(
                symbol=symbol,
                start_date=date_str,
                end_date=date_str,
                adjust=""
            )
            
            if df is None or df.empty:
                self.record_failure()
                return None
            
            row = df.iloc[0]
            self.record_success()
            
            return {
                'stock_code': stock_code,
                'trade_date': trade_date.strftime('%Y%m%d'),
                'open': float(row['开盘']),
                'high': float(row['最高']),
                'low': float(row['最低']),
                'close': float(row['收盘']),
                'volume': float(row['成交量']),
                'amount': float(row['成交额']),
                'source': self.source_name
            }
            
        except Exception as e:
            print(f"⚠️ AkShare 获取失败: {e}")
            self.record_failure()
            return None
    
    def test_connection(self) -> bool:
        if not self._ak:
            return False
        try:
            result = self.fetch("000001.SZ", date.today())
            return result is not None
        except:
            return False
