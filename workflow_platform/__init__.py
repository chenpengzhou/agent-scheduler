"""
工作流引擎 - Workflow Engine
让工作流能跑起来
支持DAG和并行执行
支持审批流程
"""

__version__ = "1.0.0"

# 导出核心类
from .models.workflow import (
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowStatus,
    StepDefinition,
    StepInstance,
    TaskDefinition,
    TaskInstance,
    StepType,
)
from .engine.core import WorkflowEngine
from .engine.dag import DAG, DAGExecutor, DAGBuilder
from .engine.executor import WorkflowExecutor
from .models.condition import Condition, ConditionEvaluator, ExecutionStrategy
from .models.approval import (
    ApprovalInstance,
    ApprovalStatus,
    ApprovalType,
    ApprovalDefinition,
)
from .services.approval_service import ApprovalService, NotificationService

__all__ = [
    # 模型
    "WorkflowDefinition",
    "WorkflowInstance",
    "WorkflowStatus",
    "StepDefinition",
    "StepInstance",
    "TaskDefinition",
    "TaskInstance",
    "StepType",
    # 引擎
    "WorkflowEngine",
    "DAG",
    "DAGExecutor",
    "DAGBuilder",
    "WorkflowExecutor",
    # 条件
    "Condition",
    "ConditionEvaluator",
    "ExecutionStrategy",
    # 审批
    "ApprovalInstance",
    "ApprovalStatus",
    "ApprovalType",
    "ApprovalDefinition",
    "ApprovalService",
    "NotificationService",
]
