#!/usr/bin/env python3
"""
Redis 任务队列 - Agent 调度器
"""
import json
import redis
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys
sys.path.insert(0, "/home/robin/.openclaw/workspace-dev/scheduler")
from models import Task, TaskStatus, ScheduleType


class RedisQueue:
    """Redis 任务队列"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        # 配置连接池
        self.pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
            max_connections=20,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        self.redis = redis.Redis(connection_pool=self.pool)
        self._prefix = "scheduler"
    
    # ========== Key 定义 ==========
    def _task_key(self, task_id: str) -> str:
        return f"{self._prefix}:tasks:{task_id}"
    
    def _workflow_key(self, workflow_id: str) -> str:
        return f"{self._prefix}:workflows:{workflow_id}"
    
    @property
    def pending_queue(self) -> str:
        return f"{self._prefix}:queue:pending"
    
    @property
    def running_queue(self) -> str:
        return f"{self._prefix}:queue:running"
    
    @property
    def completed_queue(self) -> str:
        return f"{self._prefix}:queue:completed"
    
    @property
    def failed_queue(self) -> str:
        return f"{self._prefix}:queue:failed"
    
    @property
    def crontab_key(self) -> str:
        return f"{self._prefix}:crontab"
    
    @property
    def heartbeat_key(self) -> str:
        return f"{self._prefix}:heartbeat"
    
    # ========== 任务操作 ==========
    def create_task(self, task: Task) -> Task:
        """创建任务"""
        try:
            task_data = task.model_dump()
            task_data["created_at"] = task.created_at.isoformat()
            task_data["updated_at"] = task.updated_at.isoformat()
            if task.scheduled_at:
                task_data["scheduled_at"] = task.scheduled_at.isoformat()
            if task.started_at:
                task_data["started_at"] = task.started_at.isoformat()
            if task.completed_at:
                task_data["completed_at"] = task.completed_at.isoformat()
            
            # 将 dict 类型转为 JSON 字符串存储
            if "payload" in task_data and isinstance(task_data["payload"], dict):
                task_data["payload"] = json.dumps(task_data["payload"])
            if "result" in task_data and isinstance(task_data["result"], dict):
                task_data["result"] = json.dumps(task_data["result"])
            if "output" in task_data and isinstance(task_data["output"], dict):
                task_data["output"] = json.dumps(task_data["output"])
            if "depends_on" in task_data and isinstance(task_data["depends_on"], list):
                task_data["depends_on"] = json.dumps(task_data["depends_on"])
            if "required_fields" in task_data and isinstance(task_data["required_fields"], list):
                task_data["required_fields"] = json.dumps(task_data["required_fields"])
            
            # 过滤掉 None 值（Redis hset 不支持）
            task_data = {k: v for k, v in task_data.items() if v is not None}
            
            # 存储任务详情
            self.redis.hset(self._task_key(task.id), mapping=task_data)
            
            # 根据调度类型处理
            if task.schedule_type == ScheduleType.IMMEDIATE:
                # 检查任务是否已在任意队列中，避免重复添加
                all_queues = [
                    self.redis.lrange(self.pending_queue, 0, -1),
                    self.redis.lrange(self.running_queue, 0, -1),
                    self.redis.lrange(self.completed_queue, 0, -1),
                    self.redis.lrange(self.failed_queue, 0, -1)
                ]
                in_queue = any(task.id in queue for queue in all_queues)
                
                if not in_queue:
                    # 任务不在队列中，加入 pending 队列
                    self.redis.rpush(self.pending_queue, task.id)
            elif task.schedule_type == ScheduleType.CRON:
                # 定时任务，存储到 crontab
                self.redis.hset(self.crontab_key, task.id, json.dumps({
                    "task_id": task.id,
                    "cron_expr": task.cron_expr,
                    "enabled": True
                }))
            
            return task
        except Exception as e:
            print(f"❌ 创建任务失败: {e}")
            raise
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        try:
            task_data = self.redis.hgetall(self._task_key(task_id))
            if not task_data:
                return None
            
            # 转换时间字段
            for field in ["created_at", "updated_at", "scheduled_at", "started_at", "completed_at"]:
                if field in task_data and task_data[field]:
                    task_data[field] = datetime.fromisoformat(task_data[field])
            
            # 将 JSON 字符串转回 dict/list
            if "payload" in task_data and task_data["payload"]:
                task_data["payload"] = json.loads(task_data["payload"])
            if "result" in task_data and task_data["result"]:
                task_data["result"] = json.loads(task_data["result"])
            if "output" in task_data and task_data["output"]:
                task_data["output"] = json.loads(task_data["output"])
            if "depends_on" in task_data and task_data["depends_on"]:
                task_data["depends_on"] = json.loads(task_data["depends_on"])
            if "required_fields" in task_data and task_data["required_fields"]:
                task_data["required_fields"] = json.loads(task_data["required_fields"])
            
            # 转换枚举
            task_data["status"] = TaskStatus(task_data["status"])
            task_data["schedule_type"] = ScheduleType(task_data["schedule_type"])
            
            return Task(**task_data)
        except Exception as e:
            print(f"❌ 获取任务失败: {e}")
            return None
    
    def update_task(self, task: Task) -> Task:
        """更新任务"""
        task.updated_at = datetime.now()
        return self.create_task(task)
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        try:
            self.redis.delete(self._task_key(task_id))
            # 从各队列中移除
            self.redis.lrem(self.pending_queue, 0, task_id)
            self.redis.lrem(self.running_queue, 0, task_id)
            self.redis.lrem(self.completed_queue, 0, task_id)
            self.redis.lrem(self.failed_queue, 0, task_id)
            return True
        except Exception as e:
            print(f"❌ 删除任务失败: {e}")
            return False
    
    def get_pending_tasks(self, limit: int = 100) -> List[str]:
        """获取待执行任务 ID 列表"""
        try:
            return self.redis.lrange(self.pending_queue, 0, limit - 1)
        except Exception as e:
            print(f"❌ 获取待执行任务失败: {e}")
            return []
    
    def pop_pending_task(self) -> Optional[str]:
        """取出待执行任务"""
        try:
            return self.redis.lpop(self.pending_queue)
        except Exception as e:
            print(f"❌ 取出任务失败: {e}")
            return None
    
    def move_to_running(self, task_id: str) -> bool:
        """移动到运行中队列"""
        try:
            self.redis.lrem(self.pending_queue, 0, task_id)
            self.redis.rpush(self.running_queue, task_id)
            return True
        except Exception as e:
            print(f"❌ 移动到运行队列失败: {e}")
            return False
    
    def move_to_completed(self, task_id: str) -> bool:
        """移动到完成队列"""
        try:
            self.redis.lrem(self.running_queue, 0, task_id)
            self.redis.rpush(self.completed_queue, task_id)
            return True
        except Exception as e:
            print(f"❌ 移动到完成队列失败: {e}")
            return False
    
    def move_to_failed(self, task_id: str) -> bool:
        """移动到失败队列"""
        try:
            self.redis.lrem(self.running_queue, 0, task_id)
            self.redis.rpush(self.failed_queue, task_id)
            return True
        except Exception as e:
            print(f"❌ 移动到失败队列失败: {e}")
            return False
    
# 将 dict 类型转为 JSON 字符串存储
            if "dag" in wf_data and isinstance(wf_data["dag"], dict):
                wf_data["dag"] = json.dumps(wf_data["dag"])
            if "completed_tasks" in wf_data and isinstance(wf_data["completed_tasks"], list):
                wf_data["completed_tasks"] = json.dumps(wf_data["completed_tasks"])
            
            # 过滤掉 None 值
            wf_data = {k: v for k, v in wf_data.items() if v is not None}
            
            self.redis.hset(self._workflow_key(workflow.id), mapping=wf_data)
            
            # 创建 DAG 任务
            for task_id, deps in workflow.dag.items():
                task = Task(
                    id=task_id,
                    name=f"Workflow-{workflow.name}-{task_id}",
                    agent_id="",
                    schedule_type=ScheduleType.DAG,
                    depends_on=deps,
                    status=TaskStatus.PENDING
                )
                self.create_task(task)
            
            return workflow
        except Exception as e:
            print(f"❌ 创建工作流失败: {e}")
            raise
    
