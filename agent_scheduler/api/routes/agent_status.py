"""
Agent状态API
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/monitor/agents", tags=["agent-status"])

# 全局服务
_status_service = None


def init_service(agents_db=None):
    """初始化服务"""
    from agent_scheduler.services.agent_status_service import get_agent_status_service
    global _status_service
    _status_service = get_agent_status_service()
    _status_service.set_agents_db(agents_db or {})


# Pydantic模型
class SyncStatusRequest(BaseModel):
    agent_id: str
    status: str
    current_task: str = ""
    last_active_at: Optional[str] = None


# API路由
@router.get("/status")
async def get_all_agent_status():
    """获取所有Agent状态"""
    if not _status_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return {
        "agents": _status_service.get_all_agents_status(),
        "statistics": _status_service.get_status_statistics()
    }


@router.get("/status/{agent_id}")
async def get_agent_status(agent_id: str):
    """获取指定Agent状态"""
    if not _status_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    status = _status_service.get_agent_status(agent_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return status


@router.get("/statistics")
async def get_status_statistics():
    """获取状态统计"""
    if not _status_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _status_service.get_status_statistics()


@router.get("/history/{agent_id}")
async def get_status_history(agent_id: str, limit: int = 20):
    """获取状态变更历史"""
    if not _status_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return {
        "agent_id": agent_id,
        "history": _status_service.get_status_history(agent_id, limit)
    }


@router.get("/types")
async def get_status_types():
    """获取状态类型"""
    if not _status_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return {"status_types": _status_service.get_status_types()}


@router.post("/sync")
async def sync_agent_status(request: SyncStatusRequest):
    """同步Agent状态"""
    if not _status_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    success = _status_service.sync_agent_status(request.model_dump())
    
    return {"success": success}


@router.post("/sync-all")
async def sync_all_agents():
    """同步所有Agent状态"""
    if not _status_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    result = _status_service.sync_from_openclaw()
    
    return result


@router.post("/auto-refresh/start")
async def start_auto_refresh():
    """启动自动刷新"""
    if not _status_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    _status_service.start_auto_refresh()
    
    return {"message": "Auto refresh started"}


@router.post("/auto-refresh/stop")
async def stop_auto_refresh():
    """停止自动刷新"""
    if not _status_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    _status_service.stop_auto_refresh()
    
    return {"message": "Auto refresh stopped"}
