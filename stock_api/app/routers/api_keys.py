# -*- coding: utf-8 -*-
"""
API Keys 管理路由 - 增强版
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.services.api_key_service import api_key_service, Role
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/admin/api-keys", tags=["API Keys"])


class CreateKeyRequest(BaseModel):
    name: str
    role: str = "user"
    rate_limit: int = 100
    expires_days: int = 365
    permissions: Optional[List[str]] = None


class UpdateKeyRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    rate_limit: Optional[int] = None
    expires_days: Optional[int] = None
    is_active: Optional[bool] = None


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key: Optional[str] = None  # 创建时返回完整key
    key_hint: str
    key_prefix: str
    is_active: bool
    rate_limit: int
    role: str
    permissions: List[str]
    expires_at: str
    last_used_at: Optional[str] = None
    created_at: Optional[str] = None


class UsageStatsResponse(BaseModel):
    total_calls: int
    avg_response_ms: Optional[int] = 0
    daily_stats: List[dict]
    endpoint_stats: List[dict]
    key_stats: List[dict]


class RateLimitStatus(BaseModel):
    key_id: int
    key_name: str
    rate_limit: int
    used_today: int
    remaining: int
    reset_at: str


def get_current_user(request: Request) -> dict:
    """获取当前用户"""
    return request.state.user


def require_admin(request: Request) -> dict:
    """需要管理员权限"""
    user = request.state.user
    if not user.get('is_admin'):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


@router.post("/", response_model=ApiKeyResponse)
async def create_api_key(
    request: CreateKeyRequest,
    authorization: str = Header(None)
):
    """创建新的API Key"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="无效token")
    
    # 验证角色
    if request.role not in Role.PERMISSIONS:
        raise HTTPException(status_code=400, detail=f"无效的角色: {request.role}")
    
    result = api_key_service.create_key(
        name=request.name,
        user_id=user["id"],
        role=request.role,
        rate_limit=request.rate_limit,
        expires_days=request.expires_days,
        permissions=request.permissions
    )
    
    return ApiKeyResponse(**result)


@router.get("/", response_model=List[ApiKeyResponse])
async def list_api_keys(
    authorization: str = Header(None),
    include_inactive: bool = Query(False, description="包含已停用的Key")
):
    """列出所有API Keys"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="无效token")
    
    # 非管理员只能看自己的keys
    user_id = None if user.get('is_admin') else user.get('user_id')
    
    keys = api_key_service.list_keys(user_id=user_id, include_inactive=include_inactive)
    
    # 构建响应，不显示完整key
    result = []
    for k in keys:
        resp = ApiKeyResponse(
            id=k['id'],
            name=k['name'],
            key=None,  # 不返回完整key
            key_hint=f"{k.get('key_prefix', '****')}...",
            key_prefix=k.get('key_prefix', '****'),
            is_active=bool(k.get('is_active')),
            rate_limit=k.get('rate_limit', 100),
            role=k.get('role', 'user'),
            permissions=k.get('permissions', []),
            expires_at=k.get('expires_at', ''),
            last_used_at=k.get('last_used_at'),
            created_at=k.get('created_at')
        )
        result.append(resp)
    
    return result


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: int,
    authorization: str = Header(None)
):
    """获取单个API Key详情"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="无效token")
    
    key = api_key_service.get_key(key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API Key不存在")
    
    # 非管理员只能看自己的keys
    if not user.get('is_admin') and key.get('created_by') != user.get('user_id'):
        raise HTTPException(status_code=403, detail="无权访问此Key")
    
    return ApiKeyResponse(
        id=key['id'],
        name=key['name'],
        key=None,
        key_hint=f"{key.get('key_prefix', '****')}...",
        key_prefix=key.get('key_prefix', '****'),
        is_active=bool(key.get('is_active')),
        rate_limit=key.get('rate_limit', 100),
        role=key.get('role', 'user'),
        permissions=key.get('permissions', []),
        expires_at=key.get('expires_at', ''),
        last_used_at=key.get('last_used_at'),
        created_at=key.get('created_at')
    )


@router.put("/{key_id}")
async def update_api_key(
    key_id: int,
    request: UpdateKeyRequest,
    authorization: str = Header(None)
):
    """更新API Key"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="无效token")
    
    # 非管理员只能更新自己的keys
    key = api_key_service.get_key(key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API Key不存在")
    
    if not user.get('is_admin') and key.get('created_by') != user.get('user_id'):
        raise HTTPException(status_code=403, detail="无权修改此Key")
    
    # 验证角色
    if request.role and request.role not in Role.PERMISSIONS:
        raise HTTPException(status_code=400, detail=f"无效的角色: {request.role}")
    
    updates = {}
    if request.name is not None:
        updates['name'] = request.name
    if request.role is not None:
        updates['role'] = request.role
    if request.rate_limit is not None:
        updates['rate_limit'] = request.rate_limit
    if request.expires_days is not None:
        updates['expires_days'] = request.expires_days
    if request.is_active is not None:
        updates['is_active'] = request.is_active
    
    api_key_service.update_key(key_id, **updates)
    return {"message": "API Key已更新"}


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: int,
    authorization: str = Header(None),
    soft: bool = Query(True, description="软删除")
):
    """删除API Key"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="无效token")
    
    # 非管理员只能删除自己的keys
    key = api_key_service.get_key(key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API Key不存在")
    
    if not user.get('is_admin') and key.get('created_by') != user.get('user_id'):
        raise HTTPException(status_code=403, detail="无权删除此Key")
    
    api_key_service.delete_key(key_id, soft=soft)
    return {"message": "API Key已删除"}


@router.get("/{key_id}/stats", response_model=UsageStatsResponse)
async def get_key_usage_stats(
    key_id: int,
    days: int = Query(7, ge=1, le=90),
    authorization: str = Header(None)
):
    """获取Key的使用统计"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="无效token")
    
    # 验证权限
    key = api_key_service.get_key(key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API Key不存在")
    
    if not user.get('is_admin') and key.get('created_by') != user.get('user_id'):
        raise HTTPException(status_code=403, detail="无权查看此Key的统计")
    
    stats = api_key_service.get_usage_stats(key_id=key_id, days=days)
    return UsageStatsResponse(**stats)


@router.get("/{key_id}/rate-limit")
async def get_rate_limit_status(
    key_id: int,
    authorization: str = Header(None)
):
    """获取速率限制状态"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="无效token")
    
    status = api_key_service.get_rate_limit_status(key_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    
    return status


@router.get("/stats/summary", response_model=UsageStatsResponse)
async def get_usage_stats_summary(
    days: int = Query(7, ge=1, le=90),
    authorization: str = Header(None)
):
    """获取所有Key的使用统计汇总（仅管理员）"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="无效token")
    
    if not user.get('is_admin'):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    stats = api_key_service.get_usage_stats(key_id=None, days=days)
    return UsageStatsResponse(**stats)


@router.post("/validate")
async def validate_api_key(key: str):
    """验证API Key（用于测试）"""
    result = api_key_service.validate_key(key)
    if result:
        return {
            "valid": True,
            "id": result.get('id'),
            "name": result.get('name'),
            "role": result.get('role', 'user'),
            "permissions": result.get('permissions', [])
        }
    return {"valid": False}


@router.get("/roles/list")
async def list_roles():
    """列出所有可用的角色及其权限"""
    return {
        "roles": [
            {"name": role, "permissions": perms}
            for role, perms in Role.PERMISSIONS.items()
        ]
    }