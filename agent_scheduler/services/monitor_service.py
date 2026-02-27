"""
监控服务 - Agent状态和任务监控
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging

from .event_service import EventService, EventType, get_event_service

logger = logging.getLogger(__name__)


class MonitorService:
    """监控服务"""
    
    def __init__(self, agents_db=None, tasks_db=None, demands_db=None, event_service=None):
        self._agents_db_ref = agents_db
        self._tasks_db_ref = tasks_db
        self._demands_db_ref = demands_db
        self.event_service = event_service or get_event_service()
    
    def _get_agents_db(self):
        if self._agents_db_ref is not None:
            return self._agents_db_ref
        from agent_scheduler.api.routes.agents import agents_db
        return agents_db
    
    def _get_tasks_db(self):
        if self._tasks_db_ref is not None:
            return self._tasks_db_ref
        from agent_scheduler.api.routes.tasks import tasks_db
        return tasks_db
    
    def _get_demands_db(self):
        if self._demands_db_ref is not None:
            return self._demands_db_ref
        from agent_scheduler.api.routes.demands import demands_db
        return demands_db
    
    def get_agent_status_board(self) -> List[Dict]:
        """获取Agent状态看板"""
        agents_db = self._get_agents_db()
        result = []
        
        for agent in agents_db.values():
            result.append({
                "id": agent.get("id"),
                "name": agent.get("name"),
                "status": agent.get("status", "OFFLINE"),
                "role_id": agent.get("role_id"),
                "current_tasks": agent.get("current_tasks", 0),
                "max_concurrent_tasks": agent.get("max_concurrent_tasks", 1),
                "last_active_at": agent.get("last_active_at"),
                "updated_at": agent.get("updated_at")
            })
        
        status_order = {"BUSY": 0, "IDLE": 1, "OFFLINE": 2, "ERROR": 3}
        result.sort(key=lambda x: status_order.get(x["status"], 99))
        
        return result
    
    def get_task_progress(self, demand_id: str = None) -> List[Dict]:
        """获取任务进度"""
        tasks_db = self._get_tasks_db()
        tasks = list(tasks_db.values())
        
        if demand_id:
            tasks = [t for t in tasks if t.get("demand_id") == demand_id]
        
        result = []
        for task in tasks:
            status = task.get("status", "PENDING")
            progress = 0
            if status == "PENDING":
                progress = 0
            elif status == "RUNNING":
                progress = 50
            elif status == "COMPLETED":
                progress = 100
            elif status in ["FAILED", "CANCELLED"]:
                progress = -1
            
            result.append({
                "id": task.get("id"),
                "name": task.get("name"),
                "status": status,
                "progress": progress,
                "priority": task.get("priority"),
                "demand_id": task.get("demand_id"),
                "assigned_agent_id": task.get("assigned_agent_id")
            })
        
        return result
    
    def get_statistics(self) -> Dict:
        """获取统计概览"""
        agents_db = self._get_agents_db()
        tasks_db = self._get_tasks_db()
        
        # Agent统计
        agent_stats = {"total": len(agents_db), "online": 0, "busy": 0, "idle": 0, "offline": 0}
        for agent in agents_db.values():
            status = agent.get("status", "OFFLINE")
            if status == "BUSY":
                agent_stats["busy"] += 1
            elif status == "IDLE":
                agent_stats["idle"] += 1
            elif status == "OFFLINE":
                agent_stats["offline"] += 1
            else:
                agent_stats["online"] += 1
        
        # Task统计
        task_stats = {"total": len(tasks_db), "pending": 0, "running": 0, "completed": 0, "failed": 0, "cancelled": 0}
        for task in tasks_db.values():
            status = task.get("status", "PENDING")
            key = status.lower()
            if key in task_stats:
                task_stats[key] += 1
        
        # 成功率
        total_finished = task_stats["completed"] + task_stats["failed"]
        success_rate = (task_stats["completed"] / total_finished * 100) if total_finished > 0 else 0
        
        # Agent负载
        agent_loads = []
        for agent in agents_db.values():
            current = agent.get("current_tasks", 0)
            max_tasks = agent.get("max_concurrent_tasks", 1)
            load = (current / max_tasks * 100) if max_tasks > 0 else 0
            agent_loads.append({
                "agent_name": agent.get("name"),
                "load_percent": round(load, 1),
                "current_tasks": current
            })
        
        return {
            "agents": agent_stats,
            "tasks": task_stats,
            "success_rate": round(success_rate, 2),
            "agent_loads": agent_loads
        }
    
    def get_event_counts(self, period: str = "today") -> Dict:
        """获取事件计数"""
        now = datetime.now()
        if period == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start = now - timedelta(days=7)
        elif period == "month":
            start = now - timedelta(days=30)
        else:
            start = now - timedelta(days=1)
        
        return self.event_service.get_event_stats(days=(now - start).days)
    
    def get_dashboard_summary(self) -> Dict:
        """获取仪表盘概要"""
        return {
            "agent_status": self.get_agent_status_board(),
            "statistics": self.get_statistics(),
            "event_counts_today": self.get_event_counts("today"),
            "tasks_in_progress": len([
                t for t in self._get_tasks_db().values()
                if t.get("status") == "RUNNING"
            ])
        }
    
    def record_task_event(self, task_id: str, event_type: str, data: Dict = None):
        """记录任务事件"""
        tasks_db = self._get_tasks_db()
        task = tasks_db.get(task_id, {})
        
        self.event_service.emit(
            event_type,
            data or {"task_id": task_id, "task_name": task.get("name")},
            source=f"task:{task_id}"
        )
    
    def record_agent_event(self, agent_id: str, event_type: str, data: Dict = None):
        """记录Agent事件"""
        agents_db = self._get_agents_db()
        agent = agents_db.get(agent_id, {})
        
        self.event_service.emit(
            event_type,
            data or {"agent_id": agent_id, "agent_name": agent.get("name")},
            source=f"agent:{agent_id}"
        )
