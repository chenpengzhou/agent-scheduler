"""
审批服务 - 管理审批流程
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ..models.approval import (
    ApprovalInstance, ApprovalStatus, ApprovalType,
    ApprovalDefinition, Notification, NotificationConfig
)

logger = logging.getLogger(__name__)


class ApprovalService:
    """审批服务"""
    
    def __init__(self, notification_service=None):
        self.notification_service = notification_service
        self.pending_approvals: Dict[str, ApprovalInstance] = {}
    
    def create_approval(
        self,
        step_instance_id: str,
        workflow_instance_id: str,
        title: str,
        content: Dict[str, Any] = None,
        approver: str = None
    ) -> ApprovalInstance:
        """创建审批实例"""
        approval = ApprovalInstance(
            id="",
            step_instance_id=step_instance_id,
            workflow_instance_id=workflow_instance_id,
            title=title,
            content=content or {},
            approver=approver,
            status=ApprovalStatus.PENDING
        )
        
        self.pending_approvals[approval.id] = approval
        
        # 发送通知
        if self.notification_service:
            self.notification_service.send_approval_notification(
                approval, "approval_submitted"
            )
        
        logger.info(f"Approval created: {approval.id} for workflow {workflow_instance_id}")
        return approval
    
    def get_approval(self, approval_id: str) -> Optional[ApprovalInstance]:
        """获取审批实例"""
        return self.pending_approvals.get(approval_id)
    
    def get_approvals_for_workflow(self, workflow_instance_id: str) -> List[ApprovalInstance]:
        """获取工作流的所有审批"""
        return [
            a for a in self.pending_approvals.values()
            if a.workflow_instance_id == workflow_instance_id
        ]
    
    def approve(
        self,
        approval_id: str,
        approved_by: str,
        comment: str = ""
    ) -> Optional[ApprovalInstance]:
        """审批通过"""
        approval = self.pending_approvals.get(approval_id)
        if not approval:
            return None
        
        approval.status = ApprovalStatus.APPROVED
        approval.approved_by = approved_by
        approval.approved_at = datetime.now()
        approval.comment = comment
        
        # 发送通知
        if self.notification_service:
            self.notification_service.send_approval_notification(
                approval, "approved"
            )
        
        logger.info(f"Approval approved: {approval_id} by {approved_by}")
        return approval
    
    def reject(
        self,
        approval_id: str,
        rejected_by: str,
        comment: str = ""
    ) -> Optional[ApprovalInstance]:
        """审批拒绝"""
        approval = self.pending_approvals.get(approval_id)
        if not approval:
            return None
        
        approval.status = ApprovalStatus.REJECTED
        approval.approved_by = rejected_by
        approval.approved_at = datetime.now()
        approval.comment = comment
        
        # 发送通知
        if self.notification_service:
            self.notification_service.send_approval_notification(
                approval, "rejected"
            )
        
        logger.info(f"Approval rejected: {approval_id} by {rejected_by}")
        return approval
    
    def is_approved(self, approval_id: str) -> bool:
        """检查审批是否通过"""
        approval = self.pending_approvals.get(approval_id)
        return approval.status == ApprovalStatus.APPROVED if approval else False
    
    def is_rejected(self, approval_id: str) -> bool:
        """检查审批是否被拒绝"""
        approval = self.pending_approvals.get(approval_id)
        return approval.status == ApprovalStatus.REJECTED if approval else False


class NotificationService:
    """通知服务"""
    
    def __init__(self, config: NotificationConfig = None):
        self.config = config or NotificationConfig()
        self.notifications: List[Notification] = []
    
    def send_approval_notification(
        self,
        approval: ApprovalInstance,
        notification_type: str
    ):
        """发送审批通知"""
        # 根据类型决定是否发送
        if notification_type == "approval_submitted" and not self.config.notify_on_submit:
            return
        if notification_type == "approved" and not self.config.notify_on_approve:
            return
        if notification_type == "rejected" and not self.config.notify_on_reject:
            return
        
        # 构建通知内容
        title = f"审批{self._get_type_text(notification_type)}"
        
        if notification_type == "approval_submitted":
            content = f"您有待审批项：{approval.title}"
        elif notification_type == "approved":
            content = f"审批已通过：{approval.title}"
        else:
            content = f"审批已拒绝：{approval.title}"
        
        # 创建通知
        notification = Notification(
            id="",
            notification_type=notification_type,
            title=title,
            content=content,
            recipients=[approval.approver] if approval.approver else [],
            channels=self.config.notify_channels
        )
        
        self.notifications.append(notification)
        
        # 实际发送通知（这里只是模拟）
        self._send(notification)
        
        logger.info(f"Notification sent: {notification.id} type={notification_type}")
    
    def _get_type_text(self, notification_type: str) -> str:
        """获取类型描述"""
        mapping = {
            "approval_submitted": "通知",
            "approved": "通过",
            "rejected": "拒绝"
        }
        return mapping.get(notification_type, "")
    
    def _send(self, notification: Notification):
        """发送通知（实际实现可对接各种渠道）"""
        # 模拟发送
        notification.sent = True
        print(f"📧 通知发送: {notification.title} -> {notification.recipients}")
    
    def get_notifications(self, workflow_instance_id: str = None) -> List[Notification]:
        """获取通知列表"""
        if workflow_instance_id:
            return [n for n in self.notifications if workflow_instance_id in n.content]
        return self.notifications
