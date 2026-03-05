#!/usr/bin/env python3
"""
FastAPI 接口 - Agent 调度器 & 工作流引擎
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uvicorn

import sys
sys.path.insert(0, "/home/robin/.openclaw/workspace-dev/scheduler")

from models import Task, TaskStatus, AgentConfig, WorkflowTemplate, WorkflowInstance, NodeExecution
from task_queue import RedisQueue
from scheduler_core import execute_task, retry_task, validate_output, DEFAULT_AGENT_CONFIG
from workflow_engine import workflow_engine

app = FastAPI(title="塔罗会调度系统", version="1.0.0")
queue = RedisQueue()


# ========== 任务管理 ==========

class TaskCreate(BaseModel):
    name: str
    agent_id: str
    message: str = ""
    payload: Dict[str, Any] = {}
    timeout: int = 300
    retry: int = 0
    output_format: Optional[str] = None
    required_fields: List[str] = []
    max_retries: int = 5
    created_by: Optional[str] = ""


class TaskResponse(BaseModel):
    id: str
    name: str
    agent_id: str
    message: str
    status: str
    output: Optional[Dict] = None
    error_message: Optional[str] = None
    retry_count: int
    max_retries: int
    created_at: str


@app.post("/tasks", response_model=TaskResponse)
async def create_task(task_data: TaskCreate):
    """创建任务"""
    task = Task(
        name=task_data.name,
        agent_id=task_data.agent_id,
        message=task_data.message,
        payload=task_data.payload,
        timeout=task_data.timeout,
        output_format=task_data.output_format,
        required_fields=task_data.required_fields,
        max_retries=task_data.max_retries,
        created_by=task_data.created_by or ""
    )
    
    queue.create_task(task)
    # 只创建任务，不执行，由调度系统巡查触发
    
    return TaskResponse(
        id=task.id,
        name=task.name,
        agent_id=task.agent_id,
        message=task.message,
        status=task.status.value,
        output=task.output,
        error_message=task.error_message,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
        created_at=task.created_at.isoformat()
    )


@app.get("/tasks")
async def list_tasks(status: Optional[str] = None, limit: int = 100):
    """任务列表"""
    task_ids = queue.get_pending_tasks(limit=limit)
    tasks = []
    for tid in task_ids:
        t = queue.get_task(tid)
        if t:
            tasks.append(TaskResponse(
                id=t.id,
                name=t.name,
                agent_id=t.agent_id,
                message=t.message,
                status=t.status.value,
                output=t.output,
                error_message=t.error_message,
                retry_count=t.retry_count,
                max_retries=t.max_retries,
                created_at=t.created_at.isoformat()
            ))
    return {"tasks": tasks, "total": len(tasks)}


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务"""
    task = queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse(
        id=task.id,
        name=task.name,
        agent_id=task.agent_id,
        message=task.message,
        status=task.status.value,
        output=task.output,
        error_message=task.error_message,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
        created_at=task.created_at.isoformat()
    )


@app.post("/tasks/{task_id}/retry")
async def retry_task_endpoint(task_id: str):
    """重试任务"""
    task = queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    retry_task(task_id, queue)
    return {"status": "retrying", "task_id": task_id}


# ========== 工作流管理 ==========

class WorkflowTemplateCreate(BaseModel):
    name: str
    description: str = ""
    yaml_content: str
    created_by: str = ""


class WorkflowInstanceCreate(BaseModel):
    template_id: str
    trigger_input: Dict[str, Any] = {}


@app.post("/workflows/templates")
async def create_workflow_template(data: WorkflowTemplateCreate):
    """创建工作流模板"""
    template = workflow_engine.create_template(
        name=data.name,
        description=data.description,
        yaml_content=data.yaml_content,
        created_by=data.created_by
    )
    return {"id": template.id, "name": template.name}


@app.get("/workflows/templates")
async def list_workflow_templates():
    """列表工作流模板"""
    templates = workflow_engine.list_templates()
    return {"templates": [{"id": t.id, "name": t.name, "description": t.description} for t in templates]}


@app.get("/workflows/templates/{template_id}")
async def get_workflow_template(template_id: str):
    """获取工作流模板"""
    template = workflow_engine.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@app.post("/workflows/instances")
async def create_workflow_instance(data: WorkflowInstanceCreate):
    """启动工作流实例"""
    instance = workflow_engine.start_instance(data.template_id, data.trigger_input)
    if not instance:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"id": instance.id, "template_name": instance.template_name, "status": instance.status.value}


@app.get("/workflows/instances")
async def list_workflow_instances():
    """列表工作流实例"""
    instances = workflow_engine.list_instances()
    return {"instances": [{"id": i.id, "template_name": i.template_name, "status": i.status.value} for i in instances]}


@app.get("/workflows/instances/{instance_id}")
async def get_workflow_instance(instance_id: str):
    """获取工作流实例"""
    instance = workflow_engine.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    return instance


@app.post("/workflows/instances/{instance_id}/approve")
async def approve_workflow_node(instance_id: str, execution_id: str, decision: str):
    """审批工作流节点"""
    result = workflow_engine.approve_node(execution_id, decision)
    if not result:
        raise HTTPException(status_code=404, detail="Execution not found")
    return {"status": "approved" if decision == "approve" else "rejected"}


# ========== Agent 配置管理 ==========

class AgentConfigUpdate(BaseModel):
    agent_id: str
    account: str
    channel: str = "feishu"
    default_group: str = "oc_655d32450caf2473e50b5197ff6a7d44"


@app.get("/agents/config")
async def list_agent_configs():
    """获取所有Agent配置"""
    return {"agents": [
        {
            "agent_id": cfg.agent_id,
            "account": cfg.account,
            "channel": cfg.channel,
            "default_group": cfg.default_group
        }
        for cfg in DEFAULT_AGENT_CONFIG.values()
    ]}


@app.get("/agents/config/{agent_id}")
async def get_agent_config(agent_id: str):
    """获取单个Agent配置"""
    from scheduler_core import get_agent_config
    cfg = get_agent_config(agent_id)
    return {
        "agent_id": cfg.agent_id,
        "account": cfg.account,
        "channel": cfg.channel,
        "default_group": cfg.default_group
    }


# ========== 健康检查 ==========

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
