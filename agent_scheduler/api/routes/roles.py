"""
角色管理API
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import uuid

from agent_scheduler.models.role import PRESET_ROLES, RoleType

router = APIRouter(prefix="/api/v1/roles", tags=["roles"])

# 模拟数据库
roles_db = {}

# 初始化预置角色
for role in PRESET_ROLES:
    roles_db[role.id] = {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "role_type": role.role_type.value,
        "permissions": role.permissions,
        "required_capabilities": role.required_capabilities,
        "level": role.level,
        "parent_role_id": role.parent_role_id,
        "agent_count": 0,
        "created_at": role.created_at,
        "updated_at": role.updated_at
    }


# Pydantic模型
class RoleCreate(BaseModel):
    name: str
    description: str = ""
    permissions: List[str] = []
    required_capabilities: List[str] = []
    level: int = 1
    parent_role_id: Optional[str] = None


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    required_capabilities: Optional[List[str]] = None
    level: Optional[int] = None
    parent_role_id: Optional[str] = None


class RoleResponse(BaseModel):
    id: str
    name: str
    description: str
    role_type: str
    permissions: List[str]
    required_capabilities: List[str]
    level: int
    parent_role_id: Optional[str]
    agent_count: int
    created_at: datetime
    updated_at: datetime


# API路由
@router.post("", response_model=RoleResponse)
async def create_role(role: RoleCreate):
    """创建角色"""
    role_id = f"role_{uuid.uuid4().hex[:8]}"
    now = datetime.now()
    
    role_data = {
        "id": role_id,
        "name": role.name,
        "description": role.description,
        "role_type": RoleType.CUSTOM.value,
        "permissions": role.permissions,
        "required_capabilities": role.required_capabilities,
        "level": role.level,
        "parent_role_id": role.parent_role_id,
        "agent_count": 0,
        "created_at": now,
        "updated_at": now
    }
    
    roles_db[role_id] = role_data
    return role_data


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(role_id: str):
    """获取角色详情"""
    role = roles_db.get(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.get("", response_model=List[RoleResponse])
async def list_roles(
    role_type: Optional[str] = None,
    level: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
):
    """列取角色列表"""
    result = list(roles_db.values())
    
    if role_type:
        result = [r for r in result if r.get("role_type") == role_type]
    if level is not None:
        result = [r for r in result if r.get("level") == level]
    
    return result[offset:offset + limit]


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(role_id: str, role: RoleUpdate):
    """更新角色"""
    if role_id not in roles_db:
        raise HTTPException(status_code=404, detail="Role not found")
    
    existing = roles_db[role_id]
    
    # 系统预置角色不能修改
    if existing.get("role_type") == "SYSTEM":
        raise HTTPException(status_code=400, detail="Cannot modify system preset role")
    
    update_data = role.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        existing[key] = value
    
    existing["updated_at"] = datetime.now()
    roles_db[role_id] = existing
    
    return existing


@router.delete("/{role_id}")
async def delete_role(role_id: str):
    """删除角色"""
    if role_id not in roles_db:
        raise HTTPException(status_code=404, detail="Role not found")
    
    role = roles_db[role_id]
    
    # 系统预置角色不能删除
    if role.get("role_type") == "SYSTEM":
        raise HTTPException(status_code=400, detail="Cannot delete system preset role")
    
    # 检查是否有Agent使用此角色
    if role.get("agent_count", 0) > 0:
        raise HTTPException(status_code=400, detail="Cannot delete role with assigned agents")
    
    del roles_db[role_id]
    return {"message": "Deleted successfully"}
