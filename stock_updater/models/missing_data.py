# -*- coding: utf-8 -*-
"""
缺失数据模型
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional
from . import DataType


@dataclass
class MissingData:
    """缺失数据记录"""
    stock_code: str              # 股票代码
    data_type: DataType          # 数据类型
    start_date: date             # 缺失起始日期
    end_date: date               # 缺失结束日期
    reason: str = ""              # 缺失原因
    
    @property
    def date_range(self) -> tuple:
        """获取缺失日期范围"""
        return (self.start_date, self.end_date)
    
    @property
    def days_count(self) -> int:
        """缺失天数"""
        return (self.end_date - self.start_date).days + 1
    
    def __repr__(self):
        return f"MissingData({self.stock_code}, {self.data_type.value}, {self.start_date}~{self.end_date}, {self.days_count}天)"
