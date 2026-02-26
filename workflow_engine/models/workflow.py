"""
工作流数据模型
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class AgentSelector:
    """Agent选择器"""
    agent_type: str = "dev-engineer"  # agent类型
    capabilities: List[str] = field(default_factory=list)  # 能力要求


@dataclass
class TaskDefinition:
    """任务定义"""
    id: str
    name: str
    description: str = ""
    executor_type: str = "agent"  # agent, script, function
    agent_selector: Optional[AgentSelector] = None
    input_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepDefinition:
    """步骤定义"""
    id: str
    name: str
    description: str = ""
    task_def: Optional[TaskDefinition] = None
    next_steps: List[str] = field(default_factory=list)  # 下一步步骤ID列表


@dataclass
class WorkflowDefinition:
    """工作流定义"""
    id: str
    name: str
    version: str = "1.0"
    description: str = ""
    steps: List[StepDefinition] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_step(self, step_id: str) -> Optional[StepDefinition]:
        """根据ID获取步骤"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_first_step(self) -> Optional[StepDefinition]:
        """获取第一个步骤"""
        return self.steps[0] if self.steps else None


@dataclass
class WorkflowInstance:
    """工作流实例"""
    id: str
    definition_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step_id: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class StepInstance:
    """步骤实例"""
    id: str
    definition_id: str  # 对应的StepDefinition.id
    workflow_instance_id: str
    status: StepStatus = StepStatus.PENDING
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class TaskInstance:
    """任务实例"""
    id: str
    definition_id: str  # 对应的TaskDefinition.id
    step_instance_id: str
    workflow_instance_id: str
    status: TaskStatus = TaskStatus.PENDING
    input_params: Dict[str, Any] = field(default_factory=dict)
    output_result: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
