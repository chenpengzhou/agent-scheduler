"""
消息管理API - Agent消息通知
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/messages", tags=["messages"])

# 全局桥接实例
_notification_bridge = None


def init_service():
    """初始化服务"""
    from agent_scheduler.services.notification_bridge import get_notification_bridge
    global _notification_bridge
    _notification_bridge = get_notification_bridge()


# Pydantic模型
class TaskEventNotifyRequest(BaseModel):
    event_type: str  # TASK_RECEIVED, TASK_STARTED, TASK_COMPLETED, TASK_TRANSFERRED, TASK_FAILED
    agent_name: str
    task_name: str
    priority: int = 2
    group_id: Optional[str] = None
    duration_seconds: float = 0
    next_agent: str = ""
    from_agent: str = ""
    to_agent: str = ""
    error_message: str = ""


class CustomMessageRequest(BaseModel):
    message: str
    channel: str = "console"
    targets: List[str] = []


# API路由
@router.post("/task-event")
async def notify_task_event(request: TaskEventNotifyRequest):
    """发送任务事件通知"""
    if not _notification_bridge:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    event_handlers = {
        "TASK_RECEIVED": _notification_bridge.notify_task_received,
        "TASK_STARTED": _notification_bridge.notify_task_started,
        "TASK_COMPLETED": _notification_bridge.notify_task_completed,
        "TASK_TRANSFERRED": _notification_bridge.notify_task_transferred,
        "TASK_FAILED": _notification_bridge.notify_task_failed
    }
    
    handler = event_handlers.get(request.event_type)
    
    if not handler:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Must be one of: {list(event_handlers.keys())}"
        )
    
    # 根据事件类型调用对应的处理方法
    if request.event_type == "TASK_RECEIVED":
        handler(request.agent_name, request.task_name, request.priority, request.group_id)
    elif request.event_type == "TASK_STARTED":
        handler(request.agent_name, request.task_name, request.priority, request.group_id)
    elif request.event_type == "TASK_COMPLETED":
        handler(
            request.agent_name,
            request.task_name,
            request.duration_seconds,
            request.next_agent,
            request.group_id
        )
    elif request.event_type == "TASK_TRANSFERRED":
        handler(request.task_name, request.from_agent, request.to_agent, request.group_id)
    elif request.event_type == "TASK_FAILED":
        handler(request.agent_name, request.task_name, request.error_message, request.group_id)
    
    return {"success": True, "event_type": request.event_type}


@router.post("/send")
async def send_custom_message(request: CustomMessageRequest):
    """发送自定义消息"""
    if not _notification_bridge:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    success = _notification_bridge.message_bridge.send(
        message=request.message,
        channel=request.channel,
        targets=request.targets
    )
    
    return {"success": success}


@router.get("/templates")
async def get_message_templates():
    """获取消息模板"""
    from agent_scheduler.services.message_service import MessageTemplate
    
    return {
        "templates": {
            "TASK_RECEIVED": MessageTemplate.TASK_RECEIVED,
            "TASK_STARTED": MessageTemplate.TASK_STARTED,
            "TASK_COMPLETED": MessageTemplate.TASK_COMPLETED,
            "TASK_TRANSFERRED": MessageTemplate.TASK_TRANSFERRED,
            "TASK_FAILED": MessageTemplate.TASK_FAILED,
            "QUEUE_UPDATED": MessageTemplate.QUEUE_UPDATED
        }
    }


@router.post("/preview")
async def preview_message(event_type: str, **kwargs):
    """预览消息"""
    from agent_scheduler.services.message_service import MessageService
    
    try:
        message = MessageService.build_message(event_type, **kwargs)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
