# -*- coding: utf-8 -*-
"""
中间件 - Token验证
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.auth import auth_service


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件"""
    
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
    ]
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # 检查是否公开
        if path in self.PUBLIC_PATHS or path in self.PUBLIC_AUTH_PATHS:
            return await call_next(request)
        
        for prefix in self.PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)
        
        # 验证Token
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid token"}
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
        
        return await call_next(request)
