# -*- coding: utf-8 -*-
"""
数据获取器基类
"""
from abc import ABC, abstractmethod
from datetime import date
from typing import List, Dict
from ..models import DataType


class StockDataFetcher(ABC):
    """股票数据获取器抽象基类"""
    
    @abstractmethod
    def fetch(self, 
              stock_code: str, 
              data_type: DataType,
              start_date: date,
              end_date: date) -> List[Dict]:
        """
        获取指定股票数据
        
        Args:
            stock_code: 股票代码
            data_type: 数据类型
            start_date: 起始日期
            end_date: 结束日期
            
        Returns:
            数据记录列表
        """
        pass
    
    @abstractmethod
    def fetch_batch(self, 
                    stock_codes: List[str],
                    data_type: DataType,
                    start_date: date,
                    end_date: date) -> Dict[str, List[Dict]]:
        """
        批量获取多只股票数据
        
        Args:
            stock_codes: 股票代码列表
            data_type: 数据类型
            start_date: 起始日期
            end_date: 结束日期
            
        Returns:
            {stock_code: [records]} 
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """获取器名称"""
        pass
    
    def test_connection(self) -> bool:
        """测试连接是否正常"""
        try:
            result = self.fetch("000001.SZ", DataType.OHLCV, 
                              date.today(), date.today())
            return True
        except Exception:
            return False
