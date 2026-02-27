# 工作流引擎完整文档

## 概述

工作流引擎是一个支持DAG执行、并行处理、审批流程的自动化工作流系统。

## 技术架构

### 迭代版本

| 迭代 | 功能 | 状态 |
|------|------|------|
| 迭代1 | MVP基础框架 | ✅ 完成 |
| 迭代2 | 状态持久化 + API | ✅ 完成 |
| 迭代3 | DAG + 并行执行 | ✅ 完成 |
| 迭代4 | 审批 + 通知 | ✅ 完成 |
| 迭代5 | 集成 + 测试 | ✅ 完成 |

## 快速开始

### 安装

```bash
cd workflow_engine
pip install -e .
```

### 基本使用

```python
from workflow_engine import WorkflowEngine, WorkflowDefinition, StepDefinition, TaskDefinition

# 创建工作流
steps = [
    StepDefinition(
        id='step1',
        name='第一步',
        task_def=TaskDefinition(id='t1', name='执行任务', executor_type='script')
    )
]

wf_def = WorkflowDefinition(id='my-workflow', name='我的工作流', steps=steps)

# 执行
engine = WorkflowEngine()
result = engine.execute(wf_def)
print(result.status)
```

### DAG并行执行

```python
from workflow_engine import ParallelExecutor, WorkflowDefinition, StepDefinition, TaskDefinition

steps = [
    StepDefinition(id='s1', name='开始', task_def=TaskDefinition(id='t1', name='init', executor_type='script')),
    StepDefinition(id='s2', name='任务A', task_def=TaskDefinition(id='t2', name='taskA', executor_type='script')),
    StepDefinition(id='s3', name='任务B', task_def=TaskDefinition(id='t3', name='taskB', executor_type='script')),
    StepDefinition(id='s4', name='结束', task_def=TaskDefinition(id='t4', name='end', executor_type='script')),
]

wf_def = WorkflowDefinition(id='dag', name='DAG工作流', steps=steps)

# 定义依赖
depends_on = {
    's2': ['s1'],
    's3': ['s1'],
    's4': ['s2', 's3']
}

executor = ParallelExecutor()
result = executor.execute(wf_def, depends_on_map=depends_on)
```

### 审批流程

```python
from workflow_engine.services.approval_service import ApprovalService, NotificationService

notification_svc = NotificationService()
approval_svc = ApprovalService(notification_svc)

# 创建审批
approval = approval_svc.create_approval(
    step_instance_id='step_approval',
    workflow_instance_id='wf_001',
    title='请假申请',
    approver='manager'
)

# 审批通过
approval_svc.approve(approval.id, approved_by='manager', comment='同意')

# 审批拒绝
approval_svc.reject(approval.id, rejected_by='manager', comment='不同意')
```

### REST API

```bash
# 启动API服务
python -m uvicorn api.main:app --port 8000

# 创建工作流定义
curl -X POST http://localhost:8000/api/v1/workflow-definitions \
  -H "Content-Type: application/json" \
  -d '{"name": "测试", "definition_json": {"steps": [{"id": "s1", "name": "第一步"}]}}'

# 启动工作流实例
curl -X POST http://localhost:8000/api/v1/workflow-instances \
  -H "Content-Type: application/json" \
  -d '{"definition_id": "<def_id>", "input_data": {}}'

# 查询指标
curl http://localhost:8000/api/v1/workflow-instances/metrics
```

## 核心模块

### 模型

- `models/workflow.py` - 工作流模型
- `models/condition.py` - 条件模型
- `models/approval.py` - 审批模型

### 引擎

- `engine/core.py` - 核心引擎
- `engine/dag.py` - DAG引擎
- `engine/executor.py` - 并行执行器

### 服务

- `services/approval_service.py` - 审批服务
- `api/services/workflow_svc.py` - 工作流服务

## 测试

```bash
# 运行集成测试
python workflow_engine/tests/test_integration.py
```

## API文档

访问 http://localhost:8000/docs 查看完整API文档
