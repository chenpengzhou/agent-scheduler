# -*- coding: utf-8 -*-
"""
认证服务 - bcrypt版
"""
from datetime import datetime, timedelta
from typing import Optional
import jwt
import os
from .utils.db import init_db, query_one, query_all, execute
from .config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_HOURS

# 默认管理员配置从环境变量获取
DEFAULT_ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


class AuthService:
    """认证服务"""
    
    def __init__(self):
        init_db()  # 确保数据库初始化
        self._ensure_default_user()
    
    def _ensure_default_user(self):
        """确保默认用户存在"""
        user = query_one("SELECT id FROM users WHERE username = ?", (DEFAULT_ADMIN_USERNAME,))
        if not user:
            password_hash = self.get_password_hash(DEFAULT_ADMIN_PASSWORD)
            execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (DEFAULT_ADMIN_USERNAME, password_hash, "admin")
            )
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """密码哈希"""
        try:
            import bcrypt
            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        except ImportError:
            # 如果bcrypt不可用，使用SHA256作为后备
            import hashlib
            return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """验证密码"""
        try:
            import bcrypt
            return bcrypt.checkpw(plain.encode(), hashed.encode())
        except ImportError:
            # 后备验证
            import hashlib
            return hashlib.sha256(plain.encode()).hexdigest() == hashed
    
    def create_access_token(self, data: dict) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    def verify_token(self, token: str) -> Optional[dict]:
        """验证令牌"""
        # 检查是否在黑名单
        blacklisted = query_one(
            "SELECT id FROM token_blacklist WHERE token = ?",
            (token,)
        )
        if blacklisted:
            return None
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def authenticate(self, username: str, password: str) -> Optional[dict]:
        """认证用户"""
        user = query_one(
            "SELECT id, username, password_hash, role, is_active FROM users WHERE username = ?",
            (username,)
        )
        
        if not user:
            return None
        
        if not user['is_active']:
            return None
        
        if not self.verify_password(password, user['password_hash']):
            return None
        
        # 更新最后登录时间
        execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now().isoformat(), user['id'])
        )
        
        is_admin = user['role'] == 'admin'
        
        # 生成Token
        access_token = self.create_access_token({
            "sub": user['username'],
            "user_id": user['id'],
            "is_admin": is_admin
        })
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_HOURS * 3600,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "is_admin": is_admin
            }
        }
    
    def logout(self, token: str) -> bool:
        """登出 - 将token加入黑名单"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            expired_at = datetime.fromtimestamp(payload['exp'])
            
            execute(
                "INSERT INTO token_blacklist (token, expired_at) VALUES (?, ?)",
                (token, expired_at.isoformat())
            )
            return True
        except:
            return False
    
    def get_user(self, username: str) -> Optional[dict]:
        """获取用户信息"""
        user = query_one(
            "SELECT id, username, role, is_active, created_at, last_login FROM users WHERE username = ?",
            (username,)
        )
        if user:
            user['is_admin'] = user['role'] == 'admin'
        return user
    
    def get_all_users(self) -> list:
        """获取所有用户"""
        users = query_all("SELECT id, username, role, is_active, created_at, last_login FROM users ORDER BY id")
        for u in users:
            u['is_admin'] = u['role'] == 'admin'
        return users
    
    def create_user(self, username: str, password: str, role: str = "user") -> dict:
        """创建用户"""
        password_hash = self.get_password_hash(password)
        user_id = execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, password_hash, role)
        )
        return {"id": user_id, "username": username, "role": role}
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """更新用户"""
        allowed_fields = ['username', 'role', 'is_active']
        updates = []
        values = []
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(user_id)
        execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            tuple(values)
        )
        return True
    
    def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        # 不能删除admin用户
        user = query_one("SELECT role FROM users WHERE id = ?", (user_id,))
        if not user or user['role'] == 'admin':
            return False
        
        execute("DELETE FROM users WHERE id = ?", (user_id,))
        return True
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """修改密码"""
        user = query_one("SELECT password_hash FROM users WHERE username = ?", (username,))
        
        if not user:
            return False
        
        if not self.verify_password(old_password, user['password_hash']):
            return False
        
        new_hash = self.get_password_hash(new_password)
        execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_hash, username))
        return True
    
    def refresh_token(self, token: str) -> Optional[dict]:
        """刷新令牌"""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        user = query_one(
            "SELECT id, username, role, is_active FROM users WHERE username = ?",
            (payload['sub'],)
        )
        
        if not user or not user['is_active']:
            return None
        
        is_admin = user['role'] == 'admin'
        new_token = self.create_access_token({
            "sub": user['username'],
            "user_id": user['id'],
            "is_admin": is_admin
        })
        
        return {
            "access_token": new_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_HOURS * 3600
        }


# 全局认证服务
auth_service = AuthService()
