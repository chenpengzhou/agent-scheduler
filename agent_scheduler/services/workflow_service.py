"""
工作流服务 - 自动流转规则引擎
"""
from typing import List, Dict, Optional, Callable
from datetime import datetime
import logging

from ..models.workflow_config import (
    DEFAULT_WORKFLOW_CONFIG, 
    ROLE_ID_MAPPING,
    WorkflowStage
)

logger = logging.getLogger(__name__)


class WorkflowService:
    """工作流服务"""
    
    def __init__(self, config: Dict = None):
        self.config = config or DEFAULT_WORKFLOW_CONFIG
        self.agents_db = {}
        self.tasks_db = {}
        self.trigger_callbacks: List[Callable] = []
    
    def set_dbs(self, agents_db: Dict = None, tasks_db: Dict = None):
        """设置数据库引用"""
        self.agents_db = agents_db or {}
        self.tasks_db = tasks_db or {}
    
    def register_trigger_callback(self, callback: Callable):
        """注册触发回调"""
        self.trigger_callbacks.append(callback)
    
    def get_stages(self) -> List[Dict]:
        """获取所有阶段"""
        return self.config.get("stages", [])
    
    def get_stage(self, stage_id: str) -> Optional[Dict]:
        """获取指定阶段"""
        for stage in self.config.get("stages", []):
            if stage["id"] == stage_id:
                return stage
        return None
    
    def get_next_stage(self, current_stage: str) -> Optional[str]:
        """获取下一阶段"""
        stage = self.get_stage(current_stage)
        if stage:
            return stage.get("next")
        return None
    
    def get_stage_by_role(self, role_id: str) -> Optional[str]:
        """根据角色ID获取阶段"""
        role = ROLE_ID_MAPPING.get(role_id)
        if not role:
            return None
        
        for stage in self.config.get("stages", []):
            if stage.get("role") == role:
                return stage["id"]
        return None
    
    def get_role_by_stage(self, stage: str) -> Optional[str]:
        """根据阶段获取角色"""
        stage_info = self.get_stage(stage)
        if stage_info:
            return stage_info.get("role")
        return None
    
    def get_transitions(self, from_stage: str = None) -> List[Dict]:
        """获取流转规则"""
        transitions = self.config.get("transitions", [])
        
        if from_stage:
            return [t for t in transitions if t.get("from_stage") == from_stage]
        
        return transitions
    
    def find_next_agent(self, current_stage: str) -> Optional[Dict]:
        """查找下一个Agent"""
        # 获取下一阶段
        next_stage = self.get_next_stage(current_stage)
        if not next_stage:
            return None
        
        # 获取下一阶段对应的角色
        role = self.get_role_by_stage(next_stage)
        if not role:
            return None
        
        # 查找该角色的Agent
        for agent in self.agents_db.values():
            # 检查Agent的角色
            agent_role_id = agent.get("role_id", "")
            agent_role = ROLE_ID_MAPPING.get(agent_role_id, "")
            
            if agent_role == role:
                # 检查Agent是否可用
                if agent.get("status") in ["IDLE", "BUSY"]:
                    return agent
        
        return None
    
    def trigger_transition(
        self, 
        task_id: str, 
        from_stage: str,
        event: str = "TASK_COMPLETED"
    ) -> Dict:
        """触发工作流流转"""
        # 查找流转规则
        transitions = self.get_transitions(from_stage)
        
        matching_transition = None
        for t in transitions:
            if t.get("trigger_event") == event:
                matching_transition = t
                break
        
        if not matching_transition:
            return {"success": False, "error": "No transition found"}
        
        to_stage = matching_transition.get("to_stage")
        
        # 更新任务
        if task_id in self.tasks_db:
            self.tasks_db[task_id]["workflow_stage"] = to_stage
        
        # 查找下一个Agent
        next_agent = self.find_next_agent(from_stage)
        
        # 执行动作
        actions = matching_transition.get("actions", [])
        action_results = []
        
        for action in actions:
            action_type = action.get("type")
            
            if action_type == "NOTIFY":
                # 通知
                action_results.append({
                    "type": "NOTIFY",
                    "target_role": action.get("target_role"),
                    "message": f"任务流转到 {to_stage}"
                })
            
            elif action_type == "ASSIGN_TO_AGENT" and next_agent:
                # 分配任务
                self.tasks_db[task_id]["assigned_agent_id"] = next_agent["id"]
                action_results.append({
                    "type": "ASSIGN_TO_AGENT",
                    "agent_id": next_agent["id"],
                    "agent_name": next_agent.get("name")
                })
        
        # 触发回调
        for callback in self.trigger_callbacks:
            try:
                callback(task_id, from_stage, to_stage, next_agent)
            except Exception as e:
                logger.error(f"Trigger callback error: {e}")
        
        return {
            "success": True,
            "from_stage": from_stage,
            "to_stage": to_stage,
            "next_agent": next_agent,
            "actions": action_results
        }
    
    def get_workflow_path(self, start_stage: str = None) -> List[str]:
        """获取工作流路径"""
        if not start_stage:
            start_stage = self.config["stages"][0]["id"]
        
        path = [start_stage]
        current = start_stage
        
        while True:
            next_stage = self.get_next_stage(current)
            if not next_stage or next_stage in path:
                break
            path.append(next_stage)
            current = next_stage
        
        return path
    
    def validate_workflow(self) -> Dict:
        """验证工作流配置"""
        errors = []
        
        # 检查阶段完整性
        stages = self.config.get("stages", [])
        stage_ids = {s["id"] for s in stages}
        
        # 检查流转
        for transition in self.config.get("transitions", []):
            from_s = transition.get("from_stage")
            to_s = transition.get("to_stage")
            
            if from_s and from_s not in stage_ids:
                errors.append(f"Invalid from_stage: {from_s}")
            
            if to_s and to_s not in stage_ids:
                errors.append(f"Invalid to_stage: {to_s}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }


class TriggerService:
    """触发器服务"""
    
    def __init__(self, workflow_service: WorkflowService = None):
        self.workflow_service = workflow_service or WorkflowService()
        self.rules: List[Dict] = []
    
    def add_rule(self, rule: Dict):
        """添加触发规则"""
        self.rules.append(rule)
    
    def evaluate(self, event: str, context: Dict) -> List[Dict]:
        """评估触发条件"""
        matching_rules = []
        
        for rule in self.rules:
            if rule.get("event") == event:
                # 检查条件
                conditions = rule.get("conditions", {})
                
                matches = True
                for key, value in conditions.items():
                    if context.get(key) != value:
                        matches = False
                        break
                
                if matches:
                    matching_rules.append(rule)
        
        return matching_rules
    
    def execute(self, event: str, context: Dict) -> List[Dict]:
        """执行触发"""
        rules = self.evaluate(event, context)
        results = []
        
        for rule in rules:
            action = rule.get("action")
            
            if action == "TRANSITION":
                result = self.workflow_service.trigger_transition(
                    context.get("task_id"),
                    context.get("current_stage"),
                    event
                )
                results.append(result)
        
        return results
