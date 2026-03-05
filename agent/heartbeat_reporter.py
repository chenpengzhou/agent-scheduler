#!/usr/bin/env python3
"""
Agent 心跳上报模块 - 调度系统版
实时上报 Agent 状态到调度系统
"""
import os
import sys
import json
import time
import threading
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List

# 配置
SCHEDULER_URL = os.environ.get("SCHEDULER_URL", "http://localhost:8080")
HEARTBEAT_INTERVAL = 30  # 心跳间隔（秒）
AGENT_ID = os.environ.get("AGENT_ID", "dev-engineer")


class SchedulerReporter:
    """调度系统上报器"""
    
    def __init__(self, agent_id: str = None, scheduler_url: str = None):
        self.agent_id = agent_id or AGENT_ID
        self.scheduler_url = scheduler_url or SCHEDULER_URL
        self.register_url = f"{self.scheduler_url}/api/v1/agents/register"
        self.heartbeat_url = f"{self.scheduler_url}/api/v1/agents/heartbeat"
        self._running = False
        self._thread = None
    
    def register(self, capabilities: List[str] = None) -> bool:
        """注册 Agent 到调度系统"""
        data = {
            "agent_id": self.agent_id,
            "capabilities": capabilities or []
        }
        
        try:
            response = requests.post(
                self.register_url,
                json=data,
                timeout=5
            )
            if response.status_code == 200:
                print(f"✅ Agent注册成功: {self.agent_id}")
                return True
            else:
                print(f"⚠️ Agent注册失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Agent注册异常: {e}")
            return False
    
    def heartbeat(self, status: str = "online", current_task: str = None) -> bool:
        """发送心跳到调度系统"""
        # 状态映射: idle -> online, busy保持busy, offline保持offline
        if status == "idle":
            status = "online"
        
        data = {
            "agent_id": self.agent_id,
            "status": status,
        }
        if current_task:
            data["current_task"] = current_task
        
        try:
            response = requests.post(
                self.heartbeat_url,
                json=data,
                timeout=5
            )
            if response.status_code == 200:
                print(f"✅ 心跳上报成功: {self.agent_id} - {status}")
                return True
            else:
                print(f"⚠️ 心跳上报失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 心跳上报异常: {e}")
            return False
    
    def report_idle(self):
        """上报空闲状态"""
        return self.heartbeat("online")
    
    def report_busy(self, task_name: str = None):
        """上报忙碌状态"""
        return self.heartbeat("busy", task_name)
    
    def report_online(self):
        """上报在线状态"""
        return self.heartbeat("online")
    
    def report_offline(self):
        """上报离线状态"""
        return self.heartbeat("offline")
    
    def start_background(self, capabilities: List[str] = None):
        """启动后台心跳"""
        if self._running:
            return
        
        # 先注册
        self.register(capabilities)
        
        self._running = True
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()
        print(f"✅ 调度心跳已启动: {self.agent_id}")
    
    def stop_background(self):
        """停止后台心跳"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        print(f"⏹️ 调度心跳已停止: {self.agent_id}")
    
    def _heartbeat_loop(self):
        """后台心跳循环"""
        while self._running:
            try:
                self.heartbeat("online")
            except Exception as e:
                print(f"❌ 后台心跳异常: {e}")
            time.sleep(HEARTBEAT_INTERVAL)


# 全局实例
_reporter = None

def get_scheduler_reporter(agent_id: str = None) -> SchedulerReporter:
    """获取全局调度上报器"""
    global _reporter
    if _reporter is None:
        _reporter = SchedulerReporter(agent_id)
    return _reporter


def register_to_scheduler(agent_id: str = None, capabilities: List[str] = None) -> bool:
    """注册到调度系统"""
    reporter = get_scheduler_reporter(agent_id)
    return reporter.register(capabilities)


def start_heartbeat(agent_id: str = None, capabilities: List[str] = None):
    """启动后台心跳"""
    reporter = get_scheduler_reporter(agent_id)
    reporter.start_background(capabilities)


def report_status(status: str, task_name: str = None):
    """便捷函数：上报状态变化"""
    reporter = get_scheduler_reporter()
    if status == "busy":
        return reporter.report_busy(task_name)
    elif status == "idle":
        return reporter.report_idle()
    else:
        return reporter.heartbeat(status, task_name)


# ========== 兼容旧接口 ==========
class HeartbeatReporter(SchedulerReporter):
    """兼容旧接口"""
    pass


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="调度系统心跳客户端")
    parser.add_argument("--agent-id", default="test-agent", help="Agent ID")
    parser.add_argument("--capabilities", nargs="*", default=["general"], help="Agent能力")
    parser.add_argument("--once", action="store_true", help="只发送一次心跳")
    args = parser.parse_args()
    
    reporter = SchedulerReporter(args.agent_id)
    
    # 注册
    reporter.register(args.capabilities)
    
    if args.once:
        reporter.heartbeat("online")
    else:
        # 启动后台心跳
        reporter.start_background(args.capabilities)
        
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            reporter.stop_background()
