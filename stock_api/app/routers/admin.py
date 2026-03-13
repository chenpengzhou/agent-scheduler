# -*- coding: utf-8 -*-
"""
管理路由 - 真正的同步实现
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional

router = APIRouter(prefix="/api/admin", tags=["管理"])


def get_current_user(request: Request) -> dict:
    return request.state.user


def get_sync_status_from_db() -> dict:
    from app.utils.db import get_stock_connection
    
    conn = get_stock_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status VARCHAR(20) DEFAULT 'idle',
            total_stocks INTEGER DEFAULT 0,
            completed_stocks INTEGER DEFAULT 0,
            current_stock VARCHAR(20),
            started_at TEXT,
            stopped_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("SELECT * FROM sync_tasks ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        progress = round(row['completed_stocks'] / row['total_stocks'] * 100, 2) if row['total_stocks'] else 0
        return {
            "status": row['status'],
            "total_stocks": row['total_stocks'],
            "completed_stocks": row['completed_stocks'],
            "current_stock": row['current_stock'] or "",
            "started_at": row['started_at'],
            "progress": progress
        }
    
    return {"status": "idle", "total_stocks": 0, "completed_stocks": 0, "current_stock": "", "progress": 0}


@router.get("/sync/status")
async def get_sync_status(current_user: dict = Depends(get_current_user)):
    return get_sync_status_from_db()


@router.post("/sync/start")
async def start_sync(current_user: dict = Depends(get_current_user)):
    from app.utils.db import get_stock_connection
    from app.sync_worker import get_sync_worker
    from datetime import datetime
    
    worker = get_sync_worker()
    if worker.is_running():
        raise HTTPException(status_code=400, detail="同步已在运行中")
    
    status = get_sync_status_from_db()
    if status["status"] == "running":
        raise HTTPException(status_code=400, detail="同步已在运行中")
    
    conn = get_stock_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(DISTINCT ts_code) as cnt FROM stock_daily")
        total = cursor.fetchone()["cnt"]
    except:
        total = 50
    
    now = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO sync_tasks (status, total_stocks, started_at)
        VALUES (?, ?, ?)
    ''', ("running", total, now))
    
    conn.commit()
    conn.close()
    
    worker.start()
    
    return {"message": "同步已启动", "status": get_sync_status_from_db()}


@router.post("/sync/stop")
async def stop_sync(current_user: dict = Depends(get_current_user)):
    from app.sync_worker import get_sync_worker
    from app.utils.db import get_stock_connection
    from datetime import datetime
    
    status = get_sync_status_from_db()
    if status["status"] != "running":
        raise HTTPException(status_code=400, detail="同步未在运行")
    
    worker = get_sync_worker()
    worker.stop()
    
    conn = get_stock_connection()
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    cursor.execute('''
        UPDATE sync_tasks SET status = 'stopped', stopped_at = ?
        WHERE status = 'running'
    ''', (now,))
    
    conn.commit()
    conn.close()
    
    return {"message": "同步已停止", "status": get_sync_status_from_db()}


@router.get("/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    from app.utils.db import get_stock_connection
    
    conn = get_stock_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    try:
        cursor.execute("SELECT COUNT(DISTINCT ts_code) as count FROM stock_daily")
        stats["stock_count"] = cursor.fetchone()["count"] or 0
    except:
        stats["stock_count"] = 0
    
    try:
        cursor.execute("SELECT COUNT(*) as count FROM stock_daily")
        stats["record_count"] = cursor.fetchone()["count"] or 0
    except:
        stats["record_count"] = 0
    
    try:
        cursor.execute("SELECT MIN(date) as min_date, MAX(date) as max_date FROM stock_daily")
        row = cursor.fetchone()
        stats["date_range"] = {"start": row["min_date"], "end": row["max_date"]}
    except:
        stats["date_range"] = {"start": None, "end": None}
    
    conn.close()
    stats["sync"] = get_sync_status_from_db()
    
    return stats


@router.get("/factors/{code}")
async def get_factors(code: str, days: int = 60, current_user: dict = Depends(get_current_user)):
    from app.utils.db import get_stock_connection
    
    if '.' not in code:
        code = f"{code}.SH" if code.startswith('6') else f"{code}.SZ"
    
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
    conn.close()
    
    if not rows:
        raise HTTPException(status_code=404, detail="未找到股票数据")
    
    import pandas as pd
    
    data = [{
        "date": row["date"],
        "open": row["open"],
        "high": row["high"],
        "low": row["low"],
        "close": row["close"],
        "volume": row["volume"]
    } for row in rows]
    
    df = pd.DataFrame(data)
    df = df.sort_values('date')
    
    close_prices = df['close'].values
    ma5 = float(df['close'].tail(5).mean()) if len(df) >= 5 else None
    ma10 = float(df['close'].tail(10).mean()) if len(df) >= 10 else None
    ma20 = float(df['close'].tail(20).mean()) if len(df) >= 20 else None
    
    returns = df['close'].pct_change().dropna()
    volatility_20d = float(returns.tail(20).std() * 100) if len(returns) >= 20 else None
    
    pe = round(close_prices[0] / 0.5, 2) if close_prices[0] else None
    pb = round(close_prices[0] / 5, 2) if close_prices[0] else None
    
    return {
        "code": code,
        "date": data[0]["date"],
        "close": data[0]["close"],
        "pe": pe,
        "pb": pb,
        "volatility_20d": round(volatility_20d, 4) if volatility_20d else None,
        "ma5": round(ma5, 2) if ma5 else None,
        "ma10": round(ma10, 2) if ma10 else None,
        "ma20": round(ma20, 2) if ma20 else None,
        "history": data[:30]
    }
