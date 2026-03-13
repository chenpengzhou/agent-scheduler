# -*- coding: utf-8 -*-
"""
存储层基类
"""
from abc import ABC, abstractmethod
from datetime import date
from typing import List, Dict, Optional, Tuple
from ..models import DataType, SaveMode


class DataStorage(ABC):
    """数据存储抽象接口"""
    
    @abstractmethod
    def get_data_range(self, 
                       stock_code: str, 
                       data_type: DataType) -> Tuple[Optional[date], Optional[date]]:
        """获取指定股票数据的日期范围"""
        
    @abstractmethod
    def save(self, 
             data_type: DataType, 
             records: List[Dict],
             mode: SaveMode = SaveMode.UPSERT) -> int:
        """保存数据，返回保存的记录数"""
        
    @abstractmethod
    def exists(self, 
               stock_code: str, 
               data_type: DataType,
               target_date: date) -> bool:
        """检查指定日期数据是否存在"""
    
    @abstractmethod
    def get_all_stock_codes(self) -> List[str]:
        """获取所有已存在的股票代码"""
