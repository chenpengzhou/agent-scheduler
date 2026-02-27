"""
消息模板服务
"""
from typing import Dict, Optional
from datetime import datetime


class MessageTemplate:
    """消息模板"""
    
    # 任务接收通知
    TASK_RECEIVED = """📥 {agent_name} 收到新任务
━━━━━━━━━━━━━━━━
任务: {task_name}
优先级: {priority}
开始执行..."""
    
    # 任务开始通知
    TASK_STARTED = """🚀 {agent_name} 开始执行任务
━━━━━━━━━━━━━━━━
任务: {task_name}
优先级: {priority}
开始时间: {start_time}"""
    
    # 任务完成通知
    TASK_COMPLETED = """✅ {agent_name} 任务完成
━━━━━━━━━━━━━━━━
任务: {task_name}
耗时: {duration}
状态: 已完成
下一步: 流转至 [{next_agent}]"""
    
    # 任务流转通知
    TASK_TRANSFERRED = """🔄 任务流转
━━━━━━━━━━━━━━━━
任务: {task_name}
从: [{from_agent}]
→ 至: [{to_agent}]"""
    
    # 任务失败通知
    TASK_FAILED = """❌ {agent_name} 任务失败
━━━━━━━━━━━━━━━━
任务: {task_name}
错误: {error_message}
需要人工介入处理"""
    
    # 任务队列更新
    QUEUE_UPDATED = """📋 任务队列更新
━━━━━━━━━━━━━━━━
Agent: {agent_name}
队列位置: {queue_position}
等待任务数: {waiting_count}"""


class MessageService:
    """消息服务 - 生成格式化消息"""
    
    @staticmethod
    def format_priority(priority: int) -> str:
        """格式化优先级"""
        priority_map = {
            0: "🔴 P0-紧急",
            1: "🟠 P1-高",
            2: "🟡 P2-中",
            3: "🔵 P3-低"
        }
        return priority_map.get(priority, f"P{priority}")
    
    @staticmethod
    def format_duration(seconds: float) -> str:
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
            return f"{hours}小时{minutes}分"
    
    @staticmethod
    def format_time(dt: datetime) -> str:
        """格式化时间"""
        return dt.strftime("%H:%M:%S")
    
    @classmethod
    def task_received(cls, agent_name: str, task_name: str, priority: int, **kwargs) -> str:
        return MessageTemplate.TASK_RECEIVED.format(
            agent_name=agent_name,
            task_name=task_name,
            priority=cls.format_priority(priority)
        )
    
    @classmethod
    def task_started(cls, agent_name: str, task_name: str, priority: int, start_time: datetime = None, **kwargs) -> str:
        if start_time is None:
            start_time = datetime.now()
        return MessageTemplate.TASK_STARTED.format(
            agent_name=agent_name,
            task_name=task_name,
            priority=cls.format_priority(priority),
            start_time=cls.format_time(start_time)
        )
    
    @classmethod
    def task_completed(cls, agent_name: str, task_name: str, duration_seconds: float, next_agent: str = "", **kwargs) -> str:
        duration = cls.format_duration(duration_seconds)
        next_info = next_agent if next_agent else "无"
        return MessageTemplate.TASK_COMPLETED.format(
            agent_name=agent_name,
            task_name=task_name,
            duration=duration,
            next_agent=next_info
        )
    
    @classmethod
    def task_transferred(cls, task_name: str, from_agent: str, to_agent: str, **kwargs) -> str:
        return MessageTemplate.TASK_TRANSFERRED.format(
            task_name=task_name,
            from_agent=from_agent,
            to_agent=to_agent
        )
    
    @classmethod
    def task_failed(cls, agent_name: str, task_name: str, error_message: str, **kwargs) -> str:
        return MessageTemplate.TASK_FAILED.format(
            agent_name=agent_name,
            task_name=task_name,
            error_message=error_message or "未知错误"
        )
    
    @classmethod
    def queue_updated(cls, agent_name: str, queue_position: int, waiting_count: int, **kwargs) -> str:
        return MessageTemplate.QUEUE_UPDATED.format(
            agent_name=agent_name,
            queue_position=queue_position,
            waiting_count=waiting_count
        )
    
    @classmethod
    def build_message(cls, event_type: str, **kwargs) -> str:
        builders = {
            "TASK_RECEIVED": cls.task_received,
            "TASK_STARTED": cls.task_started,
            "TASK_COMPLETED": cls.task_completed,
            "TASK_TRANSFERRED": cls.task_transferred,
            "TASK_FAILED": cls.task_failed,
            "QUEUE_UPDATED": cls.queue_updated
        }
        builder = builders.get(event_type)
        return builder(**kwargs) if builder else f"消息: {event_type}"
