#!/usr/bin/env python3
"""
调度系统核心模块
A2A调用、输出验证、重试机制
"""
import sys
import json
import time
import re
import subprocess
import threading
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

sys.path.insert(0, "/home/robin/.openclaw/workspace-dev/scheduler")
from models import Task, TaskStatus, AgentConfig
from task_queue import RedisQueue


# Agent配置（从配置文件或数据库加载）
DEFAULT_AGENT_CONFIG = {
    "product-manager": AgentConfig(
        agent_id="product-manager",
        account="product-manager",
        channel="feishu",
        default_group="oc_655d32450caf2473e50b5197ff6a7d44"
    ),
    "dev-engineer": AgentConfig(
        agent_id="dev-engineer",
        account="dev-engineer",
        channel="feishu",
        default_group="oc_655d32450caf2473e50b5197ff6a7d44"
    ),
    "architect": AgentConfig(
        agent_id="architect",
        account="architect",
        channel="feishu",
        default_group="oc_655d32450caf2473e50b5197ff6a7d44"
    ),
    "qa-tester": AgentConfig(
        agent_id="qa-tester",
        account="qa-tester",
        channel="feishu",
        default_group="oc_655d32450caf2473e50b5197ff6a7d44"
    ),
    "sre-engineer": AgentConfig(
        agent_id="sre-engineer",
        account="sre-engineer",
        channel="feishu",
        default_group="oc_655d32450caf2473e50b5197ff6a7d44"
    ),
    "trader": AgentConfig(
        agent_id="trader",
        account="trader",
        channel="feishu",
        default_group="oc_655d32450caf2473e50b5197ff6a7d44"
    )
}


def get_agent_config(agent_id: str) -> AgentConfig:
    """获取Agent配置"""
    return DEFAULT_AGENT_CONFIG.get(agent_id, AgentConfig(
        agent_id=agent_id,
        account=agent_id,
        channel="feishu",
        default_group="oc_655d32450caf2473e50b5197ff6a7d44"
    ))


def validate_output(task: Task) -> Tuple[bool, str]:
    """
    验证Agent输出
    返回: (是否有效, 结果或错误信息)
    """
    output = task.output
    output_format = task.output_format
    required_fields = task.required_fields
    
    # 如果没有指定格式要求，验证基本有效性
    if not output_format:
        if not output:
            return False, "输出为空"
        return True, "验证通过"
    
    # JSON格式验证
    if output_format == "json":
        try:
            if isinstance(output, str):
                output = json.loads(output)
            
            # 检查必填字段
            for field in required_fields:
                if field not in output:
                    return False, f"缺少字段: {field}"
            return True, output
        except json.JSONDecodeError as e:
            return False, f"输出不是有效JSON: {e}"
    
    return True, "验证通过"


def notify_error(task: Task, error_message: str):
    """错误通知 - 超过重试次数后通知人工"""
    try:
        import subprocess
        
        # 通知消息
        message = f"""⚠️ 任务执行失败

任务: {task.name}
Agent: {task.agent_id}
错误: {error_message}
重试次数: {task.retry_count}/{task.max_retries}

请人工处理。"""
        
        # 使用CEO账号发送通知
        cmd = [
            "/home/robin/.npm-global/bin/openclaw", "message", "send",
            "--channel", "feishu",
            "--target", "oc_655d32450caf2473e50b5197ff6a7d44",
            "--message", message
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ 已发送错误通知")
        else:
            print(f"⚠️ 通知发送失败: {result.stderr[:100]}")
    except Exception as e:
        print(f"❌ 通知异常: {e}")


def execute_task_async(task: Task, queue: RedisQueue):
    """异步执行任务"""
    try:
        # 更新状态为running
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        queue.update_task(task)
        
        # 获取Agent配置
        config = get_agent_config(task.agent_id)
        
        # 构建消息
        message = task.message or f"请执行任务: {task.name}"
        
        # 调用Agent
        cmd = [
            "/home/robin/.npm-global/bin/openclaw", "agent",
            "--agent", task.agent_id,
            "--channel", config.channel,
            "--message", message,
            "--deliver",
            "--reply-account", config.account,
            "--reply-to", config.default_group,
            "--timeout", str(task.timeout)
        ]
        
        print(f"🔄 执行任务: {task.name} -> {task.agent_id}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=task.timeout + 30)
        
        if result.returncode == 0:
            # 解析输出
            try:
                # 尝试从输出中提取JSON
                output_text = result.stdout
                # 简单的JSON提取（可能需要改进）
                task.output = {"result": output_text}
            except:
                task.output = {"result": result.stdout}
            
            # 验证输出
            is_valid, validation_result = validate_output(task)
            
            if is_valid:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                print(f"✅ 任务完成: {task.name}")
            else:
                # 输出验证失败，检查重试
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.PENDING
                    print(f"⚠️ 输出验证失败，重试 {task.retry_count}/{task.max_retries}: {validation_result}")
                else:
                    task.status = TaskStatus.FAILED
                    task.error_message = f"输出验证失败: {validation_result}"
                    task.completed_at = datetime.now()
                    print(f"❌ 任务失败: {task.name} - {validation_result}")
                    notify_error(task, validation_result)
        else:
            # Agent执行失败
            task.error = result.stderr[:500]
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                print(f"⚠️ Agent执行失败，重试 {task.retry_count}/{task.max_retries}")
            else:
                task.status = TaskStatus.FAILED
                task.error_message = f"Agent执行失败: {task.error}"
                task.completed_at = datetime.now()
                print(f"❌ 任务失败: {task.name}")
                notify_error(task, task.error or "Agent执行失败")
        
        task.updated_at = datetime.now()
        queue.update_task(task)
        
    except subprocess.TimeoutExpired:
        task.status = TaskStatus.FAILED
        task.error_message = "执行超时"
        task.completed_at = datetime.now()
        queue.update_task(task)
        print(f"❌ 任务超时: {task.name}")
        
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = str(e)[:500]
        task.completed_at = datetime.now()
        queue.update_task(task)
        print(f"❌ 任务异常: {task.name} - {e}")


def execute_task(task: Task, queue: RedisQueue):
    """执行任务（异步）"""
    thread = threading.Thread(target=execute_task_async, args=(task, queue))
    thread.daemon = True
    thread.start()
    print(f"🔄 已启动任务: {task.name}")


def retry_task(task_id: str, queue: RedisQueue) -> bool:
    """重试任务"""
    task = queue.get_task(task_id)
    if not task:
        return False
    
    task.status = TaskStatus.PENDING
    task.retry_count = 0
    task.error = None
    task.error_message = None
    queue.update_task(task)
    
    execute_task(task, queue)
    return True
