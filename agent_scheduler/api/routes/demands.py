"""
需求管理API
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/v1/demands", tags=["demands"])

# 模拟数据库
demands_db = {}


# Pydantic模型
class DemandCreate(BaseModel):
    title: str
    description: str = ""
    category: str = "功能"  # 功能/Bug/优化
    tags: List[str] = []
    owner_id: str = ""
    priority: int = 2  # 0-10, 支持数字
    estimated_hours: float = 0.0
    acceptance_criteria: str = ""
    stage: str = "WATCHING"  # 支持指定阶段


class DemandUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    assignee_id: Optional[str] = None
    priority: Optional[int] = None
    stage: Optional[str] = None
    status: Optional[str] = None
    estimated_hours: Optional[float] = None
    acceptance_criteria: Optional[str] = None


class DemandResponse(BaseModel):
    id: str
    title: str
    description: str
    status: str
    stage: str
    priority: int
    category: str
    tags: List[str]
    owner_id: str
    assignee_id: str
    acceptance_criteria: str
    estimated_hours: float
    actual_hours: float
    sort_order: int
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime]
    completed_at: Optional[datetime]


# API路由
@router.post("", response_model=DemandResponse)
async def create_demand(demand: DemandCreate):
    """创建需求"""
    demand_id = str(uuid.uuid4())
    now = datetime.now()
    
    # 计算sort_order（按优先级）
    max_order = max([d.get("sort_order", 0) for d in demands_db.values()], default=0)
    
    demand_data = {
        "id": demand_id,
        "title": demand.title,
        "description": demand.description,
        "status": "DRAFT",
        "stage": "WATCHING",
        "priority": demand.priority,
        "category": demand.category,
        "tags": demand.tags,
        "owner_id": demand.owner_id,
        "assignee_id": "",
        "acceptance_criteria": demand.acceptance_criteria,
        "estimated_hours": demand.estimated_hours,
        "actual_hours": 0.0,
        "sort_order": max_order + 1,
        "created_at": now,
        "updated_at": now,
        "submitted_at": None,
        "completed_at": None
    }
    
    demands_db[demand_id] = demand_data
    return demand_data


@router.get("/{demand_id}", response_model=DemandResponse)
async def get_demand(demand_id: str):
    """获取需求详情"""
    demand = demands_db.get(demand_id)
    if not demand:
        raise HTTPException(status_code=404, detail="Demand not found")
    return demand


@router.get("", response_model=List[DemandResponse])
async def list_demands(
    status: Optional[str] = None,
    stage: Optional[str] = None,
    priority: Optional[int] = None,
    category: Optional[str] = None,
    owner_id: Optional[str] = None,
    assignee_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """列取需求列表"""
    result = list(demands_db.values())
    
    # 过滤
    if status:
        result = [d for d in result if d.get("status") == status]
    if stage:
        result = [d for d in result if d.get("stage") == stage]
    if priority is not None:
        result = [d for d in result if d.get("priority") == priority]
    if category:
        result = [d for d in result if d.get("category") == category]
    if owner_id:
        result = [d for d in result if d.get("owner_id") == owner_id]
    if assignee_id:
        result = [d for d in result if d.get("assignee_id") == assignee_id]
    
    # 按sort_order排序
    result.sort(key=lambda x: (x.get("priority", 999), x.get("sort_order", 0)))
    
    return result[offset:offset + limit]


@router.put("/{demand_id}", response_model=DemandResponse)
async def update_demand(demand_id: str, demand: DemandUpdate):
    """更新需求"""
    if demand_id not in demands_db:
        raise HTTPException(status_code=404, detail="Demand not found")
    
    existing = demands_db[demand_id]
    update_data = demand.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        existing[key] = value
    
    existing["updated_at"] = datetime.now()
    demands_db[demand_id] = existing
    
    return existing


@router.delete("/{demand_id}")
async def delete_demand(demand_id: str):
    """删除需求"""
    if demand_id not in demands_db:
        raise HTTPException(status_code=404, detail="Demand not found")
    
    del demands_db[demand_id]
    return {"message": "Deleted successfully"}


@router.post("/{demand_id}/submit")
async def submit_demand(demand_id: str):
    """提交需求"""
    if demand_id not in demands_db:
        raise HTTPException(status_code=404, detail="Demand not found")
    
    demand = demands_db[demand_id]
    
    if demand["status"] != "DRAFT":
        raise HTTPException(status_code=400, detail="Only DRAFT demand can be submitted")
    
    demand["status"] = "SUBMITTED"
    demand["submitted_at"] = datetime.now()
    demand["updated_at"] = datetime.now()
    
    return demand


@router.post("/{demand_id}/complete")
async def complete_demand(demand_id: str):
    """完成需求"""
    if demand_id not in demands_db:
        raise HTTPException(status_code=404, detail="Demand not found")
    
    demand = demands_db[demand_id]
    
    demand["status"] = "COMPLETED"
    demand["stage"] = "SHIPPED"
    demand["completed_at"] = datetime.now()
    demand["updated_at"] = datetime.now()
    
    return demand


@router.get("/stats/summary")
async def get_demand_stats():
    """获取需求统计"""
    demands = list(demands_db.values())
    
    # 按状态统计
    status_counts = {}
    for d in demands:
        status = d.get("status", "UNKNOWN")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # 按阶段统计
    stage_counts = {}
    for d in demands:
        stage = d.get("stage", "UNKNOWN")
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
    
    # 按优先级统计
    priority_counts = {}
    for d in demands:
        priority = d.get("priority", -1)
        priority_counts[str(priority)] = priority_counts.get(str(priority), 0) + 1
    
    return {
        "total": len(demands),
        "by_status": status_counts,
        "by_stage": stage_counts,
        "by_priority": priority_counts
    }
