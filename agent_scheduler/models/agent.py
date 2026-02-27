"""
Agent数据模型
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


class AgentStatus(Enum):
    """Agent状态"""
    IDLE = "IDLE"           # 空闲
    BUSY = "BUSY"           # 忙碌
    OFFLINE = "OFFLINE"     # 离线
    ERROR = "ERROR"         # 错误


@dataclass
class Agent:
    """Agent"""
    id: str = ""
    name: str = ""
    agent_type: str = ""    # agent类型
    description: str = ""
    status: AgentStatus = AgentStatus.IDLE
    
    # 能力
    capabilities: List[str] = field(default_factory=list)  # 技能标签
    max_concurrent_tasks: int = 1  # 最大并发任务数
    
    # 关联
    role_id: Optional[str] = None
    
    # 统计
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    
    # 时间
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_active_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class AgentRegistration:
    """Agent注册信息"""
    agent_id: str
    hostname: str = ""
    ip_address: str = ""
    port: int = 0
    version: str = "1.0"
    capabilities: List[str] = field(default_factory=list)
    registered_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: Optional[datetime] = None


@dataclass
class AgentCapability:
    """Agent能力标签"""
    id: str = ""
    name: str = ""
    description: str = ""
    category: str = ""  # 技术、业务、管理等
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
