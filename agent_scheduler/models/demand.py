"""
需求数据模型
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


class DemandStatus(Enum):
    """需求状态"""
    DRAFT = "DRAFT"           # 草稿
    SUBMITTED = "SUBMITTED"   # 已提交
    IN_PROGRESS = "IN_PROGRESS"  # 进行中
    COMPLETED = "COMPLETED"   # 已完成
    CANCELLED = "CANCELLED"  # 已取消


class DemandStage(Enum):
    """需求阶段"""
    WATCHING = "WATCHING"     # 观望
    VALIDATING = "VALIDATING" # 评审中
    BUILDING = "BUILDING"     # 开发中
    SHIPPED = "SHIPPED"       # 已发布


class DemandPriority(Enum):
    """需求优先级"""
    P0 = 0  # 紧急
    P1 = 1  # 高
    P2 = 2  # 中
    P3 = 3  # 低


@dataclass
class Demand:
    """需求"""
    id: str = ""
    title: str = ""
    description: str = ""
    
    # 状态
    status: DemandStatus = DemandStatus.DRAFT
    stage: DemandStage = DemandStage.WATCHING
    priority: DemandPriority = DemandPriority.P2
    
    # 分类
    category: str = ""  # 功能/Bug/优化
    tags: List[str] = field(default_factory=list)
    
    # 负责人
    owner_id: str = ""       # 发起人
    assignee_id: str = ""    # 负责人
    
    # 内容
    acceptance_criteria: str = ""  # 验收标准
    
    # 估算
    estimated_hours: float = 0.0
    actual_hours: float = 0.0
    
    # 附件
    attachments: List[Dict[str, str]] = field(default_factory=list)
    
    # 时间
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 排序
    sort_order: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class DemandComment:
    """需求评论"""
    id: str = ""
    demand_id: str = ""
    author_id: str = ""
    content: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
