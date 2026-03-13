# -*- coding: utf-8 -*-
"""
账户管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/account", tags=["账户管理"])


def get_current_user(request: Request) -> dict:
    return request.state.user


# ===== 账户操作 =====
@router.get("")
async def get_account(current_user: dict = Depends(get_current_user)):
    """获取账户信息"""
    from app.services.account_service import account_service
    return account_service.get_account(1)


@router.get("/summary")
async def get_account_summary(current_user: dict = Depends(get_current_user)):
    """获取账户总览"""
    from app.services.account_service import account_service
    return account_service.get_account_summary()


@router.put("")
async def update_account(
    name: Optional[str] = None,
    initial_capital: Optional[float] = None,
    cash: Optional[float] = None,
    current_user: dict = Depends(get_current_user)
):
    """更新账户"""
    from app.services.account_service import account_service
    
    updates = {}
    if name:
        updates['name'] = name
    if initial_capital:
        updates['initial_capital'] = initial_capital
    if cash is not None:
        updates['cash'] = cash
    
    success = account_service.update_account(1, **updates)
    
    if not success:
        raise HTTPException(status_code=400, detail="更新失败")
    
    return {"message": "账户已更新"}


# ===== 交易记录 =====
@router.get("/trades")
async def get_trades(
    ts_code: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """获取交易记录"""
    from app.services.account_service import account_service
    return account_service.get_trades(ts_code, limit)


@router.post("/trades")
async def add_trade(
    ts_code: str,
    name: str,
    action: str,
    quantity: int,
    price: float,
    trade_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """添加交易记录"""
    from app.services.account_service import account_service
    
    if action not in ['buy', 'sell']:
        raise HTTPException(status_code=400, detail="action必须是buy或sell")
    
    return account_service.add_trade(ts_code, name, action, quantity, price, trade_date)
