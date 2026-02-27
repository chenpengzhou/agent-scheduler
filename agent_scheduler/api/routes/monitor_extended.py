"""
扩展监控API - 首页布局优化
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/monitor", tags=["monitor-extended"])


# Pydantic模型
class DashboardOverviewRequest(BaseModel):
    show_agents: bool = True
    show_demands: bool = True
    show_tasks: bool = True


# API路由
@router.get("/dashboard/overview")
async def get_dashboard_overview():
    """获取Dashboard概览（首页全Agent信息）"""
    from agent_scheduler.api.routes.agents import agents_db
    from agent_scheduler.api.routes.demands import demands_db
    from agent_scheduler.api.routes.tasks import tasks_db
    from agent_scheduler.services.agent_status_service import get_agent_status_service
    
    # 获取Agent概览
    agents = []
    for agent in agents_db.values():
        agents.append({
            "id": agent.get("id"),
            "name": agent.get("name"),
            "status": agent.get("status", "OFFLINE"),
            "role_id": agent.get("role_id"),
            "work_status": agent.get("work_status", "Idle"),
            "current_task": agent.get("current_task", ""),
            "max_concurrent_tasks": agent.get("max_concurrent_tasks", 1),
            "current_tasks": agent.get("current_tasks", 0)
        })
    
    # 统计
    agent_stats = {
        "total": len(agents),
        "online": sum(1 for a in agents if a.get("status") != "OFFLINE"),
        "busy": sum(1 for a in agents if a.get("status") == "BUSY"),
        "idle": sum(1 for a in agents if a.get("status") == "IDLE")
    }
    
    # 获取需求统计
    demand_stats = {
        "total": len(demands_db),
        "by_stage": {}
    }
    for demand in demands_db.values():
        stage = demand.get("stage", "WATCHING")
        demand_stats["by_stage"][stage] = demand_stats["by_stage"].get(stage, 0) + 1
    
    # 获取任务统计
    task_stats = {
        "total": len(tasks_db),
        "by_status": {}
    }
    for task in tasks_db.values():
        status = task.get("status", "PENDING")
        task_stats["by_status"][status] = task_stats["by_status"].get(status, 0) + 1
    
    # 计算今日事件（简化为已完成任务数）
    today_completed = 0
    for task in tasks_db.values():
        if task.get("status") == "COMPLETED":
            completed_at = task.get("completed_at")
            if completed_at:
                if isinstance(completed_at, str):
                    completed_at = datetime.fromisoformat(completed_at)
                if completed_at.date() == datetime.now().date():
                    today_completed += 1
    
    return {
        "agents": agents,
        "agent_stats": agent_stats,
        "demand_stats": demand_stats,
        "task_stats": task_stats,
        "today_events": today_completed,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/dashboard/agents")
async def get_dashboard_agents(
    status: Optional[str] = None,
    role_id: Optional[str] = None,
    work_status: Optional[str] = None
):
    """获取Dashboard Agent列表（支持筛选）"""
    from agent_scheduler.api.routes.agents import agents_db
    
    agents = []
    for agent in agents_db.values():
        # 筛选
        if status and agent.get("status") != status:
            continue
        if role_id and agent.get("role_id") != role_id:
            continue
        if work_status and agent.get("work_status") != work_status:
            continue
        
        agents.append({
            "id": agent.get("id"),
            "name": agent.get("name"),
            "status": agent.get("status", "OFFLINE"),
            "role_id": agent.get("role_id"),
            "work_status": agent.get("work_status", "Idle"),
            "current_task": agent.get("current_task", ""),
            "today_completed": agent.get("completed_tasks", 0),
            "last_active_at": agent.get("last_active_at")
        })
    
    return {
        "total": len(agents),
        "agents": agents
    }


@router.get("/dashboard/demands")
async def get_dashboard_demands():
    """获取Dashboard需求概览"""
    from agent_scheduler.api.routes.demands import demands_db
    
    # 按阶段统计
    stage_counts = {
        "WATCHING": 0,
        "VALIDATING": 0,
        "BUILDING": 0,
        "SHIPPED": 0
    }
    
    demands = []
    for demand in demands_db.values():
        stage = demand.get("stage", "WATCHING")
        if stage in stage_counts:
            stage_counts[stage] += 1
        
        demands.append({
            "id": demand.get("id"),
            "title": demand.get("title"),
            "stage": stage,
            "priority": demand.get("priority"),
            "owner_id": demand.get("owner_id")
        })
    
    # 排序: BUILDING > VALIDATING > WATCHING > SHIPPED
    demands.sort(key=lambda d: (
        0 if d["stage"] == "BUILDING" else
        1 if d["stage"] == "VALIDATING" else
        2 if d["stage"] == "WATCHING" else 3
    ))
    
    return {
        "total": len(demands),
        "by_stage": stage_counts,
        "demands": demands[:50]  # 返回前50个
    }


@router.get("/dashboard/pipeline")
async def get_dashboard_pipeline():
    """获取Dashboard流水线概览"""
    from agent_scheduler.api.routes.demands import demands_db
    
    stage_counts = {
        "WATCHING": 0,
        "VALIDATING": 0,
        "BUILDING": 0,
        "SHIPPED": 0
    }
    
    for demand in demands_db.values():
        stage = demand.get("stage", "WATCHING")
        if stage in stage_counts:
            stage_counts[stage] += 1
    
    # 计算进度
    total = sum(stage_counts.values())
    if total > 0:
        progress = (stage_counts["SHIPPED"] / total) * 100
    else:
        progress = 0
    
    # 构建流水线展示
    pipeline_display = " → ".join([
        f"{stage}: {stage_counts[stage]}"
        for stage in ["WATCHING", "VALIDATING", "BUILDING", "SHIPPED"]
    ])
    
    return {
        "pipeline": pipeline_display,
        "by_stage": stage_counts,
        "progress_percent": round(progress, 1),
        "total": total
    }


@router.get("/dashboard/filters/agents")
async def get_agent_filter_options():
    """获取Agent筛选选项"""
    from agent_scheduler.api.routes.agents import agents_db
    
    status_options = [
        {"value": "IDLE", "label": "空闲"},
        {"value": "BUSY", "label": "忙碌"},
        {"value": "OFFLINE", "label": "离线"}
    ]
    
    # 获取所有角色
    role_ids = set()
    for agent in agents_db.values():
        if agent.get("role_id"):
            role_ids.add(agent.get("role_id"))
    
    role_options = [
        {"value": r, "label": r.replace("role_", "").replace("_", " ").title()}
        for r in role_ids
    ]
    
    return {
        "status_options": status_options,
        "role_options": role_options
    }
