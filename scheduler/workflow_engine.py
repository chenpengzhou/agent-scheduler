#!/usr/bin/env python3
"""
工作流引擎核心模块
模板解析、流程编排、人工确认
"""
import sys
import json
import re
import yaml
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

sys.path.insert(0, "/home/robin/.openclaw/workspace-dev/scheduler")
from models import (
    WorkflowTemplate, WorkflowInstance, NodeExecution, 
    WorkflowNode, WorkflowStatus, NodeStatus
)


class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self):
        self.templates: Dict[str, WorkflowTemplate] = {}
        self.instances: Dict[str, WorkflowInstance] = {}
        self.node_executions: Dict[str, NodeExecution] = {}
    
    # ========== 模板管理 ==========
    
    def parse_yaml(self, yaml_content: str) -> Dict[str, Any]:
        """解析YAML模板"""
        try:
            return yaml.safe_load(yaml_content)
        except Exception as e:
            raise ValueError(f"YAML解析失败: {e}")
    
    def create_template(self, name: str, description: str, yaml_content: str, created_by: str = "") -> WorkflowTemplate:
        """创建模板"""
        template = WorkflowTemplate(
            name=name,
            description=description,
            yaml_content=yaml_content,
            created_by=created_by
        )
        self.templates[template.id] = template
        return template
    
    def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        """获取模板"""
        return self.templates.get(template_id)
    
    def list_templates(self) -> List[WorkflowTemplate]:
        """列表模板"""
        return list(self.templates.values())
    
    # ========== 变量替换 ==========
    
    def replace_variables(self, message: str, instance: WorkflowInstance, 
                        node_outputs: Dict[str, Dict]) -> str:
        """替换变量"""
        result = message
        
        # 替换 trigger.input
        if instance.trigger_input:
            trigger_json = json.dumps(instance.trigger_input, ensure_ascii=False)
            result = result.replace("{trigger.input}", trigger_json)
            # 也支持直接访问字段
            for key, value in instance.trigger_input.items():
                result = result.replace(f"{{trigger.input.{key}}}", str(value))
        
        # 替换 node.XXX.output
        for pattern in re.findall(r'{node\.(.*?)\.output}', result):
            node_name = pattern
            if node_name in node_outputs:
                output_json = json.dumps(node_outputs[node_name], ensure_ascii=False)
                result = result.replace(f'{{node.{node_name}.output}}', output_json)
                # 也支持直接访问字段
                for key, value in node_outputs[node_name].items():
                    result = result.replace(f'{{node.{node_name}.{key}}}', str(value))
        
        # 替换 node.XXX.status
        for pattern in re.findall(r'{node\.(.*?)\.status}', result):
            node_name = pattern
            # 简化处理
            result = result.replace(f'{{node.{node_name}.status}}', 'completed')
        
        return result
    
    # ========== 实例管理 ==========
    
    def start_instance(self, template_id: str, trigger_input: Dict[str, Any]) -> Optional[WorkflowInstance]:
        """启动实例"""
        template = self.get_template(template_id)
        if not template:
            return None
        
        # 解析YAML
        config = self.parse_yaml(template.yaml_content)
        
        # 创建实例
        instance = WorkflowInstance(
            template_id=template_id,
            template_name=template.name,
            trigger_input=trigger_input,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now()
        )
        self.instances[instance.id] = instance
        
        # 解析节点并创建执行
        nodes_config = config.get("nodes", [])
        node_outputs = {}  # 存储节点输出
        
        for node_config in nodes_config:
            # 确保 depends_on 是列表
            depends_on_val = node_config.get("depends_on", [])
            if depends_on_val is None:
                depends_on_val = []
            elif isinstance(depends_on_val, str):
                # 字符串转为列表
                if depends_on_val.strip():
                    depends_on_val = [depends_on_val.strip()]
                else:
                    depends_on_val = []
            elif isinstance(depends_on_val, list):
                pass  # 已经是列表
            else:
                depends_on_val = []
            
            node = WorkflowNode(
                name=node_config.get("name", ""),
                agent=node_config.get("agent", ""),
                message=node_config.get("message", ""),
                depends_on=depends_on_val,
                output_format=node_config.get("output_format"),
                required_fields=node_config.get("required_fields", []),
                requires_approval=node_config.get("requires_approval", False),
                approver=node_config.get("approver")
            )
            
            # 替换变量
            message = self.replace_variables(node.message, instance, node_outputs)
            
            # 创建节点执行
            execution = NodeExecution(
                instance_id=instance.id,
                node_name=node.name,
                agent_id=node.agent,
                message=message,
                output_format=node.output_format,
                required_fields=node.required_fields,
                requires_approval=node.requires_approval,
                approver=node.approver,
                depends_on=node.depends_on
            )
            self.node_executions[execution.id] = execution
        
        # 触发第一个节点
        self._trigger_ready_nodes(instance.id)
        
        return instance
    
    def _trigger_ready_nodes(self, instance_id: str):
        """触发就绪的节点"""
        instance = self.instances.get(instance_id)
        if not instance:
            return
        
        # 获取所有节点执行
        executions = [e for e in self.node_executions.values() 
                    if e.instance_id == instance_id]
        
        for execution in executions:
            if execution.status != NodeStatus.PENDING:
                continue
            
            # 检查依赖是否完成
            deps_completed = True
            for dep_name in execution.depends_on:
                dep_exec = self._find_execution(instance_id, dep_name)
                if not dep_exec or dep_exec.status != NodeStatus.COMPLETED:
                    deps_completed = False
                    break
            
            if deps_completed:
                # 触发执行
                self._execute_node(execution)
    
    def _find_execution(self, instance_id: str, node_name: str) -> Optional[NodeExecution]:
        """查找节点执行"""
        for e in self.node_executions.values():
            if e.instance_id == instance_id and e.node_name == node_name:
                return e
        return None
    
    def _execute_node(self, execution: NodeExecution):
        """执行节点"""
        from scheduler_core import execute_task, get_agent_config
        
        execution.status = NodeStatus.RUNNING
        execution.started_at = datetime.now()
        
        # 获取Agent配置
        config = get_agent_config(execution.agent_id)
        
        # 触发Agent执行
        from task_queue import RedisQueue
        from models import Task
        
        task = Task(
            name=f"[工作流] {execution.node_name}",
            agent_id=execution.agent_id,
            message=execution.message,
            output_format=execution.output_format,
            required_fields=execution.required_fields
        )
        
        queue = RedisQueue()
        queue.create_task(task)
        
        # 执行任务
        execute_task(task, queue)
        
        # 保存任务ID到节点执行
        execution.output = {"task_id": task.id}
    
    def check_node_completion(self, task_id: str, output: Dict[str, Any]):
        """检查节点完成"""
        # 找到对应的节点执行
        for execution in self.node_executions.values():
            if execution.output and execution.output.get("task_id") == task_id:
                execution.output = output
                execution.status = NodeStatus.COMPLETED
                execution.completed_at = datetime.now()
                
                # 检查是否需要人工确认
                if execution.requires_approval:
                    execution.status = NodeStatus.AWAITING_APPROVAL
                    print(f"⏳ 等待审批: {execution.node_name}")
                else:
                    # 触发下游节点
                    self._trigger_ready_nodes(execution.instance_id)
                break
    
    def approve_node(self, execution_id: str, decision: str) -> bool:
        """审批节点"""
        execution = self.node_executions.get(execution_id)
        if not execution:
            return False
        
        execution.approval_decision = decision
        
        if decision == "approve":
            execution.status = NodeStatus.COMPLETED
            execution.completed_at = datetime.now()
            # 触发下游节点
            self._trigger_ready_nodes(execution.instance_id)
        else:
            # 驳回，重新执行
            execution.status = NodeStatus.PENDING
            execution.retry_count += 1
            self._execute_node(execution)
        
        return True
    
    def get_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """获取实例"""
        return self.instances.get(instance_id)
    
    def list_instances(self) -> List[WorkflowInstance]:
        """列表实例"""
        return list(self.instances.values())


# 全局实例
workflow_engine = WorkflowEngine()
