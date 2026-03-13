# -*- coding: utf-8 -*-
"""
响应模型
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class QuoteResponse(BaseModel):
    """单股查询响应"""
    code: str
    name: Optional[str] = None
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    source: str
    timestamp: str


class QuotesResponse(BaseModel):
    """批量查询响应"""
    count: int
    data: List[QuoteResponse]
    timestamp: str


class StatusResponse(BaseModel):
    """状态查询响应"""
    status: str
    version: str
    db_path: str
    db_records: int
    db_stocks: int
    uptime: str


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None
    timestamp: str
