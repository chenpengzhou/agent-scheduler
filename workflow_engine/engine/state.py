"""
工作流状态管理
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from datetime import datetime

from workflow_engine.models.workflow import (
    WorkflowInstance, 
    StepInstance, 
    TaskInstance,
    WorkflowStatus,
    StepStatus,
    TaskStatus
)


class StateManager(ABC):
    """状态管理器抽象基类"""
    
    @abstractmethod
    def save_workflow(self, instance: WorkflowInstance) -> None:
        """保存工作流实例"""
        pass
    
    @abstractmethod
    def load_workflow(self, instance_id: str) -> Optional[WorkflowInstance]:
        """加载工作流实例"""
        pass
    
    @abstractmethod
    def list_workflows(self) -> List[WorkflowInstance]:
        """列出所有工作流实例"""
        pass
    
    @abstractmethod
    def save_step(self, instance: StepInstance) -> None:
        """保存步骤实例"""
        pass
    
    @abstractmethod
    def load_step(self, instance_id: str) -> Optional[StepInstance]:
        """加载步骤实例"""
        pass
    
    @abstractmethod
    def save_task(self, instance: TaskInstance) -> None:
        """保存任务实例"""
        pass
    
    @abstractmethod
    def load_task(self, instance_id: str) -> Optional[TaskInstance]:
        """加载任务实例"""
        pass


class InMemoryStateManager(StateManager):
    """内存状态管理器"""
    
    def __init__(self):
        self._workflows: Dict[str, WorkflowInstance] = {}
        self._steps: Dict[str, StepInstance] = {}
        self._tasks: Dict[str, TaskInstance] = {}
    
    def save_workflow(self, instance: WorkflowInstance) -> None:
        """保存工作流实例"""
        self._workflows[instance.id] = instance
    
    def load_workflow(self, instance_id: str) -> Optional[WorkflowInstance]:
        """加载工作流实例"""
        return self._workflows.get(instance_id)
    
    def list_workflows(self) -> List[WorkflowInstance]:
        """列出所有工作流实例"""
        return list(self._workflows.values())
    
    def delete_workflow(self, instance_id: str) -> None:
        """删除工作流实例"""
        self._workflows.pop(instance_id, None)
    
    def save_step(self, instance: StepInstance) -> None:
        """保存步骤实例"""
        self._steps[instance.id] = instance
    
    def load_step(self, instance_id: str) -> Optional[StepInstance]:
        """加载步骤实例"""
        return self._steps.get(instance_id)
    
    def get_steps_by_workflow(self, workflow_instance_id: str) -> List[StepInstance]:
        """获取工作流的所有步骤"""
        return [
            step for step in self._steps.values()
            if step.workflow_instance_id == workflow_instance_id
        ]
    
    def save_task(self, instance: TaskInstance) -> None:
        """保存任务实例"""
        self._tasks[instance.id] = instance
    
    def load_task(self, instance_id: str) -> Optional[TaskInstance]:
        """加载任务实例"""
        return self._tasks.get(instance_id)
    
    def get_tasks_by_step(self, step_instance_id: str) -> List[TaskInstance]:
        """获取步骤的所有任务"""
        return [
            task for task in self._tasks.values()
            if task.step_instance_id == step_instance_id
        ]
    
    def clear(self) -> None:
        """清空所有状态"""
        self._workflows.clear()
        self._steps.clear()
        self._tasks.clear()
