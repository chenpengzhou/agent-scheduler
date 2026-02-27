"""
通知管理API
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

# 全局服务
_notification_service = None


def init_service():
    """初始化服务"""
    from agent_scheduler.services.notification_service import get_notification_service
    global _notification_service
    _notification_service = get_notification_service()


# Pydantic模型
class NotificationSendRequest(BaseModel):
    notification_type: str
    title: str
    content: str
    recipients: List[str]
    channel: str = "feishu"
    metadata: dict = {}


class ApprovalNotificationRequest(BaseModel):
    approval_id: str
    demand_id: str
    demand_title: str
    approver_id: str
    action: str = "requested"  # requested, approved, rejected


class TaskNotificationRequest(BaseModel):
    task_id: str
    task_name: str
    agent_id: str
    action: str = "assigned"  # assigned, started, completed, failed


class DemandNotificationRequest(BaseModel):
    demand_id: str
    demand_title: str
    owner_id: str
    action: str = "created"  # created, completed, stage_changed


# API路由
@router.post("/send")
async def send_notification(request: NotificationSendRequest):
    """发送通知"""
    if not _notification_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    from agent_scheduler.services.notification_service import NotificationType, NotificationChannel
    
    try:
        notif_type = NotificationType(request.notification_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification type")
    
    try:
        channel = NotificationChannel(request.channel)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel")
    
    notif_id = _notification_service.send(
        notification_type=notif_type,
        title=request.title,
        content=request.content,
        recipients=request.recipients,
        channel=channel,
        metadata=request.metadata
    )
    
    return {"notification_id": notif_id, "status": "sent"}


@router.post("/approval")
async def send_approval_notification(request: ApprovalNotificationRequest):
    """发送审批通知"""
    if not _notification_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    notif_id = _notification_service.send_approval_notification(
        approval_id=request.approval_id,
        demand_id=request.demand_id,
        demand_title=request.demand_title,
        approver_id=request.approver_id,
        action=request.action
    )
    
    return {"notification_id": notif_id}


@router.post("/task")
async def send_task_notification(request: TaskNotificationRequest):
    """发送任务通知"""
    if not _notification_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    notif_id = _notification_service.send_task_notification(
        task_id=request.task_id,
        task_name=request.task_name,
        agent_id=request.agent_id,
        action=request.action
    )
    
    return {"notification_id": notif_id}


@router.post("/demand")
async def send_demand_notification(request: DemandNotificationRequest):
    """发送需求通知"""
    if not _notification_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    notif_id = _notification_service.send_demand_notification(
        demand_id=request.demand_id,
        demand_title=request.demand_title,
        owner_id=request.owner_id,
        action=request.action
    )
    
    return {"notification_id": notif_id}


@router.get("")
async def get_notifications(
    recipient_id: Optional[str] = None,
    notification_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
):
    """获取通知列表"""
    if not _notification_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    from agent_scheduler.services.notification_service import NotificationType
    
    notif_type = None
    if notification_type:
        try:
            notif_type = NotificationType(notification_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid notification type")
    
    notifications = _notification_service.get_notifications(
        recipient_id=recipient_id,
        notification_type=notif_type,
        status=status,
        limit=limit
    )
    
    return [
        {
            "id": n.id,
            "type": n.type.value,
            "title": n.title,
            "content": n.content,
            "recipients": n.recipients,
            "channel": n.channel.value,
            "status": n.status,
            "created_at": n.created_at.isoformat(),
            "sent_at": n.sent_at.isoformat() if n.sent_at else None
        }
        for n in notifications
    ]


@router.get("/statistics")
async def get_notification_statistics():
    """获取通知统计"""
    if not _notification_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    return _notification_service.get_statistics()


@router.post("/queue/process")
async def process_queue():
    """处理通知队列"""
    if not _notification_service:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    _notification_service.process_queue()
    
    return {"message": "Queue processed"}
