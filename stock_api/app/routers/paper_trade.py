# -*- coding: utf-8 -*-
"""
模拟交易路由
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/paper", tags=["模拟交易"])


def get_current_user(request: Request) -> dict:
    return request.state.user


class TradeRequest(BaseModel):
    code: str
    price: float
    quantity: int
    date: Optional[str] = None


# ===== 账户总览 =====
@router.get("/summary")
async def get_summary(
    prices: Optional[str] = Query(None, description="股票价格,格式:code:price,code:price"),
    current_user: dict = Depends(get_current_user)
):
    """获取账户摘要"""
    from app.services.paper_trade_service import paper_trade_service
    
    price_dict = {}
    if prices:
        for item in prices.split(','):
            if ':' in item:
                code, price = item.split(':')
                price_dict[code] = float(price)
    
    return paper_trade_service.get_summary(price_dict)


# ===== 持仓管理 =====
@router.get("/positions")
async def get_positions(
    prices: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """获取持仓列表"""
    from app.services.paper_trade_service import paper_trade_service
    
    price_dict = {}
    if prices:
        for item in prices.split(','):
            if ':' in item:
                code, price = item.split(':')
                price_dict[code] = float(price)
    
    return paper_trade_service.get_positions(price_dict)


@router.get("/positions/{code}")
async def get_position(
    code: str,
    current_user: dict = Depends(get_current_user)
):
    """获取单个持仓"""
    from app.services.paper_trade_service import paper_trade_service
    
    position = paper_trade_service.get_position(code)
    if not position:
        raise HTTPException(status_code=404, detail="持仓不存在")
    
    return position


# ===== 交易操作 =====
@router.post("/buy")
async def buy_stock(
    req: TradeRequest,
    current_user: dict = Depends(get_current_user)
):
    """买入"""
    from app.services.paper_trade_service import paper_trade_service
    
    result = paper_trade_service.buy(req.code, req.price, req.quantity, req.date)
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', '买入失败'))
    
    return result


@router.post("/sell")
async def sell_stock(
    req: TradeRequest,
    current_user: dict = Depends(get_current_user)
):
    """卖出"""
    from app.services.paper_trade_service import paper_trade_service
    
    result = paper_trade_service.sell(req.code, req.price, req.quantity, req.date)
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', '卖出失败'))
    
    return result


# ===== 交易记录 =====
@router.get("/orders")
async def get_orders(
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user)
):
    """获取订单历史"""
    from app.services.paper_trade_service import paper_trade_service
    return paper_trade_service.get_orders(limit)


@router.get("/trades")
async def get_trades(
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user)
):
    """获取成交记录"""
    from app.services.paper_trade_service import paper_trade_service
    return paper_trade_service.get_trades(limit)


# ===== 重置 =====
@router.post("/reset")
async def reset_paper_trade(
    initial_capital: Optional[float] = None,
    current_user: dict = Depends(get_current_user)
):
    """重置模拟交易"""
    from app.services.paper_trade_service import paper_trade_service
    return paper_trade_service.reset(initial_capital)
