#!/usr/bin/env python3
"""
事件发布器 - 本地模块
任务状态变更时发布事件到服务器
"""
import os
import sys
import json
import time
import threading
import queue
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from pathlib import Path

# 配置
SYNC_SERVER_URL = os.environ.get("SYNC_SERVER_URL", "http://localhost:8001")
SYNC_API_KEY = os.environ.get("SYNC_API_KEY", "")
EVENT_QUEUE_SIZE = 100
RETRY_MAX = 3
RETRY_DELAY = 5


class EventPublisher:
    """事件发布器"""
    
    def __init__(self, server_url: str = None, api_key: str = None):
        self.server_url = server_url or SYNC_SERVER_URL
        self.api_key = api_key or SYNC_API_KEY
        self.api_url = f"{self.server_url}/api/v1/sync"
        self._event_queue = queue.Queue(maxsize=EVENT_QUEUE_SIZE)
        self._running = False
        self._thread = None
        self._local_store = Path("/tmp/sync_failed")
        self._local_store.mkdir(exist_ok=True)
    
    def _get_headers(self) -> Dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    def _push_event(self, event: str, data: Dict[str, Any]) -> bool:
        """推送事件到服务器"""
        payload = {
            "event": event,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        for attempt in range(RETRY_MAX):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=5
                )
                if response.status_code == 200:
                    return True
                elif response.status_code == 409:  # 幂等：重复事件
                    return True
                else:
                    print(f"⚠️ 推送失败 ({response.status_code}): {event}")
            except Exception as e:
                print(f"⚠️ 推送异常: {e}")
            
            if attempt < RETRY_MAX - 1:
                time.sleep(RETRY_DELAY)
        
        # 推送失败，暂存本地
        self._save_failed_event(event, data)
        return False
    
    def _save_failed_event(self, event: str, data: Dict):
        """保存失败事件到本地"""
        filename = self._local_store / f"{int(time.time()*1000)}_{event}.json"
        try:
            with open(filename, 'w') as f:
                json.dump({"event": event, "data": data, "timestamp": datetime.now().isoformat()}, f)
            print(f"💾 事件已暂存: {filename}")
        except Exception as e:
            print(f"❌ 暂存失败: {e}")
    
    def _retry_failed_events(self):
        """重试失败的事件"""
        for filepath in self._local_store.glob("*.json"):
            try:
                with open(filepath) as f:
                    event_data = json.load(f)
                
                if self._push_event(event_data["event"], event_data["data"]):
                    filepath.unlink()  # 删除已成功的文件
                    print(f"✅ 重试成功: {filepath.name}")
            except Exception as e:
                print(f"❌ 重试失败: {filepath.name}, {e}")
    
    def publish(self, event: str, data: Dict[str, Any]):
        """发布事件"""
        self._event_queue.put({"event": event, "data": data})
    
    def start(self):
        """启动事件处理循环"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._event_loop, daemon=True)
        self._thread.start()
        print(f"✅ 事件发布器已启动: {self.server_url}")
    
    def stop(self):
        """停止事件处理"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        print("⏹️ 事件发布器已停止")
    
    def _event_loop(self):
        """事件处理循环"""
        while self._running:
            try:
                # 处理队列中的事件
                try:
                    event_data = self._event_queue.get(timeout=1)
                    self._push_event(event_data["event"], event_data["data"])
                except queue.Empty:
                    pass
                
                # 重试失败的事件
                self._retry_failed_events()
                
            except Exception as e:
                print(f"❌ 事件循环异常: {e}")
                time.sleep(1)


# 全局实例
_publisher = None

def get_publisher() -> EventPublisher:
    """获取全局事件发布器"""
    global _publisher
    if _publisher is None:
        _publisher = EventPublisher()
    return _publisher


def publish_task_changed(task_id: str, status: str, agent_id: str, **extra):
    """便捷函数：发布任务变更事件"""
    get_publisher().publish("task_changed", {
        "task_id": task_id,
        "status": status,
        "agent_id": agent_id,
        **extra
    })

def publish_agent_status(agent_id: str, status: str, task_name: str = None):
    """便捷函数：发布 Agent 状态变更"""
    get_publisher().publish("agent_status", {
        "agent_id": agent_id,
        "status": status,
        "task_name": task_name
    })


# ========== 集成到调度系统 ==========
def on_task_status_changed(task_id: str, old_status: str, new_status: str, agent_id: str):
    """任务状态变更回调"""
    publish_task_changed(task_id, new_status, agent_id)


if __name__ == "__main__":
    # 测试
    publisher = EventPublisher()
    publisher.start()
    
    # 测试推送
    publish_task_changed("test-001", "running", "dev-engineer")
    time.sleep(1)
    publish_agent_status("dev-engineer", "busy", "开发任务")
    time.sleep(1)
    
    publisher.stop()
    print("✅ 事件发布器测试完成")
