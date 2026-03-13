# -*- coding: utf-8 -*-
"""
数据源配置与权重
"""
from dataclasses import dataclass
from enum import Enum


class DataSource(Enum):
    """支持的数据源"""
    TUSHARE = "tushare"
    JUQING = "聚宽"           # 聚宽
    BAOSTOCK = "baostock"     # Baostock
    AKSHARE = "akshare"


# 数据源优先级权重
SOURCE_WEIGHTS = {
    DataSource.TUSHARE: 0.40,    # 40%
    DataSource.JUQING: 0.30,    # 30%
    DataSource.BAOSTOCK: 0.20,  # 20%
    DataSource.AKSHARE: 0.10,   # 10%
}

# 数据源优先级顺序（用于少数服从多数）
SOURCE_PRIORITY = [
    DataSource.TUSHARE,   # 最高优先级
    DataSource.JUQING,
    DataSource.BAOSTOCK,
    DataSource.AKSHARE,   # 最低优先级
]


@dataclass
class SourceConfig:
    """数据源配置"""
    name: DataSource
    enabled: bool = True
    timeout: float = 10.0      # 超时时间(秒)
    max_retries: int = 3     # 最大重试次数
    disabled: bool = False    # 是否被禁用（连续失败后）
    consecutive_failures: int = 0  # 连续失败次数
    
    @property
    def weight(self) -> float:
        return SOURCE_WEIGHTS.get(self.name, 0.0)


# 免费数据源特殊配置
FREE_SOURCE_CONFIG = {
    DataSource.AKSHARE: {"timeout": 5.0, "max_retries": 3},
    DataSource.BAOSTOCK: {"timeout": 5.0, "max_retries": 3},
}


# 验证阈值配置
class VerifyThreshold:
    """验证阈值"""
    PRICE = 0.005        # 价格类 ±0.5%
    VOLUME = 0.10        # 成交量 ±10%
    FINANCIAL = 0.20      # 财务类差异 >20%
