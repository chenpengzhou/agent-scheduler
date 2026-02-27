"""
Workflow Engine Models
"""
from .node import NodeType, NodeStatus, NodeConfig, WorkflowNode, NodeExecution
from .workflow import (
    WorkflowDefinition, 
    WorkflowInstance,
    WorkflowStatus,
    StepDefinition,
    StepInstance,
    TaskDefinition,
    TaskInstance,
    StepType,
    StepStatus,
    TaskStatus
)

# 添加兼容层
class Edge:
    """工作流连线"""
    pass

class WorkflowTemplate:
    """工作流模板 - 兼容WorkflowDefinition"""
    pass

class WorkflowExecution:
    """工作流执行 - 兼容WorkflowInstance"""
    pass

__all__ = [
    "NodeType",
    "NodeStatus", 
    "NodeConfig",
    "WorkflowNode",
    "NodeExecution",
    "Edge",
    "WorkflowTemplate",
    "WorkflowExecution",
    "WorkflowDefinition",
    "WorkflowInstance",
    "WorkflowStatus",
    "StepDefinition",
    "StepInstance",
    "TaskDefinition",
    "TaskInstance",
    "StepType",
    "StepStatus",
    "TaskStatus"
]
