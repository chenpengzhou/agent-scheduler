# -*- coding: utf-8 -*-
"""
API Key 管理服务
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.utils.db import query_one, query_all, execute


class ApiKeyService:
    """API Key 管理服务"""
    
    @staticmethod
    def generate_key() -> str:
        """生成随机API Key"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_key(key: str) -> str:
        """哈希API Key用于存储"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def create_key(self, name: str, user_id: int, role: str = "user", 
                   rate_limit: int = 100, expires_days: int = 365) -> Dict:
        """创建新的API Key"""
        key_value = self.generate_key()
        key_hash = self.hash_key(key_value)
        expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
        
        key_id = execute('''
            INSERT INTO api_keys (name, key_value, is_active, rate_limit, created_by, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, key_hash, 1, rate_limit, user_id, expires_at))
        
        return {
            "id": key_id,
            "name": name,
            "key": key_value,  # 返回完整key，只显示一次
            "key_hint": f"sk_{key_value[:8]}...",
            "rate_limit": rate_limit,
            "role": role,
            "expires_at": expires_at
        }
    
    def list_keys(self, user_id: int = None) -> List[Dict]:
        """列出API Keys"""
        if user_id:
            keys = query_all('''
                SELECT id, name, is_active, rate_limit, created_at, expires_at
                FROM api_keys WHERE created_by = ?
                ORDER BY created_at DESC
            ''', (user_id,))
        else:
            keys = query_all('''
                SELECT id, name, is_active, rate_limit, created_at, expires_at
                FROM api_keys ORDER BY created_at DESC
            ''')
        
        return [dict(k) for k in keys]
    
    def delete_key(self, key_id: int) -> bool:
        """删除API Key"""
        execute('DELETE FROM api_keys WHERE id = ?', (key_id,))
        return True
    
    def validate_key(self, key: str) -> Optional[Dict]:
        """验证API Key"""
        key_hash = self.hash_key(key)
        result = query_one('''
            SELECT * FROM api_keys WHERE key_value = ? AND is_active = 1
        ''', (key_hash,))
        
        if not result:
            # 尝试直接匹配（未哈希的key）
            result = query_one('''
                SELECT * FROM api_keys WHERE key_value = ? AND is_active = 1
            ''', (key,))
        
        if result:
            # 检查是否过期
            if result.get('expires_at'):
                expires = datetime.fromisoformat(result['expires_at'])
                if expires < datetime.now():
                    return None  # 已过期
            return dict(result)
        return None
    
    def get_usage_stats(self, key_id: int = None) -> Dict:
        """获取使用统计"""
        # 这里简化实现，实际应该记录每次API调用
        if key_id:
            keys = query_all('''
                SELECT name, rate_limit FROM api_keys WHERE id = ?
            ''', (key_id,))
        else:
            keys = query_all('''
                SELECT name, rate_limit FROM api_keys WHERE is_active = 1
            ''')
        
        return {
            "active_keys": len(keys),
            "total_keys": query_one('SELECT COUNT(*) as cnt FROM api_keys')[0] if query_one('SELECT COUNT(*) as cnt FROM api_keys') else 0
        }


# 全局实例
api_key_service = ApiKeyService()
