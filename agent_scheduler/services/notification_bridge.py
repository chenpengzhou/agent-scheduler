"""
消息通知桥接 - 负责实际发送消息到各种渠道
"""
from typing import Dict, List, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class MessageChannel:
    """消息渠道"""
    FEISHU = "feishu"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    WEBHOOK = "webhook"
    CONSOLE = "console"  # 开发调试用


class MessageBridge:
    """消息桥接 - 发送到各个平台"""
    
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.default_channel = MessageChannel.CONSOLE
        
        # 注册默认处理器
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认处理器"""
        self.handlers[MessageChannel.CONSOLE] = self._send_console
        self.handlers[MessageChannel.FEISHU] = self._send_feishu
        self.handlers[MessageChannel.TELEGRAM] = self._send_telegram
    
    def register_handler(self, channel: str, handler: Callable):
        """注册自定义消息处理器"""
        self.handlers[channel] = handler
        logger.info(f"Registered message handler for: {channel}")
    
    def send(
        self,
        message: str,
        channel: str = None,
        targets: List[str] = None,
        metadata: Dict = None
    ) -> bool:
        """发送消息"""
        channel = channel or self.default_channel
        targets = targets or []
        
        handler = self.handlers.get(channel)
        
        if not handler:
            logger.warning(f"No handler for channel: {channel}, using console")
            handler = self.handlers[MessageChannel.CONSOLE]
        
        try:
            result = handler(message, targets, metadata or {})
            logger.info(f"Message sent via {channel}: {len(message)} chars")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    def _send_console(self, message: str, targets: List[str], metadata: Dict) -> bool:
        """发送到控制台"""
        print("\n" + "="*50)
        print("📨 AGENT MESSAGE")
        print("="*50)
        print(message)
        if targets:
            print(f"Targets: {', '.join(targets)}")
        print("="*50 + "\n")
        return True
    
    def _send_feishu(self, message: str, targets: List[str], metadata: Dict) -> bool:
        """发送到飞书"""
        # 这里会调用OpenClaw的消息系统
        # 实际发送逻辑由网关处理
        logger.info(f"[FEISHU] Would send to {targets}: {message[:50]}...")
        
        # 可以通过OpenClaw的消息API发送
        # from openclaw import message
        # message.send(channel="feishu", target=target, message=message)
        
        return True
    
    def _send_telegram(self, message: str, targets: List[str], metadata: Dict) -> bool:
        """发送到Telegram"""
        logger.info(f"[TELEGRAM] Would send to {targets}: {message[:50]}...")
        return True
    
    def send_to_group(self, message: str, group_id: str) -> bool:
        """发送消息到群组"""
        return self.send(message, targets=[group_id])
    
    def send_to_user(self, message: str, user_id: str) -> bool:
        """发送消息给用户"""
        return self.send(message, targets=[user_id])


class NotificationBridge:
    """通知桥接 - 与Agent调度系统的通知服务集成"""
    
    def __init__(self, message_bridge: MessageBridge = None):
        self.message_bridge = message_bridge or MessageBridge()
        self.enabled = True
    
    def notify_task_received(
        self,
        agent_name: str,
        task_name: str,
        priority: int,
        group_id: str = None
    ):
        """通知任务接收"""
        if not self.enabled:
            return
        
        from .message_service import MessageService
        message = MessageService.task_received(
            agent_name=agent_name,
            task_name=task_name,
            priority=priority
        )
        
        self.message_bridge.send(message, targets=[group_id] if group_id else [])
    
    def notify_task_started(
        self,
        agent_name: str,
        task_name: str,
        priority: int,
        group_id: str = None
    ):
        """通知任务开始"""
        if not self.enabled:
            return
        
        from .message_service import MessageService
        message = MessageService.task_started(
            agent_name=agent_name,
            task_name=task_name,
            priority=priority
        )
        
        self.message_bridge.send(message, targets=[group_id] if group_id else [])
    
    def notify_task_completed(
        self,
        agent_name: str,
        task_name: str,
        duration_seconds: float,
        next_agent: str = "",
        group_id: str = None
    ):
        """通知任务完成"""
        if not self.enabled:
            return
        
        from .message_service import MessageService
        message = MessageService.task_completed(
            agent_name=agent_name,
            task_name=task_name,
            duration_seconds=duration_seconds,
            next_agent=next_agent
        )
        
        self.message_bridge.send(message, targets=[group_id] if group_id else [])
    
    def notify_task_transferred(
        self,
        task_name: str,
        from_agent: str,
        to_agent: str,
        group_id: str = None
    ):
        """通知任务流转"""
        if not self.enabled:
            return
        
        from .message_service import MessageService
        message = MessageService.task_transferred(
            task_name=task_name,
            from_agent=from_agent,
            to_agent=to_agent
        )
        
        self.message_bridge.send(message, targets=[group_id] if group_id else [])
    
    def notify_task_failed(
        self,
        agent_name: str,
        task_name: str,
        error_message: str,
        group_id: str = None
    ):
        """通知任务失败"""
        if not self.enabled:
            return
        
        from .message_service import MessageService
        message = MessageService.task_failed(
            agent_name=agent_name,
            task_name=task_name,
            error_message=error_message
        )
        
        self.message_bridge.send(message, targets=[group_id] if group_id else [])


# 全局实例
_message_bridge = MessageBridge()
_notification_bridge = NotificationBridge(_message_bridge)


def get_message_bridge() -> MessageBridge:
    return _message_bridge


def get_notification_bridge() -> NotificationBridge:
    return _notification_bridge
