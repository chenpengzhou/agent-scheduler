"""
API路由 - 工作流定义
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session

from api.models import get_db
from api.services.workflow_svc import WorkflowService

router = APIRouter(prefix="/api/v1/workflow-definitions", tags=["workflow-definitions"])


# ===== Pydantic模型 =====

class WorkflowDefCreate(BaseModel):
    name: str
    version: str = "1.0"
    description: str = ""
    definition_json: dict
    tags: List[str] = []
    created_by: str = "system"


class WorkflowDefUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    definition_json: Optional[dict] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class WorkflowDefResponse(BaseModel):
    id: str
    name: str
    version: str
    description: str
    definition_json: dict
    is_active: bool
    is_template: bool
    created_at: datetime
    updated_at: datetime
    created_by: str
    tags: List[str]

    class Config:
        from_attributes = True


def to_response(definition: "WorkflowDefinitionDB") -> WorkflowDefResponse:
    """转换为响应模型"""
    return WorkflowDefResponse(
        id=definition.id,
        name=definition.name,
        version=definition.version,
        description=definition.description or "",
        definition_json=definition.definition_json,
        is_active=definition.is_active,
        is_template=definition.is_template,
        created_at=definition.created_at,
        updated_at=definition.updated_at,
        created_by=definition.created_by or "system",
        tags=definition.tags or []
    )


# ===== 路由 =====

@router.post("", response_model=WorkflowDefResponse)
async def create_workflow_definition(
    definition: WorkflowDefCreate,
    db: Session = Depends(get_db)
):
    """创建工作流定义"""
    svc = WorkflowService(db)
    result = svc.create_definition(
        name=definition.name,
        definition_json=definition.definition_json,
        description=definition.description,
        version=definition.version,
        tags=definition.tags,
        created_by=definition.created_by
    )
    return to_response(result)


@router.get("/{def_id}", response_model=WorkflowDefResponse)
async def get_workflow_definition(
    def_id: str,
    db: Session = Depends(get_db)
):
    """获取工作流定义"""
    svc = WorkflowService(db)
    definition = svc.get_definition(def_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Workflow definition not found")
    return to_response(definition)


@router.get("", response_model=List[WorkflowDefResponse])
async def list_workflow_definitions(
    name: Optional[str] = None,
    tag: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """列取工作流定义"""
    svc = WorkflowService(db)
    definitions = svc.list_definitions(name=name, tag=tag, offset=offset, limit=limit)
    return [to_response(d) for d in definitions]


@router.put("/{def_id}", response_model=WorkflowDefResponse)
async def update_workflow_definition(
    def_id: str,
    definition: WorkflowDefUpdate,
    db: Session = Depends(get_db)
):
    """更新工作流定义"""
    svc = WorkflowService(db)
    update_data = definition.model_dump(exclude_unset=True)
    result = svc.update_definition(def_id, **update_data)
    if not result:
        raise HTTPException(status_code=404, detail="Workflow definition not found")
    return to_response(result)


@router.delete("/{def_id}")
async def delete_workflow_definition(
    def_id: str,
    db: Session = Depends(get_db)
):
    """删除工作流定义"""
    svc = WorkflowService(db)
    success = svc.delete_definition(def_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow definition not found")
    return {"message": "Deleted successfully"}
