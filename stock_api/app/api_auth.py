# -*- coding: utf-8 -*-
"""
API 认证依赖 - 支持 Bearer Token 和 API Key
"""
from fastapi import Header, HTTPException, Request, Depends
from typing import Optional
from functools import wraps

from app.auth import auth_service
from app.services.api_key_service import api_key_service, Role


class AuthResult:
    """认证结果"""
    def __init__(self, auth_type: str, user_info: dict):
        self.auth_type = auth_type  # 'bearer' or 'api_key'
        self.user_info = user_info
        self.key_id = user_info.get('id') if auth_type == 'api_key' else None
        self.user_id = user_info.get('user_id') if auth_type == 'bearer' else None
        self.role = user_info.get('role', 'user') if auth_type == 'api_key' else ('admin' if user_info.get('is_admin') else 'user')
        self.permissions = user_info.get('permissions', [])
    
    def has_permission(self, permission: str) -> bool:
        """检查是否有指定权限"""
        # admin有所有权限
        if self.role == Role.ADMIN or "*" in self.permissions:
            return True
        return permission in self.permissions


def get_auth_result(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> AuthResult:
    """
    获取认证结果 - 同时支持 Bearer Token 和 API Key
    
    优先级：
    1. X-API-Key header (API Key认证)
    2. Authorization: Bearer <token> (JWT认证)
    """
    # 优先使用 API Key
    if x_api_key:
        key_info = api_key_service.validate_key(x_api_key)
        if key_info:
            return AuthResult(auth_type='api_key', user_info=key_info)
        raise HTTPException(status_code=401, detail="无效的API Key或已过期")
    
    # 其次使用 Bearer Token
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        payload = auth_service.verify_token(token)
        if payload:
            return AuthResult(auth_type='bearer', user_info=payload)
        raise HTTPException(status_code=401, detail="无效或已过期的Token")
    
    raise HTTPException(status_code=401, detail="缺少认证信息，请提供 X-API-Key 或 Bearer Token")


def require_auth(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> AuthResult:
    """需要认证"""
    return get_auth_result(authorization, x_api_key)


def require_permission(permission: str):
    """
    需要指定权限的装饰器/依赖
    
    用法:
    @router.get("/endpoint")
    async def endpoint(auth: AuthResult = Depends(require_permission("stocks:read"))):
        ...
    """
    def dependency(
        authorization: Optional[str] = Header(None),
        x_api_key: Optional[str] = Header(None, alias="X-API-Key")
    ) -> AuthResult:
        auth_result = get_auth_result(authorization, x_api_key)
        
        if not auth_result.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"需要权限: {permission}，当前角色: {auth_result.role}"
            )
        
        return auth_result
    
    return dependency


def require_role(role: str):
    """
    需要指定角色的装饰器/依赖
    
    用法:
    @router.get("/admin-only")
    async def admin_endpoint(auth: AuthResult = Depends(require_role("admin"))):
        ...
    """
    def dependency(
        authorization: Optional[str] = Header(None),
        x_api_key: Optional[str] = Header(None, alias="X-API-Key")
    ) -> AuthResult:
        auth_result = get_auth_result(authorization, x_api_key)
        
        if auth_result.role != role and auth_result.role != Role.ADMIN:
            raise HTTPException(
                status_code=403,
                detail=f"需要角色: {role}，当前角色: {auth_result.role}"
            )
        
        return auth_result
    
    return dependency


def get_current_auth(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Optional[AuthResult]:
    """获取当前认证信息，找不到返回None"""
    try:
        return get_auth_result(authorization, x_api_key)
    except HTTPException:
        return None


def record_api_usage(endpoint: str, method: str):
    """
    记录API使用量的依赖
    
    用法:
    @router.get("/endpoint")
    async def endpoint(
        auth: AuthResult = Depends(require_auth),
        _usage: None = Depends(record_api_usage("/api/endpoint", "GET"))
    ):
        ...
    """
    def dependency(
        authorization: Optional[str] = Header(None),
        x_api_key: Optional[str] = Header(None, alias="X-API-Key")
    ):
        import time
        start_time = time.time()
        
        # 获取认证
        auth_result = None
        try:
            auth_result = get_auth_result(authorization, x_api_key)
        except HTTPException:
            pass
        
        # 记录使用量（异步更好，这里简化）
        if auth_result and auth_result.key_id:
            elapsed_ms = int((time.time() - start_time) * 1000)
            api_key_service.record_usage(
                api_key_id=auth_result.key_id,
                endpoint=endpoint,
                method=method,
                status_code=200,
                response_time_ms=elapsed_ms
            )
        
        return auth_result
    
    return dependency