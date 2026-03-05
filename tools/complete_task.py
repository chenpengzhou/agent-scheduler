#!/usr/bin/env python3
"""
Agent任务完成工具 - 完成任务后通知下一个Agent + 写入events
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, Any, Optional

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

# Agent 流转映射
# 流程: 产品 → 架构(方案设计) → 开发 → 架构(代码审核) → QA → SRE → 验收
DEFAULT_NEXT = {
    "product-manager": "architect",
    "architect": "dev-engineer",
    "dev-engineer": "architect",
    "qa-tester": "sre-engineer",
    "sre-engineer": "product-manager"
}

# 条件分支
BRANCH_NEXT = {
    "architect": {
        "方案通过": "dev-engineer",
        "方案不通过": "product-manager",
        "代码通过": "qa-tester",
        "代码不通过": "dev-engineer"
    },
    "qa-tester": {
        "测试通过": "sre-engineer",
        "测试不通过": "dev-engineer"
    }
}


def write_event(agent_id: str, event_type: str, message: str, 
                input_data: str = None, output_data: str = None) -> bool:
    """写入 events 表"""
    try:
        db_path = Path(MONITOR_DB)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(MONITOR_DB)
        cursor = conn.cursor()
        
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


def complete_task(
    current_agent: str,
    task_name: str,
    result: str = "已完成",
    branch: Optional[str] = None
) -> Dict[str, Any]:
    """
    完成任务并通知下一个Agent + 写入事件
    
    Args:
        current_agent: 当前Agent key
        task_name: 任务名称
        result: 任务结果（如"审核通过"）
        branch: 条件分支（如"通过"或"不通过"）
    
    Returns:
        执行结果
    """
    current_name = AGENT_NAMES.get(current_agent, current_agent)
    
    # 确定下一个Agent
    if branch and current_agent in BRANCH_NEXT:
        next_agent = BRANCH_NEXT[current_agent].get(branch)
    else:
        next_agent = DEFAULT_NEXT.get(current_agent)
    
    if not next_agent:
        return {"error": f"未知Agent或无下一跳: {current_agent}"}
    
    next_name = AGENT_NAMES.get(next_agent, next_agent)
    
    # 构建完成消息
    complete_msg = f"✅ {current_name} 任务完成\n任务: {task_name}\n结果: {result}"
    
    # 构建新任务消息
    new_task_msg = f"""📥 {next_name} 收到新任务
任务: {task_name}
来自: {current_name}
结果: {result}
开始处理..."""
    
    # 1. 发送完成消息
    complete_success = send_message(complete_msg)
    
    # 2. 发送新任务消息给下一个Agent
    next_success = send_message(new_task_msg)
    
    # 3. 写入事件
    event_success = write_event(
        agent_id=current_agent,
        event_type="task_completed",
        message=f"完成任务: {task_name}",
        input_data=json.dumps({"task": task_name, "result": result, "branch": branch}),
        output_data=json.dumps({
            "next_agent": next_agent,
            "notified": next_success
        })
    )
    
    return {
        "current_agent": current_agent,
        "current_name": current_name,
        "next_agent": next_agent,
        "next_name": next_name,
        "task_name": task_name,
        "result": result,
        "branch": branch,
        "complete_msg": complete_msg,
        "new_task_msg": new_task_msg,
        "notified": next_success,
        "event_written": event_success
    }


def get_next_agents(current_agent: str) -> Dict[str, str]:
    """获取当前Agent的所有可能的下一个Agent"""
    result = {}
    if current_agent in BRANCH_NEXT:
        for branch, agent in BRANCH_NEXT[current_agent].items():
            result[branch] = agent
    if current_agent in DEFAULT_NEXT and "默认" not in result:
        result["默认"] = DEFAULT_NEXT[current_agent]
    return result


# CLI接口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("用法: python complete_task.py <当前Agent> <任务名称> [结果] [分支]")
        print("")
        print("Agent列表:")
        for k, v in AGENT_NAMES.items():
            print(f"  {k}: {v}")
        print("")
        print("示例:")
        print("  # 开发完成任务，流转给架构（代码审核）")
        print("  python3 complete_task.py dev-engineer '迭代3开发' '开发完成'")
        print("")
        print("  # 架构审核通过，流转给QA")
        print("  python3 complete_task.py architect '代码审核' '审核通过' 通过")
        print("")
        print("  # 架构审核不通过，流转给开发")
        print("  python3 complete_task.py architect '代码审核' '审核不通过' 不通过")
        print("")
        print("  # QA测试通过，流转给SRE")
        print("  python3 complete_task.py qa-tester '功能测试' '测试通过' 通过")
        sys.exit(1)
    
    current_agent = sys.argv[1]
    task_name = sys.argv[2]
    result = sys.argv[3] if len(sys.argv) > 3 else "已完成"
    branch = sys.argv[4] if len(sys.argv) > 4 else None
    
    result = complete_task(current_agent, task_name, result, branch)
    print(json.dumps(result, ensure_ascii=False, indent=2))
