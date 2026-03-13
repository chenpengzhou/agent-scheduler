# -*- coding: utf-8 -*-
"""
持仓管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/positions", tags=["持仓管理"])


def get_current_user(request: Request) -> dict:
    return request.state.user


class PositionRequest(BaseModel):
    ts_code: str
    name: str
    quantity: int
    price: float
    action: str = "buy"


class PriceUpdateRequest(BaseModel):
    current_price: float


class PricesUpdateRequest(BaseModel):
    prices: dict


# ===== 持仓操作 =====
@router.get("")
async def get_positions(current_user: dict = Depends(get_current_user)):
    """获取所有持仓"""
    from app.services.position_service import position_service
    return position_service.get_positions()


@router.get("/summary")
async def get_position_summary(current_user: dict = Depends(get_current_user)):
    """获取持仓汇总"""
    from app.services.position_service import position_service
    return position_service.get_position_summary()


@router.get("/{ts_code}")
async def get_position(ts_code: str, current_user: dict = Depends(get_current_user)):
    """获取单个持仓"""
    from app.services.position_service import position_service
    position = position_service.get_position(ts_code)
    
    if not position:
        raise HTTPException(status_code=404, detail="持仓不存在")
    
    return position


@router.post("")
async def add_position(req: PositionRequest, current_user: dict = Depends(get_current_user)):
    """添加持仓"""
    from app.services.position_service import position_service
    return position_service.add_position(req.ts_code, req.name, req.quantity, req.price, req.action)


@router.put("/{ts_code}/price")
async def update_price(ts_code: str, req: PriceUpdateRequest, current_user: dict = Depends(get_current_user)):
    """更新持仓价格"""
    from app.services.position_service import position_service
    success = position_service.update_price(ts_code, req.current_price)
    
    if not success:
        raise HTTPException(status_code=404, detail="持仓不存在")
    
    return {"message": "价格已更新"}


@router.post("/refresh-prices")
async def refresh_prices(req: PricesUpdateRequest, current_user: dict = Depends(get_current_user)):
    """批量刷新价格"""
    from app.services.position_service import position_service
    count = position_service.update_all_prices(req.prices)
    return {"message": f"已更新 {count} 只股票"}


@router.delete("/{ts_code}")
async def close_position(ts_code: str, current_user: dict = Depends(get_current_user)):
    """平仓"""
    from app.services.position_service import position_service
    success = position_service.close_position(ts_code)
    
    if not success:
        raise HTTPException(status_code=404, detail="持仓不存在")
    
    return {"message": "已平仓"}
