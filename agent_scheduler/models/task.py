"""
任务数据模型
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "PENDING"       # 待执行
    RUNNING = "RUNNING"       # 执行中
    COMPLETED = "COMPLETED"   # 已完成
    FAILED = "FAILED"         # 失败
    CANCELLED = "CANCELLED"   # 已取消
    RETRYING = "RETRYING"     # 重试中


class TaskPriority(Enum):
    """任务优先级"""
    P0 = 0  # 紧急
    P1 = 1  # 高
    P2 = 2  # 中
    P3 = 3  # 低


class TaskType(Enum):
    """任务类型"""
    AGENT = "AGENT"     # Agent任务
    SCRIPT = "SCRIPT"   # 脚本任务
    API = "API"         # API调用任务


@dataclass
class Task:
    """任务"""
    id: str = ""
    name: str = ""
    description: str = ""
    
    # 关联
    demand_id: str = ""         # 关联的需求ID
    workflow_instance_id: str = ""  # 关联的工作流实例
    parent_task_id: str = ""    # 父任务ID（依赖）
    
    # 类型和优先级
    task_type: TaskType = TaskType.AGENT
    priority: TaskPriority = TaskPriority.P2
    
    # 状态
    status: TaskStatus = TaskStatus.PENDING
    
    # 执行信息
    assigned_agent_id: str = ""  # 分配的Agent
    next_agent_id: str = ""     # 下一个处理者
    executor_type: str = "agent"  # 执行器类型
    executor_params: Dict[str, Any] = field(default_factory=dict)  # 执行参数
    
    # 输入输出
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    
    # 依赖
    depends_on: List[str] = field(default_factory=list)  # 依赖的任务ID列表
    
    # 重试
    retry_count: int = 0
    max_retries: int = 3
    retry_delay_seconds: int = 60
    
    # 时间
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 错误信息
    error_message: str = ""
    error_details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class TaskExecution:
    """任务执行记录"""
    id: str = ""
    task_id: str = ""
    agent_id: str = ""
    status: TaskStatus = TaskStatus.PENDING
    
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    output: str = ""
    error: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
