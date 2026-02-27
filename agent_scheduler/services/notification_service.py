"""
通知服务 - 审批和任务通知
"""
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """通知类型"""
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    TASK_ASSIGNED = "TASK_ASSIGNED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    DEMAND_CREATED = "DEMAND_CREATED"
    DEMAND_COMPLETED = "DEMAND_COMPLETED"
    STAGE_TRANSITIONED = "STAGE_TRANSITIONED"


class NotificationChannel(Enum):
    """通知渠道"""
    EMAIL = "email"
    FEISHU = "feishu"
    DINGTALK = "dingtalk"
    SMS = "sms"
    WEBHOOK = "webhook"


class Notification:
    """通知"""
    def __init__(
        self,
        notification_type: NotificationType,
        title: str,
        content: str,
        recipients: List[str],
        channel: NotificationChannel = NotificationChannel.FEISHU,
        metadata: Dict = None
    ):
        self.id = f"notif_{datetime.now().timestamp()}"
        self.type = notification_type
        self.title = title
        self.content = content
        self.recipients = recipients
        self.channel = channel
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.sent_at: Optional[datetime] = None
        self.status = "pending"  # pending, sent, failed


class NotificationService:
    """通知服务"""
    
    def __init__(self):
        self.notifications: List[Notification] = []
        self.handlers: Dict[NotificationChannel, Callable] = {}
        self.notification_queue: List[Notification] = []
    
    def register_handler(self, channel: NotificationChannel, handler: Callable):
        """注册通知处理器"""
        self.handlers[channel] = handler
        logger.info(f"Registered handler for channel: {channel.value}")
    
    def send(
        self,
        notification_type: NotificationType,
        title: str,
        content: str,
        recipients: List[str],
        channel: NotificationChannel = NotificationChannel.FEISHU,
        metadata: Dict = None
    ) -> str:
        """发送通知"""
        notification = Notification(
            notification_type=notification_type,
            title=title,
            content=content,
            recipients=recipients,
            channel=channel,
            metadata=metadata
        )
        
        self.notifications.append(notification)
        
        # 尝试发送
        handler = self.handlers.get(channel)
        if handler:
            try:
                handler(notification)
                notification.status = "sent"
                notification.sent_at = datetime.now()
                logger.info(f"Notification sent: {notification.id}")
            except Exception as e:
                notification.status = "failed"
                logger.error(f"Failed to send notification: {e}")
        else:
            # 加入队列等待处理
            self.notification_queue.append(notification)
            logger.info(f"Notification queued: {notification.id}")
        
        return notification.id
    
    def send_approval_notification(
        self,
        approval_id: str,
        demand_id: str,
        demand_title: str,
        approver_id: str,
        action: str  # requested, approved, rejected
    ) -> str:
        """发送审批通知"""
        if action == "requested":
            title = "待审批"
            content = f"需求「{demand_title}」需要您的审批"
        elif action == "approved":
            title = "审批通过"
            content = f"需求「{demand_title}」已通过审批"
        else:
            title = "审批拒绝"
            content = f"需求「{demand_title}」已被拒绝"
        
        return self.send(
            notification_type=NotificationType.APPROVAL_REQUESTED if action == "requested" 
            else NotificationType.APPROVED if action == "approved" 
            else NotificationType.REJECTED,
            title=title,
            content=content,
            recipients=[approver_id],
            metadata={"approval_id": approval_id, "demand_id": demand_id}
        )
    
    def send_task_notification(
        self,
        task_id: str,
        task_name: str,
        agent_id: str,
        action: str  # assigned, started, completed, failed
    ) -> str:
        """发送任务通知"""
        if action == "assigned":
            title = "新任务分配"
            content = f"您有新任务: {task_name}"
        elif action == "started":
            title = "任务开始"
            content = f"任务已开始: {task_name}"
        elif action == "completed":
            title = "任务完成"
            content = f"任务已完成: {task_name}"
        else:
            title = "任务失败"
            content = f"任务执行失败: {task_name}"
        
        return self.send(
            notification_type=getattr(NotificationType, f"TASK_{action.upper()}"),
            title=title,
            content=content,
            recipients=[agent_id],
            metadata={"task_id": task_id}
        )
    
    def send_demand_notification(
        self,
        demand_id: str,
        demand_title: str,
        owner_id: str,
        action: str  # created, completed, stage_changed
    ) -> str:
        """发送需求通知"""
        if action == "created":
            title = "新需求创建"
            content = f"新需求已创建: {demand_title}"
        elif action == "completed":
            title = "需求完成"
            content = f"需求已完成: {demand_title}"
        else:
            title = "需求阶段变更"
            content = f"需求阶段已变更: {demand_title}"
        
        return self.send(
            notification_type=getattr(NotificationType, f"DEMAND_{action.upper()}") if action != "stage_changed" else NotificationType.STAGE_TRANSITIONED,
            title=title,
            content=content,
            recipients=[owner_id],
            metadata={"demand_id": demand_id}
        )
    
    def get_notifications(
        self,
        recipient_id: Optional[str] = None,
        notification_type: Optional[NotificationType] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """获取通知列表"""
        result = self.notifications
        
        if recipient_id:
            result = [n for n in result if recipient_id in n.recipients]
        if notification_type:
            result = [n for n in result if n.type == notification_type]
        if status:
            result = [n for n in result if n.status == status]
        
        result.sort(key=lambda x: x.created_at, reverse=True)
        return result[:limit]
    
    def get_statistics(self) -> Dict:
        """获取通知统计"""
        total = len(self.notifications)
        sent = len([n for n in self.notifications if n.status == "sent"])
        failed = len([n for n in self.notifications if n.status == "failed"])
        pending = len([n for n in self.notifications if n.status == "pending"])
        
        by_type = {}
        for n in self.notifications:
            t = n.type.value
            by_type[t] = by_type.get(t, 0) + 1
        
        return {
            "total": total,
            "sent": sent,
            "failed": failed,
            "pending": pending,
            "by_type": by_type
        }
    
    def process_queue(self):
        """处理通知队列"""
        while self.notification_queue:
            notification = self.notification_queue.pop(0)
            handler = self.handlers.get(notification.channel)
            
            if handler:
                try:
                    handler(notification)
                    notification.status = "sent"
                    notification.sent_at = datetime.now()
                except Exception as e:
                    notification.status = "failed"
                    logger.error(f"Failed to process notification: {e}")


# 全局通知服务
_notification_service = NotificationService()


def get_notification_service() -> NotificationService:
    """获取通知服务实例"""
    return _notification_service
