"""
审批模型 - 支持审批流程
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


class ApprovalStatus(Enum):
    """审批状态"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ApprovalType(Enum):
    """审批类型"""
    MANUAL = "MANUAL"  # 人工审批
    AUTO = "AUTO"     # 自动审批


@dataclass
class ApprovalDefinition:
    """审批定义"""
    id: str
    name: str
    description: str = ""
    approver_roles: List[str] = field(default_factory=list)  # 审批人角色
    approver_users: List[str] = field(default_factory=list)  # 审批人用户ID
    approval_type: ApprovalType = ApprovalType.MANUAL
    timeout_seconds: int = 3600  # 超时时间
    auto_approve_on_timeout: bool = False


@dataclass
class ApprovalInstance:
    """审批实例"""
    id: str
    step_instance_id: str
    workflow_instance_id: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver: Optional[str] = None
    
    # 审批内容
    title: str = ""
    content: Dict[str, Any] = field(default_factory=dict)
    
    # 时间
    created_at: datetime = field(default_factory=datetime.now)
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    
    # 意见
    comment: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class NotificationConfig:
    """通知配置"""
    notify_on_submit: bool = True      # 提交审批时通知
    notify_on_approve: bool = True     # 审批通过时通知
    notify_on_reject: bool = True      # 审批拒绝时通知
    notify_channels: List[str] = field(default_factory=lambda: ["feishu", "email"])


@dataclass
class Notification:
    """通知"""
    id: str
    notification_type: str  # approval_submitted, approved, rejected
    title: str
    content: str
    recipients: List[str]
    channels: List[str]
    created_at: datetime = field(default_factory=datetime.now)
    sent: bool = False

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
