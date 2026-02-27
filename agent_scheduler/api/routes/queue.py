"""
队列管理API - Agent任务队列
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/queue", tags=["queue"])

# 全局服务实例
_queue_service = None


def init_service(tasks_db=None, agents_db=None):
    """初始化服务"""
    from agent_scheduler.services.task_queue_service import TaskQueueService
    global _queue_service
    _queue_service = TaskQueueService(tasks_db, agents_db)


# Pydantic模型
class AddToQueueRequest(BaseModel):
    task_id: str
    agent_id: str


class ReorderQueueRequest(BaseModel):
    task_ids: List[str]


# API路由
@router.get("/overview")
async def get_queue_overview():
    """获取队列概览"""
    if not _queue_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _queue_service.get_queue_overview()


@router.get("/agents")
async def get_all_queues():
    """获取所有Agent队列"""
    if not _queue_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _queue_service.get_all_agent_queues()


@router.get("/agents/{agent_id}")
async def get_agent_queue(agent_id: str):
    """获取指定Agent的队列"""
    if not _queue_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _queue_service.get_agent_queue(agent_id)


@router.get("/agents/{agent_id}/stats")
async def get_agent_queue_stats(agent_id: str):
    """获取Agent队列统计"""
    if not _queue_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _queue_service.get_agent_queue_stats(agent_id)


@router.get("/agents/{agent_id}/next")
async def get_next_task(agent_id: str):
    """获取下一个待执行任务"""
    if not _queue_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    task = _queue_service.get_next_task(agent_id)
    
    if not task:
        return {"task": None, "message": "No task available"}
    
    return {"task": task}


@router.post("/add")
async def add_to_queue(request: AddToQueueRequest):
    """将任务加入队列"""
    if not _queue_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    success = _queue_service.add_to_queue(request.task_id, request.agent_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"success": True}


@router.post("/agents/{agent_id}/reorder")
async def reorder_queue(agent_id: str, request: ReorderQueueRequest):
    """重新排序队列"""
    if not _queue_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    success = _queue_service.reorder_queue(agent_id, request.task_ids)
    
    return {"success": success}


@router.post("/tasks/{task_id}/remove")
async def remove_from_queue(task_id: str):
    """从队列中移除任务"""
    if not _queue_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    success = _queue_service.remove_from_queue(task_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"success": True}
