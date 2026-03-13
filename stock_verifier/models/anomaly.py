# -*- coding: utf-8 -*-
"""
异常记录模型
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, Dict
from enum import Enum


class HandleStatus(Enum):
    """处理状态"""
    PENDING = "pending"          # 待处理
    DISCUSSING = "discussing"    # 讨论中
    RESOLVED = "resolved"        # 已解决
    IGNORED = "ignored"          # 已忽略


@dataclass
class AnomalyRecord:
    """异常记录"""
    stock_code: str
    trade_date: date
    data_type: str
    
    # 可选字段
    id: Optional[int] = None
    sources_data: Dict[str, Optional[Dict]] = field(default_factory=dict)
    diff_fields: str = ""
    diff_percentage: float = 0.0
    handling_status: HandleStatus = HandleStatus.PENDING
    discussion: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
