# -*- coding: utf-8 -*-
"""
数据需求模型
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List
from . import DataType


@dataclass
class DataRequirement:
    """数据需求"""
    stock_code: str              # 股票代码 (e.g., "000001.SZ")
    data_type: DataType          # 数据类型
    start_date: date             # 起始日期
    end_date: Optional[date] = None  # 结束日期 (None = 至今)
    fields: Optional[List[str]] = None  # 所需字段列表
    
    def __post_init__(self):
        # 标准化股票代码格式
        if self.stock_code and not '.' in self.stock_code:
            # 默认添加 .SZ 后缀
            if self.stock_code.startswith('6'):
                self.stock_code = f"{self.stock_code}.SH"
            else:
                self.stock_code = f"{self.stock_code}.SZ"
    
    @property
    def date_range(self) -> tuple:
        """获取日期范围"""
        return (self.start_date, self.end_date)
