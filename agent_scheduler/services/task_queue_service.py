"""
任务队列服务 - Agent任务队列管理
"""
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class TaskQueueService:
    """任务队列服务"""
    
    def __init__(self, tasks_db: Dict = None, agents_db: Dict = None):
        self.tasks_db = tasks_db or {}
        self.agents_db = agents_db or {}
    
    def get_agent_queue(self, agent_id: str) -> Dict:
        """获取Agent的任务队列"""
        # 获取分配给该Agent的所有任务
        agent_tasks = []
        
        for task in self.tasks_db.values():
            if task.get("assigned_agent_id") == agent_id:
                agent_tasks.append(task)
        
        # 分类: 正在执行、等待执行
        running = []
        waiting = []
        
        for task in agent_tasks:
            status = task.get("status", "PENDING")
            if status == "RUNNING":
                running.append(task)
            else:
                waiting.append(task)
        
        # 按优先级排序
        running.sort(key=lambda t: t.get("priority", 999))
        waiting.sort(key=lambda t: (t.get("priority", 999), t.get("created_at", datetime.min)))
        
        # 计算统计
        stats = self.get_agent_queue_stats(agent_id)
        
        return {
            "agent_id": agent_id,
            "running": running,
            "waiting": waiting,
            "stats": stats
        }
    
    def get_agent_queue_stats(self, agent_id: str) -> Dict:
        """获取Agent队列统计"""
        agent = self.agents_db.get(agent_id, {})
        max_concurrent = agent.get("max_concurrent_tasks", 1)
        
        # 统计任务状态
        agent_tasks = [t for t in self.tasks_db.values() if t.get("assigned_agent_id") == agent_id]
        
        stats = {
            "total": len(agent_tasks),
            "running": sum(1 for t in agent_tasks if t.get("status") == "RUNNING"),
            "waiting": sum(1 for t in agent_tasks if t.get("status") in ["PENDING", "SCHEDULED"]),
            "completed": sum(1 for t in agent_tasks if t.get("status") == "COMPLETED"),
            "failed": sum(1 for t in agent_tasks if t.get("status") == "FAILED"),
            "max_concurrent": max_concurrent,
            "current_concurrent": sum(1 for t in agent_tasks if t.get("status") == "RUNNING")
        }
        
        # 计算可用槽位
        stats["available_slots"] = max(0, max_concurrent - stats["running"])
        
        return stats
    
    def get_next_task(self, agent_id: str) -> Optional[Dict]:
        """获取下一个待执行任务"""
        queue = self.get_agent_queue(agent_id)
        
        # 如果有正在运行的任务且已达并发上限，返回None
        if queue["stats"]["running"] >= queue["stats"]["max_concurrent"]:
            return None
        
        # 返回等待队列中的第一个任务
        if queue["waiting"]:
            return queue["waiting"][0]
        
        return None
    
    def add_to_queue(self, task_id: str, agent_id: str) -> bool:
        """将任务加入队列"""
        if task_id not in self.tasks_db:
            return False
        
        task = self.tasks_db[task_id]
        task["assigned_agent_id"] = agent_id
        task["queue_position"] = self._get_queue_position(agent_id)
        
        logger.info(f"Task {task_id} added to queue of agent {agent_id}")
        return True
    
    def remove_from_queue(self, task_id: str) -> bool:
        """从队列中移除任务"""
        if task_id not in self.tasks_db:
            return False
        
        task = self.tasks_db[task_id]
        task["assigned_agent_id"] = ""
        task.pop("queue_position", None)
        
        return True
    
    def reorder_queue(self, agent_id: str, task_ids: List[str]) -> bool:
        """重新排序队列"""
        for i, task_id in enumerate(task_ids):
            if task_id in self.tasks_db:
                self.tasks_db[task_id]["queue_position"] = i
        return True
    
    def _get_queue_position(self, agent_id: str) -> int:
        """获取队列位置"""
        positions = [
            t.get("queue_position", 0)
            for t in self.tasks_db.values()
            if t.get("assigned_agent_id") == agent_id
        ]
        return max(positions, default=-1) + 1
    
    def get_all_agent_queues(self) -> List[Dict]:
        """获取所有Agent的队列"""
        result = []
        
        for agent_id in self.agents_db.keys():
            queue = self.get_agent_queue(agent_id)
            result.append(queue)
        
        return result
    
    def get_queue_overview(self) -> Dict:
        """获取队列概览"""
        total_tasks = len(self.tasks_db)
        total_agents = len(self.agents_db)
        
        # 按状态统计
        status_counts = defaultdict(int)
        priority_counts = defaultdict(int)
        
        for task in self.tasks_db.values():
            status_counts[task.get("status", "UNKNOWN")] += 1
            priority_counts[f"P{task.get('priority', 2)}"] += 1
        
        return {
            "total_tasks": total_tasks,
            "total_agents": total_agents,
            "by_status": dict(status_counts),
            "by_priority": dict(priority_counts),
            "agents": [
                {
                    "agent_id": agent_id,
                    "name": self.agents_db[agent_id].get("name", ""),
                    **self.get_agent_queue_stats(agent_id)
                }
                for agent_id in self.agents_db.keys()
            ]
        }


class PriorityScheduler:
    """优先级调度器"""
    
    @staticmethod
    def sort_by_priority(tasks: List[Dict]) -> List[Dict]:
        """按优先级排序"""
        # P0(0) > P1(1) > P2(2) > P3(3)
        return sorted(
            tasks,
            key=lambda t: (
                t.get("priority", 999),
                t.get("created_at", datetime.min)
            )
        )
    
    @staticmethod
    def filter_runnable(tasks: List[Dict], max_concurrent: int) -> List[Dict]:
        """过滤可执行的任务"""
        running = [t for t in tasks if t.get("status") == "RUNNING"]
        
        if len(running) >= max_concurrent:
            return []
        
        pending = [t for t in tasks if t.get("status") in ["PENDING", "SCHEDULED"]]
        return PriorityScheduler.sort_by_priority(pending)[:max_concurrent - len(running)]
    
    @staticmethod
    def get_executable_tasks(tasks: List[Dict], agent_id: str, max_concurrent: int = 1) -> List[Dict]:
        """获取可执行的任务列表"""
        # 过滤属于该Agent的任务
        agent_tasks = [t for t in tasks if t.get("assigned_agent_id") == agent_id]
        
        # 过滤可执行的
        return PriorityScheduler.filter_runnable(agent_tasks, max_concurrent)
