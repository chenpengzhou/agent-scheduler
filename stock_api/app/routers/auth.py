# -*- coding: utf-8 -*-
"""
认证路由
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/auth", tags=["认证"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: dict


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    last_login: Optional[str] = None


def get_current_user(request: Request) -> dict:
    """获取当前用户"""
    return request.state.user


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """登录"""
    from app.auth import auth_service
    
    result = auth_service.authenticate(req.username, req.password)
    
    if not result:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    return result


@router.post("/logout")
async def logout(request: Request):
    """登出"""
    from app.auth import auth_service
    
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if token:
        auth_service.logout(token)
    
    return {"message": "登出成功"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    from app.auth import auth_service
    
    user = auth_service.get_user(current_user['sub'])
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return UserResponse(**user)
