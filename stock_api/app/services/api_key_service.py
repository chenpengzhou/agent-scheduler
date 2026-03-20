# -*- coding: utf-8 -*-
"""
API Key 管理服务 - 增强版
支持角色权限和使用量统计
"""
import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.utils.db import query_one, query_all, execute, get_connection


# 角色定义
class Role:
    ADMIN = "admin"           # 管理员 - 所有权限
    TRADER = "trader"         # 操盘手 - 交易相关权限
    STRATEGIST = "strategist" # 策略专家 - 策略相关权限
    USER = "user"             # 普通用户 - 基础权限
    
    # 角色权限映射
    PERMISSIONS = {
        ADMIN: ["*"],  # 所有权限
        TRADER: [
            "stocks:read",
            "positions:read",
            "positions:write",
            "account:read",
            "trades:read",
            "trades:write",
            "paper_trade:read",
            "paper_trade:write",
        ],
        STRATEGIST: [
            "stocks:read",
            "strategies:read",
            "strategies:write",
            "backtest:read",
            "backtest:write",
            "factors:read",
            "paper_trade:read",
        ],
        USER: [
            "stocks:read",
            "account:read",
        ],
    }
    
    @classmethod
    def get_permissions(cls, role: str) -> List[str]:
        """获取角色权限列表"""
        return cls.PERMISSIONS.get(role, cls.PERMISSIONS[cls.USER])
    
    @classmethod
    def has_permission(cls, role: str, permission: str) -> bool:
        """检查角色是否有指定权限"""
        perms = cls.get_permissions(role)
        return "*" in perms or permission in perms


class ApiKeyService:
    """API Key 管理服务"""
    
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        """确保数据库表存在"""
        from app.utils.db import init_db
        init_db()
    
    @staticmethod
    def generate_key() -> str:
        """生成随机API Key"""
        return f"sk_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def hash_key(key: str) -> str:
        """哈希API Key用于存储"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    @staticmethod
    def get_key_prefix(key: str) -> str:
        """获取Key前缀用于快速查找"""
        if key.startswith("sk_"):
            return key[:12]
        return key[:8]
    
    def create_key(self, name: str, user_id: int, role: str = "user", 
                   rate_limit: int = 100, expires_days: int = 365,
                   permissions: List[str] = None) -> Dict:
        """创建新的API Key"""
        key_value = self.generate_key()
        key_hash = self.hash_key(key_value)
        key_prefix = self.get_key_prefix(key_value)
        expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
        
        # 如果没有指定权限，使用角色默认权限
        if permissions is None:
            permissions = Role.get_permissions(role)
        permissions_json = json.dumps(permissions)
        
        key_id = execute('''
            INSERT INTO api_keys (name, key_value, key_prefix, is_active, rate_limit, role, permissions, created_by, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, key_hash, key_prefix, 1, rate_limit, role, permissions_json, user_id, expires_at))
        
        return {
            "id": key_id,
            "name": name,
            "key": key_value,  # 返回完整key，只显示一次
            "key_hint": f"{key_value[:8]}...",
            "key_prefix": key_prefix,
            "is_active": True,
            "rate_limit": rate_limit,
            "role": role,
            "permissions": permissions,
            "expires_at": expires_at
        }
    
    def list_keys(self, user_id: int = None, include_inactive: bool = False) -> List[Dict]:
        """列出API Keys"""
        if user_id:
            if include_inactive:
                keys = query_all('''
                    SELECT id, name, key_prefix, is_active, rate_limit, role, permissions, created_at, expires_at, last_used_at, created_by
                    FROM api_keys WHERE created_by = ?
                    ORDER BY created_at DESC
                ''', (user_id,))
            else:
                keys = query_all('''
                    SELECT id, name, key_prefix, is_active, rate_limit, role, permissions, created_at, expires_at, last_used_at, created_by
                    FROM api_keys WHERE created_by = ? AND is_active = 1
                    ORDER BY created_at DESC
                ''', (user_id,))
        else:
            if include_inactive:
                keys = query_all('''
                    SELECT id, name, key_prefix, is_active, rate_limit, role, permissions, created_at, expires_at, last_used_at, created_by
                    FROM api_keys ORDER BY created_at DESC
                ''')
            else:
                keys = query_all('''
                    SELECT id, name, key_prefix, is_active, rate_limit, role, permissions, created_at, expires_at, last_used_at, created_by
                    FROM api_keys WHERE is_active = 1
                    ORDER BY created_at DESC
                ''')
        
        result = []
        for k in keys:
            item = dict(k)
            # 解析权限JSON
            if item.get('permissions'):
                try:
                    item['permissions'] = json.loads(item['permissions'])
                except:
                    item['permissions'] = []
            result.append(item)
        return result
    
    def get_key(self, key_id: int) -> Optional[Dict]:
        """获取单个Key详情"""
        key = query_one('''
            SELECT id, name, key_prefix, is_active, rate_limit, role, permissions, created_at, expires_at, last_used_at, created_by
            FROM api_keys WHERE id = ?
        ''', (key_id,))
        
        if key:
            item = dict(key)
            if item.get('permissions'):
                try:
                    item['permissions'] = json.loads(item['permissions'])
                except:
                    item['permissions'] = []
            return item
        return None
    
    def update_key(self, key_id: int, **kwargs) -> bool:
        """更新API Key"""
        allowed_fields = ['name', 'is_active', 'rate_limit', 'role', 'expires_days']
        updates = []
        values = []
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                if field == 'expires_days':
                    updates.append("expires_at = ?")
                    values.append((datetime.now() + timedelta(days=value)).isoformat())
                elif field == 'role' and value:
                    updates.append("role = ?")
                    values.append(value)
                    # 同时更新权限
                    perms = Role.get_permissions(value)
                    updates.append("permissions = ?")
                    values.append(json.dumps(perms))
                else:
                    updates.append(f"{field} = ?")
                    values.append(value)
        
        if not updates:
            return False
        
        values.append(key_id)
        execute(
            f"UPDATE api_keys SET {', '.join(updates)} WHERE id = ?",
            tuple(values)
        )
        return True
    
    def delete_key(self, key_id: int, soft: bool = True) -> bool:
        """删除API Key"""
        if soft:
            execute('UPDATE api_keys SET is_active = 0 WHERE id = ?', (key_id,))
        else:
            execute('DELETE FROM api_keys WHERE id = ?', (key_id,))
        return True
    
    def validate_key(self, key: str) -> Optional[Dict]:
        """验证API Key"""
        # 先用前缀快速查找
        key_prefix = self.get_key_prefix(key)
        
        # 查找匹配的key
        candidates = query_all('''
            SELECT * FROM api_keys WHERE key_prefix = ? AND is_active = 1
        ''', (key_prefix,))
        
        for candidate in candidates:
            # 验证hash
            if candidate['key_value'] == self.hash_key(key):
                # 检查是否过期
                if candidate.get('expires_at'):
                    try:
                        expires = datetime.fromisoformat(candidate['expires_at'])
                        if expires < datetime.now():
                            return None  # 已过期
                    except:
                        pass
                
                # 更新最后使用时间
                execute(
                    "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), candidate['id'])
                )
                
                # 解析权限
                result = dict(candidate)
                if result.get('permissions'):
                    try:
                        result['permissions'] = json.loads(result['permissions'])
                    except:
                        result['permissions'] = []
                return result
        
        return None
    
    def check_permission(self, key: str, permission: str) -> bool:
        """检查API Key是否有指定权限"""
        key_info = self.validate_key(key)
        if not key_info:
            return False
        
        role = key_info.get('role', 'user')
        perms = key_info.get('permissions', [])
        
        # admin角色有所有权限
        if role == Role.ADMIN or "*" in perms:
            return True
        
        return permission in perms
    
    def record_usage(self, api_key_id: int, endpoint: str, method: str, 
                     status_code: int = 200, response_time_ms: int = 0):
        """记录API使用量"""
        execute('''
            INSERT INTO api_usage (api_key_id, endpoint, method, status_code, response_time_ms)
            VALUES (?, ?, ?, ?, ?)
        ''', (api_key_id, endpoint, method, status_code, response_time_ms))
    
    def get_usage_stats(self, key_id: int = None, days: int = 7) -> Dict:
        """获取使用统计"""
        stats = {
            "total_calls": 0,
            "daily_stats": [],
            "endpoint_stats": [],
            "key_stats": []
        }
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # 时间范围
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        if key_id:
            # 单个Key的统计
            cursor.execute('''
                SELECT COUNT(*) as cnt, 
                       SUM(response_time_ms) as total_time,
                       AVG(response_time_ms) as avg_time
                FROM api_usage 
                WHERE api_key_id = ? AND call_time >= ?
            ''', (key_id, since))
            row = cursor.fetchone()
            stats["total_calls"] = row['cnt'] if row else 0
            stats["avg_response_ms"] = int(row['avg_time']) if row and row['avg_time'] else 0
            
            # 每日统计
            cursor.execute('''
                SELECT DATE(call_time) as day, COUNT(*) as calls
                FROM api_usage 
                WHERE api_key_id = ? AND call_time >= ?
                GROUP BY DATE(call_time)
                ORDER BY day DESC
            ''', (key_id, since))
            stats["daily_stats"] = [dict(r) for r in cursor.fetchall()]
            
            # 端点统计
            cursor.execute('''
                SELECT endpoint, method, COUNT(*) as calls, AVG(response_time_ms) as avg_ms
                FROM api_usage 
                WHERE api_key_id = ? AND call_time >= ?
                GROUP BY endpoint, method
                ORDER BY calls DESC
            ''', (key_id, since))
            stats["endpoint_stats"] = [dict(r) for r in cursor.fetchall()]
            
        else:
            # 所有Key的统计
            cursor.execute('''
                SELECT COUNT(*) as cnt FROM api_usage WHERE call_time >= ?
            ''', (since,))
            row = cursor.fetchone()
            stats["total_calls"] = row['cnt'] if row else 0
            
            # 每日统计
            cursor.execute('''
                SELECT DATE(call_time) as day, COUNT(*) as calls
                FROM api_usage 
                WHERE call_time >= ?
                GROUP BY DATE(call_time)
                ORDER BY day DESC
            ''', (since,))
            stats["daily_stats"] = [dict(r) for r in cursor.fetchall()]
            
            # Key统计排行
            cursor.execute('''
                SELECT ak.name, ak.role, COUNT(au.id) as calls
                FROM api_keys ak
                LEFT JOIN api_usage au ON ak.id = au.api_key_id AND au.call_time >= ?
                GROUP BY ak.id, ak.name, ak.role
                ORDER BY calls DESC
                LIMIT 20
            ''', (since,))
            stats["key_stats"] = [dict(r) for r in cursor.fetchall()]
        
        conn.close()
        return stats
    
    def get_rate_limit_status(self, key_id: int) -> Dict:
        """获取速率限制状态"""
        key = self.get_key(key_id)
        if not key:
            return {"error": "Key not found"}
        
        # 获取当天使用量
        today = datetime.now().strftime('%Y-%m-%d')
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) as cnt FROM api_usage 
            WHERE api_key_id = ? AND DATE(call_time) = ?
        ''', (key_id, today))
        row = cursor.fetchone()
        conn.close()
        
        used = row['cnt'] if row else 0
        limit = key.get('rate_limit', 100)
        
        return {
            "key_id": key_id,
            "key_name": key['name'],
            "rate_limit": limit,
            "used_today": used,
            "remaining": max(0, limit - used),
            "reset_at": f"{today} 23:59:59"
        }


# 全局实例
api_key_service = ApiKeyService()