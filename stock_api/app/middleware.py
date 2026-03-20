# -*- coding: utf-8 -*-
"""
中间件 - Token验证 + API Key认证
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.auth import auth_service
from app.services.api_key_service import api_key_service


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件 - 支持 Bearer Token 和 API Key"""
    
    # 公开路径（完全匹配）
    PUBLIC_PATHS = [
        "/",
        "/health",
        "/docs",
        "/openapi.json",
    ]
    
    # 公开路由前缀（需要认证的路径不包含）
    PUBLIC_PREFIXES = [
        "/static",
        "/templates",
    ]
    
    # 需要公开的认证相关路径
    PUBLIC_AUTH_PATHS = [
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/refresh",
        "/api/admin/api-keys/validate",  # Key验证接口公开
        "/api/admin/api-keys/roles/list",  # 角色列表公开
    ]
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # 检查是否公开
        if path in self.PUBLIC_PATHS or path in self.PUBLIC_AUTH_PATHS:
            return await call_next(request)
        
        for prefix in self.PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)
        
        # 尝试 API Key 认证
        x_api_key = request.headers.get("X-API-Key")
        if x_api_key:
            key_info = api_key_service.validate_key(x_api_key)
            if key_info:
                request.state.user = key_info
                request.state.auth_type = "api_key"
                return await call_next(request)
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired API Key"}
            )
        
        # 尝试 Bearer Token 认证
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing authentication. Provide X-API-Key header or Bearer token"}
            )
        
        token = auth_header.replace("Bearer ", "")
        payload = auth_service.verify_token(token)
        
        if not payload:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"}
            )
        
        # 将用户信息存入request.state
        request.state.user = payload
        request.state.auth_type = "bearer"
        
        return await call_next(request)