"""
工作流配置模型
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid


class WorkflowStage(Enum):
    """工作流阶段"""
    DEMAND_ANALYSIS = "DEMAND_ANALYSIS"  # 需求分析
    DESIGN = "DESIGN"                    # 程序设计
    DEVELOPMENT = "DEVELOPMENT"           # 代码开发
    TESTING = "TESTING"                  # 质量测试
    DEPLOYED = "DEPLOYED"                # 部署发布
    ACCEPTANCE = "ACCEPTANCE"            # 验收确认


class TriggerEvent(Enum):
    """触发事件"""
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    APPROVAL_GRANTED = "APPROVAL_GRANTED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"


class TriggerAction(Enum):
    """触发动作"""
    ASSIGN_TO_AGENT = "ASSIGN_TO_AGENT"
    NOTIFY = "NOTIFY"
    ESCALATE = "ESCALATE"
    CREATE_TASK = "CREATE_TASK"


@dataclass
class WorkflowTransition:
    """工作流流转规则"""
    from_stage: str
    to_stage: str
    trigger_event: str
    conditions: Dict = field(default_factory=dict)
    actions: List[Dict] = field(default_factory=list)


@dataclass
class RoleStageMapping:
    """角色-阶段映射"""
    role_id: str
    stage: str
    agent_ids: List[str] = field(default_factory=list)


# 默认工作流配置
DEFAULT_WORKFLOW_CONFIG = {
    "stages": [
        {"id": "DEMAND_ANALYSIS", "name": "需求分析", "role": "Product", "next": "DESIGN"},
        {"id": "DESIGN", "name": "程序设计", "role": "Architect", "next": "DEVELOPMENT"},
        {"id": "DEVELOPMENT", "name": "代码开发", "role": "Dev", "next": "TESTING"},
        {"id": "TESTING", "name": "质量测试", "role": "QA", "next": "DEPLOYED"},
        {"id": "DEPLOYED", "name": "部署发布", "role": "SRE", "next": "ACCEPTANCE"},
        {"id": "ACCEPTANCE", "name": "验收确认", "role": "Product", "next": None}
    ],
    "transitions": [
        {
            "from_stage": "DEMAND_ANALYSIS",
            "to_stage": "DESIGN",
            "trigger_event": "TASK_COMPLETED",
            "actions": [{"type": "NOTIFY", "target_role": "Architect"}]
        },
        {
            "from_stage": "DESIGN",
            "to_stage": "DEVELOPMENT",
            "trigger_event": "TASK_COMPLETED",
            "actions": [{"type": "NOTIFY", "target_role": "Dev"}]
        },
        {
            "from_stage": "DEVELOPMENT",
            "to_stage": "TESTING",
            "trigger_event": "TASK_COMPLETED",
            "actions": [{"type": "NOTIFY", "target_role": "QA"}]
        },
        {
            "from_stage": "TESTING",
            "to_stage": "DEPLOYED",
            "trigger_event": "TASK_COMPLETED",
            "actions": [{"type": "NOTIFY", "target_role": "SRE"}]
        },
        {
            "from_stage": "DEPLOYED",
            "to_stage": "ACCEPTANCE",
            "trigger_event": "TASK_COMPLETED",
            "actions": [{"type": "NOTIFY", "target_role": "Product"}]
        }
    ]
}

# 角色ID映射
ROLE_ID_MAPPING = {
    "role_product": "Product",
    "role_architect": "Architect", 
    "role_dev": "Dev",
    "role_qa": "QA",
    "role_sre": "SRE"
}
