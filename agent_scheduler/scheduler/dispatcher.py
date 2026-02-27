"""
任务分发器 - 根据角色/能力分发任务给Agent
"""
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from ..models.task import Task, TaskStatus
from ..models.agent import Agent, AgentStatus

logger = logging.getLogger(__name__)


class Dispatcher:
    """任务分发器"""
    
    def __init__(self, agents_db: Dict[str, Dict] = None):
        self.agents_db = agents_db or {}
    
    def dispatch(self, task: Task, available_agents: List[Agent]) -> Optional[str]:
        """分发任务给合适的Agent"""
        if not available_agents:
            logger.warning(f"No available agents for task: {task.id}")
            return None
        
        # 根据任务类型和能力需求筛选
        suitable_agents = self._filter_agents(task, available_agents)
        
        if not suitable_agents:
            logger.warning(f"No suitable agent for task: {task.id}")
            return None
        
        # 选择最合适的Agent（负载最低的）
        selected_agent = self._select_agent(task, suitable_agents)
        
        if selected_agent:
            logger.info(f"Task {task.id} dispatched to agent {selected_agent.id}")
            return selected_agent.id
        
        return None
    
    def _filter_agents(self, task: Task, agents: List[Agent]) -> List[Agent]:
        """根据任务需求筛选Agent"""
        suitable = []
        
        for agent in agents:
            # Agent必须是空闲状态
            if agent.status != AgentStatus.IDLE:
                continue
            
            # 检查能力匹配
            if task.executor_type == "agent" and agent.capabilities:
                # 任务需要的能力
                required = task.executor_params.get("required_capabilities", [])
                
                if required:
                    # Agent必须具备所有必需能力
                    if not all(cap in agent.capabilities for cap in required):
                        continue
            
            # 检查并发限制
            current_tasks = getattr(agent, 'current_tasks', 0)
            if current_tasks >= agent.max_concurrent_tasks:
                continue
            
            suitable.append(agent)
        
        return suitable
    
    def _select_agent(self, task: Task, agents: List[Agent]) -> Optional[Agent]:
        """选择最合适的Agent"""
        if not agents:
            return None
        
        # 按负载排序（当前任务数少的优先）
        agents.sort(key=lambda a: getattr(a, 'current_tasks', 0))
        
        return agents[0]
    
    def dispatch_by_role(self, task: Task, role_id: str) -> Optional[str]:
        """根据角色分发任务"""
        # 查找该角色的Agent
        role_agents = [
            Agent(
                id=a["id"],
                name=a["name"],
                agent_type=a["agent_type"],
                capabilities=a.get("capabilities", []),
                max_concurrent_tasks=a.get("max_concurrent_tasks", 1),
                status=AgentStatus.IDLE if a.get("status") == "IDLE" else AgentStatus.BUSY
            )
            for a in self.agents_db.values()
            if a.get("role_id") == role_id
        ]
        
        return self.dispatch(task, role_agents)
    
    def dispatch_by_capability(self, task: Task, capability: str) -> Optional[str]:
        """根据能力分发任务"""
        # 查找具有该能力的Agent
        capable_agents = [
            Agent(
                id=a["id"],
                name=a["name"],
                agent_type=a["agent_type"],
                capabilities=a.get("capabilities", []),
                max_concurrent_tasks=a.get("max_concurrent_tasks", 1),
                status=AgentStatus.IDLE if a.get("status") == "IDLE" else AgentStatus.BUSY
            )
            for a in self.agents_db.values()
            if capability in a.get("capabilities", [])
        ]
        
        return self.dispatch(task, capable_agents)


class LoadBalancer:
    """负载均衡器"""
    
    def __init__(self):
        self.agent_loads: Dict[str, int] = {}
    
    def get_load(self, agent_id: str) -> int:
        """获取Agent当前负载"""
        return self.agent_loads.get(agent_id, 0)
    
    def increment_load(self, agent_id: str):
        """增加负载"""
        self.agent_loads[agent_id] = self.agent_loads.get(agent_id, 0) + 1
    
    def decrement_load(self, agent_id: str):
        """减少负载"""
        current = self.agent_loads.get(agent_id, 0)
        if current > 0:
            self.agent_loads[agent_id] = current - 1
    
    def get_least_loaded_agent(self, agent_ids: List[str]) -> Optional[str]:
        """获取负载最低的Agent"""
        if not agent_ids:
            return None
        
        loads = [(aid, self.get_load(aid)) for aid in agent_ids]
        loads.sort(key=lambda x: x[1])
        
        return loads[0][0]
