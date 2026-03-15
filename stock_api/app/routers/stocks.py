# -*- coding: utf-8 -*-
"""
股票路由 - 修复版
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api", tags=["股票数据"])


def get_current_user(request: Request) -> dict:
    """获取当前用户"""
    return request.state.user


def normalize_code(code: str) -> str:
    """标准化股票代码"""
    if '.' not in code:
        return f"{code}.SH" if code.startswith('6') else f"{code}.SZ"
    return code


@router.get("/quote")
async def get_quote(
    code: str = Query(..., description="股票代码"),
    date: Optional[str] = Query(None, description="日期 YYYYMMDD"),
    current_user: dict = Depends(get_current_user)
):
    """单股查询"""
    from app.utils.db import get_stock_connection
    
    code = normalize_code(code)
    
    if not date:
        from datetime import datetime
        date = datetime.now().strftime('%Y%m%d')
    
    conn = get_stock_connection()
    cursor = conn.cursor()
    
    # 参数化查询
    try:
        cursor.execute('''
            SELECT ts_code, date, open, high, low, close, vol, volume, amount
            FROM stock_daily
            WHERE ts_code = ? AND date = ?
        ''', (code, date))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "code": row["ts_code"],
                "date": row["date"],
                "open": float(row["open"] or 0),
                "high": float(row["high"] or 0),
                "low": float(row["low"] or 0),
                "close": float(row["close"] or 0),
                "volume": float(row["vol"] or row["volume"] or 0),
                "amount": float(row["amount"] or 0),
                "source": "local"
            }
    except Exception as e:
        pass
    
    raise HTTPException(status_code=404, detail=f"未找到股票 {code} 的数据")


@router.get("/quotes")
async def get_quotes(
    codes: str = Query(..., description="股票代码列表，逗号分隔"),
    date: Optional[str] = Query(None, description="日期 YYYYMMDD"),
    current_user: dict = Depends(get_current_user)
):
    """批量查询 - 使用IN语句优化"""
    code_list = [normalize_code(c.strip()) for c in codes.split(',') if c.strip()]
    
    if len(code_list) > 100:
        raise HTTPException(status_code=400, detail="最多支持100只股票")
    
    from app.utils.db import get_stock_connection
    from datetime import datetime
    
    if not date:
        date = datetime.now().strftime('%Y%m%d')
    
    conn = get_stock_connection()
    cursor = conn.cursor()
    
    # 使用 IN 语句批量查询
    placeholders = ','.join(['?'] * len(code_list))
    query = f'''
        SELECT ts_code, date, open, high, low, close, vol, volume, amount
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
                "volume": float(row["vol"] or row["volume"] or 0),
                "amount": float(row["amount"] or 0),
                "source": "local"
            })
    except:
        results = []
    
    conn.close()
    
    return {
        "count": len(results),
        "data": results
    }


@router.get("/stocks")
async def get_stocks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="搜索代码或名称"),
    current_user: dict = Depends(get_current_user)
):
    """股票列表"""
    from app.utils.db import get_stock_connection
    
    conn = get_stock_connection()
    cursor = conn.cursor()
    
    # 从stock_daily表获取列表
    if search:
        where_clause = "WHERE ts_code LIKE ?"
        params = [f"%{search}%"]
    else:
        where_clause = ""
        params = []
    
    # 获取总数
    cursor.execute(f"SELECT COUNT(DISTINCT ts_code) as total FROM stock_daily {where_clause}", params)
    total = cursor.fetchone()["total"]
    
    # 获取列表
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
    
    # 模拟股票名称映射
    name_map = {
        "600000.SH": "浦发银行",
        "600036.SH": "招商银行",
        "600519.SH": "贵州茅台",
        "601318.SH": "中国平安",
        "000001.SZ": "平安银行",
        "000002.SZ": "万科A",
    }
    
    return {
        "page": page,
        "page_size": page_size,
        "total": total or 0,
        "pages": (total + page_size - 1) // page_size if total else 0,
        "data": [{"code": row["ts_code"], "name": name_map.get(row["ts_code"], row["ts_code"].split('.')[0])} for row in rows]
    }


@router.get("/stocks/{code}")
async def get_stock_detail(
    code: str,
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user)
):
    """股票详情"""
    from app.utils.db import get_stock_connection
    
    code = normalize_code(code)
    
    conn = get_stock_connection()
    cursor = conn.cursor()
    
    # 参数化查询
    cursor.execute('''
        SELECT date, open, high, low, close, volume
        FROM stock_daily
        WHERE ts_code = ?
        ORDER BY date DESC
        LIMIT ?
    ''', (code, days))
    
    rows = cursor.fetchall()
    
    # 获取基本信息
    cursor.execute("SELECT name FROM stock WHERE ts_code = ? LIMIT 1", (code,))
    name_row = cursor.fetchone()
    
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
    
    # 计算涨跌幅
    pct_chg = 0
    if len(history) > 1:
        latest_close = history[0]["close"]
        prev_close = history[1]["close"]
        if prev_close:
            pct_chg = ((latest_close - prev_close) / prev_close * 100)
    
    return {
        "code": code,
        "name": name_row["name"] if name_row else "",
        "latest": history[0],
        "pct_chg": round(pct_chg, 2),
        "history": history
    }


@router.get("/stocks/search")
async def search_stocks(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """股票搜索"""
    from app.utils.db import get_stock_connection
    
    conn = get_stock_connection()
    cursor = conn.cursor()
    
    # 参数化查询
    cursor.execute('''
        SELECT DISTINCT ts_code, name
        FROM stock
        WHERE ts_code LIKE ? OR name LIKE ?
        LIMIT ?
    ''', (f"%{q}%", f"%{q}%", limit))
    
    rows = cursor.fetchall()
    
    if not rows:
        cursor.execute('''
            SELECT DISTINCT ts_code
            FROM stock_daily
            WHERE ts_code LIKE ?
            LIMIT ?
        ''', (f"%{q}%", limit))
        rows = [{"ts_code": row["ts_code"], "name": ""} for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "data": [{"code": row["ts_code"], "name": row.get("name", "")} for row in rows]
    }
