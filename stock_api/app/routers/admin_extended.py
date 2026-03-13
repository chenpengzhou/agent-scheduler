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


# ===== 请求模型 =====
class BacktestRequest(BaseModel):
    strategy: str
    start_date: str
    end_date: str
    initial_capital: float = 100000


class AlertRuleRequest(BaseModel):
    name: str
    type: str
    condition: Optional[str] = "gt"
    threshold: float = 5.0
    enabled: bool = True


class ScreenRequest(BaseModel):
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_pe: Optional[float] = None
    max_pe: Optional[float] = None


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
    """选股筛选 - GET方式"""
    from app.services.factor_service import factor_service
    criteria = {}
    if min_price:
        criteria["min_price"] = min_price
    if max_price:
        criteria["max_price"] = max_price
    return factor_service.screen_stocks(criteria)


@router.post("/factors/screen")
async def screen_stocks_post(req: ScreenRequest, current_user: dict = Depends(get_current_user)):
    """选股筛选 - POST方式 (JSON Body)"""
    from app.services.factor_service import factor_service
    criteria = {}
    if req.min_price:
        criteria["min_price"] = req.min_price
    if req.max_price:
        criteria["max_price"] = req.max_price
    if req.min_pe:
        criteria["min_pe"] = req.min_pe
    if req.max_pe:
        criteria["max_pe"] = req.max_pe
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
    """回测 - Query参数"""
    from app.services.strategy_service import strategy_service
    return strategy_service.backtest(strategy, start_date, end_date, initial_capital)


@router.post("/strategy/backtest/run")
async def backtest_post(req: BacktestRequest, current_user: dict = Depends(get_current_user)):
    """回测 - JSON Body (POST)"""
    from app.services.strategy_service import strategy_service
    return strategy_service.backtest(req.strategy, req.start_date, req.end_date, req.initial_capital)


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
    req: AlertRuleRequest,
    current_user: dict = Depends(get_current_user)
):
    """创建告警规则"""
    from app.services.monitor_service import monitor_service
    return monitor_service.create_alert_rule(req.dict())


@router.get("/monitor/rules")
async def get_alert_rules(enabled_only: bool = False, current_user: dict = Depends(get_current_user)):
    """获取告警规则"""
    from app.services.monitor_service import monitor_service
    return monitor_service.get_alert_rules(enabled_only)


@router.put("/monitor/rules/{rule_id}")
async def update_alert_rule(
    rule_id: int,
    name: Optional[str] = None,
    rule_type: Optional[str] = None,
    condition: Optional[str] = None,
    threshold: Optional[float] = None,
    enabled: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    """更新告警规则"""
    from app.services.monitor_service import monitor_service
    
    updates = {}
    if name:
        updates['name'] = name
    if rule_type:
        updates['type'] = rule_type
    if condition:
        updates['condition'] = condition
    if threshold is not None:
        updates['threshold'] = threshold
    if enabled is not None:
        updates['enabled'] = enabled
    
    success = monitor_service.update_alert_rule(rule_id, **updates)
    
    if not success:
        raise HTTPException(status_code=400, detail="更新失败")
    
    return {"message": "规则已更新"}


@router.delete("/monitor/rules/{rule_id}")
async def delete_alert_rule(rule_id: int, current_user: dict = Depends(get_current_user)):
    """删除告警规则"""
    from app.services.monitor_service import monitor_service
    success = monitor_service.delete_alert_rule(rule_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="删除失败")
    
    return {"message": "规则已删除"}


@router.get("/monitor/records")
async def get_alert_records(
    resolved: bool = False,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """获取告警记录"""
    from app.services.monitor_service import monitor_service
    return monitor_service.get_alert_records(resolved, limit)


@router.post("/monitor/records/{record_id}/resolve")
async def resolve_alert(record_id: int, current_user: dict = Depends(get_current_user)):
    """确认告警"""
    from app.services.monitor_service import monitor_service
    success = monitor_service.resolve_alert(record_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="确认失败")
    
    return {"message": "告警已确认"}


@router.delete("/monitor/records/{record_id}")
async def delete_alert_record(record_id: int, current_user: dict = Depends(get_current_user)):
    """删除告警记录"""
    from app.services.monitor_service import monitor_service
    success = monitor_service.delete_alert_record(record_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="删除失败")
    
    return {"message": "记录已删除"}


@router.get("/monitor/stats")
async def get_alert_stats(current_user: dict = Depends(get_current_user)):
    """获取告警统计"""
    from app.services.monitor_service import monitor_service
    return monitor_service.get_alert_stats()


# ===== 因子计算增强 =====
@router.get("/factors/low-volatility")
async def get_low_volatility_stocks(
    days: int = 60,
    top_n: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """获取低波动率股票"""
    from app.services.factor_service import factor_service
    return factor_service.get_low_volatility_stocks(days, top_n)


@router.get("/factors/high-dividend")
async def get_high_dividend_stocks(
    top_n: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """获取高股息股票"""
    from app.services.factor_service import factor_service
    return factor_service.get_high_dividend_stocks(top_n)


@router.get("/factors/pe-roe")
async def get_pe_roe_stocks(
    min_pe: float = 0,
    max_pe: float = 30,
    min_roe: float = 5,
    top_n: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """获取PE-ROE策略股票"""
    from app.services.factor_service import factor_service
    return factor_service.get_pe_roe_stocks(min_pe, max_pe, min_roe, top_n)


@router.get("/factors/custom/{code}")
async def get_custom_factor(
    code: str,
    factor_name: str,
    current_user: dict = Depends(get_current_user)
):
    """计算自定义因子"""
    from app.services.factor_service import factor_service
    value = factor_service.calculate_custom_factor(code, factor_name)
    
    if value is None:
        raise HTTPException(status_code=404, detail="因子计算失败")
    
    return {"code": code, "factor": factor_name, "value": value}


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


# ===== 推送配置 =====
@router.get("/settings/push")
async def get_push_config(current_user: dict = Depends(get_current_user)):
    """获取推送配置"""
    from app.services.monitor_service import monitor_service
    return {
        "telegram_enabled": monitor_service.telegram_enabled,
        "telegram_bot_token": "***" if monitor_service.telegram_bot_token else "",
        "telegram_chat_id": "***" if monitor_service.telegram_chat_id else ""
    }


@router.post("/settings/push")
async def configure_push(
    telegram_token: Optional[str] = None,
    telegram_chat_id: Optional[str] = None,
    enabled: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """配置推送"""
    from app.services.monitor_service import monitor_service
    
    if telegram_token:
        monitor_service.configure_telegram(telegram_token, telegram_chat_id or "")
    
    monitor_service.telegram_enabled = enabled
    
    return {"message": "推送配置已更新"}
