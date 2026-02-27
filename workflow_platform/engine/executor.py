"""
工作流执行引擎
"""
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import logging

from ..models import (
    WorkflowTemplate, 
    WorkflowExecution,
    WorkflowNode,
    NodeType,
    NodeStatus,
    NodeExecution
)

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """工作流执行引擎"""
    
    def __init__(self):
        self.templates_db: Dict[str, WorkflowTemplate] = {}
        self.executions_db: Dict[str, WorkflowExecution] = {}
        self.node_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认处理器"""
        self.node_handlers[NodeType.START] = self._handle_start
        self.node_handlers[NodeType.AGENT] = self._handle_agent
        self.node_handlers[NodeType.APPROVAL] = self._handle_approval
        self.node_handlers[NodeType.CONDITION] = self._handle_condition
        self.node_handlers[NodeType.TIMER] = self._handle_timer
        self.node_handlers[NodeType.NOTIFY] = self._handle_notify
        self.node_handlers[NodeType.END] = self._handle_end
    
    # ==================== 模板管理 ====================
    
    def create_template(self, template: WorkflowTemplate) -> WorkflowTemplate:
        """创建工作流模板"""
        self.templates_db[template.id] = template
        logger.info(f"Created workflow template: {template.name}")
        return template
    
    def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        """获取模板"""
        return self.templates_db.get(template_id)
    
    def list_templates(self) -> List[WorkflowTemplate]:
        """列出所有模板"""
        return list(self.templates_db.values())
    
    def update_template(self, template_id: str, **kwargs) -> Optional[WorkflowTemplate]:
        """更新模板"""
        template = self.templates_db.get(template_id)
        if not template:
            return None
        
        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        template.updated_at = datetime.now()
        return template
    
    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        if template_id in self.templates_db:
            del self.templates_db[template_id]
            return True
        return False
    
    # ==================== 执行管理 ====================
    
    def start_execution(self, template_id: str, input_data: Dict = None) -> WorkflowExecution:
        """开始执行工作流"""
        template = self.templates_db.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # 创建执行实例
        execution = WorkflowExecution(
            template_id=template_id,
            template_name=template.name,
            input_data=input_data or {},
            status="running"
        )
        
        self.executions_db[execution.id] = execution
        
        # 获取开始节点并执行
        start_node = template.get_start_node()
        if start_node:
            execution.current_node_id = start_node.id
            self._execute_node(execution, start_node)
        
        logger.info(f"Started workflow execution: {execution.id}")
        return execution
    
    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """获取执行实例"""
        return self.executions_db.get(execution_id)
    
    def list_executions(self, template_id: str = None) -> List[WorkflowExecution]:
        """列出执行实例"""
        executions = list(self.executions_db.values())
        if template_id:
            executions = [e for e in executions if e.template_id == template_id]
        return executions
    
    def _execute_node(self, execution: WorkflowExecution, node: WorkflowNode):
        """执行节点"""
        logger.info(f"Executing node: {node.name} ({node.node_type.value})")
        
        # 记录历史
        execution.execution_history.append({
            "node_id": node.id,
            "node_name": node.name,
            "node_type": node.node_type.value,
            "timestamp": datetime.now().isoformat(),
            "status": "running"
        })
        
        # 调用处理器
        handler = self.node_handlers.get(node.node_type)
        if handler:
            result = handler(execution, node)
            
            # 更新节点状态
            if result.get("status") == "completed":
                # 流转到下一个节点
                self._move_to_next_node(execution, node, result)
        else:
            logger.warning(f"No handler for node type: {node.node_type}")
            self._move_to_next_node(execution, node, {"status": "completed"})
    
    def _move_to_next_node(self, execution: WorkflowExecution, current_node: WorkflowNode, result: Dict):
        """移动到下一个节点"""
        template = self.templates_db.get(execution.template_id)
        if not template:
            return
        
        next_nodes = template.get_next_nodes(current_node.id)
        
        if not next_nodes:
            # 没有下一个节点，工作流结束
            execution.status = "completed"
            execution.completed_at = datetime.now()
            logger.info(f"Workflow completed: {execution.id}")
            return
        
        # 执行下一个节点
        for next_node in next_nodes:
            execution.current_node_id = next_node.id
            self._execute_node(execution, next_node)
    
    # ==================== 节点处理器 ====================
    
    def _handle_start(self, execution: WorkflowExecution, node: WorkflowNode) -> Dict:
        """处理开始节点"""
        return {"status": "completed", "output": {}}
    
    def _handle_agent(self, execution: WorkflowExecution, node: WorkflowNode) -> Dict:
        """处理Agent节点"""
        # 这里调用Agent执行任务
        # 实际实现中会调用Agent API
        logger.info(f"Triggering agent: {node.config.agent_name}")
        
        # 模拟执行
        return {
            "status": "completed",
            "output": {
                "agent_id": node.config.agent_id,
                "result": "Task executed"
            }
        }
    
    def _handle_approval(self, execution: WorkflowExecution, node: WorkflowNode) -> Dict:
        """处理审批节点"""
        logger.info(f"Approval required: {node.config.approver}")
        
        # 实际实现中会等待审批
        return {
            "status": "completed",
            "output": {
                "approved": True,
                "approver": node.config.approver
            }
        }
    
    def _handle_condition(self, execution: WorkflowExecution, node: WorkflowNode) -> Dict:
        """处理条件节点"""
        # 评估条件
        conditions = node.config.conditions
        
        # 简单实现：默认通过
        result = True
        
        logger.info(f"Condition evaluation: {result}")
        
        return {
            "status": "completed",
            "output": {"result": result}
        }
    
    def _handle_timer(self, execution: WorkflowExecution, node: WorkflowNode) -> Dict:
        """处理定时节点"""
        logger.info(f"Timer triggered: {node.config.cron_expression}")
        
        return {
            "status": "completed",
            "output": {}
        }
    
    def _handle_notify(self, execution: WorkflowExecution, node: WorkflowNode) -> Dict:
        """处理通知节点"""
        logger.info(f"Sending notification: {node.config.notification_channel}")
        
        return {
            "status": "completed",
            "output": {
                "sent": True,
                "channel": node.config.notification_channel
            }
        }
    
    def _handle_end(self, execution: WorkflowExecution, node: WorkflowNode) -> Dict:
        """处理结束节点"""
        execution.status = "completed"
        execution.completed_at = datetime.now()
        
        logger.info(f"Workflow ended: {execution.id}")
        
        return {"status": "completed", "output": node.config.output}
