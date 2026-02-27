"""
任务耗时统计服务
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class DurationService:
    """任务耗时统计服务"""
    
    def __init__(self, tasks_db: Dict = None):
        self.tasks_db = tasks_db or {}
    
    def get_task_duration(self, task_id: str) -> Optional[Dict]:
        """获取任务耗时详情"""
        task = self.tasks_db.get(task_id)
        if not task:
            return None
        
        return self._calculate_duration_details(task)
    
    def _calculate_duration_details(self, task: Dict) -> Dict:
        """计算任务耗时详情"""
        created = task.get("created_at")
        started = task.get("started_at")
        completed = task.get("completed_at")
        
        # 总耗时
        total_seconds = 0
        if created:
            end_time = completed or datetime.now()
            total_seconds = (end_time - created).total_seconds()
        
        # 各阶段耗时
        stage_durations = {}
        
        # PENDING阶段
        if created and started:
            pending_seconds = (started - created).total_seconds()
            if pending_seconds > 0:
                stage_durations["PENDING"] = {
                    "seconds": pending_seconds,
                    "formatted": self._format_duration(pending_seconds)
                }
        
        # RUNNING阶段
        if started:
            end_time = completed or datetime.now()
            running_seconds = (end_time - started).total_seconds()
            if running_seconds > 0:
                stage_durations["RUNNING"] = {
                    "seconds": running_seconds,
                    "formatted": self._format_duration(running_seconds)
                }
        
        return {
            "task_id": task.get("id"),
            "task_name": task.get("name"),
            "status": task.get("status"),
            "total_seconds": total_seconds,
            "total_formatted": self._format_duration(total_seconds),
            "stage_durations": stage_durations,
            "created_at": created.isoformat() if created else None,
            "started_at": started.isoformat() if started else None,
            "completed_at": completed.isoformat() if completed else None
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
    
    def get_average_duration(self, status: str = None) -> Dict:
        """获取平均耗时"""
        tasks = list(self.tasks_db.values())
        
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        
        if not tasks:
            return {"average_seconds": 0, "formatted": "0秒"}
        
        total_seconds = 0
        count = 0
        
        for task in tasks:
            created = task.get("created_at")
            completed = task.get("completed_at") or datetime.now()
            
            if created and completed:
                duration = (completed - created).total_seconds()
                total_seconds += duration
                count += 1
        
        avg_seconds = total_seconds / count if count > 0 else 0
        
        return {
            "average_seconds": avg_seconds,
            "formatted": self._format_duration(avg_seconds),
            "sample_count": count
        }
    
    def get_duration_stats(self, days: int = 7) -> Dict:
        """获取耗时统计"""
        now = datetime.now()
        cutoff = now - timedelta(days=days)
        
        # 过滤最近的任务
        recent_tasks = [
            t for t in self.tasks_db.values()
            if t.get("created_at") and t.get("created_at") > cutoff
        ]
        
        if not recent_tasks:
            return {
                "period_days": days,
                "total_tasks": 0,
                "average_seconds": 0,
                "formatted": "0秒",
                "by_status": {}
            }
        
        # 按状态统计
        by_status = defaultdict(lambda: {"total": 0, "count": 0})
        
        for task in recent_tasks:
            status = task.get("status", "UNKNOWN")
            created = task.get("created_at")
            completed = task.get("completed_at") or datetime.now()
            
            if created:
                duration = (completed - created).total_seconds()
                by_status[status]["total"] += duration
                by_status[status]["count"] += 1
        
        # 计算平均值
        for status in by_status:
            total = by_status[status]["total"]
            count = by_status[status]["count"]
            by_status[status]["average_seconds"] = total / count if count > 0 else 0
            by_status[status]["formatted"] = self._format_duration(total / count if count > 0 else 0)
        
        # 总体平均
        all_durations = []
        for task in recent_tasks:
            created = task.get("created_at")
            completed = task.get("completed_at") or datetime.now()
            if created:
                all_durations.append((completed - created).total_seconds())
        
        avg_seconds = sum(all_durations) / len(all_durations) if all_durations else 0
        
        return {
            "period_days": days,
            "total_tasks": len(recent_tasks),
            "average_seconds": avg_seconds,
            "formatted": self._format_duration(avg_seconds),
            "by_status": dict(by_status)
        }
    
    def get_slowest_tasks(self, limit: int = 10) -> List[Dict]:
        """获取耗时最长的任务"""
        tasks_with_duration = []
        
        for task in self.tasks_db.values():
            created = task.get("created_at")
            completed = task.get("completed_at") or datetime.now()
            
            if created:
                duration = (completed - created).total_seconds()
                tasks_with_duration.append({
                    "task_id": task.get("id"),
                    "task_name": task.get("name"),
                    "status": task.get("status"),
                    "duration_seconds": duration,
                    "formatted": self._format_duration(duration)
                })
        
        # 排序
        tasks_with_duration.sort(key=lambda x: x["duration_seconds"], reverse=True)
        
        return tasks_with_duration[:limit]


class TaskDetailService:
    """任务详情服务"""
    
    def __init__(self, tasks_db: Dict = None):
        self.tasks_db = tasks_db or {}
    
    def get_task_detail(self, task_id: str) -> Optional[Dict]:
        """获取任务完整详情"""
        task = self.tasks_db.get(task_id)
        if not task:
            return None
        
        # 基本信息
        detail = {
            "id": task.get("id"),
            "name": task.get("name"),
            "description": task.get("description"),
            "status": task.get("status"),
            "priority": task.get("priority"),
            "demand_id": task.get("demand_id"),
            "assigned_agent_id": task.get("assigned_agent_id"),
            "depends_on": task.get("depends_on", []),
            "created_at": task.get("created_at"),
            "updated_at": task.get("updated_at"),
            "started_at": task.get("started_at"),
            "completed_at": task.get("completed_at")
        }
        
        # 执行信息
        detail["executor_type"] = task.get("executor_type", "agent")
        detail["executor_params"] = task.get("executor_params", {})
        detail["input_data"] = task.get("input_data", {})
        detail["output_data"] = task.get("output_data", {})
        
        # 错误信息
        detail["error_message"] = task.get("error_message", "")
        
        # 重试信息
        detail["retry_count"] = task.get("retry_count", 0)
        detail["max_retries"] = task.get("max_retries", 0)
        
        # 工作流信息
        detail["workflow_stage"] = task.get("workflow_stage", "")
        
        return detail
    
    def get_task_timeline(self, task_id: str) -> List[Dict]:
        """获取任务时间线"""
        task = self.tasks_db.get(task_id)
        if not task:
            return []
        
        timeline = []
        
        # 创建
        if task.get("created_at"):
            timeline.append({
                "event": "TASK_CREATED",
                "timestamp": task.get("created_at").isoformat() if hasattr(task.get("created_at"), "isoformat") else str(task.get("created_at")),
                "description": "任务创建"
            })
        
        # 开始
        if task.get("started_at"):
            timeline.append({
                "event": "TASK_STARTED",
                "timestamp": task.get("started_at").isoformat() if hasattr(task.get("started_at"), "isoformat") else str(task.get("started_at")),
                "description": "任务开始执行"
            })
        
        # 完成/失败
        if task.get("completed_at"):
            status = task.get("status", "")
            if status == "COMPLETED":
                timeline.append({
                    "event": "TASK_COMPLETED",
                    "timestamp": task.get("completed_at").isoformat() if hasattr(task.get("completed_at"), "isoformat") else str(task.get("completed_at")),
                    "description": "任务完成"
                })
            elif status in ["FAILED", "CANCELLED"]:
                timeline.append({
                    "event": "TASK_FAILED",
                    "timestamp": task.get("completed_at").isoformat() if hasattr(task.get("completed_at"), "isoformat") else str(task.get("completed_at")),
                    "description": f"任务{status}",
                    "error": task.get("error_message", "")
                })
        
        return timeline
