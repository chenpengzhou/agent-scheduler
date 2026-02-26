"""
工作流引擎 - Workflow Engine
让工作流能跑起来
支持DAG和并行执行
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
)
from .engine.core import WorkflowEngine
from .engine.dag import DAG, DAGExecutor, DAGBuilder
from .engine.executor import ParallelExecutor
from .models.condition import Condition, ConditionEvaluator, ExecutionStrategy

__all__ = [
    # 模型
    "WorkflowDefinition",
    "WorkflowInstance",
    "WorkflowStatus",
    "StepDefinition",
    "StepInstance",
    "TaskDefinition",
    "TaskInstance",
    # 引擎
    "WorkflowEngine",
    "DAG",
    "DAGExecutor",
    "DAGBuilder",
    "ParallelExecutor",
    # 条件
    "Condition",
    "ConditionEvaluator",
    "ExecutionStrategy",
]
