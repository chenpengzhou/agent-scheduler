# -*- coding: utf-8 -*-
"""
API Keys 管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from app.services.api_key_service import api_key_service
from app.auth import get_current_user

router = APIRouter(prefix="/api/admin/api-keys", tags=["API Keys"])

class CreateKeyRequest(BaseModel):
    name: str
    role: str = "user"
    rate_limit: int = 100
    expires_days: int = 365

class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key: str = None  # 创建时返回完整key
    key_hint: str
    rate_limit: int
    role: str
    expires_at: str

@router.post("/", response_model=ApiKeyResponse)
async def create_api_key(
    request: CreateKeyRequest,
    authorization: str = Header(None)
):
    """创建新的API Key"""
    # 从authorization header获取当前用户
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="无效token")
    
    result = api_key_service.create_key(
        name=request.name,
        user_id=user["id"],
        role=request.role,
        rate_limit=request.rate_limit,
        expires_days=request.expires_days
    )
    
    return result

@router.get("/", response_model=List[dict])
async def list_api_keys(authorization: str = Header(None)):
    """列出所有API Keys"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="无效token")
    
    return api_key_service.list_keys(user_id=user["id"])

@router.delete("/{key_id}")
async def delete_api_key(key_id: int, authorization: str = Header(None)):
    """删除API Key"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="无效token")
    
    api_key_service.delete_key(key_id)
    return {"message": "API Key已删除"}

@router.get("/stats")
async def get_usage_stats(authorization: str = Header(None)):
    """获取使用统计"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    
    token = authorization.replace("Bearer ", "")
    user = get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="无效token")
    
    return api_key_service.get_usage_stats()

@router.post("/validate")
async def validate_api_key(key: str):
    """验证API Key（用于测试）"""
    result = api_key_service.validate_key(key)
    if result:
        return {"valid": True, "role": result.get("role", "user")}
    return {"valid": False}
