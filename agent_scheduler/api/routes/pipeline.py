"""
流水线管理API
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])

# 全局服务实例（在main.py中初始化）
_pipeline_service = None
_priority_service = None


def init_services(demands_db):
    """初始化服务"""
    from agent_scheduler.services.pipeline_service import PipelineService
    from agent_scheduler.services.priority_service import PriorityService
    
    global _pipeline_service, _priority_service
    _pipeline_service = PipelineService(demands_db)
    _priority_service = PriorityService(demands_db)


# Pydantic模型
class StageTransition(BaseModel):
    target_stage: str
    reason: str = ""


class PrioritySuggestion(BaseModel):
    demand_id: str


class ReorderRequest(BaseModel):
    new_order: int


class BulkTransitionRequest(BaseModel):
    demand_ids: List[str]
    target_stage: str


# API路由
@router.get("/stages")
async def get_stages():
    """获取所有阶段"""
    return {
        "stages": [
            {"id": "WATCHING", "name": "观望", "description": "需求收集阶段"},
            {"id": "VALIDATING", "name": "评审中", "description": "需求评审阶段"},
            {"id": "BUILDING", "name": "开发中", "description": "开发执行阶段"},
            {"id": "SHIPPED", "name": "已发布", "description": "已完成上线"}
        ]
    }


@router.post("/demands/{demand_id}/transition")
async def transition_stage(demand_id: str, transition: StageTransition):
    """需求阶段流转"""
    if not _pipeline_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    result = _pipeline_service.transition(demand_id, transition.target_stage, transition.reason)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/demands/{demand_id}/can-transition/{target_stage}")
async def can_transition(demand_id: str, target_stage: str):
    """检查是否可以流转"""
    if not _pipeline_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    can_do = _pipeline_service.can_transition_stage(demand_id, target_stage)
    return {"can_transition": can_do}


@router.get("/stats/stage")
async def get_stage_stats():
    """获取各阶段统计"""
    if not _pipeline_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _pipeline_service.get_stage_stats()


@router.get("/stats/priority")
async def get_priority_stats():
    """获取各优先级统计"""
    if not _priority_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _priority_service.get_priority_stats()


@router.get("/stats/matrix")
async def get_priority_matrix():
    """获取优先级矩阵"""
    if not _priority_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _priority_service.get_priority_matrix()


@router.get("/demands/stage/{stage}")
async def get_demands_by_stage(stage: str):
    """获取指定阶段的需求"""
    if not _pipeline_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _pipeline_service.get_demands_by_stage(stage)


@router.post("/demands/bulk-transition")
async def bulk_transition(request: BulkTransitionRequest):
    """批量流转"""
    if not _pipeline_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _pipeline_service.bulk_transition(request.demand_ids, request.target_stage)


@router.get("/demands/sort")
async def sort_demands(
    stage: Optional[str] = None,
    by: str = "priority",
    limit: int = 100,
    offset: int = 0
):
    """排序需求"""
    if not _priority_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    # 获取需求列表
    from agent_scheduler.api.routes.demands import demands_db
    
    demands = list(demands_db.values())
    
    # 按阶段过滤
    if stage:
        demands = [d for d in demands if d.get("stage") == stage]
    
    # 排序
    demands = _priority_service.sort_demands(demands, by)
    
    return demands[offset:offset + limit]


@router.post("/demands/{demand_id}/reorder")
async def reorder_demand(demand_id: str, request: ReorderRequest):
    """调整需求顺序"""
    if not _priority_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    result = _priority_service.reorder(demand_id, request.new_order)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/demands/{demand_id}/suggest-priority")
async def suggest_priority(demand_id: str):
    """智能推荐优先级"""
    if not _priority_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _priority_service.suggest_priority(demand_id)


@router.get("/trend")
async def get_trend(days: int = 7):
    """获取阶段趋势"""
    if not _pipeline_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _pipeline_service.get_stage_trend(days)


@router.get("/average-time")
async def get_average_time():
    """获取各阶段平均耗时"""
    if not _pipeline_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _pipeline_service.get_stage_average_time()


@router.post("/auto-balance")
async def auto_balance():
    """自动平衡各阶段需求"""
    if not _priority_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _priority_service.auto_balance()
