"""
数据库模型 - SQLAlchemy
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, JSON, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class WorkflowStatusDB(enum.Enum):
    """工作流状态"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"


class StepStatusDB(enum.Enum):
    """步骤状态"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class TaskStatusDB(enum.Enum):
    """任务状态"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ApprovalStatusDB(enum.Enum):
    """审批状态"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class WorkflowDefinitionDB(Base):
    """工作流定义表"""
    __tablename__ = "workflow_definitions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    version = Column(String(20), default="1.0")
    description = Column(Text)
    definition_json = Column(JSON, nullable=False)

    # 状态
    is_active = Column(Boolean, default=True)
    is_template = Column(Boolean, default=False)

    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100))
    tags = Column(JSON, default=list)

    # 关系
    instances = relationship("WorkflowInstanceDB", back_populates="definition")


class WorkflowInstanceDB(Base):
    """工作流实例表"""
    __tablename__ = "workflow_instances"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    definition_id = Column(String(36), ForeignKey("workflow_definitions.id"), nullable=False)
    definition_version = Column(String(20))

    # 状态
    status = Column(SQLEnum(WorkflowStatusDB), default=WorkflowStatusDB.PENDING)
    state_json = Column(JSON, default=dict)

    # 执行信息
    current_step_id = Column(String(100))
    completed_steps = Column(JSON, default=list)
    failed_steps = Column(JSON, default=list)
    error_message = Column(Text, default="")

    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # 上下文数据
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    variables = Column(JSON, default=dict)

    # 元数据
    triggered_by = Column(String(100))
    correlation_id = Column(String(36))
    parent_instance_id = Column(String(36))
    priority = Column(Integer, default=5)

    # 关系
    definition = relationship("WorkflowDefinitionDB", back_populates="instances")
    steps = relationship("StepInstanceDB", back_populates="workflow_instance", cascade="all, delete-orphan")
    tasks = relationship("TaskInstanceDB", back_populates="workflow_instance", cascade="all, delete-orphan")
    approvals = relationship("ApprovalInstanceDB", back_populates="workflow_instance", cascade="all, delete-orphan")


class StepInstanceDB(Base):
    """步骤实例表"""
    __tablename__ = "step_instances"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    definition_id = Column(String(100), nullable=False)
    workflow_instance_id = Column(String(36), ForeignKey("workflow_instances.id"), nullable=False)

    # 状态
    status = Column(SQLEnum(StepStatusDB), default=StepStatusDB.PENDING)

    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # 输入/输出
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)

    # 执行详情
    executor_id = Column(String(100))
    execution_logs = Column(JSON, default=list)

    # 重试信息
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    retry_history = Column(JSON, default=list)

    # 错误信息
    error_message = Column(Text)
    error_code = Column(String(50))
    error_details = Column(JSON, default=dict)

    # 关系
    workflow_instance = relationship("WorkflowInstanceDB", back_populates="steps")
    tasks = relationship("TaskInstanceDB", back_populates="step_instance", cascade="all, delete-orphan")


class TaskInstanceDB(Base):
    """任务实例表"""
    __tablename__ = "task_instances"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    definition_id = Column(String(100), nullable=False)
    step_instance_id = Column(String(36), ForeignKey("step_instances.id"), nullable=False)
    workflow_instance_id = Column(String(36), ForeignKey("workflow_instances.id"), nullable=False)

    # 状态
    status = Column(SQLEnum(TaskStatusDB), default=TaskStatusDB.PENDING)

    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # 执行信息
    executor_type = Column(String(20), default="agent")
    executor_id = Column(String(100))

    # 输入/输出
    input_params = Column(JSON, default=dict)
    output_params = Column(JSON, default=dict)
    result_data = Column(JSON, default=dict)
    result_status = Column(String(20))

    # 执行日志
    execution_logs = Column(JSON, default=list)

    # 重试信息
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # 错误信息
    error_message = Column(Text)
    error_code = Column(String(50))
    stack_trace = Column(Text)

    # 关系
    step_instance = relationship("StepInstanceDB", back_populates="tasks")
    workflow_instance = relationship("WorkflowInstanceDB", back_populates="tasks")


class ApprovalInstanceDB(Base):
    """审批实例表"""
    __tablename__ = "approval_instances"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    step_instance_id = Column(String(36), ForeignKey("step_instances.id"), nullable=True)
    workflow_instance_id = Column(String(36), ForeignKey("workflow_instances.id"), nullable=False)

    # 审批信息
    approval_type = Column(String(50))  # manual, auto
    status = Column(SQLEnum(ApprovalStatusDB), default=ApprovalStatusDB.PENDING)
    approver = Column(String(100))

    # 审批内容
    title = Column(String(255))
    content = Column(JSON, default=dict)

    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime)
    approved_by = Column(String(100))

    # 审批意见
    comment = Column(Text)

    # 关系
    workflow_instance = relationship("WorkflowInstanceDB", back_populates="approvals")


class LogEntryDB(Base):
    """日志表"""
    __tablename__ = "log_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_instance_id = Column(String(36), ForeignKey("workflow_instances.id"), nullable=True)
    step_instance_id = Column(String(36), ForeignKey("step_instances.id"), nullable=True)
    task_instance_id = Column(String(36), ForeignKey("task_instances.id"), nullable=True)

    # 日志内容
    level = Column(String(20))  # DEBUG, INFO, WARNING, ERROR
    message = Column(Text)
    extra = Column(JSON, default=dict)

    # 时间
    created_at = Column(DateTime, default=datetime.utcnow)
