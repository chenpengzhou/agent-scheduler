# -*- coding: utf-8 -*-
"""
验证请求模型
"""
from dataclasses import dataclass
from datetime import date
from typing import List, Optional
from enum import Enum


class DataType(Enum):
    """数据类型"""
    OHLCV = "ohlcv"           # 日线行情
    DAILY_BASIC = "daily_basic"  # 日线基础


@dataclass
class VerifyRequest:
    """验证请求"""
    stock_code: str           # 股票代码
    trade_date: date         # 交易日期
    data_types: List[DataType]  # 要验证的数据类型
    force_verify: bool = False  # 是否强制验证
    
    def __post_init__(self):
        # 标准化股票代码
        if self.stock_code and '.' not in self.stock_code:
            if self.stock_code.startswith('6'):
                self.stock_code = f"{self.stock_code}.SH"
            else:
                self.stock_code = f"{self.stock_code}.SZ"
