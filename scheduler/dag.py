#!/usr/bin/env python3
"""
DAG 工作流引擎 - Agent 调度器
"""
from typing import List, Dict, Set, Optional
from collections import defaultdict, deque
import sys
sys.path.insert(0, "/home/robin/.openclaw/workspace-dev/scheduler")
from task_queue import queue
from models import Task, TaskStatus, Workflow


class DAGEngine:
    """DAG 工作流引擎"""
    
    def __init__(self):
        self.queue = queue
    
    def topological_sort(self, dag: Dict[str, List[str]]) -> List[str]:
        """
        拓扑排序 - 返回任务执行顺序
        dag: {task_id: [dependent_task_ids]}
        返回: 按依赖顺序排列的任务ID列表
        """
        # 构建入度表
        in_degree = defaultdict(int)
        all_tasks = set(dag.keys())
        
        for task_id, deps in dag.items():
            if task_id not in in_degree:
                in_degree[task_id] = 0
            for dep in deps:
                all_tasks.add(dep)
                in_degree[task_id] += 1
        
        # BFS
        queue = deque([task for task in all_tasks if in_degree[task] == 0])
        result = []
        
        while queue:
            task_id = queue.popleft()
            result.append(task_id)
            
            # 更新依赖该任务的任务
            for other_task, deps in dag.items():
                if task_id in deps:
                    in_degree[other_task] -= 1
                    if in_degree[other_task] == 0:
                        queue.append(other_task)
        
        # 检测循环依赖
        if len(result) != len(all_tasks):
            raise ValueError("DAG 存在循环依赖")
        
        return result
    
    def get_ready_tasks(self, workflow: Workflow) -> List[str]:
        """
        获取就绪的任务（所有依赖都已完成）
        """
        ready = []
        completed = set(workflow.completed_tasks)
        
        for task_id, deps in workflow.dag.items():
            if task_id in completed:
                continue
            # 检查所有依赖是否都已完成
            if all(dep in completed for dep in deps):
                ready.append(task_id)
        
        return ready
    
    def can_execute(self, task_id: str, workflow: Workflow) -> bool:
        """检查任务是否可以执行"""
        if task_id in workflow.completed_tasks:
            return False
        
        deps = workflow.dag.get(task_id, [])
        return all(dep in workflow.completed_tasks for dep in deps)
    
    def execute_task(self, workflow_id: str, task_id: str) -> bool:
        """
        执行任务
        1. 更新任务状态为 running
        2. 分发给 Agent
        3. 等待 Agent 返回结果
        """
        workflow = self.queue.get_workflow(workflow_id)
        if not workflow:
            return False
        
        task = self.queue.get_task(task_id)
        if not task:
            return False
        
        # 检查依赖
        if not self.can_execute(task_id, workflow):
            return False
        
        # 更新任务状态
        task.status = TaskStatus.RUNNING
        self.queue.update_task(task)
        
        # 移动到运行队列
        self.queue.move_to_running(task_id)
        
        return True
    
    def complete_task(self, workflow_id: str, task_id: str, result: dict = None) -> bool:
        """
        完成任务
        1. 更新任务状态为 completed
        2. 更新工作流进度
        3. 触发下游任务
        """
        workflow = self.queue.get_workflow(workflow_id)
        if not workflow:
            return False
        
        # 更新任务状态
        task = self.queue.get_task(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.result = result
            self.queue.update_task(task)
            self.queue.move_to_completed(task_id)
        
        # 更新工作流
        workflow.completed_tasks.append(task_id)
        workflow.progress = len(workflow.completed_tasks) / len(workflow.dag)
        
        if workflow.progress >= 1.0:
            workflow.status = TaskStatus.COMPLETED
        
        wf_data = workflow.model_dump()
        wf_data["created_at"] = workflow.created_at.isoformat()
        wf_data["updated_at"] = workflow.updated_at.isoformat()
        self.queue.redis.hset(f"scheduler:workflows:{workflow_id}", mapping=wf_data)
        
        # 触发下游任务
        self._trigger_downstream(workflow_id, task_id)
        
        return True
    
    def fail_task(self, workflow_id: str, task_id: str, error: str) -> bool:
        """任务失败"""
        workflow = self.queue.get_workflow(workflow_id)
        if not workflow:
            return False
        
        task = self.queue.get_task(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.error = error
            self.queue.update_task(task)
            self.queue.move_to_failed(task_id)
        
        # 工作流失败
        workflow.status = TaskStatus.FAILED
        wf_data = workflow.model_dump()
        wf_data["created_at"] = workflow.created_at.isoformat()
        wf_data["updated_at"] = workflow.updated_at.isoformat()
        self.queue.redis.hset(f"scheduler:workflows:{workflow_id}", mapping=wf_data)
        
        return True
    
    def _trigger_downstream(self, workflow_id: str, completed_task_id: str):
        """触发下游任务"""
        workflow = self.queue.get_workflow(workflow_id)
        if not workflow:
            return
        
        ready_tasks = self.get_ready_tasks(workflow)
        for task_id in ready_tasks:
            self.execute_task(workflow_id, task_id)
    
    def check_circular_dependency(self, dag: Dict[str, List[str]]) -> bool:
        """检查循环依赖"""
        try:
            self.topological_sort(dag)
            return False
        except ValueError:
            return True


# 全局实例
dag_engine = DAGEngine()
