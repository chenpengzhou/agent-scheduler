# -*- coding: utf-8 -*-
"""
股票路由 - API Key认证版
支持 Bearer Token 和 X-API-Key 认证
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query, Header, Response
from pydantic import BaseModel
from typing import Optional, List
import time

from app.api_auth import get_auth_result, AuthResult, require_permission, record_api_usage
from app.services.api_key_service import api_key_service

router = APIRouter(prefix="/api", tags=["股票数据"])


def normalize_code(code: str) -> str:
    """标准化股票代码"""
    if '.' not in code:
        return f"{code}.SH" if code.startswith('6') else f"{code}.SZ"
    return code


def require_stocks_read():
    """股票读取权限"""
    return require_permission("stocks:read")


@router.get("/quote")
async def get_quote(
    code: str = Query(..., description="股票代码"),
    date: Optional[str] = Query(None, description="日期 YYYYMMDD"),
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    response: Response = None
):
    """单股查询 - 需要 stocks:read 权限"""
    start_time = time.time()
    
    auth = get_auth_result(authorization, x_api_key)
    if not auth.has_permission("stocks:read"):
        raise HTTPException(status_code=403, detail="需要 stocks:read 权限")
    
    code = normalize_code(code)
    
    if not date:
        from datetime import datetime
        date = datetime.now().strftime('%Y%m%d')
    
    conn = get_stock_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT ts_code, date, open, high, low, close, volume, amount
            FROM stock_daily
            WHERE ts_code = ? AND date = ?
        ''', (code, date))
        
        row = cursor.fetchone()
        
        if row:
            result = {
                "code": row["ts_code"],
                "date": row["date"],
                "open": float(row["open"] or 0),
                "high": float(row["high"] or 0),
                "low": float(row["low"] or 0),
                "close": float(row["close"] or 0),
                "volume": float(row["volume"] or 0),
                "amount": float(row["amount"] or 0),
                "source": "local"
            }
            conn.close()
            
            # 记录使用量
            if auth.key_id:
                elapsed_ms = int((time.time() - start_time) * 1000)
                api_key_service.record_usage(auth.key_id, "/api/quote", "GET", 200, elapsed_ms)
            
            return result
    except Exception as e:
        pass
    
    conn.close()
    raise HTTPException(status_code=404, detail=f"未找到股票 {code} 的数据")


@router.get("/quotes")
async def get_quotes(
    codes: str = Query(..., description="股票代码列表，逗号分隔"),
    date: Optional[str] = Query(None, description="日期 YYYYMMDD"),
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    response: Response = None
):
    """批量查询 - 需要 stocks:read 权限"""
    start_time = time.time()
    
    auth = get_auth_result(authorization, x_api_key)
    if not auth.has_permission("stocks:read"):
        raise HTTPException(status_code=403, detail="需要 stocks:read 权限")
    
    code_list = [normalize_code(c.strip()) for c in codes.split(',') if c.strip()]
    
    if len(code_list) > 100:
        raise HTTPException(status_code=400, detail="最多支持100只股票")
    
    from datetime import datetime
    
    if not date:
        date = datetime.now().strftime('%Y%m%d')
    
    conn = get_stock_connection()
    cursor = conn.cursor()
    
    placeholders = ','.join(['?'] * len(code_list))
    query = f'''
        SELECT ts_code, date, open, high, low, close, volume, amount
        FROM stock_daily
        WHERE ts_code IN ({placeholders}) AND date = ?
    '''
    
    try:
        cursor.execute(query, code_list + [date])
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "code": row["ts_code"],
                "date": row["date"],
                "open": float(row["open"] or 0),
                "high": float(row["high"] or 0),
                "low": float(row["low"] or 0),
                "close": float(row["close"] or 0),
                "volume": float(row["volume"] or 0),
                "amount": float(row["amount"] or 0),
                "source": "local"
            })
    except:
        results = []
    
    conn.close()
    
    # 记录使用量
    if auth.key_id:
        elapsed_ms = int((time.time() - start_time) * 1000)
        api_key_service.record_usage(auth.key_id, "/api/quotes", "GET", 200, elapsed_ms)
    
    return {
        "count": len(results),
        "data": results
    }


@router.get("/stocks")
async def get_stocks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="搜索代码或名称"),
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    response: Response = None
):
    """股票列表 - 需要 stocks:read 权限"""
    start_time = time.time()
    
    auth = get_auth_result(authorization, x_api_key)
    if not auth.has_permission("stocks:read"):
        raise HTTPException(status_code=403, detail="需要 stocks:read 权限")
    
    conn = get_stock_connection()
    cursor = conn.cursor()
    
    if search:
        where_clause = "WHERE ts_code LIKE ?"
        params = [f"%{search}%"]
    else:
        where_clause = ""
        params = []
    
    cursor.execute(f"SELECT COUNT(DISTINCT ts_code) as total FROM stock_daily {where_clause}", params)
    total = cursor.fetchone()["total"]
    
    offset = (page - 1) * page_size
    
    query = f'''
        SELECT DISTINCT ts_code
        FROM stock_daily {where_clause}
        ORDER BY ts_code
        LIMIT ? OFFSET ?
    '''
    cursor.execute(query, params + [page_size, offset])
    rows = cursor.fetchall()
    
    conn.close()
    
    name_map = {
        "600000.SH": "浦发银行",
        "600036.SH": "招商银行",
        "600519.SH": "贵州茅台",
        "601318.SH": "中国平安",
        "000001.SZ": "平安银行",
        "000002.SZ": "万科A",
    }
    
    # 记录使用量
    if auth.key_id:
        elapsed_ms = int((time.time() - start_time) * 1000)
        api_key_service.record_usage(auth.key_id, "/api/stocks", "GET", 200, elapsed_ms)
    
    return {
        "page": page,
        "page_size": page_size,
        "total": total or 0,
        "pages": (total + page_size - 1) // page_size if total else 0,
        "data": [{"code": row["ts_code"], "name": name_map.get(row["ts_code"], row["ts_code"].split('.')[0])} for row in rows]
    }


@router.get("/stocks/search")
async def search_stocks(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50),
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    response: Response = None
):
    """股票搜索 - 需要 stocks:read 权限"""
    start_time = time.time()
    
    auth = get_auth_result(authorization, x_api_key)
    if not auth.has_permission("stocks:read"):
        raise HTTPException(status_code=403, detail="需要 stocks:read 权限")
    
    conn = get_stock_connection()
    cursor = conn.cursor()
    
    search_pattern = f"%{q}%"
    cursor.execute('''
        SELECT DISTINCT ts_code
        FROM stock_daily
        WHERE ts_code LIKE ?
        LIMIT ?
    ''', (search_pattern, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return {"data": []}
    
    name_map = {
        "600000.SH": "浦发银行",
        "600036.SH": "招商银行",
        "600519.SH": "贵州茅台",
        "601318.SH": "中国平安",
        "000001.SZ": "平安银行",
        "000002.SZ": "万科A",
    }
    
    # 记录使用量
    if auth.key_id:
        elapsed_ms = int((time.time() - start_time) * 1000)
        api_key_service.record_usage(auth.key_id, "/api/stocks/search", "GET", 200, elapsed_ms)
    
    return {
        "data": [{"code": row["ts_code"], "name": name_map.get(row["ts_code"], row["ts_code"].split('.')[0])} for row in rows]
    }


@router.get("/stocks/{code}")
async def get_stock_detail(
    code: str,
    days: int = Query(30, ge=1, le=365),
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    response: Response = None
):
    """股票详情 - 需要 stocks:read 权限"""
    start_time = time.time()
    
    auth = get_auth_result(authorization, x_api_key)
    if not auth.has_permission("stocks:read"):
        raise HTTPException(status_code=403, detail="需要 stocks:read 权限")
    
    code = normalize_code(code)
    
    conn = get_stock_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT date, open, high, low, close, volume
        FROM stock_daily
        WHERE ts_code = ?
        ORDER BY date DESC
        LIMIT ?
    ''', (code, days))
    
    rows = cursor.fetchall()
    
    name_map = {
        "600000.SH": "浦发银行",
        "600036.SH": "招商银行",
        "600519.SH": "贵州茅台",
        "601318.SH": "中国平安",
        "000001.SZ": "平安银行",
        "000002.SZ": "万科A",
        "000333.SZ": "美的集团",
        "600030.SH": "中信证券",
        "601166.SH": "兴业银行",
        "600016.SH": "民生银行",
    }
    
    conn.close()
    
    if not rows:
        raise HTTPException(status_code=404, detail="未找到股票数据")
    
    history = [{
        "date": row["date"],
        "open": float(row["open"] or 0),
        "high": float(row["high"] or 0),
        "low": float(row["low"] or 0),
        "close": float(row["close"] or 0),
        "volume": float(row["volume"] or 0)
    } for row in rows]
    
    pct_chg = 0
    if len(history) > 1:
        latest_close = history[0]["close"]
        prev_close = history[1]["close"]
        if prev_close:
            pct_chg = ((latest_close - prev_close) / prev_close * 100)
    
    # 记录使用量
    if auth.key_id:
        elapsed_ms = int((time.time() - start_time) * 1000)
        api_key_service.record_usage(auth.key_id, f"/api/stocks/{code}", "GET", 200, elapsed_ms)
    
    return {
        "code": code,
        "name": name_map.get(code, code.split('.')[0]),
        "latest": history[0],
        "pct_chg": round(pct_chg, 2),
        "history": history
    }


# 辅助函数
def get_stock_connection():
    """获取股票数据库连接"""
    from app.utils.db import get_connection
    import os
    STOCK_DB_PATH = os.environ.get('STOCK_DB_PATH', os.path.expanduser("~/.openclaw/data/stock.db"))
    return get_connection(STOCK_DB_PATH)