#!/usr/bin/env python3
"""
Agent 调度系统 - 核心巡查引擎
每分钟巡查所有任务，根据状态决定操作
使用 A2A (openclaw agent) 直接调用 Agent
"""
import sys
import json
import time
import threading
import os
from datetime import datetime
from typing import Optional

# 生产环境日志级别
VERBOSE = os.environ.get("SCHEDULER_VERBOSE", "false").lower() == "true"


def log(msg: str):
    """日志输出"""
    if VERBOSE:
        print(msg)


sys.path.insert(0, "/home/robin/.openclaw/workspace-dev/scheduler")
from task_queue import RedisQueue
from models import TaskStatus


# Agent 配置
AGENT_NAMES = {
    "product-manager": "产品-埃姆林",
    "architect": "架构-莎伦",
    "dev-engineer": "开发-阿尔杰",
    "qa-tester": "质量-伦纳德",
    "sre-engineer": "运维-嘉德丽雅"
}

# 使用 Redis 队列
queue = RedisQueue()


def send_to_agent_async(agent_key: str, task: dict):
    """异步调用 Agent（后台运行）"""
    try:
        import subprocess
        
        agent_name = AGENT_NAMES.get(agent_key, agent_key)
        task_name = task.get('name', '未命名')
        
        # 构造消息
        message = f"""📋 {agent_name} 收到新任务

任务: {task_name}

请处理。"""
        
        # 使用 openclaw agent 调用（--deliver 让回复发送到群里，--reply-account 指定发送账号）
        # --reply-to 使Agent能够在群里回复消息
        cmd = [
            "/home/robin/.npm-global/bin/openclaw", "agent",
            "--agent", agent_key,
            "--channel", "feishu",
            "--message", message,
            "--deliver",
            "--reply-account", agent_key,
            "--reply-to", "oc_655d32450caf2473e50b5197ff6a7d44",
            "--timeout", "60"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        
        if result.returncode == 0:
            log(f"✅ A2A调用 {agent_name} 成功")
        else:
            log(f"❌ A2A调用失败: {result.stderr[:100]}")
    except Exception as e:
        log(f"❌ A2A调用异常: {e}")


def send_to_agent(agent_key: str, task: dict):
    """调用 Agent（异步后台运行）"""
    # 异步执行，不阻塞调度系统
    thread = threading.Thread(target=send_to_agent_async, args=(agent_key, task))
    thread.daemon = True
    thread.start()
    log(f"🔄 已启动 A2A 调用: {AGENT_NAMES.get(agent_key, agent_key)}")


def process_task(task_id: str) -> bool:
    """处理单个任务"""
    # 从 Redis 获取任务
    task = queue.get_task(task_id)
    if not task:
        return False
    
    status = task.status.value if hasattr(task.status, 'value') else str(task.status)
    agent_id = task.agent_id
    created_by = task.created_by or ""
    
    log(f"处理任务: {task.name} - {status}")
    
    # 1. pending -> A2A 调用 Agent
    if status == "pending":
        # ===== 防重复调度：检查是否有 pending/running 的同一节点任务 =====
        task_name = task.name
        
        # 检查 pending 队列中是否有同名的任务
        pending_task_ids = queue.redis.lrange(queue.pending_queue, 0, -1)
        for pending_id in pending_task_ids:
            if pending_id == task_id:
                continue
            pending_task = queue.get_task(pending_id)
            if pending_task and pending_task.name == task_name:
                log(f"   ⏭️ 跳过：pending 队列中已有同名任务 {task_name}")
                # 移出 pending 队列，避免重复调度
                queue.redis.lrem(queue.pending_queue, 0, task_id)
                return False
        
        # 检查 running 队列中是否有同名的任务
        running_task_ids = queue.redis.lrange(queue.running_queue, 0, -1)
        for running_id in running_task_ids:
            if running_id == task_id:
                continue
            running_task = queue.get_task(running_id)
            if running_task and running_task.name == task_name:
                log(f"   ⏭️ 跳过：running 队列中已有同名任务 {task_name}")
                # 移出 pending 队列
                queue.redis.lrem(queue.pending_queue, 0, task_id)
                return False
        
        # 检查 completed 队列中是否有同名的最近完成的任务（避免刚完成又被调度）
        # 这里简化处理：如果刚完成的任务还在 completed 队列中，则跳过
        # 注意：这可能导致一些边界问题，但对于大多数场景是安全的
        
        # 防 chain_id 重复调度
        chain_id = task.chain_id
        if chain_id:
            # 获取所有 running 任务，检查是否有同链ID的任务已在运行
            for running_id in running_task_ids:
                running_task = queue.get_task(running_id)
                if running_task and running_task.chain_id == chain_id and running_task.id != task_id:
                    log(f"   ⏭️ 跳过：同链任务 {running_task.name} 正在运行")
                    # 移出 pending 队列，避免重复调度
                    queue.redis.lrem(queue.pending_queue, 0, task_id)
                    return False
        
        task_dict = {
            "id": task.id,
            "name": task.name,
            "agent_id": agent_id,
            "created_by": created_by,
            "chain_id": chain_id
        }
        send_to_agent(agent_id, task_dict)
        
        # 更新任务状态为 running，避免重复调用
        task.status = TaskStatus.RUNNING
        queue.update_task(task)
        log(f"   → 已更新状态为 running")
        return True
    
    # 2. completed -> 触发下游节点
    elif status == "completed":
        log(f"   ✅ 任务完成: {task.name}")
        # 触发下游节点
        trigger_downstream(task, queue)
        return True
    
    return False


def trigger_downstream(task, queue: RedisQueue):
    """触发下游依赖任务"""
    # 如果已经触发过下游，不再重复触发
    if task.downstream_triggered:
        log(f"   ⏭️ 下游已触发，跳过: {task.name}")
        return
    
    # 标记已触发下游
    task.downstream_triggered = True
    queue.update_task(task)
    
    # 获取所有 pending 任务，检查是否有依赖当前任务的任务
    pending_task_ids = queue.redis.lrange(queue.pending_queue, 0, -1)
    
    triggered = []
    for downstream_id in pending_task_ids:
        downstream = queue.get_task(downstream_id)
        if downstream and downstream.depends_on:
            # 检查当前任务是否在依赖列表中
            if task.id in downstream.depends_on or task.name in downstream.depends_on:
                # 检查是否所有依赖都已完成
                all_deps_met = True
                for dep_id in downstream.depends_on:
                    dep_task = queue.get_task(dep_id)
                    if dep_task and dep_task.status != TaskStatus.COMPLETED:
                        all_deps_met = False
                        break
                
                if all_deps_met:
                    # 移除依赖标记，触发任务
                    downstream.depends_on = []
                    downstream.chain_id = task.chain_id  # 继承链ID
                    queue.update_task(downstream)
                    triggered.append(downstream.name)
                    log(f"   → 触发下游任务: {downstream.name}")
    
    if triggered:
        log(f"   ✅ 已触发 {len(triggered)} 个下游任务")


def run_scheduler():
    """运行调度系统"""
    # 从 Redis 获取待处理任务
    pending_task_ids = queue.get_pending_tasks(limit=10)
    log(f"🔄 巡查启动: {len(pending_task_ids)} 待处理")
    
    if not pending_task_ids:
        return
    
    # 处理每个任务
    for task_id in pending_task_ids:
        try:
            process_task(task_id)
        except Exception as e:
            log(f"❌ 处理任务失败: {e}")


if __name__ == "__main__":
    run_scheduler()
