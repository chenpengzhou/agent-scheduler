"""
工作流服务层
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import json

from api.models.db import (
    WorkflowDefinitionDB, WorkflowInstanceDB, StepInstanceDB,
    TaskInstanceDB, ApprovalInstanceDB, LogEntryDB,
    WorkflowStatusDB, StepStatusDB, TaskStatusDB, ApprovalStatusDB
)
from api.services.logging_service import get_logger

logger = get_logger("workflow_service")


class WorkflowService:
    """工作流服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ===== 工作流定义管理 =====
    
    def create_definition(self, name: str, definition_json: Dict, 
                          description: str = "", version: str = "1.0",
                          tags: List[str] = None, created_by: str = "system") -> WorkflowDefinitionDB:
        """创建工作流定义"""
        definition = WorkflowDefinitionDB(
            id=str(uuid.uuid4()),
            name=name,
            version=version,
            description=description,
            definition_json=definition_json,
            tags=tags or [],
            created_by=created_by,
            is_active=True,
            is_template=False
        )
        self.db.add(definition)
        self.db.commit()
        self.db.refresh(definition)
        
        logger.info("workflow_definition_created", definition_id=definition.id, name=name)
        return definition
    
    def get_definition(self, def_id: str) -> Optional[WorkflowDefinitionDB]:
        """获取工作流定义"""
        return self.db.query(WorkflowDefinitionDB).filter(
            WorkflowDefinitionDB.id == def_id
        ).first()
    
    def list_definitions(self, name: str = None, tag: str = None,
                        offset: int = 0, limit: int = 20) -> List[WorkflowDefinitionDB]:
        """列取工作流定义"""
        query = self.db.query(WorkflowDefinitionDB)
        
        if name:
            query = query.filter(WorkflowDefinitionDB.name.like(f"%{name}%"))
        if tag:
            query = query.filter(WorkflowDefinitionDB.tags.contains([tag]))
        
        return query.offset(offset).limit(limit).all()
    
    def update_definition(self, def_id: str, **kwargs) -> Optional[WorkflowDefinitionDB]:
        """更新工作流定义"""
        definition = self.get_definition(def_id)
        if not definition:
            return None
        
        for key, value in kwargs.items():
            if hasattr(definition, key):
                setattr(definition, key, value)
        
        definition.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(definition)
        
        logger.info("workflow_definition_updated", definition_id=def_id)
        return definition
    
    def delete_definition(self, def_id: str) -> bool:
        """删除工作流定义"""
        definition = self.get_definition(def_id)
        if not definition:
            return False
        
        self.db.delete(definition)
        self.db.commit()
        
        logger.info("workflow_definition_deleted", definition_id=def_id)
        return True
    
    # ===== 工作流实例管理 =====
    
    def start_instance(self, definition_id: str, input_data: Dict = None,
                       triggered_by: str = "api", correlation_id: str = None) -> Optional[WorkflowInstanceDB]:
        """启动工作流实例"""
        definition = self.get_definition(definition_id)
        if not definition:
            return None
        
        instance = WorkflowInstanceDB(
            id=str(uuid.uuid4()),
            definition_id=definition_id,
            definition_version=definition.version,
            status=WorkflowStatusDB.PENDING,
            input_data=input_data or {},
            state_json={},
            completed_steps=[],
            failed_steps=[],
            triggered_by=triggered_by,
            correlation_id=correlation_id,
            priority=5
        )
        self.db.add(instance)
        
        # 创建步骤实例
        def_json = definition.definition_json
        steps = def_json.get("steps", [])
        
        for step_def in steps:
            step_instance = StepInstanceDB(
                id=str(uuid.uuid4()),
                definition_id=step_def.get("id"),
                workflow_instance_id=instance.id,
                status=StepStatusDB.PENDING,
                input_data={},
                output_data={}
            )
            self.db.add(step_instance)
        
        self.db.commit()
        self.db.refresh(instance)
        
        # 更新当前步骤为第一个步骤
        if steps:
            instance.current_step_id = steps[0].get("id")
            instance.status = WorkflowStatusDB.RUNNING
            instance.started_at = datetime.utcnow()
            self.db.commit()
        
        logger.info("workflow_instance_started", instance_id=instance.id, definition_id=definition_id)
        return instance
    
    def get_instance(self, instance_id: str) -> Optional[WorkflowInstanceDB]:
        """获取工作流实例"""
        return self.db.query(WorkflowInstanceDB).filter(
            WorkflowInstanceDB.id == instance_id
        ).first()
    
    def list_instances(self, definition_id: str = None, status: WorkflowStatusDB = None,
                      start_time_from: datetime = None, start_time_to: datetime = None,
                      offset: int = 0, limit: int = 20) -> List[WorkflowInstanceDB]:
        """列取工作流实例"""
        query = self.db.query(WorkflowInstanceDB)
        
        if definition_id:
            query = query.filter(WorkflowInstanceDB.definition_id == definition_id)
        if status:
            query = query.filter(WorkflowInstanceDB.status == status)
        if start_time_from:
            query = query.filter(WorkflowInstanceDB.created_at >= start_time_from)
        if start_time_to:
            query = query.filter(WorkflowInstanceDB.created_at <= start_time_to)
        
        return query.order_by(WorkflowInstanceDB.created_at.desc()).offset(offset).limit(limit).all()
    
    def pause_instance(self, instance_id: str) -> Optional[WorkflowInstanceDB]:
        """暂停工作流实例"""
        instance = self.get_instance(instance_id)
        if not instance or instance.status != WorkflowStatusDB.RUNNING:
            return None
        
        instance.status = WorkflowStatusDB.PAUSED
        self.db.commit()
        
        logger.info("workflow_instance_paused", instance_id=instance_id)
        return instance
    
    def resume_instance(self, instance_id: str) -> Optional[WorkflowInstanceDB]:
        """恢复工作流实例"""
        instance = self.get_instance(instance_id)
        if not instance or instance.status != WorkflowStatusDB.PAUSED:
            return None
        
        instance.status = WorkflowStatusDB.RUNNING
        self.db.commit()
        
        logger.info("workflow_instance_resumed", instance_id=instance_id)
        return instance
    
    def cancel_instance(self, instance_id: str, reason: str = "") -> Optional[WorkflowInstanceDB]:
        """取消工作流实例"""
        instance = self.get_instance(instance_id)
        if not instance or instance.status not in [WorkflowStatusDB.RUNNING, WorkflowStatusDB.PAUSED]:
            return None
        
        instance.status = WorkflowStatusDB.CANCELLED
        instance.completed_at = datetime.utcnow()
        if reason:
            instance.error_message = reason
        self.db.commit()
        
        logger.info("workflow_instance_cancelled", instance_id=instance_id, reason=reason)
        return instance
    
    def retry_instance(self, instance_id: str) -> Optional[WorkflowInstanceDB]:
        """重试工作流实例"""
        instance = self.get_instance(instance_id)
        if not instance or instance.status != WorkflowStatusDB.FAILED:
            return None
        
        instance.status = WorkflowStatusDB.PENDING
        instance.completed_steps = []
        instance.failed_steps = []
        instance.started_at = None
        instance.completed_at = None
        instance.error_message = ""
        
        # 重置所有步骤状态
        steps = self.db.query(StepInstanceDB).filter(
            StepInstanceDB.workflow_instance_id == instance_id
        ).all()
        for step in steps:
            step.status = StepStatusDB.PENDING
            step.error_message = ""
        
        self.db.commit()
        
        logger.info("workflow_instance_retried", instance_id=instance_id)
        return instance
    
    # ===== 步骤管理 =====
    
    def get_steps(self, instance_id: str) -> List[StepInstanceDB]:
        """获取工作流步骤列表"""
        return self.db.query(StepInstanceDB).filter(
            StepInstanceDB.workflow_instance_id == instance_id
        ).order_by(StepInstanceDB.created_at).all()
    
    def get_step(self, instance_id: str, step_id: str) -> Optional[StepInstanceDB]:
        """获取工作流步骤详情"""
        return self.db.query(StepInstanceDB).filter(
            StepInstanceDB.workflow_instance_id == instance_id,
            StepInstanceDB.id == step_id
        ).first()
    
    # ===== 任务管理 =====
    
    def get_tasks(self, instance_id: str) -> List[TaskInstanceDB]:
        """获取工作流任务列表"""
        return self.db.query(TaskInstanceDB).filter(
            TaskInstanceDB.workflow_instance_id == instance_id
        ).order_by(TaskInstanceDB.created_at).all()
    
    def get_task(self, instance_id: str, task_id: str) -> Optional[TaskInstanceDB]:
        """获取工作流任务详情"""
        return self.db.query(TaskInstanceDB).filter(
            TaskInstanceDB.workflow_instance_id == instance_id,
            TaskInstanceDB.id == task_id
        ).first()
    
    # ===== 审批管理 =====
    
    def get_approvals(self, instance_id: str) -> List[ApprovalInstanceDB]:
        """获取工作流审批列表"""
        return self.db.query(ApprovalInstanceDB).filter(
            ApprovalInstanceDB.workflow_instance_id == instance_id
        ).order_by(ApprovalInstanceDB.created_at).all()
    
    def approve(self, instance_id: str, approval_id: str, approved_by: str, comment: str = "") -> Optional[ApprovalInstanceDB]:
        """审批通过"""
        approval = self.db.query(ApprovalInstanceDB).filter(
            ApprovalInstanceDB.id == approval_id,
            ApprovalInstanceDB.workflow_instance_id == instance_id
        ).first()
        
        if not approval:
            return None
        
        approval.status = ApprovalStatusDB.APPROVED
        approval.approved_by = approved_by
        approval.approved_at = datetime.utcnow()
        approval.comment = comment
        self.db.commit()
        
        logger.info("approval_approved", instance_id=instance_id, approval_id=approval_id)
        return approval
    
    def reject(self, instance_id: str, approval_id: str, approved_by: str, comment: str = "") -> Optional[ApprovalInstanceDB]:
        """审批拒绝"""
        approval = self.db.query(ApprovalInstanceDB).filter(
            ApprovalInstanceDB.id == approval_id,
            ApprovalInstanceDB.workflow_instance_id == instance_id
        ).first()
        
        if not approval:
            return None
        
        approval.status = ApprovalStatusDB.REJECTED
        approval.approved_by = approved_by
        approval.approved_at = datetime.utcnow()
        approval.comment = comment
        self.db.commit()
        
        logger.info("approval_rejected", instance_id=instance_id, approval_id=approval_id)
        return approval
    
    # ===== 日志管理 =====
    
    def add_log(self, workflow_instance_id: str, level: str, message: str,
                step_instance_id: str = None, task_instance_id: str = None,
                extra: Dict = None) -> LogEntryDB:
        """添加日志"""
        log_entry = LogEntryDB(
            workflow_instance_id=workflow_instance_id,
            step_instance_id=step_instance_id,
            task_instance_id=task_instance_id,
            level=level,
            message=message,
            extra=extra or {}
        )
        self.db.add(log_entry)
        self.db.commit()
        return log_entry
    
    def get_logs(self, instance_id: str, level: str = None, limit: int = 100) -> List[LogEntryDB]:
        """获取工作流日志"""
        query = self.db.query(LogEntryDB).filter(
            LogEntryDB.workflow_instance_id == instance_id
        )
        
        if level:
            query = query.filter(LogEntryDB.level == level)
        
        return query.order_by(LogEntryDB.created_at.desc()).limit(limit).all()
    
    # ===== 指标 =====
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        total_definitions = self.db.query(WorkflowDefinitionDB).count()
        total_instances = self.db.query(WorkflowInstanceDB).count()
        
        status_counts = {}
        for status in WorkflowStatusDB:
            count = self.db.query(WorkflowInstanceDB).filter(
                WorkflowInstanceDB.status == status
            ).count()
            status_counts[status.value] = count
        
        return {
            "total_definitions": total_definitions,
            "total_instances": total_instances,
            "status_counts": status_counts
        }
