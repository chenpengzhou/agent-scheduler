"""
DAG引擎 - 有向无环图支持
"""
from typing import Dict, List, Set, Optional, Any
from collections import defaultdict, deque
import uuid

from ..models.workflow import StepDefinition
from ..models.condition import Condition, ConditionEvaluator, StepDependsOn


class DAGNode:
    """DAG节点"""
    
    def __init__(self, step: StepDefinition):
        self.step = step
        self.id = step.id
        self.in_degree = 0  # 入度
        self.out_degree = 0  # 出度


class DAG:
    """有向无环图"""
    
    def __init__(self):
        self.nodes: Dict[str, DAGNode] = {}
        self.edges: Dict[str, List[str]] = defaultdict(list)  # from -> to
        self.reverse_edges: Dict[str, List[str]] = defaultdict(list)  # to -> from
        self.conditions: Dict[str, Condition] = {}  # 步骤ID -> 条件
    
    def add_step(self, step: StepDefinition, depends_on: List[str] = None, 
                 condition: Condition = None):
        """添加步骤节点"""
        node = DAGNode(step)
        self.nodes[step.id] = node
        
        # 添加依赖边
        if depends_on:
            node.in_degree = len(depends_on)
            for dep_id in depends_on:
                self.edges[dep_id].append(step.id)
                self.reverse_edges[step.id].append(dep_id)
        
        # 添加条件
        if condition:
            self.conditions[step.id] = condition
    
    def get_ready_steps(self, completed_steps: Set[str]) -> List[str]:
        """获取就绪的步骤（入度为0或所有前驱已完成）"""
        ready = []
        
        for step_id, node in self.nodes.items():
            if step_id in completed_steps:
                continue
            
            # 检查所有前驱是否完成
            deps = self.reverse_edges.get(step_id, [])
            if not deps or all(dep in completed_steps for dep in deps):
                ready.append(step_id)
        
        return ready
    
    def topological_sort(self) -> List[str]:
        """拓扑排序（Kahn算法）"""
        # 计算入度
        in_degree = {node_id: len(self.reverse_edges.get(node_id, [])) 
                     for node_id in self.nodes}
        
        # 入度为0的节点队列
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            node_id = queue.popleft()
            result.append(node_id)
            
            # 更新邻居节点的入度
            for neighbor in self.edges[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 检测环
        if len(result) != len(self.nodes):
            raise ValueError("Cycle detected in DAG!")
        
        return result
    
    def has_cycle(self) -> bool:
        """检测是否有环"""
        try:
            self.topological_sort()
            return False
        except ValueError:
            return True
    
    def get_parallel_groups(self, completed_steps: Set[str]) -> List[List[str]]:
        """获取可并行执行的步骤组"""
        # 按拓扑顺序分组
        topo_order = self.topological_sort()
        
        groups = []
        current_group = []
        
        for step_id in topo_order:
            if step_id in completed_steps:
                continue
            
            # 检查前驱是否全部完成
            deps = self.reverse_edges.get(step_id, [])
            if all(dep in completed_steps for dep in deps):
                current_group.append(step_id)
            else:
                # 前驱未全部完成，新开一组
                if current_group:
                    groups.append(current_group)
                    current_group = []
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def evaluate_condition(self, step_id: str, context: Dict[str, Any]) -> Optional[str]:
        """评估条件，返回下一步步骤ID"""
        condition = self.conditions.get(step_id)
        if not condition:
            return None
        
        if ConditionEvaluator.evaluate(condition.expression, context):
            return condition.target_step_id
        elif condition.otherwise_step_id:
            return condition.otherwise_step_id
        
        return None


class DAGBuilder:
    """DAG构建器"""
    
    def __init__(self):
        self.dag = DAG()
    
    def build_from_steps(self, steps: List[StepDefinition], 
                         depends_on_map: Dict[str, List[str]] = None,
                         conditions: Dict[str, Condition] = None) -> DAG:
        """从步骤列表构建DAG"""
        depends_on_map = depends_on_map or {}
        conditions = conditions or {}
        
        # 添加所有节点
        for step in steps:
            deps = depends_on_map.get(step.id, [])
            condition = conditions.get(step.id)
            self.dag.add_step(step, depends_on=deps, condition=condition)
        
        # 检查环
        if self.dag.has_cycle():
            raise ValueError("Workflow definition contains a cycle!")
        
        return self.dag


class DAGExecutor:
    """DAG执行器"""
    
    def __init__(self, dag: DAG):
        self.dag = dag
        self.completed_steps: Set[str] = set()
        self.failed_steps: Set[str] = set()
        self.running_steps: Set[str] = set()
        self.execution_order: List[str] = []
    
    def get_next_steps(self) -> List[str]:
        """获取下一步可执行的步骤"""
        return self.dag.get_ready_steps(self.completed_steps)
    
    def mark_completed(self, step_id: str):
        """标记步骤完成"""
        self.completed_steps.add(step_id)
        self.running_steps.discard(step_id)
        self.execution_order.append(step_id)
    
    def mark_failed(self, step_id: str):
        """标记步骤失败"""
        self.failed_steps.add(step_id)
        self.running_steps.discard(step_id)
    
    def is_step_ready(self, step_id: str) -> bool:
        """检查步骤是否就绪"""
        if step_id in self.completed_steps or step_id in self.failed_steps:
            return False
        
        # 检查前驱是否完成
        deps = self.dag.reverse_edges.get(step_id, [])
        return all(dep in self.completed_steps for dep in deps)
    
    def get_execution_plan(self) -> List[List[str]]:
        """获取执行计划（按批次）"""
        plan = []
        completed = set()
        
        while True:
            # 获取当前可执行的批次
            batch = self.dag.get_parallel_groups(completed)
            if not batch:
                break
            
            plan.extend(batch)
            
            # 模拟完成这些步骤
            for step_ids in batch:
                if isinstance(step_ids, list):
                    completed.update(step_ids)
                else:
                    completed.add(step_ids)
        
        return plan
