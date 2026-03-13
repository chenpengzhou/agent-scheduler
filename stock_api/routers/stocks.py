# -*- coding: utf-8 -*-
"""
股票API路由
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List
from datetime import datetime
from models import QuoteResponse, QuotesResponse, StatusResponse, ErrorResponse
from services.stock_service import get_stock_service

router = APIRouter()


@router.get("/quote", response_model=QuoteResponse)
async def get_quote(
    code: str = Query(..., description="股票代码，如 600000 或 600000.SH")
):
    """
    单股查询
    
    GET /api/quote?code=600000
    """
    try:
        service = get_stock_service()
        
        quote = service.get_quote(code)
        
        if not quote:
            raise HTTPException(status_code=404, detail=f"未找到股票 {code} 的数据")
        
        return QuoteResponse(
            code=quote['code'],
            date=quote['date'],
            open=quote['open'],
            high=quote['high'],
            low=quote['low'],
            close=quote['close'],
            volume=quote['volume'],
            amount=quote['amount'],
            source=quote.get('source', 'local'),
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quotes", response_model=QuotesResponse)
async def get_quotes(
    codes: str = Query(..., description="股票代码列表，用逗号分隔，如 600000,000001"),
    date: str = Query(None, description="日期 YYYYMMDD")
):
    """
    批量查询
    
    GET /api/quotes?codes=600000,000001
    """
    try:
        # 解析股票代码列表
        code_list = [c.strip() for c in codes.split(',') if c.strip()]
        
        if not code_list:
            raise HTTPException(status_code=400, detail="股票代码不能为空")
        
        if len(code_list) > 100:
            raise HTTPException(status_code=400, detail="最多支持100只股票")
        
        service = get_stock_service()
        
        quotes = service.get_quotes(code_list, date)
        
        data = [
            QuoteResponse(
                code=q['code'],
                date=q['date'],
                open=q['open'],
                high=q['high'],
                low=q['low'],
                close=q['close'],
                volume=q['volume'],
                amount=q['amount'],
                source=q.get('source', 'local'),
                timestamp=datetime.now().isoformat()
            )
            for q in quotes
        ]
        
        return QuotesResponse(
            count=len(data),
            data=data,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """
    状态查询
    
    GET /api/status
    """
    try:
        service = get_stock_service()
        stats = service.get_stats()
        
        return StatusResponse(
            status="running",
            version="1.0.0",
            db_path=stats.get('db_path', ''),
            db_records=stats.get('db_records', 0),
            db_stocks=stats.get('db_stocks', 0),
            uptime="N/A"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
