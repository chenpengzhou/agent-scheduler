"""
异常处理和监控告警服务
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class AlertLevel:
    """告警级别"""
    P0 = "P0"  # 紧急
    P1 = "P1"  # 高
    P2 = "P2"  # 中
    P3 = "P3"  # 低


class AlertType:
    """告警类型"""
    TASK_STUCK = "TASK_STUCK"           # 任务卡住
    TASK_LOOP = "TASK_LOOP"            # 任务循环
    AGENT_OFFLINE = "AGENT_OFFLINE"     # Agent离线
    WORKFLOW_BLOCKED = "WORKFLOW_BLOCKED"  # 工作流阻塞
    MAX_TRANSITIONS = "MAX_TRANSITIONS"  # 最大流转次数


class ExceptionHandler:
    """异常处理器"""
    
    def __init__(self):
        self.alert_history: List[Dict] = []
        self.max_transitions = 10  # 最大流转次数
        self.stuck_threshold_minutes = 30  # 卡住阈值(分钟)
        self.offline_threshold_minutes = 60  # 离线阈值(分钟)
    
    def check_task_stuck(self, task: Dict) -> Optional[Dict]:
        """检查任务是否卡住"""
        if task.get("status") not in ["RUNNING", "PENDING"]:
            return None
        
        # 检查运行时间
        started_at = task.get("started_at") or task.get("created_at")
        if not started_at:
            return None
        
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at)
        
        elapsed = datetime.now() - started_at
        elapsed_minutes = elapsed.total_seconds() / 60
        
        if elapsed_minutes > self.stuck_threshold_minutes:
            return {
                "type": AlertType.TASK_STUCK,
                "level": AlertLevel.P0 if elapsed_minutes > 60 else AlertLevel.P1,
                "task_id": task["id"],
                "task_name": task.get("name"),
                "message": f"任务已运行 {int(elapsed_minutes)} 分钟",
                "elapsed_minutes": int(elapsed_minutes)
            }
        
        return None
    
    def check_task_loop(self, task: Dict) -> Optional[Dict]:
        """检查任务是否循环"""
        transition_count = len(task.get("transition_history", []))
        
        if transition_count > self.max_transitions:
            return {
                "type": AlertType.TASK_LOOP,
                "level": AlertLevel.P0,
                "task_id": task["id"],
                "task_name": task.get("name"),
                "message": f"任务已流转 {transition_count} 次",
                "transition_count": transition_count
            }
        
        return None
    
    def check_agent_offline(self, agent: Dict) -> Optional[Dict]:
        """检查Agent是否离线"""
        if agent.get("status") == "OFFLINE":
            last_active = agent.get("last_active_at")
            if not last_active:
                return {
                    "type": AlertType.AGENT_OFFLINE,
                    "level": AlertLevel.P2,
                    "agent_id": agent["id"],
                    "agent_name": agent.get("name"),
                    "message": "Agent已离线"
                }
            
            if isinstance(last_active, str):
                last_active = datetime.fromisoformat(last_active)
            
            elapsed = datetime.now() - last_active
            elapsed_minutes = elapsed.total_seconds() / 60
            
            if elapsed_minutes > self.offline_threshold_minutes:
                return {
                    "type": AlertType.AGENT_OFFLINE,
                    "level": AlertLevel.P1,
                    "agent_id": agent["id"],
                    "agent_name": agent.get("name"),
                    "message": f"Agent已离线 {int(elapsed_minutes)} 分钟"
                }
        
        return None
    
    def check_workflow_blocked(self, task: Dict, workflow_service) -> Optional[Dict]:
        """检查工作流是否阻塞"""
        current_stage = task.get("workflow_stage")
        if not current_stage:
            return None
        
        # 检查是否有下一个阶段
        next_stage = workflow_service.get_next_stage(current_stage)
        
        if not next_stage:
            # 检查是否在最终阶段
            if current_stage == "ACCEPTANCE":
                return None  # 正常完成
            
            # 尝试查找下一个Agent
            next_agent = workflow_service.find_next_agent(current_stage)
            
            if not next_agent:
                return {
                    "type": AlertType.WORKFLOW_BLOCKED,
                    "level": AlertLevel.P1,
                    "task_id": task["id"],
                    "task_name": task.get("name"),
                    "current_stage": current_stage,
                    "message": f"工作流在 {current_stage} 阶段阻塞，无法找到下一个Agent"
                }
        
        return None
    
    def process_all(self, tasks: List[Dict], agents: List[Dict], workflow_service = None) -> List[Dict]:
        """处理所有异常检查"""
        alerts = []
        
        # 检查任务
        for task in tasks:
            # 检查卡住
            alert = self.check_task_stuck(task)
            if alert:
                alerts.append(alert)
            
            # 检查循环
            alert = self.check_task_loop(task)
            if alert:
                alerts.append(alert)
            
            # 检查工作流阻塞
            if workflow_service:
                alert = self.check_workflow_blocked(task, workflow_service)
                if alert:
                    alerts.append(alert)
        
        # 检查Agent
        for agent in agents:
            alert = self.check_agent_offline(agent)
            if alert:
                alerts.append(alert)
        
        # 记录历史
        self.alert_history.extend(alerts)
        
        return alerts
    
    def get_alerts_by_level(self, level: str) -> List[Dict]:
        """按级别获取告警"""
        return [a for a in self.alert_history if a.get("level") == level]
    
    def get_alerts_by_type(self, alert_type: str) -> List[Dict]:
        """按类型获取告警"""
        return [a for a in self.alert_history if a.get("type") == alert_type]
    
    def clear_alerts(self):
        """清空告警历史"""
        self.alert_history.clear()


class SystemMonitor:
    """系统监控"""
    
    def __init__(self):
        self.metrics = {
            "total_tasks": 0,
            "running_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "total_agents": 0,
            "active_agents": 0,
            "avg_task_duration": 0
        }
    
    def collect_metrics(self, tasks_db: Dict, agents_db: Dict):
        """收集指标"""
        self.metrics["total_tasks"] = len(tasks_db)
        self.metrics["total_agents"] = len(agents_db)
        
        # 统计任务状态
        status_counts = defaultdict(int)
        durations = []
        
        for task in tasks_db.values():
            status_counts[task.get("status", "UNKNOWN")] += 1
            
            # 计算已完成任务的耗时
            if task.get("status") == "COMPLETED":
                started = task.get("started_at") or task.get("created_at")
                completed = task.get("completed_at")
                
                if started and completed:
                    if isinstance(started, str):
                        started = datetime.fromisoformat(started)
                    if isinstance(completed, str):
                        completed = datetime.fromisoformat(completed)
                    
                    duration = (completed - started).total_seconds()
                    durations.append(duration)
        
        self.metrics["running_tasks"] = status_counts.get("RUNNING", 0)
        self.metrics["completed_tasks"] = status_counts.get("COMPLETED", 0)
        self.metrics["failed_tasks"] = status_counts.get("FAILED", 0)
        
        # 计算平均耗时
        if durations:
            self.metrics["avg_task_duration"] = sum(durations) / len(durations)
        
        # 统计Agent状态
        active_count = sum(1 for a in agents_db.values() if a.get("status") != "OFFLINE")
        self.metrics["active_agents"] = active_count
        
        return self.metrics
    
    def get_health_status(self) -> Dict:
        """获取健康状态"""
        # 简单的健康检查
        issues = []
        
        if self.metrics["failed_tasks"] > self.metrics["total_tasks"] * 0.2:
            issues.append("失败率过高")
        
        if self.metrics["active_agents"] == 0 and self.metrics["total_agents"] > 0:
            issues.append("没有活跃的Agent")
        
        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "metrics": self.metrics
        }
