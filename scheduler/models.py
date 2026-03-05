#!/usr/bin/env python3
"""
数据模型 - Agent 任务调度器 & 工作流引擎
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


# ========== 调度系统模型 ==========

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduleType(str, Enum):
    IMMEDIATE = "immediate"
    CRON = "cron"
    DAG = "dag"


class Task(BaseModel):
    """任务模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    chain_id: Optional[str] = None  # 所属链ID
    name: str
    agent_id: str
    
    # 消息内容
    message: str = ""
    
    # 执行配置
    payload: Dict[str, Any] = Field(default_factory=dict)
    timeout: int = 300
    retry: int = 0
    
    # 调度配置
    schedule_type: ScheduleType = ScheduleType.IMMEDIATE
    cron_expr: Optional[str] = None
    depends_on: List[str] = Field(default_factory=list)
    
    # 创建者
    created_by: Optional[str] = ""
    
    # Agent输出
    output: Optional[Dict[str, Any] | str] = None
    output_format: Optional[str] = None  # json/text/plain
    required_fields: List[str] = Field(default_factory=list)
    
    # 状态：pending → running → completed/failed
    status: TaskStatus = TaskStatus.PENDING
    
    # 下游触发标记
    downstream_triggered: bool = False  # 是否已触发下游节点
    
    # 执行结果
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 5
    
    # 时间
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class AgentConfig(BaseModel):
    """Agent配置模型"""
    agent_id: str
    account: str  # 发送账号
    channel: str = "feishu"
    default_group: str = "oc_655d32450caf2473e50b5197ff6a7d44"
    description: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)


# ========== 工作流引擎模型 ==========

class WorkflowStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"


class WorkflowTemplate(BaseModel):
    """工作流模板"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    yaml_content: str = ""
    version: int = 1
    created_by: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class WorkflowInstance(BaseModel):
    """工作流实例"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    template_id: str
    template_name: str = ""
    status: WorkflowStatus = WorkflowStatus.PAUSED
    trigger_input: Dict[str, Any] = Field(default_factory=dict)
    current_node: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)


class NodeExecution(BaseModel):
    """节点执行"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    instance_id: str
    node_name: str
    agent_id: str
    
    # 消息和输出
    message: str = ""
    output: Optional[Dict[str, Any] | str] = None
    output_format: Optional[str] = None
    required_fields: List[str] = Field(default_factory=list)
    
    # 状态
    status: NodeStatus = NodeStatus.PENDING
    retry_count: int = 0
    
    # 审批
    requires_approval: bool = False
    approver: Optional[str] = None
    approval_decision: Optional[str] = None  # approve/reject
    
    # 依赖
    depends_on: List[str] = Field(default_factory=list)
    
    # 时间
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)


class WorkflowNode(BaseModel):
    """工作流节点定义（YAML解析后）"""
    name: str
    agent: str
    message: str = ""
    depends_on: List[str] = Field(default_factory=list)
    output_format: Optional[str] = None
    required_fields: List[str] = Field(default_factory=list)
    requires_approval: bool = False
    approver: Optional[str] = None


class WorkflowTrigger(BaseModel):
    """工作流触发器"""
    type: str  # manual/schedule/webhook
    cron_expr: Optional[str] = None
    webhook_path: Optional[str] = None
