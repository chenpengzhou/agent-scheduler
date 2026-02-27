"""
Agent状态服务 - 从OpenClaw获取真实状态
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import time
import threading

logger = logging.getLogger(__name__)


# Agent状态类型
class AgentWorkStatus:
    """Agent工作状态"""
    WORKING = "Working"      # 执行任务
    THINKING = "Thinking"    # 推理中
    ANALYZING = "Analyzing"  # 分析中
    RESEARCHING = "Researching"  # 调研中
    WRITING = "Writing"      # 撰写中
    IDLE = "Idle"           # 空闲
    OFFLINE = "Offline"     # 离线
    
    # 颜色映射
    COLORS = {
        WORKING: "🟢",
        THINKING: "🔵",
        ANALYZING: "🟣",
        RESEARCHING: "🟡",
        WRITING: "🟠",
        IDLE: "⚪",
        OFFLINE: "⚫"
    }
    
    @classmethod
    def get_color(cls, status: str) -> str:
        return cls.COLORS.get(status, "⚪")


class AgentStatusService:
    """Agent状态服务"""
    
    def __init__(self, refresh_interval: int = 5):
        self.refresh_interval = refresh_interval  # 秒
        self.agents_db = {}
        self.status_history: Dict[str, List[Dict]] = defaultdict(list)
        self.max_history = 100  # 每个Agent保留最近100条
        self._running = False
        self._thread = None
        self._last_refresh = None
    
    def set_agents_db(self, agents_db: Dict):
        """设置Agent数据库引用"""
        self.agents_db = agents_db
    
    def sync_agent_status(self, session_status: Dict) -> bool:
        """同步Agent状态"""
        try:
            agent_id = session_status.get("agent_id")
            status = session_status.get("status", "Idle")
            current_task = session_status.get("current_task", "")
            last_active = session_status.get("last_active_at", datetime.now().isoformat())
            
            if agent_id in self.agents_db:
                old_status = self.agents_db[agent_id].get("work_status", "Idle")
                
                # 更新状态
                self.agents_db[agent_id]["work_status"] = status
                self.agents_db[agent_id]["current_task"] = current_task
                self.agents_db[agent_id]["last_active_at"] = last_active
                
                # 记录历史
                if old_status != status:
                    self._record_status_change(agent_id, old_status, status)
                
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error syncing agent status: {e}")
            return False
    
    def sync_from_openclaw(self) -> Dict:
        """从OpenClaw同步所有Agent状态"""
        # 这里可以调用OpenClaw的session API获取状态
        # 由于在开发环境，我们模拟一下
        result = {
            "synced": 0,
            "failed": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # 实际实现中，这里会调用:
        # sessions_list() 获取所有session
        # 获取每个session的状态
        
        # 模拟同步
        for agent_id in self.agents_db:
            # 检查是否有最近活动
            last_active = self.agents_db[agent_id].get("last_active_at")
            if last_active:
                if isinstance(last_active, str):
                    last_active = datetime.fromisoformat(last_active)
                
                elapsed = (datetime.now() - last_active).total_seconds()
                
                if elapsed > 300:  # 5分钟无活动
                    self.agents_db[agent_id]["work_status"] = AgentWorkStatus.OFFLINE
                elif self.agents_db[agent_id].get("status") == "BUSY":
                    # 随机分配一个工作状态
                    self.agents_db[agent_id]["work_status"] = AgentWorkStatus.WORKING
                else:
                    self.agents_db[agent_id]["work_status"] = AgentWorkStatus.IDLE
            
            result["synced"] += 1
        
        self._last_refresh = datetime.now()
        return result
    
    def _record_status_change(self, agent_id: str, old_status: str, new_status: str):
        """记录状态变更"""
        record = {
            "agent_id": agent_id,
            "old_status": old_status,
            "new_status": new_status,
            "timestamp": datetime.now().isoformat()
        }
        
        self.status_history[agent_id].append(record)
        
        # 保留最近100条
        if len(self.status_history[agent_id]) > self.max_history:
            self.status_history[agent_id] = self.status_history[agent_id][-self.max_history:]
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict]:
        """获取Agent状态"""
        if agent_id not in self.agents_db:
            return None
        
        agent = self.agents_db[agent_id]
        
        return {
            "agent_id": agent_id,
            "name": agent.get("name", ""),
            "status": agent.get("work_status", AgentWorkStatus.IDLE),
            "color": AgentWorkStatus.get_color(agent.get("work_status", AgentWorkStatus.IDLE)),
            "current_task": agent.get("current_task", ""),
            "last_active_at": agent.get("last_active_at"),
            "updated_at": self._last_refresh.isoformat() if self._last_refresh else None
        }
    
    def get_all_agents_status(self) -> List[Dict]:
        """获取所有Agent状态"""
        result = []
        
        for agent_id in self.agents_db:
            status = self.get_agent_status(agent_id)
            if status:
                result.append(status)
        
        # 按状态排序: Working > Thinking > ... > Offline
        status_order = {
            AgentWorkStatus.WORKING: 0,
            AgentWorkStatus.THINKING: 1,
            AgentWorkStatus.ANALYZING: 2,
            AgentWorkStatus.RESEARCHING: 3,
            AgentWorkStatus.WRITING: 4,
            AgentWorkStatus.IDLE: 5,
            AgentWorkStatus.OFFLINE: 6
        }
        
        result.sort(key=lambda x: status_order.get(x["status"], 99))
        
        return result
    
    def get_status_statistics(self) -> Dict:
        """获取状态统计"""
        all_status = self.get_all_agents_status()
        
        stats = {
            "total": len(all_status),
            "by_status": defaultdict(int),
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None
        }
        
        for agent in all_status:
            status = agent["status"]
            stats["by_status"][status] += 1
        
        stats["by_status"] = dict(stats["by_status"])
        
        return stats
    
    def get_status_history(self, agent_id: str, limit: int = 20) -> List[Dict]:
        """获取状态变更历史"""
        history = self.status_history.get(agent_id, [])
        return history[-limit:][::-1]
    
    def start_auto_refresh(self):
        """启动自动刷新"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()
        logger.info("Agent status auto-refresh started")
    
    def stop_auto_refresh(self):
        """停止自动刷新"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Agent status auto-refresh stopped")
    
    def _refresh_loop(self):
        """刷新循环"""
        while self._running:
            try:
                self.sync_from_openclaw()
            except Exception as e:
                logger.error(f"Error in refresh loop: {e}")
            
            time.sleep(self.refresh_interval)
    
    def get_status_types(self) -> List[Dict]:
        """获取所有状态类型"""
        return [
            {"value": "Working", "label": "🟢 Working", "color": "green"},
            {"value": "Thinking", "label": "🔵 Thinking", "color": "blue"},
            {"value": "Analyzing", "label": "🟣 Analyzing", "color": "purple"},
            {"value": "Researching", "label": "🟡 Researching", "color": "yellow"},
            {"value": "Writing", "label": "🟠 Writing", "color": "orange"},
            {"value": "Idle", "label": "⚪ Idle", "color": "gray"},
            {"value": "Offline", "label": "⚫ Offline", "color": "black"}
        ]


# 全局实例
_agent_status_service = AgentStatusService(refresh_interval=5)


def get_agent_status_service() -> AgentStatusService:
    return _agent_status_service
