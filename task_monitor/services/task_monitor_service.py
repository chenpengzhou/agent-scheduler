"""
任务流转监控系统 - 任务监控服务
"""
from typing import List, Dict, Optional, Any
from datetime import datetime
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class TaskStatus:
    """任务状态定义"""
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    
    # 颜色映射
    COLORS = {
        PENDING: "🟡",
        SCHEDULED: "🔵",
        RUNNING: "🟠",
        COMPLETED: "🟢",
        FAILED: "🔴",
        TIMEOUT: "⚫",
        CANCELLED: "⚪"
    }
    
    # 流转方向
    TRANSITIONS = {
        PENDING: [SCHEDULED, CANCELLED],
        SCHEDULED: [RUNNING, PENDING, CANCELLED],
        RUNNING: [COMPLETED, FAILED, TIMEOUT, CANCELLED],
        COMPLETED: [],  # 终态
        FAILED: [PENDING, RUNNING],  # 可重试
        TIMEOUT: [PENDING, RUNNING],  # 可重试
        CANCELLED: [PENDING]  # 可重新开始
    }
    
    @classmethod
    def get_color(cls, status: str) -> str:
        return cls.COLORS.get(status, "⚪")
    
    @classmethod
    def get_next_statuses(cls, status: str) -> List[str]:
        return cls.TRANSITIONS.get(status, [])


class TaskMonitorService:
    """任务监控服务"""
    
    def __init__(self, tasks_db: Dict = None):
        self.tasks_db = tasks_db or {}
    
    def get_task_list(
        self,
        status: Optional[List[str]] = None,
        agent_id: Optional[str] = None,
        priority: Optional[int] = None,
        demand_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """获取任务列表"""
        tasks = list(self.tasks_db.values())
        
        # 筛选
        if status:
            tasks = [t for t in tasks if t.get("status") in status]
        if agent_id:
            tasks = [t for t in tasks if t.get("assigned_agent_id") == agent_id]
        if priority is not None:
            tasks = [t for t in tasks if t.get("priority") == priority]
        if demand_id:
            tasks = [t for t in tasks if t.get("demand_id") == demand_id]
        
        # 排序：按状态优先级，然后按创建时间
        status_order = {
            "RUNNING": 0,
            "PENDING": 1,
            "SCHEDULED": 2,
            "FAILED": 3,
            "TIMEOUT": 4,
            "COMPLETED": 5,
            "CANCELLED": 6
        }
        tasks.sort(key=lambda t: (
            status_order.get(t.get("status", ""), 99),
            t.get("created_at", datetime.min)
        ))
        
        return tasks[offset:offset + limit]
    
    def get_task_stats(self) -> Dict:
        """获取任务状态统计"""
        stats = {
            "total": len(self.tasks_db),
            "by_status": defaultdict(int),
            "by_priority": defaultdict(int)
        }
        
        for task in self.tasks_db.values():
            status = task.get("status", "PENDING")
            priority = task.get("priority", 2)
            
            stats["by_status"][status] += 1
            stats["by_priority"][f"P{priority}"] += 1
        
        # 转换为普通dict
        stats["by_status"] = dict(stats["by_status"])
        stats["by_priority"] = dict(stats["by_priority"])
        
        # 计算百分比
        if stats["total"] > 0:
            stats["by_status_pct"] = {
                k: round(v / stats["total"] * 100, 1)
                for k, v in stats["by_status"].items()
            }
        else:
            stats["by_status_pct"] = {}
        
        return stats
    
    def get_task_detail(self, task_id: str) -> Optional[Dict]:
        """获取任务详情"""
        task = self.tasks_db.get(task_id)
        if not task:
            return None
        
        # 计算耗时
        duration_info = self._calculate_duration(task)
        
        # 获取流转方向
        current_status = task.get("status", "PENDING")
        next_statuses = TaskStatus.get_next_statuses(current_status)
        
        return {
            "id": task.get("id"),
            "name": task.get("name"),
            "description": task.get("description"),
            "status": current_status,
            "status_color": TaskStatus.get_color(current_status),
            "priority": task.get("priority"),
            "demand_id": task.get("demand_id"),
            "assigned_agent_id": task.get("assigned_agent_id"),
            "created_at": task.get("created_at"),
            "started_at": task.get("started_at"),
            "completed_at": task.get("completed_at"),
            "duration": duration_info,
            "next_possible_statuses": next_statuses,
            "depends_on": task.get("depends_on", [])
        }
    
    def _calculate_duration(self, task: Dict) -> Dict:
        """计算任务耗时"""
        created = task.get("created_at")
        started = task.get("started_at")
        completed = task.get("completed_at")
        
        if not created:
            return {"total_seconds": 0, "formatted": "0秒"}
        
        # 计算总耗时
        end_time = completed or datetime.now()
        total_seconds = (end_time - created).total_seconds()
        
        # 格式化
        formatted = self._format_duration(total_seconds)
        
        return {
            "total_seconds": total_seconds,
            "formatted": formatted
        }
    
    def _format_duration(self, seconds: float) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{int(seconds)}秒"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}分{secs}秒"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            secs = int(seconds % 60)
            return f"{hours}小时{minutes}分{secs}秒"
    
    def get_transition_graph(self, task_id: str) -> Dict:
        """获取任务流转图"""
        task = self.tasks_db.get(task_id)
        if not task:
            return None
        
        current_status = task.get("status", "PENDING")
        next_statuses = TaskStatus.get_next_statuses(current_status)
        
        # 构建流转图
        graph = {
            "current_status": current_status,
            "current_color": TaskStatus.get_color(current_status),
            "next_statuses": [
                {
                    "status": s,
                    "color": TaskStatus.get_color(s)
                }
                for s in next_statuses
            ],
            "possible_paths": self._build_paths(current_status)
        }
        
        return graph
    
    def _build_paths(self, status: str, max_depth: int = 3) -> List[List[str]]:
        """构建从当前状态开始的所有可能路径"""
        paths = []
        
        def dfs(current: str, path: List[str], depth: int):
            if depth > max_depth:
                return
            
            next_statuses = TaskStatus.get_next_statuses(current)
            
            if not next_statuses:
                paths.append(path + [current])
            else:
                for next_s in next_statuses:
                    dfs(next_s, path + [current], depth + 1)
        
        dfs(status, [], 0)
        return paths
    
    def get_status_filter_options(self) -> List[Dict]:
        """获取状态筛选选项"""
        return [
            {"value": "PENDING", "label": "🟡 待处理", "color": "yellow"},
            {"value": "SCHEDULED", "label": "🔵 已调度", "color": "blue"},
            {"value": "RUNNING", "label": "🟠 执行中", "color": "orange"},
            {"value": "COMPLETED", "label": "🟢 已完成", "color": "green"},
            {"value": "FAILED", "label": "🔴 失败", "color": "red"},
            {"value": "TIMEOUT", "label": "⚫ 超时", "color": "black"},
            {"value": "CANCELLED", "label": "⚪ 已取消", "color": "gray"}
        ]
