"""
任务管理API
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

# 模拟数据库
tasks_db = {}

# 调度引擎
from agent_scheduler.scheduler.engine import SchedulerEngine
scheduler = SchedulerEngine()


# Pydantic模型
class TaskCreate(BaseModel):
    name: str
    description: str = ""
    demand_id: str = ""
    task_type: str = "AGENT"  # AGENT, SCRIPT, API
    priority: int = 2  # 0-10, 支持数字
    executor_type: str = "agent"
    executor_params: dict = {}
    input_data: dict = {}
    depends_on: List[str] = []
    max_retries: int = 3
    retry_delay_seconds: int = 60


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    assigned_agent_id: Optional[str] = None
    input_data: Optional[dict] = None


class TaskResponse(BaseModel):
    id: str
    name: str
    description: str
    demand_id: str
    task_type: str
    priority: int
    status: str
    assigned_agent_id: str
    executor_type: str
    input_data: dict
    output_data: dict
    depends_on: List[str]
    retry_count: int
    max_retries: int
    error_message: str
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


def to_response(task: dict) -> TaskResponse:
    """转换为响应模型"""
    return TaskResponse(
        id=task["id"],
        name=task["name"],
        description=task["description"],
        demand_id=task["demand_id"],
        task_type=task["task_type"],
        priority=task["priority"],
        status=task["status"],
        assigned_agent_id=task["assigned_agent_id"],
        executor_type=task["executor_type"],
        input_data=task["input_data"],
        output_data=task["output_data"],
        depends_on=task["depends_on"],
        retry_count=task["retry_count"],
        max_retries=task["max_retries"],
        error_message=task["error_message"],
        created_at=task["created_at"],
        updated_at=task["updated_at"],
        started_at=task["started_at"],
        completed_at=task["completed_at"]
    )


# API路由
@router.post("", response_model=TaskResponse)
async def create_task(task: TaskCreate):
    """创建任务"""
    task_id = str(uuid.uuid4())
    now = datetime.now()
    
    task_data = {
        "id": task_id,
        "name": task.name,
        "description": task.description,
        "demand_id": task.demand_id,
        "workflow_instance_id": "",
        "parent_task_id": "",
        "task_type": task.task_type,
        "priority": task.priority,
        "status": "PENDING",
        "assigned_agent_id": "",
        "executor_type": task.executor_type,
        "executor_params": task.executor_params,
        "input_data": task.input_data,
        "output_data": {},
        "depends_on": task.depends_on,
        "retry_count": 0,
        "max_retries": task.max_retries,
        "retry_delay_seconds": task.retry_delay_seconds,
        "error_message": "",
        "error_details": {},
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "completed_at": None
    }
    
    tasks_db[task_id] = task_data
    
    # 提交到调度引擎 - 转换为TaskPriority枚举（支持0-10）
    from agent_scheduler.models.task import Task as TaskModel, TaskPriority as TTPriority
    # 将priority限制在0-3范围内
    priority_value = max(0, min(3, task.priority))
    task_model = TaskModel(
        id=task_id,
        name=task.name,
        task_type=task.task_type,
        priority=TTPriority(priority_value),
        depends_on=task.depends_on,
        max_retries=task.max_retries
    )
    scheduler.submit_task(task_model)
    
    return to_response(task_data)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """获取任务详情"""
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return to_response(task)


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = None,
    priority: Optional[int] = None,
    demand_id: Optional[str] = None,
    assigned_agent_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """列取任务列表"""
    result = list(tasks_db.values())
    
    if status:
        result = [t for t in result if t["status"] == status]
    if priority is not None:
        result = [t for t in result if t["priority"] == priority]
    if demand_id:
        result = [t for t in result if t["demand_id"] == demand_id]
    if assigned_agent_id:
        result = [t for t in result if t["assigned_agent_id"] == assigned_agent_id]
    
    # 按优先级和创建时间排序
    result.sort(key=lambda t: (t["priority"], t["created_at"]))
    
    return [to_response(t) for t in result[offset:offset + limit]]


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, task: TaskUpdate):
    """更新任务"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    
    existing = tasks_db[task_id]
    update_data = task.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        existing[key] = value
    
    existing["updated_at"] = datetime.now()
    tasks_db[task_id] = existing
    
    return to_response(existing)


@router.post("/{task_id}/start")
async def start_task(task_id: str, agent_id: str):
    """开始执行任务"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_db[task_id]
    
    if task["status"] != "PENDING":
        raise HTTPException(status_code=400, detail="Task is not in PENDING status")
    
    task["status"] = "RUNNING"
    task["assigned_agent_id"] = agent_id
    task["started_at"] = datetime.now()
    task["updated_at"] = datetime.now()
    
    # 通知调度引擎
    scheduler.start_task(task_id)
    
    return task


@router.post("/{task_id}/complete")
async def complete_task(task_id: str, output: dict = {}):
    """完成任务"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_db[task_id]
    
    task["status"] = "COMPLETED"
    task["output_data"] = output
    task["completed_at"] = datetime.now()
    task["updated_at"] = datetime.now()
    
    # 通知调度引擎
    scheduler.complete_task(task_id, output)
    
    return task


@router.post("/{task_id}/fail")
async def fail_task(task_id: str, error: str = ""):
    """标记任务失败"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_db[task_id]
    
    task["status"] = "FAILED"
    task["error_message"] = error
    task["completed_at"] = datetime.now()
    task["updated_at"] = datetime.now()
    
    # 通知调度引擎
    scheduler.fail_task(task_id, error)
    
    return task


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消任务"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_db[task_id]
    
    if task["status"] in ["COMPLETED", "FAILED", "CANCELLED"]:
        raise HTTPException(status_code=400, detail="Cannot cancel completed/failed/cancelled task")
    
    task["status"] = "CANCELLED"
    task["completed_at"] = datetime.now()
    task["updated_at"] = datetime.now()
    
    # 通知调度引擎
    scheduler.cancel_task(task_id)
    
    return task


@router.get("/stats/summary")
async def get_task_stats():
    """获取任务统计"""
    return scheduler.get_statistics()


@router.get("/ready")
async def get_ready_tasks():
    """获取就绪任务列表"""
    ready = scheduler.get_ready_tasks()
    return [to_response(tasks_db[t.id]) for t in ready if t.id in tasks_db]


@router.get("/pending-by-priority")
async def get_pending_tasks_by_priority():
    """按优先级获取待执行任务"""
    pending = scheduler.get_pending_tasks_by_priority()
    return [to_response(tasks_db[t.id]) for t in pending if t.id in tasks_db]


@router.post("/{task_id}/dispatch")
async def dispatch_task(task_id: str, agent_id: str):
    """手动分发任务给指定Agent"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_db[task_id]
    
    if task["status"] != "PENDING":
        raise HTTPException(status_code=400, detail="Task is not in PENDING status")
    
    # 检查Agent是否存在
    from agent_scheduler.api.routes.agents import agents_db
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = agents_db[agent_id]
    
    # 检查Agent是否可用
    if agent.get("status") != "IDLE":
        raise HTTPException(status_code=400, detail="Agent is not IDLE")
    
    # 分配任务
    task["status"] = "RUNNING"
    task["assigned_agent_id"] = agent_id
    task["started_at"] = datetime.now()
    task["updated_at"] = datetime.now()
    
    # 更新Agent状态
    agent["status"] = "BUSY"
    agent["current_tasks"] = agent.get("current_tasks", 0) + 1
    agents_db[agent_id] = agent
    
    # 通知调度引擎
    scheduler.start_task(task_id)
    
    return task


@router.get("/execution-order")
async def get_execution_order():
    """获取任务执行顺序（DAG拓扑排序）"""
    order = scheduler.dag_scheduler.get_execution_order()
    return {"batches": order}
