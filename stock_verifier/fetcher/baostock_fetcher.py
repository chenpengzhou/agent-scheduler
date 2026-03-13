# -*- coding: utf-8 -*-
"""
Baostock 数据获取器
"""
from datetime import date
from typing import Optional, Dict
from .base import DataFetcher
from ..models import DataSource, SourceConfig


class BaostockFetcher(DataFetcher):
    """Baostock 数据获取器"""
    
    def __init__(self):
        config = SourceConfig(
            name=DataSource.BAOSTOCK,
            enabled=True,
            timeout=5.0  # 免费源特殊处理：5s超时
        )
        super().__init__(DataSource.BAOSTOCK, config)
        
        self._bs = None
        self._init_api()
    
    def _init_api(self):
        """初始化 API"""
        try:
            import baostock as bs
            self._bs = bs
            lg = bs.login()
            if lg.error_code != '0':
                print(f"⚠️ Baostock 登录失败: {lg.error_msg}")
                self.config.enabled = False
        except ImportError:
            print("⚠️ 请安装 baostock: pip install baostock")
            self.config.enabled = False
    
    def fetch(self, stock_code: str, trade_date: date) -> Optional[Dict]:
        """获取数据"""
        if not self.is_enabled or not self._bs:
            return None
        
        self._rate_limit_wait(min_interval=0.5)
        
        try:
            # 转换股票代码格式
            bs_code = self._to_baostock_code(stock_code)
            date_str = trade_date.strftime('%Y-%m-%d')
            
            rs = self._bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume,amount",
                start_date=date_str,
                end_date=date_str,
                frequency="d",
                adjustflag="3"  # 不复权
            )
            
            if rs.error_code != '0':
                self.record_failure()
                return None
            
            # 读取数据
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                self.record_failure()
                return None
            
            row = data_list[0]
            self.record_success()
            
            return {
                'stock_code': stock_code,
                'trade_date': trade_date.strftime('%Y%m%d'),
                'open': float(row[1]) if row[1] else 0,
                'high': float(row[2]) if row[2] else 0,
                'low': float(row[3]) if row[3] else 0,
                'close': float(row[4]) if row[4] else 0,
                'volume': float(row[5]) if row[5] else 0,
                'amount': float(row[6]) if row[6] else 0,
                'source': self.source_name
            }
            
        except Exception as e:
            print(f"⚠️ Baostock 获取失败: {e}")
            self.record_failure()
            return None
    
    def _to_baostock_code(self, stock_code: str) -> str:
        """转换为 Baostock 格式"""
        if '.' in stock_code:
            code, market = stock_code.split('.')
            if market == 'SH':
                return f"sh.{code}"
            else:
                return f"sz.{code}"
        elif stock_code.startswith('6'):
            return f"sh.{stock_code}"
        else:
            return f"sz.{stock_code}"
    
    def test_connection(self) -> bool:
        if not self._bs:
            return False
        try:
            rs = self._bs.query_history_k_data_plus(
                "sh.600000",
                "date,close",
                start_date=date.today().strftime('%Y-%m-%d'),
                end_date=date.today().strftime('%Y-%m-%d')
            )
            return rs.error_code == '0'
        except:
            return False
    
    def __del__(self):
        """退出时登出"""
        if self._bs:
            try:
                self._bs.logout()
            except:
                pass
