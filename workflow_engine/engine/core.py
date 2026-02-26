"""
工作流引擎核心
"""
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import logging

from ..models.workflow import (
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowStatus,
    StepDefinition,
    StepInstance,
    StepStatus,
    TaskDefinition,
    TaskInstance,
    TaskStatus,
)
from .state import StateManager, InMemoryStateManager


logger = logging.getLogger(__name__)


class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self, state_manager: Optional[StateManager] = None):
        self.state_manager = state_manager or InMemoryStateManager()
        self.task_executors: Dict[str, Callable] = {}
        
        # 注册默认的执行器
        self._register_default_executors()
    
    def _register_default_executors(self):
        """注册默认执行器"""
        self.task_executors["agent"] = self._execute_agent_task
        self.task_executors["script"] = self._execute_script_task
        self.task_executors["function"] = self._execute_function_task
    
    def register_executor(self, executor_type: str, executor: Callable):
        """注册任务执行器"""
        self.task_executors[executor_type] = executor
    
    def execute(
        self, 
        workflow_def: WorkflowDefinition, 
        input_data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> WorkflowInstance:
        """执行工作流"""
        # 创建工作流实例
        instance = WorkflowInstance(
            id="",
            definition_id=workflow_def.id,
            status=WorkflowStatus.PENDING,
            input_data=input_data or {},
            state=context or {},
        )
        
        # 保存初始状态
        self.state_manager.save_workflow(instance)
        
        logger.info(f"[Workflow {instance.id}] Started: {workflow_def.name}")
        print(f"🚀 Starting workflow: {workflow_def.name}")
        print(f"📋 Status: {instance.status.value} → RUNNING")
        
        # 更新状态为运行中
        instance.status = WorkflowStatus.RUNNING
        instance.started_at = datetime.now()
        self.state_manager.save_workflow(instance)
        
        try:
            # 获取第一个步骤
            current_step = workflow_def.get_first_step()
            
            while current_step:
                # 执行步骤
                instance = self._execute_step(instance, current_step)
                
                # 检查工作流状态
                if instance.status == WorkflowStatus.FAILED:
                    break
                
                # 获取下一步
                current_step = self._get_next_step(workflow_def, current_step, instance)
            
            # 工作流完成
            if instance.status == WorkflowStatus.RUNNING:
                instance.status = WorkflowStatus.COMPLETED
                instance.completed_at = datetime.now()
                print(f"✅ Status: COMPLETED")
                print(f"🏁 Workflow finished successfully!")
            
        except Exception as e:
            instance.status = WorkflowStatus.FAILED
            instance.error_message = str(e)
            instance.completed_at = datetime.now()
            print(f"❌ Status: FAILED")
            print(f"💥 Error: {e}")
            logger.exception(f"[Workflow {instance.id}] Failed: {e}")
        
        # 保存最终状态
        self.state_manager.save_workflow(instance)
        
        return instance
    
    def _execute_step(
        self, 
        workflow_instance: WorkflowInstance,
        step_def: StepDefinition
    ) -> WorkflowInstance:
        """执行单个步骤"""
        print(f"\n📌 Step: {step_def.name} ({step_def.id})")
        
        # 创建步骤实例
        step_instance = StepInstance(
            id="",
            definition_id=step_def.id,
            workflow_instance_id=workflow_instance.id,
            status=StepStatus.PENDING,
        )
        
        # 继承父级输入
        step_instance.input_data = workflow_instance.input_data.copy()
        
        self.state_manager.save_step(step_instance)
        
        try:
            # 更新状态为运行中
            step_instance.status = StepStatus.RUNNING
            step_instance.started_at = datetime.now()
            self.state_manager.save_step(step_instance)
            
            print(f"   Status: RUNNING")
            
            # 执行任务（如果有）
            if step_def.task_def:
                step_instance = self._execute_task(step_instance, step_def.task_def)
                
                # 更新工作流状态
                if step_instance.status == StepStatus.FAILED:
                    workflow_instance.status = WorkflowStatus.FAILED
                    workflow_instance.failed_steps.append(step_def.id)
                    workflow_instance.error_message = step_instance.error_message
            
            # 步骤完成
            if step_instance.status != StepStatus.FAILED:
                step_instance.status = StepStatus.COMPLETED
                step_instance.completed_at = datetime.now()
                
                # 合并输出到工作流状态
                workflow_instance.state.update(step_instance.output_data)
                workflow_instance.completed_steps.append(step_def.id)
                
                print(f"   Status: COMPLETED")
            
        except Exception as e:
            step_instance.status = StepStatus.FAILED
            step_instance.error_message = str(e)
            step_instance.completed_at = datetime.now()
            workflow_instance.status = WorkflowStatus.FAILED
            workflow_instance.error_message = str(e)
            print(f"   Status: FAILED: {e}")
            logger.exception(f"[Step {step_def.id}] Failed: {e}")
        
        self.state_manager.save_step(step_instance)
        self.state_manager.save_workflow(workflow_instance)
        
        return workflow_instance
    
    def _execute_task(
        self, 
        step_instance: StepInstance, 
        task_def: TaskDefinition
    ) -> StepInstance:
        """执行任务"""
        print(f"   📝 Task: {task_def.name}")
        
        # 创建任务实例
        task_instance = TaskInstance(
            id="",
            definition_id=task_def.id,
            step_instance_id=step_instance.id,
            workflow_instance_id=step_instance.workflow_instance_id,
            status=TaskStatus.PENDING,
            input_params=task_def.input_params or {},
        )
        
        self.state_manager.save_task(task_instance)
        
        try:
            # 更新状态为运行中
            task_instance.status = TaskStatus.RUNNING
            task_instance.started_at = datetime.now()
            self.state_manager.save_task(task_instance)
            
            # 获取执行器
            executor = self.task_executors.get(task_def.executor_type)
            if not executor:
                raise ValueError(f"Unknown executor type: {task_def.executor_type}")
            
            # 执行任务
            result = executor(task_instance, task_def)
            
            # 任务完成
            task_instance.status = TaskStatus.COMPLETED
            task_instance.completed_at = datetime.now()
            task_instance.output_result = result or {}
            
            # 合并结果到步骤输出
            step_instance.output_data.update(task_instance.output_result)
            
            print(f"      ✅ Task completed")
            
        except Exception as e:
            task_instance.status = TaskStatus.FAILED
            task_instance.error_message = str(e)
            task_instance.completed_at = datetime.now()
            step_instance.status = StepStatus.FAILED
            step_instance.error_message = str(e)
            print(f"      ❌ Task failed: {e}")
            logger.exception(f"[Task {task_def.id}] Failed: {e}")
        
        self.state_manager.save_task(task_instance)
        
        return step_instance
    
    def _execute_agent_task(
        self, 
        task_instance: TaskInstance, 
        task_def: TaskDefinition
    ) -> Dict[str, Any]:
        """执行Agent任务"""
        # 模拟Agent执行
        agent_type = task_def.agent_selector.agent_type if task_def.agent_selector else "dev-engineer"
        print(f"      🤖 Agent: {agent_type}")
        
        # 返回模拟结果
        return {
            "agent_type": agent_type,
            "result": f"Task {task_def.name} executed by {agent_type}",
            "timestamp": datetime.now().isoformat(),
        }
    
    def _execute_script_task(
        self, 
        task_instance: TaskInstance, 
        task_def: TaskDefinition
    ) -> Dict[str, Any]:
        """执行脚本任务"""
        print(f"      📜 Script: {task_def.name}")
        return {"result": "Script executed"}
    
    def _execute_function_task(
        self, 
        task_instance: TaskInstance, 
        task_def: TaskDefinition
    ) -> Dict[str, Any]:
        """执行函数任务"""
        print(f"      🔧 Function: {task_def.name}")
        return {"result": "Function executed"}
    
    def _get_next_step(
        self, 
        workflow_def: WorkflowDefinition,
        current_step: StepDefinition,
        workflow_instance: WorkflowInstance
    ) -> Optional[StepDefinition]:
        """获取下一步骤"""
        if not current_step.next_steps:
            return None
        
        next_step_id = current_step.next_steps[0]
        return workflow_def.get_step(next_step_id)
    
    def get_status(self, instance_id: str) -> Optional[WorkflowInstance]:
        """获取工作流状态"""
        return self.state_manager.load_workflow(instance_id)
    
    def list_workflows(self) -> List[WorkflowInstance]:
        """列出所有工作流"""
        return self.state_manager.list_workflows()
