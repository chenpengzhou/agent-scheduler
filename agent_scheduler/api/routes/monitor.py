"""
监控管理API
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/monitor", tags=["monitor"])

# 全局服务实例
_monitor_service = None
_event_service = None


def init_services(agents_db=None, tasks_db=None, demands_db=None):
    """初始化服务"""
    from agent_scheduler.services.monitor_service import MonitorService
    from agent_scheduler.services.event_service import get_event_service
    
    # 延迟导入获取最新的db引用
    from agent_scheduler.api.routes.agents import agents_db as agents_db_ref
    from agent_scheduler.api.routes.tasks import tasks_db as tasks_db_ref
    from agent_scheduler.api.routes.demands import demands_db as demands_db_ref
    
    global _monitor_service, _event_service
    _monitor_service = MonitorService(
        agents_db=agents_db or agents_db_ref,
        tasks_db=tasks_db or tasks_db_ref,
        demands_db=demands_db or demands_db_ref,
        event_service=get_event_service()
    )
    _event_service = get_event_service()


# API路由
@router.get("/dashboard")
async def get_dashboard():
    """获取仪表盘概要"""
    if not _monitor_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _monitor_service.get_dashboard_summary()


@router.get("/agents/status")
async def get_agent_status_board():
    """获取Agent状态看板"""
    if not _monitor_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _monitor_service.get_agent_status_board()


@router.get("/tasks/progress")
async def get_task_progress(demand_id: Optional[str] = None):
    """获取任务进度"""
    if not _monitor_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _monitor_service.get_task_progress(demand_id)


@router.get("/statistics")
async def get_statistics():
    """获取统计概览"""
    if not _monitor_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _monitor_service.get_statistics()


@router.get("/events/count")
async def get_event_counts(period: str = "today"):
    """获取事件计数"""
    if not _monitor_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    valid_periods = ["today", "week", "month"]
    if period not in valid_periods:
        raise HTTPException(status_code=400, detail=f"Invalid period. Must be one of: {valid_periods}")
    
    return _monitor_service.get_event_counts(period)


@router.get("/events/live-feed")
async def get_live_feed(limit: int = 100):
    """获取Live Feed"""
    if not _event_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    if limit > 1000:
        limit = 1000
    
    return _event_service.get_live_feed(limit)


@router.get("/events")
async def get_events(
    limit: int = 100, 
    event_type: Optional[str] = None,
    source: Optional[str] = None
):
    """获取事件列表"""
    if not _event_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    events = _event_service.get_events(limit, event_type)
    
    if source:
        events = [e for e in events if e.get("source") == source]
    
    return events
