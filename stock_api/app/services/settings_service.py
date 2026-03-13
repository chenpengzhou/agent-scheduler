# -*- coding: utf-8 -*-
"""
系统设置服务
"""
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime


class SettingsService:
    """系统设置服务"""
    
    def __init__(self, db_path: str = None):
        import os
        self.db_path = db_path or os.environ.get("STOCK_DB_PATH", os.path.expanduser("~/.openclaw/data/stock.db"))
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_users(self) -> List[Dict]:
        """获取用户列表"""
        conn = self._get_conn()
        
        try:
            df = conn.execute('''
                SELECT id, username, role, is_active, created_at, last_login
                FROM users
                ORDER BY id
            ''').fetchall()
            conn.close()
            return [dict(row) for row in df]
        except:
            conn.close()
            return []
    
    def create_user(self, username: str, password: str, role: str = "user") -> Dict:
        """创建用户"""
        import hashlib
        
        conn = self._get_conn()
        
        # 检查是否已存在
        existing = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            conn.close()
            return {"error": "用户名已存在"}
        
        # 创建用户
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn.execute('''
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, ?)
        ''', (username, password_hash, role))
        
        conn.commit()
        user_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.close()
        
        return {"message": "用户创建成功", "user_id": user_id}
    
    def update_user(self, user_id: int, data: Dict) -> Dict:
        """更新用户"""
        conn = self._get_conn()
        
        if "password" in data:
            import hashlib
            data["password_hash"] = hashlib.sha256(data["password"].encode()).hexdigest()
            del data["password"]
        
        if "username" in data:
            del data["username"]
        
        if data:
            set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
            values = list(data.values()) + [user_id]
            conn.execute(f'UPDATE users SET {set_clause} WHERE id = ?', values)
            conn.commit()
        
        conn.close()
        return {"message": "用户已更新"}
    
    def delete_user(self, user_id: int) -> Dict:
        """删除用户"""
        conn = self._get_conn()
        
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        return {"message": "用户已删除"}
    
    def get_sync_config(self) -> Dict:
        """获取同步配置"""
        conn = self._get_conn()
        
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sync_config (
                    id INTEGER PRIMARY KEY,
                    source TEXT,
                    interval_minutes INTEGER DEFAULT 60,
                    enabled INTEGER DEFAULT 1,
                    updated_at TEXT
                )
            ''')
            
            df = conn.execute('SELECT * FROM sync_config').fetchall()
            conn.close()
            
            return [dict(row) for row in df]
        except:
            conn.close()
            return []
    
    def update_sync_config(self, config: Dict) -> Dict:
        """更新同步配置"""
        conn = self._get_conn()
        
        # 确保表存在
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sync_config (
                id INTEGER PRIMARY KEY,
                source TEXT,
                interval_minutes INTEGER DEFAULT 60,
                enabled INTEGER DEFAULT 1,
                updated_at TEXT
            )
        ''')
        
        conn.execute('''
            INSERT OR REPLACE INTO sync_config (source, interval_minutes, enabled, updated_at)
            VALUES (?, ?, ?, ?)
        ''', (
            config["source"],
            config.get("interval_minutes", 60),
            config.get("enabled", 1),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return {"message": "配置已更新"}
    
    def get_api_keys(self) -> List[Dict]:
        """获取API Keys"""
        conn = self._get_conn()
        
        try:
            df = conn.execute('SELECT * FROM api_keys WHERE 1=0').fetchall()
        except:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    key TEXT,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT
                )
            ''')
            conn.commit()
            df = []
        
        conn.close()
        return []
    
    def create_api_key(self, name: str) -> Dict:
        """创建API Key"""
        import secrets
        
        conn = self._get_conn()
        
        # 确保表存在
        conn.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY,
                name TEXT,
                key TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT
            )
        ''')
        
        api_key = secrets.token_hex(32)
        
        conn.execute('''
            INSERT INTO api_keys (name, key, created_at)
            VALUES (?, ?, ?)
        ''', (name, api_key, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return {"message": "API Key已创建", "api_key": api_key}
    
    def get_system_info(self) -> Dict:
        """获取系统信息"""
        conn = self._get_conn()
        
        info = {}
        
        try:
            info["stock_count"] = conn.execute('SELECT COUNT(DISTINCT ts_code) FROM stock_daily').fetchone()[0] or 0
            info["record_count"] = conn.execute('SELECT COUNT(*) FROM stock_daily').fetchone()[0] or 0
        except:
            info["stock_count"] = 0
            info["record_count"] = 0
        
        conn.close()
        
        info["version"] = "1.0.0"
        info["uptime"] = "N/A"
        
        return info


# 全局实例
settings_service = SettingsService()
