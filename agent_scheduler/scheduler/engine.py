"""
调度引擎 - 任务调度核心
"""
from typing import List, Dict, Set, Optional, Any, Callable
from collections import defaultdict, deque
import logging
import time
import threading
from datetime import datetime

from ..models.task import Task, TaskStatus, TaskPriority

logger = logging.getLogger(__name__)


class DAGScheduler:
    """基于DAG的调度器"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.running_tasks: Set[str] = set()
    
    def add_task(self, task: Task):
        """添加任务"""
        self.tasks[task.id] = task
        logger.info(f"Task added: {task.id} ({task.name})")
    
    def get_ready_tasks(self) -> List[Task]:
        """获取就绪的任务（所有依赖都已完成）"""
        ready = []
        
        for task_id, task in self.tasks.items():
            # 跳过已完成和失败的任务
            if task_id in self.completed_tasks or task_id in self.failed_tasks:
                continue
            
            # 跳过正在运行的任务
            if task_id in self.running_tasks:
                continue
            
            # 检查依赖是否都完成
            if self._is_ready(task):
                ready.append(task)
        
        # 按优先级排序
        ready.sort(key=lambda t: t.priority.value)
        return ready
    
    def _is_ready(self, task: Task) -> bool:
        """检查任务是否就绪"""
        if not task.depends_on:
            return True
        
        # 所有依赖任务都必须完成
        for dep_id in task.depends_on:
            if dep_id not in self.completed_tasks:
                return False
        return True
    
    def mark_running(self, task_id: str):
        """标记任务开始执行"""
        self.running_tasks.add(task_id)
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.RUNNING
            self.tasks[task_id].started_at = datetime.now()
    
    def mark_completed(self, task_id: str, output: Dict[str, Any] = None):
        """标记任务完成"""
        self.completed_tasks.add(task_id)
        self.running_tasks.discard(task_id)
        
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.COMPLETED
            self.tasks[task_id].completed_at = datetime.now()
            if output:
                self.tasks[task_id].output_data = output
    
    def mark_failed(self, task_id: str, error: str = ""):
        """标记任务失败"""
        self.failed_tasks.add(task_id)
        self.running_tasks.discard(task_id)
        
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.FAILED
            self.tasks[task_id].error_message = error
            self.tasks[task_id].completed_at = datetime.now()
    
    def get_execution_order(self) -> List[List[str]]:
        """获取执行顺序（拓扑排序后的批次）"""
        # 计算入度
        in_degree = defaultdict(int)
        for task_id, task in self.tasks.items():
            if not task.depends_on:
                in_degree[task_id] = 0
            else:
                in_degree[task_id] = len(task.depends_on)
        
        # 按优先级初始化 - 处理int或枚举
        def get_priority_value(t):
            if hasattr(t, 'value'):
                return t.value
            return t
        
        queue = deque([t for t, d in in_degree.items() if d == 0])
        queue = deque(sorted(queue, key=lambda x: get_priority_value(self.tasks[x].priority)))
        
        result = []
        
        while queue:
            batch = []
            next_queue = deque()
            
            # 取出当前批次
            while queue:
                task_id = queue.popleft()
                batch.append(task_id)
                
                # 更新依赖者的入度
                for other_id, other_task in self.tasks.items():
                    if task_id in other_task.depends_on:
                        in_degree[other_id] -= 1
                        if in_degree[other_id] == 0:
                            next_queue.append(other_id)
            
            if batch:
                result.append(batch)
            
            # 按优先级排序下一批次
            next_queue = deque(sorted(next_queue, key=lambda x: get_priority_value(self.tasks[x].priority)))
            queue = next_queue
        
        return result
    
    def has_cycle(self) -> bool:
        """检测环"""
        try:
            self.get_execution_order()
            return False
        except Exception:
            return True


class SchedulerEngine:
    """调度引擎"""
    
    def __init__(self):
        self.dag_scheduler = DAGScheduler()
    
    def submit_task(self, task: Task) -> str:
        """提交任务"""
        self.dag_scheduler.add_task(task)
        return task.id
    
    def submit_tasks(self, tasks: List[Task]) -> List[str]:
        """批量提交任务"""
        return [self.submit_task(task) for task in tasks]
    
    def get_ready_tasks(self) -> List[Task]:
        """获取就绪任务"""
        return self.dag_scheduler.get_ready_tasks()
    
    def start_task(self, task_id: str) -> bool:
        """开始执行任务"""
        ready_tasks = self.dag_scheduler.get_ready_tasks()
        
        for task in ready_tasks:
            if task.id == task_id:
                self.dag_scheduler.mark_running(task_id)
                return True
        
        return False
    
    def complete_task(self, task_id: str, output: Dict[str, Any] = None):
        """完成任务"""
        self.dag_scheduler.mark_completed(task_id, output)
        logger.info(f"Task completed: {task_id}")
    
    def fail_task(self, task_id: str, error: str = ""):
        """任务失败"""
        task = self.dag_scheduler.tasks.get(task_id)
        
        if not task:
            return
        
        # 检查是否需要重试
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.RETRYING
            logger.info(f"Task retry scheduled: {task_id} (retry {task.retry_count}/{task.max_retries})")
        else:
            self.dag_scheduler.mark_failed(task_id, error)
            logger.error(f"Task failed: {task_id}, error: {error}")
    
    def cancel_task(self, task_id: str):
        """取消任务"""
        if task_id in self.dag_scheduler.tasks:
            self.dag_scheduler.tasks[task_id].status = TaskStatus.CANCELLED
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        task = self.dag_scheduler.tasks.get(task_id)
        return task.status if task else None
    
    def get_all_tasks(self) -> List[Task]:
        """获取所有任务"""
        return list(self.dag_scheduler.tasks.values())
    
    def get_statistics(self) -> Dict[str, int]:
        """获取统计信息"""
        tasks = self.dag_scheduler.tasks
        
        stats = {
            "total": len(tasks),
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0
        }
        
        for task in tasks.values():
            if task.status == TaskStatus.PENDING:
                stats["pending"] += 1
            elif task.status == TaskStatus.RUNNING:
                stats["running"] += 1
            elif task.status == TaskStatus.COMPLETED:
                stats["completed"] += 1
            elif task.status == TaskStatus.FAILED:
                stats["failed"] += 1
            elif task.status == TaskStatus.CANCELLED:
                stats["cancelled"] += 1
        
        return stats
    
    def get_ready_task_ids(self) -> List[str]:
        """获取就绪任务ID列表"""
        ready_tasks = self.dag_scheduler.get_ready_tasks()
        return [t.id for t in ready_tasks]
    
    def get_pending_tasks_by_priority(self) -> List[Task]:
        """按优先级获取待执行任务"""
        all_tasks = self.get_all_tasks()
        pending = [t for t in all_tasks if t.status == TaskStatus.PENDING]
        
        # 直接使用TaskPriority枚举
        pending.sort(key=lambda t: t.priority.value if hasattr(t.priority, 'value') else t.priority)
        return pending


class AutoScheduler:
    """自动调度器 - 自动将任务分发给合适的Agent"""
    
    def __init__(self, scheduler_engine: SchedulerEngine, agents_db: Dict[str, Dict] = None):
        self.scheduler = scheduler_engine
        self.agents_db = agents_db or {}
        self.dispatch_callback: Optional[Callable] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._interval = 5  # 调度间隔（秒）
    
    def set_dispatch_callback(self, callback: Callable[[Task, str], None]):
        """设置任务分发回调"""
        self.dispatch_callback = callback
    
    def start(self):
        """启动自动调度"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Auto scheduler started")
    
    def stop(self):
        """停止自动调度"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Auto scheduler stopped")
    
    def _run_loop(self):
        """调度循环"""
        while self._running:
            try:
                self._schedule_next()
            except Exception as e:
                logger.error(f"Schedule error: {e}")
            time.sleep(self._interval)
    
    def _schedule_next(self):
        """调度下一个任务"""
        # 获取就绪任务
        ready_tasks = self.scheduler.get_ready_tasks()
        
        if not ready_tasks:
            return
        
        # 获取可用Agent
        available_agents = self._get_available_agents()
        
        if not available_agents:
            return
        
        # 按优先级分配任务
        for task in ready_tasks:
            agent_id = self._dispatch_task(task, available_agents)
            if agent_id and self.dispatch_callback:
                self.dispatch_callback(task, agent_id)
    
    def _get_available_agents(self) -> List[Dict]:
        """获取可用Agent列表"""
        available = []
        for agent in self.agents_db.values():
            status = agent.get("status", "")
            # 过滤空闲Agent
            if status in ["IDLE", "Idle"]:
                # 检查并发限制
                current_tasks = agent.get("current_tasks", 0)
                max_tasks = agent.get("max_concurrent_tasks", 1)
                if current_tasks < max_tasks:
                    available.append(agent)
        return available
    
    def _dispatch_task(self, task: Task, agents: List[Dict]) -> Optional[str]:
        """分发任务给Agent"""
        # 根据任务要求筛选
        required_capabilities = task.executor_params.get("required_capabilities", [])
        required_role = task.executor_params.get("required_role", "")
        
        suitable = agents
        
        # 按能力过滤
        if required_capabilities:
            suitable = [
                a for a in suitable
                if any(
                    cap.get("name") in required_capabilities or cap in required_capabilities
                    for cap in a.get("capabilities", [])
                )
            ]
        
        # 按角色过滤
        if required_role:
            suitable = [a for a in suitable if a.get("role_id") == required_role]
        
        if not suitable:
            return None
        
        # 选择负载最低的
        suitable.sort(key=lambda a: a.get("current_tasks", 0))
        selected = suitable[0]
        
        # 更新Agent负载
        selected["current_tasks"] = selected.get("current_tasks", 0) + 1
        
        return selected.get("id")
    
    def manual_dispatch(self, task_id: str, agent_id: str) -> bool:
        """手动分发任务"""
        if task_id not in self.scheduler.dag_scheduler.tasks:
            return False
        
        task = self.scheduler.dag_scheduler.tasks[task_id]
        
        # 检查Agent是否可用
        agent = self.agents_db.get(agent_id)
        if not agent:
            return False
        
        if agent.get("status") != "IDLE":
            return False
        
        # 分配任务
        task.assigned_agent_id = agent_id
        self.scheduler.start_task(task_id)
        
        # 更新Agent状态
        agent["current_tasks"] = agent.get("current_tasks", 0) + 1
        agent["status"] = "BUSY"
        
        return True
