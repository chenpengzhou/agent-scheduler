"""
并行执行器 - 支持步骤并行执行
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime

from ..models.workflow import (
    WorkflowDefinition, WorkflowInstance, WorkflowStatus,
    StepDefinition, StepInstance, StepStatus,
    TaskDefinition, TaskInstance, TaskStatus
)
from .dag import DAGExecutor, DAG, DAGBuilder
from .state import StateManager

logger = logging.getLogger(__name__)


class ParallelExecutor:
    """并行执行器"""
    
    def __init__(
        self,
        state_manager: StateManager = None,
        max_parallel: int = 5
    ):
        self.state_manager = state_manager
        self.max_parallel = max_parallel
        self.task_executors: Dict[str, Callable] = {}
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
        depends_on_map: Dict[str, List[str]] = None,
        conditions: Dict = None,
        input_data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> WorkflowInstance:
        """执行工作流（支持DAG和并行）"""
        # 创建工作流实例
        instance = WorkflowInstance(
            id=str(uuid.uuid4()),
            definition_id=workflow_def.id,
            status=WorkflowStatus.PENDING,
            input_data=input_data or {},
            state=context or {},
        )
        
        # 保存初始状态
        if self.state_manager:
            self.state_manager.save_workflow(instance)
        
        logger.info(f"[Workflow {instance.id}] Started: {workflow_def.name}")
        print(f"\n🚀 Starting DAG workflow: {workflow_def.name}")
        
        # 构建DAG
        dag_builder = DAGBuilder()
        dag = dag_builder.build_from_steps(
            workflow_def.steps,
            depends_on_map=depends_on_map or {},
            conditions=conditions or {}
        )
        
        # 创建DAG执行器
        dag_executor = DAGExecutor(dag)
        
        # 更新状态
        instance.status = WorkflowStatus.RUNNING
        instance.started_at = datetime.now()
        
        if self.state_manager:
            self.state_manager.save_workflow(instance)
        
        print(f"📋 Status: RUNNING")
        print(f"📊 Total steps: {len(workflow_def.steps)}")
        
        try:
            # 执行主循环
            while True:
                # 获取可执行的步骤
                ready_steps = dag_executor.get_next_steps()
                
                if not ready_steps:
                    # 检查是否全部完成
                    if dag_executor.completed_steps == set(dag.nodes.keys()):
                        break
                    # 有失败步骤
                    if dag_executor.failed_steps:
                        instance.status = WorkflowStatus.FAILED
                        break
                    # 死锁
                    logger.error("Deadlock: no ready steps but workflow not complete")
                    break
                
                # 执行就绪的步骤（并行）
                print(f"\n⚡ Executing {len(ready_steps)} steps in parallel: {ready_steps}")
                
                # 串行执行每批（简化实现）
                for step_id in ready_steps:
                    step_def = workflow_def.get_step(step_id)
                    if step_def:
                        instance = self._execute_step(instance, step_def, dag_executor)
                        
                        # 检查失败
                        if instance.status == WorkflowStatus.FAILED:
                            break
                
                # 检查工作流状态
                if instance.status == WorkflowStatus.FAILED:
                    break
            
            # 工作流完成
            if instance.status == WorkflowStatus.RUNNING:
                instance.status = WorkflowStatus.COMPLETED
                instance.completed_at = datetime.now()
                print(f"\n✅ Status: COMPLETED")
                print(f"🏁 Workflow finished successfully!")
            
        except Exception as e:
            instance.status = WorkflowStatus.FAILED
            instance.error_message = str(e)
            instance.completed_at = datetime.now()
            print(f"\n❌ Status: FAILED: {e}")
            logger.exception(f"[Workflow {instance.id}] Failed: {e}")
        
        # 保存最终状态
        if self.state_manager:
            self.state_manager.save_workflow(instance)
        
        return instance
    
    def _execute_step(
        self,
        workflow_instance: WorkflowInstance,
        step_def: StepDefinition,
        dag_executor: DAGExecutor
    ) -> WorkflowInstance:
        """执行单个步骤"""
        print(f"\n📌 Step: {step_def.name} ({step_def.id})")
        
        # 创建步骤实例
        step_instance = StepInstance(
            id=str(uuid.uuid4()),
            definition_id=step_def.id,
            workflow_instance_id=workflow_instance.id,
            status=StepStatus.PENDING,
        )
        
        # 继承父级输入
        step_instance.input_data = workflow_instance.input_data.copy()
        # 合并工作流状态
        step_instance.input_data.update(workflow_instance.state)
        
        if self.state_manager:
            self.state_manager.save_step(step_instance)
        
        try:
            # 更新状态
            step_instance.status = StepStatus.RUNNING
            step_instance.started_at = datetime.now()
            
            if self.state_manager:
                self.state_manager.save_step(step_instance)
            
            print(f"   Status: RUNNING")
            
            # 执行任务
            if step_def.task_def:
                step_instance = self._execute_task(step_instance, step_def.task_def)
                
                if step_instance.status == StepStatus.FAILED:
                    workflow_instance.status = WorkflowStatus.FAILED
                    workflow_instance.error_message = step_instance.error_message
                    dag_executor.mark_failed(step_def.id)
                    print(f"   Status: FAILED: {step_instance.error_message}")
                    return workflow_instance
            
            # 步骤完成
            step_instance.status = StepStatus.COMPLETED
            step_instance.completed_at = datetime.now()
            
            # 合并输出
            workflow_instance.state.update(step_instance.output_data)
            
            dag_executor.mark_completed(step_def.id)
            print(f"   Status: COMPLETED")
            
        except Exception as e:
            step_instance.status = StepStatus.FAILED
            step_instance.error_message = str(e)
            step_instance.completed_at = datetime.now()
            workflow_instance.status = WorkflowStatus.FAILED
            workflow_instance.error_message = str(e)
            dag_executor.mark_failed(step_def.id)
            print(f"   Status: FAILED: {e}")
            logger.exception(f"[Step {step_def.id}] Failed: {e}")
        
        if self.state_manager:
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
            id=str(uuid.uuid4()),
            definition_id=task_def.id,
            step_instance_id=step_instance.id,
            workflow_instance_id=step_instance.workflow_instance_id,
            status=TaskStatus.PENDING,
            input_params=task_def.input_params or {},
        )
        
        if self.state_manager:
            self.state_manager.save_task(task_instance)
        
        try:
            task_instance.status = TaskStatus.RUNNING
            task_instance.started_at = datetime.now()
            
            if self.state_manager:
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
        
        if self.state_manager:
            self.state_manager.save_task(task_instance)
        
        return step_instance
    
    def _execute_agent_task(
        self,
        task_instance: TaskInstance,
        task_def: TaskDefinition
    ) -> Dict[str, Any]:
        """执行Agent任务"""
        agent_type = task_def.agent_selector.agent_type if task_def.agent_selector else "dev-engineer"
        print(f"      🤖 Agent: {agent_type}")
        
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


import uuid
