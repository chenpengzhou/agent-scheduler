"""
API路由 - 工作流实例
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session

from api.models import get_db
from api.services.workflow_svc import WorkflowService
from api.models.db import WorkflowStatusDB, StepStatusDB, TaskStatusDB, ApprovalStatusDB

router = APIRouter(prefix="/api/v1/workflow-instances", tags=["workflow-instances"])

# ===== Pydantic模型 =====

class WorkflowStartRequest(BaseModel):
    definition_id: str
    input_data: dict = {}
    triggered_by: str = "api"
    correlation_id: Optional[str] = None


class CancelRequest(BaseModel):
    reason: str = ""


class RetryRequest(BaseModel):
    pass


class WorkflowInstanceResponse(BaseModel):
    id: str
    definition_id: str
    definition_version: str
    status: str
    current_step_id: Optional[str]
    completed_steps: List[str]
    failed_steps: List[str]
    state_json: dict
    input_data: dict
    output_data: dict
    error_message: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    triggered_by: str

    class Config:
        from_attributes = True


class StepResponse(BaseModel):
    id: str
    definition_id: str
    workflow_instance_id: str
    status: str
    input_data: dict
    output_data: dict
    error_message: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: str
    definition_id: str
    step_instance_id: str
    workflow_instance_id: str
    status: str
    input_params: dict
    output_params: dict
    result_data: dict
    error_message: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ApprovalResponse(BaseModel):
    id: str
    step_instance_id: Optional[str]
    workflow_instance_id: str
    approval_type: str
    status: str
    approver: Optional[str]
    title: str
    content: dict
    created_at: datetime
    approved_at: Optional[datetime]
    approved_by: Optional[str]
    comment: Optional[str]

    class Config:
        from_attributes = True


class ApproveRequest(BaseModel):
    approved_by: str
    comment: str = ""


class RejectRequest(BaseModel):
    approved_by: str
    comment: str = ""


class LogResponse(BaseModel):
    id: str
    workflow_instance_id: str
    step_instance_id: Optional[str]
    task_instance_id: Optional[str]
    level: str
    message: str
    extra: dict
    created_at: datetime

    class Config:
        from_attributes = True


class MetricsResponse(BaseModel):
    total_definitions: int
    total_instances: int
    status_counts: dict


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime


# ===== 辅助函数 =====

def instance_to_response(instance: "WorkflowInstanceDB") -> WorkflowInstanceResponse:
    """转换为响应模型"""
    return WorkflowInstanceResponse(
        id=instance.id,
        definition_id=instance.definition_id,
        definition_version=instance.definition_version or "1.0",
        status=instance.status.value,
        current_step_id=instance.current_step_id,
        completed_steps=instance.completed_steps or [],
        failed_steps=instance.failed_steps or [],
        state_json=instance.state_json or {},
        input_data=instance.input_data or {},
        output_data=instance.output_data or {},
        error_message=instance.error_message or "",
        created_at=instance.created_at,
        started_at=instance.started_at,
        completed_at=instance.completed_at,
        triggered_by=instance.triggered_by or "system"
    )


def step_to_response(step: "StepInstanceDB") -> StepResponse:
    """转换为步骤响应"""
    return StepResponse(
        id=step.id,
        definition_id=step.definition_id,
        workflow_instance_id=step.workflow_instance_id,
        status=step.status.value,
        input_data=step.input_data or {},
        output_data=step.output_data or {},
        error_message=step.error_message or "",
        created_at=step.created_at,
        started_at=step.started_at,
        completed_at=step.completed_at
    )


def task_to_response(task: "TaskInstanceDB") -> TaskResponse:
    """转换为任务响应"""
    return TaskResponse(
        id=task.id,
        definition_id=task.definition_id,
        step_instance_id=task.step_instance_id,
        workflow_instance_id=task.workflow_instance_id,
        status=task.status.value,
        input_params=task.input_params or {},
        output_params=task.output_params or {},
        result_data=task.result_data or {},
        error_message=task.error_message or "",
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at
    )


def approval_to_response(approval: "ApprovalInstanceDB") -> ApprovalResponse:
    """转换为审批响应"""
    return ApprovalResponse(
        id=approval.id,
        step_instance_id=approval.step_instance_id,
        workflow_instance_id=approval.workflow_instance_id,
        approval_type=approval.approval_type or "manual",
        status=approval.status.value,
        approver=approval.approver,
        title=approval.title or "",
        content=approval.content or {},
        created_at=approval.created_at,
        approved_at=approval.approved_at,
        approved_by=approval.approved_by,
        comment=approval.comment
    )


# ===== 路由 =====

@router.post("", response_model=WorkflowInstanceResponse)
async def start_workflow_instance(
    start_req: WorkflowStartRequest,
    db: Session = Depends(get_db)
):
    """启动工作流实例"""
    svc = WorkflowService(db)
    instance = svc.start_instance(
        definition_id=start_req.definition_id,
        input_data=start_req.input_data,
        triggered_by=start_req.triggered_by,
        correlation_id=start_req.correlation_id
    )
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow definition not found")
    return instance_to_response(instance)


# ===== 监控指标（放在/{instance_id}之前避免路由冲突）=====

@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(db: Session = Depends(get_db)):
    """获取系统指标"""
    svc = WorkflowService(db)
    metrics = svc.get_metrics()
    return MetricsResponse(**metrics)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(status="healthy", timestamp=datetime.utcnow())


@router.get("/{instance_id}", response_model=WorkflowInstanceResponse)
async def get_workflow_instance(
    instance_id: str,
    db: Session = Depends(get_db)
):
    """获取工作流实例详情"""
    svc = WorkflowService(db)
    instance = svc.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    return instance_to_response(instance)


@router.get("", response_model=List[WorkflowInstanceResponse])
async def list_workflow_instances(
    definition_id: Optional[str] = None,
    status: Optional[str] = None,
    start_time_from: Optional[datetime] = None,
    start_time_to: Optional[datetime] = None,
    offset: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """列取工作流实例"""
    svc = WorkflowService(db)
    
    # 转换status字符串到枚举
    status_enum = None
    if status:
        try:
            status_enum = WorkflowStatusDB[status]
        except KeyError:
            pass
    
    instances = svc.list_instances(
        definition_id=definition_id,
        status=status_enum,
        start_time_from=start_time_from,
        start_time_to=start_time_to,
        offset=offset,
        limit=limit
    )
    return [instance_to_response(i) for i in instances]


