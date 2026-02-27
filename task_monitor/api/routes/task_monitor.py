"""
任务监控API
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/monitor/tasks", tags=["task-monitor"])

# 全局服务实例
_monitor_service = None


def init_service(tasks_db):
    """初始化服务"""
    from task_monitor.services.task_monitor_service import TaskMonitorService
    global _monitor_service
    _monitor_service = TaskMonitorService(tasks_db)


# API路由
@router.get("/list")
async def get_task_list(
    status: Optional[str] = None,
    agent_id: Optional[str] = None,
    priority: Optional[int] = None,
    demand_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """获取任务列表（带筛选）"""
    if not _monitor_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    # 处理多选状态
    status_list = None
    if status:
        status_list = [s.strip() for s in status.split(",")]
    
    tasks = _monitor_service.get_task_list(
        status=status_list,
        agent_id=agent_id,
        priority=priority,
        demand_id=demand_id,
        limit=limit,
        offset=offset
    )
    
    # 添加状态颜色
    from task_monitor.services.task_monitor_service import TaskStatus
    for task in tasks:
        task["status_color"] = TaskStatus.get_color(task.get("status", ""))
    
    return {
        "total": len(tasks),
        "tasks": tasks
    }


@router.get("/stats")
async def get_task_stats():
    """获取任务状态统计"""
    if not _monitor_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _monitor_service.get_task_stats()


@router.get("/filters/options")
async def get_filter_options():
    """获取筛选选项"""
    if not _monitor_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return {
        "status_options": _monitor_service.get_status_filter_options()
    }


@router.get("/{task_id}")
async def get_task_detail(task_id: str):
    """获取任务详情"""
    if not _monitor_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    task = _monitor_service.get_task_detail(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task


@router.get("/{task_id}/transition-graph")
async def get_transition_graph(task_id: str):
    """获取任务流转图"""
    if not _monitor_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    graph = _monitor_service.get_transition_graph(task_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return graph
