#!/usr/bin/env python3
"""
Agent自动触发模块
检测任务消息并自动调用工具
"""

import re
import os
import subprocess
import json
from datetime import datetime
from typing import Optional, Dict, List

# 工具路径
TOOLS_DIR = "/home/robin/.openclaw/workspace-dev/tools"
RECEIVE_TASK_SCRIPT = f"{TOOLS_DIR}/receive_task.py"
COMPLETE_TASK_SCRIPT = f"{TOOLS_DIR}/complete_task.py"

# Agent名称映射
AGENT_NAMES = {
    "product-manager": "产品经理",
    "architect": "架构师",
    "dev-engineer": "开发工程师",
    "qa-tester": "测试工程师",
    "sre-engineer": "运维工程师"
}


class MessagePattern:
    """消息模式识别"""
    
    # 派发任务模式
    PATTERNS_TASK_ASSIGNED = [
        r"派发.*任务[:：]\s*(.+)",
        r"请.*处理.*任务[:：]\s*(.+)",
        r"交给.*处理.*任务[:：]\s*(.+)",
        r"任务[:：]\s*(.+)",  # 通用
    ]
    
    # 完成任务模式
    PATTERNS_TASK_COMPLETED = [
        r"完成.*任务[:：]\s*(.+)",
        r".*任务.*完成[:：]\s*(.+)",
        r"处理完成[:：]\s*(.+)",
        r"已.*完成[:：]\s*(.+)",
    ]
    
    # 优先级模式
    PRIORITY_PATTERNS = [
        (r"P0|紧急|紧急任务", "P0"),
        (r"P1|重要", "P1"),
        (r"P2|一般", "P2"),
        (r"P3|低", "P3"),
    ]
    
    @classmethod
    def detect_task_assigned(cls, message: str) -> Optional[Dict]:
        """检测任务派发"""
        message = message.strip()
        
        for pattern in cls.PATTERNS_TASK_ASSIGNED:
            match = re.search(pattern, message)
            if match:
                task_name = match.group(1).strip()
                priority = cls.detect_priority(message)
                return {
                    "task_name": task_name,
                    "priority": priority,
                    "type": "assigned"
                }
        
        return None
    
    @classmethod
    def detect_task_completed(cls, message: str) -> Optional[Dict]:
        """检测任务完成"""
        message = message.strip()
        
        for pattern in cls.PATTERNS_TASK_COMPLETED:
            match = re.search(pattern, message)
            if match:
                task_name = match.group(1).strip()
                return {
                    "task_name": task_name,
                    "type": "completed"
                }
        
        return None
    
    @classmethod
    def detect_priority(cls, message: str) -> str:
        """检测优先级"""
        for pattern, priority in cls.PRIORITY_PATTERNS:
            if re.search(pattern, message):
                return priority
        return "P2"  # 默认


class AutoTrigger:
    """自动触发器"""
    
    def __init__(self):
        self.message_pattern = MessagePattern()
        self.last_triggered = {}  # 避免重复触发
    
    def process_message(self, message: str, agent_name: str = None) -> Optional[Dict]:
        """处理消息，自动触发工具"""
        
        # 检测任务派发
        task_info = self.message_pattern.detect_task_assigned(message)
        if task_info and agent_name:
            return self.trigger_receive_task(agent_name, task_info)
        
        # 检测任务完成
        task_info = self.message_pattern.detect_task_completed(message)
        if task_info and agent_name:
            return self.trigger_complete_task(agent_name, task_info)
        
        return None
    
    def trigger_receive_task(self, agent_name: str, task_info: Dict) -> Dict:
        """触发接收任务"""
        task_name = task_info["task_name"]
        priority = task_info.get("priority", "P2")
        
        print(f"[AutoTrigger] 检测到任务派发: {agent_name} -> {task_name} ({priority})")
        
        # 调用工具
        try:
            result = subprocess.run(
                ["python3", RECEIVE_TASK_SCRIPT, agent_name, task_name, priority],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return {
                "action": "receive_task",
                "agent": agent_name,
                "task": task_name,
                "priority": priority,
                "success": result.returncode == 0,
                "output": result.stdout
            }
        except Exception as e:
            return {
                "action": "receive_task",
                "agent": agent_name,
                "task": task_name,
                "success": False,
                "error": str(e)
            }
    
    def trigger_complete_task(self, agent_name: str, task_info: Dict) -> Dict:
        """触发完成任务"""
        task_name = task_info["task_name"]
        
        print(f"[AutoTrigger] 检测到任务完成: {agent_name} -> {task_name}")
        
        # 调用工具
        try:
            result = subprocess.run(
                ["python3", COMPLETE_TASK_SCRIPT, agent_name, task_name, "已完成"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return {
                "action": "complete_task",
                "agent": agent_name,
                "task": task_name,
                "success": result.returncode == 0,
                "output": result.stdout
            }
        except Exception as e:
            return {
                "action": "complete_task",
                "agent": agent_name,
                "task": task_name,
                "success": False,
                "error": str(e)
            }


# 全局实例
_auto_trigger = AutoTrigger()


def process(message: str, agent_name: str = None) -> Optional[Dict]:
    """处理消息的入口函数"""
    return _auto_trigger.process_message(message, agent_name)


if __name__ == "__main__":
    # 测试
    test_messages = [
        "派发任务：迭代3开发",
        "请开发工程师处理API开发任务",
        "任务完成：代码审查",
        "已完成PRD编写"
    ]
    
    for msg in test_messages:
        print(f"\n消息: {msg}")
        result = process(msg, "dev-engineer")
        print(f"结果: {result}")
