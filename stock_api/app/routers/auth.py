# -*- coding: utf-8 -*-
"""
认证路由 - 8个API
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
    is_active: bool
    created_at: Optional[str] = None
    last_login: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UpdateUserRequest(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


def get_current_user(request: Request) -> dict:
    """获取当前用户"""
    return request.state.user


def require_admin(request: Request) -> dict:
    """需要管理员权限"""
    user = request.state.user
    if not user.get('is_admin'):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """1. 登录"""
    from app.auth import auth_service
    
    result = auth_service.authenticate(req.username, req.password)
    
    if not result:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    return result


@router.post("/logout")
async def logout(request: Request):
    """2. 登出"""
    from app.auth import auth_service
    
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if token:
        auth_service.logout(token)
    
    return {"message": "登出成功"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """3. 获取当前用户信息"""
    from app.auth import auth_service
    
    user = auth_service.get_user(current_user['sub'])
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return UserResponse(**user)


@router.post("/register", response_model=UserResponse)
async def register(req: RegisterRequest, current_user: dict = Depends(require_admin)):
    """4. 注册用户 (仅管理员)"""
    from app.auth import auth_service
    
    # 检查用户名是否已存在
    existing = auth_service.get_user(req.username)
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    user = auth_service.create_user(req.username, req.password, req.role)
    
    return UserResponse(
        id=user['id'],
        username=user['username'],
        role=user['role'],
        is_active=True
    )


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    """5. 修改密码"""
    from app.auth import auth_service
    
    success = auth_service.change_password(
        current_user['sub'],
        req.old_password,
        req.new_password
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="旧密码错误")
    
    return {"message": "密码修改成功"}


@router.post("/refresh")
async def refresh_token(request: Request):
    """6. 刷新令牌"""
    from app.auth import auth_service
    
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if not token:
        raise HTTPException(status_code=401, detail="缺少令牌")
    
    result = auth_service.refresh_token(token)
    
    if not result:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")
    
    return result


@router.get("/users", response_model=list)
async def get_users(current_user: dict = Depends(require_admin)):
    """7. 获取用户列表 (仅管理员)"""
    from app.auth import auth_service
    
    users = auth_service.get_all_users()
    
    return [UserResponse(**u) for u in users]


@router.put("/users/{user_id}")
async def update_user(user_id: int, req: UpdateUserRequest, current_user: dict = Depends(require_admin)):
    """8. 更新用户 (仅管理员)"""
    from app.auth import auth_service
    
    updates = {}
    if req.username:
        updates['username'] = req.username
    if req.role:
        updates['role'] = req.role
    if req.is_active is not None:
        updates['is_active'] = req.is_active
    
    success = auth_service.update_user(user_id, **updates)
    
    if not success:
        raise HTTPException(status_code=400, detail="更新失败")
    
    return {"message": "用户更新成功"}


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, current_user: dict = Depends(require_admin)):
    """9. 删除用户 (仅管理员)"""
    from app.auth import auth_service
    
    success = auth_service.delete_user(user_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="无法删除用户")
    
    return {"message": "用户删除成功"}
