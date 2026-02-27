"""
任务耗时统计API
"""
from typing import Optional
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/monitor/tasks", tags=["task-duration"])

# 全局服务
_duration_service = None
_detail_service = None


def init_service(tasks_db):
    """初始化服务"""
    from task_monitor.services.duration_service import DurationService, TaskDetailService
    global _duration_service, _detail_service
    _duration_service = DurationService(tasks_db)
    _detail_service = TaskDetailService(tasks_db)


# API路由
@router.get("/{task_id}/duration")
async def get_task_duration(task_id: str):
    """获取任务耗时详情"""
    if not _duration_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    duration = _duration_service.get_task_duration(task_id)
    
    if not duration:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return duration


@router.get("/duration/average")
async def get_average_duration(status: Optional[str] = None):
    """获取平均耗时"""
    if not _duration_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _duration_service.get_average_duration(status)


@router.get("/duration/stats")
async def get_duration_stats(days: int = 7):
    """获取耗时统计"""
    if not _duration_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _duration_service.get_duration_stats(days)


@router.get("/duration/slowest")
async def get_slowest_tasks(limit: int = 10):
    """获取耗时最长的任务"""
    if not _duration_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return {"tasks": _duration_service.get_slowest_tasks(limit)}


@router.get("/{task_id}/detail")
async def get_task_detail(task_id: str):
    """获取任务完整详情"""
    if not _detail_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    detail = _detail_service.get_task_detail(task_id)
    
    if not detail:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return detail


@router.get("/{task_id}/timeline")
async def get_task_timeline(task_id: str):
    """获取任务时间线"""
    if not _detail_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    timeline = _detail_service.get_task_timeline(task_id)
    
    return {"task_id": task_id, "timeline": timeline}
