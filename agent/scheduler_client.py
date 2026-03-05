#!/usr/bin/env python3
"""
调度系统集成模块
Agent 注册和心跳上报到调度系统
"""
import os
import sys
import time
import threading
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List

# 配置 - 调度系统地址
SCHEDULER_URL = os.environ.get("SCHEDULER_URL", "http://localhost:8080")
AGENT_ID = os.environ.get("AGENT_ID", "dev-engineer")
HEARTBEAT_INTERVAL = 30  # 心跳间隔（秒）


class SchedulerAgent:
    """调度系统 Agent 客户端"""
    
    def __init__(self, agent_id: str = None, scheduler_url: str = None, capabilities: List[str] = None):
        self.agent_id = agent_id or AGENT_ID
        self.scheduler_url = scheduler_url or SCHEDULER_URL
        self.capabilities = capabilities or ["coding"]
        self._running = False
        self._thread = None
        self._last_heartbeat = None
    
    def _get_api_url(self, path: str) -> str:
        return f"{self.scheduler_url}{path}"
    
    def register(self) -> bool:
        """注册 Agent"""
        url = self._get_api_url("/api/v1/agents/register")
        data = {
            "agent_id": self.agent_id,
            "capabilities": self.capabilities
        }
        
        try:
            response = requests.post(url, json=data, timeout=5)
            if response.status_code == 200:
                print(f"✅ Agent 注册成功: {self.agent_id}")
                return True
            elif response.status_code == 409:
                print(f"ℹ️ Agent 已存在: {self.agent_id}")
                return True
            else:
                print(f"⚠️ 注册失败 ({response.status_code}): {response.text}")
                return False
        except Exception as e:
            print(f"❌ 注册异常: {e}")
            return False
    
    def heartbeat(self, status: str = "idle", task_name: str = None) -> bool:
        """发送心跳"""
        url = self._get_api_url("/api/v1/agents/heartbeat")
        data = {
            "agent_id": self.agent_id,
            "status": status
        }
        if task_name:
            data["task_name"] = task_name
        
        try:
            response = requests.post(url, json=data, timeout=5)
            if response.status_code == 200:
                self._last_heartbeat = datetime.now()
                return True
            else:
                print(f"⚠️ 心跳失败 ({response.status_code})")
                return False
        except Exception as e:
            print(f"❌ 心跳异常: {e}")
            return False
    
    def start(self):
        """启动：先注册，然后启动心跳循环"""
        if self._running:
            return
        
        # 先注册
        if not self.register():
            print("⚠️ 注册失败，但继续启动心跳...")
        
        # 启动心跳循环
        self._running = True
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()
        print(f"✅ 调度系统客户端已启动: {self.agent_id}")
    
    def stop(self):
        """停止"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        self.heartbeat("offline")
        print(f"⏹️ 调度系统客户端已停止")
    
    def _heartbeat_loop(self):
        """心跳循环"""
        while self._running:
            try:
                self.heartbeat("idle")
            except Exception as e:
                print(f"❌ 心跳循环异常: {e}")
            time.sleep(HEARTBEAT_INTERVAL)
    
    def report_busy(self, task_name: str = None):
        """上报忙碌状态"""
        return self.heartbeat("busy", task_name)
    
    def report_idle(self):
        """上报空闲状态"""
        return self.heartbeat("idle")
    
    def report_offline(self):
        """上报离线状态"""
        return self.heartbeat("offline")


# 全局实例
_scheduler_agent = None

def get_scheduler_agent(agent_id: str = None, capabilities: List[str] = None) -> SchedulerAgent:
    """获取全局调度系统客户端"""
    global _scheduler_agent
    if _scheduler_agent is None:
        _scheduler_agent = SchedulerAgent(agent_id, capabilities=capabilities)
    return _scheduler_agent


def register_agent(agent_id: str = None, capabilities: List[str] = None) -> bool:
    """便捷函数：注册 Agent"""
    return SchedulerAgent(agent_id, capabilities=capabilities).register()


def start_heartbeat(agent_id: str = None, capabilities: List[str] = None):
    """便捷函数：启动心跳"""
    agent = get_scheduler_agent(agent_id, capabilities)
    agent.start()
    return agent


def stop_heartbeat():
    """便捷函数：停止心跳"""
    global _scheduler_agent
    if _scheduler_agent:
        _scheduler_agent.stop()
        _scheduler_agent = None


# ========== 状态变化回调 ==========
def on_task_start(task_name: str):
    """任务开始时调用"""
    if _scheduler_agent:
        _scheduler_agent.report_busy(task_name)

def on_task_complete(task_name: str = None):
    """任务完成时调用"""
    if _scheduler_agent:
        _scheduler_agent.report_idle()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="调度系统 Agent 客户端")
    parser.add_argument("--agent-id", "-a", default=AGENT_ID, help="Agent ID")
    parser.add_argument("--capabilities", "-c", nargs="+", default=["coding"], help="Agent 能力")
    parser.add_argument("--register-only", "-r", action="store_true", help="仅注册，不启动心跳")
    args = parser.parse_args()
    
    agent = SchedulerAgent(args.agent_id, capabilities=args.capabilities)
    
    if args.register_only:
        agent.register()
    else:
        agent.start()
        print("按 Ctrl+C 停止...")
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            agent.stop()
