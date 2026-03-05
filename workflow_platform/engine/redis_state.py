#!/usr/bin/env python3
"""
Redis 状态管理器 - 工作流引擎持久化
"""
import json
import redis
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import asdict, is_dataclass
from enum import Enum
import uuid

from .state import StateManager
from workflow_platform.models.workflow import (
    WorkflowInstance, StepInstance, TaskInstance,
    WorkflowStatus, StepStatus, TaskStatus
)


def serialize_datetime(obj):
    """序列化 datetime 对象"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def dataclass_to_dict(obj) -> Dict:
    """将 dataclass 转换为字典"""
    if obj is None:
        return {}
    
    result = {}
    data = asdict(obj) if is_dataclass(obj) else obj
    
    for key, value in data.items():
        if value is None:
            continue  # 跳过 None 值
        
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, Enum):
            result[key] = value.value
        elif isinstance(value, dict):
            result[key] = json.dumps(value, default=serialize_datetime)
        elif isinstance(value, list):
            result[key] = json.dumps(value, default=serialize_datetime)
        else:
            result[key] = value
    return result


def dict_to_dataclass(data: Dict, cls):
    """将字典转换为 dataclass"""
    if not data:
        return None
    
    # 转换枚举
    if 'status' in data and isinstance(data['status'], str):
        if cls == WorkflowInstance:
            data['status'] = WorkflowStatus(data['status'])
        elif cls == StepInstance:
            data['status'] = StepStatus(data['status'])
        elif cls == TaskInstance:
            data['status'] = TaskStatus(data['status'])
    
    # 转换时间字段
    for field in ['created_at', 'started_at', 'completed_at', 'updated_at']:
        if field in data and isinstance(data[field], str):
            try:
                data[field] = datetime.fromisoformat(data[field])
            except:
                pass
    
    # 转换 dict/list 字段
    for field in ['input_data', 'output_data', 'state', 'completed_steps', 'failed_steps', 
                  'input_params', 'output_result', 'metadata']:
        if field in data and isinstance(data[field], str):
            try:
                data[field] = json.loads(data[field])
            except:
                pass
    
    return cls(**data)


class RedisStateManager(StateManager):
    """Redis 状态管理器"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 1):
        """
        初始化 Redis 状态管理器
        
        Args:
            host: Redis 主机地址
            port: Redis 端口
            db: Redis 数据库编号（默认1，与调度系统分开）
        """
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
        self._prefix = "workflow"
    
    # ========== Key 定义 ==========
    def _workflow_key(self, workflow_id: str) -> str:
        return f"{self._prefix}:{workflow_id}:instance"
    
    def _step_key(self, step_id: str) -> str:
        return f"{self._prefix}:step:{step_id}"
    
    def _task_key(self, task_id: str) -> str:
        return f"{self._prefix}:task:{task_id}"
    
    def _workflow_steps_key(self, workflow_instance_id: str) -> str:
        return f"{self._prefix}:{workflow_instance_id}:steps"
    
    def _workflow_tasks_key(self, step_instance_id: str) -> str:
        return f"{self._prefix}:{step_instance_id}:tasks"
    
    def _node_status_key(self, workflow_id: str, node_name: str) -> str:
        return f"{self._prefix}:{workflow_id}:node:{node_name}"
    
    def _workflow_status_key(self, workflow_id: str) -> str:
        return f"{self._prefix}:{workflow_id}:status"
    
    # ========== 工作流实例 ==========
    def save_workflow(self, instance: WorkflowInstance) -> None:
        """保存工作流实例"""
        data = dataclass_to_dict(instance)
        
        # 存储到 Redis Hash
        self.redis.hset(self._workflow_key(instance.id), mapping=data)
        
        # 同时更新工作流状态索引
        self.redis.set(
            self._workflow_status_key(instance.id),
            instance.status.value if isinstance(instance.status, Enum) else instance.status
        )
    
    def load_workflow(self, instance_id: str) -> Optional[WorkflowInstance]:
        """加载工作流实例"""
        data = self.redis.hgetall(self._workflow_key(instance_id))
        if not data:
            return None
        return dict_to_dataclass(data, WorkflowInstance)
    
    def list_workflows(self) -> List[WorkflowInstance]:
        """列出所有工作流实例"""
        # 扫描所有 workflow:*:instance keys
        workflows = []
        for key in self.redis.scan_iter(match=f"{self._prefix}:*:instance"):
            data = self.redis.hgetall(key)
            if data:
                wf = dict_to_dataclass(data, WorkflowInstance)
                if wf:
                    workflows.append(wf)
        return workflows
    
    def delete_workflow(self, instance_id: str) -> bool:
        """删除工作流实例"""
        # 删除工作流
        self.redis.delete(self._workflow_key(instance_id))
        self.redis.delete(self._workflow_status_key(instance_id))
        
        # 删除关联的步骤和任务
        step_ids = self.redis.smembers(self._workflow_steps_key(instance_id))
        for step_id in step_ids:
            self.redis.delete(self._step_key(step_id))
            # 删除步骤关联的任务
            task_ids = self.redis.smembers(self._workflow_tasks_key(step_id))
            for task_id in task_ids:
                self.redis.delete(self._task_key(task_id))
            self.redis.delete(self._workflow_tasks_key(step_id))
        
        self.redis.delete(self._workflow_steps_key(instance_id))
        return True
    
    # ========== 步骤实例 ==========
    def save_step(self, instance: StepInstance) -> None:
        """保存步骤实例"""
        data = dataclass_to_dict(instance)
        self.redis.hset(self._step_key(instance.id), mapping=data)
        
        # 关联到工作流
        self.redis.sadd(self._workflow_steps_key(instance.workflow_instance_id), instance.id)
    
    def load_step(self, instance_id: str) -> Optional[StepInstance]:
        """加载步骤实例"""
        data = self.redis.hgetall(self._step_key(instance_id))
        if not data:
            return None
        return dict_to_dataclass(data, StepInstance)
    
    def get_steps_by_workflow(self, workflow_instance_id: str) -> List[StepInstance]:
        """获取工作流的所有步骤"""
        step_ids = self.redis.smembers(self._workflow_steps_key(workflow_instance_id))
        steps = []
        for step_id in step_ids:
            step = self.load_step(step_id)
            if step:
                steps.append(step)
        return steps
    
    # ========== 任务实例 ==========
    def save_task(self, instance: TaskInstance) -> None:
        """保存任务实例"""
        data = dataclass_to_dict(instance)
        self.redis.hset(self._task_key(instance.id), mapping=data)
        
        # 关联到步骤
        self.redis.sadd(self._workflow_tasks_key(instance.step_instance_id), instance.id)
    
    def load_task(self, instance_id: str) -> Optional[TaskInstance]:
        """加载任务实例"""
        data = self.redis.hgetall(self._task_key(instance_id))
        if not data:
            return None
        return dict_to_dataclass(data, TaskInstance)
    
    def get_tasks_by_step(self, step_instance_id: str) -> List[TaskInstance]:
        """获取步骤的所有任务"""
        task_ids = self.redis.smembers(self._workflow_tasks_key(step_instance_id))
        tasks = []
        for task_id in task_ids:
            task = self.load_task(task_id)
            if task:
                tasks.append(task)
        return tasks
    
    # ========== 节点状态查询（用于下游触发）==========
    def get_node_status(self, workflow_id: str, node_name: str) -> Optional[str]:
        """获取节点状态"""
        status = self.redis.hget(self._node_status_key(workflow_id, node_name), "status")
        return status
    
    def set_node_status(self, workflow_id: str, node_name: str, status: str) -> None:
        """设置节点状态"""
        self.redis.hset(
            self._node_status_key(workflow_id, node_name),
            mapping={
                "status": status,
                "updated_at": datetime.now().isoformat()
            }
        )
    
    def check_node_completion(self, workflow_id: str, node_name: str) -> bool:
        """检查节点是否已完成"""
        status = self.get_node_status(workflow_id, node_name)
        return status == "COMPLETED"
    
    def get_workflow_status(self, workflow_id: str) -> Optional[str]:
        """获取工作流整体状态"""
        return self.redis.get(self._workflow_status_key(workflow_id))
    
    def set_workflow_status(self, workflow_id: str, status: str) -> None:
        """设置工作流整体状态"""
        self.redis.set(self._workflow_status_key(workflow_id), status)
    
    # ========== 便捷方法 ==========
    def create_workflow(self, definition_id: str, input_data: Dict = None) -> WorkflowInstance:
        """创建工作流实例"""
        instance = WorkflowInstance(
            id=str(uuid.uuid4()),
            definition_id=definition_id,
            status=WorkflowStatus.PENDING,
            input_data=input_data or {},
            state={}
        )
        self.save_workflow(instance)
        return instance
    
    def get_or_create_workflow(self, workflow_id: str) -> Optional[WorkflowInstance]:
        """获取或创建工作流"""
        wf = self.load_workflow(workflow_id)
        if not wf:
            wf = WorkflowInstance(
                id=workflow_id,
                definition_id="",
                status=WorkflowStatus.PENDING
            )
            self.save_workflow(wf)
        return wf
    
    def clear_all(self) -> None:
        """清空所有工作流数据"""
        # 扫描并删除所有相关 keys
        for key in self.redis.scan_iter(match=f"{self._prefix}:*"):
            self.redis.delete(key)
