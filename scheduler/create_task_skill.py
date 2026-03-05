#!/usr/bin/env python3
"""
CEO 创建任务 Skill
用法：python3 create_task_skill.py <任务名称> <步骤1> <步骤2> ...
示例：python3 create_task_skill.py "蜂群算力开发" "产品方案" "技术方案" "开发" "测试" "部署"
"""
import sys
import json
from datetime import datetime

# 添加路径
sys.path.insert(0, "/home/robin/.openclaw/workspace-dev/scheduler")
from db import db


# 默认工作流
DEFAULT_STEPS = ["产品方案", "技术方案", "开发", "代码审核", "测试", "部署"]

# Agent 映射：步骤 -> Agent
STEP_TO_AGENT = {
    "产品方案": "product-manager",
    "技术方案": "architect",
    "开发": "dev-engineer",
    "代码审核": "architect",
    "测试": "qa-tester",
    "部署": "sre-engineer"
}

# Agent 名称
AGENT_NAMES = {
    "product-manager": "产品-埃姆林",
    "architect": "架构-莎伦",
    "dev-engineer": "开发-阿尔杰",
    "qa-tester": "质量-伦纳德",
    "sre-engineer": "运维-嘉德丽雅"
}


def create_task(task_name: str, steps: list = None, description: str = "") -> str:
    """创建任务"""
    if not steps:
        steps = DEFAULT_STEPS.copy()
    
    # 创建任务
    task = db.create_task(
        name=task_name,
        description=description,
        steps=steps
    )
    
    # 输出结果
    result = f"✅ 任务已创建\n"
    result += f"名称: {task_name}\n"
    result += f"ID: {task['id']}\n"
    result += f"步骤: {' → '.join(steps)}\n"
    result += f"当前: {steps[0]} (待处理)\n"
    result += f"\n下一步: 调度系统将通知 {AGENT_NAMES.get(STEP_TO_AGENT.get(steps[0]), 'Agent')} 处理"
    
    return result


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print(f"\n默认步骤: {' → '.join(DEFAULT_STEPS)}")
        sys.exit(1)
    
    task_name = sys.argv[1]
    steps = sys.argv[2:] if len(sys.argv) > 2 else None
    
    result = create_task(task_name, steps)
    print(result)
