"""
工作流管理API
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/workflow", tags=["workflow"])

# 全局服务
_workflow_service = None
_trigger_service = None


def init_service(agents_db=None, tasks_db=None):
    """初始化服务"""
    from agent_scheduler.services.workflow_service import WorkflowService, TriggerService
    from agent_scheduler.api.routes.agents import agents_db as a_db
    from agent_scheduler.api.routes.tasks import tasks_db as t_db
    
    global _workflow_service, _trigger_service
    _workflow_service = WorkflowService()
    _trigger_service = TriggerService(_workflow_service)
    
    # 设置数据库引用
    _workflow_service.set_dbs(agents_db or a_db, tasks_db or t_db)


# Pydantic模型
class TriggerTransitionRequest(BaseModel):
    task_id: str
    current_stage: str
    event: str = "TASK_COMPLETED"


class AddRuleRequest(BaseModel):
    event: str
    conditions: dict = {}
    action: str


# API路由
@router.get("/stages")
async def get_stages():
    """获取所有阶段"""
    if not _workflow_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return {"stages": _workflow_service.get_stages()}


@router.get("/stages/{stage_id}")
async def get_stage(stage_id: str):
    """获取指定阶段"""
    if not _workflow_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    stage = _workflow_service.get_stage(stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    
    return stage


@router.get("/stages/{stage_id}/next")
async def get_next_stage(stage_id: str):
    """获取下一阶段"""
    if not _workflow_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    next_stage = _workflow_service.get_next_stage(stage_id)
    
    return {"current_stage": stage_id, "next_stage": next_stage}


@router.get("/transitions")
async def get_transitions(from_stage: Optional[str] = None):
    """获取流转规则"""
    if not _workflow_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return {"transitions": _workflow_service.get_transitions(from_stage)}


@router.post("/trigger")
async def trigger_transition(request: TriggerTransitionRequest):
    """触发工作流流转"""
    if not _workflow_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    result = _workflow_service.trigger_transition(
        task_id=request.task_id,
        from_stage=request.current_stage,
        event=request.event
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/path")
async def get_workflow_path(start_stage: Optional[str] = None):
    """获取工作流路径"""
    if not _workflow_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    path = _workflow_service.get_workflow_path(start_stage)
    
    return {"path": path}


@router.get("/validate")
async def validate_workflow():
    """验证工作流配置"""
    if not _workflow_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _workflow_service.validate_workflow()


@router.get("/role/{role_id}/stage")
async def get_stage_by_role(role_id: str):
    """根据角色获取阶段"""
    if not _workflow_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    stage = _workflow_service.get_stage_by_role(role_id)
    
    return {"role_id": role_id, "stage": stage}


@router.get("/stage/{stage_id}/role")
async def get_role_by_stage(stage_id: str):
    """根据阶段获取角色"""
    if not _workflow_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    role = _workflow_service.get_role_by_stage(stage_id)
    
    return {"stage": stage_id, "role": role}


@router.get("/next-agent/{current_stage}")
async def find_next_agent(current_stage: str):
    """查找下一个Agent"""
    if not _workflow_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    agent = _workflow_service.find_next_agent(current_stage)
    
    if not agent:
        return {"agent": None, "message": "No available agent found"}
    
    return {"agent": agent}
