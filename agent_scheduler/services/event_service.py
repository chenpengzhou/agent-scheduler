"""
事件服务 - 实时事件流管理
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


class EventType:
    """事件类型"""
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_TIMEOUT = "TASK_TIMEOUT"
    STATUS_CHANGED = "STATUS_CHANGED"
    AGENT_REGISTERED = "AGENT_REGISTERED"
    DEMAND_CREATED = "DEMAND_CREATED"
    DEMAND_COMPLETED = "DEMAND_COMPLETED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVAL_COMPLETED = "APPROVAL_COMPLETED"


class EventService:
    """事件服务"""
    
    def __init__(self, max_events: int = 1000):
        self.max_events = max_events
        self.events = deque(maxlen=max_events)
        self.event_handlers = []
    
    def emit(self, event_type: str, data: Dict, source: str = "") -> str:
        """发布事件"""
        event = {
            "id": f"evt_{len(self.events)}",
            "type": event_type,
            "data": data,
            "source": source,
            "timestamp": datetime.now().isoformat()
        }
        
        self.events.append(event)
        
        # 触发处理器
        for handler in self.event_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
        
        logger.info(f"Event emitted: {event_type}")
        return event["id"]
    
    def get_events(self, limit: int = 100, event_type: str = None) -> List[Dict]:
        """获取事件列表"""
        events = list(self.events)
        
        if event_type:
            events = [e for e in events if e["type"] == event_type]
        
        return events[-limit:][::-1]
    
    def get_live_feed(self, limit: int = 100) -> List[Dict]:
        """获取Live Feed（最近事件）"""
        return self.get_events(limit)
    
    def get_events_by_source(self, source: str, limit: int = 100) -> List[Dict]:
        """按来源获取事件"""
        events = [e for e in self.events if e.get("source") == source]
        return events[-limit:][::-1]
    
    def get_event_stats(self, days: int = 1) -> Dict:
        """获取事件统计"""
        now = datetime.now()
        cutoff = now - timedelta(days=days)
        
        recent_events = [
            e for e in self.events
            if datetime.fromisoformat(e["timestamp"]) > cutoff
        ]
        
        # 按类型统计
        type_counts = {}
        for e in recent_events:
            t = e["type"]
            type_counts[t] = type_counts.get(t, 0) + 1
        
        return {
            "total": len(recent_events),
            "by_type": type_counts,
            "period_days": days
        }
    
    def add_handler(self, handler):
        """添加事件处理器"""
        self.event_handlers.append(handler)
    
    def clear(self):
        """清空事件"""
        self.events.clear()


# 全局事件服务实例
_event_service = EventService()


def get_event_service() -> EventService:
    """获取事件服务实例"""
    return _event_service
