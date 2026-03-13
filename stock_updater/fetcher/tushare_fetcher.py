# -*- coding: utf-8 -*-
"""
Tushare 数据获取器
"""
import os
import time
from datetime import date, timedelta
from typing import List, Dict
from .base import StockDataFetcher
from ..models import DataType


class TushareFetcher(StockDataFetcher):
    """Tushare Pro API 数据获取器"""
    
    def __init__(self, api_token: str = None, rate_limit: float = 5.0):
        self.api_token = api_token or os.environ.get('TUSHARE_TOKEN', '')
        self.rate_limit = rate_limit
        self._last_call_time = 0
        self._pro = None
        
        if self.api_token:
            self._init_api()
    
    def _init_api(self):
        """初始化 Tushare API"""
        try:
            import tushare as ts
            ts.set_token(self.api_token)
            self._pro = ts.pro_api()
        except ImportError:
            print("⚠️ 请安装 tushare: pip install tushare")
        except Exception as e:
            print(f"⚠️ Tushare API 初始化失败: {e}")
    
    @property
    def name(self) -> str:
        return "tushare"
    
    def _rate_limit_wait(self):
        """速率限制等待"""
        min_interval = 1.0 / self.rate_limit
        elapsed = time.time() - self._last_call_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_call_time = time.time()
    
    def fetch(self, 
              stock_code: str, 
              data_type: DataType,
              start_date: date,
              end_date: date) -> List[Dict]:
        """获取指定股票数据"""
        if not self._pro:
            raise RuntimeError("Tushare API 未初始化")
        
        self._rate_limit_wait()
        
        # 标准化股票代码
        ts_code = stock_code
        if '.' not in ts_code:
            if ts_code.startswith('6'):
                ts_code = f"{ts_code}.SH"
            else:
                ts_code = f"{ts_code}.SZ"
        
        try:
            if data_type == DataType.OHLCV:
                return self._fetch_daily(ts_code, start_date, end_date)
            elif data_type == DataType.DAILY_BASIC:
                return self._fetch_daily_basic(ts_code, start_date, end_date)
            else:
                raise ValueError(f"不支持的数据类型: {data_type}")
        except Exception as e:
            print(f"❌ 获取 {stock_code} 数据失败: {e}")
            return []
    
    def _fetch_daily(self, ts_code: str, start_date: date, end_date: date) -> List[Dict]:
        """获取日线数据"""
        records = []
        
        # Tushare 每次最多获取 1800 条，需要分页获取
        current_date = start_date
        while current_date <= end_date:
            # 每次获取约 180 天的数据
            period_end = min(current_date + timedelta(days=180), end_date)
            
            try:
                df = self._pro.daily(
                    ts_code=ts_code,
                    start_date=current_date.strftime('%Y%m%d'),
                    end_date=period_end.strftime('%Y%m%d')
                )
                
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        records.append({
                            'stock_code': row['ts_code'],
                            'trade_date': row['trade_date'],
                            'open': float(row['open']),
                            'high': float(row['high']),
                            'low': float(row['low']),
                            'close': float(row['close']),
                            'volume': float(row['vol']),
                            'amount': float(row.get('amount', 0))
                        })
            except Exception as e:
                print(f"⚠️ API 调用失败: {e}")
            
            current_date = period_end + timedelta(days=1)
        
        return records
    
    def _fetch_daily_basic(self, ts_code: str, start_date: date, end_date: date) -> List[Dict]:
        """获取日线基础数据"""
        records = []
        
        current_date = start_date
        while current_date <= end_date:
            period_end = min(current_date + timedelta(days=180), end_date)
            
            try:
                df = self._pro.daily_basic(
                    ts_code=ts_code,
                    start_date=current_date.strftime('%Y%m%d'),
                    end_date=period_end.strftime('%Y%m%d')
                )
                
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        records.append({
                            'stock_code': row['ts_code'],
                            'trade_date': row['trade_date'],
                            'turn_over_rate_f': row.get('turn_over_rate_f'),
                            'turn_over_rate': row.get('turn_over_rate'),
                            'volume_ratio': row.get('volume_ratio'),
                            'pe': row.get('pe'),
                            'pb': row.get('pb'),
                            'ps': row.get('ps'),
                            'dv_ratio': row.get('dv_ratio'),
                            'total_share': row.get('total_share'),
                            'float_share': row.get('float_share'),
                            'free_share': row.get('free_share'),
                            'total_mv': row.get('total_mv'),
                            'circ_mv': row.get('circ_mv')
                        })
            except Exception as e:
                print(f"⚠️ API 调用失败: {e}")
            
            current_date = period_end + timedelta(days=1)
        
        return records
    
    def fetch_batch(self, 
                    stock_codes: List[str],
                    data_type: DataType,
                    start_date: date,
                    end_date: date) -> Dict[str, List[Dict]]:
        """批量获取多只股票数据"""
        results = {}
        
        for i, code in enumerate(stock_codes):
            print(f"  [{i+1}/{len(stock_codes)}] 获取 {code}...")
            
            records = self.fetch(code, data_type, start_date, end_date)
            results[code] = records
            
            # 避免请求过快
            if i < len(stock_codes) - 1:
                time.sleep(0.2)
        
        return results
    
    def test_connection(self) -> bool:
        """测试连接"""
        if not self._pro:
            return False
        
        try:
            # 尝试获取交易日历
            df = self._pro.trade_cal(exchange='SSE', start_date=date.today().strftime('%Y%m%d'),
                                     end_date=date.today().strftime('%Y%m%d'))
            return df is not None and not df.empty
        except Exception:
            return False


class AkShareFetcher(StockDataFetcher):
    """AkShare 免费 API 数据获取器（备选）"""
    
    def __init__(self):
        self._ak = None
        try:
            import akshare as ak
            self._ak = ak
        except ImportError:
            print("⚠️ 请安装 akshare: pip install akshare")
    
    @property
    def name(self) -> str:
        return "akshare"
    
    def fetch(self, 
              stock_code: str, 
              data_type: DataType,
              start_date: date,
              end_date: date) -> List[Dict]:
        """获取数据"""
        if not self._ak:
            raise RuntimeError("AkShare 未安装")
        
        if data_type == DataType.OHLCV:
            return self._fetch_stock_zh_a_hist(stock_code, start_date, end_date)
        return []
    
    def _fetch_stock_zh_a_hist(self, stock_code: str, start_date: date, 
                               end_date: date) -> List[Dict]:
        """获取 A 股历史数据"""
        try:
            # 标准化代码
            symbol = stock_code.replace('.SZ', '').replace('.SH', '')
            
            df = self._ak.stock_zh_a_hist(
                symbol=symbol,
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d'),
                adjust=""
            )
            
            if df is None or df.empty:
                return []
            
            records = []
            for _, row in df.iterrows():
                records.append({
                    'stock_code': stock_code,
                    'trade_date': row['日期'].replace('-', ''),
                    'open': float(row['开盘']),
                    'high': float(row['最高']),
                    'low': float(row['最低']),
                    'close': float(row['收盘']),
                    'volume': float(row['成交量']),
                    'amount': float(row['成交额'])
                })
            
            return records
        except Exception as e:
            print(f"⚠️ AkShare 获取失败: {e}")
            return []
    
    def fetch_batch(self, 
                    stock_codes: List[str],
                    data_type: DataType,
                    start_date: date,
                    end_date: date) -> Dict[str, List[Dict]]:
        results = {}
        for code in stock_codes:
            results[code] = self.fetch(code, data_type, start_date, end_date)
        return results
