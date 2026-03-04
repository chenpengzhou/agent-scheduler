#!/usr/bin/env python3
"""
Agent 调度系统 - 数据库模块
"""
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


DB_PATH = "/home/robin/.openclaw/data/scheduler.db"


class TaskDB:
    """任务数据库"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                steps TEXT NOT NULL,
                current_step INTEGER DEFAULT 0,
                step TEXT,
                status TEXT DEFAULT '待处理',
                feedback TEXT DEFAULT '',
                history TEXT DEFAULT '[]',
                notify_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deadline TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                from_status TEXT,
                to_status TEXT,
                action TEXT,
                feedback TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _connect(self):
        return sqlite3.connect(self.db_path)
    
    def create_task(self, name: str, description: str, steps: List[str], deadline: str = None) -> Dict:
        """创建任务"""
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        step = steps[0] if steps else ""
        
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (id, name, description, steps, current_step, step, 
                status, feedback, history, notify_count, created_at, updated_at, deadline)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (task_id, name, description, json.dumps(steps), 0, step, 
              "待处理", "", "[]", 0, now, now, deadline or ""))
        conn.commit()
        conn.close()
        
        self.add_history(task_id, None, "待处理", "创建任务", "")
        return self.get_task(task_id)
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        return self._row_to_task(row) if row else None
    
    def get_all_tasks(self) -> List[Dict]:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_task(row) for row in rows]
    
    def get_pending_tasks(self) -> List[Dict]:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM tasks 
            WHERE status IN ('待处理', '待审核', '审核不通过')
            ORDER BY updated_at ASC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_task(row) for row in rows]
    
    def update_task_status(self, task_id: str, status: str, feedback: str = "", action: str = None) -> bool:
        now = datetime.now().isoformat()
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        old_status = row[0]
        cursor.execute("UPDATE tasks SET status = ?, feedback = ?, updated_at = ?, notify_count = 0 WHERE id = ?",
                     (status, feedback, now, task_id))
        conn.commit()
        conn.close()
        self.add_history(task_id, old_status, status, action or status, feedback)
        return True
    
    def update_step(self, task_id: str, step: str, current_step: int) -> bool:
        now = datetime.now().isoformat()
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET step = ?, current_step = ?, updated_at = ? WHERE id = ?",
                     (step, current_step, now, task_id))
        conn.commit()
        conn.close()
        return True
    
    def increment_notify(self, task_id: str) -> int:
        now = datetime.now().isoformat()
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET notify_count = notify_count + 1, updated_at = ? WHERE id = ?",
                     (now, task_id))
        conn.commit()
        cursor.execute("SELECT notify_count FROM tasks WHERE id = ?", (task_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def add_history(self, task_id: str, from_status: str, to_status: str, action: str, feedback: str):
        now = datetime.now().isoformat()
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO status_history (task_id, from_status, to_status, action, feedback, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (task_id, from_status, to_status, action, feedback, now))
        conn.commit()
        conn.close()
    
    def _row_to_task(self, row: tuple) -> Dict:
        return {
            "id": row[0], "name": row[1], "description": row[2],
            "steps": json.loads(row[3]), "current_step": row[4], "step": row[5],
            "status": row[6], "feedback": row[7], "history": json.loads(row[8]),
            "notify_count": row[9], "created_at": row[10], "updated_at": row[11], "deadline": row[12]
        }


db = TaskDB()
