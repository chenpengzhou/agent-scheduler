"""
工作流节点模型 (兼容层)
"""
from enum import Enum


class NodeType(Enum):
    """节点类型"""
    START = "start"
    AGENT = "agent"
    APPROVAL = "approval"
    CONDITION = "condition"
    TIMER = "timer"
    NOTIFY = "notify"
    END = "end"


class NodeStatus(Enum):
    """节点状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class NodeConfig:
    """节点配置"""
    pass


class WorkflowNode:
    """工作流节点"""
    pass


class NodeExecution:
    """节点执行记录"""
    pass
