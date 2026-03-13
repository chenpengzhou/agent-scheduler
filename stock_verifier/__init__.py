# -*- coding: utf-8 -*-
"""
股票数据多源验证模块

功能：
- 4个数据源：Tushare、聚宽、Baostock、AkShare
- 优先级权重：Tushare 40%、聚宽 30%、Baostock 20%、AkShare 10%
- 少数服从多数，Tushare有最终话语权
- 免费源特殊处理：5s超时、连续失败3次禁用

使用示例：
    python -m stock_verifier verify --stock 000001.SZ
    python -m stock_verifier batch --stocks 000001.SZ 600000.SH --days 5
    python -m stock_verifier stats
"""

from .verifier import StockDataVerifier
from .models import VerifyRequest, DataType, VerifyStatus

__version__ = "1.0.0"

__all__ = [
    'StockDataVerifier',
    'VerifyRequest',
    'DataType',
    'VerifyStatus'
]
