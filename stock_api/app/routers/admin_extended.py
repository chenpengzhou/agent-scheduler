# -*- coding: utf-8 -*-
"""
系统管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/admin", tags=["系统管理"])


def get_current_user(request: Request) -> dict:
    return request.state.user


# ===== 数据管理 =====
@router.get("/data/sync/status")
async def get_sync_status(current_user: dict = Depends(get_current_user)):
    """获取同步状态"""
    from app.services.data_manager import data_manager
    return data_manager.get_sync_status()


@router.post("/data/sync/start")
async def start_sync(current_user: dict = Depends(get_current_user)):
    """启动同步"""
    from app.services.data_manager import data_manager
    return data_manager.start_sync()


@router.post("/data/sync/stop")
async def stop_sync(current_user: dict = Depends(get_current_user)):
    """停止同步"""
    from app.services.data_manager import data_manager
    return data_manager.stop_sync()


@router.get("/data/quality")
async def get_quality_report(current_user: dict = Depends(get_current_user)):
    """数据质量报告"""
    from app.services.data_manager import data_manager
    return data_manager.get_quality_report()


@router.post("/data/backfill")
async def manual_backfill(
    stock_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """手动补数据"""
    from app.services.data_manager import data_manager
    return data_manager.manual_backfill(stock_code, start_date, end_date)


@router.get("/data/export")
async def export_data(
    format: str = "csv",
    stocks: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """导出数据"""
    from app.services.data_manager import data_manager
    stock_list = stocks.split(",") if stocks else None
    filepath = data_manager.export_data(format, stock_list)
    return {"filepath": filepath}


# ===== 因子计算 =====
@router.get("/factors/{code}")
async def get_factors(code: str, days: int = 60, current_user: dict = Depends(get_current_user)):
    """获取因子数据"""
    from app.services.factor_service import factor_service
    return factor_service.get_factors(code, days)


@router.get("/factors/batch")
async def get_factors_batch(
    codes: str,
    days: int = 60,
    current_user: dict = Depends(get_current_user)
):
    """批量获取因子"""
    from app.services.factor_service import factor_service
    code_list = codes.split(",")
    return factor_service.get_factors_batch(code_list, days)


@router.get("/factors/screen")
async def screen_stocks(
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    current_user: dict = Depends(get_current_user)
):
    """选股筛选"""
    from app.services.factor_service import factor_service
    criteria = {}
    if min_price:
        criteria["min_price"] = min_price
    if max_price:
        criteria["max_price"] = max_price
    return factor_service.screen_stocks(criteria)


# ===== 选股策略 =====
@router.post("/strategy/backtest")
async def backtest(
    strategy: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000,
    current_user: dict = Depends(get_current_user)
):
    """回测"""
    from app.services.strategy_service import strategy_service
    return strategy_service.backtest(strategy, start_date, end_date, initial_capital)


@router.get("/strategy/signals")
async def get_signals(
    codes: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """获取选股信号"""
    from app.services.strategy_service import strategy_service
    code_list = codes.split(",") if codes else None
    return strategy_service.get_signals(code_list)


@router.get("/strategy/recommendations")
async def get_recommendations(
    strategy: str = "low_volatility",
    top_n: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """获取持仓推荐"""
    from app.services.strategy_service import strategy_service
    return strategy_service.get_recommendations(strategy, top_n)


@router.post("/strategy/trade")
async def simulate_trade(
    code: str,
    action: str,
    quantity: int,
    price: Optional[float] = None,
    current_user: dict = Depends(get_current_user)
):
    """模拟交易"""
    from app.services.strategy_service import strategy_service
    return strategy_service.simulate_trade(code, action, quantity, price)


@router.get("/strategy/portfolio")
async def get_portfolio(
    initial_capital: float = 100000,
    current_user: dict = Depends(get_current_user)
):
    """获取模拟组合"""
    from app.services.strategy_service import strategy_service
    return strategy_service.get_portfolio(initial_capital)


# ===== 监控告警 =====
@router.get("/monitor/alerts")
async def get_alerts(current_user: dict = Depends(get_current_user)):
    """获取告警"""
    from app.services.monitor_service import monitor_service
    return monitor_service.get_all_alerts()


@router.post("/monitor/rules")
async def create_alert_rule(
    name: str,
    type: str,
    threshold: float = 5.0,
    current_user: dict = Depends(get_current_user)
):
    """创建告警规则"""
    from app.services.monitor_service import monitor_service
    return monitor_service.create_alert_rule({
        "name": name,
        "type": type,
        "threshold": threshold
    })


@router.get("/monitor/rules")
async def get_alert_rules(current_user: dict = Depends(get_current_user)):
    """获取告警规则"""
    from app.services.monitor_service import monitor_service
    return monitor_service.get_alert_rules()


# ===== 系统设置 =====
@router.get("/settings/users")
async def get_users(current_user: dict = Depends(get_current_user)):
    """获取用户列表"""
    from app.services.settings_service import settings_service
    return settings_service.get_users()


@router.post("/settings/users")
async def create_user(
    username: str,
    password: str,
    role: str = "user",
    current_user: dict = Depends(get_current_user)
):
    """创建用户"""
    from app.services.settings_service import settings_service
    return settings_service.create_user(username, password, role)


@router.get("/settings/info")
async def get_system_info(current_user: dict = Depends(get_current_user)):
    """获取系统信息"""
    from app.services.settings_service import settings_service
    return settings_service.get_system_info()


@router.get("/settings/sync-config")
async def get_sync_config(current_user: dict = Depends(get_current_user)):
    """获取同步配置"""
    from app.services.settings_service import settings_service
    return settings_service.get_sync_config()
