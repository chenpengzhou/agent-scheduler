#!/usr/bin/env python3
"""
Agent任务接收工具 - 收到任务时自动通知 + 写入events
"""

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# 飞书群ID
GROUP_ID = "oc_655d32450caf2473e50b5197ff6a7d44"

# 监控数据库
MONITOR_DB = "/home/robin/.openclaw/workspace/monitor/data/monitor.db"

# Agent 名称映射
AGENT_NAMES = {
    "product-manager": "产品-埃姆林",
    "architect": "架构-莎伦",
    "dev-engineer": "开发-阿尔杰",
    "qa-tester": "质量-伦纳德",
    "sre-engineer": "运维-嘉德丽雅",
    "trader": "操盘手-佛尔思",
    "marketing": "运营-奥黛丽",
    "strategy-expert": "策略-沃伦"
}

# 通知模板
NOTIFY_TEMPLATE = "📥 {agent_name} 收到新任务\n任务: {task_name}\n优先级: {priority}\n来自: {from_agent}\n开始执行..."


def write_event(agent_id: str, event_type: str, message: str, 
                input_data: str = None, output_data: str = None) -> bool:
    """写入 events 表"""
    try:
        db_path = Path(MONITOR_DB)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(MONITOR_DB)
        cursor = conn.cursor()
        
        # 确保表存在
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT,
                input_data TEXT,
                output_data TEXT,
                duration_ms INTEGER,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
            )
        """)
        
        # 写入事件
        cursor.execute("""
            INSERT INTO events (agent_id, event_type, message, input_data, output_data, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (agent_id, event_type, message, input_data, output_data, int(time.time())))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"写入事件失败: {e}")
        return False


def send_message(message: str) -> bool:
    """发送消息到飞书群"""
    try:
        import subprocess
        result = subprocess.run([
            "openclaw", "message", "send",
            "--channel", "feishu",
            "--target", GROUP_ID,
            "--message", message
        ], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception as e:
        print(f"发送消息失败: {e}")
        return False


def receive_task(
    agent_key: str,
    task_name: str,
    priority: str = "P2",
    from_agent: str = ""
) -> Dict[str, Any]:
    """
    收到任务时自动通知 + 写入事件
    
    Args:
        agent_key: Agent key (如 dev-engineer)
        task_name: 任务名称
        priority: 优先级 (P0/P1/P2/P3)
        from_agent: 任务来源
    
    Returns:
        执行结果
    """
    agent_name = AGENT_NAMES.get(agent_key, agent_key)
    
    # 构建消息
    message = NOTIFY_TEMPLATE.format(
        agent_name=agent_name,
        task_name=task_name,
        priority=priority,
        from_agent=from_agent or "系统"
    )
    
    # 1. 发送消息
    notify_success = send_message(message)
    
    # 2. 写入事件
    event_success = write_event(
        agent_id=agent_key,
        event_type="task_received",
        message=f"收到任务: {task_name}",
        input_data=json.dumps({"task": task_name, "priority": priority, "from": from_agent}),
        output_data=json.dumps({"notified": notify_success})
    )
    
    return {
        "agent_key": agent_key,
        "agent_name": agent_name,
        "task_name": task_name,
        "priority": priority,
        "from_agent": from_agent,
        "message": message,
        "notified": notify_success,
        "event_written": event_success
    }


# CLI接口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("用法: python receive_task.py <AgentKey> <任务名称> [优先级] [来源]")
        print("")
        print("AgentKey 列表:")
        for k, v in AGENT_NAMES.items():
            print(f"  {k}: {v}")
        print("")
        print("示例:")
        print("  python3 receive_task.py dev-engineer '迭代3开发' P1 product-manager")
        sys.exit(1)
    
    agent_key = sys.argv[1]
    task_name = sys.argv[2]
    priority = sys.argv[3] if len(sys.argv) > 3 else "P2"
    from_agent = sys.argv[4] if len(sys.argv) > 4 else ""
    
    result = receive_task(agent_key, task_name, priority, from_agent)
    print(json.dumps(result, ensure_ascii=False, indent=2))
