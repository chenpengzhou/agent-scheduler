# -*- coding: utf-8 -*-
"""
数据类型枚举
"""
from enum import Enum


class DataType(Enum):
    """支持的数据类型"""
    OHLCV = "ohlcv"             # 开盘/最高/最低/收盘/成交量
    DAILY_BASIC = "daily_basic"  # 日线基础数据
    FINANCIAL = "financial"      # 财务数据
    ADJUSTMENT = "adjustment"    # 复权数据


class SaveMode(Enum):
    """数据保存模式"""
    UPSERT = "upsert"           # 存在则更新，不存在则插入
    REPLACE = "replace"         # 全量替换
    APPEND = "append"           # 仅追加


# 导出所有类型供外部使用
__all__ = ['DataType', 'SaveMode']
