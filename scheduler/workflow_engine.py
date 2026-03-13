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
import redis
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("workflow_engine")

sys.path.insert(0, "/home/robin/.openclaw/workspace-dev/scheduler")
from models import (
    WorkflowTemplate, WorkflowInstance, NodeExecution, 
    WorkflowNode, WorkflowStatus, NodeStatus
)


class WorkflowEngine:
    """工作流引擎 - 支持多进程共享"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379, redis_db: int = 0):
        # Redis 连接（带重试）
        self._redis_host = redis_host
        self._redis_port = redis_port
        self._redis_db = redis_db
        self._connect_redis()
        self._prefix = "workflow"
        
        # 内存缓存（从 Redis 加载）
        self.templates: Dict[str, WorkflowTemplate] = {}
        self.instances: Dict[str, WorkflowInstance] = {}
        self.node_executions: Dict[str, NodeExecution] = {}
        
        # 强制从 Redis 加载数据
        self._load_from_redis()
        logger.info(f"WorkflowEngine 初始化完成: {len(self.templates)} 模板, {len(self.instances)} 实例, {len(self.node_executions)} 执行")
    
    def _serialize_value(self, value: Any) -> Any:
        """序列化值 - 确保所有类型都能存入 Redis"""
        if value is None:
            return None
        elif isinstance(value, bool):
            return 1 if value else 0
        elif isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif hasattr(value, 'isoformat'):  # 其他 datetime 子类
            return value.isoformat()
        else:
            return value
    
    def _deserialize_value(self, key: str, value: Any, field_type: str = None) -> Any:
        """反序列化值"""
        if value is None:
            return None
        
        # 尝试自动检测类型
        if isinstance(value, str):
            # 尝试解析为 JSON
            if value.startswith('{') or value.startswith('['):
                try:
                    return json.loads(value)
                except:
                    pass
            # 尝试解析为 datetime
            if 'at' in key.lower() or 'time' in key.lower():
                try:
                    return datetime.fromisoformat(value)
                except:
                    pass
            # 尝试解析为 bool/int
            if value in ('true', 'false'):
                return value == 'true'
            try:
                return int(value)
            except:
                pass
        
        return value
    
    def _connect_redis(self):
        """连接 Redis，带重试机制"""
        for attempt in range(3):
            try:
                self.redis = redis.Redis(
                    host=self._redis_host,
                    port=self._redis_port,
                    db=self._redis_db,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                self.redis.ping()
                logger.info(f"Redis 连接成功: {self._redis_host}:{self._redis_port}")
                return
            except Exception as e:
                logger.warning(f"Redis 连接失败 (尝试 {attempt+1}/3): {e}")
                if attempt == 2:
                    raise RuntimeError(f"无法连接 Redis: {e}")
                import time
                time.sleep(1)
    
    def reload(self):
        """强制从 Redis 重新加载所有数据"""
        self._load_from_redis()
    
    # ========== Redis Key 定义 ==========
    def _template_key(self, template_id: str) -> str:
        return f"{self._prefix}:templates:{template_id}"
    
    def _instance_key(self, instance_id: str) -> str:
        return f"{self._prefix}:instances:{instance_id}"
    
    def _execution_key(self, execution_id: str) -> str:
        return f"{self._prefix}:executions:{execution_id}"
    
    @property
    def _template_ids_key(self) -> str:
        return f"{self._prefix}:template_ids"
    
    @property
    def _instance_ids_key(self) -> str:
        return f"{self._prefix}:instance_ids"
    
    @property
    def _execution_ids_key(self) -> str:
        return f"{self._prefix}:execution_ids"
    
    # ========== Redis 持久化 ==========
    def _load_from_redis(self):
        """从 Redis 加载数据"""
        try:
            # 重新连接 Redis（确保连接有效）
            self._connect_redis()
            
            # 加载模板
            template_ids = self.redis.smembers(self._template_ids_key) or set()
            logger.info(f"从 Redis 加载 {len(template_ids)} 个模板...")
            for template_id in template_ids:
                template_data = self.redis.hgetall(self._template_key(template_id))
                if template_data:
                    self._restore_template(template_data)
            
            # 加载实例
            instance_ids = self.redis.smembers(self._instance_ids_key) or set()
            logger.info(f"从 Redis 加载 {len(instance_ids)} 个实例...")
            for instance_id in instance_ids:
                instance_data = self.redis.hgetall(self._instance_key(instance_id))
                if instance_data:
                    self._restore_instance(instance_data)
            
            # 加载节点执行
            execution_ids = self.redis.smembers(self._execution_ids_key) or set()
            logger.info(f"从 Redis 加载 {len(execution_ids)} 个执行...")
            for execution_id in execution_ids:
                execution_data = self.redis.hgetall(self._execution_key(execution_id))
                if execution_data:
                    self._restore_execution(execution_data)
            
            logger.info(f"✅ 从 Redis 加载完成: {len(self.templates)} 模板, {len(self.instances)} 实例, {len(self.node_executions)} 执行")
        except Exception as e:
            logger.error(f"❌ Redis 加载失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _save_template(self, template: WorkflowTemplate):
        """保存模板到 Redis"""
        try:
            self._connect_redis()  # 确保连接有效
            data = template.model_dump()
            data["created_at"] = template.created_at.isoformat()
            data["updated_at"] = template.updated_at.isoformat()
            data = {k: v for k, v in data.items() if v is not None}
            
            self.redis.hset(self._template_key(template.id), mapping=data)
            self.redis.sadd(self._template_ids_key, template.id)
            logger.info(f"✅ 保存模板到 Redis: {template.id}")
        except Exception as e:
            logger.error(f"❌ 保存模板失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _save_instance(self, instance: WorkflowInstance):
        """保存实例到 Redis - 使用统一序列化"""
        try:
            self._connect_redis()  # 确保连接有效
            data = instance.model_dump()
            data["created_at"] = instance.created_at.isoformat()
            if instance.started_at:
                data["started_at"] = instance.started_at.isoformat()
            if instance.completed_at:
                data["completed_at"] = instance.completed_at.isoformat()
            data = {k: v for k, v in data.items() if v is not None}
            
            # 使用统一序列化函数处理所有值
            data = {k: self._serialize_value(v) for k, v in data.items()}
            
            self.redis.hset(self._instance_key(instance.id), mapping=data)
            self.redis.sadd(self._instance_ids_key, instance.id)
            logger.info(f"✅ 保存实例到 Redis: {instance.id}")
        except Exception as e:
            logger.error(f"❌ 保存实例失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _save_execution(self, execution: NodeExecution):
        """保存节点执行到 Redis - 使用统一序列化"""
        try:
            self._connect_redis()  # 确保连接有效
            data = execution.model_dump()
            data["created_at"] = execution.created_at.isoformat()
            if execution.started_at:
                data["started_at"] = execution.started_at.isoformat()
            if execution.completed_at:
                data["completed_at"] = execution.completed_at.isoformat()
            data = {k: v for k, v in data.items() if v is not None}
            
            # 使用统一序列化函数处理所有值
            data = {k: self._serialize_value(v) for k, v in data.items()}
            
            self.redis.hset(self._execution_key(execution.id), mapping=data)
            self.redis.sadd(self._execution_ids_key, execution.id)
            logger.info(f"✅ 保存执行到 Redis: {execution.id} (node: {execution.node_name})")
        except Exception as e:
            logger.error(f"❌ 保存执行失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _restore_template(self, data: dict):
        """从数据恢复模板"""
        if "created_at" in data and data["created_at"]:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and data["updated_at"]:
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        self.templates[data["id"]] = WorkflowTemplate(**data)
    
    def _restore_instance(self, data: dict):
        """从数据恢复实例"""
        if "created_at" in data and data["created_at"]:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "started_at" in data and data["started_at"]:
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if "completed_at" in data and data["completed_at"]:
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        
        # 反序列化 trigger_input (JSON字符串 -> dict)
        if "trigger_input" in data and data["trigger_input"]:
            try:
                # 先处理中文引号问题
                trigger_input_str = data["trigger_input"]
                # 将中文引号替换为英文引号
                trigger_input_str = trigger_input_str.replace('"', '"').replace('"', '"')
                data["trigger_input"] = json.loads(trigger_input_str)
            except (json.JSONDecodeError, TypeError, Exception) as e:
                # 如果还是失败，尝试直接使用原始字符串作为值
                logger.warning(f"trigger_input 反序列化失败: {e}, 原始值: {data['trigger_input'][:50]}...")
                data["trigger_input"] = {"raw": data["trigger_input"]}
        
        data["status"] = WorkflowStatus(data["status"])
        self.instances[data["id"]] = WorkflowInstance(**data)
    
    def _restore_execution(self, data: dict):
        """从数据恢复执行"""
        if "created_at" in data and data["created_at"]:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "started_at" in data and data["started_at"]:
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if "completed_at" in data and data["completed_at"]:
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        
        # 转换复杂类型
        if "depends_on" in data and data["depends_on"]:
            data["depends_on"] = json.loads(data["depends_on"])
        if "required_fields" in data and data["required_fields"]:
            data["required_fields"] = json.loads(data["required_fields"])
        if "output" in data and data["output"]:
            try:
                data["output"] = json.loads(data["output"])
            except:
                pass
        
        data["status"] = NodeStatus(data["status"])
        self.node_executions[data["id"]] = NodeExecution(**data)
    
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
        # 持久化到 Redis
        self._save_template(template)
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
        print(f"🔄 [工作流] 启动实例，模板ID: {template_id}")
        
        template = self.get_template(template_id)
        if not template:
            print(f"❌ [工作流] 模板不存在: {template_id}")
            return None
        
        print(f"📋 [工作流] 模板: {template.name}")
        
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
        # 持久化到 Redis
        self._save_instance(instance)
        
        print(f"✅ [工作流] 实例已创建: {instance.id}")
        
        # 解析节点并创建执行
        nodes_config = config.get("nodes", [])
        print(f"📝 [工作流] 节点数量: {len(nodes_config)}")
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
            # 保存到 Redis，确保所有节点都能被后续流程找到
            self._save_execution(execution)
        
        # 触发第一个节点
        self._trigger_ready_nodes(instance.id)
        
        return instance
    
    def _trigger_ready_nodes(self, instance_id: str, max_retries: int = 3):
        """触发就绪的节点 - 带重试"""
        instance = self.instances.get(instance_id)
        if not instance:
            logger.warning(f"_trigger_ready_nodes: 实例不存在 {instance_id}")
            return
        
        # 获取所有节点执行
        executions = [e for e in self.node_executions.values() 
                    if e.instance_id == instance_id]
        
        logger.info(f"_trigger_ready_nodes: instance_id={instance_id}, pending nodes={len([e for e in executions if e.status == NodeStatus.PENDING])}")
        
        for execution in executions:
            if execution.status != NodeStatus.PENDING:
                continue
            
            logger.info(f"   检查节点: {execution.node_name}, 依赖: {execution.depends_on}")
            
            # 检查依赖是否完成
            deps_completed = True
            for dep_name in execution.depends_on:
                dep_exec = self._find_execution(instance_id, dep_name)
                logger.info(f"      依赖 {dep_name}: {dep_exec}")
                if not dep_exec or dep_exec.status != NodeStatus.COMPLETED:
                    deps_completed = False
                    break
            
            if deps_completed:
                # 触发执行
                logger.info(f"   ✅ 依赖满足，触发节点: {execution.node_name}")
                self._execute_node(execution)
    
    def _trigger_ready_nodes_with_retry(self, instance_id: str):
        """带重试的下游触发"""
        for attempt in range(3):
            try:
                self._load_from_redis()  # 每次重试前重新加载最新数据
                self._trigger_ready_nodes(instance_id)
                return
            except Exception as e:
                logger.warning(f"触发下游失败 (尝试 {attempt+1}/3): {e}")
                if attempt < 2:
                    import time
                    time.sleep(0.5 * (attempt + 1))
    
    def _find_execution(self, instance_id: str, node_name: str) -> Optional[NodeExecution]:
        """查找节点执行"""
        for e in self.node_executions.values():
            if e.instance_id == instance_id and e.node_name == node_name:
                logger.info(f"_find_execution: 查找 {node_name}, 结果={e.id}, status={e.status}")
                return e
        logger.warning(f"_find_execution: 未找到节点 {node_name}")
        return None
    
    def _execute_node(self, execution: NodeExecution):
        """执行节点"""
        from scheduler_core import execute_task, get_agent_config
        
        execution.status = NodeStatus.RUNNING
        execution.started_at = datetime.now()
        
        # 持久化到 Redis
        self._save_execution(execution)
        
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
            required_fields=execution.required_fields,
            depends_on=execution.depends_on
        )
        
        queue = RedisQueue()
        queue.create_task(task)
        
        # 执行任务
        execute_task(task, queue)
        
        # 保存任务ID到节点执行
        execution.output = {"task_id": task.id}
        self._save_execution(execution)
    
    def check_node_completion(self, task_id: str, output: Dict[str, Any]):
        """检查节点完成"""
        logger.info(f"🔔 check_node_completion 被调用: task_id={task_id}")
        
        # 关键修复：每次调用时都从 Redis 重新加载数据，确保获取最新状态
        self._load_from_redis()
        
        # 找到对应的节点执行
        found = False
        for execution in self.node_executions.values():
            if execution.output and execution.output.get("task_id") == task_id:
                found = True
                logger.info(f"✅ 找到匹配的节点执行: {execution.node_name} (id={execution.id})")
                
                execution.output = output
                
                # 🆕 新增：验证 required_fields
                if execution.required_fields:
                    missing_fields = [f for f in execution.required_fields 
                                   if f not in output or output.get(f) is None]
                    if missing_fields:
                        logger.warning(f"⚠️ 节点输出缺少必要字段: {missing_fields}")
                        
                        # 找到上游节点并重新激活
                        for dep_name in execution.depends_on:
                            dep_exec = self._find_execution(execution.instance_id, dep_name)
                            if dep_exec:
                                dep_exec.status = NodeStatus.PENDING
                                dep_exec.retry_count += 1
                                dep_exec.error_message = f"下游节点 {execution.node_name} 缺少字段: {missing_fields}"
                                self._save_execution(dep_exec)
                                logger.info(f"🔄 已重新激活上游节点: {dep_name}")
                        
                        # 标记当前节点为失败
                        execution.status = NodeStatus.FAILED
                        execution.error_message = f"缺少必要字段: {missing_fields}"
                        execution.completed_at = datetime.now()
                        self._save_execution(execution)
                        
                        logger.error(f"❌ 节点 {execution.node_name} 失败: 缺少字段 {missing_fields}")
                        return
                
                execution.status = NodeStatus.COMPLETED
                execution.completed_at = datetime.now()
                
                # 持久化到 Redis
                self._save_execution(execution)
                
                # 检查是否需要人工确认
                if execution.requires_approval:
                    execution.status = NodeStatus.AWAITING_APPROVAL
                    logger.info(f"⏳ 等待审批: {execution.node_name}")
                else:
                    # 触发下游节点（使用带重试的方法）
                    logger.info(f"🚀 触发下游节点 (instance_id={execution.instance_id})")
                    self._trigger_ready_nodes_with_retry(execution.instance_id)
                break
        
        if not found:
            logger.warning(f"⚠️ 未找到匹配的节点执行: task_id={task_id}")
            logger.warning(f"   当前内存中的执行数: {len(self.node_executions)}")
    
    def approve_node(self, execution_id: str, decision: str) -> bool:
        """审批节点"""
        execution = self.node_executions.get(execution_id)
        if not execution:
            return False
        
        execution.approval_decision = decision
        
        if decision == "approve":
            execution.status = NodeStatus.COMPLETED
            execution.completed_at = datetime.now()
            # 触发下游节点（使用带重试的方法）
            self._trigger_ready_nodes_with_retry(execution.instance_id)
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
