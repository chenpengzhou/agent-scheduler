# -*- coding: utf-8 -*-
"""
验证规则模型
"""
from dataclasses import dataclass
from enum import Enum


class FieldType(Enum):
    """字段类型"""
    PRICE = "price"             # 价格类
    VOLUME = "volume"           # 成交量
    FINANCIAL = "financial"     # 财务因子


class HandlerType(Enum):
    """处理方式"""
    PRIMARY_TRUST = "primary_trust"   # 信任主源
    MAJORITY = "majority"              # 少数服从多数
    WEIGHTED = "weighted"              # 加权平均


@dataclass
class VerifyRule:
    """验证规则"""
    field: str                  # 验证字段
    field_type: FieldType       # 字段类型
    threshold: float           # 阈值
    handler: HandlerType = HandlerType.PRIMARY_TRUST


# 默认验证规则
DEFAULT_RULES = [
    # 价格类 ±0.5%
    VerifyRule("close", FieldType.PRICE, 0.005, HandlerType.PRIMARY_TRUST),
    VerifyRule("open", FieldType.PRICE, 0.005, HandlerType.PRIMARY_TRUST),
    VerifyRule("high", FieldType.PRICE, 0.005, HandlerType.PRIMARY_TRUST),
    VerifyRule("low", FieldType.PRICE, 0.005, HandlerType.PRIMARY_TRUST),
    
    # 成交量 ±10%
    VerifyRule("volume", FieldType.VOLUME, 0.10, HandlerType.MAJORITY),
    
    # 财务因子 >20%
    VerifyRule("pe", FieldType.FINANCIAL, 0.20, HandlerType.WEIGHTED),
    VerifyRule("pb", FieldType.FINANCIAL, 0.20, HandlerType.WEIGHTED),
]
