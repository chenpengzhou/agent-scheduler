#!/usr/bin/env python3
"""
Agent 心跳模块 - Agent 调度器
"""
import sys
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

sys.path.insert(0, "/home/robin/.openclaw/workspace-dev/scheduler")
from task_queue import queue
from models import AgentHeartbeat, AgentStatus


class HeartbeatManager:
    """Agent 心跳管理器"""
    
    def __init__(self):
        self.queue = queue
        self.timeout = 60  # 心跳超时时间（秒）
    
    def register(self, agent_id: str, capabilities: List[str] = None) -> AgentHeartbeat:
        """注册 Agent"""
        heartbeat = AgentHeartbeat(
            agent_id=agent_id,
            status=AgentStatus.ONLINE,
            capabilities=capabilities or [],
            last_heartbeat=datetime.now()
        )
        self.queue.register_agent(heartbeat)
        return heartbeat
    
    def heartbeat(self, agent_id: str, status: str = None, current_task: str = None,
                  cpu_percent: float = 0.0, memory_percent: float = 0.0, 
                  uptime: int = 0) -> AgentHeartbeat:
        """Agent 心跳上报"""
        # 状态映射: idle -> online
        if status == "idle":
            status = "online"
        
        existing = self.queue.get_agent_status(agent_id)
        
        if existing:
            if status:
                existing.status = AgentStatus(status)
            if current_task is not None:
                existing.current_task = current_task
            existing.cpu_percent = cpu_percent
            existing.memory_percent = memory_percent
            existing.uptime = uptime
            existing.last_heartbeat = datetime.now()
            return self.queue.update_heartbeat(existing)
        else:
            # 未注册，自动注册
            return self.register(agent_id)
    
    def get_status(self, agent_id: str) -> Optional[AgentHeartbeat]:
        """获取 Agent 状态"""
        return self.queue.get_agent_status(agent_id)
    
    def get_all_agents(self) -> List[AgentHeartbeat]:
        """获取所有 Agent"""
        return self.queue.get_all_agents()
    
    def get_online_agents(self) -> List[AgentHeartbeat]:
        """获取在线 Agent"""
        agents = self.get_all_agents()
        return [a for a in agents if a.status == AgentStatus.ONLINE]
    
    def get_busy_agents(self) -> List[AgentHeartbeat]:
        """获取忙碌 Agent"""
        agents = self.get_all_agents()
        return [a for a in agents if a.status == AgentStatus.BUSY]
    
    def check_timeout(self) -> List[str]:
        """检查超时的 Agent"""
        timeout_agents = []
        now = datetime.now()
        
        for agent in self.get_all_agents():
            elapsed = (now - agent.last_heartbeat).total_seconds()
            if elapsed > self.timeout:
                # 标记为离线
                agent.status = AgentStatus.OFFLINE
                self.queue.update_heartbeat(agent)
                timeout_agents.append(agent.agent_id)
        
        return timeout_agents
    
    def set_busy(self, agent_id: str, task_id: str) -> bool:
        """设置 Agent 为忙碌状态"""
        agent = self.queue.get_agent_status(agent_id)
        if agent:
            agent.status = AgentStatus.BUSY
            agent.current_task = task_id
            self.queue.update_heartbeat(agent)
            return True
        return False
    
    def set_free(self, agent_id: str) -> bool:
        """设置 Agent 为空闲状态"""
        agent = self.queue.get_agent_status(agent_id)
        if agent:
            agent.status = AgentStatus.ONLINE
            agent.current_task = None
            self.queue.update_heartbeat(agent)
            return True
        return False
    
    def unregister(self, agent_id: str) -> bool:
        """注销 Agent"""
        agent = self.queue.get_agent_status(agent_id)
        if agent:
            agent.status = AgentStatus.OFFLINE
            self.queue.update_heartbeat(agent)
            return True
        return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取监控指标"""
        all_agents = self.get_all_agents()
        
        return {
            "total_agents": len(all_agents),
            "online": len([a for a in all_agents if a.status == AgentStatus.ONLINE]),
            "busy": len([a for a in all_agents if a.status == AgentStatus.BUSY]),
            "offline": len([a for a in all_agents if a.status == AgentStatus.OFFLINE]),
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "status": a.status.value,
                    "current_task": a.current_task,
                    "cpu_percent": a.cpu_percent,
                    "memory_percent": a.memory_percent,
                    "last_heartbeat": a.last_heartbeat.isoformat(),
                    "capabilities": a.capabilities
                }
                for a in all_agents
            ]
        }


# 全局实例
heartbeat_manager = HeartbeatManager()
