"""
角色数据模型
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any
from datetime import datetime
import uuid


class RoleType(Enum):
    """角色类型"""
    SYSTEM = "SYSTEM"     # 系统预置
    CUSTOM = "CUSTOM"     # 自定义


@dataclass
class Role:
    """角色"""
    id: str = ""
    name: str = ""
    description: str = ""
    role_type: RoleType = RoleType.CUSTOM
    
    # 权限
    permissions: List[str] = field(default_factory=list)  # 权限列表
    
    # 能力要求
    required_capabilities: List[str] = field(default_factory=list)
    
    # 层级
    level: int = 1  # 角色层级
    parent_role_id: str = None
    
    # 统计
    agent_count: int = 0
    
    # 时间
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


# 预置角色
PRESET_ROLES = [
    # 项目角色
    Role(
        id="role_admin",
        name="管理员",
        description="系统管理员，拥有所有权限",
        role_type=RoleType.SYSTEM,
        permissions=["*"],
        level=10
    ),
    Role(
        id="role_product",
        name="产品经理",
        description="负责需求管理和产品规划",
        role_type=RoleType.SYSTEM,
        permissions=["demand:create", "demand:edit", "demand:approve", "planning:create"],
        required_capabilities=["product_management", "analysis"],
        level=6
    ),
    Role(
        id="role_dev",
        name="开发工程师",
        description="负责代码开发和实现",
        role_type=RoleType.SYSTEM,
        permissions=["task:execute", "code:write", "test:run", "commit:create"],
        required_capabilities=["coding", "testing"],
        level=5
    ),
    Role(
        id="role_qa",
        name="测试工程师",
        description="负责测试和质量保证",
        role_type=RoleType.SYSTEM,
        permissions=["test:create", "test:execute", "test:approve"],
        required_capabilities=["testing", "analysis"],
        level=4
    ),
    Role(
        id="role_sre",
        name="运维工程师",
        description="负责系统运维和部署",
        role_type=RoleType.SYSTEM,
        permissions=["deploy:execute", "monitor:view", "alert:manage", "config:update"],
        required_capabilities=["devops", "monitoring"],
        level=5
    ),
    Role(
        id="role_architect",
        name="架构师",
        description="负责技术架构和代码审查",
        role_type=RoleType.SYSTEM,
        permissions=["design:create", "code:review", "architecture:design"],
        required_capabilities=["architecture", "review"],
        level=7
    ),
    # Agent角色
    Role(
        id="role_minion",
        name="执行者",
        description="执行具体开发、运维任务",
        role_type=RoleType.SYSTEM,
        permissions=["task:execute", "code:write"],
        required_capabilities=["coding"],
        level=2
    ),
    Role(
        id="role_sage",
        name="分析者",
        description="数据分析、决策建议",
        role_type=RoleType.SYSTEM,
        permissions=["data:read", "data:analyze", "report:create"],
        required_capabilities=["analysis", "research"],
        level=3
    ),
    Role(
        id="role_scout",
        name="调研者",
        description="市场调研、竞品分析",
        role_type=RoleType.SYSTEM,
        permissions=["research:execute", "data:read", "report:create"],
        required_capabilities=["research", "analysis"],
        level=3
    ),
    Role(
        id="role_quill",
        name="写作者",
        description="文档撰写、内容生成",
        role_type=RoleType.SYSTEM,
        permissions=["document:write", "content:create", "report:create"],
        required_capabilities=["writing", "communication"],
        level=2
    ),
    Role(
        id="role_observer",
        name="统筹者",
        description="全局监控、任务分发",
        role_type=RoleType.SYSTEM,
        permissions=["*"],
        required_capabilities=["management", "analysis"],
        level=8
    ),
]
