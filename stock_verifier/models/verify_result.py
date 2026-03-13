# -*- coding: utf-8 -*-
"""
验证结果模型
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, Optional, List
from enum import Enum


class VerifyStatus(Enum):
    """验证状态"""
    UNKNOWN = "unknown"           # 未验证
    CONSISTENT = "consistent"     # 一致
    INCONSISTENT = "inconsistent" # 不一致
    SINGLE_SOURCE = "single"      # 单源
    ERROR = "error"               # 错误


@dataclass
class VerifyResult:
    """验证结果"""
    stock_code: str
    trade_date: date
    data_type: str
    
    # 多源数据
    sources_data: Dict[str, Optional[Dict]] = field(default_factory=dict)
    
    # 验证状态
    status: VerifyStatus = VerifyStatus.UNKNOWN
    
    # 差异信息
    diff_details: Dict[str, float] = field(default_factory=dict)  # 字段差异
    anomalies: List[str] = field(default_factory=list)
    
    # 最终采纳的数据
    final_data: Optional[Dict] = None
    
    # 验证元数据
    verified_at: datetime = None
    verify_duration_ms: int = 0
    
    def __post_init__(self):
        if self.verified_at is None:
            self.verified_at = datetime.now()
    
    @property
    def source_count(self) -> int:
        """获取到数据的源数量"""
        return sum(1 for v in self.sources_data.values() if v is not None)
    
    @property
    def has_anomaly(self) -> bool:
        """是否有异常"""
        return self.status == VerifyStatus.INCONSISTENT
