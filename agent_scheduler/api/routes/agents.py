"""
Agent管理API
"""
from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

# 模拟数据库
agents_db = {}
# 状态变更历史
status_history_db: Dict[str, List] = {}


# Pydantic模型
class AgentCreate(BaseModel):
    name: str
    agent_type: str
    description: str = ""
    capabilities: List[str] = []
    max_concurrent_tasks: int = 1
    role_id: Optional[str] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    capabilities: Optional[List[str]] = None
    max_concurrent_tasks: Optional[int] = None
    role_id: Optional[str] = None
    status: Optional[str] = None


class AgentStatusUpdate(BaseModel):
    status: str
    reason: str = ""


class AgentCapabilityItem(BaseModel):
    name: str
    score: int = 3  # 1-5评分


class AgentCapabilitiesUpdate(BaseModel):
    capabilities: List[AgentCapabilityItem]


class AgentResponse(BaseModel):
    id: str
    name: str
    agent_type: str
    description: str
    status: str
    capabilities: List[Dict]  # 包含name和score
    max_concurrent_tasks: int
    role_id: Optional[str]
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    created_at: datetime
    updated_at: datetime
    last_active_at: Optional[datetime]


class StatusHistoryItem(BaseModel):
    agent_id: str
    old_status: str
    new_status: str
    reason: str
    timestamp: datetime


# API路由
@router.post("", response_model=AgentResponse)
async def create_agent(agent: AgentCreate):
    """创建Agent"""
    agent_id = str(uuid.uuid4())
    now = datetime.now()
    
    # 转换capabilities为带评分格式
    capabilities = []
    for cap in agent.capabilities:
        if isinstance(cap, str):
            capabilities.append({"name": cap, "score": 3})  # 默认3分
        elif isinstance(cap, dict):
            capabilities.append(cap)
    
    agent_data = {
        "id": agent_id,
        "name": agent.name,
        "agent_type": agent.agent_type,
        "description": agent.description,
        "status": "IDLE",
        "capabilities": capabilities,
        "max_concurrent_tasks": agent.max_concurrent_tasks,
        "role_id": agent.role_id,
        "total_tasks": 0,
        "completed_tasks": 0,
        "failed_tasks": 0,
        "created_at": now,
        "updated_at": now,
        "last_active_at": None
    }
    
    agents_db[agent_id] = agent_data
    # 初始化状态历史
    status_history_db[agent_id] = []
    
    return agent_data


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """获取Agent详情"""
    agent = agents_db.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    role_id: Optional[str] = None,
    status: Optional[str] = None,
    capability: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """列取Agent列表"""
    result = list(agents_db.values())
    
    if role_id:
        result = [a for a in result if a.get("role_id") == role_id]
    if status:
        result = [a for a in result if a.get("status") == status]
    if capability:
        # capabilities: [{"name": "python", "score": 4}]
        result = [a for a in result if any(
            isinstance(c, dict) and c.get("name") == capability 
            for c in a.get("capabilities", [])
        )]
    
    return result[offset:offset + limit]


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, agent: AgentUpdate):
    """更新Agent"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    existing = agents_db[agent_id]
    update_data = agent.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        existing[key] = value
    
    existing["updated_at"] = datetime.now()
    agents_db[agent_id] = existing
    
    return existing


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    """删除Agent"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    del agents_db[agent_id]
    return {"message": "Deleted successfully"}


@router.post("/{agent_id}/heartbeat")
async def agent_heartbeat(agent_id: str):
    """Agent心跳"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agents_db[agent_id]["last_active_at"] = datetime.now()
    agents_db[agent_id]["status"] = "IDLE"
    agents_db[agent_id]["updated_at"] = datetime.now()
    
    return {"message": "Heartbeat received"}


@router.get("/{agent_id}/stats")
async def get_agent_stats(agent_id: str):
    """获取Agent统计"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = agents_db[agent_id]
    
    completion_rate = 0
    if agent["total_tasks"] > 0:
        completion_rate = agent["completed_tasks"] / agent["total_tasks"] * 100
    
    return {
        "agent_id": agent_id,
        "total_tasks": agent["total_tasks"],
        "completed_tasks": agent["completed_tasks"],
        "failed_tasks": agent["failed_tasks"],
        "completion_rate": round(completion_rate, 2),
        "status": agent["status"]
    }


@router.put("/{agent_id}/status", response_model=AgentResponse)
async def update_agent_status(agent_id: str, status_update: AgentStatusUpdate):
    """更新Agent状态"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # 验证状态值
    valid_statuses = ["IDLE", "BUSY", "OFFLINE", "ERROR", "WORKING", "THINKING", "ANALYZING", "RESEARCHING", "WRITING"]
    if status_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    agent = agents_db[agent_id]
    old_status = agent["status"]
    new_status = status_update.status
    
    # 记录状态变更历史
    if agent_id not in status_history_db:
        status_history_db[agent_id] = []
    
    status_history_db[agent_id].append({
        "agent_id": agent_id,
        "old_status": old_status,
        "new_status": new_status,
        "reason": status_update.reason,
        "timestamp": datetime.now()
    })
    
    # 保留最近100条历史记录
    if len(status_history_db[agent_id]) > 100:
        status_history_db[agent_id] = status_history_db[agent_id][-100:]
    
    # 更新状态
    agent["status"] = new_status
    agent["updated_at"] = datetime.now()
    agents_db[agent_id] = agent
    
    return agent


@router.put("/{agent_id}/capabilities", response_model=AgentResponse)
async def update_agent_capabilities(agent_id: str, caps_update: AgentCapabilitiesUpdate):
    """更新Agent能力标签（含评分）"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # 验证评分范围
    for cap in caps_update.capabilities:
        if not 1 <= cap.score <= 5:
            raise HTTPException(status_code=400, detail="Score must be between 1 and 5")
    
    agent = agents_db[agent_id]
    agent["capabilities"] = [{"name": cap.name, "score": cap.score} for cap in caps_update.capabilities]
    agent["updated_at"] = datetime.now()
    agents_db[agent_id] = agent
    
    return agent


@router.get("/{agent_id}/status-history")
async def get_agent_status_history(agent_id: str, limit: int = 20):
    """获取Agent状态变更历史"""
    if agent_id not in agents_db:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    history = status_history_db.get(agent_id, [])
    # 返回最近的记录
    return history[-limit:][::-1]
